"""
CIBIL API Integration Module for Intelli-Credit.

This module provides integration with credit bureau APIs (CIBIL, Experian, Equifax)
for fetching commercial and consumer credit scores.

IMPORTANT: In production, replace mock data with actual API calls using
your organization's credit bureau credentials.

Author: Credit Intelligence System
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class CIBILScore:
    """Commercial CIBIL score data."""
    score: int  # 300-900
    score_date: str
    credit_history_length_months: int
    total_accounts: int
    active_accounts: int
    closed_accounts: int
    overdue_accounts: int
    total_outstanding: float  # In Crores
    highest_credit_limit: float
    dpd_last_12m: int  # Days Past Due in last 12 months
    dpd_last_6m: int
    dpd_last_3m: int
    enquiries_last_6m: int
    enquiries_last_3m: int
    wilful_defaulter: bool
    suit_filed_status: str  # NONE/PENDING/SETTLED
    written_off_status: bool
    restructured_status: bool
    payment_history: List[str]  # Last 12 months: 000=on-time, 030=30dpd, etc
    account_types: Dict[str, int]  # {term_loan: 2, working_capital: 1, etc}


@dataclass
class DirectorCIBILScore:
    """Individual CIBIL score for directors/promoters."""
    name: str
    pan: str
    score: int
    total_accounts: int
    overdue_accounts: int
    total_outstanding: float
    dpd_last_12m: int
    suit_filed: bool
    wilful_defaulter: bool


@dataclass
class CIBILReport:
    """Complete CIBIL report for company and directors."""
    request_id: str
    company_cibil: CIBILScore
    director_cibils: List[DirectorCIBILScore]
    overall_risk_flag: str  # LOW/MEDIUM/HIGH/CRITICAL
    remarks: List[str]


class CIBILAPIError(Exception):
    """Exception for CIBIL API errors."""
    pass


# ─── Mock Data for Testing ───────────────────────────────────────────────────

def _generate_mock_cibil_company(
    company_name: str,
    scenario: str = "good",
) -> CIBILScore:
    """Generate mock CIBIL data for testing. Remove in production."""

    if scenario == "excellent":
        return CIBILScore(
            score=825,
            score_date=datetime.now().strftime("%Y-%m-%d"),
            credit_history_length_months=84,
            total_accounts=8,
            active_accounts=5,
            closed_accounts=3,
            overdue_accounts=0,
            total_outstanding=12.5,
            highest_credit_limit=20.0,
            dpd_last_12m=0,
            dpd_last_6m=0,
            dpd_last_3m=0,
            enquiries_last_6m=2,
            enquiries_last_3m=1,
            wilful_defaulter=False,
            suit_filed_status="NONE",
            written_off_status=False,
            restructured_status=False,
            payment_history=["000"] * 12,
            account_types={"term_loan": 2, "working_capital": 1, "overdraft": 2},
        )
    elif scenario == "good":
        return CIBILScore(
            score=720,
            score_date=datetime.now().strftime("%Y-%m-%d"),
            credit_history_length_months=48,
            total_accounts=6,
            active_accounts=4,
            closed_accounts=2,
            overdue_accounts=0,
            total_outstanding=8.5,
            highest_credit_limit=15.0,
            dpd_last_12m=30,
            dpd_last_6m=0,
            dpd_last_3m=0,
            enquiries_last_6m=3,
            enquiries_last_3m=1,
            wilful_defaulter=False,
            suit_filed_status="NONE",
            written_off_status=False,
            restructured_status=False,
            payment_history=["000"] * 11 + ["030"],
            account_types={"term_loan": 2, "working_capital": 2},
        )
    elif scenario == "average":
        return CIBILScore(
            score=650,
            score_date=datetime.now().strftime("%Y-%m-%d"),
            credit_history_length_months=36,
            total_accounts=5,
            active_accounts=4,
            closed_accounts=1,
            overdue_accounts=1,
            total_outstanding=5.2,
            highest_credit_limit=8.0,
            dpd_last_12m=90,
            dpd_last_6m=60,
            dpd_last_3m=30,
            enquiries_last_6m=5,
            enquiries_last_3m=2,
            wilful_defaulter=False,
            suit_filed_status="PENDING",
            written_off_status=False,
            restructured_status=False,
            payment_history=["000"] * 8 + ["030", "060", "030", "000"],
            account_types={"term_loan": 2, "working_capital": 1, "credit_card": 2},
        )
    elif scenario == "poor":
        return CIBILScore(
            score=580,
            score_date=datetime.now().strftime("%Y-%m-%d"),
            credit_history_length_months=24,
            total_accounts=4,
            active_accounts=3,
            closed_accounts=1,
            overdue_accounts=2,
            total_outstanding=3.8,
            highest_credit_limit=5.0,
            dpd_last_12m=180,
            dpd_last_6m=120,
            dpd_last_3m=90,
            enquiries_last_6m=8,
            enquiries_last_3m=4,
            wilful_defaulter=False,
            suit_filed_status="PENDING",
            written_off_status=False,
            restructured_status=True,
            payment_history=["000"] * 5 + ["030", "060", "090", "090", "060", "030", "030"],
            account_types={"term_loan": 1, "working_capital": 2, "credit_card": 1},
        )
    else:  # critical
        return CIBILScore(
            score=420,
            score_date=datetime.now().strftime("%Y-%m-%d"),
            credit_history_length_months=18,
            total_accounts=3,
            active_accounts=2,
            closed_accounts=1,
            overdue_accounts=2,
            total_outstanding=2.5,
            highest_credit_limit=4.0,
            dpd_last_12m=270,
            dpd_last_6m=210,
            dpd_last_3m=150,
            enquiries_last_6m=12,
            enquiries_last_3m=6,
            wilful_defaulter=True,
            suit_filed_status="PENDING",
            written_off_status=True,
            restructured_status=True,
            payment_history=["STD"] * 6 + ["SUB", "DBT", "DBT", "DBT", "DBT", "DBT"],
            account_types={"term_loan": 1, "working_capital": 2},
        )


def _generate_mock_directors(
    promoter_names: List[str],
    company_scenario: str,
) -> List[DirectorCIBILScore]:
    """Generate mock director CIBIL scores."""
    directors = []

    for i, name in enumerate(promoter_names[:3]):  # Max 3 directors
        if company_scenario == "excellent":
            score = 800 + (i * 10)
            overdue = 0
            dpd = 0
            suit_filed = False
            wilful = False
        elif company_scenario == "good":
            score = 730 - (i * 10)
            overdue = 0
            dpd = 0
            suit_filed = False
            wilful = False
        elif company_scenario == "average":
            score = 660 - (i * 10)
            overdue = 1 if i == 0 else 0
            dpd = 30 if i == 0 else 0
            suit_filed = False
            wilful = False
        elif company_scenario == "poor":
            score = 590 - (i * 10)
            overdue = 1
            dpd = 90
            suit_filed = i == 0
            wilful = False
        else:  # critical
            score = 450 - (i * 10)
            overdue = 2
            dpd = 180
            suit_filed = True
            wilful = i == 0

        directors.append(DirectorCIBILScore(
            name=name,
            pan=f"FAKE{i}1234A",
            score=score,
            total_accounts=3 + i,
            overdue_accounts=overdue,
            total_outstanding=1.5 + (i * 0.5),
            dpd_last_12m=dpd,
            suit_filed=suit_filed,
            wilful_defaulter=wilful,
        ))

    return directors


# ─── Main API Functions ──────────────────────────────────────────────────────

def fetch_cibil_report(
    company_name: str,
    cin: str,
    promoter_names: List[str],
    promoter_pans: Optional[List[str]] = None,
    use_mock: bool = True,
    mock_scenario: str = "good",
) -> CIBILReport:
    """
    Fetch CIBIL report for company and directors.

    Args:
        company_name: Legal name of company
        cin: Corporate Identity Number
        promoter_names: List of director/promoter names
        promoter_pans: List of director PANs (optional)
        use_mock: If True, return mock data for testing
        mock_scenario: "excellent", "good", "average", "poor", "critical"

    Returns:
        CIBILReport with company and director scores

    Raises:
        CIBILAPIError: If API call fails
    """

    if use_mock:
        # Generate mock data for testing
        company_cibil = _generate_mock_cibil_company(company_name, mock_scenario)
        director_cibils = _generate_mock_directors(promoter_names, mock_scenario)

        # Determine overall risk
        if company_cibil.wilful_defaulter or any(d.wilful_defaulter for d in director_cibils):
            risk_flag = "CRITICAL"
        elif company_cibil.score < 600:
            risk_flag = "HIGH"
        elif company_cibil.score < 700:
            risk_flag = "MEDIUM"
        else:
            risk_flag = "LOW"

        # Generate remarks
        remarks = []
        if company_cibil.wilful_defaulter:
            remarks.append("WILFUL DEFAULTER TAG - Cannot lend per RBI guidelines")
        if company_cibil.written_off_status:
            remarks.append("Previous account written off")
        if company_cibil.restructured_status:
            remarks.append("Account restructured in past")
        if company_cibil.dpd_last_3m > 60:
            remarks.append(f"Recent payment delays: {company_cibil.dpd_last_3m} DPD in last 3 months")
        if company_cibil.enquiries_last_3m > 3:
            remarks.append(f"High credit enquiries: {company_cibil.enquiries_last_3m} in last 3 months")

        for director in director_cibils:
            if director.wilful_defaulter:
                remarks.append(f"Director {director.name} is wilful defaulter")
            if director.suit_filed:
                remarks.append(f"Suit filed against director {director.name}")

        if not remarks:
            remarks.append("Clean credit history with no adverse remarks")

        return CIBILReport(
            request_id=f"MOCK{datetime.now().strftime('%Y%m%d%H%M%S')}",
            company_cibil=company_cibil,
            director_cibils=director_cibils,
            overall_risk_flag=risk_flag,
            remarks=remarks,
        )

    else:
        # ─── PRODUCTION CODE ─────────────────────────────────────────────────
        # Replace this section with actual CIBIL API integration
        """
        PRODUCTION IMPLEMENTATION GUIDE:

        1. Install CIBIL API client:
           pip install cibil-api-client  # (hypothetical)

        2. Set environment variables:
           CIBIL_API_KEY=your_api_key
           CIBIL_API_SECRET=your_secret
           CIBIL_API_ENDPOINT=https://api.cibil.com/v2

        3. Example API call structure:

        import requests
        from requests.auth import HTTPBasicAuth

        api_key = os.getenv("CIBIL_API_KEY")
        api_secret = os.getenv("CIBIL_API_SECRET")
        endpoint = os.getenv("CIBIL_API_ENDPOINT")

        # Company CIBIL request
        company_response = requests.post(
            f"{endpoint}/commercial/report",
            auth=HTTPBasicAuth(api_key, api_secret),
            json={
                "company_name": company_name,
                "cin": cin,
                "report_type": "DETAILED",
            },
            timeout=30,
        )

        if company_response.status_code != 200:
            raise CIBILAPIError(f"CIBIL API error: {company_response.text}")

        # Parse response and create CIBILScore object
        company_data = company_response.json()
        company_cibil = CIBILScore(
            score=company_data["score"],
            score_date=company_data["score_date"],
            # ... map all fields from API response
        )

        # Director CIBIL requests
        director_cibils = []
        for name, pan in zip(promoter_names, promoter_pans or []):
            director_response = requests.post(
                f"{endpoint}/consumer/report",
                auth=HTTPBasicAuth(api_key, api_secret),
                json={
                    "name": name,
                    "pan": pan,
                    "report_type": "DETAILED",
                },
                timeout=30,
            )
            # Parse and append
            # director_cibils.append(DirectorCIBILScore(...))

        return CIBILReport(
            request_id=company_data["request_id"],
            company_cibil=company_cibil,
            director_cibils=director_cibils,
            overall_risk_flag=_assess_overall_risk(company_cibil, director_cibils),
            remarks=_generate_remarks(company_cibil, director_cibils),
        )
        """
        raise CIBILAPIError(
            "Production CIBIL API not configured. "
            "Set use_mock=True for testing or implement actual API integration."
        )


def cibil_report_to_dict(report: CIBILReport) -> Dict[str, Any]:
    """Convert CIBIL report to dictionary for JSON serialization."""
    return {
        "request_id": report.request_id,
        "company_cibil": {
            "score": report.company_cibil.score,
            "score_date": report.company_cibil.score_date,
            "credit_history_months": report.company_cibil.credit_history_length_months,
            "total_accounts": report.company_cibil.total_accounts,
            "active_accounts": report.company_cibil.active_accounts,
            "overdue_accounts": report.company_cibil.overdue_accounts,
            "total_outstanding_cr": report.company_cibil.total_outstanding,
            "dpd_last_12m": report.company_cibil.dpd_last_12m,
            "dpd_last_6m": report.company_cibil.dpd_last_6m,
            "dpd_last_3m": report.company_cibil.dpd_last_3m,
            "enquiries_last_6m": report.company_cibil.enquiries_last_6m,
            "enquiries_last_3m": report.company_cibil.enquiries_last_3m,
            "wilful_defaulter": report.company_cibil.wilful_defaulter,
            "suit_filed": report.company_cibil.suit_filed_status,
            "written_off": report.company_cibil.written_off_status,
            "restructured": report.company_cibil.restructured_status,
            "payment_history": report.company_cibil.payment_history,
        },
        "director_cibils": [
            {
                "name": d.name,
                "pan": d.pan,
                "score": d.score,
                "overdue_accounts": d.overdue_accounts,
                "total_outstanding_cr": d.total_outstanding,
                "dpd_last_12m": d.dpd_last_12m,
                "suit_filed": d.suit_filed,
                "wilful_defaulter": d.wilful_defaulter,
            }
            for d in report.director_cibils
        ],
        "overall_risk_flag": report.overall_risk_flag,
        "remarks": report.remarks,
    }


# ─── Example Usage ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Test with mock data
    report = fetch_cibil_report(
        company_name="ABC Manufacturing Pvt Ltd",
        cin="U12345MH2015PTC123456",
        promoter_names=["Rajesh Kumar", "Priya Sharma"],
        use_mock=True,
        mock_scenario="good",
    )

    print("=" * 60)
    print(f"CIBIL REPORT: {report.company_cibil.score}")
    print(f"Risk Flag: {report.overall_risk_flag}")
    print("\nCompany CIBIL Details:")
    print(f"  Score: {report.company_cibil.score}")
    print(f"  Overdue Accounts: {report.company_cibil.overdue_accounts}")
    print(f"  DPD Last 3M: {report.company_cibil.dpd_last_3m}")
    print(f"  Wilful Defaulter: {report.company_cibil.wilful_defaulter}")

    print("\nDirector CIBIL Scores:")
    for director in report.director_cibils:
        print(f"  {director.name}: {director.score}")

    print("\nRemarks:")
    for remark in report.remarks:
        print(f"  - {remark}")
