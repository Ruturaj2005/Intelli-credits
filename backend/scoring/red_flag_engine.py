"""
Red Flag Engine for Corporate Credit Assessment.

This module implements automatic rejection triggers based on hard stops
that credit managers use in practice. These are non-negotiable criteria
where no amount of positive factors can override the red flag.

RED FLAG CATEGORIES:
1. Regulatory Red Flags (RBI negative list, struck-off companies)
2. Credit Red Flags (CIBIL below threshold, wilful defaulter)
3. Financial Red Flags (FOR > 50%, negative net worth)
4. Legal Red Flags (criminal cases, serious fraud)
5. Compliance Red Flags (missing critical documents)

Author: Credit Intelligence System
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class RedFlagSeverity(str, Enum):
    """Severity of red flag - determines action."""
    CRITICAL = "CRITICAL"       # Auto-reject, no exceptions
    HIGH = "HIGH"               # Escalate to senior management
    MEDIUM = "MEDIUM"           # Flag for review but can proceed
    LOW = "LOW"                 # Monitor only


class RedFlagCategory(str, Enum):
    """Categories of red flags."""
    REGULATORY = "REGULATORY"
    CREDIT = "CREDIT"
    FINANCIAL = "FINANCIAL"
    LEGAL = "LEGAL"
    COMPLIANCE = "COMPLIANCE"
    FRAUD = "FRAUD"
    OPERATIONAL = "OPERATIONAL"


class RedFlagAction(str, Enum):
    """Required action for red flag."""
    AUTO_REJECT = "AUTO_REJECT"
    ESCALATE = "ESCALATE"
    CONDITIONAL_PROCEED = "CONDITIONAL_PROCEED"
    MONITOR = "MONITOR"


@dataclass
class RedFlag:
    """Individual red flag with details."""
    code: str                   # Unique identifier (e.g., RF001)
    name: str
    category: RedFlagCategory
    severity: RedFlagSeverity
    action: RedFlagAction
    description: str
    trigger_value: Any          # The value that triggered this flag
    threshold: Any              # The threshold that was breached
    remediation: Optional[str] = None
    override_possible: bool = False

    def to_dict(self) -> Dict:
        return {
            "code": self.code,
            "name": self.name,
            "category": self.category.value,
            "severity": self.severity.value,
            "action": self.action.value,
            "description": self.description,
            "trigger_value": str(self.trigger_value),
            "threshold": str(self.threshold),
            "remediation": self.remediation,
            "override_possible": self.override_possible,
        }


@dataclass
class RedFlagResult:
    """Result of red flag evaluation."""
    has_critical_flags: bool
    should_auto_reject: bool
    flags: List[RedFlag]
    rejection_reason: Optional[str]
    escalation_required: bool
    flags_by_severity: Dict[str, List[RedFlag]]
    total_flag_count: int
    recommendation: str

    def to_dict(self) -> Dict:
        return {
            "has_critical_flags": self.has_critical_flags,
            "should_auto_reject": self.should_auto_reject,
            "flags": [f.to_dict() for f in self.flags],
            "rejection_reason": self.rejection_reason,
            "escalation_required": self.escalation_required,
            "flags_by_severity": {
                k: [f.to_dict() for f in v]
                for k, v in self.flags_by_severity.items()
            },
            "total_flag_count": self.total_flag_count,
            "recommendation": self.recommendation,
        }


# ─── Red Flag Checks ─────────────────────────────────────────────────────────

def _check_cibil_score(cibil_score: Optional[int]) -> Optional[RedFlag]:
    """Check CIBIL score thresholds."""
    if cibil_score is None:
        return None

    if cibil_score < 500:
        return RedFlag(
            code="RF001",
            name="CIBIL Score Critical",
            category=RedFlagCategory.CREDIT,
            severity=RedFlagSeverity.CRITICAL,
            action=RedFlagAction.AUTO_REJECT,
            description=f"CIBIL score {cibil_score} is below minimum threshold of 500",
            trigger_value=cibil_score,
            threshold=500,
            remediation="Borrower must improve credit score before reapplication",
            override_possible=False,
        )
    elif cibil_score < 600:
        return RedFlag(
            code="RF002",
            name="CIBIL Score Poor",
            category=RedFlagCategory.CREDIT,
            severity=RedFlagSeverity.HIGH,
            action=RedFlagAction.ESCALATE,
            description=f"CIBIL score {cibil_score} is below preferred threshold of 600",
            trigger_value=cibil_score,
            threshold=600,
            remediation="Require additional collateral or guarantor",
            override_possible=True,
        )
    elif cibil_score < 650:
        return RedFlag(
            code="RF003",
            name="CIBIL Score Below Average",
            category=RedFlagCategory.CREDIT,
            severity=RedFlagSeverity.MEDIUM,
            action=RedFlagAction.CONDITIONAL_PROCEED,
            description=f"CIBIL score {cibil_score} is below desirable threshold of 650",
            trigger_value=cibil_score,
            threshold=650,
            remediation="Consider higher interest rate or shorter tenure",
            override_possible=True,
        )
    return None


def _check_wilful_defaulter(is_wilful_defaulter: bool) -> Optional[RedFlag]:
    """Check wilful defaulter status."""
    if is_wilful_defaulter:
        return RedFlag(
            code="RF004",
            name="Wilful Defaulter",
            category=RedFlagCategory.CREDIT,
            severity=RedFlagSeverity.CRITICAL,
            action=RedFlagAction.AUTO_REJECT,
            description="Borrower/Director is tagged as Wilful Defaulter in RBI database",
            trigger_value=True,
            threshold="Not a wilful defaulter",
            remediation="No remediation possible - regulatory prohibition",
            override_possible=False,
        )
    return None


def _check_for_ratio(for_ratio: float) -> Optional[RedFlag]:
    """Check Fixed Obligation to Income Ratio."""
    if for_ratio > 60:
        return RedFlag(
            code="RF005",
            name="FOR Ratio Extreme",
            category=RedFlagCategory.FINANCIAL,
            severity=RedFlagSeverity.CRITICAL,
            action=RedFlagAction.AUTO_REJECT,
            description=f"FOR ratio {for_ratio:.1f}% exceeds critical threshold of 60%",
            trigger_value=f"{for_ratio:.1f}%",
            threshold="60%",
            remediation="Reduce existing debt or increase income substantially",
            override_possible=False,
        )
    elif for_ratio > 50:
        return RedFlag(
            code="RF006",
            name="FOR Ratio High",
            category=RedFlagCategory.FINANCIAL,
            severity=RedFlagSeverity.HIGH,
            action=RedFlagAction.ESCALATE,
            description=f"FOR ratio {for_ratio:.1f}% exceeds safe threshold of 50%",
            trigger_value=f"{for_ratio:.1f}%",
            threshold="50%",
            remediation="Consider reduced loan amount or extended tenure",
            override_possible=True,
        )
    elif for_ratio > 45:
        return RedFlag(
            code="RF007",
            name="FOR Ratio Elevated",
            category=RedFlagCategory.FINANCIAL,
            severity=RedFlagSeverity.MEDIUM,
            action=RedFlagAction.CONDITIONAL_PROCEED,
            description=f"FOR ratio {for_ratio:.1f}% is above comfortable threshold of 45%",
            trigger_value=f"{for_ratio:.1f}%",
            threshold="45%",
            remediation="Monitor debt servicing closely",
            override_possible=True,
        )
    return None


def _check_company_age(company_age_years: float, loan_amount_cr: float) -> Optional[RedFlag]:
    """Check company age vs loan amount."""
    if company_age_years < 1 and loan_amount_cr > 1:
        return RedFlag(
            code="RF008",
            name="Very New Company Large Loan",
            category=RedFlagCategory.OPERATIONAL,
            severity=RedFlagSeverity.HIGH,
            action=RedFlagAction.ESCALATE,
            description=f"Company age {company_age_years:.1f} years requesting Rs.{loan_amount_cr:.1f} Cr",
            trigger_value=f"{company_age_years:.1f} years",
            threshold="Minimum 1 year for loans > 1 Cr",
            remediation="Require strong promoter guarantee and collateral",
            override_possible=True,
        )
    elif company_age_years < 2 and loan_amount_cr > 5:
        return RedFlag(
            code="RF009",
            name="New Company Large Loan",
            category=RedFlagCategory.OPERATIONAL,
            severity=RedFlagSeverity.HIGH,
            action=RedFlagAction.ESCALATE,
            description=f"Company age {company_age_years:.1f} years requesting Rs.{loan_amount_cr:.1f} Cr",
            trigger_value=f"{company_age_years:.1f} years",
            threshold="Minimum 2 years for loans > 5 Cr",
            remediation="Enhanced due diligence and additional security required",
            override_possible=True,
        )
    return None


def _check_sector_negative_list(is_negative_list: bool, sector: str) -> Optional[RedFlag]:
    """Check if sector is on RBI negative list."""
    if is_negative_list:
        return RedFlag(
            code="RF010",
            name="Sector on Negative List",
            category=RedFlagCategory.REGULATORY,
            severity=RedFlagSeverity.CRITICAL,
            action=RedFlagAction.AUTO_REJECT,
            description=f"Sector '{sector}' is on RBI/Bank's negative lending list",
            trigger_value=sector,
            threshold="Not on negative list",
            remediation="No remediation - regulatory restriction",
            override_possible=False,
        )
    return None


def _check_mca_status(strike_off_notice: bool, company_status: str) -> Optional[RedFlag]:
    """Check MCA company status."""
    status_upper = company_status.upper() if company_status else ""

    if strike_off_notice or status_upper in ["STRUCK OFF", "DISSOLVED", "LIQUIDATION"]:
        return RedFlag(
            code="RF011",
            name="Company Status Invalid",
            category=RedFlagCategory.REGULATORY,
            severity=RedFlagSeverity.CRITICAL,
            action=RedFlagAction.AUTO_REJECT,
            description=f"Company status: {company_status or 'Strike-off notice issued'}",
            trigger_value=company_status or "Strike-off",
            threshold="Active status",
            remediation="Company must regularize status with ROC",
            override_possible=False,
        )
    elif status_upper in ["DORMANT", "INACTIVE"]:
        return RedFlag(
            code="RF012",
            name="Company Dormant/Inactive",
            category=RedFlagCategory.REGULATORY,
            severity=RedFlagSeverity.HIGH,
            action=RedFlagAction.ESCALATE,
            description=f"Company status: {company_status}",
            trigger_value=company_status,
            threshold="Active status",
            remediation="Company must file fresh ROC returns",
            override_possible=True,
        )
    return None


def _check_directors_disqualified(directors_disqualified: bool) -> Optional[RedFlag]:
    """Check if directors are disqualified."""
    if directors_disqualified:
        return RedFlag(
            code="RF013",
            name="Directors Disqualified",
            category=RedFlagCategory.REGULATORY,
            severity=RedFlagSeverity.CRITICAL,
            action=RedFlagAction.AUTO_REJECT,
            description="One or more directors disqualified under Section 164 of Companies Act",
            trigger_value=True,
            threshold="No disqualified directors",
            remediation="Replace disqualified directors and file compliance",
            override_possible=False,
        )
    return None


def _check_criminal_cases(has_criminal_cases: bool, case_details: str) -> Optional[RedFlag]:
    """Check for criminal cases against company/directors."""
    if has_criminal_cases:
        return RedFlag(
            code="RF014",
            name="Criminal Proceedings",
            category=RedFlagCategory.LEGAL,
            severity=RedFlagSeverity.CRITICAL,
            action=RedFlagAction.AUTO_REJECT,
            description=f"Criminal proceedings against company/directors: {case_details}",
            trigger_value=case_details,
            threshold="No criminal cases",
            remediation="Cannot proceed until cases are resolved",
            override_possible=False,
        )
    return None


def _check_serious_litigation(
    pending_cases: int,
    litigation_amount_cr: float,
    loan_amount_cr: float,
) -> Optional[RedFlag]:
    """Check for serious pending litigation."""
    if litigation_amount_cr > loan_amount_cr * 0.5:
        return RedFlag(
            code="RF015",
            name="Material Litigation",
            category=RedFlagCategory.LEGAL,
            severity=RedFlagSeverity.HIGH,
            action=RedFlagAction.ESCALATE,
            description=f"{pending_cases} cases with exposure Rs.{litigation_amount_cr:.1f} Cr (>{50}% of loan)",
            trigger_value=f"Rs.{litigation_amount_cr:.1f} Cr",
            threshold=f"<50% of loan amount (Rs.{loan_amount_cr*0.5:.1f} Cr)",
            remediation="Await case resolution or get indemnity from promoters",
            override_possible=True,
        )
    return None


def _check_gst_discrepancy(discrepancy_percent: float) -> Optional[RedFlag]:
    """Check GST return discrepancy (GSTR-3B vs GSTR-2A)."""
    if discrepancy_percent > 30:
        return RedFlag(
            code="RF016",
            name="GST Fraud Suspected",
            category=RedFlagCategory.FRAUD,
            severity=RedFlagSeverity.CRITICAL,
            action=RedFlagAction.AUTO_REJECT,
            description=f"GST discrepancy of {discrepancy_percent:.1f}% indicates revenue inflation",
            trigger_value=f"{discrepancy_percent:.1f}%",
            threshold="30%",
            remediation="Forensic audit required before any consideration",
            override_possible=False,
        )
    elif discrepancy_percent > 20:
        return RedFlag(
            code="RF017",
            name="GST Discrepancy High",
            category=RedFlagCategory.FRAUD,
            severity=RedFlagSeverity.HIGH,
            action=RedFlagAction.ESCALATE,
            description=f"GST discrepancy of {discrepancy_percent:.1f}% requires explanation",
            trigger_value=f"{discrepancy_percent:.1f}%",
            threshold="20%",
            remediation="Obtain reconciliation statement from borrower",
            override_possible=True,
        )
    elif discrepancy_percent > 10:
        return RedFlag(
            code="RF018",
            name="GST Discrepancy Moderate",
            category=RedFlagCategory.FRAUD,
            severity=RedFlagSeverity.MEDIUM,
            action=RedFlagAction.CONDITIONAL_PROCEED,
            description=f"GST discrepancy of {discrepancy_percent:.1f}% above normal variation",
            trigger_value=f"{discrepancy_percent:.1f}%",
            threshold="10%",
            remediation="Review with finance team",
            override_possible=True,
        )
    return None


def _check_negative_net_worth(net_worth: float) -> Optional[RedFlag]:
    """Check for negative net worth."""
    if net_worth < 0:
        return RedFlag(
            code="RF019",
            name="Negative Net Worth",
            category=RedFlagCategory.FINANCIAL,
            severity=RedFlagSeverity.CRITICAL,
            action=RedFlagAction.AUTO_REJECT,
            description=f"Net worth is negative (Rs.{net_worth:.2f} Cr) - company has eroded capital",
            trigger_value=f"Rs.{net_worth:.2f} Cr",
            threshold="Positive net worth",
            remediation="Capital infusion required before lending",
            override_possible=False,
        )
    return None


def _check_dscr_critical(dscr: float) -> Optional[RedFlag]:
    """Check for critically low DSCR."""
    if dscr <= 0:
        return RedFlag(
            code="RF020",
            name="DSCR Zero/Negative",
            category=RedFlagCategory.FINANCIAL,
            severity=RedFlagSeverity.CRITICAL,
            action=RedFlagAction.AUTO_REJECT,
            description=f"DSCR is {dscr:.2f} - no debt servicing capacity",
            trigger_value=f"{dscr:.2f}",
            threshold=">0",
            remediation="Company cannot service debt from operations",
            override_possible=False,
        )
    elif dscr < 0.8:
        return RedFlag(
            code="RF021",
            name="DSCR Critical",
            category=RedFlagCategory.FINANCIAL,
            severity=RedFlagSeverity.HIGH,
            action=RedFlagAction.ESCALATE,
            description=f"DSCR is {dscr:.2f} - severely constrained debt servicing",
            trigger_value=f"{dscr:.2f}",
            threshold="0.8",
            remediation="Require substantial improvement in cash flows",
            override_possible=True,
        )
    return None


def _check_nclt_status(company_under_cirp: bool, cirp_details: str = "") -> Optional[RedFlag]:
    """Check for NCLT insolvency proceedings."""
    if company_under_cirp:
        return RedFlag(
            code="RF022",
            name="Company under CIRP",
            category=RedFlagCategory.REGULATORY,
            severity=RedFlagSeverity.CRITICAL,
            action=RedFlagAction.AUTO_REJECT,
            description=f"Company under CIRP/IBC proceedings - {cirp_details}",
            trigger_value=cirp_details or "CIRP Initiated",
            threshold="Not under insolvency proceedings",
            remediation="Cannot lend to company under IBC proceedings",
            override_possible=False,
        )
    return None


def _check_hidden_emi(has_hidden_emi: bool, emi_count: int = 0, emi_amount: float = 0) -> Optional[RedFlag]:
    """Check for hidden EMI obligations."""
    if has_hidden_emi:
        return RedFlag(
            code="RF023",
            name="Hidden EMI Detected",
            category=RedFlagCategory.FRAUD,
            severity=RedFlagSeverity.HIGH,
            action=RedFlagAction.ESCALATE,
            description=f"Found {emi_count} undisclosed EMI payment(s) totaling Rs.{emi_amount:.2f} L/month",
            trigger_value=f"{emi_count} EMIs, Rs.{emi_amount:.2f} L",
            threshold="All EMIs disclosed",
            remediation="Obtain explanation and update debt schedule",
            override_possible=True,
        )
    return None


def _check_collateral_over_mortgaged(is_over_mortgaged: bool, existing_charges: float = 0, asset_value: float = 0) -> Optional[RedFlag]:
    """Check if collateral is over-mortgaged."""
    if is_over_mortgaged:
        ltv_percent = (existing_charges / asset_value * 100) if asset_value > 0 else 0
        return RedFlag(
            code="RF024",
            name="Collateral Over-Mortgaged",
            category=RedFlagCategory.FINANCIAL,
            severity=RedFlagSeverity.CRITICAL,
            action=RedFlagAction.AUTO_REJECT,
            description=f"Collateral already mortgaged for Rs.{existing_charges:.2f} Cr (LTV {ltv_percent:.0f}%)",
            trigger_value=f"Rs.{existing_charges:.2f} Cr",
            threshold=f"<75% of asset value (Rs.{asset_value:.2f} Cr)",
            remediation="Require fresh/additional collateral",
            override_possible=False,
        )
    return None


def _check_financial_reconciliation_fraud(reconciliation_variance: float) -> Optional[RedFlag]:
    """Check for financial reconciliation fraud (three-way mismatch)."""
    if reconciliation_variance > 40:
        return RedFlag(
            code="RF025",
            name="Financial Reconciliation Fraud",
            category=RedFlagCategory.FRAUD,
            severity=RedFlagSeverity.CRITICAL,
            action=RedFlagAction.AUTO_REJECT,
            description=f"Revenue variance of {reconciliation_variance:.1f}% across Books/GST/Bank - fraud suspected",
            trigger_value=f"{reconciliation_variance:.1f}%",
            threshold="40%",
            remediation="Forensic audit mandatory before any consideration",
            override_possible=False,
        )
    elif reconciliation_variance > 25:
        return RedFlag(
            code="RF025",
            name="Financial Reconciliation High Variance",
            category=RedFlagCategory.FRAUD,
            severity=RedFlagSeverity.HIGH,
            action=RedFlagAction.ESCALATE,
            description=f"Revenue variance of {reconciliation_variance:.1f}% indicates serious discrepancies",
            trigger_value=f"{reconciliation_variance:.1f}%",
            threshold="25%",
            remediation="Detailed reconciliation and explanation required",
            override_possible=True,
        )
    return None


def _check_auditor_resignation(auditor_changes_count: int, period_months: int = 12) -> Optional[RedFlag]:
    """Check for frequent auditor changes/resignations."""
    if auditor_changes_count > 2:
        return RedFlag(
            code="RF026",
            name="Frequent Auditor Changes",
            category=RedFlagCategory.FRAUD,
            severity=RedFlagSeverity.HIGH,
            action=RedFlagAction.ESCALATE,
            description=f"{auditor_changes_count} auditor changes in {period_months} months - governance concern",
            trigger_value=f"{auditor_changes_count} changes",
            threshold="≤2 changes in 12 months",
            remediation="Investigate reasons for auditor exits, obtain resignation letters",
            override_possible=True,
        )
    return None


def _check_gst_cancelled(gst_status: str) -> Optional[RedFlag]:
    """Check if GST registration is cancelled."""
    if gst_status and gst_status.upper() in ["CANCELLED", "SUSPENDED"]:
        return RedFlag(
            code="RF027",
            name="GST Cancelled",
            category=RedFlagCategory.REGULATORY,
            severity=RedFlagSeverity.CRITICAL,
            action=RedFlagAction.AUTO_REJECT,
            description=f"GST registration status: {gst_status} - business operations questionable",
            trigger_value=gst_status,
            threshold="Active GST",
            remediation="Company must restore GST registration before consideration",
            override_possible=False,
        )
    return None


def _check_cheque_bounces(bounce_count: int, period_months: int = 3) -> Optional[RedFlag]:
    """Check for cheque bounces."""
    if bounce_count > 5:
        return RedFlag(
            code="RF028",
            name="Multiple Cheque Bounces",
            category=RedFlagCategory.CREDIT,
            severity=RedFlagSeverity.CRITICAL,
            action=RedFlagAction.AUTO_REJECT,
            description=f"{bounce_count} cheque bounces in {period_months} months - severe liquidity crisis",
            trigger_value=f"{bounce_count} bounces",
            threshold="≤2 bounces in 3 months",
            remediation="Liquidity issue must be resolved before lending",
            override_possible=False,
        )
    elif bounce_count > 2:
        return RedFlag(
            code="RF028",
            name="Cheque Bounces Detected",
            category=RedFlagCategory.CREDIT,
            severity=RedFlagSeverity.HIGH,
            action=RedFlagAction.ESCALATE,
            description=f"{bounce_count} cheque bounces in {period_months} months - liquidity concern",
            trigger_value=f"{bounce_count} bounces",
            threshold="≤2 bounces",
            remediation="Verify reasons and assess current liquidity position",
            override_possible=True,
        )
    return None


def _check_promoter_default_history(defaulted_ventures_count: int, default_amount_cr: float = 0) -> Optional[RedFlag]:
    """Check promoter's default history in previous ventures."""
    if defaulted_ventures_count > 2:
        return RedFlag(
            code="RF029",
            name="Promoter Serial Defaulter",
            category=RedFlagCategory.CREDIT,
            severity=RedFlagSeverity.CRITICAL,
            action=RedFlagAction.AUTO_REJECT,
            description=f"Promoter has {defaulted_ventures_count} defaulted ventures (Rs.{default_amount_cr:.2f} Cr)",
            trigger_value=f"{defaulted_ventures_count} defaults",
            threshold="≤1 past default",
            remediation="Cannot lend to serial defaulters",
            override_possible=False,
        )
    elif defaulted_ventures_count > 0:
        return RedFlag(
            code="RF029",
            name="Promoter Default History",
            category=RedFlagCategory.CREDIT,
            severity=RedFlagSeverity.HIGH,
            action=RedFlagAction.ESCALATE,
            description=f"Promoter has {defaulted_ventures_count} past default(s)",
            trigger_value=f"{defaulted_ventures_count} default(s)",
            threshold="No past defaults",
            remediation="Enhanced due diligence on promoter track record required",
            override_possible=True,
        )
    return None


