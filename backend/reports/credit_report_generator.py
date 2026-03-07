"""
Credit Report Generator — Comprehensive Credit Assessment Report

Generates formatted credit report with:
1. Executive Summary (TL;DR with decision)
2. Company Profile (basic info, sector, age, structure)
3. Financial Analysis (P&L, balance sheet, ratios)
4. Risk Assessment (red flags, risk matrix, scoring)
5. Verification Summary (data sources validated)
6. Collateral Analysis (security coverage)
7. Decision & Conditions (approval/rejection)
8. Monitoring Setup (post-disbursement plan)

Output Formats:
- JSON (machine-readable, API integration)
- Formatted Text Report (human-readable, email/print)
- HTML (web view)

Author: Credit Intelligence System
"""
from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class BorrowerProfile:
    """Borrower profile section."""
    company_name: str
    cin: str
    gstin: str
    pan: str
    incorporation_date: str
    company_age_years: float
    sector: str
    registered_office: str
    directors: List[str]
    promoters: List[str]


@dataclass
class FinancialSummary:
    """Financial summary section."""
    revenue_cr: float
    ebitda_cr: float
    net_profit_cr: float
    total_assets_cr: float
    net_worth_cr: float
    total_debt_cr: float
    
    # Ratios
    debt_equity_ratio: float
    current_ratio: float
    roe_percent: float
    roa_percent: float
    ebitda_margin_percent: float


@dataclass
class LoanDetails:
    """Loan request details."""
    loan_amount_cr: float
    loan_purpose: str
    requested_tenure_months: int
    proposed_roi_percent: float
    collateral_offered: str
    collateral_value_cr: float


@dataclass
class RiskAssessment:
    """Risk assessment section."""
    credit_score: int
    risk_grade: str  # AAA, AA, A, BBB, BB, B, C, D
    probability_of_default_pct: float
    loss_given_default_pct: float
    expected_loss_cr: float
    
    # Red flags
    red_flags_count: int
    critical_flags: List[str]
    high_flags: List[str]
    
    # Risk matrix scores
    character_score: int
    capacity_score: int
    capital_score: int
    collateral_score: int
    conditions_score: int
    
    overall_recommendation: str  # APPROVE, CONDITIONAL_APPROVE, REJECT


@dataclass
class VerificationSummary:
    """Data verification summary."""
    cibil_verified: bool
    gst_verified: bool
    mca_verified: bool
    bank_statements_verified: bool
    itr_verified: bool
    collateral_verified: bool
    
    data_quality_score: float  # 0-100
    confidence_level: str  # HIGH, MEDIUM, LOW


@dataclass
class DecisionOutput:
    """Final credit decision."""
    decision: str  # APPROVED, REJECTED, CONDITIONAL_APPROVED, DEFERRED
    approved_amount_cr: Optional[float]
    approved_tenure_months: Optional[int]
    approved_roi_percent: Optional[float]
    
    conditions: List[str]
    rejection_reasons: List[str]
    
    security_required: str
    guarantors_required: int
    
    approved_by: str
    approval_date: str


@dataclass
class MonitoringPlan:
    """Post-disbursement monitoring plan."""
    monitoring_frequency: str  # MONTHLY, QUARTERLY
    
    documents_required: List[str]
    covenants_to_monitor: List[str]
    early_warning_indicators: List[str]
    
    review_date: str
    account_manager: str


@dataclass
class CreditReport:
    """Complete credit assessment report."""
    report_id: str
    generated_date: str
    borrower_profile: BorrowerProfile
    financial_summary: FinancialSummary
    loan_details: LoanDetails
    risk_assessment: RiskAssessment
    verification_summary: VerificationSummary
    decision: DecisionOutput
    monitoring_plan: Optional[MonitoringPlan]
    
    # Metadata
    assessed_by: str = "Intelli-Credits AI System"
    report_version: str = "1.0"


