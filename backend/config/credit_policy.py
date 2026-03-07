"""
Credit Policy Configuration File

This file contains all configurable thresholds, weights, and parameters
used throughout the Intelli-Credits system. Credit managers can adjust
these values to align with their institution's lending policies.

All thresholds are based on industry best practices and RBI guidelines
but can be customized as per organizational risk appetite.
"""

from typing import Dict, List, Any
from dataclasses import dataclass, field


# ═══════════════════════════════════════════════════════════════════════════
# 1. FINANCIAL RATIOS & THRESHOLDS
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class FinancialThresholds:
    """Financial ratio thresholds for credit assessment"""

    # Debt Service Coverage Ratio (DSCR)
    dscr_minimum: float = 1.25  # Below this → reject
    dscr_comfortable: float = 1.5  # Above this → good
    dscr_excellent: float = 2.0  # Above this → excellent

    # Debt-to-Equity Ratio
    debt_to_equity_maximum: float = 3.0  # Above this → red flag
    debt_to_equity_comfortable: float = 2.0  # Below this → comfortable
    debt_to_equity_conservative: float = 1.5  # Below this → conservative

    # Current Ratio (Liquidity)
    current_ratio_minimum: float = 1.0  # Below this → liquidity concern
    current_ratio_comfortable: float = 1.5  # Above this → comfortable
    current_ratio_excellent: float = 2.0  # Above this → excellent

    # Quick Ratio (Acid Test)
    quick_ratio_minimum: float = 0.5  # Below this → critical
    quick_ratio_comfortable: float = 1.0  # Above this → comfortable
    quick_ratio_excellent: float = 1.5  # Above this → excellent

    # Interest Coverage Ratio
    interest_coverage_minimum: float = 2.0  # Below this → concern
    interest_coverage_comfortable: float = 3.0  # Above this → comfortable

    # Net Worth Requirement (as % of loan amount)
    min_net_worth_to_loan_ratio: float = 0.25  # Net worth should be ≥ 25% of loan

    # Return on Assets (ROA)
    roa_minimum: float = 2.0  # Below this → poor profitability
    roa_comfortable: float = 5.0  # Above this → good profitability


@dataclass
class WorkingCapitalThresholds:
    """Working capital specific thresholds"""

    # Working Capital to Revenue Ratio
    wc_to_revenue_surplus: float = 0.25  # WC ≥ 25% of revenue → surplus
    wc_to_revenue_adequate: float = 0.15  # WC ≥ 15% of revenue → adequate
    wc_to_revenue_tight: float = 0.08  # WC ≥ 8% of revenue → tight

    # Operating Cycle Days
    debtor_days_maximum: float = 90  # Above this → collection concern
    inventory_days_maximum: float = 120  # Above this → slow moving inventory
    creditor_days_minimum: float = 30  # Below this → poor negotiation with suppliers

    # Cash Conversion Cycle
    cash_conversion_cycle_excellent: float = 30  # Below 30 days → excellent
    cash_conversion_cycle_good: float = 60  # Below 60 days → good
    cash_conversion_cycle_acceptable: float = 90  # Below 90 days → acceptable
    cash_conversion_cycle_poor: float = 120  # Above 120 days → poor


@dataclass
class FORThresholds:
    """Fixed Obligation Ratio thresholds"""

    for_healthy: float = 40.0  # FOR < 40% → healthy
    for_strained: float = 50.0  # FOR 40-50% → strained
    for_over_leveraged: float = 60.0  # FOR 50-60% → over-leveraged
    # FOR > 60% → critical (auto-reject)


