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


class ExposureStatus(str, Enum):
    """Status of exposure limit checks."""
    GREEN = "GREEN"
    AMBER = "AMBER"
    HARD_BLOCK = "HARD_BLOCK"


class PSLCategory(str, Enum):
    """Priority Sector Lending categories."""
    AGRICULTURE = "AGRICULTURE"
    MSME = "MSME"
    EXPORT_CREDIT = "EXPORT_CREDIT"
    HOUSING = "HOUSING"
    EDUCATION = "EDUCATION"
    RENEWABLE_ENERGY = "RENEWABLE_ENERGY"


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
    compliance_result: Dict[str, Any] = Field(default_factory=dict)  # NEW: Compliance agent output
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
        "compliance": AgentStatus.PENDING,
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
    compliance_result: Dict[str, Any] = Field(default_factory=dict)  # NEW
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


# ─── Compliance Models (Indian Regulatory Checks) ─────────────────────────────

class ComplianceSeverity(str, Enum):
    """Compliance check severity levels."""
    HARD_REJECT = "HARD_REJECT"
    RED = "RED"
    AMBER = "AMBER"
    GREEN = "GREEN"


class ComplianceFlag(BaseModel):
    """Individual compliance flag."""
    check: str = ""
    severity: ComplianceSeverity = ComplianceSeverity.GREEN
    triggered: bool = False
    details: Optional[str] = None
    source: str = ""


class DirectorStatus(BaseModel):
    """Director status and verification details."""
    name: str = ""
    din: str = ""
    status: str = "UNKNOWN"  # ACTIVE | DISQUALIFIED | UNKNOWN


class CERSAICharge(BaseModel):
    """CERSAI registered charge details."""
    charge_holder: str = ""
    amount: float = 0.0
    registration_date: str = ""
    charge_type: str = ""  # Primary | Second | Pari Passu


class SuspiciousTransaction(BaseModel):
    """AML suspicious transaction record."""
    date: str = ""
    amount: float = 0.0
    type: str = ""  # Structuring | Smurfing | Layering
    description: str = ""


