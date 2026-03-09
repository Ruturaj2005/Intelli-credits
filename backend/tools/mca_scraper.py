"""
MCA (Ministry of Corporate Affairs) Data Scraper for Intelli-Credit.

Extracts company masterdata, charges, legal filings, and compliance status
from MCA21 portal (www.mca.gov.in).

IMPORTANT: Web scraping MCA portal requires handling CAPTCHAs and may be
against ToS. In production, use authorized MCA data API providers like:
- Signzy
- Karza
- Grid (by TrustID)

Author: Credit Intelligence System
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime, date
from typing import Any, Dict, List, Optional

from tools.mca_network_analyzer import analyze_mca_network


@dataclass
class MCACompanyMaster:
    """Company master data from MCA."""
    cin: str
    company_name: str
    company_status: str  # Active/Strike Off/Amalgamated/Dissolved
    company_class: str  # Private/Public/OPC
    company_category: str  # Company limited by shares/guarantee
    date_of_incorporation: str  # YYYY-MM-DD
    registered_state: str
    roc_code: str  # Registrar of Companies
    authorized_capital: float  # In INR (convert to Crores)
    paid_up_capital: float
    listed_status: bool
    date_of_last_agm: Optional[str]
    date_of_balance_sheet: Optional[str]
    email: str
    registered_address: str


@dataclass
class MCACharge:
    """Charge (security) registered with MCA."""
    charge_id: str
    charge_holder_name: str
    charge_amount: float  # In Crores
    charge_creation_date: str
    charge_modification_date: Optional[str]
    charge_satisfaction_date: Optional[str]  # If closed
    charge_status: str  # Outstanding/Satisfied/Partial
    assets_charged: str
    charge_type: str  # Hypothecation/Mortgage/Pledge


@dataclass
class MCADirector:
    """Director information from MCA."""
    din: str  # Director Identification Number
    name: str
    designation: str  # Director/MD/CEO
    appointment_date: str
    cessation_date: Optional[str]
    is_disqualified: bool
    disqualification_reason: Optional[str]


@dataclass
class MCAFiling:
    """Recent MCA filings."""
    form_type: str  # AOC-4, MGT-7, DIR-12, etc
    filing_date: str
    description: str
    status: str  # Filed/Pending


@dataclass
class MCAComplianceStatus:
    """Compliance status with MCA."""
    annual_return_filed: bool  # MGT-7
    financial_statements_filed: bool  # AOC-4
    last_ar_filing_date: Optional[str]
    last_fs_filing_date: Optional[str]
    pending_filings: int
    strike_off_notice: bool
    strike_off_reason: Optional[str]
    defaulter_list: bool


@dataclass
class MCAReport:
    """Complete MCA report."""
    cin: str
    fetch_date: str
    company_master: MCACompanyMaster
    directors: List[MCADirector]
    charges: List[MCACharge]
    recent_filings: List[MCAFiling]
    compliance_status: MCAComplianceStatus
    red_flags: List[str]


class MCAAPIError(Exception):
    """Exception for MCA API/scraper errors."""
    pass


# ─── Mock Data Generation ────────────────────────────────────────────────────

def _generate_mock_mca_data(
    company_name: str,
    cin: Optional[str] = None,
    scenario: str = "clean",
) -> MCAReport:
    """Generate mock MCA data for testing."""

    cin = cin or f"U{12345}{company_name[:2].upper()}2015PTC{123456}"
    today = date.today()

    if scenario == "clean":
        company_master = MCACompanyMaster(
            cin=cin,
            company_name=company_name,
            company_status="Active",
            company_class="Private",
            company_category="Company limited by shares",
            date_of_incorporation="2015-06-15",
            registered_state="Maharashtra",
            roc_code="RoC-Mumbai",
            authorized_capital=10_00_00_000,  # 10 Cr
            paid_up_capital=7_50_00_000,  # 7.5 Cr
            listed_status=False,
            date_of_last_agm="2023-09-30",
            date_of_balance_sheet="2024-03-31",
            email=f"info@{company_name.lower().replace(' ', '')}.com",
            registered_address="123 Industrial Area, Mumbai, Maharashtra 400001",
        )

        directors = [
            MCADirector(
                din="01234567",
                name="Rajesh Kumar",
                designation="Managing Director",
                appointment_date="2015-06-15",
                cessation_date=None,
                is_disqualified=False,
                disqualification_reason=None,
            ),
            MCADirector(
                din="01234568",
                name="Priya Sharma",
                designation="Director",
                appointment_date="2015-06-15",
                cessation_date=None,
                is_disqualified=False,
                disqualification_reason=None,
            ),
        ]

        charges = [
            MCACharge(
                charge_id="CHG001",
                charge_holder_name="State Bank of India",
                charge_amount=5.0,
                charge_creation_date="2020-01-15",
                charge_modification_date=None,
                charge_satisfaction_date=None,
                charge_status="Outstanding",
                assets_charged="Plant and Machinery, Stock",
                charge_type="Hypothecation",
            ),
        ]

        recent_filings = [
            MCAFiling(
                form_type="AOC-4",
                filing_date="2024-10-30",
                description="Financial Statements FY 2023-24",
                status="Filed",
            ),
            MCAFiling(
                form_type="MGT-7",
                filing_date="2024-10-30",
                description="Annual Return FY 2023-24",
                status="Filed",
            ),
        ]

        compliance_status = MCAComplianceStatus(
            annual_return_filed=True,
            financial_statements_filed=True,
            last_ar_filing_date="2024-10-30",
            last_fs_filing_date="2024-10-30",
            pending_filings=0,
            strike_off_notice=False,
            strike_off_reason=None,
            defaulter_list=False,
        )

        red_flags = []

    elif scenario == "defaulter":
        company_master = MCACompanyMaster(
            cin=cin,
            company_name=company_name,
            company_status="Active",
            company_class="Private",
            company_category="Company limited by shares",
            date_of_incorporation="2018-03-10",
            registered_state="Karnataka",
            roc_code="RoC-Bangalore",
            authorized_capital=5_00_00_000,
            paid_up_capital=2_00_00_000,
            listed_status=False,
            date_of_last_agm="2022-09-30",
            date_of_balance_sheet="2023-03-31",
            email=f"info@{company_name.lower().replace(' ', '')}.com",
            registered_address="45B Tech Park, Bangalore, Karnataka 560001",
        )

        directors = [
            MCADirector(
                din="09876543",
                name="Amit Patel",
                designation="Director",
                appointment_date="2018-03-10",
                cessation_date=None,
                is_disqualified=True,
                disqualification_reason="Section 164(2)(a) - Default in filing",
            ),
        ]

        charges = [
            MCACharge(
                charge_id="CHG002",
                charge_holder_name="HDFC Bank",
                charge_amount=3.5,
                charge_creation_date="2019-05-20",
                charge_modification_date="2022-08-15",
                charge_satisfaction_date=None,
                charge_status="Outstanding",
                assets_charged="Factory Land and Building",
                charge_type="Mortgage",
            ),
        ]

        recent_filings = [
            MCAFiling(
                form_type="AOC-4",
                filing_date="2023-12-15",
                description="Financial Statements FY 2022-23 (Delayed)",
                status="Filed",
            ),
        ]

        compliance_status = MCAComplianceStatus(
            annual_return_filed=False,
            financial_statements_filed=True,
            last_ar_filing_date="2023-08-20",
            last_fs_filing_date="2023-12-15",
            pending_filings=2,
            strike_off_notice=False,
            strike_off_reason=None,
            defaulter_list=True,
        )

        red_flags = [
            "Director disqualified under Section 164(2)(a)",
            "Company on MCA defaulter list for non-filing",
            "Pending filings: 2",
            "Annual return not filed for FY 2023-24",
        ]

    else:  # strike_off scenario
        company_master = MCACompanyMaster(
            cin=cin,
            company_name=company_name,
            company_status="Active (Under Process of Striking Off)",
            company_class="Private",
            company_category="Company limited by shares",
            date_of_incorporation="2017-08-01",
            registered_state="Delhi",
            roc_code="RoC-Delhi",
            authorized_capital=1_00_00_000,
            paid_up_capital=50_00_000,
            listed_status=False,
            date_of_last_agm="2021-09-30",
            date_of_balance_sheet="2022-03-31",
            email="",
            registered_address="Unknown",
        )

        directors = [
            MCADirector(
                din="11223344",
                name="Unknown",
                designation="Director",
                appointment_date="2017-08-01",
                cessation_date="2022-01-01",
                is_disqualified=False,
                disqualification_reason=None,
            ),
        ]

        charges = []
        recent_filings = []

        compliance_status = MCAComplianceStatus(
            annual_return_filed=False,
            financial_statements_filed=False,
            last_ar_filing_date="2022-10-01",
            last_fs_filing_date="2022-10-01",
            pending_filings=5,
            strike_off_notice=True,
            strike_off_reason="Non-filing of documents for 2 consecutive years",
            defaulter_list=True,
        )

        red_flags = [
            "CRITICAL: Strike-off notice issued by ROC",
            "Company status: Under Process of Striking Off",
            "No filings for last 2 years",
            "All directors have resigned/ceased",
            "Company on MCA defaulter list",
        ]

    return MCAReport(
        cin=cin,
        fetch_date=today.isoformat(),
        company_master=company_master,
        directors=directors,
        charges=charges,
        recent_filings=recent_filings,
        compliance_status=compliance_status,
        red_flags=red_flags,
    )


# ─── Main API Functions ──────────────────────────────────────────────────────

def fetch_mca_report(
    cin: str,
    company_name: Optional[str] = None,
    use_mock: bool = True,
    mock_scenario: str = "clean",
) -> MCAReport:
    """
    Fetch MCA report for a company.

    Args:
        cin: Corporate Identity Number (required)
        company_name: Company name (optional, for mock data)
        use_mock: If True, return mock data for testing
        mock_scenario: "clean", "defaulter", or "strike_off"

    Returns:
        MCAReport with company data and compliance status

    Raises:
        MCAAPIError: If API call fails or CIN not found
    """

    if use_mock:
        return _generate_mock_mca_data(
            company_name=company_name or "Test Company Pvt Ltd",
            cin=cin,
            scenario=mock_scenario,
        )

    else:
        # ─── PRODUCTION CODE ─────────────────────────────────────────────────
        """
        PRODUCTION IMPLEMENTATION GUIDE:

        Option 1: Use MCA Data API Provider (Recommended)
        --------------------------------------------------
        Providers: Signzy, Karza, Grid, IDfy

        import requests

        api_key = os.getenv("MCA_API_KEY")  # e.g., Signzy API key
        endpoint = os.getenv("MCA_API_ENDPOINT")

        response = requests.post(
            f"{endpoint}/v2/mca/corporate",
            headers={"Authorization": f"Bearer {api_key}"},
            json={"cin": cin},
            timeout=60,
        )

        if response.status_code != 200:
            raise MCAAPIError(f"MCA API error: {response.text}")

        data = response.json()

        return MCAReport(
            cin=cin,
            fetch_date=datetime.now().isoformat(),
            company_master=MCACompanyMaster(...),  # Map from API response
            directors=[MCADirector(...) for d in data["directors"]],
            charges=[MCACharge(...) for c in data["charges"]],
            recent_filings=[MCAFiling(...) for f in data["filings"]],
            compliance_status=MCAComplianceStatus(...),
            red_flags=_identify_red_flags(data),
        )


        Option 2: Web Scraping MCA Portal (Not Recommended)
        -----------------------------------------------------
        - Requires handling CAPTCHA
        - Requires managing sessions
        - May violate ToS
        - Not reliable for production

        DO NOT USE SCRAPING IN PRODUCTION.
        """
        raise MCAAPIError(
            "Production MCA API not configured. "
            "Set use_mock=True for testing or implement API integration with "
            "authorized providers like Signzy, Karza, or Grid."
        )


def mca_report_to_dict(report: MCAReport) -> Dict[str, Any]:
    """Convert MCA report to dictionary for JSON serialization."""
    return {
        "cin": report.cin,
        "fetch_date": report.fetch_date,
        "company_master": {
            "company_name": report.company_master.company_name,
            "company_status": report.company_master.company_status,
            "company_class": report.company_master.company_class,
            "date_of_incorporation": report.company_master.date_of_incorporation,
            "registered_state": report.company_master.registered_state,
            "roc_code": report.company_master.roc_code,
            "authorized_capital_cr": report.company_master.authorized_capital / 1_00_00_000,
            "paid_up_capital_cr": report.company_master.paid_up_capital / 1_00_00_000,
            "listed": report.company_master.listed_status,
            "date_of_last_agm": report.company_master.date_of_last_agm,
            "date_of_balance_sheet": report.company_master.date_of_balance_sheet,
            "registered_address": report.company_master.registered_address,
        },
        "directors": [
            {
                "din": d.din,
                "name": d.name,
                "designation": d.designation,
                "appointment_date": d.appointment_date,
                "cessation_date": d.cessation_date,
                "is_disqualified": d.is_disqualified,
                "disqualification_reason": d.disqualification_reason,
            }
            for d in report.directors
        ],
        "charges": [
            {
                "charge_id": c.charge_id,
                "holder": c.charge_holder_name,
                "amount_cr": c.charge_amount,
                "creation_date": c.charge_creation_date,
                "status": c.charge_status,
                "assets_charged": c.assets_charged,
                "charge_type": c.charge_type,
            }
            for c in report.charges
        ],
        "recent_filings": [
            {
                "form_type": f.form_type,
                "filing_date": f.filing_date,
                "description": f.description,
                "status": f.status,
            }
            for f in report.recent_filings
        ],
        "compliance_status": {
            "annual_return_filed": report.compliance_status.annual_return_filed,
            "financial_statements_filed": report.compliance_status.financial_statements_filed,
            "last_ar_filing_date": report.compliance_status.last_ar_filing_date,
            "last_fs_filing_date": report.compliance_status.last_fs_filing_date,
            "pending_filings": report.compliance_status.pending_filings,
            "strike_off_notice": report.compliance_status.strike_off_notice,
            "strike_off_reason": report.compliance_status.strike_off_reason,
            "defaulter_list": report.compliance_status.defaulter_list,
        },
        "red_flags": report.red_flags,
    }


async def run_mca_scraper(company_cin: str, company_name: Optional[str] = None) -> Dict[str, Any]:
    """
    Enhanced MCA scraper that includes network risk analysis.
    """
    mca_report = fetch_mca_report(cin=company_cin, company_name=company_name)
    
    director_dins = [d.din for d in mca_report.directors]
    
    # ── NEW: Network analysis ──────────────────────────────────────────
    network_analysis = await analyze_mca_network(
        company_cin=company_cin,
        director_dins=director_dins,
    )
    
    # We can either return mca_report_to_dict or a custom dict. Based on existing pipeline:
    return {
        "company_status": mca_report.company_master.company_status,
        "incorporation_date": mca_report.company_master.date_of_incorporation,
        "authorized_capital": mca_report.company_master.authorized_capital,
        "paid_up_capital": mca_report.company_master.paid_up_capital,
        "total_directors": len(mca_report.directors),
        "disqualified_directors": sum(1 for d in mca_report.directors if d.is_disqualified),
        "total_charges": len(mca_report.charges),
        "unsatisfied_charges": sum(1 for c in mca_report.charges if c.charge_status == "Outstanding" or c.charge_status == "UNSATISFIED"),
        "strike_off_notice": mca_report.compliance_status.strike_off_notice,
        "defaulter_list": mca_report.compliance_status.defaulter_list,
        "director_network": network_analysis,
        "promoter_integrity_score": network_analysis.get("promoter_integrity_score", 75),
        "network_risk_level": network_analysis.get("network_risk_level", "LOW"),
        "nclt_linked_directors": len(network_analysis.get("connected_nclt_entities", [])) > 0,
        "shell_company_links": network_analysis.get("shell_company_links", 0),
    }


# ─── Helper Functions ────────────────────────────────────────────────────────

def calculate_company_age(incorporation_date_str: str) -> float:
    """Calculate company age in years from incorporation date."""
    try:
        inc_date = datetime.strptime(incorporation_date_str, "%Y-%m-%d").date()
        age_days = (date.today() - inc_date).days
        return max(age_days / 365.25, 0)
    except Exception:
        return 0.0


# ─── Example Usage ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Test with mock data
    print("=" * 60)
    print("SCENARIO 1: Clean Company")
    print("=" * 60)
    report1 = fetch_mca_report(
        cin="U12345MH2015PTC123456",
        company_name="ABC Manufacturing Pvt Ltd",
        use_mock=True,
        mock_scenario="clean",
    )
    print(f"Company: {report1.company_master.company_name}")
    print(f"Status: {report1.company_master.company_status}")
    print(f"Paid-up Capital: Rs.{report1.company_master.paid_up_capital / 1_00_00_000:.2f} Cr")
    print(f"Directors: {len(report1.directors)}")
    print(f"Charges: {len(report1.charges)}")
    print(f"Red Flags: {len(report1.red_flags)}")
    if report1.red_flags:
        for flag in report1.red_flags:
            print(f"  - {flag}")

    print("\n" + "=" * 60)
    print("SCENARIO 2: Defaulter Company")
    print("=" * 60)
    report2 = fetch_mca_report(
        cin="U67890KA2018PTC234567",
        company_name="XYZ Tech Pvt Ltd",
        use_mock=True,
        mock_scenario="defaulter",
    )
    print(f"Company: {report2.company_master.company_name}")
    print(f"Status: {report2.company_master.company_status}")
    print(f"Compliance - AR Filed: {report2.compliance_status.annual_return_filed}")
    print(f"Disqualified Directors: {sum(1 for d in report2.directors if d.is_disqualified)}")
    print(f"Red Flags: {len(report2.red_flags)}")
    if report2.red_flags:
        for flag in report2.red_flags:
            print(f"  - {flag}")
