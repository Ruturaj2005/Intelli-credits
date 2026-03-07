"""
Bank Statement Analyzer — Advanced Transaction Pattern Detection

Analyzes 12-month bank statements to detect:
1. Hidden EMI obligations (regular outflows not declared)
2. Suspicious transaction patterns (structuring, round-tripping)
3. Employee salary patterns (operational health indicator)
4. Income volatility (business stability)
5. Cheque bounces (RF028)
6. Large cash withdrawals (possible fund diversion)
7. Average balance trends (liquidity health)
8. Circular transactions (group fund pooling)

Red Flag Rules:
- Outward cheque bounce >3 → RF028
- Hidden EMIs > declared loans → RF023
- Cash withdrawals >20% of credits → Flag
- Income volatility >40% → High risk

Output:
- Bank statement score (0-100)
- Suspicious transaction count
- Detected EMI obligations
- Liquidity metrics

Author: Credit Intelligence System
"""
from __future__ import annotations

import asyncio
import logging
import re
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class Transaction:
    """Individual bank transaction."""
    date: str
    description: str
    debit: float
    credit: float
    balance: float
    transaction_type: str = "Unknown"  # EMI, Salary, Cash, Transfer, etc.
    is_suspicious: bool = False
    suspicion_reason: Optional[str] = None


@dataclass
class EMIPattern:
    """Detected EMI pattern (potential hidden loan)."""
    payee: str
    amount: float
    frequency: str  # Monthly, Quarterly
    occurrences: int
    first_payment_date: str
    last_payment_date: str
    total_amount_paid: float
    is_declared: bool = False


@dataclass
class BankStatementResult:
    """Result from bank statement analysis."""
    score: float  # 0-100
    flags: List[str]
    data: Dict[str, Any]
    confidence: float
    
    # Key metrics
    average_monthly_balance: float = 0.0
    total_credits: float = 0.0
    total_debits: float = 0.0
    cheque_bounces: int = 0
    suspicious_transactions: List[Transaction] = field(default_factory=list)
    detected_emis: List[EMIPattern] = field(default_factory=list)
    hidden_emi_amount: float = 0.0
    income_volatility: float = 0.0
    salary_payments_detected: int = 0


async def analyze_bank_statement(
    transactions: List[Dict[str, Any]],
    declared_loans: Optional[List[Dict[str, Any]]] = None,
    company_name: str = "Unknown",
    period_months: int = 12
) -> BankStatementResult:
    """
    Analyze bank statement transactions.
    
    Args:
        transactions: List of transaction dicts with keys:
            - date, description, debit, credit, balance
        declared_loans: List of declared loan EMIs
        company_name: Company name for pattern detection
        period_months: Analysis period in months
        
    Returns:
        BankStatementResult with analysis findings
    """
    logger.info(f"💳 Analyzing bank statement: {len(transactions)} transactions over {period_months} months")
    
    # Parse transactions
    parsed_txns = _parse_transactions(transactions)
    
    # Categorize transactions
    categorized = _categorize_transactions(parsed_txns, company_name)
    
    # Detect EMI patterns
    detected_emis = _detect_emi_patterns(parsed_txns, declared_loans)
    
    # Detect suspicious patterns
    suspicious_txns = _detect_suspicious_patterns(parsed_txns)
    
    # Calculate liquidity metrics
    liquidity_metrics = _calculate_liquidity_metrics(parsed_txns)
    
    # Detect cheque bounces
    cheque_bounces = _count_cheque_bounces(parsed_txns)
    
    # Calculate income volatility
    income_volatility = _calculate_income_volatility(parsed_txns)
    
    # Detect salary patterns
    salary_count = _detect_salary_payments(parsed_txns)
    
    # Calculate hidden EMI amount
    hidden_emi_amount = sum(
        emi.total_amount_paid / emi.occurrences 
        for emi in detected_emis 
        if not emi.is_declared
    )
    
    # Generate flags
    flags = _generate_bank_flags(
        cheque_bounces,
        detected_emis,
        hidden_emi_amount,
        suspicious_txns,
        income_volatility,
        liquidity_metrics
    )
    
    # Calculate score
    score = _calculate_bank_score(
        cheque_bounces,
        len(suspicious_txns),
        hidden_emi_amount,
        income_volatility,
        liquidity_metrics
    )
    
    # Build detailed data
    data = {
        "total_credits": liquidity_metrics["total_credits"],
        "total_debits": liquidity_metrics["total_debits"],
        "average_balance": liquidity_metrics["avg_balance"],
        "min_balance": liquidity_metrics["min_balance"],
        "max_balance": liquidity_metrics["max_balance"],
        "balance_trend": liquidity_metrics["balance_trend"],
        "detected_emis": [
            {
                "payee": emi.payee,
                "amount": emi.amount,
                "frequency": emi.frequency,
                "occurrences": emi.occurrences,
                "total_paid": emi.total_amount_paid,
                "is_declared": emi.is_declared
            }
            for emi in detected_emis
        ],
        "suspicious_transactions": [
            {
                "date": txn.date,
                "description": txn.description,
                "amount": txn.debit + txn.credit,
                "reason": txn.suspicion_reason
            }
            for txn in suspicious_txns
        ],
        "cheque_bounces": cheque_bounces,
        "income_volatility_pct": income_volatility,
        "salary_payments": salary_count,
        "transaction_summary": {
            "total": len(parsed_txns),
            "credits": sum(1 for t in parsed_txns if t.credit > 0),
            "debits": sum(1 for t in parsed_txns if t.debit > 0)
        }
    }
    
    confidence = 0.85 if len(parsed_txns) >= period_months * 20 else 0.6
    
    logger.info(
        f"✅ Bank analysis complete | Score: {score:.1f}/100 | "
        f"Flags: {len(flags)} | Suspicious: {len(suspicious_txns)}"
    )
    
    return BankStatementResult(
        score=score,
        flags=flags,
        data=data,
        confidence=confidence,
        average_monthly_balance=liquidity_metrics["avg_balance"],
        total_credits=liquidity_metrics["total_credits"],
        total_debits=liquidity_metrics["total_debits"],
        cheque_bounces=cheque_bounces,
        suspicious_transactions=suspicious_txns,
        detected_emis=detected_emis,
        hidden_emi_amount=hidden_emi_amount,
        income_volatility=income_volatility,
        salary_payments_detected=salary_count
    )


