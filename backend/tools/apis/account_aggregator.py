"""
Account Aggregator API — RBI-regulated Financial Data Aggregation

Simulates RBI Account Aggregator framework for fetching:
- 12-month bank statements (all accounts)
- Cheque bounce history
- Average balance trends
- EMI payment patterns
- Cash withdrawal patterns
- Salary credits
- Suspicious transaction alerts

Purpose:
Account Aggregator is an RBI-regulated entity that enables
consent-based sharing of financial information.

Red Flag Rules:
- Outward cheque bounce >3 → RF028
- Hidden EMIs detected → RF023
- Cash withdrawals >20% of credits → Flag

Author: Credit Intelligence System
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class BankAccount:
    """Bank account details."""
    account_number: str
    account_type: str  # Savings, Current
    bank_name: str
    ifsc: str
    opening_date: str


@dataclass
class AccountAggregatorResult:
    """Result from Account Aggregator."""
    data: Optional[Dict[str, Any]]
    error: Optional[str] = None
    source: str = "account_aggregator"
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    is_mock: bool = False


async def fetch_account_aggregator_data(
    cin: str,
    consent_id: Optional[str] = None,
    use_mock: bool = True,
    mock_scenario: str = "healthy"
) -> AccountAggregatorResult:
    """
    Fetch banking data via Account Aggregator.
    
    Args:
        cin: Corporate Identification Number
        consent_id: User consent token
        use_mock: Use mock data
        mock_scenario: Mock scenario (healthy, stressed, suspicious)
        
    Returns:
        AccountAggregatorResult with banking data
    """
    logger.info(f"🏦 Fetching Account Aggregator data for CIN: {cin}")
    
    if use_mock:
        await asyncio.sleep(1.5)
        return _get_mock_aa_data(cin, mock_scenario)
    
    # In production: Call actual AA API
    try:
        result = await _fetch_real_aa_data(cin, consent_id)
        return result
    except Exception as e:
        logger.error(f"AA API error: {e}")
        return AccountAggregatorResult(data=None, error=str(e))


async def _fetch_real_aa_data(cin: str, consent_id: Optional[str]) -> AccountAggregatorResult:
    """Fetch real AA data (placeholder)."""
    return AccountAggregatorResult(data=None, error="AA API not configured")


def _get_mock_aa_data(cin: str, scenario: str) -> AccountAggregatorResult:
    """Generate mock Account Aggregator data."""
    logger.info(f"🎭 Using mock AA data (scenario: {scenario})")
    
    # Generate base account
    accounts = [
        {
            "account_number": "XXXXXXXX1234",
            "account_type": "Current",
            "bank_name": "State Bank of India",
            "ifsc": "SBIN0001234",
            "opening_date": "2018-05-15"
        }
    ]
    
    if scenario == "healthy":
        # Generate healthy transaction pattern
        monthly_credits = []
        monthly_debits = []
        balances = []
        
        for month in range(12):
            credit = np.random.uniform(8_000_000, 12_000_000)
            debit = credit * 0.85  # Healthy surplus
            balance = 3_000_000 + (credit - debit) * (month + 1) * 0.1
            
            monthly_credits.append(credit)
            monthly_debits.append(debit)
            balances.append(balance)
        
        data = {
            "cin": cin,
            "consent_valid_until": (datetime.now() + timedelta(days=90)).isoformat(),
            "accounts": accounts,
            "summary_12m": {
                "total_credits_annual": sum(monthly_credits),
                "total_debits_annual": sum(monthly_debits),
                "average_monthly_balance": np.mean(balances),
                "min_balance": min(balances),
                "max_balance": max(balances),
                "balance_trend": "Improving"
            },
            "cheque_bounces": {
                "outward_bounces": 0,
                "inward_bounces": 1,
                "last_bounce_date": None
            },
            "emi_patterns": [
                {
                    "payee": "HDFC Bank Ltd",
                    "amount": 250_000,
                    "frequency": "Monthly",
                    "occurrences": 12
                }
            ],
            "salary_payments": {
                "monthly_salary_outflow": 1_200_000,
                "employee_count_estimated": 25
            },
            "cash_withdrawal_ratio": 5.2,  # % of total credits
            "suspicious_transactions": []
        }
    
    elif scenario == "stressed":
        monthly_credits = []
        monthly_debits = []
        balances = []
        
        for month in range(12):
            # Declining business
            credit = 6_000_000 * (1 - month * 0.05)  # 5% decline per month
            debit = credit * 1.05  # Spending more than earning
            balance = max(500_000 - month * 50_000, 100_000)  # Declining balance
            
            monthly_credits.append(credit)
            monthly_debits.append(debit)
            balances.append(balance)
        
        data = {
            "cin": cin,
            "consent_valid_until": (datetime.now() + timedelta(days=90)).isoformat(),
            "accounts": accounts,
            "summary_12m": {
                "total_credits_annual": sum(monthly_credits),
                "total_debits_annual": sum(monthly_debits),
                "average_monthly_balance": np.mean(balances),
                "min_balance": min(balances),
                "max_balance": max(balances),
                "balance_trend": "Declining"
            },
            "cheque_bounces": {
                "outward_bounces": 5,  # RF028!
                "inward_bounces": 3,
                "last_bounce_date": (datetime.now() - timedelta(days=15)).strftime("%Y-%m-%d")
            },
            "emi_patterns": [
                {
                    "payee": "HDFC Bank Ltd",
                    "amount": 250_000,
                    "frequency": "Monthly",
                    "occurrences": 12
                },
                {
                    "payee": "XYZ Finance Ltd",  # Undeclared!
                    "amount": 150_000,
                    "frequency": "Monthly",
                    "occurrences": 10
                }
            ],
            "salary_payments": {
                "monthly_salary_outflow": 800_000,  # Reduced
                "employee_count_estimated": 15
            },
            "cash_withdrawal_ratio": 28.5,  # High!
            "suspicious_transactions": [
                {
                    "date": (datetime.now() - timedelta(days=20)).strftime("%Y-%m-%d"),
                    "amount": 2_000_000,
                    "type": "Cash withdrawal",
                    "reason": "Unusually large cash withdrawal"
                }
            ]
        }
    
    elif scenario == "suspicious":
        data = {
            "cin": cin,
            "consent_valid_until": (datetime.now() + timedelta(days=90)).isoformat(),
            "accounts": accounts,
            "summary_12m": {
                "total_credits_annual": 80_000_000,
                "total_debits_annual": 79_500_000,
                "average_monthly_balance": 1_500_000,
                "min_balance": 500_000,
                "max_balance": 5_000_000,
                "balance_trend": "Volatile"
            },
            "cheque_bounces": {
                "outward_bounces": 2,
                "inward_bounces": 0,
                "last_bounce_date": (datetime.now() - timedelta(days=45)).strftime("%Y-%m-%d")
            },
            "emi_patterns": [],
            "salary_payments": {
                "monthly_salary_outflow": 200_000,  # Very low for turnover
                "employee_count_estimated": 3
            },
            "cash_withdrawal_ratio": 45.0,  # Extremely high!
            "suspicious_transactions": [
                {
                    "date": (datetime.now() - timedelta(days=10)).strftime("%Y-%m-%d"),
                    "amount": 5_000_000,
                    "type": "Round amount transfer",
                    "reason": "Suspiciously round amount"
                },
                {
                    "date": (datetime.now() - timedelta(days=12)).strftime("%Y-%m-%d"),
                    "amount": 4_800_000,
                    "type": "Credit from related party",
                    "reason": "Same-day credit-debit pattern"
                },
                {
                    "date": (datetime.now() - timedelta(days=12)).strftime("%Y-%m-%d"),
                    "amount": 4_800_000,
                    "type": "Debit to related party",
                    "reason": "Possible circular transaction"
                }
            ]
        }
    
    else:
        return _get_mock_aa_data(cin, "healthy")
    
    return AccountAggregatorResult(data=data, is_mock=True)


# ─── Integration Example ─────────────────────────────────────────────────────

async def main_example():
    """Example usage."""
    scenarios = [
        ("healthy", "U12345DL2015PTC111111"),
        ("stressed", "U12345DL2016PTC222222"),
        ("suspicious", "U12345DL2017PTC333333")
    ]
    
    for scenario, cin in scenarios:
        print(f"\n{'='*60}")
        print(f"Scenario: {scenario.upper()}")
        print(f"CIN: {cin}")
        print('='*60)
        
        result = await fetch_account_aggregator_data(cin, use_mock=True, mock_scenario=scenario)
        
        if result.data:
            summary = result.data['summary_12m']
            print(f"Total Credits (12m): ₹{summary['total_credits_annual']:,.0f}")
            print(f"Avg Balance: ₹{summary['average_monthly_balance']:,.0f}")
            print(f"Balance Trend: {summary['balance_trend']}")
            print(f"Cheque Bounces (outward): {result.data['cheque_bounces']['outward_bounces']}")
            print(f"Cash Withdrawal Ratio: {result.data['cash_withdrawal_ratio']:.1f}%")
            print(f"Suspicious Transactions: {len(result.data['suspicious_transactions'])}")


if __name__ == "__main__":
    asyncio.run(main_example())