class ComplianceResult(BaseModel):
    """Comprehensive compliance check results for Indian regulatory requirements."""
    
    # Overall status
    hard_reject: bool = False
    hard_reject_reason: Optional[str] = None
    hard_reject_checks_triggered: List[str] = Field(default_factory=list)
    
    # Priority 1 — Hard Reject Checks
    wilful_defaulter: Dict[str, Any] = Field(default_factory=lambda: {
        "check": "wilful_defaulter",
        "triggered": False,
        "matched_entity": None,
        "severity": "GREEN",
        "source": "RBI/CIBIL"
    })
    
    nclt_status: Dict[str, Any] = Field(default_factory=lambda: {
        "check": "nclt_status",
        "under_cirp": False,
        "case_number": None,
        "admission_date": None,
        "director_linked_nclt": False,
        "severity": "GREEN"
    })
    
    fema_ed: Dict[str, Any] = Field(default_factory=lambda: {
        "check": "fema_ed",
        "case_found": False,
        "case_details": None,
        "severity": "GREEN"
    })
    
    cibil_writeoff: Dict[str, Any] = Field(default_factory=lambda: {
        "check": "cibil_writeoff",
        "writeoff_found": False,
        "writeoff_amount": None,
        "writeoff_year": None,
        "severity": "GREEN"
    })
    
    gst_status: Dict[str, Any] = Field(default_factory=lambda: {
        "check": "gst_status",
        "status": "UNKNOWN",
        "cancellation_date": None,
        "cancellation_reason": None,
        "severity": "GREEN"
    })
    
    din_status: Dict[str, Any] = Field(default_factory=lambda: {
        "check": "din_status",
        "directors": [],
        "any_disqualified": False,
        "severity": "GREEN"
    })
    
    # Priority 2 — CRILC / SMA Status
    crilc_sma: Dict[str, Any] = Field(default_factory=lambda: {
        "check": "crilc_sma",
        "sma_status": "STANDARD",
        "reporting_bank": None,
        "as_of_date": None,
        "severity": "GREEN"
    })
    
    ots_history: Dict[str, Any] = Field(default_factory=lambda: {
        "check": "ots_history",
        "ots_found": False,
        "ots_date": None,
        "ots_bank": None,
        "years_since_ots": None,
        "severity": "GREEN"
    })
    
    # Priority 3 — KYC / AML Checks
    pan_verify: Dict[str, Any] = Field(default_factory=lambda: {
        "check": "pan_verify",
        "pan": "",
        "status": "UNKNOWN",
        "name_match": False,
        "severity": "AMBER"
    })
    
    pep_status: Dict[str, Any] = Field(default_factory=lambda: {
        "check": "pep_status",
        "pep_found": False,
        "pep_details": None,
        "edd_required": False,
        "severity": "GREEN"
    })
    
    aml_patterns: Dict[str, Any] = Field(default_factory=lambda: {
        "check": "aml_patterns",
        "structuring_detected": False,
        "smurfing_detected": False,
        "layering_detected": False,
        "cash_deposit_ratio": 0.0,
        "suspicious_transactions": [],
        "severity": "GREEN"
    })
    
    # Priority 4 — Collateral / Security Checks
    cersai: Dict[str, Any] = Field(default_factory=lambda: {
        "check": "cersai",
        "existing_charges": [],
        "fully_mortgaged": False,
        "severity": "GREEN"
    })
    
    ltv_ratio: Dict[str, Any] = Field(default_factory=lambda: {
        "check": "ltv_ratio",
        "calculated_ltv": 0.0,
        "rbi_cap": 0.75,
        "within_limit": True,
        "collateral_type": "unknown",
        "severity": "GREEN"
    })
    
    # Priority 5 — Statutory Compliance Checks
    epfo_compliance: Dict[str, Any] = Field(default_factory=lambda: {
        "check": "epfo_compliance",
        "applicable": False,
        "default_months": 0,
        "pf_headcount": None,
        "payroll_headcount": None,
        "headcount_mismatch_pct": 0.0,
        "compliance_status": "UNKNOWN",
        "severity": "GREEN"
    })
    
    esic_compliance: Dict[str, Any] = Field(default_factory=lambda: {
        "check": "esic_compliance",
        "applicable": False,
        "default_months": 0,
        "compliance_status": "UNKNOWN",
        "severity": "GREEN"
    })
    
    income_tax_compliance: Dict[str, Any] = Field(default_factory=lambda: {
        "check": "income_tax_compliance",
        "26as_tds_credits": 0.0,
        "itr_declared_revenue": 0.0,
        "revenue_gap_pct": 0.0,
        "pending_it_demand": 0.0,
        "tds_default": False,
        "advance_tax_regular": True,
        "under_scrutiny": False,
        "severity": "GREEN"
    })
    
    # Priority 6 — GST Deep Dive
    gst_deep_dive: Dict[str, Any] = Field(default_factory=lambda: {
        "check": "gst_deep_dive",
        "gstr9_3b_mismatch_pct": 0.0,
        "itc_reversal_amount": 0.0,
        "pending_gst_demand": 0.0,
        "filing_gaps_last_24m": 0,
        "scheme_type": "UNKNOWN",
        "scheme_violation": False,
        "eway_bill_turnover_match": True,
        "severity": "GREEN"
    })
    
    # Priority 7 — Sector Specific Checks
    sector_classification: Dict[str, Any] = Field(default_factory=lambda: {
        "check": "sector_classification",
        "nic_code": "",
        "rbi_sector": "",
        "is_sensitive_sector": False,
        "psl_eligible": False,
        "psl_category": None,
        "udyam_number": None,
        "udyam_valid": None,
        "severity": "GREEN"
    })
    
    # Summary metrics
    total_hard_rejects: int = 0
    total_red_flags: int = 0
    total_amber_flags: int = 0
    compliance_score: float = 1.0  # 0 to 1, 1 = fully compliant
    
    # Timestamp
    checked_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class RiskPremiumBreakup(BaseModel):
    """Interest rate risk premium breakdown."""
    base_rate: float = 8.5
    credit_risk_spread: float = 0.0
    sector_risk_spread: float = 0.0
    compliance_risk_spread: float = 0.0
    final_rate: float = 8.5


