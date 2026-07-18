from pydantic import BaseModel
from typing import List, Optional

class KPI(BaseModel):
    label: str
    value: float
    unit: Optional[str] = ""

class EDPatient(BaseModel):
    patient_id: str
    triage_category: str
    on_trolley: bool
    wait_minutes: int
    awaiting_bed: bool

class Bed(BaseModel):
    bed_id: str
    ward_name: str
    specialty: str
    occupied: bool
    type: str  # "occupied", "free", "cleaning", "closed"

class Inpatient(BaseModel):
    patient_id: str
    age: int
    frailty_score: int
    diagnosis: str
    ward: str
    predicted_discharge_date: str
    length_of_stay: int
    discharge_ready: bool
    dtoc: bool

class ForecastPoint(BaseModel):
    time: str
    arrivals: Optional[int] = None
    beds: Optional[float] = None

class SyntheticDataset(BaseModel):
    kpis: List[KPI]
    ed: List[EDPatient]
    beds: List[Bed]
    inpatients: List[Inpatient]
    edForecast: List[ForecastPoint]
    bedForecast: List[ForecastPoint]
