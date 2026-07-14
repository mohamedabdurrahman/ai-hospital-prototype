from __future__ import annotations

from pathlib import Path

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestRegressor

MODEL_PATH = Path(__file__).resolve().parent / "bed_forecast_model.pkl"


def build_bed_forecast_model(train_df: pd.DataFrame) -> RandomForestRegressor:
    X = train_df[["current_occupancy", "predicted_discharges"]]
    y = train_df["available_beds_next_24h"]
    model = RandomForestRegressor(n_estimators=150, random_state=42)
    model.fit(X, y)
    return model


def train_bed_forecast_model(train_df: pd.DataFrame) -> RandomForestRegressor:
    model = build_bed_forecast_model(train_df)
    joblib.dump(model, MODEL_PATH)
    return model


def load_bed_forecast_model() -> RandomForestRegressor:
    return joblib.load(MODEL_PATH)


def predict_available_beds(model: RandomForestRegressor, row: pd.Series) -> float:
    feature_df = pd.DataFrame([row])
    return float(model.predict(feature_df[["current_occupancy", "predicted_discharges"]])[0])