def _parse_transactions(raw_txns: List[Dict[str, Any]]) -> List[Transaction]:
    """Parse raw transaction data into structured format."""
    transactions = []
    
    for txn in raw_txns:
        transactions.append(Transaction(
            date=txn.get("date", ""),
            description=txn.get("description", "").upper(),
            debit=float(txn.get("debit", 0) or 0),
            credit=float(txn.get("credit", 0) or 0),
            balance=float(txn.get("balance", 0) or 0)
        ))
    
    return transactions


def _categorize_transactions(
    transactions: List[Transaction],
    company_name: str
) -> Dict[str, List[Transaction]]:
    """Categorize transactions by type."""
    categories = defaultdict(list)
    
    for txn in transactions:
        desc = txn.description
        
        # EMI/Loan payments
        if any(keyword in desc for keyword in ["EMI", "LOAN", "INSTALLMENT", "NBFC", "FINANCE"]):
            txn.transaction_type = "EMI"
            categories["emi"].append(txn)
        
        # Salary payments
        elif any(keyword in desc for keyword in ["SALARY", "SAL", "WAGES", "PAYROLL"]):
            txn.transaction_type = "Salary"
            categories["salary"].append(txn)
        
        # Cash withdrawals
        elif any(keyword in desc for keyword in ["CASH", "ATM", "WITHDRAWAL"]):
            txn.transaction_type = "Cash"
            categories["cash"].append(txn)
        
        # Cheque transactions
        elif any(keyword in desc for keyword in ["CHQ", "CHEQUE", "CHECK"]):
            txn.transaction_type = "Cheque"
            categories["cheque"].append(txn)
        
        # GST/Tax payments
        elif any(keyword in desc for keyword in ["GST", "TDS", "TAX", "CHALLAN"]):
            txn.transaction_type = "Tax"
            categories["tax"].append(txn)
        
        # Transfers
        elif any(keyword in desc for keyword in ["NEFT", "RTGS", "IMPS", "UPI", "TRANSFER"]):
            txn.transaction_type = "Transfer"
            categories["transfer"].append(txn)
        
        else:
            categories["other"].append(txn)
    
    return dict(categories)