class DecisionExplainability(BaseModel):
    """Decision explainability details."""
    top_positive_factors: List[str] = Field(default_factory=list)
    top_negative_factors: List[str] = Field(default_factory=list)
    why_this_rate: str = ""
    why_this_amount: str = ""
    why_rejected: Optional[str] = None
    checks_triggered: List[str] = Field(default_factory=list)


class FinalDecision(BaseModel):
    """Final credit decision output."""
    recommendation: str = "REJECT"  # APPROVE | REJECT | REFER_TO_COMMITTEE
    rejection_reason: Optional[str] = None
    suggested_loan_amount: float = 0.0
    suggested_interest_rate: float = 0.0
    risk_premium_breakup: RiskPremiumBreakup = Field(default_factory=RiskPremiumBreakup)
    conditions_precedent: List[str] = Field(default_factory=list)
    explainability: DecisionExplainability = Field(default_factory=DecisionExplainability)


class MasterCreditOutput(BaseModel):
    """Master credit appraisal output with full compliance integration."""
    
    # Company identification
    company_name: str = ""
    cin: str = ""
    pan: str = ""
    gstin: str = ""
    
    # Processing metadata
    processing_metadata: Dict[str, Any] = Field(default_factory=dict)
    
    # Financial analysis
    financials: Dict[str, Any] = Field(default_factory=dict)
    banking_behavior: Dict[str, Any] = Field(default_factory=dict)
    gst_analysis: Dict[str, Any] = Field(default_factory=dict)
    
    # NEW: Full compliance result
    compliance: ComplianceResult = Field(default_factory=ComplianceResult)
    
    # Updated 5Cs (now fed by compliance signals)
    five_cs_summary: Dict[str, Any] = Field(default_factory=dict)
    
    # Final decision
    decision: FinalDecision = Field(default_factory=FinalDecision)
    
    # CAM document path
    cam_path: str = ""


# ─── Explainable Scoring Models ──────────────────────────────────────────────

class RatioFlag(str, Enum):
    """Color-coded flag for ratio performance."""
    GREEN = "GREEN"
    AMBER = "AMBER"
    RED = "RED"
    HARD_REJECT = "HARD_REJECT"


class LoanType(str, Enum):
    """Type of loan for weight profile selection."""
    WORKING_CAPITAL = "WORKING_CAPITAL"
    TERM_LOAN = "TERM_LOAN"
    PROJECT_FINANCE = "PROJECT_FINANCE"


class RatioScore(BaseModel):
    """
    Single ratio result with full transparency and traceability.
    
    Every field is designed for auditability and explainability.
    """
    # Identification
    parameter_name: str = ""
    category: str = ""  # Repayment Capacity | Liquidity | Leverage | Profitability | Banking Behavior
    
    # Calculation details
    formula: str = ""
    company_value: float = 0.0
    company_value_display: str = ""  # Formatted for display (e.g., "1.45x", "23.5%")
    
    # RBI benchmarks (if applicable)
    rbi_floor: Optional[float] = None
    rbi_floor_display: Optional[str] = None
    rbi_source: Optional[str] = None  # Full RBI circular reference
    rbi_mandated: bool = False  # True if RBI hard floor, False if guidance only
    
    # Industry benchmarks
    industry_median: Optional[float] = None
    industry_p25: Optional[float] = None  # 25th percentile
    industry_p75: Optional[float] = None  # 75th percentile
    industry_source: str = ""  # "RBI OBSE FY2024" or similar
    
    # Scoring
    score: float = 0.0  # 0 to 100
    weight: float = 0.0  # As decimal (e.g., 0.25 for 25%)
    weighted_score: float = 0.0
    
    # Flags and explanation
    flag: RatioFlag = RatioFlag.GREEN
    reason: str = ""  # Plain English explanation
    data_source: str = ""  # Where company data came from
    benchmark_source: str = ""  # Where benchmark came from
    
    # Metadata
    calculated_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class CategorySubtotal(BaseModel):
    """Subtotal for a scoring category."""
    category_name: str = ""
    total_weight: float = 0.0
    weighted_score: float = 0.0
    ratio_count: int = 0


