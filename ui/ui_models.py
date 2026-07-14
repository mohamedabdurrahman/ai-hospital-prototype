from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class BedStatusUI(BaseModel):
    bed_id: str
    ward_id: str
    ward_name: str | None = None
    specialty: str | None = None
    occupied: bool


class EDStatusUI(BaseModel):
    visit_id: str
    patient_id: str
    arrival_hour: int
    triage_category: str
    admitted: bool


class InpatientUI(BaseModel):
    admission_id: str
    patient_id: str
    age: int
    frailty_score: float
    primary_diagnosis: str
    los_days: int


class ForecastUI(BaseModel):
    label: str
    value: float
    unit: str


class KPIUI(BaseModel):
    name: str
    value: float | int
    unit: str
    trend: str | None = None


class AgentRecommendationUI(BaseModel):
    task: str
    summary: str
    priority_actions: list[str]
    explanation: str | None = None
    confidence: float | None = None
    tool_outputs: dict[str, Any] = Field(default_factory=dict)
