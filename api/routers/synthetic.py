"""Synthetic hospital data routes."""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter

from ..decision_latency import calculate_decision_latency_score
from ..flow_score import calculate_flow_score
from ..models import SyntheticDataset
from ..synthetic_data import (
    generate_synthetic_hospital,
    overlay_synthetic,
)


router = APIRouter()


@router.get("/synthetic", response_model=SyntheticDataset)
def get_synthetic_data(
    scenario: str = "baseline",
    seed: int = 42,
    as_of: Optional[datetime] = None,
):
    """Generate a full synthetic hospital dataset."""
    return generate_synthetic_hospital(
        scenario=scenario,
        seed=seed,
        as_of=as_of,
    )


@router.post("/overlay", response_model=SyntheticDataset)
def overlay_data(
    live_data: Optional[SyntheticDataset] = None,
    scenario: str = "baseline",
    seed: int = 42,
    as_of: Optional[datetime] = None,
):
    """
    Overlay synthetic values onto partial live data.

    Existing empty-list behaviour is retained for backwards compatibility.
    """
    return overlay_synthetic(
        live=live_data,
        scenario=scenario,
        seed=seed,
        as_of=as_of,
    )


@router.get("/scenario/{scenario_name}", response_model=SyntheticDataset)
def get_scenario(
    scenario_name: str,
    seed: int = 42,
    as_of: Optional[datetime] = None,
):
    """
    Generate synthetic data for a specific scenario:

    - baseline
    - ed_surge
    - flu_season
    - ward_closure
    - staff_shortage
    - winter_pressure
    - flu_surge
    - staffing_shortage
    - high_dtoc
    - high_boarding
    - mixed_pressure
    """
    return generate_synthetic_hospital(
        scenario=scenario_name,
        seed=seed,
        as_of=as_of,
    )


@router.get("/forecast", response_model=SyntheticDataset)
def get_forecast(
    scenario: str = "baseline",
    seed: int = 42,
    as_of: Optional[datetime] = None,
):
    """
    Return only the forecast portion of the synthetic dataset.

    Useful for GPT-5.6 Sol forecasting prompts.
    """
    dataset = generate_synthetic_hospital(
        scenario=scenario,
        seed=seed,
        as_of=as_of,
    )
    return SyntheticDataset(
        kpis=[],
        ed=[],
        beds=[],
        inpatients=[],
        edForecast=dataset.edForecast,
        bedForecast=dataset.bedForecast,
        as_of=dataset.as_of,
        seed=dataset.seed,
        human_impact=dataset.human_impact,
        forecast_inputs=dataset.forecast_inputs,
        scenario_name=dataset.scenario_name,
        scenario_description=dataset.scenario_description,
        scenario_pressure_level=dataset.scenario_pressure_level,
        sol_ready=dataset.sol_ready,
    )


@router.get("/decision-latency")
def get_decision_latency(
    scenario: str = "baseline",
    seed: int = 42,
):
    """Return the Decision Latency Score for the selected scenario."""
    dataset = generate_synthetic_hospital(scenario=scenario, seed=seed)
    return calculate_decision_latency_score(dataset)


@router.get("/flow-score")
def get_flow_score(
    scenario: str = "baseline",
    seed: int = 42,
) -> dict:
    """Return the operational Flow Score for the selected scenario."""
    dataset = generate_synthetic_hospital(scenario=scenario, seed=seed)
    return calculate_flow_score(dataset)


@router.get("/sol-forecast")
def sol_forecast(
    scenario: str = "baseline",
    seed: int = 42,
):
    """
    Generate a GPT-5.6 Sol forecasting prompt.

    The prompt covers ED arrivals, bed occupancy, DTOC pressure, and human
    impact while preserving the existing response field.
    """
    dataset = generate_synthetic_hospital(scenario=scenario, seed=seed)

    prompt = f"""
You are GPT-5.6 Sol, an advanced forecasting model.

Use the following synthetic hospital dataset to produce:
1. ED arrivals forecast (next 12 hours)
2. Bed occupancy forecast (next 48 hours)
3. DTOC escalation risk
4. Human impact analysis
5. Recommended operational actions
6. Confidence level

DATASET:
ED Forecast: {dataset.edForecast}
Bed Forecast: {dataset.bedForecast}
KPIs: {dataset.kpis}
Inpatients: {len(dataset.inpatients)} patients
Scenario: {scenario}

Respond in structured JSON with keys:
- ed_forecast
- bed_forecast
- dtoc_risk
- human_impact
- recommended_actions
- confidence
"""

    return {"prompt": prompt}
