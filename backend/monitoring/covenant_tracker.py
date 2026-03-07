"""
Covenant Tracker — Loan Covenant Compliance Monitoring

Tracks compliance with financial covenants imposed in the loan agreement:

1. Financial Covenants:
   - DSCR (Debt Service Coverage Ratio) ≥ 1.25x
   - Debt-to-Equity Ratio ≤ 2.0x
   - Current Ratio ≥ 1.5x
   - Net Worth ≥ threshold
   - Total Outside Liabilities (TOL) ≤ threshold
   - Interest Coverage Ratio ≥ 2.5x

2. Operational Covenants:
   - Maintain minimum turnover
   - No additional debt without consent
   - No asset sales beyond threshold
   - Dividend distribution restrictions

3. Governance Covenants:
   - Board composition requirements
   - Auditor appointment
   - Management continuity
   - Related party transaction limits

Breach Severity:
- MINOR: <10% deviation from covenant
- MODERATE: 10-25% deviation
- MAJOR: >25% deviation or critical covenant breach

Author: Credit Intelligence System
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class CovenantCategory(str, Enum):
    """Covenant categories."""
    FINANCIAL = "Financial"
    OPERATIONAL = "Operational"
    GOVERNANCE = "Governance"


class BreachSeverity(str, Enum):
    """Breach severity levels."""
    COMPLIANT = "COMPLIANT"
    MINOR = "MINOR"
    MODERATE = "MODERATE"
    MAJOR = "MAJOR"


@dataclass
class Covenant:
    """Loan covenant definition."""
    covenant_id: str
    name: str
    category: CovenantCategory
    threshold: float
    operator: str  # ">=", "<=", "="
    description: str
    measurement_frequency: str  # "Monthly", "Quarterly", "Annual"


@dataclass
class CovenantBreach:
    """Covenant breach record."""
    covenant: Covenant
    actual_value: float
    threshold_value: float
    deviation_pct: float
    severity: BreachSeverity
    breach_date: str
    remarks: str = ""


@dataclass
class CovenantTrackingResult:
    """Result from covenant tracking."""
    loan_account_number: str
    borrower_id: str
    tracking_date: str
    reporting_period: str  # e.g., "Q1FY24"
    
    total_covenants: int
    compliant_covenants: int
    breached_covenants: int
    
    breaches: List[CovenantBreach]
    compliance_score: float  # 0-100
    
    overall_status: str  # "Fully Compliant", "Minor Breaches", "Major Breaches"
    action_required: str
    waiver_needed: bool


async def track_covenant_compliance(
    loan_account: str,
    borrower_id: str,
    covenants: List[Covenant],
    financial_data: Dict[str, Any],
    reporting_period: str
) -> CovenantTrackingResult:
    """
    Track compliance with loan covenants.
    
    Args:
        loan_account: Loan account number
        borrower_id: Borrower identifier
        covenants: List of covenants to track
        financial_data: Latest financial data
        reporting_period: Reporting period (e.g., "Q1FY24")
        
    Returns:
        CovenantTrackingResult with compliance status
    """
    logger.info(f"📊 Tracking covenant compliance: {loan_account}, Period: {reporting_period}")
    
    breaches = []
    
    for covenant in covenants:
        # Calculate actual value based on covenant type
        actual_value = _calculate_covenant_metric(covenant, financial_data)
        
        # Check compliance
        is_compliant, deviation = _check_compliance(
            actual_value, 
            covenant.threshold, 
            covenant.operator
        )
        
        if not is_compliant:
            # Determine breach severity
            severity = _determine_breach_severity(deviation)
            
            breach = CovenantBreach(
                covenant=covenant,
                actual_value=actual_value,
                threshold_value=covenant.threshold,
                deviation_pct=deviation,
                severity=severity,
                breach_date=datetime.now().isoformat(),
                remarks=_generate_breach_remarks(covenant, actual_value, covenant.threshold)
            )
            breaches.append(breach)
    
    # Calculate compliance metrics
    total_covenants = len(covenants)
    breached_covenants = len(breaches)
    compliant_covenants = total_covenants - breached_covenants
    
    compliance_score = (compliant_covenants / total_covenants * 100) if total_covenants > 0 else 100
    
    # Determine overall status
    overall_status, action_required, waiver_needed = _determine_overall_status(breaches)
    
    logger.info(
        f"✅ Tracking complete | Covenants: {total_covenants} | "
        f"Compliant: {compliant_covenants} | Breached: {breached_covenants} | "
        f"Score: {compliance_score:.1f}%"
    )
    
    return CovenantTrackingResult(
        loan_account_number=loan_account,
        borrower_id=borrower_id,
        tracking_date=datetime.now().isoformat(),
        reporting_period=reporting_period,
        total_covenants=total_covenants,
        compliant_covenants=compliant_covenants,
        breached_covenants=breached_covenants,
        breaches=breaches,
        compliance_score=compliance_score,
        overall_status=overall_status,
        action_required=action_required,
        waiver_needed=waiver_needed
    )


def _calculate_covenant_metric(covenant: Covenant, financial_data: Dict[str, Any]) -> float:
    """Calculate the actual value for a covenant metric."""
    
    covenant_id = covenant.covenant_id
    
    # DSCR (Debt Service Coverage Ratio)
    if covenant_id == "DSCR":
        ebitda = financial_data.get('ebitda', 0)
        interest = financial_data.get('interest_expense', 0)
        principal = financial_data.get('principal_repayment', 0)
        debt_service = interest + principal
        return (ebitda / debt_service) if debt_service > 0 else 0
    
    # Debt-to-Equity Ratio
    elif covenant_id == "DEBT_EQUITY":
        total_debt = financial_data.get('total_debt', 0)
        equity = financial_data.get('shareholders_equity', 0)
        return (total_debt / equity) if equity > 0 else 999
    
    # Current Ratio
    elif covenant_id == "CURRENT_RATIO":
        current_assets = financial_data.get('current_assets', 0)
        current_liabilities = financial_data.get('current_liabilities', 0)
        return (current_assets / current_liabilities) if current_liabilities > 0 else 0
    
    # Net Worth
    elif covenant_id == "NET_WORTH":
        return financial_data.get('net_worth', 0)
    
    # Total Outside Liabilities
    elif covenant_id == "TOL":
        return financial_data.get('total_outside_liabilities', 0)
    
    # Interest Coverage Ratio
    elif covenant_id == "ICR":
        ebit = financial_data.get('ebit', 0)
        interest = financial_data.get('interest_expense', 0)
        return (ebit / interest) if interest > 0 else 0
    
    # Turnover (Revenue)
    elif covenant_id == "MIN_TURNOVER":
        return financial_data.get('revenue', 0)
    
    # Additional Debt
    elif covenant_id == "ADDITIONAL_DEBT":
        return financial_data.get('new_debt_incurred', 0)
    
    # Dividend Distribution
    elif covenant_id == "DIVIDEND":
        return financial_data.get('dividend_paid', 0)
    
    # Related Party Transactions
    elif covenant_id == "RPT_LIMIT":
        return financial_data.get('related_party_transactions', 0)
    
    # Default: return from financial_data directly
    return financial_data.get(covenant_id.lower(), 0)


def _check_compliance(actual: float, threshold: float, operator: str) -> tuple[bool, float]:
    """
    Check if covenant is compliant.
    
    Returns:
        (is_compliant, deviation_percentage)
    """
    is_compliant = False
    
    if operator == ">=":
        is_compliant = actual >= threshold
        deviation = ((threshold - actual) / threshold * 100) if threshold != 0 else 0
    elif operator == "<=":
        is_compliant = actual <= threshold
        deviation = ((actual - threshold) / threshold * 100) if threshold != 0 else 0
    elif operator == "=":
        is_compliant = abs(actual - threshold) < 0.01
        deviation = abs((actual - threshold) / threshold * 100) if threshold != 0 else 0
    else:
        deviation = 0
    
    return is_compliant, max(0, deviation)


def _determine_breach_severity(deviation_pct: float) -> BreachSeverity:
    """Determine breach severity based on deviation."""
    if deviation_pct > 25:
        return BreachSeverity.MAJOR
    elif deviation_pct > 10:
        return BreachSeverity.MODERATE
    else:
        return BreachSeverity.MINOR


def _generate_breach_remarks(covenant: Covenant, actual: float, threshold: float) -> str:
    """Generate remarks for covenant breach."""
    return (
        f"{covenant.name} breached: Actual {actual:.2f} vs Required {covenant.operator} {threshold:.2f}. "
        f"Immediate corrective action or waiver required."
    )


def _determine_overall_status(breaches: List[CovenantBreach]) -> tuple[str, str, bool]:
    """
    Determine overall covenant compliance status.
    
    Returns:
        (overall_status, action_required, waiver_needed)
    """
    if not breaches:
        return (
            "Fully Compliant",
            "Continue standard monitoring",
            False
        )
    
    major_count = sum(1 for b in breaches if b.severity == BreachSeverity.MAJOR)
    moderate_count = sum(1 for b in breaches if b.severity == BreachSeverity.MODERATE)
    minor_count = sum(1 for b in breaches if b.severity == BreachSeverity.MINOR)
    
    if major_count > 0:
        return (
            "Major Breaches",
            f"URGENT: {major_count} major breach(es). Obtain formal waiver or corrective action plan within 15 days.",
            True
        )
    elif moderate_count > 0:
        return (
            "Moderate Breaches",
            f"{moderate_count} moderate breach(es). Request explanation and remediation plan from borrower.",
            True
        )
    else:
        return (
            "Minor Breaches",
            f"{minor_count} minor deviation(s). Monitor next reporting period for improvement.",
            False
        )


# ─── Predefined Standard Covenants ──────────────────────────────────────────

STANDARD_COVENANTS = [
    Covenant(
        covenant_id="DSCR",
        name="Debt Service Coverage Ratio",
        category=CovenantCategory.FINANCIAL,
        threshold=1.25,
        operator=">=",
        description="EBITDA must be at least 1.25x the debt service (interest + principal)",
        measurement_frequency="Quarterly"
    ),
    Covenant(
        covenant_id="DEBT_EQUITY",
        name="Debt-to-Equity Ratio",
        category=CovenantCategory.FINANCIAL,
        threshold=2.0,
        operator="<=",
        description="Total debt must not exceed 2x shareholders' equity",
        measurement_frequency="Quarterly"
    ),
    Covenant(
        covenant_id="CURRENT_RATIO",
        name="Current Ratio",
        category=CovenantCategory.FINANCIAL,
        threshold=1.5,
        operator=">=",
        description="Current assets must be at least 1.5x current liabilities",
        measurement_frequency="Quarterly"
    ),
    Covenant(
        covenant_id="NET_WORTH",
        name="Minimum Net Worth",
        category=CovenantCategory.FINANCIAL,
        threshold=50_000_000,  # ₹5 Cr
        operator=">=",
        description="Net worth must be maintained above ₹5 crore",
        measurement_frequency="Annual"
    ),
    Covenant(
        covenant_id="ICR",
        name="Interest Coverage Ratio",
        category=CovenantCategory.FINANCIAL,
        threshold=2.5,
        operator=">=",
        description="EBIT must be at least 2.5x interest expense",
        measurement_frequency="Quarterly"
    ),
    Covenant(
        covenant_id="TOL",
        name="Total Outside Liabilities",
        category=CovenantCategory.FINANCIAL,
        threshold=100_000_000,  # ₹10 Cr
        operator="<=",
        description="Total borrowings from other lenders not to exceed ₹10 crore",
        measurement_frequency="Monthly"
    ),
]


# ─── Integration Example ─────────────────────────────────────────────────────

async def main_example():
    """Example usage."""
    
    # Scenario 1: Fully compliant borrower
    print("="*70)
    print("SCENARIO 1: Fully Compliant Borrower")
    print("="*70)
    
    financial_data_1 = {
        "ebitda": 15_000_000,
        "interest_expense": 2_000_000,
        "principal_repayment": 3_000_000,  # Debt service = 5M, DSCR = 15/5 = 3.0 ✓
        "total_debt": 40_000_000,
        "shareholders_equity": 30_000_000,  # D/E = 1.33 ✓
        "current_assets": 25_000_000,
        "current_liabilities": 12_000_000,  # Current Ratio = 2.08 ✓
        "net_worth": 60_000_000,  # ✓
        "ebit": 12_000_000,  # ICR = 12/2 = 6.0 ✓
        "total_outside_liabilities": 80_000_000,  # ✓
    }
    
    result1 = await track_covenant_compliance(
        loan_account="LA1234567",
        borrower_id="BRW001",
        covenants=STANDARD_COVENANTS,
        financial_data=financial_data_1,
        reporting_period="Q1FY24"
    )
    
    print(f"Overall Status: {result1.overall_status}")
    print(f"Compliance Score: {result1.compliance_score:.1f}%")
    print(f"Compliant: {result1.compliant_covenants}/{result1.total_covenants}")
    print(f"Breaches: {result1.breached_covenants}")
    print(f"Waiver Needed: {result1.waiver_needed}")
    
    # Scenario 2: Borrower with breaches
    print("\n" + "="*70)
    print("SCENARIO 2: Borrower with Covenant Breaches")
    print("="*70)
    
    financial_data_2 = {
        "ebitda": 5_000_000,
        "interest_expense": 3_000_000,
        "principal_repayment": 2_000_000,  # Debt service = 5M, DSCR = 1.0 ✗ (need 1.25)
        "total_debt": 80_000_000,
        "shareholders_equity": 25_000_000,  # D/E = 3.2 ✗ (limit 2.0)
        "current_assets": 15_000_000,
        "current_liabilities": 12_000_000,  # Current Ratio = 1.25 ✗ (need 1.5)
        "net_worth": 40_000_000,  # Net Worth = 4Cr ✗ (need 5Cr)
        "ebit": 6_000_000,  # ICR = 2.0 ✗ (need 2.5)
        "total_outside_liabilities": 120_000_000,  # ✗ (limit 10Cr)
    }
    
    result2 = await track_covenant_compliance(
        loan_account="LA7654321",
        borrower_id="BRW002",
        covenants=STANDARD_COVENANTS,
        financial_data=financial_data_2,
        reporting_period="Q2FY24"
    )
    
    print(f"Overall Status: {result2.overall_status}")
    print(f"Compliance Score: {result2.compliance_score:.1f}%")
    print(f"Compliant: {result2.compliant_covenants}/{result2.total_covenants}")
    print(f"Breaches: {result2.breached_covenants}")
    print(f"Waiver Needed: {result2.waiver_needed}")
    
    print(f"\n🚨 Covenant Breaches:")
    for breach in result2.breaches:
        print(f"  [{breach.severity.value}] {breach.covenant.name}")
        print(f"    Actual: {breach.actual_value:.2f} | Required: {breach.covenant.operator} {breach.threshold_value:.2f}")
        print(f"    Deviation: {breach.deviation_pct:.1f}%")
    
    print(f"\n📋 Action Required:")
    print(f"  {result2.action_required}")


if __name__ == "__main__":
    asyncio.run(main_example())