# ═══════════════════════════════════════════════════════════════════════════
# 2. CIBIL & CREDIT BUREAU THRESHOLDS
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class CibilThresholds:
    """CIBIL score thresholds"""

    # Company CIBIL
    company_score_minimum: int = 500  # Below this → reject
    company_score_acceptable: int = 600  # Above this → acceptable
    company_score_good: int = 700  # Above this → good
    company_score_excellent: int = 750  # Above this → excellent

    # Director/Promoter CIBIL
    director_score_minimum: int = 650  # Below this → concern
    director_score_good: int = 700  # Above this → good
    director_score_excellent: int = 750  # Above this → excellent

    # Any director below this → red flag
    director_score_critical: int = 600

    # Days Past Due (DPD) thresholds
    max_dpd_30_allowed: int = 2  # Max 2 instances of 30 DPD in last 12 months
    max_dpd_60_allowed: int = 1  # Max 1 instance of 60 DPD in last 12 months
    max_dpd_90_allowed: int = 0  # No 90+ DPD allowed

    # Wilful defaulter
    wilful_defaulter_auto_reject: bool = True


# ═══════════════════════════════════════════════════════════════════════════
# 3. COMPANY AGE & VINTAGE THRESHOLDS
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class CompanyAgeThresholds:
    """Company age and operating history thresholds"""

    minimum_age_years: float = 2.0  # Below this → high risk
    comfortable_age_years: float = 5.0  # Above this → comfortable
    mature_company_years: float = 10.0  # Above this → mature

    # Young company (<2 years) additional requirements
    young_company_max_loan_cr: float = 2.0  # Max loan: Rs. 2 Cr for <2yr companies
    young_company_min_promoter_equity: float = 0.50  # Min 50% promoter contribution


# ═══════════════════════════════════════════════════════════════════════════
# 4. LOAN AMOUNT & EXPOSURE LIMITS
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class LoanAmountThresholds:
    """Loan amount thresholds and limits"""

    # Small/Medium/Large classification
    small_loan_threshold_cr: float = 1.0  # <= 1 Cr → small
    medium_loan_threshold_cr: float = 10.0  # 1-10 Cr → medium
    # > 10 Cr → large

    # Loan to Annual Revenue Ratio
    max_loan_to_revenue_ratio: float = 0.75  # Loan should not exceed 75% of annual revenue

    # Loan to Net Worth Ratio
    max_loan_to_networth_ratio: float = 4.0  # Loan should not exceed 4x net worth

    # Collateral Coverage Ratio (LTV - Loan to Value)
    default_ltv_ratio: float = 0.75  # Max 75% LTV
    real_estate_ltv: float = 0.70  # Max 70% for real estate
    machinery_ltv: float = 0.75  # Max 75% for machinery
    inventory_ltv: float = 0.50  # Max 50% for inventory
    receivables_ltv: float = 0.60  # Max 60% for receivables


# ═══════════════════════════════════════════════════════════════════════════
# 5. SECTOR-SPECIFIC PARAMETERS
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class SectorThresholds:
    """Sector classification and exposure limits"""

    # Sector NPA thresholds
    sector_npa_low: float = 3.0  # NPA < 3% → low risk sector
    sector_npa_medium: float = 5.0  # NPA 3-5% → medium risk
    sector_npa_high: float = 10.0  # NPA 5-10% → high risk
    sector_npa_very_high: float = 15.0  # NPA > 15% → very high risk (sensitive)

    # Sector exposure limits (as % of total portfolio)
    max_exposure_positive_sector: float = 25.0  # Max 25% in positive sectors
    max_exposure_stable_sector: float = 20.0  # Max 20% in stable sectors
    max_exposure_watch_sector: float = 15.0  # Max 15% in watch sectors
    max_exposure_sensitive_sector: float = 10.0  # Max 10% in sensitive sectors
    max_exposure_negative_sector: float = 5.0  # Max 5% in negative sectors

    # Risk premium (basis points) by sector status
    risk_premium_positive: int = 0  # No premium for positive sectors
    risk_premium_stable: int = 25  # +25 bps for stable
    risk_premium_watch: int = 75  # +75 bps for watch
    risk_premium_sensitive: int = 150  # +150 bps for sensitive
    risk_premium_negative: int = 250  # +250 bps for negative


