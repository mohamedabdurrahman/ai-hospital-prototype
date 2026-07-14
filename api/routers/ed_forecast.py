from __future__ import annotations

from fastapi import APIRouter
import pandas as pd

from models.ed_forecast_model import load_ed_forecast_model, predict_ed_forecast

router = APIRouter(prefix="/forecast", tags=["ed"])

@router.get("/ed")
def forecast_ed_endpoint() -> dict[str, object]:
    ed = pd.read_csv("ed_visits.csv")
    row = {
        "hour": int(ed["arrival_hour"].mode().iloc[0]),
        "day_of_week": 0,
        "rolling_6h_avg": float(ed["arrival_hour"].value_counts().mean()),
    }
    model = load_ed_forecast_model()
    forecast = predict_ed_forecast(model, pd.Series(row))
    return {"forecasted_ed_arrivals_next_6h": round(forecast, 2)}
