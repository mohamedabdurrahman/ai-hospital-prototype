"""Synthetic hospital data generation.

Wave 1 adds time-aware demand, discharge, DTOC, occupancy, and long-stay
behaviour while preserving every existing response field.
"""

from datetime import datetime, timedelta
import hashlib
import math
from typing import List, Literal, Optional

from .models import (
    Bed,
    BedOccupancyProjectionPoint,
    EDPatient,
    EDArrivalProjectionPoint,
    ForecastInputs,
    ForecastPoint,
    HumanImpactMetrics,
    Inpatient,
    KPI,
    SolForecastInputs,
    SolHumanImpact,
    SolOperationalRisk,
    SolReadyPayload,
    SolScenarioContext,
    SyntheticDataset,
    SyntheticValidation,
    TrendPoint,
)


ENGINE_VERSION = "3.5"
_LAST_GENERATED: Optional[str] = None


SimulationScenario = Literal[
    "baseline",
    "ed_surge",
    "flu_season",
    "ward_closure",
    "staff_shortage",
    "winter_pressure",
    "flu_surge",
    "staffing_shortage",
    "high_dtoc",
    "high_boarding",
    "mixed_pressure",
]

SCENARIO_LABEL = {
    "baseline": "Baseline",
    "ed_surge": "ED Surge",
    "flu_season": "Flu Season",
    "ward_closure": "Ward Closure",
    "staff_shortage": "Staff Shortage",
    "winter_pressure": "Winter Pressure",
    "flu_surge": "Flu Surge",
    "staffing_shortage": "Staffing Shortage",
    "high_dtoc": "High DTOC",
    "high_boarding": "High Boarding",
    "mixed_pressure": "Mixed Pressure",
}

SCENARIO_METADATA = {
    "baseline": {
        "description": "Normal operating conditions with expected daily variation.",
        "pressure_level": "low",
    },
    "ed_surge": {
        "description": "Elevated emergency arrivals with increased boarding pressure.",
        "pressure_level": "high",
    },
    "flu_season": {
        "description": "Seasonal respiratory demand affecting ED, beds, and length of stay.",
        "pressure_level": "high",
    },
    "ward_closure": {
        "description": "Reduced operational bed capacity following a ward closure.",
        "pressure_level": "critical",
    },
    "staff_shortage": {
        "description": "Reduced staffing slows assessment, bed turnaround, and discharge.",
        "pressure_level": "high",
    },
    "winter_pressure": {
        "description": "Seasonal surge with increased ED demand and DTOC pressure.",
        "pressure_level": "high",
    },
    "flu_surge": {
        "description": "Flu-driven surge with high ED arrivals and respiratory LOS.",
        "pressure_level": "high",
    },
    "staffing_shortage": {
        "description": "Reduced staffing causing slower discharge and bed turnover.",
        "pressure_level": "medium",
    },
    "high_dtoc": {
        "description": "Severe DTOC pressure reducing discharge flow.",
        "pressure_level": "high",
    },
    "high_boarding": {
        "description": "ED boarding surge due to constrained inpatient capacity.",
        "pressure_level": "medium",
    },
    "mixed_pressure": {
        "description": (
            "Multiple simultaneous pressures affecting ED, DTOC, staffing, "
            "and occupancy."
        ),
        "pressure_level": "critical",
    },
}

SCENARIO_DRIVERS = {
    "baseline": ["normal_operations"],
    "ed_surge": ["high_ed_arrivals", "high_boarding"],
    "flu_season": [
        "winter_surge",
        "flu_respiratory_cases",
        "high_ed_arrivals",
    ],
    "ward_closure": ["reduced_bed_capacity", "high_bed_occupancy"],
    "staff_shortage": ["staffing_shortage", "slow_bed_turnover"],
    "winter_pressure": [
        "winter_surge",
        "high_ed_arrivals",
        "high_dtoc",
        "staffing_shortage",
    ],
    "flu_surge": [
        "flu_respiratory_cases",
        "high_ed_arrivals",
        "high_boarding",
    ],
    "staffing_shortage": [
        "staffing_shortage",
        "slow_discharge",
        "slow_bed_turnover",
    ],
    "high_dtoc": ["high_dtoc", "long_length_of_stay", "slow_discharge"],
    "high_boarding": [
        "high_boarding",
        "reduced_bed_availability",
        "long_ed_waits",
    ],
    "mixed_pressure": [
        "winter_surge",
        "high_ed_arrivals",
        "high_dtoc",
        "staffing_shortage",
        "high_boarding",
        "reduced_bed_availability",
    ],
}

WARDS = [
    {
        "code": "GMA",
        "name": "St Brigid — General Medicine A",
        "specialty": "General Medicine",
        "beds": 60,
    },
    {
        "code": "GMB",
        "name": "St Brigid — General Medicine B",
        "specialty": "General Medicine",
        "beds": 60,
    },
    {
        "code": "GEA",
        "name": "St Colmcille — Geriatrics A",
        "specialty": "Geriatrics",
        "beds": 40,
    },
    {
        "code": "GEB",
        "name": "St Colmcille — Geriatrics B",
        "specialty": "Geriatrics",
        "beds": 40,
    },
    {
        "code": "SUA",
        "name": "St Patrick — Surgical A",
        "specialty": "Surgical",
        "beds": 45,
    },
    {
        "code": "SUB",
        "name": "St Patrick — Surgical B",
        "specialty": "Surgical",
        "beds": 45,
    },
    {
        "code": "ICU",
        "name": "ICU",
        "specialty": "ICU",
        "beds": 20,
    },
    {
        "code": "SSU",
        "name": "Short Stay Unit",
        "specialty": "Short Stay",
        "beds": 30,
    },
]

