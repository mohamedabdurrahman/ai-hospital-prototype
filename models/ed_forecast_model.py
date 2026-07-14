from __future__ import annotations

from pathlib import Path

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestRegressor

MODEL_PATH = Path(__file__).resolve().parent / "ed_forecast_model.pkl"


def build_ed_forecast_model(train_df: pd.DataFrame) -> RandomForestRegressor:
    X = train_df[["hour", "day_of_week", "rolling_6h_avg"]]
    y = train_df["arrivals_next_6h"]
    model = RandomForestRegressor(n_estimators=150, random_state=42)
    model.fit(X, y)
    return model


def train_ed_forecast_model(train_df: pd.DataFrame) -> RandomForestRegressor:
    model = build_ed_forecast_model(train_df)
    joblib.dump(model, MODEL_PATH)
    return model


def load_ed_forecast_model() -> RandomForestRegressor:
    return joblib.load(MODEL_PATH)


def predict_ed_forecast(model: RandomForestRegressor, row: pd.Series) -> float:
    feature_df = pd.DataFrame([row])
    return float(model.predict(feature_df[["hour", "day_of_week", "rolling_6h_avg"]])[0])
