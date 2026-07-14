from __future__ import annotations

from fastapi import APIRouter
import pandas as pd

from models.bed_forecast_model import load_bed_forecast_model, predict_available_beds

router = APIRouter(prefix="/forecast", tags=["beds"])

@router.get("/beds")
def forecast_beds_endpoint() -> dict[str, object]:
    daily_kpis = pd.read_csv("daily_kpis.csv")
    row = {
        "current_occupancy": int(daily_kpis["trolley_count_8am"].mean()),
        "predicted_discharges": int(daily_kpis["dtoc_count"].mean()),
    }
    model = load_bed_forecast_model()
    forecast = predict_available_beds(model, pd.Series(row))
    return {"predicted_available_beds_next_24h": max(0, int(round(forecast)))}
