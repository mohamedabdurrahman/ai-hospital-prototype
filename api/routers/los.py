from __future__ import annotations

from fastapi import APIRouter, HTTPException
import pandas as pd

from models.los_model import load_los_model, predict_los

router = APIRouter(prefix="/predict", tags=["los"])

@router.get("/los")
def predict_los_endpoint(patient_id: str) -> dict[str, object]:
    patients = pd.read_csv("patients.csv")
    patient_row = patients[patients["patient_id"] == patient_id]
    if patient_row.empty:
        raise HTTPException(status_code=404, detail="Patient not found")

    model = load_los_model()
    prediction = predict_los(model, patient_row.iloc[0])
    return {"patient_id": patient_id, "predicted_length_of_stay_days": round(prediction, 2)}
