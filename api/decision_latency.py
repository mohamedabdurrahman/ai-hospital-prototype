# api/decision_latency.py

from typing import Optional
from .models import SyntheticDataset

def calculate_decision_latency_score(dataset: SyntheticDataset) -> dict:
    """
    Decision Latency Score (0–100)
    Higher score = more delay in hospital decision-making.
    """

    # Extract key metrics
    ed_risk = next((k.value for k in dataset.kpis if k.label == "ed_overcrowding_risk"), 0)
    bed_risk = next((k.value for k in dataset.kpis if k.label == "bed_pressure_risk"), 0)
    dtoc_count = next((k.value for k in dataset.kpis if k.label == "dtoc_count"), 0)
    long_stay = next((k.value for k in dataset.kpis if k.label == "long_stay_count"), 0)

    # Weighted components
    ed_component = ed_risk * 35
    bed_component = bed_risk * 30
    dtoc_component = min(25, (dtoc_count / 20) * 25)
    long_stay_component = min(10, (long_stay / 30) * 10)

    # Total score
    score = ed_component + bed_component + dtoc_component + long_stay_component
    score = min(100, round(score))

    # Classification
    if score < 35:
        level = "Low"
    elif score < 70:
        level = "Medium"
    else:
        level = "High"

    return {
        "decision_latency_score": score,
        "level": level,
        "components": {
            "ed_component": round(ed_component, 2),
            "bed_component": round(bed_component, 2),
            "dtoc_component": round(dtoc_component, 2),
            "long_stay_component": round(long_stay_component, 2),
        }
    }