def _check_group_contagion_risk(has_contagion_risk: bool, stressed_entities: int = 0, group_debt_equity: float = 0) -> Optional[RedFlag]:
    """Check for group contagion risk."""
    if has_contagion_risk:
        return RedFlag(
            code="RF030",
            name="Group Contagion Risk",
            category=RedFlagCategory.FINANCIAL,
            severity=RedFlagSeverity.HIGH,
            action=RedFlagAction.ESCALATE,
            description=f"{stressed_entities} group entities stressed, Group D/E: {group_debt_equity:.2f}x - contagion risk",
            trigger_value=f"{stressed_entities} stressed entities",
            threshold="<2 stressed entities, D/E <3x",
            remediation="Ring-fence borrower from group, obtain independent guarantees",
            override_possible=True,
        )
    return None


# ─── Main Evaluation Function ────────────────────────────────────────────────

def evaluate_red_flags(
    # Credit parameters
    cibil_score: Optional[int] = None,
    is_wilful_defaulter: bool = False,
    # Financial parameters
    for_ratio: float = 0.0,
    net_worth: float = 0.0,
    dscr: float = 1.5,
    # Company parameters
    company_age_years: float = 5.0,
    loan_amount_cr: float = 1.0,
    company_status: str = "ACTIVE",
    strike_off_notice: bool = False,
    directors_disqualified: bool = False,
    # Sector parameters
    sector: str = "",
    is_negative_list: bool = False,
    # Legal parameters
    has_criminal_cases: bool = False,
    criminal_case_details: str = "",
    pending_cases: int = 0,
    litigation_amount_cr: float = 0.0,
    # Fraud parameters
    gst_discrepancy_percent: float = 0.0,
    # New parameters (RF022-RF030)
    company_under_cirp: bool = False,
    cirp_details: str = "",
    has_hidden_emi: bool = False,
    hidden_emi_count: int = 0,
    hidden_emi_amount: float = 0,
    collateral_over_mortgaged: bool = False,
    existing_charges_cr: float = 0,
    collateral_value_cr: float = 0,
    reconciliation_variance_pct: float = 0.0,
    auditor_changes_count: int = 0,
    gst_status: str = "Active",
    cheque_bounce_count: int = 0,
    promoter_defaulted_ventures: int = 0,
    promoter_default_amount_cr: float = 0,
    group_contagion_risk: bool = False,
    group_stressed_entities: int = 0,
    group_debt_equity: float = 0,
) -> RedFlagResult:
    """
    Evaluate all red flag conditions and return comprehensive result.

    This is the main function that checks all hard-stop conditions
    that credit managers use to gatekeep loan applications.

    Returns:
        RedFlagResult with all flags and recommended action
    """
    flags: List[RedFlag] = []

    # Run all checks and collect flags
    checks = [
        _check_cibil_score(cibil_score),
        _check_wilful_defaulter(is_wilful_defaulter),
        _check_for_ratio(for_ratio),
        _check_negative_net_worth(net_worth),
        _check_dscr_critical(dscr),
        _check_company_age(company_age_years, loan_amount_cr),
        _check_mca_status(strike_off_notice, company_status),
        _check_directors_disqualified(directors_disqualified),
        _check_sector_negative_list(is_negative_list, sector),
        _check_criminal_cases(has_criminal_cases, criminal_case_details),
        _check_serious_litigation(pending_cases, litigation_amount_cr, loan_amount_cr),
        _check_gst_discrepancy(gst_discrepancy_percent),
        # New checks (RF022-RF030)
        _check_nclt_status(company_under_cirp, cirp_details),
        _check_hidden_emi(has_hidden_emi, hidden_emi_count, hidden_emi_amount),
        _check_collateral_over_mortgaged(collateral_over_mortgaged, existing_charges_cr, collateral_value_cr),
        _check_financial_reconciliation_fraud(reconciliation_variance_pct),
        _check_auditor_resignation(auditor_changes_count),
        _check_gst_cancelled(gst_status),
        _check_cheque_bounces(cheque_bounce_count),
        _check_promoter_default_history(promoter_defaulted_ventures, promoter_default_amount_cr),
        _check_group_contagion_risk(group_contagion_risk, group_stressed_entities, group_debt_equity),
    ]

    flags = [f for f in checks if f is not None]

    # Categorize by severity
    flags_by_severity: Dict[str, List[RedFlag]] = {
        RedFlagSeverity.CRITICAL.value: [],
        RedFlagSeverity.HIGH.value: [],
        RedFlagSeverity.MEDIUM.value: [],
        RedFlagSeverity.LOW.value: [],
    }
    for flag in flags:
        flags_by_severity[flag.severity.value].append(flag)

    # Determine if auto-reject
    critical_flags = flags_by_severity[RedFlagSeverity.CRITICAL.value]
    has_critical = len(critical_flags) > 0
    should_reject = has_critical

    # Build rejection reason
    rejection_reason = None
    if should_reject:
        reasons = [f.description for f in critical_flags]
        rejection_reason = "; ".join(reasons[:3])  # Top 3 reasons

    # Determine if escalation required
    high_flags = flags_by_severity[RedFlagSeverity.HIGH.value]
    escalation_required = len(high_flags) > 0 and not should_reject

    # Build recommendation
    if should_reject:
        recommendation = f"AUTO-REJECT: {len(critical_flags)} critical red flag(s) detected"
    elif escalation_required:
        recommendation = f"ESCALATE: {len(high_flags)} high-severity flag(s) require management approval"
    elif len(flags) > 0:
        recommendation = f"CONDITIONAL PROCEED: {len(flags)} flag(s) noted for monitoring"
    else:
        recommendation = "CLEAR: No red flags detected"

    return RedFlagResult(
        has_critical_flags=has_critical,
        should_auto_reject=should_reject,
        flags=flags,
        rejection_reason=rejection_reason,
        escalation_required=escalation_required,
        flags_by_severity=flags_by_severity,
        total_flag_count=len(flags),
        recommendation=recommendation,
    )


