"""Pydantic models shared by the synthetic hospital API."""

from datetime import datetime
from typing import List, Literal, Optional

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


class SolOperationalRisk(BaseModel):
    overall_risk_score: int = Field(default=0, ge=0, le=100)
    ed_risk_score: int = Field(default=0, ge=0, le=100)
    bed_risk_score: int = Field(default=0, ge=0, le=100)
    dtoc_risk_score: int = Field(default=0, ge=0, le=100)
    los_risk_score: int = Field(default=0, ge=0, le=100)
    staffing_risk_score: int = Field(default=0, ge=0, le=100)


class SolHumanImpact(BaseModel):
    patients_delayed_over_4h: int = Field(default=0, ge=0)
    patients_delayed_over_12h: int = Field(default=0, ge=0)
    patients_boarded_in_ed: int = Field(default=0, ge=0)
    total_delayed_bed_hours: float = Field(default=0.0, ge=0.0)
    total_delayed_discharge_hours: float = Field(default=0.0, ge=0.0)
    clinical_risk_level: Literal["low", "medium", "high"] = "low"


class SolScenarioContext(BaseModel):
    scenario_name: str = "baseline"
    scenario_pressure_level: str = "low"
    scenario_description: str = "Normal operating conditions."
    scenario_drivers: List[str] = Field(default_factory=list)


class SolForecastInputs(BaseModel):
    ed_arrivals_next_24h: List[int] = Field(default_factory=list)
    bed_occupancy_next_24h: List[int] = Field(default_factory=list)
    dtoc_trend_5d: List[int] = Field(default_factory=list)
    los_trend_5d: List[float] = Field(default_factory=list)


class FlowScoreV2(BaseModel):
    ed_flow: float = Field(default=0.0, ge=0.0, le=100.0)
    inpatient_flow: float = Field(default=0.0, ge=0.0, le=100.0)
    discharge_flow: float = Field(default=0.0, ge=0.0, le=100.0)
    overall_flow_score: float = Field(default=0.0, ge=0.0, le=100.0)


class FlowScoreV3(BaseModel):
    ed_flow: float = Field(default=0.0, ge=0.0, le=100.0)
    inpatient_flow: float = Field(default=0.0, ge=0.0, le=100.0)
    discharge_flow: float = Field(default=0.0, ge=0.0, le=100.0)
    staffing_flow: float = Field(default=0.0, ge=0.0, le=100.0)
    overall_flow_score: float = Field(default=0.0, ge=0.0, le=100.0)


class PrioritizedAction(BaseModel):
    action: str
    priority: Literal["high", "medium", "low"]


class OperationalNarrative(BaseModel):
    summary: str = ""
    ed_status: str = ""
    inpatient_status: str = ""
    discharge_status: str = ""
    risk_summary: str = ""


class JudgeMode(BaseModel):
    headline: str = ""
    key_risks: List[str] = Field(default_factory=list)
    key_actions: List[PrioritizedAction] = Field(default_factory=list)
    flow_summary: str = ""


class SolReadyPayload(BaseModel):
    operational_risk: SolOperationalRisk = Field(
        default_factory=SolOperationalRisk
    )
    human_impact: SolHumanImpact = Field(default_factory=SolHumanImpact)
    scenario_context: SolScenarioContext = Field(
        default_factory=SolScenarioContext
    )
    forecast_inputs: SolForecastInputs = Field(
        default_factory=SolForecastInputs
    )
    recommended_actions: List[str] = Field(default_factory=list)
    prioritized_actions: List[PrioritizedAction] = Field(default_factory=list)


class SyntheticValidation(BaseModel):
    json_structure_ok: bool = False
    capacity_limits_ok: bool = False
    scenario_effects_ok: bool = False
    kpi_ranges_ok: bool = False
    forecast_lengths_ok: bool = False
    backward_compatibility_ok: bool = False


class SyntheticHealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
    engine_version: str = "3.5"
    last_generated: str


class SituationReportResponse(BaseModel):
    as_of: str
    scenario: str
    flow_score_v2: FlowScoreV2
    flow_score_v3: FlowScoreV3 = Field(default_factory=FlowScoreV3)
    operational_risk: SolOperationalRisk
    human_impact: SolHumanImpact
    recommended_actions: List[str]
    prioritized_actions: List[PrioritizedAction] = Field(default_factory=list)
    narrative: OperationalNarrative
    judge_mode: JudgeMode = Field(default_factory=JudgeMode)
    executive_summary: str = ""
    scenario_context: SolScenarioContext = Field(
        default_factory=SolScenarioContext
    )
    forecast_inputs: SolForecastInputs = Field(
        default_factory=SolForecastInputs
    )
    checksum: str = ""
    validation: SyntheticValidation = Field(default_factory=SyntheticValidation)
    engine_version: str = "3.5"


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
    sol_ready: SolReadyPayload = Field(default_factory=SolReadyPayload)
    validation: SyntheticValidation = Field(default_factory=SyntheticValidation)
    checksum: str = ""
    engine_version: str = "3.5"
    flow_score_v2: FlowScoreV2 = Field(default_factory=FlowScoreV2)
    narrative: OperationalNarrative = Field(
        default_factory=OperationalNarrative
    )
    flow_score_v3: FlowScoreV3 = Field(default_factory=FlowScoreV3)
    judge_mode: JudgeMode = Field(default_factory=JudgeMode)
    executive_summary: str = ""
