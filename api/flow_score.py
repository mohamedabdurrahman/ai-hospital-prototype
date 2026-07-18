"""Calculate an explainable operational Flow Score.

The calculation uses only fields already present in ``SyntheticDataset`` and
does not change or extend the existing synthetic hospital response contract.
"""

from .models import SyntheticDataset


FLOW_SCORE_VERSION = "flow-v1"


def _clamp(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    return max(lower, min(upper, value))


def _ratio(numerator: int, denominator: int) -> float:
    return numerator / denominator if denominator else 0.0


def _capacity_pressure(occupancy: float) -> float:
    """Map occupancy from 85%-100% onto a 0-1 pressure scale."""
    return _clamp((occupancy - 0.85) / 0.15)


def calculate_flow_score(dataset: SyntheticDataset) -> dict:
    """Calculate a 0-100 Flow Score; higher means healthier flow."""

    operational_beds = [
        bed for bed in dataset.beds if bed.type.lower() != "closed"
    ]
    unavailable_beds = sum(
        1
        for bed in operational_beds
        if bed.occupied or bed.type.lower() == "cleaning"
    )
    unavailable_rate = _ratio(unavailable_beds, len(operational_beds))
    bed_capacity = 100.0 * (1.0 - _capacity_pressure(unavailable_rate))

    ed_count = len(dataset.ed)
    trolley_rate = _ratio(
        sum(patient.on_trolley for patient in dataset.ed),
        ed_count,
    )
    awaiting_bed_rate = _ratio(
        sum(patient.awaiting_bed for patient in dataset.ed),
        ed_count,
    )
    four_hour_breach_rate = _ratio(
        sum(patient.wait_minutes > 240 for patient in dataset.ed),
        ed_count,
    )
    ed_pressure = _clamp(
        0.40 * trolley_rate
        + 0.35 * awaiting_bed_rate
        + 0.25 * four_hour_breach_rate
    )
    ed_boarding = 100.0 * (1.0 - ed_pressure)

    inpatient_count = len(dataset.inpatients)
    dtoc_rate = _ratio(
        sum(patient.dtoc for patient in dataset.inpatients),
        inpatient_count,
    )
    discharge_ready_rate = _ratio(
        sum(patient.discharge_ready for patient in dataset.inpatients),
        inpatient_count,
    )
    discharge_pressure = _clamp(
        0.65 * _clamp(dtoc_rate / 0.10)
        + 0.35 * _clamp(discharge_ready_rate / 0.15)
    )
    discharge_flow = 100.0 * (1.0 - discharge_pressure)

    forecast_occupancies = [
        point.beds
        for point in dataset.bedForecast
        if point.beds is not None
    ]
    peak_forecast_occupancy = max(forecast_occupancies, default=0.0)
    forecast_resilience = 100.0 * (
        1.0 - _capacity_pressure(peak_forecast_occupancy)
    )

    flow_score = round(
        0.30 * bed_capacity
        + 0.30 * ed_boarding
        + 0.25 * discharge_flow
        + 0.15 * forecast_resilience
    )

    if flow_score >= 80:
        status = "Stable"
    elif flow_score >= 60:
        status = "Strained"
    elif flow_score >= 40:
        status = "High Risk"
    else:
        status = "Critical"

    return {
        "flow_score": flow_score,
        "status": status,
        "components": {
            "bed_capacity": round(bed_capacity, 2),
            "ed_boarding": round(ed_boarding, 2),
            "discharge_flow": round(discharge_flow, 2),
            "forecast_resilience": round(forecast_resilience, 2),
        },
        "version": FLOW_SCORE_VERSION,
    }