# ─── Example Usage ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Example 1: Clean application
    result1 = evaluate_red_flags(
        cibil_score=750,
        for_ratio=35,
        net_worth=10.0,
        dscr=1.8,
        company_age_years=8,
        loan_amount_cr=5.0,
    )
    print("=" * 60)
    print("EXAMPLE 1: Clean Application")
    print(f"Recommendation: {result1.recommendation}")
    print(f"Flags: {result1.total_flag_count}")

    # Example 2: Risky application
    result2 = evaluate_red_flags(
        cibil_score=580,
        for_ratio=55,
        net_worth=2.0,
        dscr=1.1,
        company_age_years=1.5,
        loan_amount_cr=10.0,
        gst_discrepancy_percent=18,
    )
    print("\n" + "=" * 60)
    print("EXAMPLE 2: Risky Application")
    print(f"Recommendation: {result2.recommendation}")
    print(f"Flags: {result2.total_flag_count}")
    for flag in result2.flags:
        print(f"  - [{flag.severity.value}] {flag.name}: {flag.description}")

    # Example 3: Auto-reject application
    result3 = evaluate_red_flags(
        cibil_score=450,
        is_wilful_defaulter=True,
        for_ratio=65,
        net_worth=-5.0,
    )
    print("\n" + "=" * 60)
    print("EXAMPLE 3: Auto-Reject Application")
    print(f"Recommendation: {result3.recommendation}")
    print(f"Rejection Reason: {result3.rejection_reason}")