class WeightProfile(BaseModel):
    """Weight distribution for a loan type."""
    loan_type: LoanType = LoanType.TERM_LOAN
    repayment_capacity: float = 0.35
    liquidity: float = 0.15
    leverage: float = 0.25
    profitability: float = 0.15
    banking_behavior: float = 0.10
    rationale: str = ""


class ScorecardResult(BaseModel):
    """
    Complete transparent scorecard with all ratios and explanations.
    """
    # Input context
    company_name: str = ""
    loan_type: LoanType = LoanType.TERM_LOAN
    loan_amount_requested: float = 0.0
    
    # Weight profile used
    weight_profile: WeightProfile = Field(default_factory=WeightProfile)
    weight_rationale: str = ""
    
    # All ratio scores
    ratio_scores: List[RatioScore] = Field(default_factory=list)
    
    # Category subtotals
    category_subtotals: List[CategorySubtotal] = Field(default_factory=list)
    
    # Score calculation
    base_financial_score: float = 0.0  # Sum of all weighted scores (0-100)
    compliance_red_flags: int = 0
    compliance_amber_flags: int = 0
    compliance_deduction: float = 0.0  # Total points deducted
    qualitative_breakdown: Optional[Dict[str, Any]] = None  # Qualitative assessment details
    final_score: float = 0.0  # After compliance deductions (0-100)
    
    # Decision band (BANK CONFIGURABLE - NOT RBI MANDATED)
    decision_band: str = ""  # APPROVE | REFER | CONDITIONAL | REJECT
    band_thresholds: Dict[str, float] = Field(default_factory=lambda: {
        "APPROVE": 75.0,
        "REFER_TO_COMMITTEE": 60.0,
        "CONDITIONAL_APPROVE": 45.0,
        "REJECT": 0.0
    })
    band_rationale: str = "Bank internal policy - not RBI mandated"
    
    # Metadata
    scored_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    scored_by: str = "ExplainableScoringAgent v2.0"


# ─── Bank Capacity Models ────────────────────────────────────────────────────

class BankConfig(BaseModel):
    """
    Bank's current capital position and internal policy limits.
    
    All fields configurable per bank's risk appetite.
    """
    # Capital adequacy (Basel III)
    tier1_capital: float = 0.0  # In INR absolute
    tier2_capital: float = 0.0  # In INR absolute
    total_capital: float = 0.0  # tier1 + tier2
    current_crar: float = 0.0  # As decimal (e.g., 0.115 for 11.5%)
    current_lcr: float = 0.0   # Liquidity Coverage Ratio
    current_nsfr: float = 0.0  # Net Stable Funding Ratio
    
    # Loan book composition
    total_loan_book: float = 0.0  # Total advances in INR
    anbc: float = 0.0  # Adjusted Net Bank Credit for PSL calculation
    psl_achieved_pct: float = 0.0  # Current PSL as % of ANBC
    psl_target_pct: float = 0.40  # RBI target 40%
    
    # Exposure tracking
    sector_exposures: Dict[str, float] = Field(default_factory=dict)  # sector: exposure_amount
    sector_limits: Dict[str, float] = Field(default_factory=dict)  # sector: limit_as_pct_of_book
    
    # Regulatory status
    under_pca: bool = False  # Under RBI Prompt Corrective Action
    pca_restrictions: List[str] = Field(default_factory=list)
    
    # Internal policy thresholds (all bank configurable)
    min_company_age_years: float = 3.0
    min_promoter_contribution_pct: float = 0.25  # 25%
    min_collateral_cover: float = 1.33  # 1.33x
    min_ticket_size: float = 0.0  # Per desk
    max_ticket_size: float = 0.0  # Per desk
    
    # Current EBLR (External Benchmark Lending Rate)
    eblr: float = 0.085  # 8.5% as per RBI/2019-20/23
    
    # Updated timestamp
    config_as_of_date: str = Field(default_factory=lambda: datetime.now().date().isoformat())


