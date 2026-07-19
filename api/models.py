"""Pydantic models shared by the synthetic hospital API."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


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


class HumanImpactMetrics(BaseModel):
    delayed_bed_hours: float = 0.0
    delayed_discharge_hours: float = 0.0
    delayed_triage_risk: float = 0.0
    patient_flow_risk: float = 0.0


class EDArrivalProjectionPoint(BaseModel):
    time: str
    arrivals: int


class BedOccupancyProjectionPoint(BaseModel):
    time: str
    occupancy: float


class TrendPoint(BaseModel):
    time: str
    value: float


class ForecastInputs(BaseModel):
    ed_arrivals_next_24h: List[EDArrivalProjectionPoint] = Field(
        default_factory=list
    )
    bed_occupancy_next_24h: List[BedOccupancyProjectionPoint] = Field(
        default_factory=list
    )
    dtoc_trend: List[TrendPoint] = Field(default_factory=list)
    los_trend: List[TrendPoint] = Field(default_factory=list)


class SyntheticDataset(BaseModel):
    kpis: List[KPI]
    ed: List[EDPatient]
    beds: List[Bed]
    inpatients: List[Inpatient]
    edForecast: List[ForecastPoint]
    bedForecast: List[ForecastPoint]
    as_of: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    seed: int = 42
    human_impact: HumanImpactMetrics = Field(default_factory=HumanImpactMetrics)
    forecast_inputs: ForecastInputs = Field(default_factory=ForecastInputs)
    scenario_name: str = "baseline"
    scenario_description: str = "Normal operating conditions."
    scenario_pressure_level: str = "low"
