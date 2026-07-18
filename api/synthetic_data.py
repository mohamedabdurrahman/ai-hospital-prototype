# synthetic_data.py

from typing import List, Literal, Optional
from datetime import datetime, timedelta
import math

from .models import (
    KPI,
    EDPatient,
    Bed,
    Inpatient,
    ForecastPoint,
    SyntheticDataset,
)

SimulationScenario = Literal[
    "baseline",
    "ed_surge",
    "flu_season",
    "ward_closure",
    "staff_shortage",
]

SCENARIO_LABEL = {
    "baseline": "Baseline",
    "ed_surge": "ED Surge",
    "flu_season": "Flu Season",
    "ward_closure": "Ward Closure",
    "staff_shortage": "Staff Shortage",
}

# Simple seedable PRNG (mulberry32-like)
def rng(seed: int):
    t = seed & 0xFFFFFFFF

    def _next() -> float:
        nonlocal t
        t = (t + 0x6D2B79F5) & 0xFFFFFFFF
        x = t
        x = (x ^ (x >> 15)) * (x | 1)
        x ^= x + ((x ^ (x >> 7)) * (x | 61))
        x = x ^ (x >> 14)
        return (x & 0xFFFFFFFF) / 4294967296.0

    return _next


WARDS = [
    {"name": "St Brigid — General Medicine A", "specialty": "General Medicine", "beds": 60},
    {"name": "St Brigid — General Medicine B", "specialty": "General Medicine", "beds": 60},
    {"name": "St Colmcille — Geriatrics A", "specialty": "Geriatrics", "beds": 40},
    {"name": "St Colmcille — Geriatrics B", "specialty": "Geriatrics", "beds": 40},
    {"name": "St Patrick — Surgical A", "specialty": "Surgical", "beds": 45},
    {"name": "St Patrick — Surgical B", "specialty": "Surgical", "beds": 45},
    {"name": "ICU", "specialty": "ICU", "beds": 20},
    {"name": "Short Stay Unit", "specialty": "Short Stay", "beds": 30},
]

DIAGNOSES = [
    "Community-acquired pneumonia", "COPD exacerbation", "Heart failure",
    "UTI / sepsis", "Fall — fractured NOF", "Stroke — TIA",
    "Cellulitis", "Acute kidney injury", "Post-op recovery",
    "Chest pain — NSTEMI", "Delirium", "Diabetes decompensation",
]


def scenario_params(scenario: SimulationScenario):
    if scenario == "ed_surge":
        return {"edMul": 1.6, "trolleyMul": 1.8, "occTarget": 0.94, "losMul": 1.0, "cleaningMul": 1.0, "closedWards": 0, "dtocMul": 1.0}
    if scenario == "flu_season":
        return {"edMul": 1.35, "trolleyMul": 1.3, "occTarget": 0.97, "losMul": 1.35, "cleaningMul": 1.1, "closedWards": 0, "dtocMul": 1.2}
    if scenario == "ward_closure":
        return {"edMul": 1.0, "trolleyMul": 1.2, "occTarget": 0.98, "losMul": 1.05, "cleaningMul": 1.0, "closedWards": 1, "dtocMul": 1.0}
    if scenario == "staff_shortage":
        return {"edMul": 1.05, "trolleyMul": 1.15, "occTarget": 0.95, "losMul": 1.15, "cleaningMul": 2.2, "closedWards": 0, "dtocMul": 1.4}
    return {"edMul": 1.0, "trolleyMul": 1.0, "occTarget": 0.9, "losMul": 1.0, "cleaningMul": 1.0, "closedWards": 0, "dtocMul": 1.0}


def pick_triage(r) -> str:
    v = r()
    if v < 0.07:
        return "Red"
    if v < 0.32:
        return "Orange"
    if v < 0.68:
        return "Yellow"
    if v < 0.92:
        return "Green"
    return "Blue"