# ═══════════════════════════════════════════════════════════════════════════
# 6. DYNAMIC WEIGHTING PARAMETERS
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class DynamicWeightingConfig:
    """Parameters for dynamic weight adjustment"""

    # Base weights (Five Cs of Credit) - Total = 100%
    base_weight_character: float = 0.25  # 25%
    base_weight_capacity: float = 0.30  # 30%
    base_weight_capital: float = 0.20  # 20%
    base_weight_collateral: float = 0.15  # 15%
    base_weight_conditions: float = 0.10  # 10%

    # Risk profile thresholds (composite risk score)
    risk_profile_standard_max: int = 19  # 0-19 → STANDARD
    risk_profile_elevated_max: int = 39  # 20-39 → ELEVATED
    risk_profile_high_risk_max: int = 59  # 40-59 → HIGH_RISK
    # 60-100 → CRITICAL

    # Weight adjustment multipliers by risk profile
    # Format: {risk_profile: {parameter: multiplier}}
    weight_multipliers: Dict[str, Dict[str, float]] = field(default_factory=lambda: {
        "STANDARD": {
            "character": 1.0,
            "capacity": 1.0,
            "capital": 1.0,
            "collateral": 1.0,
            "conditions": 1.0,
        },
        "ELEVATED": {
            "character": 1.2,  # Increase importance
            "capacity": 1.1,
            "capital": 1.0,
            "collateral": 0.9,  # Decrease importance
            "conditions": 1.0,
        },
        "HIGH_RISK": {
            "character": 1.5,  # Significantly increase
            "capacity": 1.3,
            "capital": 1.2,
            "collateral": 0.8,
            "conditions": 1.2,
        },
        "CRITICAL": {
            "character": 2.0,  # Max importance
            "capacity": 1.5,
            "capital": 1.3,
            "collateral": 0.7,
            "conditions": 1.5,
        },
    })


# ═══════════════════════════════════════════════════════════════════════════
# 7. RED FLAG AUTO-REJECT RULES
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class RedFlagConfig:
    """Red flag detection and auto-reject rules"""

    # Auto-reject conditions (any one triggers rejection)
    auto_reject_rules: List[str] = field(default_factory=lambda: [
        "Wilful defaulter status",
        "Company struck-off or dormant",
        "CIBIL score < 500",
        "FOR ratio > 60%",
        "DSCR < 0.8",
        "Net worth negative",
        "Directors disqualified",
        "NCLT proceedings ongoing",
        "ED/CBI investigation",
        "GST fraud severity HIGH (>30% discrepancy)",
        "Criminal conviction of promoters",
        "SEBI ban or regulatory action",
        "NPA status in other banks",
    ])

    # Red flag severity scoring
    critical_red_flag_weight: int = 100  # Any critical flag → auto-reject
    high_red_flag_weight: int = 30  # High severity flags
    medium_red_flag_weight: int = 15  # Medium severity flags
    low_red_flag_weight: int = 5  # Low severity flags

    # Cumulative red flag threshold (score-based rejection)
    max_cumulative_red_flag_score: int = 50  # Total score > 50 → reject


# ═══════════════════════════════════════════════════════════════════════════
# 8. RCU VERIFICATION PARAMETERS
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class RCUThresholds:
    """RCU verification score thresholds"""

    rcu_score_minimum: int = 50  # Below 50 → reject
    rcu_score_acceptable: int = 70  # Above 70 → acceptable with observations
    rcu_score_good: int = 85  # Above 85 → good

    # Mandatory RCU for loans above (in Crores)
    mandatory_rcu_threshold_cr: float = 1.0  # RCU mandatory for loans > 1 Cr

    # RCU red flag auto-reject conditions
    rcu_auto_reject_conditions: List[str] = field(default_factory=lambda: [
        "Promoter identity mismatch",
        "Document tampering suspected",
        "No business activity observed",
        "Address is virtual/fake",
    ])


