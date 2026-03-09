"""
Explainable Scoring Agent — Transparent Credit Scoring for Indian Corporate Lending

This agent provides complete transparency in credit scoring:
- Every ratio shows its formula, company value, RBI floor, and industry benchmark
- All RBI circular references are cited
- Weight profiles adapt to loan type (working capital, term loan, project finance)
- Decision bands are clearly labeled as bank-configurable (NOT RBI mandated)
- Industry benchmarks from RBI OBSE data

Key Features:
1. Dynamic weight profiles based on loan type
2. RBI regulatory floors with exact circular citations
3. Industry percentile scoring using RBI OBSE data
4. Compliance deductions (RED flags -5pts, AMBER -2pts)
5. Full audit trail for every score

Author: Credit Intelligence System v3.0
Date: March 2026
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
from datetime import datetime, date
from typing import Any, Callable, Dict, List, Optional, Tuple

import google.generativeai as genai

from models.schemas import (
    RatioScore,
    RatioFlag,
    LoanType,
    CategorySubtotal,
    WeightProfile,
    ScorecardResult,
    ComplianceResult,
)

logger = logging.getLogger(__name__)


# ─── Helper Functions ─────────────────────────────────────────────────────────

def _log(agent: str, message: str, level: str = "INFO") -> Dict[str, Any]:
    """Create structured log entry."""
    return {
        "timestamp": datetime.now().strftime("%H:%M:%S"),
        "agent": agent,
        "message": message,
        "level": level,
    }


def _safe_float(value: Any, default: float = 0.0) -> float:
    """Safely convert to float."""
    try:
        return float(value) if value is not None else default
    except (ValueError, TypeError):
        return default


def _format_ratio(value: float, ratio_type: str = "multiplier") -> str:
    """Format ratio for display."""
    if ratio_type == "multiplier":
        return f"{value:.2f}x"
    elif ratio_type == "percentage":
        return f"{value:.1f}%"
    elif ratio_type == "decimal":
        return f"{value:.4f}"
    else:
        return f"{value:.2f}"


# ─── RBI OBSE Industry Benchmarks (FY2024) ───────────────────────────────────
# Source: RBI Finances of Non-Government Non-Financial Companies 2023-24

RBI_OBSE_BENCHMARKS = {
    "Manufacturing": {
        "debt_to_equity": {"p25": 0.8, "median": 1.5, "p75": 2.5},
        "ebitda_margin_pct": {"p25": 8.0, "median": 12.5, "p75": 18.0},
        "current_ratio": {"p25": 1.2, "median": 1.5, "p75": 2.0},
    },
    "Services": {
        "debt_to_equity": {"p25": 0.5, "median": 1.0, "p75": 2.0},
        "ebitda_margin_pct": {"p25": 10.0, "median": 15.0, "p75": 22.0},
        "current_ratio": {"p25": 1.3, "median": 1.7, "p75": 2.2},
    },
    "Trading": {
        "debt_to_equity": {"p25": 1.0, "median": 1.8, "p75": 3.0},
        "ebitda_margin_pct": {"p25": 4.0, "median": 7.5, "p75": 12.0},
        "current_ratio": {"p25": 1.1, "median": 1.4, "p75": 1.8},
    },
    "Construction": {
        "debt_to_equity": {"p25": 1.2, "median": 2.0, "p75": 3.5},
        "ebitda_margin_pct": {"p25": 6.0, "median": 10.0, "p75": 15.0},
        "current_ratio": {"p25": 1.0, "median": 1.3, "p75": 1.7},
    },
    "Default": {  # Fallback if sector not found
        "debt_to_equity": {"p25": 1.0, "median": 1.5, "p75": 2.5},
        "ebitda_margin_pct": {"p25": 8.0, "median": 12.0, "p75": 17.0},
        "current_ratio": {"p25": 1.2, "median": 1.5, "p75": 1.9},
    },
}


def get_industry_benchmark(sector: str, metric: str) -> Dict[str, float]:
    """Get RBI OBSE industry benchmark for a metric."""
    # Try exact match
    if sector in RBI_OBSE_BENCHMARKS and metric in RBI_OBSE_BENCHMARKS[sector]:
        return RBI_OBSE_BENCHMARKS[sector][metric]
    
    # Try fuzzy match
    sector_lower = sector.lower()
    for key in RBI_OBSE_BENCHMARKS.keys():
        if key.lower() in sector_lower or sector_lower in key.lower():
            if metric in RBI_OBSE_BENCHMARKS[key]:
                return RBI_OBSE_BENCHMARKS[key][metric]
    
    # Return default
    if metric in RBI_OBSE_BENCHMARKS["Default"]:
        return RBI_OBSE_BENCHMARKS["Default"][metric]
    
    return {"p25": 0.0, "median": 0.0, "p75": 0.0}


# ─── Weight Profile Selection ────────────────────────────────────────────────

def get_weight_profile(loan_type: LoanType) -> WeightProfile:
    """
    Get scoring weight profile based on loan type.
    
    RBI does not mandate these weights - they are based on credit underwriting
    best practices adapted to loan purpose.
    """
    if loan_type == LoanType.WORKING_CAPITAL:
        return WeightProfile(
            loan_type=LoanType.WORKING_CAPITAL,
            repayment_capacity=0.25,
            liquidity=0.35,  # Higher weight for WC as it's about cash flow
            leverage=0.15,
            profitability=0.15,
            banking_behavior=0.10,
            rationale="Working capital loans prioritize liquidity and cash conversion cycle. "
                     "Liquidity weighted 35% as receivables/inventory management is critical. "
                     "Repayment capacity 25% to ensure EMI serviceability."
        )
    elif loan_type == LoanType.PROJECT_FINANCE:
        return WeightProfile(
            loan_type=LoanType.PROJECT_FINANCE,
            repayment_capacity=0.40,  # Highest weight
            liquidity=0.10,  # Lower as project has own cash flows
            leverage=0.20,
            profitability=0.20,  # Project profitability critical
            banking_behavior=0.10,
            rationale="Project finance emphasizes repayment capacity (40%) as debt servicing "
                     "depends on project cash flows. Profitability 20% to assess project viability. "
                     "Liquidity less critical (10%) as project generates own cash."
        )
    else:  # TERM_LOAN (default)
        return WeightProfile(
            loan_type=LoanType.TERM_LOAN,
            repayment_capacity=0.35,
            liquidity=0.15,
            leverage=0.25,  # Higher weight as term loans increase debt burden
            profitability=0.15,
            banking_behavior=0.10,
            rationale="Term loans emphasize repayment capacity (35%) and leverage (25%). "
                     "Leverage critical as term debt increases balance sheet gearing. "
                     "Balanced approach suitable for capex and expansion loans."
        )


# ─── Ratio Calculation Functions ─────────────────────────────────────────────

def calculate_dscr(
    ebitda: float,
    annual_debt_service: float,
    data_source: str = "Financial Statements"
) -> RatioScore:
    """
    Calculate Debt Service Coverage Ratio with RBI floor.
    
    RBI Floor: 1.2x
    Source: RBI/2024-25/12 DoR.STR.REC.7/21.04.048/2024-25
    
    Below 1.2x = HARD REJECT
    1.2 to 1.5x = RED
    1.5 to 1.75x = AMBER
    Above 1.75x = GREEN
    """
    dscr_value = ebitda / annual_debt_service if annual_debt_service > 0 else 0.0
    
    # Determine flag
    if dscr_value < 1.2:
        flag = RatioFlag.HARD_REJECT
        reason = f"DSCR {dscr_value:.2f}x is below RBI mandatory floor of 1.2x. HARD REJECT as per regulatory requirement."
        score = 0.0
    elif dscr_value < 1.5:
        flag = RatioFlag.RED
        reason = f"DSCR {dscr_value:.2f}x is above RBI floor but in RED zone (1.2-1.5x). Debt servicing capacity is weak."
        score = 40.0
    elif dscr_value < 1.75:
        flag = RatioFlag.AMBER
        reason = f"DSCR {dscr_value:.2f}x is in AMBER zone (1.5-1.75x). Adequate but not strong debt servicing capacity."
        score = 70.0
    else:
        flag = RatioFlag.GREEN
        reason = f"DSCR {dscr_value:.2f}x is in GREEN zone (>1.75x). Strong debt servicing capacity with comfortable buffer."
        score = 100.0
    
    return RatioScore(
        parameter_name="Debt Service Coverage Ratio (DSCR)",
        category="Repayment Capacity",
        formula="EBITDA / (Annual Principal Repayment + Annual Interest)",
        company_value=round(dscr_value, 2),
        company_value_display=_format_ratio(dscr_value, "multiplier"),
        rbi_floor=1.2,
        rbi_floor_display="1.20x",
        rbi_source="RBI/2024-25/12 DoR.STR.REC.7/21.04.048/2024-25",
        rbi_mandated=True,
        score=score,
        flag=flag,
        reason=reason,
        data_source=data_source,
        benchmark_source="RBI Regulatory Floor",
    )


def calculate_current_ratio(
    current_assets: float,
    current_liabilities: float,
    data_source: str = "Balance Sheet"
) -> RatioScore:
    """
    Calculate Current Ratio with RBI floor.
    
    RBI Floor: 1.33x (Tandon Committee MPBF Method)
    Source: RBI Tandon Committee Report on Working Capital Finance
    
    Below 1.0x = RED
    1.0 to 1.33x = AMBER
    Above 1.5x = GREEN
    """
    current_ratio = current_assets / current_liabilities if current_liabilities > 0 else 0.0
    
    # Determine flag
    if current_ratio < 1.0:
        flag = RatioFlag.RED
        reason = f"Current Ratio {current_ratio:.2f}x is below 1.0x. Working capital deficit indicates liquidity stress."
        score = 30.0
    elif current_ratio < 1.33:
        flag = RatioFlag.AMBER
        reason = f"Current Ratio {current_ratio:.2f}x is below RBI guidance of 1.33x (Tandon Committee). Liquidity is tight."
        score = 60.0
    elif current_ratio < 1.5:
        flag = RatioFlag.GREEN
        reason = f"Current Ratio {current_ratio:.2f}x meets RBI guidance of 1.33x. Adequate liquidity position."
        score = 85.0
    else:
        flag = RatioFlag.GREEN
        reason = f"Current Ratio {current_ratio:.2f}x is strong (>1.5x). Comfortable liquidity cushion."
        score = 100.0
    
    return RatioScore(
        parameter_name="Current Ratio",
        category="Liquidity",
        formula="Current Assets / Current Liabilities",
        company_value=round(current_ratio, 2),
        company_value_display=_format_ratio(current_ratio, "multiplier"),
        rbi_floor=1.33,
        rbi_floor_display="1.33x",
        rbi_source="RBI Tandon Committee MPBF Method",
        rbi_mandated=False,  # Guidance, not hard mandate
        score=score,
        flag=flag,
        reason=reason,
        data_source=data_source,
        benchmark_source="RBI Tandon Committee",
    )


def calculate_for_ratio(
    total_emis: float,
    net_monthly_income: float,
    data_source: str = "Bank Statements"
) -> RatioScore:
    """
    Calculate Fixed Obligation to Income Ratio.
    
    RBI Guidance: 50%
    Source: RBI/2019-20/170 (Personal Loan Guidelines - adapted for corporate)
    
    Above 60% = RED
    50 to 60% = AMBER
    Below 40% = GREEN
    """
    for_ratio_pct = (total_emis / net_monthly_income * 100) if net_monthly_income > 0 else 100.0
    
    # Determine flag
    if for_ratio_pct > 60:
        flag = RatioFlag.RED
        reason = f"FOR Ratio {for_ratio_pct:.1f}% exceeds safe threshold. Over-leveraged - high EMI burden relative to income."
        score = 25.0
    elif for_ratio_pct > 50:
        flag = RatioFlag.AMBER
        reason = f"FOR Ratio {for_ratio_pct:.1f}% exceeds RBI guidance of 50%. Moderate EMI burden - monitor closely."
        score = 60.0
    elif for_ratio_pct > 40:
        flag = RatioFlag.GREEN
        reason = f"FOR Ratio {for_ratio_pct:.1f}% is within RBI guidance. Comfortable EMI serviceability."
        score = 85.0
    else:
        flag = RatioFlag.GREEN
        reason = f"FOR Ratio {for_ratio_pct:.1f}% is well below 40%. Excellent EMI serviceability with significant headroom."
        score = 100.0
    
    return RatioScore(
        parameter_name="Fixed Obligation Ratio (FOR)",
        category="Repayment Capacity",
        formula="(Total Monthly EMIs / Net Monthly Income) × 100",
        company_value=round(for_ratio_pct, 1),
        company_value_display=_format_ratio(for_ratio_pct, "percentage"),
        rbi_floor=50.0,
        rbi_floor_display="50%",
        rbi_source="RBI/2019-20/170 (Adapted for Corporate)",
        rbi_mandated=False,
        score=score,
        flag=flag,
        reason=reason,
        data_source=data_source,
        benchmark_source="RBI Guidance",
    )


def calculate_debt_to_equity(
    total_debt: float,
    tangible_net_worth: float,
    sector: str,
    data_source: str = "Financial Statements"
) -> RatioScore:
    """
    Calculate Debt to Equity ratio with industry benchmarking.
    
    NO RBI hard floor - scored relative to RBI OBSE industry median.
    Source: RBI Finances of Non-Government Non-Financial Companies 2023-24
    
    Above 4x = RED
    2 to 4x = AMBER
    Below 2x = GREEN (but compare to industry)
    """
    d_e_ratio = total_debt / tangible_net_worth if tangible_net_worth > 0 else 999.0
    
    # Get industry benchmark
    industry_bench = get_industry_benchmark(sector, "debt_to_equity")
    
    # Determine flag and score
    if d_e_ratio > 4.0:
        flag = RatioFlag.RED
        reason = f"D/E Ratio {d_e_ratio:.2f}x exceeds 4.0x. Highly leveraged with thin equity base."
        score = 20.0
    elif d_e_ratio > 2.0:
        flag = RatioFlag.AMBER
        reason = f"D/E Ratio {d_e_ratio:.2f}x is moderately high (2-4x). Monitor leverage levels."
        score = 50.0
    else:
        # Score relative to industry percentile
        if d_e_ratio > industry_bench["p75"]:
            score = 50.0
            reason = f"D/E Ratio {d_e_ratio:.2f}x is above industry 75th percentile ({industry_bench['p75']:.2f}x). Higher leverage than peers."
        elif d_e_ratio > industry_bench["median"]:
            score = 75.0
            reason = f"D/E Ratio {d_e_ratio:.2f}x is between industry median ({industry_bench['median']:.2f}x) and P75. On par with peers."
        elif d_e_ratio > industry_bench["p25"]:
            score = 90.0
            reason = f"D/E Ratio {d_e_ratio:.2f}x is between industry P25 ({industry_bench['p25']:.2f}x) and median. Better than average."
        else:
            score = 100.0
            reason = f"D/E Ratio {d_e_ratio:.2f}x is below industry 25th percentile ({industry_bench['p25']:.2f}x). Low leverage - strong equity base."
        flag = RatioFlag.GREEN
    
    return RatioScore(
        parameter_name="Debt to Equity Ratio",
        category="Leverage",
        formula="Total Debt / Tangible Net Worth",
        company_value=round(d_e_ratio, 2),
        company_value_display=_format_ratio(d_e_ratio, "multiplier"),
        rbi_floor=None,  # No RBI floor for D/E
        rbi_mandated=False,
        industry_median=industry_bench["median"],
        industry_p25=industry_bench["p25"],
        industry_p75=industry_bench["p75"],
        industry_source=f"RBI OBSE FY2024 - {sector}",
        score=score,
        flag=flag,
        reason=reason,
        data_source=data_source,
        benchmark_source="RBI OBSE Industry Data",
    )


def calculate_gstr_mismatch(
    gstr_3b_turnover: float,
    gstr_2a_turnover: float,
    data_source: str = "GST Returns"
) -> RatioScore:
    """
    Calculate GSTR-3B vs GSTR-2A mismatch percentage.
    
    Source: CBIC Instruction F.No.20/16/04/2018-GST
    
    Above 20% = RED (Revenue inflation risk)
    10 to 20% = AMBER (Reconciliation issues)
    Below 5% = GREEN (Normal variance)
    """
    if gstr_3b_turnover == 0:
        mismatch_pct = 0.0
    else:
        mismatch_pct = abs(gstr_3b_turnover - gstr_2a_turnover) / gstr_3b_turnover * 100
    
    # Determine flag
    if mismatch_pct > 20:
        flag = RatioFlag.RED
        reason = f"GSTR-3B/2A mismatch {mismatch_pct:.1f}% exceeds 20%. High risk of revenue inflation or circular trading."
        score = 20.0
    elif mismatch_pct > 10:
        flag = RatioFlag.AMBER
        reason = f"GSTR-3B/2A mismatch {mismatch_pct:.1f}% is moderate (10-20%). Reconciliation issues detected."
        score = 60.0
    elif mismatch_pct > 5:
        flag = RatioFlag.GREEN
        reason = f"GSTR-3B/2A mismatch {mismatch_pct:.1f}% is acceptable (5-10%). Minor timing differences."
        score = 85.0
    else:
        flag = RatioFlag. GREEN
        reason = f"GSTR-3B/2A mismatch {mismatch_pct:.1f}% is minimal (<5%). Excellent GST compliance and reconciliation."
        score = 100.0
    
    return RatioScore(
        parameter_name="GSTR-3B vs 2A Mismatch",
        category="Banking Behavior",
        formula="|GSTR-3B Turnover - GSTR-2A Turnover| / GSTR-3B Turnover × 100",
        company_value=round(mismatch_pct, 1),
        company_value_display=_format_ratio(mismatch_pct, "percentage"),
        rbi_floor=None,
        rbi_source="CBIC Instruction F.No.20/16/04/2018-GST",
        rbi_mandated=False,
        score=score,
        flag=flag,
        reason=reason,
        data_source=data_source,
        benchmark_source="CBIC Guidelines",
    )


def calculate_cash_deposit_ratio(
    cash_deposits: float,
    total_credits: float,
    data_source: str = "Bank Statements"
) -> RatioScore:
    """
    Calculate Cash Deposit Ratio for AML assessment.
    
    Source: PMLA Act 2002 and RBI KYC Master Direction 2016
    
    Above 40% = RED (Money laundering risk)
    20 to 40% = AMBER (Enhanced monitoring)
    Below 20% = GREEN (Normal cash usage)
    """
    cash_ratio_pct = (cash_deposits / total_credits * 100) if total_credits > 0 else 0.0
    
    # Determine flag
    if cash_ratio_pct > 40:
        flag = RatioFlag.RED
        reason = f"Cash Deposit Ratio {cash_ratio_pct:.1f}% exceeds 40%. High money laundering risk - requires EDD."
        score = 20.0
    elif cash_ratio_pct > 20:
        flag = RatioFlag.AMBER
        reason = f"Cash Deposit Ratio {cash_ratio_pct:.1f}% is elevated (20-40%). Enhanced monitoring required per AML norms."
        score = 60.0
    else:
        flag = RatioFlag.GREEN
        reason = f"Cash Deposit Ratio {cash_ratio_pct:.1f}% is within normal limits (<20%). No AML concerns."
        score = 100.0
    
    return RatioScore(
        parameter_name="Cash Deposit Ratio",
        category="Banking Behavior",
        formula="(Cash Deposits / Total Credits) × 100",
        company_value=round(cash_ratio_pct, 1),
        company_value_display=_format_ratio(cash_ratio_pct, "percentage"),
        rbi_floor=None,
        rbi_source="PMLA Act 2002 & RBI KYC Master Direction 2016",
        rbi_mandated=False,
        score=score,
        flag=flag,
        reason=reason,
        data_source=data_source,
        benchmark_source="RBI AML/KYC Guidelines",
    )


def calculate_ebitda_margin(
    ebitda: float,
    revenue: float,
    sector: str,
    data_source: str = "Financial Statements"
) -> RatioScore:
    """
    Calculate EBITDA Margin with industry benchmarking.
    
    Source: RBI OBSE Industry Data FY2024
    
    Above P75 = 100 score
    Median to P75 = 75 score
    P25 to Median = 50 score
    Below P25 = 20 score
    """
    ebitda_margin_pct = (ebitda / revenue * 100) if revenue > 0 else 0.0
    
    # Get industry benchmark
    industry_bench = get_industry_benchmark(sector, "ebitda_margin_pct")
    
    # Score relative to industry percentile
    if ebitda_margin_pct >= industry_bench["p75"]:
        score = 100.0
        flag = RatioFlag.GREEN
        reason = f"EBITDA Margin {ebitda_margin_pct:.1f}% is above industry 75th percentile ({industry_bench['p75']:.1f}%). Excellent profitability."
    elif ebitda_margin_pct >= industry_bench["median"]:
        score = 75.0
        flag = RatioFlag.GREEN
        reason = f"EBITDA Margin {ebitda_margin_pct:.1f}% is between industry median ({industry_bench['median']:.1f}%) and P75. Above-average profitability."
    elif ebitda_margin_pct >= industry_bench["p25"]:
        score = 50.0
        flag = RatioFlag.AMBER
        reason = f"EBITDA Margin {ebitda_margin_pct:.1f}% is between industry P25 ({industry_bench['p25']:.1f}%) and median. Below-average profitability."
    else:
        score = 20.0
        flag = RatioFlag.RED
        reason = f"EBITDA Margin {ebitda_margin_pct:.1f}% is below industry 25th percentile ({industry_bench['p25']:.1f}%). Weak profitability."
    
    return RatioScore(
        parameter_name="EBITDA Margin",
        category="Profitability",
        formula="(EBITDA / Revenue) × 100",
        company_value=round(ebitda_margin_pct, 1),
        company_value_display=_format_ratio(ebitda_margin_pct, "percentage"),
        rbi_floor=None,
        rbi_mandated=False,
        industry_median=industry_bench["median"],
        industry_p25=industry_bench["p25"],
        industry_p75=industry_bench["p75"],
        industry_source=f"RBI OBSE FY2024 - {sector}",
        score=score,
        flag=flag,
        reason=reason,
        data_source=data_source,
        benchmark_source="RBI OBSE Industry Data",
    )


# ─── ExplainableScoringAgent Class ───────────────────────────────────────────

class ExplainableScoringAgent:
    """
    Transparent credit scoring agent with full explainability.
    
    Every score is traceable to:
    - Formula used
    - Company actual value
    - RBI floor (if applicable) with circular reference
    - Industry benchmark from RBI OBSE data
    - Plain English reason
    
    Weight profiles adapt to loan type for appropriate risk assessment.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize explainable scoring agent."""
        self.config = config or {}
        
        # Decision band thresholds (BANK CONFIGURABLE - NOT RBI MANDATED)
        self.decision_bands = self.config.get("decision_bands", {
            "APPROVE": 75.0,
            "REFER_TO_COMMITTEE": 60.0,
            "CONDITIONAL_APPROVE": 45.0,
            "REJECT": 0.0,
        })
    
    async def process(
        self,
        company_data: dict,
        compliance_result: ComplianceResult,
        loan_type: LoanType = LoanType.TERM_LOAN
    ) -> ScorecardResult:
        """
        Score the borrower transparently with full explainability.
        
        Args:
            company_data: All financial and banking data
            compliance_result: Results from compliance agent
            loan_type: Type of loan for weight selection
        
        Returns:
            Complete scorecard with all ratios and decision
        """
        logger.info(f"Starting explainable scoring for {company_data.get('company_name')}")
        
        company_name = company_data.get("company_name", "Unknown")
        sector = company_data.get("sector", "Default")
        loan_amount = company_data.get("loan_amount_requested", 0.0)
        
        # Step 1: Select weight profile based on loan type
        weight_profile = get_weight_profile(loan_type)
        logger.info(f"Weight profile: {loan_type.value} | {weight_profile.rationale}")
        
        # Step 2: Extract financial data
        financials = company_data.get("extracted_financials", {}).get("financials", {})
        bank_analysis = company_data.get("bank_statement_analysis", {})
        gst_analysis = company_data.get("gst_analysis", {})
        
        # Step 3: Calculate all ratios
        ratio_scores: List[RatioScore] = []
        
        # REPAYMENT CAPACITY ratios
        ebitda = _safe_float(financials.get("ebitda_3yr",[0])[-1]) if financials.get("ebitda_3yr") else 0
        annual_debt_service = _safe_float(company_data.get("annual_debt_service", loan_amount * 0.15))  # Estimate if not provided
        
        dscr_score = calculate_dscr(ebitda, annual_debt_service)
        dscr_score.weight = weight_profile.repayment_capacity * 0.6  # 60% of category weight
        dscr_score.weighted_score = dscr_score.score * dscr_score.weight
        ratio_scores.append(dscr_score)
        
        # Check for HARD REJECT on DSCR
        if dscr_score.flag == RatioFlag.HARD_REJECT:
            logger.error(f"HARD REJECT: DSCR {dscr_score.company_value} below RBI floor 1.2x")
            return self._create_hard_reject_scorecard(
                company_name, loan_type, loan_amount, weight_profile,
                f"DSCR {dscr_score.company_value}x below RBI mandatory floor 1.2x"
            )
        
        monthly_income = _safe_float(bank_analysis.get("average_monthly_credits", 0))
        existing_emis = _safe_float(bank_analysis.get("existing_emi_total", 0))
        proposed_emi = annual_debt_service / 12 if annual_debt_service > 0 else loan_amount * 0.015
        
        for_score = calculate_for_ratio(existing_emis + proposed_emi, monthly_income)
        for_score.weight = weight_profile.repayment_capacity * 0.4  # 40% of category weight
        for_score.weighted_score = for_score.score * for_score.weight
        ratio_scores.append(for_score)
        
        # LIQUIDITY ratios
        current_assets = _safe_float(financials.get("current_assets", 0))
        current_liabilities = _safe_float(financials.get("current_liabilities", 0))
        
        current_ratio_score = calculate_current_ratio(current_assets, current_liabilities)
        current_ratio_score.weight = weight_profile.liquidity
        current_ratio_score.weighted_score = current_ratio_score.score * current_ratio_score.weight
        ratio_scores.append(current_ratio_score)
        
        # LEVERAGE ratios
        total_debt = _safe_float(financials.get("total_debt", 0))
        net_worth = _safe_float(financials.get("net_worth", 1))
        
        de_score = calculate_debt_to_equity(total_debt, net_worth, sector)
        de_score.weight = weight_profile.leverage
        de_score.weighted_score = de_score.score * de_score.weight
        ratio_scores.append(de_score)
        
        # PROFITABILITY ratios
        revenue = _safe_float(financials.get("revenue_3yr", [0])[-1]) if financials.get("revenue_3yr") else 0
        
        ebitda_margin_score = calculate_ebitda_margin(ebitda, revenue, sector)
        ebitda_margin_score.weight = weight_profile.profitability
        ebitda_margin_score.weighted_score = ebitda_margin_score.score * ebitda_margin_score.weight
        ratio_scores.append(ebitda_margin_score)
        
        # BANKING BEHAVIOR ratios
        gstr_3b_turnover = _safe_float(gst_analysis.get("gstr3b_cumulative_revenue", 0))
        gstr_2a_turnover = _safe_float(gst_analysis.get("gstr2a_cumulative_revenue", 0))
        
        gstr_mismatch_score = calculate_gstr_mismatch(gstr_3b_turnover, gstr_2a_turnover)
        gstr_mismatch_score.weight = weight_profile.banking_behavior * 0.5
        gstr_mismatch_score.weighted_score = gstr_mismatch_score.score * gstr_mismatch_score.weight
        ratio_scores.append(gstr_mismatch_score)
        
        cash_deposits = _safe_float(bank_analysis.get("cash_deposits", 0))
        total_credits = _safe_float(bank_analysis.get("total_credits", 1))
        
        cash_ratio_score = calculate_cash_deposit_ratio(cash_deposits, total_credits)
        cash_ratio_score.weight = weight_profile.banking_behavior * 0.5
        cash_ratio_score.weighted_score = cash_ratio_score.score * cash_ratio_score.weight
        ratio_scores.append(cash_ratio_score)
        
        # Step 4: Calculate category subtotals
        categories = {}
        for ratio in ratio_scores:
            if ratio.category not in categories:
                categories[ratio.category] = {
                    "weighted_score": 0.0,
                    "total_weight": 0.0,
                    "count": 0
                }
            categories[ratio.category]["weighted_score"] += ratio.weighted_score
            categories[ratio.category]["total_weight"] += ratio.weight
            categories[ratio.category]["count"] += 1
        
        category_subtotals = [
            CategorySubtotal(
                category_name=cat,
                total_weight=data["total_weight"],
                weighted_score=data["weighted_score"],
                ratio_count=data["count"]
            )
            for cat, data in categories.items()
        ]
        
        # Step 5: Calculate base financial score
        base_financial_score = sum(r.weighted_score for r in ratio_scores)
        
        # Step 6: Apply compliance deductions
        compliance_red = compliance_result.total_red_flags
        compliance_amber = compliance_result.total_amber_flags
        compliance_deduction = (compliance_red * 5.0) + (compliance_amber * 2.0)
        
        final_score = max(0.0, base_financial_score - compliance_deduction)
        
        logger.info(f"Base score: {base_financial_score:.1f}, Compliance deduction: {compliance_deduction:.1f}, Final: {final_score:.1f}")
        
        # Step 7: Determine decision band
        decision_band = self._determine_decision_band(final_score)
        
        # Step 8: Create scorecard result
        scorecard = ScorecardResult(
            company_name=company_name,
            loan_type=loan_type,
            loan_amount_requested=loan_amount,
            weight_profile=weight_profile,
            weight_rationale=weight_profile.rationale,
            ratio_scores=ratio_scores,
            category_subtotals=category_subtotals,
            base_financial_score=round(base_financial_score, 2),
            compliance_red_flags=compliance_red,
            compliance_amber_flags=compliance_amber,
            compliance_deduction=round(compliance_deduction, 2),
            final_score=round(final_score, 2),
            decision_band=decision_band,
            band_thresholds=self.decision_bands,
            band_rationale="Decision bands are bank-configurable internal thresholds. NOT RBI mandated."
        )
        
        return scorecard
    
    def _determine_decision_band(self, final_score: float) -> str:
        """Determine decision band from final score."""
        if final_score >= self.decision_bands["APPROVE"]:
            return "APPROVE"
        elif final_score >= self.decision_bands["REFER_TO_COMMITTEE"]:
            return "REFER_TO_COMMITTEE"
        elif final_score >= self.decision_bands["CONDITIONAL_APPROVE"]:
            return "CONDITIONAL_APPROVE"
        else:
            return "REJECT"
    
    def _create_hard_reject_scorecard(
        self,
        company_name: str,
        loan_type: LoanType,
        loan_amount: float,
        weight_profile: WeightProfile,
        reason: str
    ) -> ScorecardResult:
        """Create scorecard for hard reject case."""
        return ScorecardResult(
            company_name=company_name,
            loan_type=loan_type,
            loan_amount_requested=loan_amount,
            weight_profile=weight_profile,
            weight_rationale=weight_profile.rationale,
            ratio_scores=[],
            category_subtotals=[],
            base_financial_score=0.0,
            final_score=0.0,
            decision_band="HARD_REJECT",
            band_rationale=reason
        )


# ─── Main Processing Function ────────────────────────────────────────────────

async def run_explainable_scoring_agent(
    state: Dict[str, Any],
    log_callback: Optional[Callable] = None
) -> Dict[str, Any]:
    """
    Run explainable scoring agent as part of pipeline.
    
    Args:
        state: Current pipeline state
        log_callback: Optional callback for streaming logs
    
    Returns:
        Updated state with scorecard_result
    """
    logs = []
    
    def log(message: str, level: str = "INFO"):
        entry = _log("EXPLAINABLE_SCORER", message, level)
        logs.append(entry)
        if log_callback:
            asyncio.create_task(log_callback(entry))
    
    log("Starting explainable transparent scoring...")
    
    try:
        # Determine loan type from state
        loan_type_str = state.get("loan_type", "TERM_LOAN")
        try:
            loan_type = LoanType[loan_type_str]
        except KeyError:
            loan_type = LoanType.TERM_LOAN
            log(f"Unknown loan type '{loan_type_str}', defaulting to TERM_LOAN", "WARN")
        
        log(f"Loan type: {loan_type.value}")
        
        # Consolidate company data
        company_data = {
            "company_name": state.get("company_name", ""),
            "sector": state.get("sector", "Default"),
            "loan_amount_requested": state.get("loan_amount_requested", 0),
            "extracted_financials": state.get("extracted_financials", {}),
            "bank_statement_analysis": state.get("extracted_financials", {}).get("bank_analysis", {}),
            "gst_analysis": state.get("extracted_financials", {}).get("gst_analysis", {}),
            "annual_debt_service": state.get("annual_debt_service"),
        }
        
        # Get compliance result
        from models.schemas import ComplianceResult
        compliance_dict = state.get("compliance_result", {})
        compliance_result = ComplianceResult(**compliance_dict) if compliance_dict else ComplianceResult()
        
        # Create and run agent
        agent = ExplainableScoringAgent()
        scorecard_result = await agent.process(company_data, compliance_result, loan_type)
        
        log(f"Scoring complete. Final score: {scorecard_result.final_score:.1f}/100", "SUCCESS")
        log(f"Decision band: {scorecard_result.decision_band}")
        
        # Convert to dict
        scorecard_dict = scorecard_result.model_dump()
        
        return {
            "scorecard_result": scorecard_dict,
            "logs": state.get("logs", []) + logs
        }
        
    except Exception as e:
        log(f"Explainable scoring agent error: {str(e)}", "ERROR")
        logger.exception("Explainable scoring agent failed")
        
        return {
            "scorecard_result": {},
            "logs": state.get("logs", []) + logs
        }