def generate_synthetic_hospital(
    scenario: SimulationScenario = "baseline",
    seed: int = 42,
) -> SyntheticDataset:
    r = rng(seed + len(scenario) * 7919)
    p = scenario_params(scenario)

    # Beds
    beds: List[Bed] = []
    active_wards = WARDS[: len(WARDS) - p["closedWards"]]
    closed_wards = WARDS[len(WARDS) - p["closedWards"] :]

    for w in active_wards:
        for i in range(w["beds"]):
            occ_prob = min(0.99, p["occTarget"] + (r() - 0.5) * 0.1)
            roll = r()
            cleaning = roll < 0.03 * p["cleaningMul"]
            occupied = (not cleaning) and (roll < occ_prob)
            beds.append(
                Bed(
                    bed_id=f"{w['specialty'][:3].upper()}-{i+1}",
                    ward_name=w["name"],
                    specialty=w["specialty"],
                    occupied=occupied,
                    type="cleaning" if cleaning else ("occupied" if occupied else "free"),
                )
            )

    for w in closed_wards:
        for i in range(w["beds"]):
            beds.append(
                Bed(
                    bed_id=f"{w['specialty'][:3].upper()}-C{i+1}",
                    ward_name=f"{w['name']} (CLOSED)",
                    specialty=w["specialty"],
                    occupied=True,
                    type="closed",
                )
            )

    # ED
    base_ed = 45 + int(r() * 25)
    ed_count = round(base_ed * p["edMul"])
    trolley_base = 12 + int(r() * 18)
    trolley_count = min(ed_count, round(trolley_base * p["trolleyMul"]))
    ed: List[EDPatient] = []

    for i in range(ed_count):
        cat = pick_triage(r)
        if cat == "Red":
            wait_base = 15
        elif cat == "Orange":
            wait_base = 90
        elif cat == "Yellow":
            wait_base = 180
        else:
            wait_base = 240
        wait = round(wait_base + (r() - 0.3) * 180)
        ed.append(
            EDPatient(
                patient_id=f"ED-{1000 + i}",
                triage_category=cat,
                on_trolley=i < trolley_count,
                wait_minutes=max(0, wait),
                awaiting_bed=r() < 0.35,
            )
        )

    # Inpatients
    inpatient_count = min(
        len([b for b in beds if b.occupied and b.type != "closed"]),
        325,
    )
    inpatients: List[Inpatient] = []
    ward_names = [w["name"] for w in active_wards]

    for i in range(inpatient_count):
        los_roll = r()
        if los_roll < 0.4:
            los = 1 + int(r() * 3)
        elif los_roll < 0.7:
            los = 4 + int(r() * 4)
        elif los_roll < 0.9:
            los = 8 + int(r() * 7)
        else:
            los = 15 + int(r() * 30)
        los = round(los * p["losMul"])

        discharge_ready = r() < 0.09
        dtoc = (not discharge_ready) and (r() < 0.05 * p["dtocMul"])
        ward = ward_names[int(r() * len(ward_names))]

        predicted_date = (datetime.now() + timedelta(days=(r() * 6 + 1))).date().isoformat()

        inpatients.append(
            Inpatient(
                patient_id=f"IP-{2000 + i}",
                age=40 + int(r() * 55),
                frailty_score=round(r() * 9),
                diagnosis=DIAGNOSES[int(r() * len(DIAGNOSES))],
                ward=ward,
                predicted_discharge_date=predicted_date,
                length_of_stay=los,
                discharge_ready=discharge_ready,
                dtoc=dtoc,
            )
        )

    # Forecasts — ED next 12h
    ed_forecast: List[ForecastPoint] = []
    now = datetime.now()
    base_arr = 9 * p["edMul"]

    for h in range(12):
        hour = (now.hour + h) % 24
        peak = 1.6 if ((10 <= hour <= 12) or (18 <= hour <= 21)) else 1.0
        jitter = 0.75 + r() * 0.5
        ed_forecast.append(
            ForecastPoint(
                time=f"{hour:02d}:00",
                arrivals=round(base_arr * peak * jitter),
            )
        )

    # Beds next 48h — occupancy %
    bed_forecast: List[ForecastPoint] = []
    total = len(beds)
    occ_now = len([b for b in beds if b.occupied]) / max(1, total)

    for h in range(0, 48, 2):
        trend = math.sin((h / 48.0) * math.pi * 2) * 0.04
        noise = (r() - 0.5) * 0.03
        occ = max(0.5, min(1.0, occ_now + trend + noise))
        bed_forecast.append(
            ForecastPoint(
                time=f"+{h}h",
                beds=round(occ * 100) / 100.0,
            )
        )

    # KPIs
    trolley_pressure = min(1.0, trolley_count / 40.0)
    ed_risk = min(1.0, 0.35 * p["edMul"] + trolley_pressure * 0.55)
    bed_risk = min(1.0, occ_now * 0.9 + (0.1 if p["closedWards"] > 0 else 0.0))
    discharge_opp = len([i for i in inpatients if i.discharge_ready])
    dtoc_count = len([i for i in inpatients if i.dtoc])
    long_stay = len([i for i in inpatients if i.length_of_stay > 14])
    avg_los = (
        sum(i.length_of_stay for i in inpatients) / len(inpatients)
        if inpatients
        else 0.0
    )
    kpi_score = max(
        0,
        min(
            100,
            round(100 - ed_risk * 40 - bed_risk * 35 - (dtoc_count / 20.0) * 25),
        ),
    )

    kpis: List[KPI] = [
        KPI(label="hospital_kpi_score", value=kpi_score, unit=""),
        KPI(label="ed_overcrowding_risk", value=round(ed_risk, 2)),
        KPI(label="bed_pressure_risk", value=round(bed_risk, 2)),
        KPI(label="discharge_opportunity_count", value=float(discharge_opp)),
        KPI(label="dtoc_count", value=float(dtoc_count)),
        KPI(label="long_stay_count", value=float(long_stay)),
        KPI(label="average_length_of_stay", value=round(avg_los, 1), unit="d"),
    ]

    return SyntheticDataset(
        kpis=kpis,
        ed=ed,
        beds=beds,
        inpatients=inpatients,
        edForecast=ed_forecast,
        bedForecast=bed_forecast,
    )


def overlay_synthetic(
    live: Optional[SyntheticDataset],
    scenario: SimulationScenario,
) -> SyntheticDataset:
    syn = generate_synthetic_hospital(scenario)

    if live is None:
        return syn

    return SyntheticDataset(
        kpis=live.kpis if live.kpis else syn.kpis,
        ed=live.ed if live.ed else syn.ed,
        beds=live.beds if live.beds else syn.beds,
        inpatients=live.inpatients if live.inpatients else syn.inpatients,
        edForecast=live.edForecast if live.edForecast else syn.edForecast,
        bedForecast=live.bedForecast if live.bedForecast else syn.bedForecast,
    )
