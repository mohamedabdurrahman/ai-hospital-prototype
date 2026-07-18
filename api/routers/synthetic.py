# routes/synthetic.py

from fastapi import APIRouter
from typing import Optional

from ..synthetic_data import (
    generate_synthetic_hospital,
    overlay_synthetic,
)
from ..models import SyntheticDataset

router = APIRouter()


@router.get("/synthetic", response_model=SyntheticDataset)
def get_synthetic_data(
    scenario: str = "baseline",
    seed: int = 42,
):
    """
    Generate a full synthetic hospital dataset.
    This mirrors the Lovable TypeScript simulator.
    """
    return generate_synthetic_hospital(
        scenario=scenario,
        seed=seed,
    )


@router.post("/overlay", response_model=SyntheticDataset)
def overlay_data(
    live_data: Optional[SyntheticDataset] = None,
    scenario: str = "baseline",
):
    """
    Overlay synthetic values onto partial live data.
    If live_data contains empty lists, synthetic values fill them.
    """
    return overlay_synthetic(
        live=live_data,
        scenario=scenario,
    )


@router.get("/scenario/{scenario_name}", response_model=SyntheticDataset)
def get_scenario(
    scenario_name: str,
    seed: int = 42,
):
    """
    Generate synthetic data for a specific scenario:
    - baseline
    - ed_surge
    - flu_season
    - ward_closure
    - staff_shortage
    """
    return generate_synthetic_hospital(
        scenario=scenario_name,
        seed=seed,
    )


@router.get("/forecast", response_model=SyntheticDataset)
def get_forecast(
    scenario: str = "baseline",
    seed: int = 42,
):
    """
    Return only the forecast portion of the synthetic dataset.
    Useful for GPT‑5.6 Sol forecasting prompts.
    """
    dataset = generate_synthetic_hospital(
        scenario=scenario,
        seed=seed,
    )
    return SyntheticDataset(
        kpis=[],
        ed=[],
        beds=[],
        inpatients=[],
        edForecast=dataset.edForecast,
        bedForecast=dataset.bedForecast,
    )
