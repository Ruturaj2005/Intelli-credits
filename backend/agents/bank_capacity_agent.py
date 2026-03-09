"""
Bank Capacity Agent — Regulatory Exposure & Lending Capacity Assessment

This agent determines whether the bank CAN lend (independent of credit score):
1. Checks 6 types of exposure limits per RBI regulations
2. Calculates maximum loanable amount considering all constraints
3. Assesses PSL (Priority Sector Lending) opportunity for pricing discount
4. Computes provisioning costs for risk-adjusted pricing
5. Builds transparent interest rate with all components visible

Key Features:
- Single Borrower Exposure (15%/20% of eligible capital)
- Group Exposure (25%/40% of eligible capital)
- Sector Concentration (bank-configurable limits)
- CRAR Impact (must maintain minimum 11.5% post-loan)
- Internal Policy Checks (age, promoter contrib, collateral)
- PCA Status (hard block if bank under PCA)
- PSL Assessment (40% ANBC target → 25-50bps discount)
- Provisioning (Standard: 0.40%, CRE: 1.00%, SME: 0.25%)
- Transparent Pricing (EBLR + Credit Spread + RAROC Charge - PSL Discount)

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
from enum import Enum

from models.schemas import (
    BankConfig,
    ExposureCheck,
    ExposureStatus,
    PSLOpportunity,
    PSLCategory,
    ProvisioningCost,
    InterestRateComponent,
    CapacityResult,
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


# ─── PSL Sector Classification ───────────────────────────────────────────────
# Source: RBI FIDD.CO.Plan.BC.5/04.09.01/2020-21

PSL_SECTOR_MAPPING = {
    "Agriculture": PSLCategory.AGRICULTURE,
    "Farming": PSLCategory.AGRICULTURE,
    "Agro": PSLCategory.AGRICULTURE,
    "MSME": PSLCategory.MSME,
    "Micro": PSLCategory.MSME,
    "Small": PSLCategory.MSME,
    "SME": PSLCategory.MSME,
    "Export": PSLCategory.EXPORT_CREDIT,
    "Housing": PSLCategory.HOUSING,
    "Real Estate": PSLCategory.HOUSING,
    "Education": PSLCategory.EDUCATION,
    "Renewable": PSLCategory.RENEWABLE_ENERGY,
    "Solar": PSLCategory.RENEWABLE_ENERGY,
    "Wind": PSLCategory.RENEWABLE_ENERGY,
}


def classify_psl_sector(sector: str, loan_amount: float, turnover: float) -> Optional[PSLCategory]:
    """
    Classify if loan qualifies for PSL.
    
    RBI PSL Guidelines FY2024:
    - Agriculture: All loans to farmers
    - MSME: Manufacturing ≤ ₹50Cr, Services ≤ ₹25Cr
    - Export Credit: All export-related financing
    - Housing: Home loans ≤ ₹35L in metro, ≤ ₹25L in others
    - Education: All education loans in India
    - Renewable Energy: Solar, wind, biomass projects
    """
    sector_lower = sector.lower()
    
    # Check direct mapping
    for key, category in PSL_SECTOR_MAPPING.items():
        if key.lower() in sector_lower:
            # Additional checks for MSME turnover limits
            if category == PSLCategory.MSME:
                # Manufacturing: ≤ ₹50Cr, Services: ≤ ₹25Cr
                if "manufacturing" in sector_lower and turnover <= 50_00_00_000:
                    return PSLCategory.MSME
                elif "service" in sector_lower and turnover <= 25_00_00_000:
                    return PSLCategory.MSME
                elif turnover <= 25_00_00_000:  # Default to lower limit
                    return PSLCategory.MSME
                else:
                    return None  # Exceeds MSME limits
            
            return category
    
    return None


# ─── BankCapacityAgent Class ──────────────────────────────────────────────────

class BankCapacityAgent:
    """
    Assess bank's regulatory capacity to lend.
    
    This agent answers: "Can we lend?" (regardless of credit score)
    - Checks all RBI exposure limits
    - Enforces internal policy guardrails
    - Calculates maximum lendable amount
    - Provides transparent pricing
    """
    
    def __init__(self, bank_config: BankConfig):
        """Initialize capacity agent with bank configuration."""
        self.bank_config = bank_config
        self.eligible_capital = bank_config.tier1_capital + bank_config.tier2_capital
    
    async def process(
        self,
        company_data: dict,
        loan_amount_requested: float
    ) -> CapacityResult:
        """
        Assess lending capacity for the borrower.
        
        Args:
            company_data: All company/group data
            loan_amount_requested: Amount requested by borrower
        
        Returns:
            Complete capacity assessment with max amount and pricing
        """
        logger.info(f"Assessing bank capacity for {company_data.get('company_name')}")
        
        company_name = company_data.get("company_name", "Unknown")
        group_name = company_data.get("group_name", company_name)
        sector = company_data.get("sector", "Default")
        turnover = _safe_float(company_data.get("turnover", 0))
        existing_exposure = _safe_float(company_data.get("existing_bank_exposure", 0))
        group_exposure = _safe_float(company_data.get("group_total_exposure", 0))
        
        exposure_checks: List[ExposureCheck] = []
        
        # ═══════════════════════════════════════════════════════════════════════
        # GATE 2A: PCA Status Check (HARD BLOCK)
        # ═══════════════════════════════════════════════════════════════════════
        pca_check = self._check_pca_status()
        exposure_checks.append(pca_check)
        
        if pca_check.status == ExposureStatus.HARD_BLOCK:
            logger.error("HARD BLOCK: Bank under PCA - cannot lend")
            return self._create_hard_block_result(
                company_name, loan_amount_requested, exposure_checks,
                "Bank is under RBI Prompt Corrective Action (PCA). Lending prohibited."
            )
        
        # ═══════════════════════════════════════════════════════════════════════
        # GATE 2B: Single Borrower Exposure Limit
        # ═══════════════════════════════════════════════════════════════════════
        single_borrower_check = self._check_single_borrower_exposure(
            existing_exposure, loan_amount_requested
        )
        exposure_checks.append(single_borrower_check)
        
        # ═══════════════════════════════════════════════════════════════════════
        # GATE 2C: Group Exposure Limit
        # ═══════════════════════════════════════════════════════════════════════
        group_check = self._check_group_exposure(
            group_name, group_exposure, loan_amount_requested
        )
        exposure_checks.append(group_check)
        
        # ═══════════════════════════════════════════════════════════════════════
        # GATE 2D: Sector Concentration Limit
        # ═══════════════════════════════════════════════════════════════════════
        sector_check = self._check_sector_concentration(sector, loan_amount_requested)
        exposure_checks.append(sector_check)
        
        # ═══════════════════════════════════════════════════════════════════════
        # GATE 2E: CRAR Impact Check
        # ═══════════════════════════════════════════════════════════════════════
        crar_check = self._check_crar_impact(loan_amount_requested)
        exposure_checks.append(crar_check)
        
        # ═══════════════════════════════════════════════════════════════════════
        # GATE 2F: Internal Policy Checks
        # ═══════════════════════════════════════════════════════════════════════
        policy_check = self._check_internal_policy(company_data, loan_amount_requested)
        exposure_checks.append(policy_check)
        
        # ═══════════════════════════════════════════════════════════════════════
        # Calculate Maximum Lendable Amount
        # ═══════════════════════════════════════════════════════════════════════
        can_lend = all(check.status != ExposureStatus.HARD_BLOCK for check in exposure_checks)
        
        if not can_lend:
            logger.error("HARD BLOCK: One or more exposure checks failed")
            return self._create_hard_block_result(
                company_name, loan_amount_requested, exposure_checks,
                "One or more regulatory exposure limits breached."
            )
        
        # Find minimum max amount across all checks
        max_amounts = [
            check.max_amount_allowed 
            for check in exposure_checks 
            if check.max_amount_allowed is not None
        ]
        
        if max_amounts:
            suggested_max_amount = min(max_amounts)
        else:
            suggested_max_amount = loan_amount_requested
        
        logger.info(f"Max lendable amount: ₹{suggested_max_amount:,.0f}")
        
        # ═══════════════════════════════════════════════════════════════════════
        # PSL Opportunity Assessment
        # ═══════════════════════════════════════════════════════════════════════
        psl_opportunity = self._assess_psl_opportunity(
            sector, loan_amount_requested, turnover
        )
        
        # ═══════════════════════════════════════════════════════════════════════
        # Provisioning Cost Calculation
        # ═══════════════════════════════════════════════════════════════════════
        provisioning = self._calculate_provisioning(sector, suggested_max_amount)
        
        # ═══════════════════════════════════════════════════════════════════════
        # Transparent Interest Rate Build-up
        # ═══════════════════════════════════════════════════════════════════════
        interest_rate_components = self._build_interest_rate(
            company_data, psl_opportunity, provisioning
        )
        
        final_rate = sum(comp.rate_bps for comp in interest_rate_components) / 100.0
        
        # ═══════════════════════════════════════════════════════════════════════
        # Create Final Result
        # ═══════════════════════════════════════════════════════════════════════
        capacity_result = CapacityResult(
            company_name=company_name,
            loan_amount_requested=loan_amount_requested,
            can_lend=can_lend,
            exposure_checks=exposure_checks,
            suggested_max_amount=suggested_max_amount,
            utilization_pct=round((suggested_max_amount / loan_amount_requested * 100), 1) if loan_amount_requested > 0 else 0.0,
            psl_opportunity=psl_opportunity,
            provisioning_cost=provisioning,
            interest_rate_components=interest_rate_components,
            final_interest_rate_pct=round(final_rate, 2),
            capacity_remarks=self._generate_capacity_remarks(exposure_checks, psl_opportunity)
        )
        
        return capacity_result
    
    # ──────────────────────────────────────────────────────────────────────────
    # RBI Exposure Check Methods
    # ──────────────────────────────────────────────────────────────────────────
    
    def _check_pca_status(self) -> ExposureCheck:
        """
        Check if bank is under RBI Prompt Corrective Action (PCA).
        
        Source: RBI Prompt Corrective Action Framework 2017
        If bank under PCA: HARD BLOCK - cannot lend
        """
        if self.bank_config.pca_status:
            return ExposureCheck(
                check_name="PCA Status Check",
                check_type="Regulatory Compliance",
                regulatory_source="RBI Prompt Corrective Action Framework 2017",
                status=ExposureStatus.HARD_BLOCK,
                limit_value=0.0,
                current_utilization=0.0,
                post_loan_utilization=0.0,
                max_amount_allowed=0.0,
                rationale="Bank is under RBI Prompt Corrective Action (PCA). All lending activities are prohibited until PCA restrictions are lifted.",
                breached=True
            )
        else:
            return ExposureCheck(
                check_name="PCA Status Check",
                check_type="Regulatory Compliance",
                regulatory_source="RBI Prompt Corrective Action Framework 2017",
                status=ExposureStatus.GREEN,
                limit_value=1.0,
                current_utilization=0.0,
                post_loan_utilization=0.0,
                rationale="Bank is NOT under PCA. Lending permitted.",
                breached=False
            )
    
    def _check_single_borrower_exposure(
        self,
        existing_exposure: float,
        loan_amount: float
    ) -> ExposureCheck:
        """
        Check Single Borrower Exposure Limit.
        
        Source: RBI DoR.CRE.REC.30/13.03.000/2023-24
        - Standard Limit: 15% of Eligible Capital (Tier 1 + Tier 2)
        - Enhanced Limit: 20% (with Board approval for infrastructure)
        
        Use 15% as conservative limit.
        """
        limit_pct = 15.0
        limit_amount = self.eligible_capital * (limit_pct / 100)
        current_utilization_pct = (existing_exposure / self.eligible_capital) * 100
        post_loan_exposure = existing_exposure + loan_amount
        post_loan_utilization_pct = (post_loan_exposure / self.eligible_capital) * 100
        
        if post_loan_utilization_pct > limit_pct:
            # Calculate max additional amount
            max_additional = limit_amount - existing_exposure
            max_amount_allowed = max(0.0, max_additional)
            
            if max_amount_allowed == 0:
                status = ExposureStatus.HARD_BLOCK
            else:
                status = ExposureStatus.AMBER
            
            return ExposureCheck(
                check_name="Single Borrower Exposure",
                check_type="RBI Regulatory Limit",
                regulatory_source="RBI DoR.CRE.REC.30/13.03.000/2023-24",
                status=status,
                limit_value=limit_pct,
                limit_display=f"{limit_pct}% of Eligible Capital = ₹{limit_amount:,.0f}",
                current_utilization=round(current_utilization_pct, 2),
                post_loan_utilization=round(post_loan_utilization_pct, 2),
                max_amount_allowed=max_amount_allowed,
                rationale=f"Post-loan exposure would be {post_loan_utilization_pct:.1f}%, exceeding {limit_pct}% limit. Max additional lending: ₹{max_amount_allowed:,.0f}",
                breached=True
            )
        else:
            return ExposureCheck(
                check_name="Single Borrower Exposure",
                check_type="RBI Regulatory Limit",
                regulatory_source="RBI DoR.CRE.REC.30/13.03.000/2023-24",
                status=ExposureStatus.GREEN,
                limit_value=limit_pct,
                limit_display=f"{limit_pct}% of Eligible Capital = ₹{limit_amount:,.0f}",
                current_utilization=round(current_utilization_pct, 2),
                post_loan_utilization=round(post_loan_utilization_pct, 2),
                rationale=f"Post-loan exposure {post_loan_utilization_pct:.1f}% is within {limit_pct}% limit. Headroom available.",
                breached=False
            )
    
    def _check_group_exposure(
        self,
        group_name: str,
        group_exposure: float,
        loan_amount: float
    ) -> ExposureCheck:
        """
        Check Group Exposure Limit.
        
        Source: RBI DoR.CRE.REC.30/13.03.000/2023-24
        - Standard Limit: 25% of Eligible Capital
        - Enhanced Limit: 40% (with Board approval for infrastructure)
        
        Use 25% as conservative limit.
        """
        limit_pct = 25.0
        limit_amount = self.eligible_capital * (limit_pct / 100)
        current_utilization_pct = (group_exposure / self.eligible_capital) * 100
        post_loan_exposure = group_exposure + loan_amount
        post_loan_utilization_pct = (post_loan_exposure / self.eligible_capital) * 100
        
        if post_loan_utilization_pct > limit_pct:
            max_additional = limit_amount - group_exposure
            max_amount_allowed = max(0.0, max_additional)
            
            if max_amount_allowed == 0:
                status = ExposureStatus.HARD_BLOCK
            else:
                status = ExposureStatus.AMBER
            
            return ExposureCheck(
                check_name="Group Exposure",
                check_type="RBI Regulatory Limit",
                regulatory_source="RBI DoR.CRE.REC.30/13.03.000/2023-24",
                status=status,
                limit_value=limit_pct,
                limit_display=f"{limit_pct}% of Eligible Capital = ₹{limit_amount:,.0f}",
                current_utilization=round(current_utilization_pct, 2),
                post_loan_utilization=round(post_loan_utilization_pct, 2),
                max_amount_allowed=max_amount_allowed,
                rationale=f"Group '{group_name}' post-loan exposure would be {post_loan_utilization_pct:.1f}%, exceeding {limit_pct}% limit. Max additional: ₹{max_amount_allowed:,.0f}",
                breached=True
            )
        else:
            return ExposureCheck(
                check_name="Group Exposure",
                check_type="RBI Regulatory Limit",
                regulatory_source="RBI DoR.CRE.REC.30/13.03.000/2023-24",
                status=ExposureStatus.GREEN,
                limit_value=limit_pct,
                limit_display=f"{limit_pct}% of Eligible Capital = ₹{limit_amount:,.0f}",
                current_utilization=round(current_utilization_pct, 2),
                post_loan_utilization=round(post_loan_utilization_pct, 2),
                rationale=f"Group exposure {post_loan_utilization_pct:.1f}% is within {limit_pct}% limit.",
                breached=False
            )
    
    def _check_sector_concentration(
        self,
        sector: str,
        loan_amount: float
    ) -> ExposureCheck:
        """
        Check Sector Concentration Limit.
        
        Source: Bank's Internal Risk Policy (NOT RBI mandated)
        Banks set sector exposure limits based on risk appetite.
        """
        # Get current sector exposure
        current_sector_exposure = self.bank_config.sector_exposures.get(sector, 0.0)
        sector_limit_pct = self.bank_config.sector_limits.get(sector, 25.0)  # Default 25%
        
        anbc = self.bank_config.anbc
        sector_limit_amount = anbc * (sector_limit_pct / 100)
        current_utilization_pct = (current_sector_exposure / anbc) * 100
        post_loan_exposure = current_sector_exposure + loan_amount
        post_loan_utilization_pct = (post_loan_exposure / anbc) * 100
        
        if post_loan_utilization_pct > sector_limit_pct:
            max_additional = sector_limit_amount - current_sector_exposure
            max_amount_allowed = max(0.0, max_additional)
            
            status = ExposureStatus.AMBER if max_amount_allowed > 0 else ExposureStatus.RED
            
            return ExposureCheck(
                check_name=f"Sector Concentration ({sector})",
                check_type="Internal Policy Limit",
                regulatory_source="Bank Internal Risk Policy",
                status=status,
                limit_value=sector_limit_pct,
                limit_display=f"{sector_limit_pct}% of ANBC = ₹{sector_limit_amount:,.0f}",
                current_utilization=round(current_utilization_pct, 2),
                post_loan_utilization=round(post_loan_utilization_pct, 2),
                max_amount_allowed=max_amount_allowed,
                rationale=f"Sector '{sector}' post-loan exposure {post_loan_utilization_pct:.1f}% would exceed internal limit of {sector_limit_pct}%. Max additional: ₹{max_amount_allowed:,.0f}",
                breached=True
            )
        else:
            return ExposureCheck(
                check_name=f"Sector Concentration ({sector})",
                check_type="Internal Policy Limit",
                regulatory_source="Bank Internal Risk Policy",
                status=ExposureStatus.GREEN,
                limit_value=sector_limit_pct,
                limit_display=f"{sector_limit_pct}% of ANBC = ₹{sector_limit_amount:,.0f}",
                current_utilization=round(current_utilization_pct, 2),
                post_loan_utilization=round(post_loan_utilization_pct, 2),
                rationale=f"Sector exposure {post_loan_utilization_pct:.1f}% is within internal limit of {sector_limit_pct}%.",
                breached=False
            )
    
    def _check_crar_impact(self, loan_amount: float) -> ExposureCheck:
        """
        Check Capital Adequacy Impact.
        
        Source: RBI Basel III DBOD.No.BP.BC.50/21.06.201/2012-13
        Minimum CRAR: 11.5% (9% + 2.5% buffer for commercial banks)
        
        Post-loan CRAR must remain ≥ 11.5%
        """
        min_crar_pct = 11.5
        
        # Calculate post-loan CRAR
        # New loan adds 100% risk weight (corporate loan)
        additional_rwa = loan_amount * 1.0  # 100% risk weight
        current_rwa = (self.bank_config.tier1_capital + self.bank_config.tier2_capital) / (self.bank_config.current_crar / 100)
        post_loan_rwa = current_rwa + additional_rwa
        post_loan_crar = ((self.bank_config.tier1_capital + self.bank_config.tier2_capital) / post_loan_rwa) * 100
        
        if post_loan_crar < min_crar_pct:
            # Calculate max loan amount that maintains min CRAR
            max_rwa_increase = ((self.bank_config.tier1_capital + self.bank_config.tier2_capital) / (min_crar_pct / 100)) - current_rwa
            max_amount_allowed = max(0.0, max_rwa_increase)
            
            status = ExposureStatus.HARD_BLOCK if max_amount_allowed == 0 else ExposureStatus.RED
            
            return ExposureCheck(
                check_name="Capital Adequacy (CRAR) Impact",
                check_type="RBI Regulatory Limit",
                regulatory_source="RBI Basel III DBOD.No.BP.BC.50/21.06.201/2012-13",
                status=status,
                limit_value=min_crar_pct,
                limit_display=f"Minimum CRAR {min_crar_pct}%",
                current_utilization=round(self.bank_config.current_crar, 2),
                post_loan_utilization=round(post_loan_crar, 2),
                max_amount_allowed=max_amount_allowed,
                rationale=f"Post-loan CRAR would drop to {post_loan_crar:.2f}%, below minimum {min_crar_pct}%. Max lendable: ₹{max_amount_allowed:,.0f}",
                breached=True
            )
        else:
            return ExposureCheck(
                check_name="Capital Adequacy (CRAR) Impact",
                check_type="RBI Regulatory Limit",
                regulatory_source="RBI Basel III DBOD.No.BP.BC.50/21.06.201/2012-13",
                status=ExposureStatus.GREEN,
                limit_value=min_crar_pct,
                limit_display=f"Minimum CRAR {min_crar_pct}%",
                current_utilization=round(self.bank_config.current_crar, 2),
                post_loan_utilization=round(post_loan_crar, 2),
                rationale=f"Post-loan CRAR {post_loan_crar:.2f}% remains above minimum {min_crar_pct}%. Adequate capital.",
                breached=False
            )
    
    def _check_internal_policy(
        self,
        company_data: dict,
        loan_amount: float
    ) -> ExposureCheck:
        """
        Check internal policy guardrails (NOT RBI mandated).
        
        Bank-specific policies like:
        - Minimum business vintage
        - Minimum promoter contribution
        - Collateral coverage ratio
        """
        policy_thresholds = self.bank_config.internal_policy_thresholds
        
        # Business vintage check
        company_age_years = _safe_float(company_data.get("company_age_years", 0))
        min_age = policy_thresholds.get("min_business_vintage_years", 3)
        
        # Promoter contribution check
        promoter_contribution_pct = _safe_float(company_data.get("promoter_contribution_pct", 0))
        min_promoter_contrib = policy_thresholds.get("min_promoter_contribution_pct", 25.0)
        
        # Collateral coverage
        collateral_value = _safe_float(company_data.get("collateral_value", 0))
        collateral_coverage = (collateral_value / loan_amount) if loan_amount > 0 else 0.0
        min_collateral_coverage = policy_thresholds.get("min_collateral_coverage", 1.25)
        
        # Check all policies
        policy_violations = []
        
        if company_age_years < min_age:
            policy_violations.append(f"Business vintage {company_age_years:.1f} years < minimum {min_age} years")
        
        if promoter_contribution_pct < min_promoter_contrib:
            policy_violations.append(f"Promoter contribution {promoter_contribution_pct:.1f}% < minimum {min_promoter_contrib}%")
        
        if collateral_coverage < min_collateral_coverage:
            policy_violations.append(f"Collateral coverage {collateral_coverage:.2f}x < minimum {min_collateral_coverage}x")
        
        if policy_violations:
            return ExposureCheck(
                check_name="Internal Policy Guardrails",
                check_type="Internal Policy",
                regulatory_source="Bank Credit Policy Manual",
                status=ExposureStatus.RED,
                limit_value=0.0,
                rationale=f"Policy violations: {'; '.join(policy_violations)}. Requires committee approval.",
                breached=True
            )
        else:
            return ExposureCheck(
                check_name="Internal Policy Guardrails",
                check_type="Internal Policy",
                regulatory_source="Bank Credit Policy Manual",
                status=ExposureStatus.GREEN,
                limit_value=1.0,
                rationale="All internal policy guardrails met: vintage, promoter contribution, collateral coverage.",
                breached=False
            )
    
    # ──────────────────────────────────────────────────────────────────────────
    # PSL & Pricing Methods
    # ──────────────────────────────────────────────────────────────────────────
    
    def _assess_psl_opportunity(
        self,
        sector: str,
        loan_amount: float,
        turnover: float
    ) -> PSLOpportunity:
        """
        Assess Priority Sector Lending opportunity.
        
        Source: RBI FIDD.CO.Plan.BC.5/04.09.01/2020-21
        Target: 40% of ANBC for domestic banks
        
        PSL loans get 25-50bps pricing discount.
        """
        psl_category = classify_psl_sector(sector, loan_amount, turnover)
        
        if psl_category:
            qualifies = True
            current_psl_achievement = self.bank_config.psl_achieved_pct
            target_psl = 40.0
            shortfall_pct = max(0.0, target_psl - current_psl_achievement)
            
            # Discount based on shortfall urgency
            if shortfall_pct > 5.0:
                discount_bps = 50.0  # Aggressive discount if far from target
                urgency = "High Priority - Bank significantly short of PSL target"
            elif shortfall_pct > 2.0:
                discount_bps = 35.0
                urgency = "Medium Priority - Bank moderately short of PSL target"
            else:
                discount_bps = 25.0
                urgency = "Low Priority - Bank near PSL target"
            
            return PSLOpportunity(
                qualifies_for_psl=True,
                psl_category=psl_category,
                psl_category_display=psl_category.value,
                regulatory_source="RBI FIDD.CO.Plan.BC.5/04.09.01/2020-21",
                current_psl_achievement_pct=round(current_psl_achievement, 2),
                psl_target_pct=target_psl,
                shortfall_pct=round(shortfall_pct, 2),
                discount_bps=discount_bps,
                discount_rationale=f"{urgency}. PSL discount: {discount_bps}bps applied."
            )
        else:
            return PSLOpportunity(
                qualifies_for_psl=False,
                psl_category=None,
                psl_category_display="Not Eligible",
                regulatory_source="RBI FIDD.CO.Plan.BC.5/04.09.01/2020-21",
                current_psl_achievement_pct=round(self.bank_config.psl_achieved_pct, 2),
                psl_target_pct=40.0,
                discount_bps=0.0,
                discount_rationale="Loan does not qualify for PSL. No pricing discount."
            )
    
    def _calculate_provisioning(
        self,
        sector: str,
        loan_amount: float
    ) -> ProvisioningCost:
        """
        Calculate provisioning requirement.
        
        Source: RBI Asset Classification Norms
        - Standard Corporate: 0.40%
        - CRE (Commercial Real Estate): 1.00%
        - SME (Secured): 0.25%
        """
        sector_lower = sector.lower()
        
        if "real estate" in sector_lower or "construction" in sector_lower:
            provision_pct = 1.00
            category = "Commercial Real Estate (CRE)"
            source = "RBI Prudential Norms on CRE"
        elif "sme" in sector_lower or "msme" in sector_lower or "small" in sector_lower:
            provision_pct = 0.25
            category = "SME (Secured)"
            source = "RBI SME Asset Classification"
        else:
            provision_pct = 0.40
            category = "Standard Corporate"
            source = "RBI Asset Classification & Provisioning"
        
        provision_amount = loan_amount * (provision_pct / 100)
        
        return ProvisioningCost(
            provision_pct=provision_pct,
            provision_amount=round(provision_amount, 2),
            asset_category=category,
            regulatory_source=source,
            rationale=f"{category} assets require {provision_pct}% standard provisioning. Amount: ₹{provision_amount:,.2f}"
        )
    
    def _build_interest_rate(
        self,
        company_data: dict,
        psl_opportunity: PSLOpportunity,
        provisioning: ProvisioningCost
    ) -> List[InterestRateComponent]:
        """
        Build transparent interest rate with all components.
        
        Components:
        1. EBLR (External Benchmark Lending Rate) - base rate
        2. Credit Spread - based on credit score
        3. RAROC Charge - risk-adjusted return target
        4. PSL Discount - if applicable
        5. Tenure Premium - for longer tenures
        """
        components = []
        
        # 1. EBLR Base Rate
        eblr_rate = 8.50  # Current EBLR (example)
        components.append(InterestRateComponent(
            component_name="EBLR Base Rate",
            rate_bps=850,
            rate_display="8.50%",
            rationale="External Benchmark Lending Rate (EBLR) as per RBI guidelines. Linked to RBI Policy Repo Rate."
        ))
        
        # 2. Credit Spread (based on credit score - will be passed from scorer)
        credit_score = _safe_float(company_data.get("credit_score", 70))
        
        if credit_score >= 80:
            credit_spread_bps = 200  # 2.00%
        elif credit_score >= 70:
            credit_spread_bps = 275  # 2.75%
        elif credit_score >= 60:
            credit_spread_bps = 350  # 3.50%
        else:
            credit_spread_bps = 450  # 4.50%
        
        components.append(InterestRateComponent(
            component_name="Credit Risk Spread",
            rate_bps=credit_spread_bps,
            rate_display=f"{credit_spread_bps/100:.2f}%",
            rationale=f"Credit score {credit_score}/100. Lower score = higher risk premium."
        ))
        
        # 3. RAROC Charge (Risk-Adjusted Return on Capital)
        raroc_target_roe = 18.0  # Bank's target ROE
        provisioning_cost_bps = int(provisioning.provision_pct * 100)
        
        components.append(InterestRateComponent(
            component_name="RAROC Charge",
            rate_bps=provisioning_cost_bps,
            rate_display=f"{provisioning_cost_bps/100:.2f}%",
            rationale=f"Risk-adjusted return to achieve target ROE of {raroc_target_roe}%. Includes {provisioning.provision_pct}% provisioning cost."
        ))
        
        # 4. PSL Discount (if applicable)
        if psl_opportunity.qualifies_for_psl:
            components.append(InterestRateComponent(
                component_name="PSL Discount",
                rate_bps=-int(psl_opportunity.discount_bps),
                rate_display=f"-{psl_opportunity.discount_bps/100:.2f}%",
                rationale=psl_opportunity.discount_rationale
            ))
        
        # 5. Tenure Premium (if long tenure)
        loan_tenure_months = _safe_float(company_data.get("loan_tenure_months", 60))
        if loan_tenure_months > 84:  # > 7 years
            tenure_premium_bps = 50
            components.append(InterestRateComponent(
                component_name="Tenure Premium",
                rate_bps=tenure_premium_bps,
                rate_display=f"{tenure_premium_bps/100:.2f}%",
                rationale=f"Long tenure ({loan_tenure_months} months) adds interest rate risk premium."
            ))
        
        return components
    
    # ──────────────────────────────────────────────────────────────────────────
    # Utilities
    # ──────────────────────────────────────────────────────────────────────────
    
    def _create_hard_block_result(
        self,
        company_name: str,
        loan_amount: float,
        exposure_checks: List[ExposureCheck],
        reason: str
    ) -> CapacityResult:
        """Create result for hard block case."""
        return CapacityResult(
            company_name=company_name,
            loan_amount_requested=loan_amount,
            can_lend=False,
            exposure_checks=exposure_checks,
            suggested_max_amount=0.0,
            utilization_pct=0.0,
            capacity_remarks=f"HARD BLOCK: {reason}"
        )
    
    def _generate_capacity_remarks(
        self,
        exposure_checks: List[ExposureCheck],
        psl_opportunity: PSLOpportunity
    ) -> str:
        """Generate summary remarks."""
        red_count = sum(1 for check in exposure_checks if check.status == ExposureStatus.RED)
        amber_count = sum(1 for check in exposure_checks if check.status == ExposureStatus.AMBER)
        
        if red_count > 0:
            remarks = f"{red_count} RED exposure flag(s). Requires committee/Board approval."
        elif amber_count > 0:
            remarks = f"{amber_count} AMBER exposure flag(s). Monitor closely."
        else:
            remarks = "All exposure checks GREEN. Within all regulatory and internal limits."
        
        if psl_opportunity.qualifies_for_psl:
            remarks += f" PSL-eligible ({psl_opportunity.psl_category_display}): {psl_opportunity.discount_bps}bps discount applied."
        
        return remarks


# ─── Main Processing Function ────────────────────────────────────────────────

async def run_bank_capacity_agent(
    state: Dict[str, Any],
    bank_config: BankConfig,
    log_callback: Optional[Callable] = None
) -> Dict[str, Any]:
    """
    Run bank capacity agent as part of pipeline.
    
    Args:
        state: Current pipeline state
        bank_config: Bank's capital and policy configuration
        log_callback: Optional callback for streaming logs
    
    Returns:
        Updated state with capacity_result
    """
    logs = []
    
    def log(message: str, level: str = "INFO"):
        entry = _log("BANK_CAPACITY", message, level)
        logs.append(entry)
        if log_callback:
            asyncio.create_task(log_callback(entry))
    
    log("Starting bank capacity assessment...")
    
    try:
        # Consolidate company data
        company_data = {
            "company_name": state.get("company_name", ""),
            "group_name": state.get("group_name"),
            "sector": state.get("sector", "Default"),
            "turnover": state.get("turnover"),
            "existing_bank_exposure": state.get("existing_bank_exposure", 0),
            "group_total_exposure": state.get("group_total_exposure", 0),
            "company_age_years": state.get("company_age_years"),
            "promoter_contribution_pct": state.get("promoter_contribution_pct"),
            "collateral_value": state.get("collateral_value"),
            "credit_score": state.get("scorecard_result", {}).get("final_score", 70),
            "loan_tenure_months": state.get("loan_tenure_months", 60),
        }
        
        loan_amount_requested = state.get("loan_amount_requested", 0)
        
        # Create and run agent
        agent = BankCapacityAgent(bank_config)
        capacity_result = await agent.process(company_data, loan_amount_requested)
        
        if capacity_result.can_lend:
            log(f"Bank CAN lend. Max amount: ₹{capacity_result.suggested_max_amount:,.0f}", "SUCCESS")
            log(f"Final interest rate: {capacity_result.final_interest_rate_pct:.2f}%")
        else:
            log(f"Bank CANNOT lend. {capacity_result.capacity_remarks}", "ERROR")
        
        # Convert to dict
        capacity_dict = capacity_result.model_dump()
        
        return {
            "capacity_result": capacity_dict,
            "logs": state.get("logs", []) + logs
        }
        
    except Exception as e:
        log(f"Bank capacity agent error: {str(e)}", "ERROR")
        logger.exception("Bank capacity agent failed")
        
        return {
            "capacity_result": {},
            "logs": state.get("logs", []) + logs
        }
