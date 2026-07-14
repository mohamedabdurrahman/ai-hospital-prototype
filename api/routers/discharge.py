from __future__ import annotations

from fastapi import APIRouter, HTTPException
import pandas as pd

from models.discharge_model import load_discharge_model, predict_discharge_probability

router = APIRouter(prefix="/predict", tags=["discharge"])

@router.get("/discharge")
def predict_discharge_endpoint(admission_id: str) -> dict[str, object]:
    admissions = pd.read_csv("admissions.csv")
    patients = pd.read_csv("patients.csv")
    admission_row = admissions[admissions["admission_id"] == admission_id]
    if admission_row.empty:
        raise HTTPException(status_code=404, detail="Admission not found")

    patient_id = admission_row.iloc[0]["patient_id"]
    patient_info = patients[patients["patient_id"] == patient_id].iloc[0]
    row = {
        "age": patient_info["age"],
        "frailty_score": patient_info["frailty_score"],
        "primary_diagnosis": patient_info["primary_diagnosis"],
        "length_of_stay_so_far": admission_row.iloc[0]["los_days"],
    }

    model = load_discharge_model()
    probability = predict_discharge_probability(model, pd.Series(row))
    return {"admission_id": admission_id, "probability_of_discharge_within_24h": round(probability, 4)}
