"""
Risk Matrix Module for Corporate Credit Assessment.

This module provides comprehensive risk factor analysis and company
risk profile computation based on multiple dimensions.

Factors considered:
- Company Profile (age, capital adequacy, status)
- Financial Health (DSCR, D/E, working capital)
- Credit History (CIBIL score, payment behavior)
- Legal/Compliance (MCA status, pending litigation)
- Sector Dynamics (industry health, regulatory outlook)
- Operational (capacity utilization, management quality)

Author: Credit Intelligence System
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, date
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class RiskLevel(str, Enum):
    """Risk level classification."""
    VERY_LOW = "VERY_LOW"
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    VERY_HIGH = "VERY_HIGH"
    CRITICAL = "CRITICAL"


class RiskCategory(str, Enum):
    """Categories of risk factors."""
    COMPANY_PROFILE = "COMPANY_PROFILE"
    FINANCIAL_HEALTH = "FINANCIAL_HEALTH"
    CREDIT_HISTORY = "CREDIT_HISTORY"
    LEGAL_COMPLIANCE = "LEGAL_COMPLIANCE"
    SECTOR_DYNAMICS = "SECTOR_DYNAMICS"
    OPERATIONAL = "OPERATIONAL"


@dataclass
class RiskFactor:
    """Individual risk factor with score and explanation."""
    name: str
    category: RiskCategory
    score: float  # 0-100, higher = riskier
    level: RiskLevel
    description: str
    data_source: str
    weight: float = 1.0  # Weight within category
    remediation: Optional[str] = None

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "category": self.category.value,
            "score": self.score,
            "level": self.level.value,
            "description": self.description,
            "data_source": self.data_source,
            "weight": self.weight,
            "remediation": self.remediation,
        }


@dataclass
class CompanyRiskProfile:
    """Complete risk profile for a company."""
    company_name: str
    assessment_date: str
    overall_risk_score: float
    overall_risk_level: RiskLevel
    risk_factors: List[RiskFactor]
    category_scores: Dict[str, float]
    key_concerns: List[str]
    mitigating_factors: List[str]
    recommendation_impact: str

    def to_dict(self) -> Dict:
        return {
            "company_name": self.company_name,
            "assessment_date": self.assessment_date,
            "overall_risk_score": self.overall_risk_score,
            "overall_risk_level": self.overall_risk_level.value,
            "risk_factors": [rf.to_dict() for rf in self.risk_factors],
            "category_scores": self.category_scores,
            "key_concerns": self.key_concerns,
            "mitigating_factors": self.mitigating_factors,
            "recommendation_impact": self.recommendation_impact,
        }


# ─── Risk Scoring Functions ──────────────────────────────────────────────────

def _score_to_level(score: float) -> RiskLevel:
    """Convert numeric risk score to risk level."""
    if score >= 80:
        return RiskLevel.CRITICAL
    elif score >= 65:
        return RiskLevel.VERY_HIGH
    elif score >= 50:
        return RiskLevel.HIGH
    elif score >= 35:
        return RiskLevel.MODERATE
    elif score >= 20:
        return RiskLevel.LOW
    else:
        return RiskLevel.VERY_LOW


def _assess_company_age_risk(
    incorporation_date: Optional[date],
    loan_amount_cr: float,
) -> RiskFactor:
    """Assess risk based on company age."""
    if incorporation_date is None:
        return RiskFactor(
            name="Company Age",
            category=RiskCategory.COMPANY_PROFILE,
            score=70,
            level=RiskLevel.HIGH,
            description="Incorporation date not available - cannot verify company history",
            data_source="MCA/Manual",
            remediation="Obtain certificate of incorporation from MCA",
        )

    today = date.today()
    age_years = (today - incorporation_date).days / 365.25

    # Risk increases for newer companies, especially with large loans
    loan_age_ratio = loan_amount_cr / max(age_years, 0.1)

    if age_years < 1:
        score = 85
        desc = f"Very new entity ({age_years:.1f} years). High risk for default."
    elif age_years < 2:
        score = 70 if loan_age_ratio > 5 else 55
        desc = f"New entity ({age_years:.1f} years). Limited track record."
    elif age_years < 3:
        score = 50 if loan_age_ratio > 5 else 40
        desc = f"Relatively new ({age_years:.1f} years). Building credit history."
    elif age_years < 5:
        score = 30 if loan_age_ratio > 8 else 25
        desc = f"Moderate track record ({age_years:.1f} years)."
    elif age_years < 10:
        score = 15
        desc = f"Established entity ({age_years:.1f} years)."
    else:
        score = 10
        desc = f"Well-established entity ({age_years:.1f} years)."

    return RiskFactor(
        name="Company Age",
        category=RiskCategory.COMPANY_PROFILE,
        score=score,
        level=_score_to_level(score),
        description=desc,
        data_source="MCA Certificate of Incorporation",
        weight=1.2 if age_years < 3 else 1.0,
        remediation="Consider additional collateral for newer entities" if age_years < 3 else None,
    )


def _assess_capital_adequacy_risk(
    authorized_capital: float,
    paid_up_capital: float,
    loan_amount_cr: float,
) -> RiskFactor:
    """Assess risk based on capital structure."""
    if paid_up_capital <= 0:
        return RiskFactor(
            name="Capital Adequacy",
            category=RiskCategory.COMPANY_PROFILE,
            score=80,
            level=RiskLevel.VERY_HIGH,
            description="Paid-up capital information not available",
            data_source="MCA/Annual Report",
            remediation="Obtain latest balance sheet with capital details",
        )

    # Loan to capital ratio
    loan_capital_ratio = loan_amount_cr / paid_up_capital

    # Capital utilization (paid-up vs authorized)
    capital_utilization = paid_up_capital / authorized_capital if authorized_capital > 0 else 0

    if loan_capital_ratio > 10:
        score = 75
        desc = f"Loan ({loan_amount_cr:.1f} Cr) is {loan_capital_ratio:.1f}x the paid-up capital. Over-leveraged."
    elif loan_capital_ratio > 5:
        score = 55
        desc = f"Loan is {loan_capital_ratio:.1f}x the paid-up capital. Elevated leverage."
    elif loan_capital_ratio > 2:
        score = 35
        desc = f"Loan is {loan_capital_ratio:.1f}x the paid-up capital. Moderate leverage."
    else:
        score = 15
        desc = f"Loan is {loan_capital_ratio:.1f}x the paid-up capital. Comfortable leverage."

    return RiskFactor(
        name="Capital Adequacy",
        category=RiskCategory.COMPANY_PROFILE,
        score=score,
        level=_score_to_level(score),
        description=desc,
        data_source="MCA Master Data / Balance Sheet",
        weight=1.0,
    )


def _assess_dscr_risk(dscr: float) -> RiskFactor:
    """Assess risk based on Debt Service Coverage Ratio."""
    if dscr <= 0:
        score = 90
        desc = "Negative or zero DSCR - company cannot service debt from operations"
        level = RiskLevel.CRITICAL
    elif dscr < 1.0:
        score = 80
        desc = f"DSCR {dscr:.2f}x < 1.0 - Insufficient cash flow to service debt"
        level = RiskLevel.VERY_HIGH
    elif dscr < 1.2:
        score = 60
        desc = f"DSCR {dscr:.2f}x - Marginal debt servicing capacity"
        level = RiskLevel.HIGH
    elif dscr < 1.5:
        score = 40
        desc = f"DSCR {dscr:.2f}x - Adequate debt servicing capacity"
        level = RiskLevel.MODERATE
    elif dscr < 2.0:
        score = 25
        desc = f"DSCR {dscr:.2f}x - Good debt servicing capacity"
        level = RiskLevel.LOW
    else:
        score = 10
        desc = f"DSCR {dscr:.2f}x - Strong debt servicing capacity"
        level = RiskLevel.VERY_LOW

    return RiskFactor(
        name="Debt Service Coverage",
        category=RiskCategory.FINANCIAL_HEALTH,
        score=score,
        level=level,
        description=desc,
        data_source="Financial Statements / ITR",
        weight=1.5,  # DSCR is critical
        remediation="Improve operating cash flows or reduce existing debt" if dscr < 1.2 else None,
    )


def _assess_debt_equity_risk(debt_to_equity: float) -> RiskFactor:
    """Assess risk based on Debt to Equity ratio."""
    if debt_to_equity < 0:
        score = 85
        desc = "Negative equity - company has eroded net worth"
        level = RiskLevel.CRITICAL
    elif debt_to_equity > 4.0:
        score = 75
        desc = f"D/E {debt_to_equity:.2f}x - Highly leveraged"
        level = RiskLevel.VERY_HIGH
    elif debt_to_equity > 2.5:
        score = 55
        desc = f"D/E {debt_to_equity:.2f}x - Above industry norms"
        level = RiskLevel.HIGH
    elif debt_to_equity > 1.5:
        score = 35
        desc = f"D/E {debt_to_equity:.2f}x - Moderate leverage"
        level = RiskLevel.MODERATE
    elif debt_to_equity > 0.5:
        score = 20
        desc = f"D/E {debt_to_equity:.2f}x - Conservative leverage"
        level = RiskLevel.LOW
    else:
        score = 10
        desc = f"D/E {debt_to_equity:.2f}x - Very conservative capital structure"
        level = RiskLevel.VERY_LOW

    return RiskFactor(
        name="Debt-Equity Ratio",
        category=RiskCategory.FINANCIAL_HEALTH,
        score=score,
        level=level,
        description=desc,
        data_source="Balance Sheet",
        weight=1.2,
    )


def _assess_cibil_risk(cibil_score: Optional[int], has_defaults: bool) -> RiskFactor:
    """Assess risk based on CIBIL score."""
    if cibil_score is None:
        return RiskFactor(
            name="Credit Bureau Score",
            category=RiskCategory.CREDIT_HISTORY,
            score=60,
            level=RiskLevel.HIGH,
            description="CIBIL score not available - cannot assess credit history",
            data_source="CIBIL/Credit Bureau",
            weight=1.5,
            remediation="Obtain commercial CIBIL report for company and directors",
        )

    base_score = 0
    if cibil_score < 500:
        base_score = 90
        desc = f"CIBIL {cibil_score} - Very poor credit history"
    elif cibil_score < 600:
        base_score = 75
        desc = f"CIBIL {cibil_score} - Poor credit history"
    elif cibil_score < 650:
        base_score = 55
        desc = f"CIBIL {cibil_score} - Below average credit"
    elif cibil_score < 700:
        base_score = 40
        desc = f"CIBIL {cibil_score} - Average credit history"
    elif cibil_score < 750:
        base_score = 25
        desc = f"CIBIL {cibil_score} - Good credit history"
    elif cibil_score < 800:
        base_score = 15
        desc = f"CIBIL {cibil_score} - Very good credit history"
    else:
        base_score = 5
        desc = f"CIBIL {cibil_score} - Excellent credit history"

    # Add penalty for existing defaults
    if has_defaults:
        base_score = min(base_score + 25, 95)
        desc += " (History of defaults detected)"

    return RiskFactor(
        name="Credit Bureau Score",
        category=RiskCategory.CREDIT_HISTORY,
        score=base_score,
        level=_score_to_level(base_score),
        description=desc,
        data_source="CIBIL Commercial Report",
        weight=1.8 if base_score > 50 else 1.2,  # Higher weight for poor scores
        remediation="Clear outstanding dues and improve payment behavior" if base_score > 50 else None,
    )


def _assess_legal_risk(
    pending_cases: int,
    case_amount_cr: float,
    strike_off_notice: bool,
    directors_disqualified: bool,
) -> RiskFactor:
    """Assess legal and compliance risk."""
    score = 0
    issues: List[str] = []

    if strike_off_notice:
        score += 50
        issues.append("Strike-off notice issued by ROC")

    if directors_disqualified:
        score += 40
        issues.append("Directors disqualified under Companies Act")

    if pending_cases > 0:
        if case_amount_cr > 10:
            score += 35
            issues.append(f"{pending_cases} pending cases worth Rs.{case_amount_cr:.1f} Cr")
        elif case_amount_cr > 1:
            score += 20
            issues.append(f"{pending_cases} pending cases worth Rs.{case_amount_cr:.1f} Cr")
        else:
            score += 10
            issues.append(f"{pending_cases} minor pending cases")

    score = min(score, 100)

    if not issues:
        desc = "No legal issues or compliance concerns identified"
        score = 5
    else:
        desc = "; ".join(issues)

    return RiskFactor(
        name="Legal & Compliance",
        category=RiskCategory.LEGAL_COMPLIANCE,
        score=score,
        level=_score_to_level(score),
        description=desc,
        data_source="MCA Portal / eCourts / Web Research",
        weight=1.5 if score > 30 else 1.0,
        remediation="Resolve pending litigation before loan sanction" if score > 30 else None,
    )


def _assess_sector_risk(
    sector_outlook: str,
    is_negative_list: bool,
    npa_ratio_sector: float,
) -> RiskFactor:
    """Assess sector/industry risk."""
    sector_upper = sector_outlook.upper() if sector_outlook else "NEUTRAL"

    if is_negative_list:
        score = 90
        desc = "Sector on RBI negative list - lending restricted"
        level = RiskLevel.CRITICAL
    elif sector_upper in ["DECLINING", "NEGATIVE", "STRESSED"]:
        score = 65 if npa_ratio_sector > 5 else 55
        desc = f"Sector outlook: {sector_outlook}. Industry facing headwinds."
    elif sector_upper in ["NEUTRAL", "STABLE"]:
        score = 30
        desc = f"Sector outlook: {sector_outlook}. Stable industry environment."
    elif sector_upper in ["POSITIVE", "GROWING"]:
        score = 15
        desc = f"Sector outlook: {sector_outlook}. Favorable industry conditions."
    else:
        score = 40
        desc = f"Sector outlook unclear: {sector_outlook}"

    # Sector NPA adjustment
    if npa_ratio_sector > 10:
        score = min(score + 20, 95)
        desc += f" Sector NPA: {npa_ratio_sector:.1f}% (elevated)"
    elif npa_ratio_sector > 5:
        score = min(score + 10, 90)
        desc += f" Sector NPA: {npa_ratio_sector:.1f}%"

    return RiskFactor(
        name="Sector/Industry Risk",
        category=RiskCategory.SECTOR_DYNAMICS,
        score=score,
        level=_score_to_level(score),
        description=desc,
        data_source="RBI Data / Industry Reports / IBEF",
        weight=1.3 if score > 50 else 1.0,
    )


def _assess_working_capital_risk(
    current_ratio: float,
    quick_ratio: float,
) -> RiskFactor:
    """Assess working capital and liquidity risk."""
    score = 0

    # Current ratio assessment
    if current_ratio < 1.0:
        score += 40
        cr_comment = f"Current ratio {current_ratio:.2f} < 1.0 (liquidity stress)"
    elif current_ratio < 1.3:
        score += 25
        cr_comment = f"Current ratio {current_ratio:.2f} (marginal liquidity)"
    elif current_ratio < 1.5:
        score += 15
        cr_comment = f"Current ratio {current_ratio:.2f} (adequate)"
    else:
        score += 5
        cr_comment = f"Current ratio {current_ratio:.2f} (healthy)"

    # Quick ratio assessment
    if quick_ratio < 0.8:
        score += 35
        qr_comment = f"Quick ratio {quick_ratio:.2f} < 0.8 (low liquidity)"
    elif quick_ratio < 1.0:
        score += 20
        qr_comment = f"Quick ratio {quick_ratio:.2f} (acceptable)"
    else:
        score += 5
        qr_comment = f"Quick ratio {quick_ratio:.2f} (good)"

    desc = f"{cr_comment}. {qr_comment}."

    return RiskFactor(
        name="Working Capital & Liquidity",
        category=RiskCategory.FINANCIAL_HEALTH,
        score=min(score, 100),
        level=_score_to_level(score),
        description=desc,
        data_source="Balance Sheet / Bank Statements",
        weight=1.1,
        remediation="Improve receivables collection and manage payables" if score > 50 else None,
    )


# ─── Main Risk Profile Function ──────────────────────────────────────────────

def compute_company_risk_profile(
    company_name: str,
    incorporation_date: Optional[date] = None,
    loan_amount_cr: float = 1.0,
    authorized_capital: float = 0.0,
    paid_up_capital: float = 0.0,
    dscr: float = 1.5,
    debt_to_equity: float = 1.0,
    cibil_score: Optional[int] = None,
    has_defaults: bool = False,
    pending_cases: int = 0,
    case_amount_cr: float = 0.0,
    strike_off_notice: bool = False,
    directors_disqualified: bool = False,
    sector_outlook: str = "NEUTRAL",
    is_negative_list: bool = False,
    npa_ratio_sector: float = 2.0,
    current_ratio: float = 1.5,
    quick_ratio: float = 1.0,
) -> CompanyRiskProfile:
    """
    Compute comprehensive risk profile for a company.

    This function evaluates all risk dimensions and produces a holistic
    risk assessment with detailed factor breakdown.

    Returns:
        CompanyRiskProfile with all risk factors and overall assessment
    """
    risk_factors: List[RiskFactor] = []

    # Assess each risk dimension
    risk_factors.append(_assess_company_age_risk(incorporation_date, loan_amount_cr))
    risk_factors.append(_assess_capital_adequacy_risk(authorized_capital, paid_up_capital, loan_amount_cr))
    risk_factors.append(_assess_dscr_risk(dscr))
    risk_factors.append(_assess_debt_equity_risk(debt_to_equity))
    risk_factors.append(_assess_cibil_risk(cibil_score, has_defaults))
    risk_factors.append(_assess_legal_risk(pending_cases, case_amount_cr, strike_off_notice, directors_disqualified))
    risk_factors.append(_assess_sector_risk(sector_outlook, is_negative_list, npa_ratio_sector))
    risk_factors.append(_assess_working_capital_risk(current_ratio, quick_ratio))

    # Compute category scores (weighted average within category)
    category_scores: Dict[str, float] = {}
    for category in RiskCategory:
        category_factors = [rf for rf in risk_factors if rf.category == category]
        if category_factors:
            total_weight = sum(rf.weight for rf in category_factors)
            weighted_sum = sum(rf.score * rf.weight for rf in category_factors)
            category_scores[category.value] = round(weighted_sum / total_weight, 2)

    # Compute overall risk score (weighted average of categories)
    category_weights = {
        RiskCategory.COMPANY_PROFILE.value: 0.15,
        RiskCategory.FINANCIAL_HEALTH.value: 0.25,
        RiskCategory.CREDIT_HISTORY.value: 0.25,
        RiskCategory.LEGAL_COMPLIANCE.value: 0.15,
        RiskCategory.SECTOR_DYNAMICS.value: 0.10,
        RiskCategory.OPERATIONAL.value: 0.10,
    }

    overall_score = 0.0
    total_weight = 0.0
    for cat, score in category_scores.items():
        weight = category_weights.get(cat, 0.1)
        overall_score += score * weight
        total_weight += weight

    overall_score = round(overall_score / total_weight if total_weight > 0 else 50, 2)

    # Identify key concerns and mitigating factors
    key_concerns = [
        rf.description for rf in risk_factors
        if rf.level in [RiskLevel.HIGH, RiskLevel.VERY_HIGH, RiskLevel.CRITICAL]
    ]

    mitigating_factors = [
        rf.description for rf in risk_factors
        if rf.level in [RiskLevel.VERY_LOW, RiskLevel.LOW] and rf.score < 20
    ]

    # Determine recommendation impact
    if overall_score >= 70:
        recommendation_impact = "HIGH RISK - Recommend REJECT or require substantial additional security"
    elif overall_score >= 50:
        recommendation_impact = "ELEVATED RISK - Recommend CONDITIONAL APPROVE with enhanced monitoring"
    elif overall_score >= 30:
        recommendation_impact = "MODERATE RISK - Standard terms with appropriate covenants"
    else:
        recommendation_impact = "LOW RISK - Favorable terms possible"

    return CompanyRiskProfile(
        company_name=company_name,
        assessment_date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        overall_risk_score=overall_score,
        overall_risk_level=_score_to_level(overall_score),
        risk_factors=risk_factors,
        category_scores=category_scores,
        key_concerns=key_concerns[:5],  # Top 5 concerns
        mitigating_factors=mitigating_factors[:3],  # Top 3 positives
        recommendation_impact=recommendation_impact,
    )


# ─── Example Usage ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    from datetime import date, timedelta

    # Example: Assess a moderately risky company
    profile = compute_company_risk_profile(
        company_name="ABC Manufacturing Pvt Ltd",
        incorporation_date=date.today() - timedelta(days=3*365),  # 3 years old
        loan_amount_cr=10.0,
        authorized_capital=5.0,
        paid_up_capital=3.0,
        dscr=1.3,
        debt_to_equity=2.2,
        cibil_score=680,
        has_defaults=False,
        pending_cases=1,
        case_amount_cr=0.5,
        sector_outlook="STABLE",
        current_ratio=1.2,
        quick_ratio=0.9,
    )

    print("=" * 60)
    print(f"COMPANY RISK PROFILE: {profile.company_name}")
    print(f"Assessment Date: {profile.assessment_date}")
    print("=" * 60)
    print(f"\nOVERALL RISK: {profile.overall_risk_level.value} ({profile.overall_risk_score}/100)")
    print(f"\nRECOMMENDATION: {profile.recommendation_impact}")

    print("\n--- Category Scores ---")
    for cat, score in profile.category_scores.items():
        print(f"  {cat}: {score}/100")

    print("\n--- Key Concerns ---")
    for concern in profile.key_concerns:
        print(f"  - {concern}")

    print("\n--- Mitigating Factors ---")
    for factor in profile.mitigating_factors:
        print(f"  + {factor}")