class ExposureCheck(BaseModel):
    """Single exposure limit check result."""
    check_name: str = ""
    can_lend: bool = True
    block_reason: Optional[str] = None
    current_exposure: float = 0.0
    limit_amount: float = 0.0
    headroom: float = 0.0
    utilization_pct: float = 0.0
    severity: str = "GREEN"  # GREEN | AMBER | HARD_BLOCK
    rbi_source: Optional[str] = None


class PSLOpportunity(BaseModel):
    """Priority Sector Lending opportunity details."""
    is_psl_eligible: bool = False
    psl_category: Optional[str] = None  # MSME | Agriculture | Affordable Housing
    current_psl_shortfall_pct: float = 0.0
    rate_discount_applicable: float = 0.0  # In basis points
    discount_rationale: str = ""


class ProvisioningCost(BaseModel):
    """Provisioning requirements for pricing."""
    loan_category: str = "Standard Corporate"  # Standard Corporate | CRE | SME
    provisioning_rate_pct: float = 0.0040  # 0.40% for standard corporate
    annual_provisioning_cost: float = 0.0  # In INR
    rbi_source: str = "RBI IRACP Norms DOR.STR.REC.68/21.04.048/2021-22"


class InterestRateComponent(BaseModel):
    """Single component of interest rate build-up."""
    component_name: str = ""
    rate_bps: float = 0.0  # In basis points (1 bps = 0.01%)
    rate_pct: float = 0.0  # As percentage
    basis: str = ""  # Explanation/source
    is_discount: bool = False  # True for PSL discount


class CapacityResult(BaseModel):
    """
    Bank's capacity to lend this loan - regulatory and internal limits.
    """
    # Overall result
    can_lend: bool = True
    cannot_lend_reason: Optional[str] = None
    severity: str = "GREEN"  # GREEN | AMBER | HARD_BLOCK
    
    # Individual checks (6 checks)
    single_borrower_exposure: ExposureCheck = Field(default_factory=ExposureCheck)
    group_exposure: ExposureCheck = Field(default_factory=ExposureCheck)
    sector_concentration: ExposureCheck = Field(default_factory=ExposureCheck)
    crar_impact: ExposureCheck = Field(default_factory=ExposureCheck)
    internal_policy: ExposureCheck = Field(default_factory=ExposureCheck)
    pca_status: ExposureCheck = Field(default_factory=ExposureCheck)
    
    # PSL opportunity
    psl_opportunity: PSLOpportunity = Field(default_factory=PSLOpportunity)
    
    # Provisioning
    provisioning: ProvisioningCost = Field(default_factory=ProvisioningCost)
    
    # Limits and suggestions
    suggested_max_amount: float = 0.0  # Based on all exposure limits
    suggested_max_tenure_years: float = 7.0
    
    # Transparent pricing build-up
    interest_rate_components: List[InterestRateComponent] = Field(default_factory=list)
    base_rate: float = 0.0  # EBLR
    total_spread_bps: float = 0.0  # Sum of all spreads
    final_rate_pct: float = 0.0  # base_rate + spread
    
    # Metadata
    checked_at: str = Field(default_factory=lambda: datetime.now().isoformat())


