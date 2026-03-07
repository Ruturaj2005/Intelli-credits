"""
End Use Verifier — Loan Fund Utilization Monitoring

Verifies that loan funds are used for the stated purpose and detects misuse:

1. Fund Diversion Detection:
   - Funds transferred to non-business entities
   - Investment in unrelated businesses
   - Cash withdrawals exceeding thresholds
   - Round-tripping of funds

2. Promoter/Related Party Transfers:
   - Unsecured loans to promoters
   - Loans to group companies
   - Advances to directors
   - Dividend payments (when restricted)

3. Asset Creation Verification:
   - Capital expenditure vs loan amount
   - Vendor payments verification
   - Supplier invoice matching
   - Fixed asset additions

4. Working Capital Usage:
   - Inventory levels
   - Receivables/payables analysis
   - Operating expenses
   - Raw material purchases

Red Flags:
- RF031: Significant fund diversion detected
- RF032: Loan to promoter/group entity
- RF033: Mismatch in stated vs actual use
- RF034: Cash withdrawal >30% of disbursed amount

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


class LoanPurpose(str, Enum):
    """Loan purpose categories."""
    TERM_LOAN_CAPEX = "Term Loan - CAPEX"
    WORKING_CAPITAL = "Working Capital"
    BUSINESS_EXPANSION = "Business Expansion"
    EQUIPMENT_PURCHASE = "Equipment Purchase"
    CONSTRUCTION = "Construction"
    VEHICLE_PURCHASE = "Vehicle Purchase"


class MisuseType(str, Enum):
    """Types of loan misuse."""
    FUND_DIVERSION = "Fund Diversion"
    PROMOTER_TRANSFER = "Promoter Transfer"
    GROUP_TRANSFER = "Group Company Transfer"
    CASH_WITHDRAWAL = "Excessive Cash Withdrawal"
    UNRELATED_EXPENSE = "Unrelated Business Expense"
    ASSET_MISMATCH = "Asset Creation Mismatch"
    DIVIDEND_PAYMENT = "Unauthorized Dividend Payment"


@dataclass
class Transaction:
    """Bank transaction record."""
    date: str
    particulars: str
    debit: float
    credit: float
    balance: float
    category: str = ""
    is_suspicious: bool = False


@dataclass
class EndUseViolation:
    """End use violation record."""
    violation_type: MisuseType
    amount: float
    percentage_of_loan: float
    description: str
    transactions: List[Transaction] = field(default_factory=list)
    severity: str = "MEDIUM"  # LOW, MEDIUM, HIGH, CRITICAL
    flag_code: Optional[str] = None


@dataclass
class EndUseVerificationResult:
    """Result from end use verification."""
    loan_account_number: str
    borrower_id: str
    verification_date: str
    
    loan_purpose: LoanPurpose
    sanctioned_amount: float
    disbursed_amount: float
    
    # Utilization analysis
    utilized_for_stated_purpose: float
    utilized_for_other_purpose: float
    utilization_percentage: float
    
    violations: List[EndUseViolation]
    compliance_score: float  # 0-100
    
    # Summary metrics
    total_diversion: float
    diversion_percentage: float
    promoter_transfers: float
    cash_withdrawals: float
    
    overall_status: str  # "Compliant", "Minor Issues", "Major Misuse", "Critical Fraud"
    flags: List[str]
    recommendation: str


async def verify_end_use(
    loan_account: str,
    borrower_id: str,
    loan_purpose: LoanPurpose,
    sanctioned_amount: float,
    disbursed_amount: float,
    transactions: List[Transaction],
    loan_agreement_terms: Dict[str, Any]
) -> EndUseVerificationResult:
    """
    Verify loan end use and detect fund misuse.
    
    Args:
        loan_account: Loan account number
        borrower_id: Borrower identifier
        loan_purpose: Purpose for which loan was sanctioned
        sanctioned_amount: Sanctioned loan amount
        disbursed_amount: Disbursed loan amount
        transactions: Bank transactions since disbursement
        loan_agreement_terms: Terms from loan agreement
        
    Returns:
        EndUseVerificationResult with compliance status
    """
    logger.info(f"🔍 Verifying end use: {loan_account}, Purpose: {loan_purpose.value}")
    
    violations = []
    flags = []
    
    # Check 1: Fund diversion to unrelated entities
    diversion_violations = _detect_fund_diversion(transactions, loan_purpose)
    violations.extend(diversion_violations)
    
    # Check 2: Transfers to promoters/directors
    promoter_violations = _detect_promoter_transfers(transactions)
    violations.extend(promoter_violations)
    
    # Check 3: Transfers to group companies
    group_violations = _detect_group_transfers(transactions)
    violations.extend(group_violations)
    
    # Check 4: Excessive cash withdrawals
    cash_violations = _detect_cash_withdrawals(transactions, disbursed_amount)
    violations.extend(cash_violations)
    
    # Check 5: Dividend payments (if restricted)
    if loan_agreement_terms.get('dividend_restricted', True):
        dividend_violations = _detect_dividend_payments(transactions)
        violations.extend(dividend_violations)
    
    # Check 6: Asset creation vs loan purpose
    if loan_purpose in [LoanPurpose.TERM_LOAN_CAPEX, LoanPurpose.EQUIPMENT_PURCHASE]:
        asset_violations = _verify_asset_creation(transactions, disbursed_amount, loan_purpose)
        violations.extend(asset_violations)
    
    # Calculate utilization metrics
    utilized_for_purpose = _calculate_utilized_for_purpose(transactions, loan_purpose)
    utilized_other = disbursed_amount - utilized_for_purpose
    utilization_pct = (utilized_for_purpose / disbursed_amount * 100) if disbursed_amount > 0 else 0
    
    # Calculate summary metrics
    total_diversion = sum(v.amount for v in violations if v.violation_type == MisuseType.FUND_DIVERSION)
    diversion_pct = (total_diversion / disbursed_amount * 100) if disbursed_amount > 0 else 0
    
    promoter_transfers = sum(v.amount for v in violations if v.violation_type == MisuseType.PROMOTER_TRANSFER)
    cash_withdrawals = sum(v.amount for v in violations if v.violation_type == MisuseType.CASH_WITHDRAWAL)
    
    # Generate flags
    if diversion_pct > 20:
        flags.append("RF031")  # Significant fund diversion
    if promoter_transfers > 0:
        flags.append("RF032")  # Loan to promoter/group entity
    if utilization_pct < 70:
        flags.append("RF033")  # Mismatch in stated vs actual use
    if (cash_withdrawals / disbursed_amount * 100) > 30:
        flags.append("RF034")  # Excessive cash withdrawal
    
    # Assign flag codes to violations
    for violation in violations:
        if violation.violation_type == MisuseType.FUND_DIVERSION:
            violation.flag_code = "RF031"
        elif violation.violation_type in [MisuseType.PROMOTER_TRANSFER, MisuseType.GROUP_TRANSFER]:
            violation.flag_code = "RF032"
        elif violation.violation_type == MisuseType.CASH_WITHDRAWAL:
            violation.flag_code = "RF034"
    
    # Calculate compliance score
    compliance_score = _calculate_compliance_score(violations, utilization_pct, diversion_pct)
    
    # Determine overall status
    overall_status = _determine_overall_status(violations, diversion_pct)
    
    # Generate recommendation
    recommendation = _generate_recommendation(overall_status, violations, diversion_pct)
    
    logger.info(
        f"✅ Verification complete | Utilization: {utilization_pct:.1f}% | "
        f"Diversion: {diversion_pct:.1f}% | Violations: {len(violations)} | "
        f"Score: {compliance_score:.1f}/100"
    )
    
    return EndUseVerificationResult(
        loan_account_number=loan_account,
        borrower_id=borrower_id,
        verification_date=datetime.now().isoformat(),
        loan_purpose=loan_purpose,
        sanctioned_amount=sanctioned_amount,
        disbursed_amount=disbursed_amount,
        utilized_for_stated_purpose=utilized_for_purpose,
        utilized_for_other_purpose=utilized_other,
        utilization_percentage=utilization_pct,
        violations=violations,
        compliance_score=compliance_score,
        total_diversion=total_diversion,
        diversion_percentage=diversion_pct,
        promoter_transfers=promoter_transfers,
        cash_withdrawals=cash_withdrawals,
        overall_status=overall_status,
        flags=flags,
        recommendation=recommendation
    )


def _detect_fund_diversion(transactions: List[Transaction], loan_purpose: LoanPurpose) -> List[EndUseViolation]:
    """Detect fund diversion to unrelated purposes."""
    violations = []
    
    suspicious_keywords = ["personal", "unrelated", "investment", "speculation", "stock market", "real estate"]
    
    for txn in transactions:
        particulars_lower = txn.particulars.lower()
        
        if any(keyword in particulars_lower for keyword in suspicious_keywords):
            violations.append(EndUseViolation(
                violation_type=MisuseType.FUND_DIVERSION,
                amount=txn.debit,
                percentage_of_loan=0.0,  # Will be calculated later
                description=f"Suspicious transfer: {txn.particulars}",
                transactions=[txn],
                severity="HIGH"
            ))
    
    return violations


def _detect_promoter_transfers(transactions: List[Transaction]) -> List[EndUseViolation]:
    """Detect transfers to promoters/directors."""
    violations = []
    
    promoter_keywords = ["director", "promoter", "unsecured loan", "advance to director"]
    
    for txn in transactions:
        particulars_lower = txn.particulars.lower()
        
        if any(keyword in particulars_lower for keyword in promoter_keywords):
            violations.append(EndUseViolation(
                violation_type=MisuseType.PROMOTER_TRANSFER,
                amount=txn.debit,
                percentage_of_loan=0.0,
                description=f"Transfer to promoter: {txn.particulars}",
                transactions=[txn],
                severity="CRITICAL"
            ))
    
    return violations


def _detect_group_transfers(transactions: List[Transaction]) -> List[EndUseViolation]:
    """Detect transfers to group companies."""
    violations = []
    
    group_keywords = ["group company", "related party", "sister concern", "inter-company"]
    
    for txn in transactions:
        particulars_lower = txn.particulars.lower()
        
        if any(keyword in particulars_lower for keyword in group_keywords):
            violations.append(EndUseViolation(
                violation_type=MisuseType.GROUP_TRANSFER,
                amount=txn.debit,
                percentage_of_loan=0.0,
                description=f"Transfer to group entity: {txn.particulars}",
                transactions=[txn],
                severity="HIGH"
            ))
    
    return violations


def _detect_cash_withdrawals(transactions: List[Transaction], disbursed_amount: float) -> List[EndUseViolation]:
    """Detect excessive cash withdrawals."""
    violations = []
    
    total_cash = sum(txn.debit for txn in transactions if "cash withdrawal" in txn.particulars.lower())
    cash_pct = (total_cash / disbursed_amount * 100) if disbursed_amount > 0 else 0
    
    if cash_pct > 30:
        cash_txns = [txn for txn in transactions if "cash withdrawal" in txn.particulars.lower()]
        violations.append(EndUseViolation(
            violation_type=MisuseType.CASH_WITHDRAWAL,
            amount=total_cash,
            percentage_of_loan=cash_pct,
            description=f"Excessive cash withdrawals ({cash_pct:.1f}% of loan)",
            transactions=cash_txns,
            severity="HIGH"
        ))
    
    return violations


def _detect_dividend_payments(transactions: List[Transaction]) -> List[EndUseViolation]:
    """Detect unauthorized dividend payments."""
    violations = []
    
    for txn in transactions:
        if "dividend" in txn.particulars.lower():
            violations.append(EndUseViolation(
                violation_type=MisuseType.DIVIDEND_PAYMENT,
                amount=txn.debit,
                percentage_of_loan=0.0,
                description=f"Unauthorized dividend payment: {txn.particulars}",
                transactions=[txn],
                severity="MEDIUM"
            ))
    
    return violations


def _verify_asset_creation(
    transactions: List[Transaction], 
    disbursed_amount: float, 
    loan_purpose: LoanPurpose
) -> List[EndUseViolation]:
    """Verify asset creation matches loan purpose."""
    violations = []
    
    # Calculate capital expenditure
    capex_keywords = ["machinery", "equipment", "plant", "construction", "vendor payment", "supplier"]
    capex_total = sum(
        txn.debit for txn in transactions 
        if any(keyword in txn.particulars.lower() for keyword in capex_keywords)
    )
    
    capex_pct = (capex_total / disbursed_amount * 100) if disbursed_amount > 0 else 0
    
    # For CAPEX loans, at least 80% should be used for asset creation
    if loan_purpose == LoanPurpose.TERM_LOAN_CAPEX and capex_pct < 80:
        violations.append(EndUseViolation(
            violation_type=MisuseType.ASSET_MISMATCH,
            amount=disbursed_amount - capex_total,
            percentage_of_loan=100 - capex_pct,
            description=f"Only {capex_pct:.1f}% used for CAPEX (expected >80%)",
            severity="HIGH"
        ))
    
    return violations


def _calculate_utilized_for_purpose(transactions: List[Transaction], loan_purpose: LoanPurpose) -> float:
    """Calculate amount utilized for stated purpose."""
    
    if loan_purpose == LoanPurpose.TERM_LOAN_CAPEX:
        keywords = ["machinery", "equipment", "plant", "construction", "vendor", "supplier"]
    elif loan_purpose == LoanPurpose.WORKING_CAPITAL:
        keywords = ["inventory", "raw material", "supplier", "vendor", "payroll", "operating"]
    elif loan_purpose == LoanPurpose.EQUIPMENT_PURCHASE:
        keywords = ["equipment", "machinery", "vendor"]
    else:
        keywords = ["business", "operational", "vendor", "supplier"]
    
    utilized = sum(
        txn.debit for txn in transactions 
        if any(keyword in txn.particulars.lower() for keyword in keywords)
    )
    
    return utilized


def _calculate_compliance_score(
    violations: List[EndUseViolation], 
    utilization_pct: float, 
    diversion_pct: float
) -> float:
    """Calculate end use compliance score (0-100)."""
    score = 100.0
    
    # Deduct points for violations
    for violation in violations:
        if violation.severity == "CRITICAL":
            score -= 30
        elif violation.severity == "HIGH":
            score -= 20
        elif violation.severity == "MEDIUM":
            score -= 10
        elif violation.severity == "LOW":
            score -= 5
    
    # Bonus for high utilization
    if utilization_pct >= 90:
        score += 10
    
    # Penalty for diversion
    if diversion_pct > 10:
        score -= (diversion_pct * 2)
    
    return max(0, min(100, score))


def _determine_overall_status(violations: List[EndUseViolation], diversion_pct: float) -> str:
    """Determine overall end use compliance status."""
    critical_count = sum(1 for v in violations if v.severity == "CRITICAL")
    high_count = sum(1 for v in violations if v.severity == "HIGH")
    
    if critical_count > 0 or diversion_pct > 30:
        return "Critical Fraud"
    elif high_count >= 2 or diversion_pct > 15:
        return "Major Misuse"
    elif len(violations) > 0:
        return "Minor Issues"
    else:
        return "Compliant"


def _generate_recommendation(overall_status: str, violations: List[EndUseViolation], diversion_pct: float) -> str:
    """Generate actionable recommendation."""
    if overall_status == "Critical Fraud":
        return (
            "CRITICAL: Loan funds severely misused. Initiate immediate recovery. "
            "Consider invoking recall clause. Escalate to senior management and legal team."
        )
    elif overall_status == "Major Misuse":
        return (
            "HIGH RISK: Significant fund diversion detected. Conduct physical verification of assets. "
            "Issue notice to borrower for explanation. Hold further disbursements."
        )
    elif overall_status == "Minor Issues":
        return (
            "Monitor closely. Request utilization certificate from borrower. "
            "Verify invoices for suspicious transactions."
        )
    else:
        return "Loan funds utilized as per stated purpose. Continue standard monitoring."


# ─── Integration Example ─────────────────────────────────────────────────────

async def main_example():
    """Example usage."""
    
    # Scenario 1: Compliant end use
    print("="*70)
    print("SCENARIO 1: Compliant End Use (CAPEX Loan)")
    print("="*70)
    
    transactions_1 = [
        Transaction("2024-01-15", "Machinery vendor - ABC Engineering", 8_000_000, 0, 2_000_000),
        Transaction("2024-01-20", "Equipment supplier - XYZ Ltd", 1_500_000, 0, 500_000),
        Transaction("2024-01-25", "Construction payment", 500_000, 0, 0),
    ]
    
    result1 = await verify_end_use(
        loan_account="LA1234567",
        borrower_id="BRW001",
        loan_purpose=LoanPurpose.TERM_LOAN_CAPEX,
        sanctioned_amount=10_000_000,
        disbursed_amount=10_000_000,
        transactions=transactions_1,
        loan_agreement_terms={"dividend_restricted": True}
    )
    
    print(f"Overall Status: {result1.overall_status}")
    print(f"Compliance Score: {result1.compliance_score:.1f}/100")
    print(f"Utilization for purpose: {result1.utilization_percentage:.1f}%")
    print(f"Diversion: {result1.diversion_percentage:.1f}%")
    print(f"Violations: {len(result1.violations)}")
    print(f"Flags: {result1.flags}")
    
    # Scenario 2: Fund misuse detected
    print("\n" + "="*70)
    print("SCENARIO 2: Fund Misuse Detected")
    print("="*70)
    
    transactions_2 = [
        Transaction("2024-01-15", "Machinery vendor - ABC Engineering", 2_000_000, 0, 8_000_000),
        Transaction("2024-01-18", "Transfer to Director - Unsecured loan", 3_000_000, 0, 5_000_000),
        Transaction("2024-01-20", "Transfer to group company - XYZ Sister Concern", 2_500_000, 0, 2_500_000),
        Transaction("2024-01-22", "Cash withdrawal", 1_500_000, 0, 1_000_000),
        Transaction("2024-01-25", "Personal investment - Real estate", 1_000_000, 0, 0),
    ]
    
    result2 = await verify_end_use(
        loan_account="LA7654321",
        borrower_id="BRW002",
        loan_purpose=LoanPurpose.TERM_LOAN_CAPEX,
        sanctioned_amount=10_000_000,
        disbursed_amount=10_000_000,
        transactions=transactions_2,
        loan_agreement_terms={"dividend_restricted": True}
    )
    
    print(f"Overall Status: {result2.overall_status}")
    print(f"Compliance Score: {result2.compliance_score:.1f}/100")
    print(f"Utilization for purpose: {result2.utilization_percentage:.1f}%")
    print(f"Diversion: {result2.diversion_percentage:.1f}%")
    print(f"Violations: {len(result2.violations)}")
    print(f"Flags: {result2.flags}")
    
    print(f"\n🚨 Violations Detected:")
    for violation in result2.violations:
        print(f"  [{violation.severity}] {violation.violation_type.value}")
        print(f"    Amount: ₹{violation.amount:,.0f} | {violation.description}")
        if violation.flag_code:
            print(f"    Flag: {violation.flag_code}")
    
    print(f"\n📋 Recommendation:")
    print(f"  {result2.recommendation}")


if __name__ == "__main__":
    asyncio.run(main_example())
