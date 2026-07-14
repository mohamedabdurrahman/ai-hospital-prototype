from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
from fastapi import APIRouter

from agent.agent_main import run_agent
from agent.tools import forecast_beds, forecast_ed, get_bed_status, get_ed_patients, get_inpatients
from ui.ui_models import AgentRecommendationUI, BedStatusUI, EDStatusUI, ForecastUI, InpatientUI, KPIUI

router = APIRouter()

ROOT = Path(__file__).resolve().parent.parent


def _load_csv(name: str) -> pd.DataFrame:
    return pd.read_csv(ROOT / name)


@router.get("/beds")
def get_ui_beds() -> list[dict[str, Any]]:
    data = get_bed_status()
    items = data.get("items", [])
    response = []
    for item in items:
        response.append(
            BedStatusUI(
                bed_id=str(item.get("bed_id", "")),
                ward_id=str(item.get("ward_id", "")),
                ward_name=item.get("name"),
                specialty=item.get("specialty"),
                occupied=bool(item.get("is_occupied", False)),
            ).model_dump()
        )
    return response


@router.get("/ed")
def get_ui_ed() -> list[dict[str, Any]]:
    data = get_ed_patients()
    items = data.get("items", [])
    response = []
    for item in items:
        response.append(
            EDStatusUI(
                visit_id=str(item.get("visit_id", "")),
                patient_id=str(item.get("patient_id", "")),
                arrival_hour=int(item.get("arrival_hour", 0)),
                triage_category=str(item.get("triage_category", "")),
                admitted=bool(item.get("admitted", False)),
            ).model_dump()
        )
    return response


@router.get("/inpatients")
def get_ui_inpatients() -> list[dict[str, Any]]:
    data = get_inpatients()
    items = data.get("items", [])
    response = []
    for item in items:
        response.append(
            InpatientUI(
                admission_id=str(item.get("admission_id", "")),
                patient_id=str(item.get("patient_id", "")),
                age=int(item.get("age", 0)),
                frailty_score=float(item.get("frailty_score", 0.0)),
                primary_diagnosis=str(item.get("primary_diagnosis", "")),
                los_days=int(item.get("los_days", 0)),
            ).model_dump()
        )
    return response


@router.get("/forecast/ed")
def get_ui_forecast_ed() -> dict[str, Any]:
    data = forecast_ed()
    return ForecastUI(label="ed_arrivals_next_6h", value=float(data.get("forecasted_ed_arrivals_next_6h", 0.0)), unit="patients").model_dump()


@router.get("/forecast/beds")
def get_ui_forecast_beds() -> dict[str, Any]:
    data = forecast_beds()
    return ForecastUI(label="available_beds_next_24h", value=float(data.get("predicted_available_beds_next_24h", 0.0)), unit="beds").model_dump()


@router.get("/kpis")
def get_ui_kpis() -> list[dict[str, Any]]:
    kpis = []
    daily_kpis = _load_csv("daily_kpis.csv")
    if not daily_kpis.empty:
        kpis.append(KPIUI(name="trolley_count_8am", value=float(daily_kpis["trolley_count_8am"].mean()), unit="patients", trend="stable").model_dump())
        kpis.append(KPIUI(name="dtoc_count", value=float(daily_kpis["dtoc_count"].mean()), unit="patients", trend="watch").model_dump())
        kpis.append(KPIUI(name="pet_24hr", value=float(daily_kpis["pet_24hr"].mean()), unit="patients", trend="stable").model_dump())
        kpis.append(KPIUI(name="los_gt_14_days", value=float(daily_kpis["los_gt_14_days"].mean()), unit="patients", trend="watch").model_dump())
    return kpis


@router.post("/run_agent")
def run_agent_endpoint() -> dict[str, Any]:
    result = run_agent()
    return AgentRecommendationUI(
        task=result.get("plan", {}).get("task", "bed_management"),
        summary=result.get("recommendation", {}).get("summary", "No recommendation"),
        priority_actions=result.get("recommendation", {}).get("priority_actions", []),
        explanation=result.get("recommendation", {}).get("explanation", "No explanation provided"),
        confidence=result.get("recommendation", {}).get("confidence", 0.0),
        tool_outputs=result.get("tool_outputs", {}),
    ).model_dump()