def generate_credit_report(
    borrower_data: Dict[str, Any],
    financial_data: Dict[str, Any],
    loan_request: Dict[str, Any],
    risk_assessment_data: Dict[str, Any],
    verification_data: Dict[str, Any],
    decision_data: Dict[str, Any],
    monitoring_data: Optional[Dict[str, Any]] = None,
) -> CreditReport:
    """
    Generate comprehensive credit report.
    
    Args:
        borrower_data: Company profile information
        financial_data: Financial statements and ratios
        loan_request: Loan details
        risk_assessment_data: Risk scores and flags
        verification_data: Data verification status
        decision_data: Credit decision details
        monitoring_data: Post-disbursement monitoring plan
        
    Returns:
        CreditReport dataclass
    """
    logger.info(f"📄 Generating credit report for: {borrower_data.get('company_name')}")
    
    # Build report sections
    borrower_profile = BorrowerProfile(
        company_name=borrower_data.get('company_name', ''),
        cin=borrower_data.get('cin', ''),
        gstin=borrower_data.get('gstin', ''),
        pan=borrower_data.get('pan', ''),
        incorporation_date=borrower_data.get('incorporation_date', ''),
        company_age_years=borrower_data.get('company_age_years', 0),
        sector=borrower_data.get('sector', ''),
        registered_office=borrower_data.get('registered_office', ''),
        directors=borrower_data.get('directors', []),
        promoters=borrower_data.get('promoters', []),
    )
    
    financial_summary = FinancialSummary(
        revenue_cr=financial_data.get('revenue_cr', 0),
        ebitda_cr=financial_data.get('ebitda_cr', 0),
        net_profit_cr=financial_data.get('net_profit_cr', 0),
        total_assets_cr=financial_data.get('total_assets_cr', 0),
        net_worth_cr=financial_data.get('net_worth_cr', 0),
        total_debt_cr=financial_data.get('total_debt_cr', 0),
        debt_equity_ratio=financial_data.get('debt_equity_ratio', 0),
        current_ratio=financial_data.get('current_ratio', 0),
        roe_percent=financial_data.get('roe_percent', 0),
        roa_percent=financial_data.get('roa_percent', 0),
        ebitda_margin_percent=financial_data.get('ebitda_margin_percent', 0),
    )
    
    loan_details = LoanDetails(
        loan_amount_cr=loan_request.get('loan_amount_cr', 0),
        loan_purpose=loan_request.get('loan_purpose', ''),
        requested_tenure_months=loan_request.get('requested_tenure_months', 0),
        proposed_roi_percent=loan_request.get('proposed_roi_percent', 0),
        collateral_offered=loan_request.get('collateral_offered', ''),
        collateral_value_cr=loan_request.get('collateral_value_cr', 0),
    )
    
    risk_assessment = RiskAssessment(
        credit_score=risk_assessment_data.get('credit_score', 0),
        risk_grade=risk_assessment_data.get('risk_grade', ''),
        probability_of_default_pct=risk_assessment_data.get('probability_of_default_pct', 0),
        loss_given_default_pct=risk_assessment_data.get('loss_given_default_pct', 0),
        expected_loss_cr=risk_assessment_data.get('expected_loss_cr', 0),
        red_flags_count=risk_assessment_data.get('red_flags_count', 0),
        critical_flags=risk_assessment_data.get('critical_flags', []),
        high_flags=risk_assessment_data.get('high_flags', []),
        character_score=risk_assessment_data.get('character_score', 0),
        capacity_score=risk_assessment_data.get('capacity_score', 0),
        capital_score=risk_assessment_data.get('capital_score', 0),
        collateral_score=risk_assessment_data.get('collateral_score', 0),
        conditions_score=risk_assessment_data.get('conditions_score', 0),
        overall_recommendation=risk_assessment_data.get('overall_recommendation', ''),
    )
    
    verification_summary = VerificationSummary(
        cibil_verified=verification_data.get('cibil_verified', False),
        gst_verified=verification_data.get('gst_verified', False),
        mca_verified=verification_data.get('mca_verified', False),
        bank_statements_verified=verification_data.get('bank_statements_verified', False),
        itr_verified=verification_data.get('itr_verified', False),
        collateral_verified=verification_data.get('collateral_verified', False),
        data_quality_score=verification_data.get('data_quality_score', 0),
        confidence_level=verification_data.get('confidence_level', 'MEDIUM'),
    )
    
    decision = DecisionOutput(
        decision=decision_data.get('decision', ''),
        approved_amount_cr=decision_data.get('approved_amount_cr'),
        approved_tenure_months=decision_data.get('approved_tenure_months'),
        approved_roi_percent=decision_data.get('approved_roi_percent'),
        conditions=decision_data.get('conditions', []),
        rejection_reasons=decision_data.get('rejection_reasons', []),
        security_required=decision_data.get('security_required', ''),
        guarantors_required=decision_data.get('guarantors_required', 0),
        approved_by=decision_data.get('approved_by', 'Credit Committee'),
        approval_date=decision_data.get('approval_date', datetime.now().isoformat()),
    )
    
    monitoring_plan = None
    if monitoring_data and decision.decision in ["APPROVED", "CONDITIONAL_APPROVED"]:
        monitoring_plan = MonitoringPlan(
            monitoring_frequency=monitoring_data.get('monitoring_frequency', 'QUARTERLY'),
            documents_required=monitoring_data.get('documents_required', []),
            covenants_to_monitor=monitoring_data.get('covenants_to_monitor', []),
            early_warning_indicators=monitoring_data.get('early_warning_indicators', []),
            review_date=monitoring_data.get('review_date', ''),
            account_manager=monitoring_data.get('account_manager', 'To be assigned'),
        )
    
    report_id = f"CR-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    report = CreditReport(
        report_id=report_id,
        generated_date=datetime.now().isoformat(),
        borrower_profile=borrower_profile,
        financial_summary=financial_summary,
        loan_details=loan_details,
        risk_assessment=risk_assessment,
        verification_summary=verification_summary,
        decision=decision,
        monitoring_plan=monitoring_plan,
    )
    
    logger.info(f"✅ Credit report generated | ID: {report_id} | Decision: {decision.decision}")
    
    return report


