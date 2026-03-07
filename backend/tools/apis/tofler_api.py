"""
Tofler API Integration — Corporate Financial Intelligence Platform

Fetches comprehensive company data from Tofler including:
- Audited financial statements (Balance Sheet, P&L, Cash Flow)
- Auditor details and changes
- Related party transactions
- Subsidiaries and group structure
- Shareholding pattern
- Charges and mortgages
- Directors and key management

Red Flag Rules:
- Auditor changed >2 times in 3 years → High risk (RF026)
- Auditor resignation (not retirement) → Critical flag
- Related party transactions >25% of revenue → Scrutiny
- Frequent director changes → Governance concern

Author: Credit Intelligence System
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

import requests

logger = logging.getLogger(__name__)


@dataclass
class FinancialStatement:
    """Financial statement data."""
    period: str  # FY 2023-24
    revenue: float
    ebitda: float
    net_profit: float
    total_assets: float
    total_liabilities: float
    net_worth: float
    current_assets: float
    current_liabilities: float


@dataclass
class ToflerResult:
    """Result from Tofler API."""
    data: Optional[Dict[str, Any]]
    error: Optional[str] = None
    source: str = "tofler"
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    is_mock: bool = False


async def fetch_tofler_data(
    cin: str,
    company_name: str,
    use_mock: bool = True,
    mock_scenario: str = "healthy"
) -> ToflerResult:
    """
    Fetch company data from Tofler API.
    
    Args:
        cin: Corporate Identification Number
        company_name: Company name
        use_mock: Use mock data
        mock_scenario: Mock scenario (healthy, stressed, governance_issues)
        
    Returns:
        ToflerResult with company data
    """
    logger.info(f"📈 Fetching Tofler data for {company_name}")
    
    if use_mock:
        await asyncio.sleep(1.5)
        return _get_mock_tofler_data(cin, company_name, mock_scenario)
    
    # In production: Call actual Tofler API
    try:
        result = await _fetch_real_tofler_data(cin, company_name)
        return result
    except Exception as e:
        logger.error(f"Tofler API error: {e}")
        return ToflerResult(data=None, error=str(e))


async def _fetch_real_tofler_data(cin: str, company_name: str) -> ToflerResult:
    """Fetch real Tofler data (placeholder)."""
    return ToflerResult(data=None, error="Tofler API not configured")


def _get_mock_tofler_data(cin: str, company_name: str, scenario: str) -> ToflerResult:
    """Generate mock Tofler data."""
    logger.info(f"🎭 Using mock Tofler data (scenario: {scenario})")
    
    if scenario == "healthy":
        data = {
            "company_name": company_name,
            "cin": cin,
            "incorporation_date": "2015-03-15",
            "company_type": "Private Limited",
            "financials": {
                "FY 2023-24": {
                    "revenue": 500_000_000,
                    "ebitda": 75_000_000,
                    "net_profit": 50_000_000,
                    "total_assets": 400_000_000,
                    "total_liabilities": 250_000_000,
                    "net_worth": 150_000_000,
                    "current_assets": 200_000_000,
                    "current_liabilities": 100_000_000
                },
                "FY 2022-23": {
                    "revenue": 450_000_000,
                    "ebitda": 65_000_000,
                    "net_profit": 42_000_000,
                    "total_assets": 350_000_000,
                    "total_liabilities": 220_000_000,
                    "net_worth": 130_000_000,
                    "current_assets": 180_000_000,
                    "current_liabilities": 95_000_000
                },
                "FY 2021-22": {
                    "revenue": 400_000_000,
                    "ebitda": 55_000_000,
                    "net_profit": 35_000_000,
                    "total_assets": 300_000_000,
                    "total_liabilities": 190_000_000,
                    "net_worth": 110_000_000,
                    "current_assets": 150_000_000,
                    "current_liabilities": 85_000_000
                }
            },
            "auditor": {
                "name": "Deloitte Haskins & Sells LLP",
                "appointment_date": "2018-09-25",
                "changes_last_3_years": 0
            },
            "directors": [
                {
                    "name": "Rajesh Kumar",
                    "din": "01234567",
                    "designation": "Managing Director",
                    "appointment_date": "2015-03-15"
                },
                {
                    "name": "Priya Sharma",
                    "din": "01234568",
                    "designation": "Director",
                    "appointment_date": "2015-03-15"
                }
            ],
            "subsidiaries": [
                {
                    "name": "Tech Solutions Inc",
                    "country": "USA",
                    "ownership_pct": 100
                }
            ],
            "related_party_transactions": {
                "total_rpt_amount": 25_000_000,
                "rpt_to_revenue_pct": 5.0,
                "major_rpts": [
                    {
                        "party_name": "Kumar Family Trust",
                        "relationship": "Promoter Group",
                        "transaction_type": "Rent paid",
                        "amount": 3_000_000
                    }
                ]
            },
            "charges": [
                {
                    "charge_holder": "State Bank of India",
                    "amount": 100_000_000,
                    "status": "Active",
                    "creation_date": "2020-06-15"
                }
            ]
        }
    
    elif scenario == "stressed":
        data = {
            "company_name": company_name,
            "cin": cin,
            "incorporation_date": "2012-08-20",
            "company_type": "Private Limited",
            "financials": {
                "FY 2023-24": {
                    "revenue": 200_000_000,
                    "ebitda": 10_000_000,
                    "net_profit": -5_000_000,  # Loss!
                    "total_assets": 150_000_000,
                    "total_liabilities": 170_000_000,  # Liabilities > Assets!
                    "net_worth": -20_000_000,  # Negative net worth!
                    "current_assets": 40_000_000,
                    "current_liabilities": 80_000_000
                },
                "FY 2022-23": {
                    "revenue": 250_000_000,
                    "ebitda": 20_000_000,
                    "net_profit": 5_000_000,
                    "total_assets": 180_000_000,
                    "total_liabilities": 165_000_000,
                    "net_worth": 15_000_000,
                    "current_assets": 50_000_000,
                    "current_liabilities": 75_000_000
                }
            },
            "auditor": {
                "name": "Small & Associates",
                "appointment_date": "2023-10-01",
                "changes_last_3_years": 2,  # Multiple changes!
                "previous_auditors": [
                    {"name": "ABC Auditors", "cessation_date": "2023-09-30", "reason": "Resignation"},
                    {"name": "XYZ & Co", "cessation_date": "2022-06-15", "reason": "Disagreement"}
                ]
            },
            "directors": [
                {
                    "name": "Vikram Singh",
                    "din": "09876543",
                    "designation": "Director",
                    "appointment_date": "2023-01-10"
                },
                {
                    "name": "Sunita Patel",
                    "din": "09876544",
                    "designation": "Director",
                    "appointment_date": "2023-01-10"
                }
            ],
            "director_changes_last_year": 4,  # High turnover!
            "subsidiaries": [],
            "related_party_transactions": {
                "total_rpt_amount": 80_000_000,
                "rpt_to_revenue_pct": 40.0,  # Very high!
                "major_rpts": [
                    {
                        "party_name": "Singh Enterprises",
                        "relationship": "Promoter Entity",
                        "transaction_type": "Sales",
                        "amount": 60_000_000
                    }
                ]
            },
            "charges": [
                {
                    "charge_holder": "ICICI Bank",
                    "amount": 120_000_000,
                    "status": "Active",
                    "creation_date": "2019-03-10"
                }
            ]
        }
    
    elif scenario == "governance_issues":
        data = {
            "company_name": company_name,
            "cin": cin,
            "incorporation_date": "2010-05-10",
            "company_type": "Private Limited",
            "financials": {
                "FY 2023-24": {
                    "revenue": 300_000_000,
                    "ebitda": 40_000_000,
                    "net_profit": 25_000_000,
                    "total_assets": 250_000_000,
                    "total_liabilities": 180_000_000,
                    "net_worth": 70_000_000,
                    "current_assets": 120_000_000,
                    "current_liabilities": 90_000_000
                }
            },
            "auditor": {
                "name": "Latest Auditors LLP",
                "appointment_date": "2024-01-15",
                "changes_last_3_years": 3,  # RF026!
                "previous_auditors": [
                    {"name": "Auditor 2", "cessation_date": "2024-01-10", "reason": "Resignation"},
                    {"name": "Auditor 1", "cessation_date": "2023-03-20", "reason": "Resignation"},
                    {"name": "Auditor 0", "cessation_date": "2022-08-15", "reason": "Terminated"}
                ]
            },
            "directors": [
                {
                    "name": "Promoter 1",
                    "din": "01010101",
                    "designation": "Managing Director",
                    "appointment_date": "2010-05-10"
                }
            ],
            "director_changes_last_year": 6,  # Very high!
            "governance_flags": [
                "Multiple auditor changes",
                "Auditor resignations",
                "High director turnover",
                "No independent directors"
            ],
            "subsidiaries": [],
            "related_party_transactions": {
                "total_rpt_amount": 100_000_000,
                "rpt_to_revenue_pct": 33.3,
                "major_rpts": []
            },
            "charges": []
        }
    
    else:
        return _get_mock_tofler_data(cin, company_name, "healthy")
    
    return ToflerResult(data=data, is_mock=True)


# ─── Integration Example ─────────────────────────────────────────────────────

async def main_example():
    """Example usage."""
    scenarios = [
        ("healthy", "Stable Corp Ltd"),
        ("stressed", "Stressed Industries Ltd"),
        ("governance_issues", "Poor Governance Co Ltd")
    ]
    
    for scenario, company in scenarios:
        print(f"\n{'='*60}")
        print(f"Scenario: {scenario.upper()}")
        print(f"Company: {company}")
        print('='*60)
        
        result = await fetch_tofler_data(
            cin=f"U12345DL2015PTC{scenario[:6].upper()}",
            company_name=company,
            use_mock=True,
            mock_scenario=scenario
        )
        
        if result.data:
            latest_fy = list(result.data['financials'].keys())[0]
            financials = result.data['financials'][latest_fy]
            
            print(f"Revenue: ₹{financials['revenue']:,.0f}")
            print(f"Net Profit: ₹{financials['net_profit']:,.0f}")
            print(f"Net Worth: ₹{financials['net_worth']:,.0f}")
            print(f"Auditor: {result.data['auditor']['name']}")
            print(f"Auditor Changes (3y): {result.data['auditor']['changes_last_3_years']}")
            
            if result.data.get('governance_flags'):
                print(f"\n⚠️  Governance Flags:")
                for flag in result.data['governance_flags']:
                    print(f"  • {flag}")


if __name__ == "__main__":
    asyncio.run(main_example())
