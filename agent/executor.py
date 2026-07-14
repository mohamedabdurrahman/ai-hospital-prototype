from __future__ import annotations

import json
import logging
import os
from typing import Any

from openai import OpenAI

from agent.planner import BedManagementPlanner
from agent.tools import (
    forecast_beds,
    forecast_ed,
    get_bed_status,
    get_ed_patients,
    get_inpatients,
    predict_discharge,
    predict_los,
)

logger = logging.getLogger(__name__)


class BedManagementExecutor:
    def __init__(self) -> None:
        self.planner = BedManagementPlanner()
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY")) if os.getenv("OPENAI_API_KEY") else None

    def run(self, data: dict[str, Any]) -> dict[str, Any]:
        tool_outputs: dict[str, Any] = {}

        try:
            tool_outputs["inpatients"] = get_inpatients()
            tool_outputs["ed_patients"] = get_ed_patients()
            tool_outputs["bed_status"] = get_bed_status()
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.warning("State tool call failed: %s", exc)

        inpatient_items = tool_outputs.get("inpatients", {}).get("items", [])
        frail_patients = sum(1 for item in inpatient_items if item.get("frailty_score", 0) >= 0.75)
        older_adult_count = sum(1 for item in inpatient_items if item.get("age", 0) >= 75)
        admission_count = len(inpatient_items)
        ed_count = tool_outputs.get("ed_patients", {}).get("count", 0)

        runtime_context = {
            **data,
            "frail_patients": frail_patients,
            "older_adult_count": older_adult_count,
            "admission_count": admission_count,
            "ed_count": ed_count,
        }

        try:
            tool_outputs["forecast_ed"] = forecast_ed()
            tool_outputs["forecast_beds"] = forecast_beds()
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.warning("Forecast tool call failed: %s", exc)

        runtime_context["ed_forecast"] = tool_outputs.get("forecast_ed", {})
        runtime_context["beds_forecast"] = tool_outputs.get("forecast_beds", {})

        plan = self.planner.build_plan(runtime_context)

        for tool_name in plan["tools_to_call"]:
            try:
                if tool_name == "forecast_ed":
                    tool_outputs[tool_name] = forecast_ed()
                elif tool_name == "forecast_beds":
                    tool_outputs[tool_name] = forecast_beds()
                elif tool_name == "predict_los":
                    tool_outputs[tool_name] = predict_los(data.get("patient_id", ""))
                elif tool_name == "predict_discharge":
                    tool_outputs[tool_name] = predict_discharge(data.get("admission_id", ""))
            except Exception as exc:  # pragma: no cover - defensive logging
                logger.warning("Tool call failed: %s", exc)
                tool_outputs[tool_name] = {"error": str(exc)}

        final_prompt = plan["prompt"] + "\n\nTool observations:\n" + json.dumps(tool_outputs, indent=2)

        heuristic_confidence = 0.62
        if runtime_context.get("ed_forecast", {}).get("forecasted_ed_arrivals_next_6h", 0) > 30:
            heuristic_confidence += 0.08
        if runtime_context.get("beds_forecast", {}).get("predicted_available_beds_next_24h", 0) < 8:
            heuristic_confidence += 0.08
        if frail_patients >= 5:
            heuristic_confidence += 0.06
        heuristic_confidence = min(0.95, heuristic_confidence)

        if self.client is None:
            return {
                "plan": plan,
                "tool_outputs": tool_outputs,
                "recommendation": {
                    "summary": "OpenAI API key not configured. Returning heuristic recommendation.",
                    "explanation": "The recommendation prioritises frail and older adults, protects ED trolley capacity, and escalates discharge planning because the current operational signals are at elevated risk.",
                    "confidence": heuristic_confidence,
                    "priority_actions": [
                        "Prioritise frail and older adults for bed allocation.",
                        "Escalate discharge planning for DTOC risks.",
                        "Monitor ED pressure and protect trolley capacity.",
                    ],
                },
            }

        completion = self.client.responses.create(
            model="gpt-4o-mini",
            input=[
                {
                    "role": "system",
                    "content": "You are a hospital operations AI helping with bed management and discharge planning.",
                },
                {"role": "user", "content": final_prompt},
            ],
            temperature=0.2,
        )

        content = completion.output_text if hasattr(completion, "output_text") else str(completion)
        confidence = 0.8
        if tool_outputs.get("forecast_ed", {}).get("forecasted_ed_arrivals_next_6h", 0) > 25:
            confidence += 0.05
        if tool_outputs.get("forecast_beds", {}).get("predicted_available_beds_next_24h", 0) < 8:
            confidence += 0.05
        confidence = min(0.95, confidence)
        return {
            "plan": plan,
            "tool_outputs": tool_outputs,
            "recommendation": {
                "summary": content,
                "explanation": "The agent used current ED, bed, and discharge signals to recommend immediate operational actions.",
                "confidence": confidence,
            },
        }