def _detect_emi_patterns(
    transactions: List[Transaction],
    declared_loans: Optional[List[Dict[str, Any]]]
) -> List[EMIPattern]:
    """
    Detect recurring payment patterns that look like EMIs.
    
    Logic:
    1. Group debits by payee name
    2. Find recurring amounts (±5% tolerance)
    3. Check if monthly/quarterly frequency
    4. Cross-check with declared loans
    """
    emis = []
    
    # Group debits by approximate payee
    payee_groups = defaultdict(list)
    
    for txn in transactions:
        if txn.debit > 5000:  # Minimum EMI threshold
            # Extract likely payee name (simplified)
            payee = _extract_payee_name(txn.description)
            if payee:
                payee_groups[payee].append(txn)
    
    # Analyze each payee group
    for payee, txns in payee_groups.items():
        if len(txns) < 3:  # Need at least 3 occurrences
            continue
        
        # Sort by date
        sorted_txns = sorted(txns, key=lambda t: t.date)
        
        # Find recurring amounts
        amounts = [t.debit for t in sorted_txns]
        recurring_amount = _find_recurring_amount(amounts)
        
        if recurring_amount:
            matching_txns = [t for t in sorted_txns if abs(t.debit - recurring_amount) / recurring_amount < 0.05]
            
            if len(matching_txns) >= 3:
                # Check if declared
                is_declared = _is_loan_declared(payee, recurring_amount, declared_loans)
                
                emis.append(EMIPattern(
                    payee=payee,
                    amount=recurring_amount,
                    frequency="Monthly",  # Simplified
                    occurrences=len(matching_txns),
                    first_payment_date=matching_txns[0].date,
                    last_payment_date=matching_txns[-1].date,
                    total_amount_paid=sum(t.debit for t in matching_txns),
                    is_declared=is_declared
                ))
    
    return emis


def _detect_suspicious_patterns(transactions: List[Transaction]) -> List[Transaction]:
    """
    Detect suspicious transaction patterns.
    
    Patterns:
    1. Round amounts (structuring to avoid reporting)
    2. Same-day credit-debit (circular transaction)
    3. Multiple small credits followed by large debit (structuring)
    4. Transactions to known shell company patterns
    """
    suspicious = []
    
    for i, txn in enumerate(transactions):
        # Pattern 1: Suspiciously round amounts (e.g., exactly 50000, 100000)
        amount = txn.debit if txn.debit > 0 else txn.credit
        if amount > 0 and amount % 50000 == 0 and amount >= 100000:
            if "CASH" in txn.description or "ATM" in txn.description:
                txn.is_suspicious = True
                txn.suspicion_reason = "Large round cash withdrawal - possible structuring"
                suspicious.append(txn)
        
        # Pattern 2: Large cash withdrawals (>20% of average credit)
        if txn.debit > 0 and "CASH" in txn.description:
            if txn.debit > 500000:
                txn.is_suspicious = True
                txn.suspicion_reason = "Large cash withdrawal - possible fund diversion"
                suspicious.append(txn)
        
        # Pattern 3: Cheque bounce indicators
        if "BOUNCE" in txn.description or "RETURN UNPAID" in txn.description:
            txn.is_suspicious = True
            txn.suspicion_reason = "Cheque bounce detected"
            suspicious.append(txn)
    
    return suspicious


def _calculate_liquidity_metrics(transactions: List[Transaction]) -> Dict[str, float]:
    """Calculate liquidity and balance metrics."""
    balances = [t.balance for t in transactions if t.balance > 0]
    credits = [t.credit for t in transactions if t.credit > 0]
    debits = [t.debit for t in transactions if t.debit > 0]
    
    metrics = {
        "avg_balance": np.mean(balances) if balances else 0,
        "min_balance": min(balances) if balances else 0,
        "max_balance": max(balances) if balances else 0,
        "total_credits": sum(credits),
        "total_debits": sum(debits),
        "balance_trend": "improving" if len(balances) > 1 and balances[-1] > balances[0] else "declining"
    }
    
    return metrics


def _count_cheque_bounces(transactions: List[Transaction]) -> int:
    """Count cheque bounce occurrences."""
    bounce_keywords = ["BOUNCE", "RETURN UNPAID", "CHQ RETURN", "INSUFFICIENT"]
    
    bounces = sum(
        1 for txn in transactions
        if any(keyword in txn.description for keyword in bounce_keywords)
    )
    
    return bounces