DIAGNOSES = [
    "Community-acquired pneumonia",
    "COPD exacerbation",
    "Heart failure",
    "UTI / sepsis",
    "Fall — fractured NOF",
    "Stroke — TIA",
    "Cellulitis",
    "Acute kidney injury",
    "Post-op recovery",
    "Chest pain — NSTEMI",
    "Delirium",
    "Diabetes decompensation",
]

COMPLEX_DISCHARGE_DIAGNOSES = {
    "Fall — fractured NOF",
    "Stroke — TIA",
    "Delirium",
    "UTI / sepsis",
}

RESPIRATORY_DIAGNOSES = (
    "Community-acquired pneumonia",
    "COPD exacerbation",
)

HOURLY_ARRIVAL_MULTIPLIERS = (
    0.70,
    0.62,
    0.55,
    0.50,
    0.48,
    0.55,
    0.72,
    0.90,
    1.05,
    1.18,
    1.28,
    1.35,
    1.32,
    1.22,
    1.15,
    1.10,
    1.13,
    1.22,
    1.38,
    1.45,
    1.38,
    1.22,
    1.05,
    0.86,
)


def _clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


def get_last_generated() -> str:
    """Return the latest generated dataset timestamp for health reporting."""
    return _LAST_GENERATED or datetime.utcnow().isoformat()


def rng(seed: int):
    """Return a small deterministic pseudo-random number generator."""
    t = seed & 0xFFFFFFFF

    def _next() -> float:
        nonlocal t
        t = (t + 0x6D2B79F5) & 0xFFFFFFFF
        x = t
        x = (x ^ (x >> 15)) * (x | 1)
        x ^= x + ((x ^ (x >> 7)) * (x | 61))
        x ^= x >> 14
        return (x & 0xFFFFFFFF) / 4294967296.0

    return _next


def scenario_params(scenario: SimulationScenario) -> dict:
    base = {
        "edMul": 1.0,
        "trolleyMul": 1.0,
        "occTarget": 0.90,
        "losMul": 1.0,
        "cleaningMul": 1.0,
        "closedWards": 0,
        "dtocMul": 1.0,
        "staffingMul": 1.0,
        "surgeChance": 0.03,
        "surgeMin": 0.25,
        "surgeRange": 0.35,
        "triageSeverityShift": 0.0,
        "respiratoryLosMul": 1.0,
        "dischargeThroughputMul": 1.0,
        "boardingMul": 1.0,
        "waitMul": 1.0,
        "bedAvailabilityPenalty": 0.0,
        "dtocLosMul": 1.0,
    }
    overrides = {
        "baseline": {},
        "ed_surge": {
            "edMul": 1.50,
            "trolleyMul": 1.70,
            "occTarget": 0.94,
            "staffingMul": 1.05,
            "surgeChance": 0.35,
        },
        "flu_season": {
            "edMul": 1.35,
            "trolleyMul": 1.30,
            "occTarget": 0.97,
            "losMul": 1.30,
            "cleaningMul": 1.10,
            "dtocMul": 1.20,
            "staffingMul": 1.10,
            "surgeChance": 0.12,
        },
        "ward_closure": {
            "edMul": 1.0,
            "trolleyMul": 1.20,
            "occTarget": 0.98,
            "losMul": 1.05,
            "closedWards": 1,
            "staffingMul": 1.05,
        },
        "staff_shortage": {
            "edMul": 1.05,
            "trolleyMul": 1.20,
            "occTarget": 0.95,
            "losMul": 1.15,
            "cleaningMul": 2.20,
            "closedWards": 0,
            "dtocMul": 1.35,
            "staffingMul": 1.45,
            "surgeChance": 0.05,
        },
        "winter_pressure": {
            "edMul": 1.27,
            "trolleyMul": 1.30,
            "occTarget": 0.96,
            "losMul": 1.12,
            "cleaningMul": 1.15,
            "dtocMul": 1.30,
            "staffingMul": 1.18,
            "surgeChance": 0.07,
            "dischargeThroughputMul": 0.88,
            "boardingMul": 1.10,
            "waitMul": 1.08,
        },
        "flu_surge": {
            "edMul": 1.22,
            "trolleyMul": 1.35,
            "occTarget": 0.96,
            "losMul": 1.08,
            "cleaningMul": 1.55,
            "dtocMul": 1.15,
            "staffingMul": 1.10,
            "surgeChance": 0.12,
            "surgeMin": 0.55,
            "surgeRange": 0.45,
            "triageSeverityShift": 0.10,
            "respiratoryLosMul": 1.45,
            "boardingMul": 1.15,
            "waitMul": 1.10,
        },
        "staffing_shortage": {
            "trolleyMul": 1.35,
            "occTarget": 0.95,
            "losMul": 1.10,
            "cleaningMul": 2.60,
            "dtocMul": 1.25,
            "staffingMul": 1.50,
            "surgeChance": 0.04,
            "dischargeThroughputMul": 0.55,
            "boardingMul": 1.30,
            "waitMul": 1.35,
            "bedAvailabilityPenalty": 0.025,
        },
        "high_dtoc": {
            "trolleyMul": 1.20,
            "occTarget": 0.96,
            "losMul": 1.12,
            "cleaningMul": 1.10,
            "dtocMul": 2.30,
            "staffingMul": 1.10,
            "dischargeThroughputMul": 0.55,
            "boardingMul": 1.10,
            "dtocLosMul": 1.55,
        },
        "high_boarding": {
            "edMul": 1.10,
            "trolleyMul": 1.75,
            "occTarget": 0.97,
            "losMul": 1.05,
            "cleaningMul": 1.50,
            "dtocMul": 1.10,
            "staffingMul": 1.15,
            "boardingMul": 1.55,
            "waitMul": 1.45,
            "bedAvailabilityPenalty": 0.04,
        },
        "mixed_pressure": {
            "edMul": 1.35,
            "trolleyMul": 1.90,
            "occTarget": 0.985,
            "losMul": 1.30,
            "cleaningMul": 2.70,
            "dtocMul": 2.40,
            "staffingMul": 1.65,
            "surgeChance": 0.12,
            "surgeMin": 0.40,
            "surgeRange": 0.45,
            "dischargeThroughputMul": 0.45,
            "boardingMul": 1.60,
            "waitMul": 1.55,
            "bedAvailabilityPenalty": 0.05,
            "dtocLosMul": 1.60,
        },
    }
    return {**base, **overrides.get(scenario, {})}


