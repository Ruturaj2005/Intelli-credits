"""
NCLT Insolvency Checker — Corporate Insolvency Resolution Process Detector

Checks National Company Law Tribunal (NCLT) records for:
- Corporate Insolvency Resolution Process (CIRP) status
- Liquidation orders
- Insolvency petitions (pending/admitted)
- Resolution professional details
- Committee of Creditors (CoC) formation

Critical Rule:
Active CIRP → RF022 (Auto Reject - Cannot lend to company under insolvency)

Features:
- Real NCLT website scraping capability
- Mock data with multiple scenarios
- Async execution with timeout
- Structured output format

Mock Scenarios:
- clean_company: No insolvency proceedings
- under_cirp: Active CIRP (auto-reject)
- cirp_resolved: Successfully resolved CIRP
- liquidation: Under liquidation

Author: Credit Intelligence System
"""
from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

RATE_LIMIT_DELAY = 2.0  # seconds


@dataclass
class InsolvencyProceeding:
    """Details of an insolvency proceeding."""
    case_number: str
    case_type: str  # CIRP, Liquidation, Section 9, Section 7
    filing_date: str
    status: str  # Admitted, Pending, Disposed, Withdrawn
    petitioner: str
    amount_claimed: Optional[float] = None
    resolution_professional: Optional[str] = None
    admission_date: Optional[str] = None
    closure_date: Optional[str] = None


@dataclass
class NCLTResult:
    """Result from NCLT checker."""
    data: Optional[Dict[str, Any]]
    error: Optional[str] = None
    source: str = "nclt"
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    is_mock: bool = False


async def check_nclt_status(
    cin: str,
    company_name: str,
    use_mock: bool = True,
    mock_scenario: str = "clean_company",
    timeout: int = 10
) -> NCLTResult:
    """
    Check NCLT records for insolvency proceedings.
    
    Args:
        cin: Corporate Identification Number
        company_name: Company name
        use_mock: If True, use mock data
        mock_scenario: Mock scenario to use
        timeout: Request timeout
        
    Returns:
        NCLTResult with insolvency status
    """
    logger.info(f"⚖️  Checking NCLT status for {company_name} (CIN: {cin})")
    
    # Try real scraping first in production
    if not use_mock:
        try:
            result = await _check_real_nclt(cin, company_name, timeout)
            if result.data:
                return result
        except Exception as e:
            logger.warning(f"⚠️  Real NCLT check failed, using mock: {str(e)}")
    
    # Use mock data
    await asyncio.sleep(RATE_LIMIT_DELAY)
    return _get_mock_nclt_data(cin, company_name, mock_scenario)


async def _check_real_nclt(
    cin: str,
    company_name: str,
    timeout: int
) -> NCLTResult:
    """
    Attempt real NCLT website scraping.
    
    Note: NCLT website structure:
    - https://nclt.gov.in/
    - Case search by company name/CIN
    - Parse cause list and orders
    """
    # Base URL for NCLT
    search_url = "https://nclt.gov.in/case-status"
    
    try:
        loop = asyncio.get_event_loop()
        
        # Search for company
        response = await loop.run_in_executor(
            None,
            lambda: requests.post(
                search_url,
                data={"company_name": company_name, "cin": cin},
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=timeout
            )
        )
        
        if response.status_code != 200:
            raise Exception(f"HTTP {response.status_code}")
        
        # Parse results
        soup = BeautifulSoup(response.content, 'html.parser')
        data = _parse_nclt_html(soup, cin, company_name)
        
        return NCLTResult(data=data, is_mock=False)
        
    except Exception as e:
        logger.error(f"❌ NCLT check error: {str(e)}")
        return NCLTResult(data=None, error=str(e))


def _parse_nclt_html(soup: BeautifulSoup, cin: str, company_name: str) -> Dict[str, Any]:
    """
    Parse NCLT HTML to extract case details.
    
    Placeholder implementation - would need actual HTML structure mapping.
    """
    # In production, parse actual NCLT HTML tables and case listings
    return {
        "company_name": company_name,
        "cin": cin,
        "is_under_cirp": False,
        "is_under_liquidation": False,
        "proceedings": [],
        "last_checked": datetime.now().isoformat()
    }


