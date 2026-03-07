from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Annotated
from enum import Enum
from datetime import datetime
import operator


# ─── Enums ────────────────────────────────────────────────────────────────────

class Severity(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class Recommendation(str, Enum):
    APPROVE = "APPROVE"
    CONDITIONAL_APPROVE = "CONDITIONAL APPROVE"
    REJECT = "REJECT"


class SectorOutlook(str, Enum):
    POSITIVE = "POSITIVE"
    NEUTRAL = "NEUTRAL"
    NEGATIVE = "NEGATIVE"


class AgentStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    DONE = "DONE"
    ERROR = "ERROR"


class JobStatus(str, Enum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


# ─── Financial Sub-models ─────────────────────────────────────────────────────

class GSTDiscrepancy(BaseModel):
    detected: bool = False
    details: str = ""
    severity: Severity = Severity.LOW


class Financials(BaseModel):
    revenue_3yr: List[float] = Field(default_factory=list)
    ebitda_3yr: List[float] = Field(default_factory=list)
    pat_3yr: List[float] = Field(default_factory=list)
    total_debt: float = 0.0
    net_worth: float = 0.0
    dscr: float = 0.0
    debt_to_equity: float = 0.0
    cash_flow_from_operations: float = 0.0


class Collateral(BaseModel):
    type: str = ""
    estimated_value: float = 0.0


# ─── Company Profile Models ──────────────────────────────────────────────────

class CompanyProfile(BaseModel):
    """Company profile extracted from MCA/documents."""
    cin: str = ""
    company_name: str = ""
    incorporation_date: Optional[str] = None  # ISO format
    company_age_years: float = 0.0
    authorized_capital: float = 0.0  # In Crores
    paid_up_capital: float = 0.0  # In Crores
    company_status: str = "ACTIVE"  # Active/Struck Off/Dormant
    company_class: str = ""  # Private/Public/OPC
    roc: str = ""  # Registrar of Companies


class FORAnalysis(BaseModel):
    """Fixed Obligation to Income Ratio analysis."""
    gross_monthly_income: float = 0.0
    existing_emi_total: float = 0.0
    proposed_emi: float = 0.0
    for_ratio: float = 0.0
    for_status: str = "UNKNOWN"  # HEALTHY/STRAINED/OVER-LEVERAGED
    recommendation: str = ""


class WorkingCapitalAnalysis(BaseModel):
    """Working capital and liquidity analysis."""
    current_assets: float = 0.0
    current_liabilities: float = 0.0
    current_ratio: float = 0.0
    quick_ratio: float = 0.0
    inventory_days: int = 0
    receivable_days: int = 0
    payable_days: int = 0
    cash_conversion_cycle: int = 0
    adequacy_status: str = "UNKNOWN"  # Adequate/Stressed/Critical


# ─── Dynamic Weight Models ───────────────────────────────────────────────────

class RiskProfileEnum(str, Enum):
    """Risk profile classification."""
    STANDARD = "STANDARD"
    ELEVATED = "ELEVATED"
    HIGH_RISK = "HIGH_RISK"
    CRITICAL = "CRITICAL"


class DynamicWeightResult(BaseModel):
    """Dynamic weight computation result."""
    risk_profile: str = RiskProfileEnum.STANDARD.value
    risk_score: int = 0
    base_weights: Dict[str, float] = Field(default_factory=dict)
    final_weights: Dict[str, float] = Field(default_factory=dict)
    weight_justifications: List[str] = Field(default_factory=list)
    scoring_mode: str = "FIVE_CS"  # FIVE_CS or EXPANDED


# ─── Red Flag Models ─────────────────────────────────────────────────────────

class RedFlagSeverity(str, Enum):
    """Red flag severity levels."""
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class RedFlagItem(BaseModel):
    """Individual red flag."""
    code: str = ""
    name: str = ""
    category: str = ""
    severity: RedFlagSeverity = RedFlagSeverity.LOW
    action: str = ""
    description: str = ""
    trigger_value: str = ""
    threshold: str = ""
    remediation: Optional[str] = None
    override_possible: bool = True


class RedFlagEvaluation(BaseModel):
    """Red flag evaluation result."""
    has_critical_flags: bool = False
    should_auto_reject: bool = False
    flags: List[RedFlagItem] = Field(default_factory=list)
    rejection_reason: Optional[str] = None
    escalation_required: bool = False
    total_flag_count: int = 0
    recommendation: str = ""


class ExtractedFinancials(BaseModel):
    company_name: str = ""
    promoters: List[str] = Field(default_factory=list)
    financials: Financials = Field(default_factory=Financials)
    collateral: Collateral = Field(default_factory=Collateral)
    gst_vs_bank_discrepancy: GSTDiscrepancy = Field(default_factory=GSTDiscrepancy)
    red_flags: List[str] = Field(default_factory=list)


# ─── Research Sub-models ──────────────────────────────────────────────────────

class KeyFinding(BaseModel):
    finding: str = ""
    severity: Severity = Severity.LOW
    source: str = ""
    date: str = ""


class ResearchFindings(BaseModel):
    litigation_risk: Severity = Severity.LOW
    promoter_integrity_score: int = 75
    sector_outlook: SectorOutlook = SectorOutlook.NEUTRAL
    sector_headwinds: List[str] = Field(default_factory=list)
    key_findings: List[KeyFinding] = Field(default_factory=list)
    recommendation_impact: str = ""


# ─── Scoring Sub-models ───────────────────────────────────────────────────────

class CScore(BaseModel):
    score: float = 0.0
    reasons: List[str] = Field(default_factory=list)
    weight: float = 0.0
    weighted_contribution: float = 0.0


class FiveCsScores(BaseModel):
    character: CScore = Field(default_factory=lambda: CScore(weight=0.25))
    capacity: CScore = Field(default_factory=lambda: CScore(weight=0.30))
    capital: CScore = Field(default_factory=lambda: CScore(weight=0.20))
    collateral: CScore = Field(default_factory=lambda: CScore(weight=0.15))
    conditions: CScore = Field(default_factory=lambda: CScore(weight=0.10))
    weighted_total: float = 0.0
    recommendation: Recommendation = Recommendation.REJECT
    suggested_loan_amount: float = 0.0
    suggested_interest_rate: str = ""
    decision_reason: str = ""
    overriding_factors: List[str] = Field(default_factory=list)


# ─── Arbitration ──────────────────────────────────────────────────────────────

class ArbitrationResult(BaseModel):
    conflict_detected: bool = False
    reconciliation_reasoning: str = ""
    adjusted_risk_weight: float = 1.0
    favors: str = "FINANCIALS"  # FINANCIALS | RESEARCH


# ─── Log Entry ────────────────────────────────────────────────────────────────

class LogEntry(BaseModel):
    timestamp: str = Field(default_factory=lambda: datetime.now().strftime("%H:%M:%S"))
    agent: str = "SYSTEM"
    message: str = ""
    level: str = "INFO"  # INFO | WARN | ERROR | SUCCESS


# ─── LangGraph State (TypedDict for StateGraph) ───────────────────────────────
# Keep as a plain dict-compatible model; agents return partial dicts to update it.

class CreditAppraisalState(BaseModel):
    """Full mutable state passed through the LangGraph pipeline."""
    job_id: str = ""
    company_name: str = ""
    sector: str = ""
    loan_amount_requested: float = 0.0
    # Serialised document payloads (text + tables) keyed by doc_type
    documents: List[Dict[str, Any]] = Field(default_factory=list)
    qualitative_notes: str = ""

    # Company profile (from MCA/documents)
    company_profile: Dict[str, Any] = Field(default_factory=dict)
    incorporation_date: Optional[str] = None

    # Agent outputs
    extracted_financials: Dict[str, Any] = Field(default_factory=dict)
    fraud_flags: List[str] = Field(default_factory=list)
    research_findings: Dict[str, Any] = Field(default_factory=dict)
    five_cs_scores: Dict[str, Any] = Field(default_factory=dict)
    final_recommendation: Dict[str, Any] = Field(default_factory=dict)
    arbitration_result: Dict[str, Any] = Field(default_factory=dict)

    # Dynamic weighting results
    dynamic_weight_config: Dict[str, Any] = Field(default_factory=dict)
    risk_profile: str = ""
    red_flag_evaluation: Dict[str, Any] = Field(default_factory=dict)

    # FOR and Working Capital analysis
    for_analysis: Dict[str, Any] = Field(default_factory=dict)
    working_capital_analysis: Dict[str, Any] = Field(default_factory=dict)

    # Qualitative override comparison
    pre_override_scores: Dict[str, Any] = Field(default_factory=dict)
    override_applied: bool = False

    # Output
    cam_path: str = ""
    logs: List[Dict[str, Any]] = Field(default_factory=list)

    # Control
    status: str = JobStatus.QUEUED
    conflict_detected: bool = False
    agent_statuses: Dict[str, str] = Field(default_factory=lambda: {
        "ingestor": AgentStatus.PENDING,
        "research": AgentStatus.PENDING,
        "scorer": AgentStatus.PENDING,
        "cam_generator": AgentStatus.PENDING,
    })
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error_message: str = ""


# ─── API Request / Response Models ───────────────────────────────────────────

class AppraisalStartResponse(BaseModel):
    job_id: str
    message: str = "Appraisal job queued successfully"


class AppraisalStatusResponse(BaseModel):
    job_id: str
    status: str
    agent_statuses: Dict[str, str]
    logs: List[Dict[str, Any]]
    conflict_detected: bool = False
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error_message: str = ""


class AppraisalResultsResponse(BaseModel):
    job_id: str
    company_name: str
    sector: str
    loan_amount_requested: float
    extracted_financials: Dict[str, Any]
    research_findings: Dict[str, Any]
    five_cs_scores: Dict[str, Any]
    final_recommendation: Dict[str, Any]
    arbitration_result: Dict[str, Any]
    pre_override_scores: Dict[str, Any]
    override_applied: bool
    fraud_flags: List[str]
    cam_path: str
    # New dynamic weighting fields
    dynamic_weight_config: Dict[str, Any] = Field(default_factory=dict)
    risk_profile: str = ""
    red_flag_evaluation: Dict[str, Any] = Field(default_factory=dict)
    for_analysis: Dict[str, Any] = Field(default_factory=dict)
    working_capital_analysis: Dict[str, Any] = Field(default_factory=dict)
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


class WSMessage(BaseModel):
    type: str  # "log" | "status" | "complete" | "error"
    payload: Dict[str, Any]
