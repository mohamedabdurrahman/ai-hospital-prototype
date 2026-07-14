from __future__ import annotations

import logging
from pathlib import Path
import sys
from typing import Any

sys.path.append(str(Path(__file__).resolve().parent.parent))

from agent.executor import BedManagementExecutor

logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")


def run_agent() -> dict[str, Any]:
    executor = BedManagementExecutor()
    context = {
        "ed_forecast": {"forecasted_ed_arrivals_next_6h": 24},
        "beds_forecast": {"predicted_available_beds_next_24h": 6},
        "dtoc_signal": "high",
        "elective_load": "medium",
        "frail_patients": 8,
        "older_adult_count": 14,
        "admission_count": 19,
        "discharge_candidates": 5,
    }
    return executor.run(context)


if __name__ == "__main__":
    result = run_agent()
    print(result)