def _scenario_seed(scenario: str) -> int:
    return sum((index + 1) * ord(character) for index, character in enumerate(scenario))


def _weekday_multiplier(moment: datetime) -> float:
    return 1.10 if moment.weekday() >= 5 else 1.0


def _seasonal_multiplier(month: int) -> float:
    if month in (12, 1, 2):
        return 1.20
    if month in (3, 11):
        return 1.10
    if month in (7, 8):
        return 0.94
    return 1.0


def _arrival_multiplier(moment: datetime) -> float:
    return (
        HOURLY_ARRIVAL_MULTIPLIERS[moment.hour]
        * _weekday_multiplier(moment)
        * _seasonal_multiplier(moment.month)
    )


def _discharge_window_multiplier(hour: int) -> float:
    if 8 <= hour < 12:
        return 1.75
    if 12 <= hour < 16:
        return 1.15
    if 16 <= hour < 20:
        return 0.65
    return 0.25


def _pick_triage(r, severity_shift: float = 0.0) -> str:
    value = r()
    red_threshold = _clamp(0.07 + severity_shift * 0.35, 0.07, 0.18)
    orange_threshold = _clamp(
        0.32 + severity_shift,
        red_threshold + 0.10,
        0.55,
    )
    yellow_threshold = _clamp(0.68 + severity_shift * 0.30, 0.68, 0.78)
    if value < red_threshold:
        return "Red"
    if value < orange_threshold:
        return "Orange"
    if value < yellow_threshold:
        return "Yellow"
    if value < 0.92:
        return "Green"
    return "Blue"


def _pick_diagnosis(r, scenario_name: str) -> str:
    if scenario_name == "flu_surge" and r() < 0.45:
        return RESPIRATORY_DIAGNOSES[int(r() * len(RESPIRATORY_DIAGNOSES))]
    return DIAGNOSES[int(r() * len(DIAGNOSES))]


def _ed_wait_risk(ed: List[EDPatient]) -> float:
    if not ed:
        return 0.0

    target_minutes = {
        "Red": 15,
        "Orange": 60,
        "Yellow": 120,
        "Green": 240,
        "Blue": 240,
    }
    severity_weight = {
        "Red": 1.0,
        "Orange": 0.85,
        "Yellow": 0.65,
        "Green": 0.35,
        "Blue": 0.25,
    }
    weighted_risk = 0.0
    total_weight = 0.0
    for patient in ed:
        target = target_minutes.get(patient.triage_category, 240)
        weight = severity_weight.get(patient.triage_category, 0.25)
        weighted_risk += _clamp(patient.wait_minutes / target, 0.0, 1.0) * weight
        total_weight += weight
    return weighted_risk / max(total_weight, 1.0)


def _dataset_checksum(dataset: SyntheticDataset) -> str:
    total_ed_arrivals = sum(
        point.arrivals
        for point in dataset.forecast_inputs.ed_arrivals_next_24h
    )
    checksum_input = (
        f"{dataset.seed}|{dataset.scenario_name}|"
        f"{total_ed_arrivals}|{len(dataset.beds)}"
    )
    return hashlib.sha256(checksum_input.encode("utf-8")).hexdigest()


