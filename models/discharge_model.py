from __future__ import annotations

from pathlib import Path

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from sklearn.compose import ColumnTransformer

MODEL_PATH = Path(__file__).resolve().parent / "discharge_model.pkl"


def build_discharge_model(train_df: pd.DataFrame) -> Pipeline:
    feature_cols = ["age", "frailty_score", "primary_diagnosis", "length_of_stay_so_far"]
    target_col = "discharge_within_24h"

    categorical_features = ["primary_diagnosis"]
    numeric_features = ["age", "frailty_score", "length_of_stay_so_far"]

    preprocessor = ColumnTransformer(
        transformers=[
            ("cat", OneHotEncoder(handle_unknown="ignore"), categorical_features),
            ("num", "passthrough", numeric_features),
        ]
    )

    model = Pipeline(
        steps=[
            ("preprocess", preprocessor),
            ("classifier", RandomForestClassifier(n_estimators=200, random_state=42)),
        ]
    )

    X = train_df[feature_cols]
    y = train_df[target_col]
    model.fit(X, y)
    return model


def train_discharge_model(train_df: pd.DataFrame) -> Pipeline:
    model = build_discharge_model(train_df)
    joblib.dump(model, MODEL_PATH)
    return model


def load_discharge_model() -> Pipeline:
    return joblib.load(MODEL_PATH)


def predict_discharge_probability(model: Pipeline, row: pd.Series) -> float:
    feature_df = pd.DataFrame([row])
    prediction = model.predict_proba(feature_df[["age", "frailty_score", "primary_diagnosis", "length_of_stay_so_far"]])[0][1]
    return float(prediction)