# ═══════════════════════════════════════════════════════════════════════════
# 9. GST & TAX COMPLIANCE THRESHOLDS
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class GSTThresholds:
    """GST and tax compliance thresholds"""

    # GSTR-3B vs GSTR-2A discrepancy
    gst_discrepancy_low: float = 5.0  # < 5% → low severity
    gst_discrepancy_medium: float = 15.0  # 5-15% → medium severity
    gst_discrepancy_high: float = 25.0  # 15-25% → high severity
    # > 25% → very high (auto-reject)

    # ITR vs GST vs Bank Statement consistency
    revenue_variance_acceptable: float = 10.0  # <10% variance acceptable
    revenue_variance_concerning: float = 20.0  # >20% variance concerning


# ═══════════════════════════════════════════════════════════════════════════
# 10. SCORING SYSTEM PARAMETERS
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class ScoringThresholds:
    """Final score thresholds and decision rules"""

    # Final score thresholds (0-100 scale)
    score_excellent: int = 80  # ≥80 → Approve (minimal conditions)
    score_good: int = 70  # 70-79 → Approve (standard conditions)
    score_acceptable: int = 60  # 60-69 → Approve (enhanced conditions)
    score_marginal: int = 50  # 50-59 → Conditional approval (strict monitoring)
    # <50 → Reject

    # Decision matrix weights
    financial_weight: float = 0.40  # 40% weight to financials
    character_weight: float = 0.25  # 25% weight to character/integrity
    market_conditions_weight: float = 0.15  # 15% weight to market/sector
    collateral_weight: float = 0.10  # 10% weight to collateral
    working_capital_weight: float = 0.10  # 10% weight to working capital


