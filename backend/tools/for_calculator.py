"""
Fixed Obligation to Income Ratio (FOR) Calculator for Intelli-Credit.

The FOR ratio measures a borrower's debt servicing capacity by comparing
total EMI obligations to monthly income. This is a critical gateway check
used by Indian banks.

Formula: FOR = (Total Monthly EMIs / Gross Monthly Income) × 100

Thresholds:
- FOR < 40%: HEALTHY - Comfortable debt servicing capacity
- FOR 40-50%: STRAINED - Moderate concern, review tenure
- FOR > 50%: OVER-LEVERAGED - High risk, auto-reject territory
- FOR > 60%: CRITICAL - Auto-reject per bank policy

Author: Credit Intelligence System
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class LoanDetails:
    """Details of an existing or proposed loan."""
    loan_type: str  # Term Loan/Working Capital/Credit Card/Personal/Home
    loan_amount: float  # In Crores
    tenure_months: int
    interest_rate: float  # Annual %
    emi: float  # Monthly EMI in Lakhs


@dataclass
class FORResult:
    """FOR calculation result."""
    gross_monthly_income: float  # In Lakhs
    existing_emis: List[LoanDetails]
    proposed_loan: LoanDetails
    existing_emi_total: float
    proposed_emi: float
    total_monthly_obligation: float
    for_ratio: float  # Percentage
    for_status: str  # HEALTHY/STRAINED/OVER-LEVERAGED/CRITICAL
    recommendation: str
    risk_level: str  # LOW/MEDIUM/HIGH/CRITICAL


def calculate_emi(
    principal: float,  # In Crores
    annual_interest_rate: float,  # %
    tenure_months: int,
) -> float:
    """
    Calculate EMI using standard formula.

    EMI = [P × R × (1+R)^N] / [(1+R)^N - 1]

    Returns: EMI in Lakhs
    """
    if tenure_months == 0 or annual_interest_rate == 0:
        return (principal * 100) / max(tenure_months, 1)  # Simple division

    principal_lakhs = principal * 100  # Convert Cr to Lakhs
    monthly_rate = annual_interest_rate / (12 * 100)  # Monthly rate as decimal

    # EMI formula
    numerator = principal_lakhs * monthly_rate * ((1 + monthly_rate) ** tenure_months)
    denominator = ((1 + monthly_rate) ** tenure_months) - 1

    if denominator == 0:
        return principal_lakhs / tenure_months

    emi = numerator / denominator
    return round(emi, 2)


def estimate_monthly_income_from_financials(
    annual_revenue: float,  # In Crores
    ebitda_margin: float,  # %
    cash_flow_from_operations: float,  # In Crores (annual)
    net_worth: float,  # In Crores
) -> float:
    """
    Estimate gross monthly income for a corporate entity.

    For companies, "income" is approximated as available cash flow
    for debt servicing. Multiple methods:

    1. Cash Flow Method: Monthly CF from operations
    2. EBITDA Method: Monthly EBITDA (proxy for cash generation)
    3. Net Worth Method: 1-2% of net worth per month (conservative)

    Returns: Estimated monthly income in Lakhs
    """
    # Method 1: Cash flow from operations (most reliable)
    if cash_flow_from_operations > 0:
        monthly_cf = (cash_flow_from_operations * 100) / 12  # Cr to Lakhs, annual to monthly
        return round(monthly_cf, 2)

    # Method 2: EBITDA-based estimation
    if annual_revenue > 0 and ebitda_margin > 0:
        annual_ebitda = annual_revenue * (ebitda_margin / 100)
        monthly_ebitda = (annual_ebitda * 100) / 12
        return round(monthly_ebitda * 0.7, 2)  # 70% of EBITDA available for debt

    # Method 3: Net worth-based conservative estimate
    if net_worth > 0:
        monthly_estimate = (net_worth * 100) * 0.015  # 1.5% of net worth per month
        return round(monthly_estimate, 2)

    return 0.0


def calculate_for(
    gross_monthly_income: float,  # In Lakhs
    existing_loans: Optional[List[LoanDetails]] = None,
    proposed_loan: Optional[LoanDetails] = None,
    # OR provide raw proposed loan details:
    proposed_loan_amount: Optional[float] = None,  # In Crores
    proposed_tenure: Optional[int] = None,
    proposed_interest_rate: Optional[float] = None,
) -> FORResult:
    """
    Calculate Fixed Obligation to Income Ratio.

    Args:
        gross_monthly_income: Monthly income in Lakhs
        existing_loans: List of existing loan details with EMIs
        proposed_loan: Proposed loan details (optional)
        proposed_loan_amount: If proposed_loan not provided, loan amount in Cr
        proposed_tenure: Tenure in months
        proposed_interest_rate: Annual interest rate %

    Returns:
        FORResult with recommendation
    """
    existing_loans = existing_loans or []

    # Calculate total existing EMI
    existing_emi_total = sum(loan.emi for loan in existing_loans)

    # Calculate proposed EMI if not provided
    if proposed_loan is None and proposed_loan_amount:
        proposed_emi = calculate_emi(
            proposed_loan_amount,
            proposed_interest_rate or 11.0,  # Default rate
            proposed_tenure or 60,  # Default 5 years
        )
        proposed_loan = LoanDetails(
            loan_type="Proposed Term Loan",
            loan_amount=proposed_loan_amount,
            tenure_months=proposed_tenure or 60,
            interest_rate=proposed_interest_rate or 11.0,
            emi=proposed_emi,
        )
    elif proposed_loan:
        proposed_emi = proposed_loan.emi
    else:
        proposed_emi = 0.0
        proposed_loan = LoanDetails(
            loan_type="N/A",
            loan_amount=0.0,
            tenure_months=0,
            interest_rate=0.0,
            emi=0.0,
        )

    # Total monthly obligation
    total_obligation = existing_emi_total + proposed_emi

    # Calculate FOR ratio
    if gross_monthly_income <= 0:
        for_ratio = 100.0  # Cannot calculate - worst case
        for_status = "UNKNOWN"
        recommendation = "Cannot calculate FOR - income data missing or zero"
        risk_level = "CRITICAL"
    else:
        for_ratio = (total_obligation / gross_monthly_income) * 100

        # Classify status
        if for_ratio < 40:
            for_status = "HEALTHY"
            recommendation = (
                f"Borrower has comfortable debt servicing capacity. "
                f"FOR of {for_ratio:.1f}% is well within safe limits."
            )
            risk_level = "LOW"
        elif for_ratio < 50:
            for_status = "STRAINED"
            recommendation = (
                f"FOR of {for_ratio:.1f}% indicates moderate debt burden. "
                f"Consider reducing loan amount or extending tenure to improve ratio."
            )
            risk_level = "MEDIUM"
        elif for_ratio < 60:
            for_status = "OVER-LEVERAGED"
            recommendation = (
                f"FOR of {for_ratio:.1f}% exceeds safe threshold. "
                f"Borrower is over-leveraged. High risk of default. "
                f"Recommend substantial loan amount reduction or reject."
            )
            risk_level = "HIGH"
        else:
            for_status = "CRITICAL"
            recommendation = (
                f"FOR of {for_ratio:.1f}% is critically high. "
                f"EMI burden exceeds 60% of income. AUTO-REJECT recommended. "
                f"Borrower cannot sustainably service this debt."
            )
            risk_level = "CRITICAL"

    return FORResult(
        gross_monthly_income=gross_monthly_income,
        existing_emis=existing_loans,
        proposed_loan=proposed_loan,
        existing_emi_total=round(existing_emi_total, 2),
        proposed_emi=round(proposed_emi, 2),
        total_monthly_obligation=round(total_obligation, 2),
        for_ratio=round(for_ratio, 2),
        for_status=for_status,
        recommendation=recommendation,
        risk_level=risk_level,
    )


def for_result_to_dict(result: FORResult) -> dict:
    """Convert FOR result to dictionary."""
    return {
        "gross_monthly_income_lakhs": result.gross_monthly_income,
        "existing_emi_total_lakhs": result.existing_emi_total,
        "proposed_emi_lakhs": result.proposed_emi,
        "total_monthly_obligation_lakhs": result.total_monthly_obligation,
        "for_ratio_percent": result.for_ratio,
        "for_status": result.for_status,
        "recommendation": result.recommendation,
        "risk_level": result.risk_level,
        "existing_loans_count": len(result.existing_emis),
    }


# ─── Example Usage ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("FOR CALCULATOR - Example 1: HEALTHY")
    print("=" * 60)

    # Scenario: Company with Rs.50L monthly income, existing 15L EMI, requesting 5Cr
    result1 = calculate_for(
        gross_monthly_income=50.0,  # 50 Lakhs
        existing_loans=[
            LoanDetails("Term Loan", 10.0, 60, 10.5, 12.0),
            LoanDetails("Working Capital", 2.0, 36, 11.0, 3.0),
        ],
        proposed_loan_amount=5.0,  # 5 Crores
        proposed_tenure=60,
        proposed_interest_rate=11.5,
    )

    print(f"Monthly Income: Rs.{result1.gross_monthly_income:.2f} L")
    print(f"Existing EMI: Rs.{result1.existing_emi_total:.2f} L")
    print(f"Proposed EMI: Rs.{result1.proposed_emi:.2f} L")
    print(f"Total Obligation: Rs.{result1.total_monthly_obligation:.2f} L")
    print(f"FOR Ratio: {result1.for_ratio:.2f}%")
    print(f"Status: {result1.for_status}")
    print(f"Risk Level: {result1.risk_level}")
    print(f"\nRecommendation: {result1.recommendation}")

    print("\n" + "=" * 60)
    print("FOR CALCULATOR - Example 2: OVER-LEVERAGED")
    print("=" * 60)

    result2 = calculate_for(
        gross_monthly_income=30.0,  # 30 Lakhs only
        existing_loans=[
            LoanDetails("Term Loan", 8.0, 48, 10.0, 10.0),
            LoanDetails("Working Capital", 3.0, 24, 12.0, 5.0),
        ],
        proposed_loan_amount=10.0,  # Requesting 10 Crores
        proposed_tenure=60,
        proposed_interest_rate=12.0,
    )

    print(f"Monthly Income: Rs.{result2.gross_monthly_income:.2f} L")
    print(f"Existing EMI: Rs.{result2.existing_emi_total:.2f} L")
    print(f"Proposed EMI: Rs.{result2.proposed_emi:.2f} L")
    print(f"Total Obligation: Rs.{result2.total_monthly_obligation:.2f} L")
    print(f"FOR Ratio: {result2.for_ratio:.2f}%")
    print(f"Status: {result2.for_status}")
    print(f"Risk Level: {result2.risk_level}")
    print(f"\nRecommendation: {result2.recommendation}")
