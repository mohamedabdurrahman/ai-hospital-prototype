from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
from fastapi import APIRouter

router = APIRouter(tags=["hospital-state"])

ROOT = Path(__file__).resolve().parent.parent.parent


@router.get("/inpatients")
def get_inpatients() -> dict[str, Any]:
    admissions = pd.read_csv(ROOT / "admissions.csv")
    patients = pd.read_csv(ROOT / "patients.csv")
    merged = admissions.merge(patients[["patient_id", "age", "frailty_score", "primary_diagnosis"]], on="patient_id", how="left")
    return {"count": int(len(merged)), "items": merged.to_dict(orient="records")}


@router.get("/ed")
def get_ed_patients() -> dict[str, Any]:
    ed_visits = pd.read_csv(ROOT / "ed_visits.csv")
    return {"count": int(len(ed_visits)), "items": ed_visits.to_dict(orient="records")}


@router.get("/beds")
def get_bed_status() -> dict[str, Any]:
    beds = pd.read_csv(ROOT / "beds.csv")
    wards = pd.read_csv(ROOT / "wards.csv")
    merged = beds.merge(wards[["ward_id", "name", "specialty"]], on="ward_id", how="left")
    occupied = int((merged["is_occupied"] == True).sum())
    return {"count": int(len(merged)), "occupied": occupied, "items": merged.to_dict(orient="records")}