def _validate_dataset(dataset: SyntheticDataset, params: dict) -> SyntheticValidation:
    payload = dataset.dict()
    required_top_level = {
        "kpis",
        "ed",
        "beds",
        "inpatients",
        "edForecast",
        "bedForecast",
        "as_of",
        "seed",
        "human_impact",
        "forecast_inputs",
        "scenario_name",
        "scenario_description",
        "scenario_pressure_level",
        "sol_ready",
        "validation",
        "checksum",
        "engine_version",
    }
    json_structure_ok = (
        required_top_level <= set(payload)
        and dataset.engine_version == ENGINE_VERSION
        and len(dataset.checksum) == 64
        and dataset.sol_ready.recommended_actions == []
    )

    operational_beds = [bed for bed in dataset.beds if bed.type != "closed"]
    occupied_beds = [bed for bed in operational_beds if bed.occupied]
    capacity_limits_ok = (
        len(occupied_beds) <= len(operational_beds)
        and len(dataset.inpatients) == len(occupied_beds)
        and len(dataset.beds) == len({bed.bed_id for bed in dataset.beds})
        and not any(
            bed.occupied for bed in dataset.beds if bed.type == "closed"
        )
    )

    baseline_params = scenario_params("baseline")
    effect_keys = {
        "edMul",
        "trolleyMul",
        "occTarget",
        "losMul",
        "cleaningMul",
        "dtocMul",
        "staffingMul",
        "boardingMul",
        "waitMul",
        "dischargeThroughputMul",
    }
    has_expected_modifier = dataset.scenario_name == "baseline" or any(
        params[key] != baseline_params[key] for key in effect_keys
    )
    context = dataset.sol_ready.scenario_context
    scenario_effects_ok = (
        dataset.scenario_name in SCENARIO_METADATA
        and has_expected_modifier
        and context.scenario_name == dataset.scenario_name
        and context.scenario_pressure_level == dataset.scenario_pressure_level
        and context.scenario_description == dataset.scenario_description
        and bool(context.scenario_drivers)
    )

    kpi_values = {kpi.label: kpi.value for kpi in dataset.kpis}
    unit_interval_kpis = {
        "ed_overcrowding_risk",
        "ed_wait_risk",
        "bed_pressure_risk",
        "dtoc_pressure_risk",
        "long_stay_pressure_risk",
        "staffing_pressure_risk",
    }
    score_kpis = {"hospital_kpi_score", "operational_risk_score"}
    count_kpis = {
        "discharge_opportunity_count",
        "dtoc_count",
        "long_stay_count",
        "average_length_of_stay",
    }
    kpi_ranges_ok = (
        all(0.0 <= kpi_values.get(label, -1.0) <= 1.0 for label in unit_interval_kpis)
        and all(0.0 <= kpi_values.get(label, -1.0) <= 100.0 for label in score_kpis)
        and all(kpi_values.get(label, -1.0) >= 0.0 for label in count_kpis)
    )

    wave_two_forecast = dataset.forecast_inputs
    sol_forecast = dataset.sol_ready.forecast_inputs
    forecast_lengths_ok = (
        len(dataset.edForecast) == 12
        and len(dataset.bedForecast) == 24
        and len(wave_two_forecast.ed_arrivals_next_24h) == 24
        and len(wave_two_forecast.bed_occupancy_next_24h) == 24
        and len(wave_two_forecast.dtoc_trend) == 5
        and len(wave_two_forecast.los_trend) == 5
        and len(sol_forecast.ed_arrivals_next_24h) == 24
        and len(sol_forecast.bed_occupancy_next_24h) == 24
        and len(sol_forecast.dtoc_trend_5d) == 5
        and len(sol_forecast.los_trend_5d) == 5
    )

    legacy_kpis = {
        "hospital_kpi_score",
        "ed_overcrowding_risk",
        "bed_pressure_risk",
        "discharge_opportunity_count",
        "dtoc_count",
        "long_stay_count",
        "average_length_of_stay",
    }
    backward_compatibility_ok = (
        legacy_kpis <= set(kpi_values)
        and isinstance(dataset.kpis, list)
        and isinstance(dataset.ed, list)
        and isinstance(dataset.beds, list)
        and isinstance(dataset.inpatients, list)
        and isinstance(dataset.edForecast, list)
        and isinstance(dataset.bedForecast, list)
    )

    return SyntheticValidation(
        json_structure_ok=json_structure_ok,
        capacity_limits_ok=capacity_limits_ok,
        scenario_effects_ok=scenario_effects_ok,
        kpi_ranges_ok=kpi_ranges_ok,
        forecast_lengths_ok=forecast_lengths_ok,
        backward_compatibility_ok=backward_compatibility_ok,
    )


def _age_for_specialty(r, specialty: str) -> int:
    if specialty == "Geriatrics":
        return 68 + int(r() * 28)
    if specialty == "ICU":
        return 30 + int(r() * 66)
    if specialty == "Short Stay":
        return 18 + int(r() * 72)
    return 35 + int(r() * 61)


def _frailty_score(r, age: int) -> int:
    age_pressure = max(0.0, (age - 55) / 40.0) * 5.0
    return round(_clamp(age_pressure + r() * 4.0, 0.0, 9.0))


def _long_stay_probability(
    age: int,
    frailty_score: int,
    specialty: str,
    diagnosis: str,
    los_multiplier: float,
) -> float:
    probability = 0.035
    probability += max(0, age - 70) / 25.0 * 0.05
    probability += frailty_score / 9.0 * 0.08
    probability += 0.05 if specialty == "Geriatrics" else 0.0
    probability += 0.03 if specialty == "ICU" else 0.0
    probability += 0.035 if diagnosis in COMPLEX_DISCHARGE_DIAGNOSES else 0.0
    probability += max(0.0, los_multiplier - 1.0) * 0.10
    return _clamp(probability, 0.03, 0.35)


def _base_length_of_stay(r, specialty: str, long_stay: bool, frailty: int) -> int:
    if long_stay:
        return min(90, 15 + int((r() ** 0.70) * 46) + round(frailty * 0.6))
    if specialty == "Short Stay":
        return 1 + int(r() * 3)
    if specialty == "Surgical":
        return 2 + int(r() * 8)
    if specialty == "ICU":
        return 4 + int(r() * 11)
    if specialty == "Geriatrics":
        return 4 + int(r() * 10)
    return 2 + int(r() * 10)


def _dtoc_probability(
    age: int,
    frailty_score: int,
    specialty: str,
    diagnosis: str,
    length_of_stay: int,
    long_stay: bool,
    dtoc_multiplier: float,
    staffing_multiplier: float,
) -> float:
    probability = 0.012
    probability += max(0, age - 65) / 30.0 * 0.035
    probability += frailty_score / 9.0 * 0.055
    probability += min(length_of_stay, 30) / 30.0 * 0.025
    probability += 0.05 if long_stay else 0.0
    probability += 0.025 if specialty == "Geriatrics" else 0.0
    probability += 0.02 if diagnosis in COMPLEX_DISCHARGE_DIAGNOSES else 0.0
    probability *= dtoc_multiplier
    probability *= 1.0 + max(0.0, staffing_multiplier - 1.0) * 0.30
    return _clamp(probability, 0.01, 0.40)