# ─── Final Decision Models (4-Gate Logic) ────────────────────────────────────

class DecisionGate(str, Enum):
    """Which gate made the final decision."""
    GATE_1_COMPLIANCE = "GATE_1_COMPLIANCE"
    GATE_2_CAPACITY = "GATE_2_CAPACITY"
    GATE_3_SCORE = "GATE_3_SCORE"
    GATE_4_AMOUNT = "GATE_4_AMOUNT"


class AmountCalculation(BaseModel):
    """Transparent amount calculation showing all constraints."""
    requested_amount: float = 0.0
    score_based_max: float = 0.0  # 3x EBITDA for term loans
    score_based_reason: str = ""
    capacity_based_max: float = 0.0  # From exposure headroom
    capacity_based_reason: str = ""
    final_approved_amount: float = 0.0
    amount_reduced: bool = False
    reduction_reason: Optional[str] = None


class EnhancedFinalDecision(BaseModel):
    """
    Complete credit decision with full 4-gate explainability.
    """
    # Decision summary
    recommendation: str = "REJECT"  # APPROVE | CONDITIONAL_APPROVE | REFER_TO_COMMITTEE | REJECT
    deciding_gate: DecisionGate = DecisionGate.GATE_3_SCORE
    
    # Amount decision
    amount_calculation: AmountCalculation = Field(default_factory=AmountCalculation)
    
    # Rejection reasons (if applicable)
    rejection_reason: Optional[str] = None
    rejection_gate: Optional[str] = None
    
    # Interest rate transparency
    interest_rate_components: List[InterestRateComponent] = Field(default_factory=list)
    final_interest_rate_pct: float = 0.0
    rate_valid_until: Optional[str] = None
    
    # Conditions and covenants
    conditions_precedent: List[str] = Field(default_factory=list)
    financial_covenants: List[str] = Field(default_factory=list)
    operational_covenants: List[str] = Field(default_factory=list)
    
    # Full explainability
    explainability: Dict[str, Any] = Field(default_factory=lambda: {
        "gate_1_compliance": {},
        "gate_2_capacity": {},
        "gate_3_score": {},
        "gate_4_amount": {},
        "scorecard_summary": {},
        "top_strengths": [],
        "top_concerns": [],
        "committee_notes": ""
    })
    
    # Decision metadata
    decided_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    decided_by: str = "DecisionEngine v3.0"
    approval_authority: str = ""  # Branch | Zonal | Central | Board
    next_review_date: Optional[str] = None


class EnhancedMasterCreditOutput(BaseModel):
    """
    Master output combining all agent results with full transparency.
    """
    # Company identification
    company_name: str = ""
    cin: str = ""
    pan: str = ""
    gstin: str = ""
    sector: str = ""
    
    # Processing metadata
    job_id: str = ""
    processing_metadata: Dict[str, Any] = Field(default_factory=dict)
    
    # Agent results
    compliance_result: ComplianceResult = Field(default_factory=ComplianceResult)
    scorecard_result: ScorecardResult = Field(default_factory=ScorecardResult)
    capacity_result: CapacityResult = Field(default_factory=CapacityResult)
    
    # Final decision (4-gate logic)
    final_decision: EnhancedFinalDecision = Field(default_factory=EnhancedFinalDecision)
    
    # Legacy compatibility (keep existing 5Cs for backward compatibility)
    five_cs_summary: Dict[str, Any] = Field(default_factory=dict)
    
    # CAM document
    cam_path: str = ""
    
    # Audit trail
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    version: str = "3.0"  # New explainable scoring version


class WSMessage(BaseModel):
    type: str  # "log" | "status" | "complete" | "error"
    payload: Dict[str, Any]