def export_report_json(report: CreditReport) -> str:
    """Export report as JSON string."""
    return json.dumps(asdict(report), indent=2, default=str)


def export_report_text(report: CreditReport) -> str:
    """Export report as formatted text."""
    
    text = []
    text.append("="*80)
    text.append("CREDIT ASSESSMENT REPORT")
    text.append("="*80)
    text.append(f"Report ID: {report.report_id}")
    text.append(f"Generated: {report.generated_date}")
    text.append(f"Assessed By: {report.assessed_by}")
    text.append("")
    
    # Executive Summary
    text.append("─" * 80)
    text.append("1. EXECUTIVE SUMMARY")
    text.append("─" * 80)
    text.append(f"Borrower: {report.borrower_profile.company_name}")
    text.append(f"Loan Amount Requested: ₹{report.loan_details.loan_amount_cr:.2f} Cr")
    text.append(f"Credit Score: {report.risk_assessment.credit_score}/900")
    text.append(f"Risk Grade: {report.risk_assessment.risk_grade}")
    text.append(f"")
    text.append(f"DECISION: {report.decision.decision}")
    if report.decision.decision in ["APPROVED", "CONDITIONAL_APPROVED"]:
        text.append(f"Approved Amount: ₹{report.decision.approved_amount_cr:.2f} Cr")
        text.append(f"Tenure: {report.decision.approved_tenure_months} months")
        text.append(f"ROI: {report.decision.approved_roi_percent:.2f}%")
    elif report.decision.rejection_reasons:
        text.append(f"Rejection Reasons: {'; '.join(report.decision.rejection_reasons)}")
    text.append("")
    
    # Company Profile
    text.append("─" * 80)
    text.append("2. COMPANY PROFILE")
    text.append("─" * 80)
    text.append(f"Company Name: {report.borrower_profile.company_name}")
    text.append(f"CIN: {report.borrower_profile.cin}")
    text.append(f"GSTIN: {report.borrower_profile.gstin}")
    text.append(f"PAN: {report.borrower_profile.pan}")
    text.append(f"Incorporation Date: {report.borrower_profile.incorporation_date}")
    text.append(f"Company Age: {report.borrower_profile.company_age_years:.1f} years")
    text.append(f"Sector: {report.borrower_profile.sector}")
    text.append(f"Registered Office: {report.borrower_profile.registered_office}")
    text.append(f"Directors: {', '.join(report.borrower_profile.directors)}")
    text.append("")
    
    # Financial Analysis
    text.append("─" * 80)
    text.append("3. FINANCIAL ANALYSIS")
    text.append("─" * 80)
    text.append(f"Revenue: ₹{report.financial_summary.revenue_cr:.2f} Cr")
    text.append(f"EBITDA: ₹{report.financial_summary.ebitda_cr:.2f} Cr ({report.financial_summary.ebitda_margin_percent:.1f}%)")
    text.append(f"Net Profit: ₹{report.financial_summary.net_profit_cr:.2f} Cr")
    text.append(f"Total Assets: ₹{report.financial_summary.total_assets_cr:.2f} Cr")
    text.append(f"Net Worth: ₹{report.financial_summary.net_worth_cr:.2f} Cr")
    text.append(f"Total Debt: ₹{report.financial_summary.total_debt_cr:.2f} Cr")
    text.append("")
    text.append("Key Ratios:")
    text.append(f"  Debt/Equity: {report.financial_summary.debt_equity_ratio:.2f}x")
    text.append(f"  Current Ratio: {report.financial_summary.current_ratio:.2f}x")
    text.append(f"  ROE: {report.financial_summary.roe_percent:.2f}%")
    text.append(f"  ROA: {report.financial_summary.roa_percent:.2f}%")
    text.append("")
    
    # Risk Assessment
    text.append("─" * 80)
    text.append("4. RISK ASSESSMENT")
    text.append("─" * 80)
    text.append(f"Credit Score: {report.risk_assessment.credit_score}/900")
    text.append(f"Risk Grade: {report.risk_assessment.risk_grade}")
    text.append(f"Probability of Default: {report.risk_assessment.probability_of_default_pct:.2f}%")
    text.append(f"Expected Loss: ₹{report.risk_assessment.expected_loss_cr:.2f} Cr")
    text.append("")
    text.append("5Cs Analysis:")
    text.append(f"  Character: {report.risk_assessment.character_score}/100")
    text.append(f"  Capacity: {report.risk_assessment.capacity_score}/100")
    text.append(f"  Capital: {report.risk_assessment.capital_score}/100")
    text.append(f"  Collateral: {report.risk_assessment.collateral_score}/100")
    text.append(f"  Conditions: {report.risk_assessment.conditions_score}/100")
    text.append("")
    text.append(f"Red Flags: {report.risk_assessment.red_flags_count}")
    if report.risk_assessment.critical_flags:
        text.append(f"  CRITICAL: {', '.join(report.risk_assessment.critical_flags)}")
    if report.risk_assessment.high_flags:
        text.append(f"  HIGH: {', '.join(report.risk_assessment.high_flags)}")
    text.append("")
    
    # Verification Summary
    text.append("─" * 80)
    text.append("5. VERIFICATION SUMMARY")
    text.append("─" * 80)
    text.append(f"CIBIL: {'✓' if report.verification_summary.cibil_verified else '✗'}")
    text.append(f"GST: {'✓' if report.verification_summary.gst_verified else '✗'}")
    text.append(f"MCA: {'✓' if report.verification_summary.mca_verified else '✗'}")
    text.append(f"Bank Statements: {'✓' if report.verification_summary.bank_statements_verified else '✗'}")
    text.append(f"ITR: {'✓' if report.verification_summary.itr_verified else '✗'}")
    text.append(f"Collateral: {'✓' if report.verification_summary.collateral_verified else '✗'}")
    text.append(f"")
    text.append(f"Data Quality Score: {report.verification_summary.data_quality_score:.1f}/100")
    text.append(f"Confidence Level: {report.verification_summary.confidence_level}")
    text.append("")
    
    # Collateral Analysis
    text.append("─" * 80)
    text.append("6. COLLATERAL ANALYSIS")
    text.append("─" * 80)
    text.append(f"Collateral Offered: {report.loan_details.collateral_offered}")
    text.append(f"Collateral Value: ₹{report.loan_details.collateral_value_cr:.2f} Cr")
    text.append(f"Loan Amount: ₹{report.loan_details.loan_amount_cr:.2f} Cr")
    ltv = (report.loan_details.loan_amount_cr / report.loan_details.collateral_value_cr * 100) if report.loan_details.collateral_value_cr > 0 else 0
    text.append(f"LTV Ratio: {ltv:.1f}%")
    text.append(f"Security Coverage: {report.decision.security_required}")
    text.append("")
    
    # Decision & Conditions
    text.append("─" * 80)
    text.append("7. DECISION & CONDITIONS")
    text.append("─" * 80)
    text.append(f"Decision: {report.decision.decision}")
    text.append(f"Approved By: {report.decision.approved_by}")
    text.append(f"Approval Date: {report.decision.approval_date}")
    text.append("")
    if report.decision.conditions:
        text.append("Conditions:")
        for i, condition in enumerate(report.decision.conditions, 1):
            text.append(f"  {i}. {condition}")
        text.append("")
    if report.decision.rejection_reasons:
        text.append("Rejection Reasons:")
        for i, reason in enumerate(report.decision.rejection_reasons, 1):
            text.append(f"  {i}. {reason}")
        text.append("")
    
    # Monitoring Setup
    if report.monitoring_plan:
        text.append("─" * 80)
        text.append("8. MONITORING SETUP")
        text.append("─" * 80)
        text.append(f"Monitoring Frequency: {report.monitoring_plan.monitoring_frequency}")
        text.append(f"Account Manager: {report.monitoring_plan.account_manager}")
        text.append(f"Next Review Date: {report.monitoring_plan.review_date}")
        text.append("")
        if report.monitoring_plan.documents_required:
            text.append("Documents Required:")
            for doc in report.monitoring_plan.documents_required:
                text.append(f"  • {doc}")
            text.append("")
        if report.monitoring_plan.covenants_to_monitor:
            text.append("Covenants to Monitor:")
            for covenant in report.monitoring_plan.covenants_to_monitor:
                text.append(f"  • {covenant}")
            text.append("")
    
    text.append("="*80)
    text.append("END OF REPORT")
    text.append("="*80)
    
    return "\n".join(text)


