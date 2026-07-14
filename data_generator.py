from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from typing import List

import numpy as np
import pandas as pd

from config import (
    DTOC_REASONS,
    SIMULATION_DAYS,
    START_DATE,
    SYNTHETIC_DISTRIBUTIONS,
    WARD_DEFINITIONS,
)
from schemas import Admission, Bed, DailyKPI, DischargePlan, EDVisit, Patient, Ward


OUTPUT_DIR = Path(__file__).resolve().parent


def generate_wards() -> List[Ward]:
    return [
        Ward(
            ward_id=item["ward_id"],
            name=item["name"],
            specialty=item["specialty"],
            bed_count=item["bed_count"],
        )
        for item in WARD_DEFINITIONS
    ]


def generate_beds(wards: List[Ward]) -> List[Bed]:
    beds: List[Bed] = []
    for ward in wards:
        for index in range(1, ward.bed_count + 1):
            bed_type = "single"
            if ward.specialty == "icu":
                bed_type = "icu"
            elif ward.specialty == "geriatrics":
                bed_type = "enhanced"
            beds.append(
                Bed(
                    bed_id=f"{ward.ward_id}-bed-{index:02d}",
                    ward_id=ward.ward_id,
                    bed_type=bed_type,
                    is_occupied=False,
                )
            )
    return beds


def generate_patients(count: int = 180) -> List[Patient]:
    rng = np.random.default_rng(42)
    age_config = SYNTHETIC_DISTRIBUTIONS["age"]
    age_bins = age_config["bins"]
    age_weights = age_config["weights"]
    frailty_config = SYNTHETIC_DISTRIBUTIONS["frailty"]

    patients: List[Patient] = []
    for idx in range(1, count + 1):
        age_bin = rng.choice(len(age_bins) - 1, p=age_weights)
        age_low = age_bins[age_bin]
        age_high = age_bins[age_bin + 1]
        age = int(rng.integers(age_low, age_high + 1)) if age_high < 100 else age_low + 10

        age_bonus = max(0, age - 60) * frailty_config["age_bonus"]
        frailty_score = min(1.0, max(0.0, frailty_config["base"] + age_bonus + rng.normal(0, frailty_config["noise"])))
        frailty_score = round(float(frailty_score), 2)

        if age >= 75:
            risk_group = "older_adult"
        elif age >= 65:
            risk_group = "senior"
        elif frailty_score >= 0.75:
            risk_group = "frail"
        else:
            risk_group = "standard"

        if age >= 75 and frailty_score >= 0.7:
            diagnosis_pool = ["Falls", "Frailty syndrome", "Delirium", "Pneumonia"]
        else:
            diagnosis_pool = ["Chest pain", "Asthma", "DVT", "Bowel obstruction", "COPD exacerbation"]

        diagnosis = rng.choice(diagnosis_pool)
        sex = rng.choice(["F", "M"])
        comorbidity_count = int(rng.poisson(1.4 + 0.03 * max(0, age - 50)))

        patients.append(
            Patient(
                patient_id=f"P-{idx:05d}",
                age=age,
                sex=sex,
                frailty_score=frailty_score,
                comorbidity_count=comorbidity_count,
                primary_diagnosis=diagnosis,
                risk_group=risk_group,
            )
        )
    return patients


def simulate_ed_visits(patients: List[Patient], days: int = SIMULATION_DAYS) -> List[EDVisit]:
    rng = np.random.default_rng(123)
    arrival_config = SYNTHETIC_DISTRIBUTIONS["ed_arrival_patterns"]
    visits: List[EDVisit] = []
    for idx, patient in enumerate(patients, start=1):
        day_offset = int(rng.integers(0, days))
        arrival_date = START_DATE + timedelta(days=day_offset)
        hour_options = arrival_config["morning_peak"] + arrival_config["evening_peak"] + arrival_config["off_peak"]
        weights = [0.22, 0.22, 0.18, 0.18, 0.20] + [0.10, 0.12, 0.12, 0.10] + [0.02] * len(arrival_config["off_peak"])
        arrival_hour = int(rng.choice(hour_options, p=np.array(weights) / np.sum(weights)))
        arrival_datetime = datetime(arrival_date.year, arrival_date.month, arrival_date.day, arrival_hour, 0)

        if patient.age >= 75 and patient.frailty_score >= 0.7:
            triage_category = "Red" if rng.random() < 0.15 else "Amber"
        elif patient.age >= 65:
            triage_category = "Amber"
        else:
            triage_category = "Green"

        admitted = bool(rng.random() < (0.35 + 0.02 * max(0, patient.age - 60) + 0.05 * patient.frailty_score))
        chief_complaint = patient.primary_diagnosis
        visits.append(
            EDVisit(
                visit_id=f"EV-{idx:05d}",
                patient_id=patient.patient_id,
                arrival_datetime=arrival_datetime,
                arrival_hour=arrival_hour,
                triage_category=triage_category,
                chief_complaint=chief_complaint,
                admitted=admitted,
            )
        )
    return visits


