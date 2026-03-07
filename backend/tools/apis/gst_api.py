"""
GST API Integration — Goods and Services Tax Data Fetcher

Fetches GST return data from GSTN (GST Network):
- GSTR-1 (Outward supplies/sales)
- GSTR-3B (Summary return and tax payment)
- Filing compliance history
- E-way bill generation data
- HSN-wise sales breakdown

Key Metrics:
- Annual turnover from GST
- Month-over-month growth
- Filing frequency and compliance
- Input tax credit utilization
- Sectoral analysis

Red Flag Rules:
- GST registration cancelled → RF027 (Auto-reject)
- Non-filing >3 months → High risk
- Turnover declining >30% → Business stress

Author: Credit Intelligence System
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import requests

logger = logging.getLogger(__name__)


@dataclass
class GSTReturn:
    """GST return filing details."""
    period: str  # MM-YYYY
    return_type: str  # GSTR-1, GSTR-3B
    filing_date: Optional[str] = None
    status: str = "Filed"  # Filed, Pending, Late
    taxable_turnover: float = 0.0
    tax_paid: float = 0.0


@dataclass
class GSTResult:
    """Result from GST API."""
    data: Optional[Dict[str, Any]]
    error: Optional[str] = None
    source: str = "gst_network"
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    is_mock: bool = False


async def fetch_gst_data(
    gstin: str,
    use_mock: bool = True,
    mock_scenario: str = "compliant"
) -> GSTResult:
    """
    Fetch GST data from GSTN API.
    
    Args:
        gstin: GST Identification Number
        use_mock: Use mock data
        mock_scenario: Mock scenario (compliant, non_compliant, cancelled)
        
    Returns:
        GSTResult with GST data
    """
    logger.info(f"📊 Fetching GST data for GSTIN: {gstin}")
    
    if use_mock:
        await asyncio.sleep(1.0)
        return _get_mock_gst_data(gstin, mock_scenario)
    
    # In production: Call actual GSTN API
    try:
        result = await _fetch_real_gst_data(gstin)
        return result
    except Exception as e:
        logger.error(f"GST API error: {e}")
        return GSTResult(data=None, error=str(e))


async def _fetch_real_gst_data(gstin: str) -> GSTResult:
    """
    Fetch real GST data (placeholder).
    
    In production:
    1. Authenticate with GSTN API
    2. Fetch taxpayer details
    3. Fetch return filing history
    4. Parse and structure data
    """
    # Placeholder
    return GSTResult(data=None, error="GSTN API not configured")


def _get_mock_gst_data(gstin: str, scenario: str) -> GSTResult:
    """Generate mock GST data."""
    logger.info(f"🎭 Using mock GST data (scenario: {scenario})")
    
    if scenario == "compliant":
        # Generate 12 months of returns
        returns = []
        base_turnover = 40_000_000 / 12  # Monthly average
        
        for month_offset in range(12):
            period_date = datetime.now() - timedelta(days=30*month_offset)
            period = period_date.strftime("%m-%Y")
            
            turnover = base_turnover * (1 + (month_offset - 6) * 0.01)  # Slight growth
            
            returns.append({
                "period": period,
                "return_type": "GSTR-3B",
                "filing_date": (period_date + timedelta(days=15)).strftime("%Y-%m-%d"),
                "status": "Filed",
                "taxable_turnover": turnover,
                "tax_paid": turnover * 0.18
            })
        
        data = {
            "gstin": gstin,
            "legal_name": "Compliant Enterprises Pvt Ltd",
            "trade_name": "Compliant Enterprises",
            "registration_date": "2017-07-01",
            "status": "Active",
            "taxpayer_type": "Regular",
            "state": "Delhi",
            "annual_turnover": 40_000_000,
            "filing_frequency": "Monthly",
            "compliance_score": 95,
            "returns": returns,
            "filing_compliance": {
                "total_returns_required": 12,
                "returns_filed": 12,
                "returns_pending": 0,
                "late_filings": 0
            },
            "last_return_filed": returns[0]["period"],
            "hsn_summary": [
                {"hsn": "8471", "description": "Computers", "turnover": 20_000_000},
                {"hsn": "8473", "description": "Parts", "turnover": 15_000_000},
                {"hsn": "9999", "description": "Other", "turnover": 5_000_000}
            ]
        }
    
    elif scenario == "non_compliant":
        data = {
            "gstin": gstin,
            "legal_name": "Non-Compliant Traders Ltd",
            "trade_name": "NC Traders",
            "registration_date": "2018-01-15",
            "status": "Active",
            "taxpayer_type": "Regular",
            "state": "Maharashtra",
            "annual_turnover": 25_000_000,
            "filing_frequency": "Monthly",
            "compliance_score": 45,
            "returns": [
                {
                    "period": "01-2024",
                    "return_type": "GSTR-3B",
                    "filing_date": None,
                    "status": "Pending",
                    "taxable_turnover": 0,
                    "tax_paid": 0
                },
                {
                    "period": "12-2023",
                    "return_type": "GSTR-3B",
                    "filing_date": None,
                    "status": "Pending",
                    "taxable_turnover": 0,
                    "tax_paid": 0
                },
                {
                    "period": "11-2023",
                    "return_type": "GSTR-3B",
                    "filing_date": "2024-01-15",
                    "status": "Late Filed",
                    "taxable_turnover": 2_000_000,
                    "tax_paid": 360_000
                }
            ],
            "filing_compliance": {
                "total_returns_required": 12,
                "returns_filed": 9,
                "returns_pending": 3,
                "late_filings": 5
            },
            "last_return_filed": "11-2023",
            "notices": [
                {
                    "notice_date": "2024-01-20",
                    "notice_type": "Non-filing notice",
                    "status": "Pending"
                }
            ]
        }
    
    elif scenario == "cancelled":
        data = {
            "gstin": gstin,
            "legal_name": "Cancelled Company Ltd",
            "trade_name": "Cancelled Co",
            "registration_date": "2019-03-01",
            "status": "Cancelled",
            "cancellation_date": "2023-11-15",
            "cancellation_reason": "Voluntary cancellation",
            "taxpayer_type": "Regular",
            "state": "Uttar Pradesh",
            "annual_turnover": 0,
            "filing_frequency": "N/A",
            "compliance_score": 0,
            "returns": [],
            "filing_compliance": {
                "total_returns_required": 0,
                "returns_filed": 0,
                "returns_pending": 0,
                "late_filings": 0
            }
        }
    
    else:
        return _get_mock_gst_data(gstin, "compliant")
    
    return GSTResult(data=data, is_mock=True)


# ─── Integration Example ─────────────────────────────────────────────────────

async def main_example():
    """Example usage."""
    scenarios = [
        ("compliant", "07AAACC1234F1ZK"),
        ("non_compliant", "27BBBCC5678G2YL"),
        ("cancelled", "09CCCCC9012H3XM")
    ]
    
    for scenario, gstin in scenarios:
        print(f"\n{'='*60}")
        print(f"Scenario: {scenario.upper()}")
        print(f"GSTIN: {gstin}")
        print('='*60)
        
        result = await fetch_gst_data(gstin, use_mock=True, mock_scenario=scenario)
        
        if result.data:
            print(f"Status: {result.data['status']}")
            print(f"Annual Turnover: ₹{result.data['annual_turnover']:,.0f}")
            print(f"Compliance Score: {result.data['compliance_score']}")
            
            if result.data.get('filing_compliance'):
                fc = result.data['filing_compliance']
                print(f"Returns Filed: {fc['returns_filed']}/{fc['total_returns_required']}")
                print(f"Pending Returns: {fc['returns_pending']}")


if __name__ == "__main__":
    asyncio.run(main_example())
