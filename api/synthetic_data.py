"""Synthetic hospital data generation.

Wave 1 adds time-aware demand, discharge, DTOC, occupancy, and long-stay
behaviour while preserving every existing response field.
"""

from datetime import datetime, timedelta
import hashlib
import math
from typing import List, Literal, Optional, Tuple

from .models import (
    Bed,
    BedOccupancyProjectionPoint,
    DeltaItem,
    EDPatient,
    EDArrivalProjectionPoint,
    FlowScoreV2,
    FlowScoreV3,
    ForecastInputs,
    ForecastPoint,
    HumanImpactMetrics,
    Inpatient,
    JudgeBriefingV2,
    JudgeMode,
    KPI,
    OperationalNarrative,
    PrioritizedAction,
    ScenarioDelta,
    ScenarioOverlayResponse,
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


def _calculate_flow_score_v2(
    ed_overcrowding_risk: float,
    ed_wait_risk: float,
    boarded_count: int,
    ed_count: int,
    bed_pressure_risk: float,
    average_los: float,
    long_stay_count: int,
    inpatient_count: int,
    dtoc_count: int,
    discharge_opportunities: int,
) -> FlowScoreV2:
    """Calculate deterministic operational flow scores on a 0-100 scale."""
    boarding_pressure = _clamp(
        boarded_count / max(1, ed_count),
        0.0,
        1.0,
    )
    ed_flow = 100.0 * (
        1.0
        - _clamp(
            ed_overcrowding_risk * 0.45
            + ed_wait_risk * 0.35
            + boarding_pressure * 0.20,
            0.0,
            1.0,
        )
    )

    los_pressure = _clamp(average_los / 14.0, 0.0, 1.0)
    long_stay_pressure = _clamp(
        (long_stay_count / max(1, inpatient_count)) / 0.25,
        0.0,
        1.0,
    )
    inpatient_flow = 100.0 * (
        1.0
        - _clamp(
            bed_pressure_risk * 0.50
            + los_pressure * 0.30
            + long_stay_pressure * 0.20,
            0.0,
            1.0,
        )
    )

    dtoc_pressure = _clamp(
        (dtoc_count / max(1, inpatient_count)) / 0.15,
        0.0,
        1.0,
    )
    discharge_opportunity_health = _clamp(
        (discharge_opportunities / max(1, inpatient_count)) / 0.12,
        0.0,
        1.0,
    )
    discharge_flow = 100.0 * (
        (1.0 - dtoc_pressure) * 0.65
        + discharge_opportunity_health * 0.35
    )

    ed_flow = round(_clamp(ed_flow, 0.0, 100.0), 1)
    inpatient_flow = round(_clamp(inpatient_flow, 0.0, 100.0), 1)
    discharge_flow = round(_clamp(discharge_flow, 0.0, 100.0), 1)
    overall_flow_score = round(
        ed_flow * 0.35
        + inpatient_flow * 0.35
        + discharge_flow * 0.30,
        1,
    )
    return FlowScoreV2(
        ed_flow=ed_flow,
        inpatient_flow=inpatient_flow,
        discharge_flow=discharge_flow,
        overall_flow_score=overall_flow_score,
    )


def _calculate_flow_score_v3(
    ed: List[EDPatient],
    ed_overcrowding_risk: float,
    boarded_count: int,
    bed_pressure_risk: float,
    inpatients: List[Inpatient],
    long_stay_count: int,
    dtoc_count: int,
    discharge_opportunities: int,
    staffing_pressure_risk: float,
) -> FlowScoreV3:
    """Calculate scenario-responsive flow from deterministic current state."""
    ed_count = len(ed)
    four_hour_breach_rate = (
        sum(patient.wait_minutes > 240 for patient in ed)
        / max(1, ed_count)
    )
    boarding_rate = boarded_count / max(1, ed_count)
    ed_pressure = _clamp(
        four_hour_breach_rate * 0.40
        + boarding_rate * 0.35
        + ed_overcrowding_risk * 0.25,
        0.0,
        1.0,
    )
    ed_flow = 100.0 * (1.0 - ed_pressure)

    inpatient_count = len(inpatients)
    excess_los_pressure = _clamp(
        sum(
            max(0, inpatient.length_of_stay - 14)
            for inpatient in inpatients
        )
        / max(1, inpatient_count * 30),
        0.0,
        1.0,
    )
    long_stay_pressure = _clamp(
        (long_stay_count / max(1, inpatient_count)) / 0.25,
        0.0,
        1.0,
    )
    inpatient_pressure = _clamp(
        bed_pressure_risk * 0.45
        + excess_los_pressure * 0.30
        + long_stay_pressure * 0.25,
        0.0,
        1.0,
    )
    inpatient_flow = 100.0 * (1.0 - inpatient_pressure)

    excess_dtoc_pressure = _clamp(
        max(0, dtoc_count - 20) / 20.0,
        0.0,
        1.0,
    )
    discharge_opportunity_health = _clamp(
        (discharge_opportunities / max(1, inpatient_count)) / 0.12,
        0.0,
        1.0,
    )
    discharge_pressure = _clamp(
        excess_dtoc_pressure * 0.65
        + (1.0 - discharge_opportunity_health) * 0.35,
        0.0,
        1.0,
    )
    discharge_flow = 100.0 * (1.0 - discharge_pressure)

    staffing_excess_pressure = _clamp(
        (staffing_pressure_risk - 0.30) / 0.70,
        0.0,
        1.0,
    )
    staffing_flow = 100.0 * (1.0 - staffing_excess_pressure)

    ed_flow = round(_clamp(ed_flow, 0.0, 100.0), 1)
    inpatient_flow = round(_clamp(inpatient_flow, 0.0, 100.0), 1)
    discharge_flow = round(_clamp(discharge_flow, 0.0, 100.0), 1)
    staffing_flow = round(_clamp(staffing_flow, 0.0, 100.0), 1)
    overall_flow_score = round(
        ed_flow * 0.30
        + inpatient_flow * 0.30
        + discharge_flow * 0.25
        + staffing_flow * 0.15,
        1,
    )
    return FlowScoreV3(
        ed_flow=ed_flow,
        inpatient_flow=inpatient_flow,
        discharge_flow=discharge_flow,
        staffing_flow=staffing_flow,
        overall_flow_score=overall_flow_score,
    )


def _highest_priority(*priorities: str) -> str:
    priority_rank = {"high": 0, "medium": 1, "low": 2}
    return min(priorities, key=priority_rank.__getitem__)


def _recommended_actions(
    scenario_name: str,
    ed_wait_risk: float,
    max_ed_wait_minutes: int,
    boarded_count: int,
    bed_pressure_risk: float,
    cleaning_bed_count: int,
    dtoc_count: int,
    long_stay_count: int,
    staffing_pressure_risk: float,
    discharge_opportunities: int,
) -> Tuple[List[str], List[PrioritizedAction]]:
    """Return legacy strings and typed actions in deterministic priority order."""
    scenario_actions = {
        "baseline": "Maintain the current cross-site flow huddle cadence.",
        "ed_surge": "Activate the ED surge streaming workflow.",
        "flu_season": "Use the seasonal respiratory demand workflow.",
        "ward_closure": "Reallocate admissions around the closed ward capacity.",
        "staff_shortage": "Rebalance available staff toward flow-critical areas.",
        "winter_pressure": "Activate the winter pressure coordination plan.",
        "flu_surge": "Use the respiratory demand escalation workflow.",
        "staffing_shortage": "Rebalance available staff toward flow-critical areas.",
        "high_dtoc": "Convene the DTOC escalation huddle.",
        "high_boarding": "Trigger the ED boarding reduction protocol.",
        "mixed_pressure": "Activate the whole-hospital pressure response plan.",
    }
    if max_ed_wait_minutes > 300:
        ed_priority = "high"
    elif max_ed_wait_minutes >= 180:
        ed_priority = "medium"
    else:
        ed_priority = "low"

    if dtoc_count > 25:
        dtoc_priority = "high"
    elif dtoc_count >= 15:
        dtoc_priority = "medium"
    else:
        dtoc_priority = "low"

    if bed_pressure_risk > 0.85:
        bed_priority = "high"
    elif bed_pressure_risk >= 0.75:
        bed_priority = "medium"
    else:
        bed_priority = "low"

    staffing_priority = (
        "high" if staffing_pressure_risk > 0.40 else "low"
    )
    scenario_priority = _highest_priority(
        ed_priority,
        dtoc_priority,
        bed_priority,
        staffing_priority,
    )

    actions: List[PrioritizedAction] = []

    def add(action: str, priority: str) -> None:
        if action not in {item.action for item in actions}:
            actions.append(PrioritizedAction(action=action, priority=priority))

    add(scenario_actions[scenario_name], scenario_priority)
    if ed_wait_risk >= 0.50:
        add(
            "Deploy rapid triage and streaming to reduce current ED waits.",
            ed_priority,
        )
    if boarded_count > 0:
        add(
            "Review boarded ED patients in the next operational flow huddle.",
            ed_priority,
        )
    if bed_pressure_risk >= 0.75:
        add("Review bed allocation across operational wards.", bed_priority)
    if cleaning_bed_count > 0:
        add(
            "Prioritize turnaround for beds already awaiting cleaning.",
            bed_priority,
        )
    if dtoc_count > 0:
        add(
            "Escalate DTOC barriers through the discharge coordination huddle.",
            dtoc_priority,
        )
    if long_stay_count > 0:
        add(
            "Review patients with LOS over 14 days for operational blockers.",
            "low",
        )
    if staffing_pressure_risk >= 0.35:
        add(
            "Rebalance available staffing toward ED flow and bed turnaround.",
            staffing_priority,
        )
    if discharge_opportunities > 0:
        add(
            "Prioritize discharge-ready patients in the operational huddle.",
            dtoc_priority,
        )

    fallback_actions = (
        "Confirm current ED, bed, and discharge constraints at the flow huddle.",
        "Review the current bed turnaround queue with site operations.",
        "Track discharge opportunities through the daily coordination cycle.",
    )
    for action in fallback_actions:
        if len(actions) >= 3:
            break
        add(action, "low")

    priority_rank = {"high": 0, "medium": 1, "low": 2}
    prioritized_actions = sorted(
        actions,
        key=lambda item: priority_rank[item.priority],
    )[:7]
    recommended_actions = [item.action for item in prioritized_actions]
    return recommended_actions, prioritized_actions


def _risk_band(score: float) -> str:
    if score < 40:
        return "low"
    if score < 70:
        return "moderate"
    if score < 85:
        return "high"
    return "severe"


def _operational_narrative(
    scenario_name: str,
    scenario_pressure_level: str,
    flow_score_v2: FlowScoreV2,
    ed_count: int,
    ed_risk_score: int,
    ed_delays_over_4h: int,
    boarded_count: int,
    occupied_bed_count: int,
    operational_capacity: int,
    bed_risk_score: int,
    long_stay_count: int,
    dtoc_count: int,
    discharge_opportunities: int,
    overall_risk_score: int,
    staffing_risk_score: int,
    clinical_risk_level: str,
) -> OperationalNarrative:
    """Build a short factual narrative without advice or predictions."""
    return OperationalNarrative(
        summary=(
            f"{SCENARIO_LABEL[scenario_name]} is active at "
            f"{scenario_pressure_level} pressure with an overall flow score "
            f"of {flow_score_v2.overall_flow_score:.1f}/100."
        ),
        ed_status=(
            f"ED pressure is {_risk_band(ed_risk_score)} with {ed_count} "
            f"patients, {ed_delays_over_4h} waits over 4 hours, and "
            f"{boarded_count} boarded patients."
        ),
        inpatient_status=(
            f"Inpatient bed pressure is {_risk_band(bed_risk_score)} with "
            f"{occupied_bed_count} of {operational_capacity} operational beds "
            f"occupied and {long_stay_count} long-stay patients."
        ),
        discharge_status=(
            f"Discharge flow is {_risk_band(100.0 - flow_score_v2.discharge_flow)} "
            f"pressure with {dtoc_count} DTOC patients and "
            f"{discharge_opportunities} discharge opportunities."
        ),
        risk_summary=(
            f"Overall operational risk is {overall_risk_score}/100 "
            f"({clinical_risk_level}); staffing risk is "
            f"{staffing_risk_score}/100."
        ),
    )


def _judge_mode_and_executive_summary(
    scenario_name: str,
    scenario_pressure_level: str,
    flow_score_v3: FlowScoreV3,
    prioritized_actions: List[PrioritizedAction],
    overall_risk_score: int,
    ed_risk_score: int,
    bed_risk_score: int,
    dtoc_risk_score: int,
    los_risk_score: int,
    staffing_risk_score: int,
    patients_delayed_over_4h: int,
    patients_boarded_in_ed: int,
    total_delayed_bed_hours: float,
    total_delayed_discharge_hours: float,
    dtoc_count: int,
    long_stay_count: int,
) -> Tuple[JudgeMode, str]:
    """Build the deterministic judge briefing and executive summary."""
    risk_candidates = [
        (
            ed_risk_score,
            f"ED risk is {ed_risk_score}/100 with "
            f"{patients_delayed_over_4h} patients delayed over 4 hours.",
        ),
        (
            bed_risk_score,
            f"Bed risk is {bed_risk_score}/100 with "
            f"{patients_boarded_in_ed} patients boarded in ED and "
            f"{total_delayed_bed_hours:.1f} delayed bed hours.",
        ),
        (
            dtoc_risk_score,
            f"DTOC risk is {dtoc_risk_score}/100 with {dtoc_count} DTOC "
            f"patients and {total_delayed_discharge_hours:.1f} delayed "
            "discharge hours.",
        ),
        (
            los_risk_score,
            f"LOS risk is {los_risk_score}/100 with {long_stay_count} "
            "patients staying over 14 days.",
        ),
        (
            staffing_risk_score,
            f"Staffing risk is {staffing_risk_score}/100 across current "
            "flow operations.",
        ),
    ]
    key_risks = [
        risk_text
        for _, risk_text in sorted(
            risk_candidates,
            key=lambda item: -item[0],
        )[:5]
    ]

    flow_components = (
        ("ED", flow_score_v3.ed_flow),
        ("inpatient", flow_score_v3.inpatient_flow),
        ("discharge", flow_score_v3.discharge_flow),
        ("staffing", flow_score_v3.staffing_flow),
    )
    constrained_label, constrained_score = min(
        flow_components,
        key=lambda item: item[1],
    )
    judge_mode = JudgeMode(
        headline=(
            f"{SCENARIO_LABEL[scenario_name]} is at "
            f"{scenario_pressure_level} pressure with operational risk "
            f"{overall_risk_score}/100 and Flow Score v3 "
            f"{flow_score_v3.overall_flow_score:.1f}/100."
        ),
        key_risks=key_risks,
        key_actions=prioritized_actions[:3],
        flow_summary=(
            f"Flow Score v3 is {flow_score_v3.overall_flow_score:.1f}/100, "
            f"with {constrained_label} flow the most constrained component "
            f"at {constrained_score:.1f}/100."
        ),
    )

    risk_summary = "; ".join(
        risk.rstrip(".") for risk in key_risks[:3]
    )
    action_summary = "; ".join(
        action.action.rstrip(".") for action in prioritized_actions[:3]
    )
    executive_summary = (
        f"The {SCENARIO_LABEL[scenario_name]} scenario is active at "
        f"{scenario_pressure_level} pressure, with Flow Score v3 at "
        f"{flow_score_v3.overall_flow_score:.1f}/100. "
        f"Key operational risks are: {risk_summary}. "
        f"Recommended actions are: {action_summary}."
    )
    return judge_mode, executive_summary


def _kpi_value(dataset: SyntheticDataset, label: str) -> float:
    return next(
        (float(kpi.value) for kpi in dataset.kpis if kpi.label == label),
        0.0,
    )


def _comparison_values(dataset: SyntheticDataset) -> dict:
    average_ed_wait = (
        sum(patient.wait_minutes for patient in dataset.ed) / len(dataset.ed)
        if dataset.ed
        else 0.0
    )
    return {
        "ed_wait": round(average_ed_wait, 1),
        "bed_pressure": _kpi_value(dataset, "bed_pressure_risk"),
        "dtoc": _kpi_value(dataset, "dtoc_count"),
        "los": _kpi_value(dataset, "average_length_of_stay"),
        "staffing_pressure": _kpi_value(
            dataset,
            "staffing_pressure_risk",
        ),
        "flow_score_v3": dataset.flow_score_v3.overall_flow_score,
        "operational_risk": float(
            dataset.sol_ready.operational_risk.overall_risk_score
        ),
    }


def calculate_scenario_delta(
    baseline: SyntheticDataset,
    scenario: SyntheticDataset,
) -> ScenarioDelta:
    """Return scenario-minus-baseline changes using deterministic metrics."""
    baseline_values = _comparison_values(baseline)
    scenario_values = _comparison_values(scenario)
    return ScenarioDelta(
        ed_wait_delta=round(
            scenario_values["ed_wait"] - baseline_values["ed_wait"],
            1,
        ),
        bed_pressure_delta=round(
            scenario_values["bed_pressure"]
            - baseline_values["bed_pressure"],
            3,
        ),
        dtoc_delta=round(
            scenario_values["dtoc"] - baseline_values["dtoc"],
            1,
        ),
        los_delta=round(
            scenario_values["los"] - baseline_values["los"],
            1,
        ),
        staffing_pressure_delta=round(
            scenario_values["staffing_pressure"]
            - baseline_values["staffing_pressure"],
            3,
        ),
        flow_score_v3_delta=round(
            scenario_values["flow_score_v3"]
            - baseline_values["flow_score_v3"],
            1,
        ),
        operational_risk_delta=round(
            scenario_values["operational_risk"]
            - baseline_values["operational_risk"],
            1,
        ),
    )


def _top_delta_items(
    baseline: SyntheticDataset,
    scenario: SyntheticDataset,
    delta: ScenarioDelta,
) -> List[DeltaItem]:
    baseline_values = _comparison_values(baseline)
    scenario_values = _comparison_values(scenario)
    metric_definitions = (
        ("ed_wait_delta", "ED wait minutes", "ed_wait", 300.0),
        ("bed_pressure_delta", "Bed pressure", "bed_pressure", 1.0),
        ("dtoc_delta", "DTOC count", "dtoc", 25.0),
        ("los_delta", "Average LOS days", "los", 14.0),
        (
            "staffing_pressure_delta",
            "Staffing pressure",
            "staffing_pressure",
            1.0,
        ),
        (
            "flow_score_v3_delta",
            "Flow Score v3",
            "flow_score_v3",
            100.0,
        ),
        (
            "operational_risk_delta",
            "Operational risk",
            "operational_risk",
            100.0,
        ),
    )
    ranked_metrics = sorted(
        metric_definitions,
        key=lambda definition: -abs(
            getattr(delta, definition[0]) / definition[3]
        ),
    )[:5]
    return [
        DeltaItem(
            metric=label,
            baseline=float(baseline_values[value_key]),
            scenario=float(scenario_values[value_key]),
            delta=float(getattr(delta, delta_field)),
        )
        for delta_field, label, value_key, _ in ranked_metrics
    ]


def _signed(value: float, digits: int = 1) -> str:
    return f"{value:+.{digits}f}"


def _build_judge_briefing_v2(
    baseline: SyntheticDataset,
    scenario: SyntheticDataset,
    delta: ScenarioDelta,
) -> JudgeBriefingV2:
    context = scenario.sol_ready.scenario_context
    scenario_description = context.scenario_description.rstrip(".")
    if scenario.scenario_name == "baseline":
        comparison_sentence = (
            "The baseline comparison shows no scenario-driven operational "
            "change."
        )
    else:
        comparison_sentence = (
            "Compared with baseline, average ED wait changed by "
            f"{_signed(delta.ed_wait_delta)} minutes, DTOC changed by "
            f"{_signed(delta.dtoc_delta)} patients, and average LOS changed "
            f"by {_signed(delta.los_delta)} days."
        )
    return JudgeBriefingV2(
        headline=(
            f"{SCENARIO_LABEL[scenario.scenario_name]} records operational "
            f"risk {_signed(delta.operational_risk_delta)} points and Flow "
            f"Score v3 {_signed(delta.flow_score_v3_delta)} points versus "
            "baseline."
        ),
        scenario_summary=(
            f"{scenario_description}. {comparison_sentence}"
        ),
        key_deltas=_top_delta_items(baseline, scenario, delta),
        priority_actions=scenario.sol_ready.prioritized_actions[:3],
        flow_summary=(
            f"Flow Score v3 is "
            f"{scenario.flow_score_v3.overall_flow_score:.1f}/100, a "
            f"{_signed(delta.flow_score_v3_delta)} point change versus "
            "baseline."
        ),
        risk_summary=(
            "Operational risk is "
            f"{scenario.sol_ready.operational_risk.overall_risk_score}/100, "
            f"a {_signed(delta.operational_risk_delta)} point change versus "
            "baseline."
        ),
    )


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
        "flow_score_v2",
        "narrative",
        "flow_score_v3",
        "judge_mode",
        "executive_summary",
        "judge_briefing_v2",
    }
    flow_v2_values = (
        dataset.flow_score_v2.ed_flow,
        dataset.flow_score_v2.inpatient_flow,
        dataset.flow_score_v2.discharge_flow,
        dataset.flow_score_v2.overall_flow_score,
    )
    flow_v3_values = (
        dataset.flow_score_v3.ed_flow,
        dataset.flow_score_v3.inpatient_flow,
        dataset.flow_score_v3.discharge_flow,
        dataset.flow_score_v3.staffing_flow,
        dataset.flow_score_v3.overall_flow_score,
    )
    flow_values = flow_v2_values + flow_v3_values
    narrative_values = dataset.narrative.dict().values()
    prioritized_actions = dataset.sol_ready.prioritized_actions
    recommended_actions = dataset.sol_ready.recommended_actions
    priority_rank = {"high": 0, "medium": 1, "low": 2}
    priority_order = [
        priority_rank[action.priority] for action in prioritized_actions
    ]
    judge_mode = dataset.judge_mode
    judge_briefing_v2 = dataset.judge_briefing_v2
    executive_sentence_count = dataset.executive_summary.count(". ") + int(
        dataset.executive_summary.endswith(".")
    )
    briefing_headline_sentences = (
        judge_briefing_v2.headline.count(". ")
        + int(judge_briefing_v2.headline.endswith("."))
    )
    scenario_summary_sentences = (
        judge_briefing_v2.scenario_summary.count(". ")
        + int(judge_briefing_v2.scenario_summary.endswith("."))
    )
    flow_summary_sentences = (
        judge_briefing_v2.flow_summary.count(". ")
        + int(judge_briefing_v2.flow_summary.endswith("."))
    )
    risk_summary_sentences = (
        judge_briefing_v2.risk_summary.count(". ")
        + int(judge_briefing_v2.risk_summary.endswith("."))
    )
    delta_metrics = [
        delta_item.metric for delta_item in judge_briefing_v2.key_deltas
    ]
    json_structure_ok = (
        required_top_level <= set(payload)
        and dataset.engine_version == ENGINE_VERSION
        and len(dataset.checksum) == 64
        and 3 <= len(recommended_actions) <= 7
        and len(recommended_actions) == len(set(recommended_actions))
        and len(prioritized_actions) == len(recommended_actions)
        and [action.action for action in prioritized_actions]
        == recommended_actions
        and priority_order == sorted(priority_order)
        and len(judge_mode.key_risks) in {3, 4, 5}
        and len(judge_mode.key_actions) == 3
        and judge_mode.key_actions == prioritized_actions[:3]
        and bool(judge_mode.headline)
        and bool(judge_mode.flow_summary)
        and 2 <= executive_sentence_count <= 4
        and briefing_headline_sentences == 1
        and 2 <= scenario_summary_sentences <= 3
        and len(judge_briefing_v2.key_deltas) == 5
        and len(delta_metrics) == len(set(delta_metrics))
        and len(judge_briefing_v2.priority_actions) == 3
        and judge_briefing_v2.priority_actions
        == prioritized_actions[:3]
        and flow_summary_sentences == 1
        and 1 <= risk_summary_sentences <= 2
        and all(
            isinstance(delta_item.delta, (int, float))
            for delta_item in judge_briefing_v2.key_deltas
        )
        and all(0.0 <= value <= 100.0 for value in flow_values)
        and all(bool(value) for value in narrative_values)
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
        and all(0.0 <= value <= 100.0 for value in flow_values)
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
        and len(judge_mode.key_actions) == 3
        and len(judge_mode.key_risks) in {3, 4, 5}
        and len(judge_briefing_v2.key_deltas) == 5
        and len(judge_briefing_v2.priority_actions) == 3
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
        and all(isinstance(action, str) for action in recommended_actions)
        and len(flow_v2_values) == 4
        and bool(dataset.judge_briefing_v2.headline)
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
    baseline_reference: Optional[SyntheticDataset] = None,
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

    ed_delays_over_4h = sum(
        patient.wait_minutes > 240 for patient in ed
    )
    patients_delayed_over_4h = ed_delays_over_4h + sum(
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

    flow_score_v2 = _calculate_flow_score_v2(
        ed_overcrowding_risk=ed_risk,
        ed_wait_risk=ed_wait_risk,
        boarded_count=patients_boarded_in_ed,
        ed_count=len(ed),
        bed_pressure_risk=bed_risk,
        average_los=average_los,
        long_stay_count=long_stay_count,
        inpatient_count=inpatient_count,
        dtoc_count=dtoc_count,
        discharge_opportunities=discharge_opportunities,
    )
    flow_score_v3 = _calculate_flow_score_v3(
        ed=ed,
        ed_overcrowding_risk=ed_risk,
        boarded_count=patients_boarded_in_ed,
        bed_pressure_risk=bed_risk,
        inpatients=inpatients,
        long_stay_count=long_stay_count,
        dtoc_count=dtoc_count,
        discharge_opportunities=discharge_opportunities,
        staffing_pressure_risk=staffing_pressure_risk,
    )

    if sol_overall_risk_score < 40:
        clinical_risk_level = "low"
    elif sol_overall_risk_score < 70:
        clinical_risk_level = "medium"
    else:
        clinical_risk_level = "high"

    recommended_actions, prioritized_actions = _recommended_actions(
        scenario_name=scenario_name,
        ed_wait_risk=ed_wait_risk,
        max_ed_wait_minutes=max(
            (patient.wait_minutes for patient in ed),
            default=0,
        ),
        boarded_count=patients_boarded_in_ed,
        bed_pressure_risk=bed_risk,
        cleaning_bed_count=sum(
            bed.type == "cleaning" for bed in operational_beds
        ),
        dtoc_count=dtoc_count,
        long_stay_count=long_stay_count,
        staffing_pressure_risk=staffing_pressure_risk,
        discharge_opportunities=discharge_opportunities,
    )
    narrative = _operational_narrative(
        scenario_name=scenario_name,
        scenario_pressure_level=scenario_metadata["pressure_level"],
        flow_score_v2=flow_score_v2,
        ed_count=len(ed),
        ed_risk_score=sol_ed_risk_score,
        ed_delays_over_4h=ed_delays_over_4h,
        boarded_count=patients_boarded_in_ed,
        occupied_bed_count=len(occupied_beds),
        operational_capacity=operational_capacity,
        bed_risk_score=sol_bed_risk_score,
        long_stay_count=long_stay_count,
        dtoc_count=dtoc_count,
        discharge_opportunities=discharge_opportunities,
        overall_risk_score=sol_overall_risk_score,
        staffing_risk_score=sol_staffing_risk_score,
        clinical_risk_level=clinical_risk_level,
    )
    judge_mode, executive_summary = _judge_mode_and_executive_summary(
        scenario_name=scenario_name,
        scenario_pressure_level=scenario_metadata["pressure_level"],
        flow_score_v3=flow_score_v3,
        prioritized_actions=prioritized_actions,
        overall_risk_score=sol_overall_risk_score,
        ed_risk_score=sol_ed_risk_score,
        bed_risk_score=sol_bed_risk_score,
        dtoc_risk_score=sol_dtoc_risk_score,
        los_risk_score=sol_los_risk_score,
        staffing_risk_score=sol_staffing_risk_score,
        patients_delayed_over_4h=patients_delayed_over_4h,
        patients_boarded_in_ed=patients_boarded_in_ed,
        total_delayed_bed_hours=human_impact.delayed_bed_hours,
        total_delayed_discharge_hours=(
            human_impact.delayed_discharge_hours
        ),
        dtoc_count=dtoc_count,
        long_stay_count=long_stay_count,
    )

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
        recommended_actions=recommended_actions,
        prioritized_actions=prioritized_actions,
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
        flow_score_v2=flow_score_v2,
        narrative=narrative,
        flow_score_v3=flow_score_v3,
        judge_mode=judge_mode,
        executive_summary=executive_summary,
    )
    dataset.checksum = _dataset_checksum(dataset)
    if scenario_name == "baseline":
        comparison_baseline = dataset
    else:
        comparison_baseline = baseline_reference or generate_synthetic_hospital(
            scenario="baseline",
            seed=seed,
            as_of=reference_time,
        )
    scenario_delta = calculate_scenario_delta(comparison_baseline, dataset)
    dataset.judge_briefing_v2 = _build_judge_briefing_v2(
        comparison_baseline,
        dataset,
        scenario_delta,
    )
    dataset.validation = _validate_dataset(dataset, params)
    _LAST_GENERATED = dataset.as_of
    return dataset


def generate_scenario_overlay(
    scenario: SimulationScenario,
    seed: int = 42,
    as_of: Optional[datetime] = None,
) -> ScenarioOverlayResponse:
    """Generate baseline and scenario datasets on one comparison clock."""
    reference_time = as_of or datetime.utcnow()
    baseline = generate_synthetic_hospital(
        scenario="baseline",
        seed=seed,
        as_of=reference_time,
    )
    if scenario == "baseline":
        scenario_dataset = baseline
    else:
        scenario_dataset = generate_synthetic_hospital(
            scenario=scenario,
            seed=seed,
            as_of=reference_time,
            baseline_reference=baseline,
        )
    delta = calculate_scenario_delta(baseline, scenario_dataset)
    return ScenarioOverlayResponse(
        as_of=baseline.as_of,
        baseline=baseline,
        scenario=scenario_dataset,
        delta=delta,
    )


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
        flow_score_v2=synthetic.flow_score_v2,
        narrative=synthetic.narrative,
        flow_score_v3=synthetic.flow_score_v3,
        judge_mode=synthetic.judge_mode,
        executive_summary=synthetic.executive_summary,
        judge_briefing_v2=synthetic.judge_briefing_v2,
    )
