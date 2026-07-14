from __future__ import annotations

from datetime import datetime

START_DATE = datetime(2026, 7, 1, 0, 0)
SIMULATION_DAYS = 14

WARD_DEFINITIONS = [
    {"ward_id": "ward-med-01", "name": "General Medicine", "specialty": "general_med", "bed_count": 24},
    {"ward_id": "ward-ger-01", "name": "Geriatrics", "specialty": "geriatrics", "bed_count": 20},
    {"ward_id": "ward-surg-01", "name": "Surgery", "specialty": "surgery", "bed_count": 18},
    {"ward_id": "ward-icu-01", "name": "Intensive Care", "specialty": "icu", "bed_count": 8},
]

SYNTHETIC_DISTRIBUTIONS = {
    "age": {
        "bins": [0, 18, 35, 50, 65, 75, 85, 100],
        "weights": [0.05, 0.10, 0.15, 0.20, 0.22, 0.18, 0.10],
    },
    "frailty": {
        "base": 0.25,
        "age_bonus": 0.008,
        "noise": 0.12,
    },
    "diagnoses": {
        "general_med": ["COPD exacerbation", "Pneumonia", "Stroke", "Heart failure", "Sepsis"],
        "geriatrics": ["Falls", "Delirium", "Urinary tract infection", "Frailty syndrome", "Pressure ulcer"],
        "surgery": ["Appendicitis", "Fracture", "Cholecystitis", "Post-op complication", "Hernia"],
        "icu": ["Respiratory failure", "Septic shock", "Multi-organ dysfunction", "Cardiac arrest", "Major trauma"],
    },
    "ed_arrival_patterns": {
        "morning_peak": [6, 7, 8, 9, 10],
        "evening_peak": [17, 18, 19, 20],
        "off_peak": [0, 1, 2, 3, 4, 5, 11, 12, 13, 14, 15, 16, 21, 22, 23],
    },
    "los_distribution": {
        "weights": [0.20, 0.22, 0.18, 0.15, 0.10, 0.07, 0.05, 0.03],
        "values": [1, 2, 3, 4, 5, 7, 10, 14],
    },
    "dtoc_probability": {
        "base": 0.18,
        "age_bonus": 0.02,
        "frailty_bonus": 0.07,
    },
}

DTOC_REASONS = ["Awaiting NHSS placement", "Awaiting home support", "Awaiting social care", "Awaiting specialist assessment"]