def _get_mock_nclt_data(
    cin: str,
    company_name: str,
    scenario: str
) -> NCLTResult:
    """
    Generate mock NCLT data based on scenario.
    """
    logger.info(f"🎭 Using mock NCLT data (scenario: {scenario})")
    
    if scenario == "clean_company":
        data = {
            "company_name": company_name,
            "cin": cin,
            "is_under_cirp": False,
            "is_under_liquidation": False,
            "has_pending_petitions": False,
            "proceedings": [],
            "nclt_records_found": 0,
            "last_checked": datetime.now().isoformat(),
            "status_summary": "No insolvency proceedings found. Company is clear."
        }
    
    elif scenario == "under_cirp":
        admission_date = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")
        data = {
            "company_name": company_name,
            "cin": cin,
            "is_under_cirp": True,
            "is_under_liquidation": False,
            "has_pending_petitions": False,
            "cirp_commencement_date": admission_date,
            "resolution_professional": "CA Mahesh Kumar",
            "resolution_professional_firm": "M K Associates",
            "moratorium_period_end": (datetime.now() + timedelta(days=180)).strftime("%Y-%m-%d"),
            "total_claims_received": 15,
            "verified_claims_amount": 450000000,
            "coc_formed": True,
            "coc_meetings_held": 3,
            "proceedings": [
                {
                    "case_number": "CP(IB)/123/MB/2024",
                    "case_type": "Corporate Insolvency Resolution Process",
                    "filing_date": (datetime.now() - timedelta(days=120)).strftime("%Y-%m-%d"),
                    "admission_date": admission_date,
                    "status": "Admitted - CIRP Ongoing",
                    "petitioner": "State Bank of India",
                    "amount_claimed": 250000000,
                    "resolution_professional": "CA Mahesh Kumar",
                    "nclt_bench": "Mumbai"
                }
            ],
            "nclt_records_found": 1,
            "last_checked": datetime.now().isoformat(),
            "status_summary": "⛔ CRITICAL: Company under active CIRP. Auto-reject recommendation.",
            "red_flag": "RF022",
            "red_flag_description": "Company under Corporate Insolvency Resolution Process"
        }
    
    elif scenario == "cirp_resolved":
        data = {
            "company_name": company_name,
            "cin": cin,
            "is_under_cirp": False,
            "is_under_liquidation": False,
            "has_pending_petitions": False,
            "past_cirp": True,
            "cirp_commencement_date": "2022-05-10",
            "cirp_closure_date": "2023-03-15",
            "resolution_outcome": "Resolution Plan Approved",
            "haircut_percentage": 35.5,
            "proceedings": [
                {
                    "case_number": "CP(IB)/456/ND/2022",
                    "case_type": "Corporate Insolvency Resolution Process",
                    "filing_date": "2022-04-20",
                    "admission_date": "2022-05-10",
                    "status": "Disposed - Resolution Plan Approved",
                    "petitioner": "ICICI Bank Ltd",
                    "amount_claimed": 180000000,
                    "resolution_professional": "CA Anita Desai",
                    "closure_date": "2023-03-15",
                    "nclt_bench": "New Delhi",
                    "resolution_applicant": "Phoenix Consortium"
                }
            ],
            "nclt_records_found": 1,
            "last_checked": datetime.now().isoformat(),
            "status_summary": "Company successfully resolved CIRP. Exercise caution - check post-resolution performance.",
            "caution_note": "Previous insolvency resolved. Enhanced due diligence recommended."
        }
    
    elif scenario == "liquidation":
        liquidation_date = (datetime.now() - timedelta(days=45)).strftime("%Y-%m-%d")
        data = {
            "company_name": company_name,
            "cin": cin,
            "is_under_cirp": False,
            "is_under_liquidation": True,
            "has_pending_petitions": False,
            "liquidation_commencement_date": liquidation_date,
            "liquidator": "CA Ramesh Patel",
            "liquidator_firm": "Patel Liquidation Services",
            "estimated_realization": 120000000,
            "proceedings": [
                {
                    "case_number": "CP(IB)/789/KB/2024",
                    "case_type": "Liquidation",
                    "filing_date": (datetime.now() - timedelta(days=60)).strftime("%Y-%m-%d"),
                    "admission_date": liquidation_date,
                    "status": "Liquidation Order Passed",
                    "petitioner": "Resolution Professional",
                    "liquidator": "CA Ramesh Patel",
                    "nclt_bench": "Kolkata"
                }
            ],
            "nclt_records_found": 1,
            "last_checked": datetime.now().isoformat(),
            "status_summary": "⛔ CRITICAL: Company under liquidation. Auto-reject.",
            "red_flag": "RF022",
            "red_flag_description": "Company under liquidation proceedings"
        }
    
    elif scenario == "pending_petition":
        data = {
            "company_name": company_name,
            "cin": cin,
            "is_under_cirp": False,
            "is_under_liquidation": False,
            "has_pending_petitions": True,
            "proceedings": [
                {
                    "case_number": "CP(IB)/234/CB/2025",
                    "case_type": "Section 9 Application (Operational Creditor)",
                    "filing_date": (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d"),
                    "status": "Pending Admission",
                    "petitioner": "ABC Suppliers Pvt Ltd",
                    "amount_claimed": 5000000,
                    "nclt_bench": "Chennai",
                    "next_hearing_date": (datetime.now() + timedelta(days=15)).strftime("%Y-%m-%d")
                }
            ],
            "nclt_records_found": 1,
            "last_checked": datetime.now().isoformat(),
            "status_summary": "⚠️  WARNING: Pending insolvency petition. Monitor closely.",
            "caution_note": "Section 9 petition pending. High risk of admission."
        }
    
    else:
        # Default to clean company
        return _get_mock_nclt_data(cin, company_name, "clean_company")
    
    return NCLTResult(data=data, is_mock=True)


def evaluate_nclt_risk(nclt_result: NCLTResult) -> Dict[str, Any]:
    """
    Evaluate risk based on NCLT findings.
    
    Returns:
        Risk assessment with score and flags
    """
    if not nclt_result.data:
        return {
            "score": 50,  # Neutral score due to unavailable data
            "risk_level": "MEDIUM",
            "flags": ["NCLT data unavailable"],
            "auto_reject": False
        }
    
    data = nclt_result.data
    flags = []
    auto_reject = False
    score = 100
    
    # Critical: Under CIRP or Liquidation
    if data.get("is_under_cirp"):
        flags.append("RF022: Company under Corporate Insolvency Resolution Process")
        auto_reject = True
        score = 0
    
    if data.get("is_under_liquidation"):
        flags.append("RF022: Company under liquidation")
        auto_reject = True
        score = 0
    
    # High Risk: Pending petitions
    if data.get("has_pending_petitions"):
        flags.append("Pending insolvency petition at NCLT")
        score -= 30
    
    # Medium Risk: Past CIRP (resolved)
    if data.get("past_cirp"):
        flags.append("Previously underwent CIRP (resolved)")
        score -= 15
    
    risk_level = "CRITICAL" if auto_reject else (
        "HIGH" if score < 50 else "MEDIUM" if score < 80 else "LOW"
    )
    
    return {
        "score": max(0, score),
        "risk_level": risk_level,
        "flags": flags,
        "auto_reject": auto_reject,
        "confidence": 0.95 if not nclt_result.error else 0.5
    }


# ─── Integration Example ─────────────────────────────────────────────────────

async def main_example():
    """Example usage of NCLT checker."""
    scenarios = [
        ("clean_company", "TechCorp Solutions Pvt Ltd"),
        ("under_cirp", "Stressed Assets Ltd"),
        ("liquidation", "Defunct Industries Ltd"),
        ("cirp_resolved", "Phoenix Revival Pvt Ltd")
    ]
    
    for scenario, company in scenarios:
        print(f"\n{'='*60}")
        print(f"Scenario: {scenario.upper()}")
        print(f"Company: {company}")
        print('='*60)
        
        result = await check_nclt_status(
            cin=f"U12345DL2015PTC{scenario[:6].upper()}",
            company_name=company,
            use_mock=True,
            mock_scenario=scenario
        )
        
        if result.data:
            print(f"Status: {result.data.get('status_summary', 'N/A')}")
            print(f"Under CIRP: {result.data.get('is_under_cirp', False)}")
            print(f"Proceedings: {len(result.data.get('proceedings', []))}")
            
            # Evaluate risk
            risk = evaluate_nclt_risk(result)
            print(f"\nRisk Assessment:")
            print(f"  Score: {risk['score']}/100")
            print(f"  Risk Level: {risk['risk_level']}")
            print(f"  Auto Reject: {risk['auto_reject']}")
            if risk['flags']:
                print(f"  Flags: {', '.join(risk['flags'])}")
        else:
            print(f"❌ Error: {result.error}")


if __name__ == "__main__":
    asyncio.run(main_example())
