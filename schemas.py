from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass
class Patient:
    patient_id: str
    age: int
    sex: str
    frailty_score: float
    comorbidity_count: int
    primary_diagnosis: str
    risk_group: str


@dataclass
class EDVisit:
    visit_id: str
    patient_id: str
    arrival_datetime: datetime
    arrival_hour: int
    triage_category: str
    chief_complaint: str
    admitted: bool


@dataclass
class Ward:
    ward_id: str
    name: str
    specialty: str
    bed_count: int


@dataclass
class Bed:
    bed_id: str
    ward_id: str
    bed_type: str
    is_occupied: bool = False


@dataclass
class Admission:
    admission_id: str
    patient_id: str
    visit_id: str
    ward_id: str
    bed_id: str
    admission_date: datetime
    expected_discharge_date: datetime
    los_days: int
    discharge_status: str


@dataclass
class DischargePlan:
    discharge_plan_id: str
    admission_id: str
    patient_id: str
    discharge_ready_date: datetime
    destination: str
    dtoc_reason: str | None
    dtoc_days: int
    home_support_required: bool
    nhss_placement_required: bool


@dataclass
class DailyKPI:
    date: datetime
    ward_id: str
    trolley_count_8am: int
    dtoc_count: int
    pet_24hr: int
    los_gt_14_days: int