def simulate_admissions(patients: List[Patient], visits: List[EDVisit], wards: List[Ward], beds: List[Bed]) -> List[Admission]:
    rng = np.random.default_rng(321)
    los_config = SYNTHETIC_DISTRIBUTIONS["los_distribution"]
    ward_lookup = {ward.ward_id: ward for ward in wards}
    available_beds = [bed for bed in beds if bed.ward_id in ward_lookup]

    admissions: List[Admission] = []
    bed_index = 0
    for visit in visits:
        if not visit.admitted:
            continue
        patient = next(patient for patient in patients if patient.patient_id == visit.patient_id)
        ward = None
        if patient.age >= 75 or patient.frailty_score >= 0.75:
            ward = ward_lookup["ward-ger-01"]
        elif patient.primary_diagnosis in ["Appendicitis", "Fracture", "Cholecystitis", "Hernia"]:
            ward = ward_lookup["ward-surg-01"]
        elif patient.primary_diagnosis in ["Respiratory failure", "Septic shock", "Multi-organ dysfunction", "Cardiac arrest"]:
            ward = ward_lookup["ward-icu-01"]
        else:
            ward = ward_lookup["ward-med-01"]

        los_days = int(rng.choice(los_config["values"], p=np.array(los_config["weights"]) / np.sum(los_config["weights"])))
        if patient.age >= 80 and rng.random() < 0.25:
            los_days += 7

        admission_date = visit.arrival_datetime
        expected_discharge_date = admission_date + timedelta(days=los_days)
        bed = available_beds[bed_index % len(available_beds)]
        bed_index += 1
        bed.ward_id = ward.ward_id

        admissions.append(
            Admission(
                admission_id=f"ADM-{len(admissions) + 1:05d}",
                patient_id=visit.patient_id,
                visit_id=visit.visit_id,
                ward_id=ward.ward_id,
                bed_id=bed.bed_id,
                admission_date=admission_date,
                expected_discharge_date=expected_discharge_date,
                los_days=los_days,
                discharge_status="active",
            )
        )
    return admissions


def simulate_dtoc(admissions: List[Admission], patients: List[Patient]) -> List[DischargePlan]:
    rng = np.random.default_rng(555)
    dtoc_config = SYNTHETIC_DISTRIBUTIONS["dtoc_probability"]
    plans: List[DischargePlan] = []
    for admission in admissions:
        patient = next(item for item in patients if item.patient_id == admission.patient_id)
        probability = dtoc_config["base"] + dtoc_config["age_bonus"] * max(0, patient.age - 70) / 10 + dtoc_config["frailty_bonus"] * patient.frailty_score
        dtoc = rng.random() < probability
        if dtoc:
            reason = rng.choice(DTOC_REASONS)
            dtoc_days = int(rng.integers(1, 5))
            discharge_ready_date = admission.expected_discharge_date + timedelta(days=dtoc_days)
            plans.append(
                DischargePlan(
                    discharge_plan_id=f"DP-{len(plans) + 1:05d}",
                    admission_id=admission.admission_id,
                    patient_id=admission.patient_id,
                    discharge_ready_date=discharge_ready_date,
                    destination="Home" if reason != "Awaiting NHSS placement" else "NHSS placement",
                    dtoc_reason=reason,
                    dtoc_days=dtoc_days,
                    home_support_required="home support" in reason.lower(),
                    nhss_placement_required="nhss" in reason.lower(),
                )
            )
    return plans


def compute_daily_kpis(admissions: List[Admission], visits: List[EDVisit], discharge_plans: List[DischargePlan], wards: List[Ward]) -> List[DailyKPI]:
    kpis: List[DailyKPI] = []
    for ward in wards:
        for day_offset in range(SIMULATION_DAYS):
            date = START_DATE + timedelta(days=day_offset)
            ward_admissions = [admission for admission in admissions if admission.ward_id == ward.ward_id]
            ward_visits = [visit for visit in visits if visit.arrival_datetime.date() == date.date()]
            ward_discharge_plans = [plan for plan in discharge_plans if plan.admission_id in {admission.admission_id for admission in ward_admissions}]

            trolley_count_8am = max(1, len(ward_visits) // 4 + len([a for a in ward_admissions if a.admission_date.date() == date.date()]))
            dtoc_count = sum(1 for plan in ward_discharge_plans if plan.dtoc_days > 0 and plan.discharge_ready_date.date() >= date.date())
            pet_24hr = sum(
                1
                for admission in ward_admissions
                if (admission.admission_date - next(visit for visit in visits if visit.visit_id == admission.visit_id).arrival_datetime).total_seconds() / 3600 > 24
                and admission.admission_date.date() == date.date()
            )
            los_gt_14_days = sum(1 for admission in ward_admissions if admission.los_days > 14 and admission.admission_date.date() <= date.date() < admission.expected_discharge_date.date())

            kpis.append(
                DailyKPI(
                    date=date,
                    ward_id=ward.ward_id,
                    trolley_count_8am=trolley_count_8am,
                    dtoc_count=dtoc_count,
                    pet_24hr=pet_24hr,
                    los_gt_14_days=los_gt_14_days,
                )
            )
    return kpis


def _to_dataframe(rows: List[object], schema: type) -> pd.DataFrame:
    return pd.DataFrame([row.__dict__ for row in rows])


def main() -> None:
    wards = generate_wards()
    beds = generate_beds(wards)
    patients = generate_patients(180)
    visits = simulate_ed_visits(patients)
    admissions = simulate_admissions(patients, visits, wards, beds)
    discharge_plans = simulate_dtoc(admissions, patients)
    daily_kpis = compute_daily_kpis(admissions, visits, discharge_plans, wards)

    outputs = {
        "wards.csv": _to_dataframe(wards, Ward),
        "beds.csv": _to_dataframe(beds, Bed),
        "patients.csv": _to_dataframe(patients, Patient),
        "ed_visits.csv": _to_dataframe(visits, EDVisit),
        "admissions.csv": _to_dataframe(admissions, Admission),
        "discharge_plans.csv": _to_dataframe(discharge_plans, DischargePlan),
        "daily_kpis.csv": _to_dataframe(daily_kpis, DailyKPI),
    }

    for filename, dataframe in outputs.items():
        dataframe.to_csv(OUTPUT_DIR / filename, index=False)

    print("Synthetic hospital data generated successfully.")
    print(f"Files written to {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