# ─── Integration Example ─────────────────────────────────────────────────────

async def main_example():
    """Example usage."""
    
    # Sample data
    borrower_data = {
        "company_name": "ABC Manufacturing Ltd",
        "cin": "U12345MH2015PTC123456",
        "gstin": "27AAAAA0000A1Z5",
        "pan": "AAAAA0000A",
        "incorporation_date": "2015-03-15",
        "company_age_years": 8.5,
        "sector": "Manufacturing - Auto Components",
        "registered_office": "Mumbai, Maharashtra",
        "directors": ["Mr. Anil Kumar", "Ms. Priya Sharma"],
        "promoters": ["Mr. Anil Kumar (60%)", "Ms. Priya Sharma (40%)"],
    }
    
    financial_data = {
        "revenue_cr": 120.5,
        "ebitda_cr": 18.2,
        "net_profit_cr": 8.5,
        "total_assets_cr": 95.0,
        "net_worth_cr": 45.0,
        "total_debt_cr": 40.0,
        "debt_equity_ratio": 0.89,
        "current_ratio": 1.8,
        "roe_percent": 18.9,
        "roa_percent": 8.9,
        "ebitda_margin_percent": 15.1,
    }
    
    loan_request = {
        "loan_amount_cr": 15.0,
        "loan_purpose": "Term Loan for capacity expansion",
        "requested_tenure_months": 60,
        "proposed_roi_percent": 10.5,
        "collateral_offered": "Land & Building + Plant & Machinery",
        "collateral_value_cr": 25.0,
    }
    
    risk_assessment_data = {
        "credit_score": 780,
        "risk_grade": "A",
        "probability_of_default_pct": 2.5,
        "loss_given_default_pct": 30.0,
        "expected_loss_cr": 0.11,
        "red_flags_count": 0,
        "critical_flags": [],
        "high_flags": [],
        "character_score": 85,
        "capacity_score": 82,
        "capital_score": 78,
        "collateral_score": 90,
        "conditions_score": 75,
        "overall_recommendation": "APPROVE",
    }
    
    verification_data = {
        "cibil_verified": True,
        "gst_verified": True,
        "mca_verified": True,
        "bank_statements_verified": True,
        "itr_verified": True,
        "collateral_verified": True,
        "data_quality_score": 92.0,
        "confidence_level": "HIGH",
    }
    
    decision_data = {
        "decision": "APPROVED",
        "approved_amount_cr": 15.0,
        "approved_tenure_months": 60,
        "approved_roi_percent": 10.5,
        "conditions": [
            "Maintain DSCR > 1.25x throughout loan tenure",
            "Submit audited financials within 90 days of FY end",
            "Create first charge on all fixed assets",
            "Personal guarantee from both promoters",
        ],
        "rejection_reasons": [],
        "security_required": "First charge on Land, Building, Plant & Machinery",
        "guarantors_required": 2,
        "approved_by": "Credit Committee - Level 2",
        "approval_date": datetime.now().isoformat(),
    }
    
    monitoring_data = {
        "monitoring_frequency": "QUARTERLY",
        "documents_required": [
            "Quarterly audited financials",
            "Stock statements",
            "Debtor/Creditor statements",
            "GST returns (GSTR-3B, GSTR-1)",
        ],
        "covenants_to_monitor": [
            "DSCR ≥ 1.25x",
            "Debt-to-Equity ≤ 2.0x",
            "Current Ratio ≥ 1.5x",
        ],
        "early_warning_indicators": [
            "GST filing delays",
            "Cheque bounces",
            "Credit rating changes",
            "Director resignations",
        ],
        "review_date": "2024-07-01",
        "account_manager": "Rajesh Verma",
    }
    
    # Generate report
    report = generate_credit_report(
        borrower_data=borrower_data,
        financial_data=financial_data,
        loan_request=loan_request,
        risk_assessment_data=risk_assessment_data,
        verification_data=verification_data,
        decision_data=decision_data,
        monitoring_data=monitoring_data,
    )
    
    # Export as text
    print(export_report_text(report))
    
    # Export as JSON
    print("\n" + "="*80)
    print("JSON OUTPUT (first 500 chars):")
    print("="*80)
    json_output = export_report_json(report)
    print(json_output[:500] + "...")


if __name__ == "__main__":
    asyncio.run(main_example())