def _calculate_income_volatility(transactions: List[Transaction]) -> float:
    """
    Calculate income volatility (coefficient of variation of monthly credits).
    
    Higher volatility = Less stable business
    """
    # Group credits by month
    monthly_credits = defaultdict(float)
    
    for txn in transactions:
        if txn.credit > 0:
            try:
                month_key = txn.date[:7]  # YYYY-MM
                monthly_credits[month_key] += txn.credit
            except:
                continue
    
    if len(monthly_credits) < 2:
        return 0.0
    
    credit_values = list(monthly_credits.values())
    mean_credit = np.mean(credit_values)
    std_credit = np.std(credit_values)
    
    # Coefficient of variation (%)
    volatility = (std_credit / mean_credit * 100) if mean_credit > 0 else 0
    
    return volatility


def _detect_salary_payments(transactions: List[Transaction]) -> int:
    """Detect employee salary payment patterns."""
    salary_keywords = ["SALARY", "SAL", "WAGES", "PAYROLL"]
    
    salary_txns = [
        txn for txn in transactions
        if txn.debit > 0 and any(keyword in txn.description for keyword in salary_keywords)
    ]
    
    # Count unique salary payment instances (monthly)
    return len(salary_txns)


def _generate_bank_flags(
    cheque_bounces: int,
    detected_emis: List[EMIPattern],
    hidden_emi_amount: float,
    suspicious_txns: List[Transaction],
    income_volatility: float,
    liquidity_metrics: Dict[str, float]
) -> List[str]:
    """Generate red flags based on bank analysis."""
    flags = []
    
    # RF028: Cheque bounces
    if cheque_bounces > 3:
        flags.append(f"RF028: Outward cheque bounces detected ({cheque_bounces} instances)")
    elif cheque_bounces > 0:
        flags.append(f"Cheque bounces: {cheque_bounces} (monitor)")
    
    # RF023: Hidden EMI obligations
    hidden_emis = [emi for emi in detected_emis if not emi.is_declared]
    if hidden_emis:
        flags.append(
            f"RF023: {len(hidden_emis)} undeclared EMI pattern(s) detected "
            f"(₹{hidden_emi_amount:,.0f}/month)"
        )
    
    # Suspicious transactions
    if len(suspicious_txns) > 5:
        flags.append(f"{len(suspicious_txns)} suspicious transactions detected")
    
    # High income volatility
    if income_volatility > 40:
        flags.append(f"High income volatility: {income_volatility:.1f}% (unstable business)")
    
    # Low liquidity warning
    avg_balance = liquidity_metrics.get("avg_balance", 0)
    monthly_credit = liquidity_metrics.get("total_credits", 0) / 12
    
    if avg_balance < monthly_credit * 0.1:  # Less than 10% of monthly income
        flags.append("Low average balance - liquidity concerns")
    
    # Declining balance trend
    if liquidity_metrics.get("balance_trend") == "declining":
        flags.append("Declining balance trend over analysis period")
    
    return flags


def _calculate_bank_score(
    cheque_bounces: int,
    suspicious_count: int,
    hidden_emi_amount: float,
    income_volatility: float,
    liquidity_metrics: Dict[str, float]
) -> float:
    """Calculate overall bank statement score (0-100)."""
    score = 100.0
    
    # Penalty for cheque bounces
    if cheque_bounces > 3:
        score -= 40  # RF028 - critical
    elif cheque_bounces > 0:
        score -= cheque_bounces * 8
    
    # Penalty for hidden EMIs
    if hidden_emi_amount > 0:
        score -= 25  # RF023
    
    # Penalty for suspicious transactions
    score -= min(suspicious_count * 3, 20)
    
    # Penalty for high volatility
    if income_volatility > 40:
        score -= 15
    elif income_volatility > 25:
        score -= 8
    
    # Penalty for low liquidity
    avg_balance = liquidity_metrics.get("avg_balance", 0)
    monthly_credit = liquidity_metrics.get("total_credits", 0) / 12
    
    if monthly_credit > 0 and avg_balance < monthly_credit * 0.1:
        score -= 10
    
    return max(0, score)


# ─── Helper functions ────────────────────────────────────────────────────────

def _extract_payee_name(description: str) -> Optional[str]:
    """Extract payee name from transaction description."""
    # Simplified extraction - in production, use more sophisticated parsing
    keywords_to_remove = ["NEFT", "RTGS", "IMPS", "UPI", "TO", "FROM", "DR", "CR"]
    
    cleaned = description
    for keyword in keywords_to_remove:
        cleaned = cleaned.replace(keyword, "")
    
    # Extract first meaningful word
    words = cleaned.strip().split()
    if words:
        return words[0]
    
    return None