# ═══════════════════════════════════════════════════════════════════════════
# MASTER CONFIGURATION OBJECT
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class CreditPolicyConfig:
    """Master credit policy configuration"""

    financial: FinancialThresholds = field(default_factory=FinancialThresholds)
    working_capital: WorkingCapitalThresholds = field(default_factory=WorkingCapitalThresholds)
    for_ratio: FORThresholds = field(default_factory=FORThresholds)
    cibil: CibilThresholds = field(default_factory=CibilThresholds)
    company_age: CompanyAgeThresholds = field(default_factory=CompanyAgeThresholds)
    loan_amount: LoanAmountThresholds = field(default_factory=LoanAmountThresholds)
    sector: SectorThresholds = field(default_factory=SectorThresholds)
    dynamic_weighting: DynamicWeightingConfig = field(default_factory=DynamicWeightingConfig)
    red_flags: RedFlagConfig = field(default_factory=RedFlagConfig)
    rcu: RCUThresholds = field(default_factory=RCUThresholds)
    gst: GSTThresholds = field(default_factory=GSTThresholds)
    scoring: ScoringThresholds = field(default_factory=ScoringThresholds)

    # Institutional parameters
    institution_name: str = "Intelli-Credits Bank"
    risk_appetite: str = "MODERATE"  # CONSERVATIVE/MODERATE/AGGRESSIVE
    policy_version: str = "1.0"
    last_updated: str = "2026-03-06"

    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary"""
        return {
            "institution_name": self.institution_name,
            "risk_appetite": self.risk_appetite,
            "policy_version": self.policy_version,
            "last_updated": self.last_updated,
            "financial": self.financial.__dict__,
            "working_capital": self.working_capital.__dict__,
            "for_ratio": self.for_ratio.__dict__,
            "cibil": self.cibil.__dict__,
            "company_age": self.company_age.__dict__,
            "loan_amount": self.loan_amount.__dict__,
            "sector": self.sector.__dict__,
            "dynamic_weighting": {
                **self.dynamic_weighting.__dict__,
                "base_weights": {
                    "character": self.dynamic_weighting.base_weight_character,
                    "capacity": self.dynamic_weighting.base_weight_capacity,
                    "capital": self.dynamic_weighting.base_weight_capital,
                    "collateral": self.dynamic_weighting.base_weight_collateral,
                    "conditions": self.dynamic_weighting.base_weight_conditions,
                }
            },
            "red_flags": self.red_flags.__dict__,
            "rcu": self.rcu.__dict__,
            "gst": self.gst.__dict__,
            "scoring": self.scoring.__dict__,
        }


# ═══════════════════════════════════════════════════════════════════════════
# DEFAULT CONFIGURATION INSTANCE
# ═══════════════════════════════════════════════════════════════════════════

# Create default config instance
DEFAULT_CREDIT_POLICY = CreditPolicyConfig()


def get_config() -> CreditPolicyConfig:
    """Get the current credit policy configuration"""
    return DEFAULT_CREDIT_POLICY


def update_config(updates: Dict[str, Any]) -> CreditPolicyConfig:
    """
    Update configuration with new values.

    Args:
        updates: Dictionary of updates to apply

    Returns:
        Updated configuration
    """
    # This is a simple implementation
    # In production, you'd want validation, persistence, versioning, etc.
    config = get_config()

    for key, value in updates.items():
        if hasattr(config, key):
            setattr(config, key, value)

    return config


# ═══════════════════════════════════════════════════════════════════════════
# CONFIGURATION PROFILES
# ═══════════════════════════════════════════════════════════════════════════

def get_conservative_config() -> CreditPolicyConfig:
    """Get conservative risk appetite configuration"""
    config = CreditPolicyConfig()
    config.risk_appetite = "CONSERVATIVE"

    # Tighten thresholds
    config.financial.dscr_minimum = 1.5
    config.financial.debt_to_equity_maximum = 2.0
    config.cibil.company_score_minimum = 600
    config.for_ratio.for_healthy = 35.0
    config.loan_amount.default_ltv_ratio = 0.65

    return config


def get_aggressive_config() -> CreditPolicyConfig:
    """Get aggressive risk appetite configuration"""
    config = CreditPolicyConfig()
    config.risk_appetite = "AGGRESSIVE"

    # Relax thresholds
    config.financial.dscr_minimum = 1.1
    config.financial.debt_to_equity_maximum = 4.0
    config.cibil.company_score_minimum = 550
    config.for_ratio.for_healthy = 45.0
    config.loan_amount.default_ltv_ratio = 0.80

    return config


if __name__ == "__main__":
    # Display current configuration
    config = get_config()
    print("═" * 80)
    print("INTELLI-CREDITS CREDIT POLICY CONFIGURATION")
    print("═" * 80)
    print(f"\nInstitution: {config.institution_name}")
    print(f"Risk Appetite: {config.risk_appetite}")
    print(f"Policy Version: {config.policy_version}")
    print(f"Last Updated: {config.last_updated}")

    print("\n" + "═" * 80)
    print("FINANCIAL THRESHOLDS")
    print("═" * 80)
    print(f"DSCR Minimum: {config.financial.dscr_minimum}x")
    print(f"Debt-to-Equity Maximum: {config.financial.debt_to_equity_maximum}x")
    print(f"Current Ratio Minimum: {config.financial.current_ratio_minimum}x")

    print("\n" + "═" * 80)
    print("CIBIL THRESHOLDS")
    print("═" * 80)
    print(f"Company Score Minimum: {config.cibil.company_score_minimum}")
    print(f"Director Score Minimum: {config.cibil.director_score_minimum}")

    print("\n" + "═" * 80)
    print("FOR THRESHOLDS")
    print("═" * 80)
    print(f"Healthy: <{config.for_ratio.for_healthy}%")
    print(f"Strained: {config.for_ratio.for_healthy}-{config.for_ratio.for_strained}%")
    print(f"Over-leveraged: {config.for_ratio.for_strained}-{config.for_ratio.for_over_leveraged}%")
    print(f"Critical: >{config.for_ratio.for_over_leveraged}%")

    print("\n" + "═" * 80)
    print("SECTOR THRESHOLDS")
    print("═" * 80)
    print(f"Max Exposure - Positive Sector: {config.sector.max_exposure_positive_sector}%")
    print(f"Max Exposure - Sensitive Sector: {config.sector.max_exposure_sensitive_sector}%")
    print(f"Risk Premium - Sensitive Sector: +{config.sector.risk_premium_sensitive} bps")

    print("\n" + "═" * 80)
