from __future__ import annotations

import joblib
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

from pathlib import Path

MODEL_PATH = Path(__file__).resolve().parent / "los_model.pkl"


def build_los_model(train_df: pd.DataFrame) -> Pipeline:
    feature_cols = ["age", "frailty_score", "primary_diagnosis", "is_older_adult"]
    target_col = "los_days"

    categorical_features = ["primary_diagnosis"]
    numeric_features = ["age", "frailty_score", "is_older_adult"]

    preprocessor = ColumnTransformer(
        transformers=[
            ("cat", OneHotEncoder(handle_unknown="ignore"), categorical_features),
            ("num", "passthrough", numeric_features),
        ]
    )

    model = Pipeline(
        steps=[
            ("preprocess", preprocessor),
            ("regressor", RandomForestRegressor(n_estimators=200, random_state=42)),
        ]
    )

    X = train_df[feature_cols].copy()
    X["is_older_adult"] = X["age"].ge(75).astype(int)
    y = train_df[target_col]

    model.fit(X, y)
    return model


def train_los_model(train_df: pd.DataFrame) -> Pipeline:
    model = build_los_model(train_df)
    joblib.dump(model, MODEL_PATH)
    return model


def load_los_model() -> Pipeline:
    return joblib.load(MODEL_PATH)


def predict_los(model: Pipeline, patient_row: pd.Series) -> float:
    feature_df = pd.DataFrame([patient_row])
    feature_df["is_older_adult"] = feature_df["age"].ge(75).astype(int)
    return float(model.predict(feature_df[["age", "frailty_score", "primary_diagnosis", "is_older_adult"]])[0])
