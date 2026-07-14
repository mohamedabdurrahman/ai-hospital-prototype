from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd

sys.path.append(str(Path(__file__).resolve().parent.parent))

from models.los_model import train_los_model
from models.discharge_model import train_discharge_model
from models.ed_forecast_model import train_ed_forecast_model
from models.bed_forecast_model import train_bed_forecast_model

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT


def prepare_training_data() -> dict[str, pd.DataFrame]:
    patients = pd.read_csv(DATA_DIR / "patients.csv")
    admissions = pd.read_csv(DATA_DIR / "admissions.csv")
    ed_visits = pd.read_csv(DATA_DIR / "ed_visits.csv")
    daily_kpis = pd.read_csv(DATA_DIR / "daily_kpis.csv")

    admissions = admissions.merge(patients[["patient_id", "age", "frailty_score", "primary_diagnosis"]], on="patient_id", how="left")
    admissions["los_days"] = admissions["los_days"].astype(float)
    admissions["discharge_within_24h"] = 0
    admissions.loc[admissions["los_days"] <= 2, "discharge_within_24h"] = 1

    los_train_df = admissions[["age", "frailty_score", "primary_diagnosis", "los_days"]].copy()
    los_train_df["is_older_adult"] = los_train_df["age"].ge(75).astype(int)

    discharge_train_df = admissions[["age", "frailty_score", "primary_diagnosis", "los_days", "discharge_within_24h"]].copy()
    discharge_train_df.rename(columns={"los_days": "length_of_stay_so_far"}, inplace=True)

    ed_features = []
    for hour in range(24):
        for day in range(7):
            subset = ed_visits[(ed_visits["arrival_hour"] == hour)]
            if subset.empty:
                continue
            ed_features.append(
                {
                    "hour": hour,
                    "day_of_week": day,
                    "rolling_6h_avg": float(len(subset)) / max(1, len(subset)),
                    "arrivals_next_6h": float(len(subset)),
                }
            )

    ed_train_df = pd.DataFrame(ed_features)
    ed_train_df = ed_train_df.fillna(0)

    bed_train_df = []
    for _, row in daily_kpis.iterrows():
        bed_train_df.append(
            {
                "current_occupancy": int(row["trolley_count_8am"] + row["dtoc_count"]),
                "predicted_discharges": int(row["dtoc_count"]),
                "available_beds_next_24h": max(0, 20 - int(row["trolley_count_8am"] + row["dtoc_count"])),
            }
        )

    bed_train_df = pd.DataFrame(bed_train_df)

    return {
        "los": los_train_df,
        "discharge": discharge_train_df,
        "ed": ed_train_df,
        "beds": bed_train_df,
    }


def run_training() -> None:
    dataframes = prepare_training_data()
    train_los_model(dataframes["los"])
    train_discharge_model(dataframes["discharge"])
    train_ed_forecast_model(dataframes["ed"])
    train_bed_forecast_model(dataframes["beds"])
    print("Training completed successfully.")


if __name__ == "__main__":
    run_training()