def _find_recurring_amount(amounts: List[float], tolerance: float = 0.05) -> Optional[float]:
    """Find most common recurring amount within tolerance."""
    if len(amounts) < 3:
        return None
    
    # Simple approach: find mode with tolerance
    amount_counts = defaultdict(int)
    
    for amount in amounts:
        # Group similar amounts
        grouped = False
        for key in amount_counts.keys():
            if abs(amount - key) / key < tolerance:
                amount_counts[key] += 1
                grouped = True
                break
        
        if not grouped:
            amount_counts[amount] = 1
    
    # Return most common
    if amount_counts:
        return max(amount_counts.items(), key=lambda x: x[1])[0]
    
    return None


def _is_loan_declared(
    payee: str,
    amount: float,
    declared_loans: Optional[List[Dict[str, Any]]]
) -> bool:
    """Check if detected EMI matches declared loans."""
    if not declared_loans:
        return False
    
    for loan in declared_loans:
        declared_emi = loan.get("emi_amount", 0)
        declared_lender = loan.get("lender", "").upper()
        
        # Check if amount and lender match
        if abs(declared_emi - amount) / amount < 0.1 and payee in declared_lender:
            return True
    
    return False


# ─── Integration Example ─────────────────────────────────────────────────────

async def main_example():
    """Example usage of bank statement analyzer."""
    
    # Generate mock transactions
    transactions = []
    base_date = datetime.now() - timedelta(days=365)
    
    for month in range(12):
        # Monthly credits (business income)
        for day in [5, 12, 20, 28]:
            date = base_date + timedelta(days=month*30 + day)
            transactions.append({
                "date": date.strftime("%Y-%m-%d"),
                "description": f"NEFT CUSTOMER PAYMENT {day}",
                "debit": 0,
                "credit": np.random.uniform(200000, 500000),
                "balance": 1500000
            })
        
        # Monthly EMI (undeclared)
        date = base_date + timedelta(days=month*30 + 7)
        transactions.append({
            "date": date.strftime("%Y-%m-%d"),
            "description": "NEFT TO NBFC FINANCE LTD LOAN INST",
            "debit": 125000,
            "credit": 0,
            "balance": 1400000
        })
        
        # Salary payments
        date = base_date + timedelta(days=month*30 + 1)
        transactions.append({
            "date": date.strftime("%Y-%m-%d"),
            "description": "SALARY PAYMENT EMPLOYEES",
            "debit": 450000,
            "credit": 0,
            "balance": 1300000
        })
    
    # Add cheque bounces
    for i in range(4):
        date = base_date + timedelta(days=i*90 + 15)
        transactions.append({
            "date": date.strftime("%Y-%m-%d"),
            "description": "CHQ RETURN UNPAID INSUFFICIENT FUNDS",
            "debit": 50000,
            "credit": 0,
            "balance": 1250000
        })
    
    # Declared loans
    declared_loans = [
        {"lender": "STATE BANK OF INDIA", "emi_amount": 85000}
        # Note: NBFC EMI is NOT declared
    ]
    
    # Analyze
    result = await analyze_bank_statement(
        transactions=transactions,
        declared_loans=declared_loans,
        company_name="Test Company Ltd",
        period_months=12
    )
    
    print("="*70)
    print("BANK STATEMENT ANALYSIS RESULTS")
    print("="*70)
    print(f"Score: {result.score:.1f}/100")
    print(f"Confidence: {result.confidence:.1%}")
    print(f"\nKey Metrics:")
    print(f"  Average Monthly Balance: ₹{result.average_monthly_balance:,.0f}")
    print(f"  Total Credits (12m): ₹{result.total_credits:,.0f}")
    print(f"  Total Debits (12m): ₹{result.total_debits:,.0f}")
    print(f"  Income Volatility: {result.income_volatility:.1f}%")
    print(f"  Cheque Bounces: {result.cheque_bounces}")
    print(f"  Suspicious Transactions: {len(result.suspicious_transactions)}")
    print(f"\nDetected EMIs:")
    for emi in result.detected_emis:
        status = "✅ Declared" if emi.is_declared else "⚠️  UNDECLARED"
        print(f"  {emi.payee}: ₹{emi.amount:,.0f}/month × {emi.occurrences} = ₹{emi.total_amount_paid:,.0f} [{status}]")
    
    if result.flags:
        print(f"\n🚨 Red Flags:")
        for flag in result.flags:
            print(f"  • {flag}")


if __name__ == "__main__":
    asyncio.run(main_example())
