from __future__ import annotations

import logging
from typing import Any

from agent.prompts import (
    bed_allocation_prompt,
    discharge_opportunity_prompt,
    elective_risk_prompt,
    situation_assessment_prompt,
)
from agent.tools import forecast_beds, forecast_ed

logger = logging.getLogger(__name__)


class BedManagementPlanner:
    def __init__(self) -> None:
        self.logger = logger

    def build_plan(self, data: dict[str, Any]) -> dict[str, Any]:
        ed_forecast = data.get("ed_forecast", {}).get("forecasted_ed_arrivals_next_6h", 0)
        beds_forecast = data.get("beds_forecast", {}).get("predicted_available_beds_next_24h", 0)
        dtoc_signal = data.get("dtoc_signal", "medium")
        elective_load = data.get("elective_load", "medium")

        if ed_forecast >= 20 or beds_forecast <= 8:
            task = "bed allocation under ED pressure"
            tools_to_call = ["forecast_ed", "forecast_beds"]
            prompt = bed_allocation_prompt(
                {
                    "ed_pressure": "high" if ed_forecast >= 20 else "medium",
                    "forecasted_beds": beds_forecast,
                    "frail_patients": data.get("frail_patients", 0),
                    "older_adult_count": data.get("older_adult_count", 0),
                    "admission_count": data.get("admission_count", 0),
                }
            )
        elif dtoc_signal in {"high", "very_high"}:
            task = "discharge opportunity review"
            tools_to_call = ["forecast_beds", "forecast_ed"]
            prompt = discharge_opportunity_prompt(
                {
                    "dtoc_signal": dtoc_signal,
                    "forecasted_beds": beds_forecast,
                    "frail_patients": data.get("frail_patients", 0),
                    "older_adult_count": data.get("older_adult_count", 0),
                    "discharge_candidates": data.get("discharge_candidates", 0),
                }
            )
        elif elective_load in {"high", "very_high"}:
            task = "elective admission risk review"
            tools_to_call = ["forecast_beds", "forecast_ed"]
            prompt = elective_risk_prompt(
                {
                    "elective_load": elective_load,
                    "forecasted_beds": beds_forecast,
                    "ed_pressure": "high" if ed_forecast >= 20 else "medium",
                    "dtoc_signal": dtoc_signal,
                }
            )
        else:
            task = "situational bed management assessment"
            tools_to_call = ["forecast_beds", "forecast_ed"]
            prompt = situation_assessment_prompt(
                {
                    "ed_pressure": "medium" if ed_forecast >= 12 else "low",
                    "forecasted_beds": beds_forecast,
                    "dtoc_signal": dtoc_signal,
                    "elective_load": elective_load,
                    "frail_patients": data.get("frail_patients", 0),
                    "older_adult_count": data.get("older_adult_count", 0),
                }
            )

        return {
            "task": task,
            "tools_to_call": tools_to_call,
            "prompt": prompt,
            "context": {
                "ed_forecast": ed_forecast,
                "beds_forecast": beds_forecast,
                "dtoc_signal": dtoc_signal,
                "elective_load": elective_load,
                "frail_patients": data.get("frail_patients", 0),
                "older_adult_count": data.get("older_adult_count", 0),
                "admission_count": data.get("admission_count", 0),
                "discharge_candidates": data.get("discharge_candidates", 0),
            },
        }