def generate_synthetic_hospital(
    scenario: SimulationScenario = "baseline",
    seed: int = 42,
    as_of: Optional[datetime] = None,
) -> SyntheticDataset:
    global _LAST_GENERATED

    reference_time = as_of or datetime.utcnow()
    scenario_name = scenario if scenario in SCENARIO_METADATA else "baseline"
    scenario_metadata = SCENARIO_METADATA[scenario_name]
    r = rng(seed + _scenario_seed(scenario_name) * 7919)
    params = scenario_params(scenario_name)

    surge_active = r() < params["surgeChance"]
    surge_multiplier = 1.0 + (
        params["surgeMin"] + r() * params["surgeRange"]
        if surge_active
        else 0.0
    )
    surge_duration_hours = 2 + int(r() * 4) if surge_active else 0
    current_arrival_pressure = (
        _arrival_multiplier(reference_time)
        * params["edMul"]
        * surge_multiplier
    )

    # Beds: each physical bed receives a globally unique ward-based ID.
    active_count = len(WARDS) - params["closedWards"]
    active_wards = WARDS[:active_count]
    closed_wards = WARDS[active_count:]
    beds: List[Bed] = []

    effective_occupancy_target = _clamp(
        params["occTarget"]
        + max(0.0, params["staffingMul"] - 1.0) * 0.04
        + max(0.0, current_arrival_pressure - 1.0) * 0.015
        + params["bedAvailabilityPenalty"],
        0.60,
        0.985,
    )
    cleaning_probability = _clamp(
        0.025 * params["cleaningMul"] * params["staffingMul"]
        + params["bedAvailabilityPenalty"],
        0.01,
        0.15,
    )

    for ward in active_wards:
        for index in range(ward["beds"]):
            cleaning = r() < cleaning_probability
            occupancy_probability = _clamp(
                effective_occupancy_target + (r() - 0.5) * 0.08,
                0.0,
                0.99,
            )
            occupied = not cleaning and r() < occupancy_probability
            beds.append(
                Bed(
                    bed_id=f"{ward['code']}-{index + 1:03d}",
                    ward_name=ward["name"],
                    specialty=ward["specialty"],
                    occupied=occupied,
                    type="cleaning" if cleaning else ("occupied" if occupied else "free"),
                )
            )

    for ward in closed_wards:
        for index in range(ward["beds"]):
            beds.append(
                Bed(
                    bed_id=f"{ward['code']}-{index + 1:03d}",
                    ward_name=f"{ward['name']} (CLOSED)",
                    specialty=ward["specialty"],
                    occupied=False,
                    type="closed",
                )
            )

    operational_beds = [bed for bed in beds if bed.type != "closed"]
    occupied_beds = [bed for bed in operational_beds if bed.occupied]
    operational_capacity = len(operational_beds)
    occupancy_now = len(occupied_beds) / max(1, operational_capacity)

    # ED: census, waits, and boarding respond to hour, weekend, season, surge,
    # occupancy, and staffing pressure.
    base_ed_census = 45 + int(r() * 24)
    census_multiplier = 0.65 + 0.35 * current_arrival_pressure
    ed_count = max(1, round(base_ed_census * census_multiplier))
    trolley_rate = _clamp(
        (
            0.16
            + max(0.0, occupancy_now - 0.85) * 1.45
            + max(0.0, params["staffingMul"] - 1.0) * 0.18
        )
        * params["trolleyMul"]
        * params["boardingMul"],
        0.05,
        0.85,
    )
    trolley_count = min(ed_count, round(ed_count * trolley_rate))
    awaiting_bed_probability = _clamp(
        (
            0.18
            + max(0.0, occupancy_now - 0.82) * 1.40
            + max(0.0, params["staffingMul"] - 1.0) * 0.20
        )
        * params["boardingMul"],
        0.12,
        0.85,
    )
    wait_pressure = _clamp(
        0.72
        + current_arrival_pressure * 0.28
        + max(0.0, occupancy_now - 0.85) * 0.80,
        0.65,
        2.50,
    ) * params["staffingMul"] * params["waitMul"]
    ed: List[EDPatient] = []

    wait_bases = {
        "Red": 10,
        "Orange": 75,
        "Yellow": 150,
        "Green": 220,
        "Blue": 260,
    }
    for index in range(ed_count):
        triage = _pick_triage(r, params["triageSeverityShift"])
        wait_minutes = round(
            wait_bases[triage] * wait_pressure * (0.65 + r() * 0.75)
        )
        ed.append(
            EDPatient(
                patient_id=f"ED-{1000 + index}",
                triage_category=triage,
                on_trolley=index < trolley_count,
                wait_minutes=max(0, wait_minutes),
                awaiting_bed=r() < awaiting_bed_probability,
            )
        )

    # Inpatients: one patient per occupied operational bed guarantees that
    # occupancy never exceeds capacity and keeps ward assignment consistent.
    inpatients: List[Inpatient] = []
    discharge_window = _discharge_window_multiplier(reference_time.hour)
    weekend_discharge_multiplier = 0.72 if reference_time.weekday() >= 5 else 1.0

    for index, bed in enumerate(occupied_beds):
        age = _age_for_specialty(r, bed.specialty)
        frailty = _frailty_score(r, age)
        diagnosis = _pick_diagnosis(r, scenario_name)
        long_stay = r() < _long_stay_probability(
            age=age,
            frailty_score=frailty,
            specialty=bed.specialty,
            diagnosis=diagnosis,
            los_multiplier=params["losMul"],
        )
        length_of_stay = _base_length_of_stay(
            r,
            specialty=bed.specialty,
            long_stay=long_stay,
            frailty=frailty,
        )
        if diagnosis in RESPIRATORY_DIAGNOSES:
            length_of_stay = round(
                length_of_stay * params["respiratoryLosMul"]
            )
        length_of_stay = max(1, round(length_of_stay * params["losMul"]))

        dtoc = r() < _dtoc_probability(
            age=age,
            frailty_score=frailty,
            specialty=bed.specialty,
            diagnosis=diagnosis,
            length_of_stay=length_of_stay,
            long_stay=long_stay,
            dtoc_multiplier=params["dtocMul"],
            staffing_multiplier=params["staffingMul"],
        )
        if dtoc:
            dtoc_los_extension = 2 + int(
                r()
                * 10
                * (1.0 + max(0.0, params["staffingMul"] - 1.0))
                * params["dtocLosMul"]
            )
            length_of_stay = min(120, length_of_stay + dtoc_los_extension)

        discharge_probability = (
            0.055 * discharge_window
            + min(length_of_stay, 14) / 14.0 * 0.025
        )
        discharge_probability *= weekend_discharge_multiplier
        discharge_probability *= params["dischargeThroughputMul"]
        discharge_probability /= params["staffingMul"]
        if long_stay:
            discharge_probability *= 0.85
        discharge_ready = (
            not dtoc
            and r() < _clamp(discharge_probability, 0.005, 0.30)
        )

        predicted_days = 0 if discharge_ready else 1 + int(r() * 6)
        if dtoc:
            predicted_days += 2 + int(r() * 7)
        if long_stay and not discharge_ready:
            predicted_days += 1 + int(r() * 3)
        predicted_date = (
            reference_time + timedelta(days=predicted_days)
        ).date().isoformat()

        inpatients.append(
            Inpatient(
                patient_id=f"IP-{2000 + index}",
                age=age,
                frailty_score=frailty,
                diagnosis=diagnosis,
                ward=bed.ward_name,
                predicted_discharge_date=predicted_date,
                length_of_stay=length_of_stay,
                discharge_ready=discharge_ready,
                dtoc=dtoc,
            )
        )

    # ED forecast — next 12 hours, preserving the existing forecast contract.
    ed_forecast: List[ForecastPoint] = []
    base_hourly_arrivals = 9.0 * params["edMul"]
    for offset in range(12):
        forecast_time = reference_time + timedelta(hours=offset)
        forecast_surge = (
            surge_multiplier if surge_active and offset < surge_duration_hours else 1.0
        )
        jitter = 0.85 + r() * 0.30
        arrivals = round(
            base_hourly_arrivals
            * _arrival_multiplier(forecast_time)
            * forecast_surge
            * jitter
        )
        ed_forecast.append(
            ForecastPoint(
                time=f"{forecast_time.hour:02d}:00",
                arrivals=max(0, arrivals),
            )
        )

    # Bed forecast — next 48 hours, bounded to available operational capacity.
    bed_forecast: List[ForecastPoint] = []
    for offset in range(0, 48, 2):
        forecast_time = reference_time + timedelta(hours=offset)
        daily_cycle = math.sin(
            ((forecast_time.hour - 14) / 24.0) * math.pi * 2
        ) * 0.025
        morning_discharge_release = -0.018 if 9 <= forecast_time.hour < 13 else 0.0
        staffing_drift = max(0.0, params["staffingMul"] - 1.0) * (offset / 48.0) * 0.03
        noise = (r() - 0.5) * 0.025
        forecast_occupancy = _clamp(
            occupancy_now
            + daily_cycle
            + morning_discharge_release
            + staffing_drift
            + noise,
            0.0,
            1.0,
        )
        bed_forecast.append(
            ForecastPoint(
                time=f"+{offset}h",
                beds=round(forecast_occupancy, 2),
            )
        )

    # Wave 2 forecast inputs use an independent seeded stream so the existing
    # 12-hour ED and 48-hour bed forecast values remain unchanged.
    projection_random = rng(
        seed + _scenario_seed(scenario_name) * 104729 + 202
    )
    ed_arrivals_next_24h: List[EDArrivalProjectionPoint] = []
    bed_occupancy_next_24h: List[BedOccupancyProjectionPoint] = []

    for offset in range(1, 25):
        forecast_time = reference_time + timedelta(hours=offset)
        forecast_surge = (
            surge_multiplier
            if surge_active and offset < surge_duration_hours
            else 1.0
        )
        arrival_jitter = 0.90 + projection_random() * 0.20
        projected_arrivals = round(
            base_hourly_arrivals
            * _arrival_multiplier(forecast_time)
            * forecast_surge
            * arrival_jitter
        )
        ed_arrivals_next_24h.append(
            EDArrivalProjectionPoint(
                time=forecast_time.isoformat(timespec="minutes"),
                arrivals=max(0, projected_arrivals),
            )
        )

        daily_cycle = math.sin(
            ((forecast_time.hour - 14) / 24.0) * math.pi * 2
        ) * 0.025
        morning_release = -0.018 if 9 <= forecast_time.hour < 13 else 0.0
        staffing_drift = (
            max(0.0, params["staffingMul"] - 1.0)
            * (offset / 24.0)
            * 0.025
        )
        occupancy_noise = (projection_random() - 0.5) * 0.018
        projected_occupancy = _clamp(
            occupancy_now
            + daily_cycle
            + morning_release
            + staffing_drift
            + occupancy_noise,
            0.0,
            1.0,
        )
        bed_occupancy_next_24h.append(
            BedOccupancyProjectionPoint(
                time=forecast_time.isoformat(timespec="minutes"),
                occupancy=round(projected_occupancy, 3),
            )
        )

    # Existing KPI labels are retained unchanged for UI and score compatibility.
    actual_awaiting_rate = (
        sum(patient.awaiting_bed for patient in ed) / len(ed) if ed else 0.0
    )
    actual_trolley_rate = trolley_count / len(ed) if ed else 0.0
    ed_risk = _clamp(
        actual_trolley_rate * 0.45
        + actual_awaiting_rate * 0.35
        + _clamp(current_arrival_pressure / 1.80, 0.0, 1.0) * 0.20,
        0.0,
        1.0,
    )
    bed_risk = _clamp(
        occupancy_now * 0.90
        + (0.10 if params["closedWards"] > 0 else 0.0)
        + max(0.0, params["staffingMul"] - 1.0) * 0.10,
        0.0,
        1.0,
    )
    discharge_opportunities = sum(
        inpatient.discharge_ready for inpatient in inpatients
    )
    dtoc_count = sum(inpatient.dtoc for inpatient in inpatients)
    long_stay_count = sum(
        inpatient.length_of_stay > 14 for inpatient in inpatients
    )
    inpatient_count = len(inpatients)
    average_los = (
        sum(inpatient.length_of_stay for inpatient in inpatients) / inpatient_count
        if inpatients
        else 0.0
    )
    ed_wait_risk = _clamp(_ed_wait_risk(ed), 0.0, 1.0)
    dtoc_pressure_risk = _clamp(
        (dtoc_count / max(1, inpatient_count)) / 0.15,
        0.0,
        1.0,
    )
    long_stay_pressure_risk = _clamp(
        (long_stay_count / max(1, inpatient_count)) / 0.25,
        0.0,
        1.0,
    )
    cleaning_rate = (
        sum(bed.type == "cleaning" for bed in operational_beds)
        / max(1, operational_capacity)
    )
    configured_staffing_pressure = _clamp(
        (params["staffingMul"] - 1.0) / 0.50,
        0.0,
        1.0,
    )
    staffing_pressure_risk = _clamp(
        configured_staffing_pressure * 0.70
        + _clamp(cleaning_rate / 0.08, 0.0, 1.0) * 0.30,
        0.0,
        1.0,
    )
    patient_flow_risk = _clamp(
        ed_wait_risk * 0.30
        + bed_risk * 0.30
        + dtoc_pressure_risk * 0.25
        + long_stay_pressure_risk * 0.15,
        0.0,
        1.0,
    )
    operational_risk_score = round(
        100
        * _clamp(
            ed_wait_risk * 0.25
            + bed_risk * 0.25
            + dtoc_pressure_risk * 0.20
            + long_stay_pressure_risk * 0.15
            + staffing_pressure_risk * 0.15,
            0.0,
            1.0,
        )
    )
    hospital_kpi_score = 100 - operational_risk_score

    delayed_bed_hours = sum(
        patient.wait_minutes / 60.0
        for patient in ed
        if patient.awaiting_bed or patient.on_trolley
    )
    delayed_bed_hours *= 1.0 + _clamp(
        (occupancy_now - 0.85) / 0.15,
        0.0,
        1.0,
    ) * 0.50

    delayed_discharge_hours = 0.0
    for inpatient in inpatients:
        if inpatient.dtoc:
            delayed_discharge_hours += 24.0 + min(
                inpatient.length_of_stay,
                30,
            ) * 6.0
        elif inpatient.discharge_ready:
            delayed_discharge_hours += 8.0
        if inpatient.length_of_stay > 14:
            delayed_discharge_hours += min(
                inpatient.length_of_stay - 14,
                60,
            ) * 2.0

    human_impact = HumanImpactMetrics(
        delayed_bed_hours=round(delayed_bed_hours, 1),
        delayed_discharge_hours=round(delayed_discharge_hours, 1),
        delayed_triage_risk=round(ed_wait_risk, 3),
        patient_flow_risk=round(patient_flow_risk, 3),
    )

    dtoc_trend: List[TrendPoint] = []
    los_trend: List[TrendPoint] = []
    for offset in range(0, 25, 6):
        forecast_time = reference_time + timedelta(hours=offset)
        morning_release = 0.04 if 9 <= forecast_time.hour < 13 else 0.0
        time_fraction = offset / 24.0
        dtoc_growth = (
            dtoc_pressure_risk * 0.08
            + staffing_pressure_risk * 0.05
        ) * time_fraction
        projected_dtoc = max(
            0.0,
            dtoc_count * (1.0 + dtoc_growth - morning_release),
        )
        dtoc_trend.append(
            TrendPoint(
                time=forecast_time.isoformat(timespec="minutes"),
                value=round(projected_dtoc, 1),
            )
        )

        los_growth = (
            dtoc_pressure_risk * 0.06
            + long_stay_pressure_risk * 0.05
            + staffing_pressure_risk * 0.04
        ) * time_fraction
        projected_los = max(
            0.0,
            average_los * (1.0 + los_growth - morning_release * 0.50),
        )
        los_trend.append(
            TrendPoint(
                time=forecast_time.isoformat(timespec="minutes"),
                value=round(projected_los, 1),
            )
        )

    forecast_inputs = ForecastInputs(
        ed_arrivals_next_24h=ed_arrivals_next_24h,
        bed_occupancy_next_24h=bed_occupancy_next_24h,
        dtoc_trend=dtoc_trend,
        los_trend=los_trend,
    )

    sol_ed_risk_score = round(
        _clamp(ed_risk * 0.55 + ed_wait_risk * 0.45, 0.0, 1.0) * 100
    )
    sol_bed_risk_score = round(_clamp(bed_risk, 0.0, 1.0) * 100)
    sol_dtoc_risk_score = round(
        _clamp(dtoc_pressure_risk, 0.0, 1.0) * 100
    )
    sol_los_risk_score = round(
        _clamp(long_stay_pressure_risk, 0.0, 1.0) * 100
    )
    sol_staffing_risk_score = round(
        _clamp(staffing_pressure_risk, 0.0, 1.0) * 100
    )
    sol_overall_risk_score = round(
        sol_ed_risk_score * 0.25
        + sol_bed_risk_score * 0.25
        + sol_dtoc_risk_score * 0.20
        + sol_los_risk_score * 0.15
        + sol_staffing_risk_score * 0.15
    )

    patients_delayed_over_4h = sum(
        patient.wait_minutes > 240 for patient in ed
    ) + sum(
        inpatient.dtoc
        or inpatient.discharge_ready
        or inpatient.length_of_stay > 14
        for inpatient in inpatients
    )
    patients_delayed_over_12h = sum(
        patient.wait_minutes > 720 for patient in ed
    ) + sum(
        inpatient.dtoc or inpatient.length_of_stay > 14
        for inpatient in inpatients
    )
    patients_boarded_in_ed = sum(
        patient.on_trolley or patient.awaiting_bed for patient in ed
    )

    if sol_overall_risk_score < 40:
        clinical_risk_level = "low"
    elif sol_overall_risk_score < 70:
        clinical_risk_level = "medium"
    else:
        clinical_risk_level = "high"

    dtoc_trend_5d: List[int] = []
    los_trend_5d: List[float] = []
    dtoc_daily_pressure = _clamp(
        dtoc_pressure_risk * 0.05
        + staffing_pressure_risk * 0.03
        + long_stay_pressure_risk * 0.02
        - params["dischargeThroughputMul"] * 0.01,
        0.0,
        0.12,
    )
    los_daily_pressure = _clamp(
        dtoc_pressure_risk * 0.025
        + long_stay_pressure_risk * 0.035
        + staffing_pressure_risk * 0.02,
        0.0,
        0.10,
    )
    for day in range(1, 6):
        dtoc_trend_5d.append(
            max(0, round(dtoc_count * (1.0 + dtoc_daily_pressure * day)))
        )
        los_trend_5d.append(
            round(max(0.0, average_los * (1.0 + los_daily_pressure * day)), 1)
        )

    sol_ready = SolReadyPayload(
        operational_risk=SolOperationalRisk(
            overall_risk_score=sol_overall_risk_score,
            ed_risk_score=sol_ed_risk_score,
            bed_risk_score=sol_bed_risk_score,
            dtoc_risk_score=sol_dtoc_risk_score,
            los_risk_score=sol_los_risk_score,
            staffing_risk_score=sol_staffing_risk_score,
        ),
        human_impact=SolHumanImpact(
            patients_delayed_over_4h=patients_delayed_over_4h,
            patients_delayed_over_12h=patients_delayed_over_12h,
            patients_boarded_in_ed=patients_boarded_in_ed,
            total_delayed_bed_hours=human_impact.delayed_bed_hours,
            total_delayed_discharge_hours=(
                human_impact.delayed_discharge_hours
            ),
            clinical_risk_level=clinical_risk_level,
        ),
        scenario_context=SolScenarioContext(
            scenario_name=scenario_name,
            scenario_pressure_level=scenario_metadata["pressure_level"],
            scenario_description=scenario_metadata["description"],
            scenario_drivers=SCENARIO_DRIVERS[scenario_name],
        ),
        forecast_inputs=SolForecastInputs(
            ed_arrivals_next_24h=[
                point.arrivals for point in ed_arrivals_next_24h
            ],
            bed_occupancy_next_24h=[
                round(point.occupancy * 100)
                for point in bed_occupancy_next_24h
            ],
            dtoc_trend_5d=dtoc_trend_5d,
            los_trend_5d=los_trend_5d,
        ),
        recommended_actions=[],
    )

    kpis: List[KPI] = [
        KPI(label="hospital_kpi_score", value=hospital_kpi_score, unit=""),
        KPI(label="ed_overcrowding_risk", value=round(ed_risk, 2)),
        KPI(label="ed_wait_risk", value=round(ed_wait_risk, 3)),
        KPI(label="bed_pressure_risk", value=round(bed_risk, 2)),
        KPI(label="dtoc_pressure_risk", value=round(dtoc_pressure_risk, 3)),
        KPI(
            label="long_stay_pressure_risk",
            value=round(long_stay_pressure_risk, 3),
        ),
        KPI(
            label="staffing_pressure_risk",
            value=round(staffing_pressure_risk, 3),
        ),
        KPI(
            label="operational_risk_score",
            value=float(operational_risk_score),
        ),
        KPI(
            label="discharge_opportunity_count",
            value=float(discharge_opportunities),
        ),
        KPI(label="dtoc_count", value=float(dtoc_count)),
        KPI(label="long_stay_count", value=float(long_stay_count)),
        KPI(label="average_length_of_stay", value=round(average_los, 1), unit="d"),
    ]

    dataset = SyntheticDataset(
        kpis=kpis,
        ed=ed,
        beds=beds,
        inpatients=inpatients,
        edForecast=ed_forecast,
        bedForecast=bed_forecast,
        as_of=reference_time.isoformat(),
        seed=seed,
        human_impact=human_impact,
        forecast_inputs=forecast_inputs,
        scenario_name=scenario_name,
        scenario_description=scenario_metadata["description"],
        scenario_pressure_level=scenario_metadata["pressure_level"],
        sol_ready=sol_ready,
        engine_version=ENGINE_VERSION,
    )
    dataset.checksum = _dataset_checksum(dataset)
    dataset.validation = _validate_dataset(dataset, params)
    _LAST_GENERATED = dataset.as_of
    return dataset


