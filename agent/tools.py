from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

BASE_URL = "http://127.0.0.1:8000"


def _get_json(path: str, params: dict[str, Any] | None = None) -> Any:
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(f"{BASE_URL}{path}", params=params)
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError as exc:
        logger.warning("Tool request failed for %s: %s", path, exc)
        return {"error": str(exc)}


def get_inpatients() -> dict[str, Any]:
    return _get_json("/inpatients")


def get_ed_patients() -> dict[str, Any]:
    return _get_json("/ed")


def get_bed_status() -> dict[str, Any]:
    return _get_json("/beds")


def predict_los(patient_id: str) -> dict[str, Any]:
    return _get_json("/predict/los", {"patient_id": patient_id})


def predict_discharge(admission_id: str) -> dict[str, Any]:
    return _get_json("/predict/discharge", {"admission_id": admission_id})


def forecast_ed() -> dict[str, Any]:
    return _get_json("/forecast/ed")


def forecast_beds() -> dict[str, Any]:
    return _get_json("/forecast/beds")