def overlay_synthetic(
    live: Optional[SyntheticDataset],
    scenario: SimulationScenario,
    seed: int = 42,
    as_of: Optional[datetime] = None,
) -> SyntheticDataset:
    synthetic = generate_synthetic_hospital(
        scenario=scenario,
        seed=seed,
        as_of=as_of,
    )

    if live is None:
        return synthetic

    return SyntheticDataset(
        kpis=live.kpis if live.kpis else synthetic.kpis,
        ed=live.ed if live.ed else synthetic.ed,
        beds=live.beds if live.beds else synthetic.beds,
        inpatients=live.inpatients if live.inpatients else synthetic.inpatients,
        edForecast=live.edForecast if live.edForecast else synthetic.edForecast,
        bedForecast=live.bedForecast if live.bedForecast else synthetic.bedForecast,
        as_of=synthetic.as_of,
        seed=synthetic.seed,
        human_impact=synthetic.human_impact,
        forecast_inputs=synthetic.forecast_inputs,
        scenario_name=synthetic.scenario_name,
        scenario_description=synthetic.scenario_description,
        scenario_pressure_level=synthetic.scenario_pressure_level,
        sol_ready=synthetic.sol_ready,
        validation=synthetic.validation,
        checksum=synthetic.checksum,
        engine_version=synthetic.engine_version,
    )
