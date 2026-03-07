"""
Dynamic Weight Engine for Corporate Credit Assessment.

This module implements context-aware weight adjustment based on risk profile.
Instead of using static weights for all borrowers, weights are dynamically
adjusted based on factors like:
- Company age (newer companies = higher scrutiny)
- Loan amount relative to risk exposure
- Sector health (declining sectors = higher scrutiny)
- Credit history (defaults = higher scrutiny on CIBIL)
- First-time borrower status

Author: Credit Intelligence System
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple


class RiskProfile(str, Enum):
    """Risk profile classification for borrowers."""
    STANDARD = "STANDARD"           # Normal scrutiny
    ELEVATED = "ELEVATED"           # Enhanced scrutiny
    HIGH_RISK = "HIGH_RISK"         # Maximum scrutiny
    CRITICAL = "CRITICAL"           # Near auto-reject territory


class ScoringParameter(str, Enum):
    """All scoring parameters in the credit assessment framework."""
    COMPANY_PROFILE = "company_profile"
    CIBIL = "cibil"
    RCU = "rcu"
    NTS_SECTOR = "nts_sector"
    LEGAL_MCA = "legal_mca"
    FOR_RATIO = "for_ratio"
    FINANCIALS = "financials"
    WORKING_CAPITAL = "working_capital"
    COLLATERAL = "collateral"
    # Legacy Five Cs mapping
    CHARACTER = "character"
    CAPACITY = "capacity"
    CAPITAL = "capital"
    CONDITIONS = "conditions"


@dataclass
class DynamicWeightConfig:
    """Configuration output from the dynamic weight engine."""
    risk_profile: RiskProfile
    risk_score: int
    base_weights: Dict[str, float]
    multipliers: Dict[str, float]
    final_weights: Dict[str, float]
    weight_justifications: List[str]
    scoring_mode: str = "EXPANDED"  # "FIVE_CS" or "EXPANDED"

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "risk_profile": self.risk_profile.value,
            "risk_score": self.risk_score,
            "base_weights": self.base_weights,
            "multipliers": self.multipliers,
            "final_weights": self.final_weights,
            "weight_justifications": self.weight_justifications,
            "scoring_mode": self.scoring_mode,
        }


# ─── Base Weights Configuration ──────────────────────────────────────────────

# Expanded scoring model (9 parameters)
EXPANDED_BASE_WEIGHTS: Dict[str, float] = {
    "company_profile":  0.08,   # Company age, reputation, status
    "cibil":            0.18,   # Credit bureau score
    "rcu":              0.08,   # Risk Containment Unit verification
    "nts_sector":       0.08,   # Industry health analysis
    "legal_mca":        0.12,   # Legal and MCA compliance
    "for_ratio":        0.14,   # Fixed Obligation to Income Ratio
    "financials":       0.15,   # ITR, GST, P&L, Balance Sheet
    "working_capital":  0.07,   # Liquidity and cash flow
    "collateral":       0.10,   # Security coverage
}

# Legacy Five Cs model (for backward compatibility)
FIVE_CS_BASE_WEIGHTS: Dict[str, float] = {
    "character":    0.25,
    "capacity":     0.30,
    "capital":      0.20,
    "collateral":   0.15,
    "conditions":   0.10,
}

# ─── Risk Multipliers ────────────────────────────────────────────────────────

# Multipliers adjust weights based on risk profile
# Higher multiplier = more weight on that parameter for risky profiles
RISK_MULTIPLIERS: Dict[RiskProfile, Dict[str, float]] = {
    RiskProfile.STANDARD: {
        "company_profile":  1.00,
        "cibil":            1.00,
        "rcu":              1.00,
        "nts_sector":       1.00,
        "legal_mca":        1.00,
        "for_ratio":        1.00,
        "financials":       1.00,
        "working_capital":  1.00,
        "collateral":       1.00,
    },
    RiskProfile.ELEVATED: {
        "company_profile":  1.20,   # More scrutiny on company background
        "cibil":            1.25,   # Credit history becomes more important
        "rcu":              1.15,   # Verification matters more
        "nts_sector":       1.20,   # Sector risk elevated
        "legal_mca":        1.30,   # Legal compliance critical
        "for_ratio":        1.10,   # EMI burden check
        "financials":       1.00,   # Financials stay same
        "working_capital":  1.00,
        "collateral":       1.10,   # Security coverage increases
    },
    RiskProfile.HIGH_RISK: {
        "company_profile":  1.50,   # Heavily scrutinize new/small companies
        "cibil":            1.50,   # Credit history is paramount
        "rcu":              1.40,   # Must verify everything
        "nts_sector":       1.35,   # Sector risk very important
        "legal_mca":        1.50,   # Any legal issues = major concern
        "for_ratio":        1.20,   # Strict EMI check
        "financials":       0.90,   # Financials can be manipulated
        "working_capital":  1.10,
        "collateral":       1.25,   # Need strong security
    },
    RiskProfile.CRITICAL: {
        "company_profile":  1.80,
        "cibil":            1.80,
        "rcu":              1.60,
        "nts_sector":       1.50,
        "legal_mca":        1.80,
        "for_ratio":        1.30,
        "financials":       0.80,   # Less trust in financials
        "working_capital":  1.20,
        "collateral":       1.50,   # Collateral becomes critical
    },
}

# Five Cs multipliers (legacy mode)
FIVE_CS_MULTIPLIERS: Dict[RiskProfile, Dict[str, float]] = {
    RiskProfile.STANDARD: {
        "character": 1.00, "capacity": 1.00, "capital": 1.00,
        "collateral": 1.00, "conditions": 1.00,
    },
    RiskProfile.ELEVATED: {
        "character": 1.30, "capacity": 1.10, "capital": 1.00,
        "collateral": 1.20, "conditions": 1.15,
    },
    RiskProfile.HIGH_RISK: {
        "character": 1.50, "capacity": 1.00, "capital": 0.90,
        "collateral": 1.40, "conditions": 1.30,
    },
    RiskProfile.CRITICAL: {
        "character": 1.80, "capacity": 0.90, "capital": 0.80,
        "collateral": 1.60, "conditions": 1.50,
    },
}


# ─── Risk Score Calculation ──────────────────────────────────────────────────

def _calculate_risk_score(
    company_age_years: float,
    loan_amount_cr: float,
    sector_status: str,
    is_first_time_borrower: bool,
    has_existing_defaults: bool,
    cibil_score: Optional[int] = None,
    promoter_age_years: Optional[int] = None,
    existing_exposure_cr: float = 0.0,
) -> Tuple[int, List[str]]:
    """
    Calculate a composite risk score (0-100) based on multiple factors.

    Returns:
        Tuple of (risk_score, list of risk factors identified)
    """
    risk_score = 0
    risk_factors: List[str] = []

    # ─── Factor 1: Company Age ───────────────────────────────────────────────
    if company_age_years < 1:
        risk_score += 25
        risk_factors.append(f"Company age < 1 year ({company_age_years:.1f} yrs) - Very new entity")
    elif company_age_years < 2:
        risk_score += 18
        risk_factors.append(f"Company age < 2 years ({company_age_years:.1f} yrs) - New entity")
    elif company_age_years < 3:
        risk_score += 12
        risk_factors.append(f"Company age < 3 years ({company_age_years:.1f} yrs) - Relatively new")
    elif company_age_years < 5:
        risk_score += 6
        risk_factors.append(f"Company age < 5 years ({company_age_years:.1f} yrs) - Moderate track record")
    # 5+ years = no additional risk

    # ─── Factor 2: Loan Amount (absolute risk) ───────────────────────────────
    if loan_amount_cr > 50:
        risk_score += 20
        risk_factors.append(f"Large exposure: Rs.{loan_amount_cr:.1f} Cr (>50 Cr)")
    elif loan_amount_cr > 25:
        risk_score += 14
        risk_factors.append(f"Significant exposure: Rs.{loan_amount_cr:.1f} Cr (>25 Cr)")
    elif loan_amount_cr > 10:
        risk_score += 8
        risk_factors.append(f"Moderate exposure: Rs.{loan_amount_cr:.1f} Cr (>10 Cr)")
    elif loan_amount_cr > 5:
        risk_score += 4
        risk_factors.append(f"Standard exposure: Rs.{loan_amount_cr:.1f} Cr (>5 Cr)")

    # ─── Factor 3: Loan Amount relative to Company Age ───────────────────────
    # A 2-year old company asking for 20 Cr is riskier than a 10-year old company
    if company_age_years > 0:
        loan_age_ratio = loan_amount_cr / company_age_years
        if loan_age_ratio > 10:
            risk_score += 15
            risk_factors.append(f"High loan-to-age ratio: {loan_age_ratio:.1f} Cr/year")
        elif loan_age_ratio > 5:
            risk_score += 8
            risk_factors.append(f"Elevated loan-to-age ratio: {loan_age_ratio:.1f} Cr/year")

    # ─── Factor 4: Sector Status ─────────────────────────────────────────────
    sector_upper = sector_status.upper() if sector_status else ""
    if sector_upper in ["DECLINING", "NEGATIVE", "STRESSED"]:
        risk_score += 20
        risk_factors.append(f"Sector status: {sector_status} - Industry under stress")
    elif sector_upper == "NEGATIVE_LIST":
        risk_score += 30
        risk_factors.append(f"Sector on RBI negative list - High regulatory risk")
    elif sector_upper in ["STABLE", "NEUTRAL"]:
        risk_score += 5
        risk_factors.append(f"Sector status: {sector_status} - Stable industry")
    # Growing/Positive = no additional risk

    # ─── Factor 5: First-Time Borrower ───────────────────────────────────────
    if is_first_time_borrower:
        risk_score += 12
        risk_factors.append("First-time borrower - No credit relationship history")

    # ─── Factor 6: Existing Defaults ─────────────────────────────────────────
    if has_existing_defaults:
        risk_score += 25
        risk_factors.append("History of defaults - Significant credit risk")

    # ─── Factor 7: CIBIL Score (if available) ────────────────────────────────
    if cibil_score is not None:
        if cibil_score < 550:
            risk_score += 20
            risk_factors.append(f"Very poor CIBIL score: {cibil_score}")
        elif cibil_score < 650:
            risk_score += 12
            risk_factors.append(f"Below average CIBIL score: {cibil_score}")
        elif cibil_score < 700:
            risk_score += 6
            risk_factors.append(f"Average CIBIL score: {cibil_score}")

    # ─── Factor 8: Existing Exposure Concentration ───────────────────────────
    if existing_exposure_cr > 0:
        new_exposure_ratio = loan_amount_cr / (existing_exposure_cr + loan_amount_cr)
        if new_exposure_ratio > 0.5:
            risk_score += 10
            risk_factors.append(f"New loan is {new_exposure_ratio*100:.0f}% of total exposure")

    # Cap risk score at 100
    risk_score = min(risk_score, 100)

    return risk_score, risk_factors


def _classify_risk_profile(risk_score: int) -> RiskProfile:
    """Classify risk profile based on composite risk score."""
    if risk_score >= 60:
        return RiskProfile.CRITICAL
    elif risk_score >= 40:
        return RiskProfile.HIGH_RISK
    elif risk_score >= 20:
        return RiskProfile.ELEVATED
    else:
        return RiskProfile.STANDARD


def _normalize_weights(weights: Dict[str, float]) -> Dict[str, float]:
    """Normalize weights to sum to 1.0."""
    total = sum(weights.values())
    if total == 0:
        return weights
    return {k: round(v / total, 4) for k, v in weights.items()}


# ─── Main Function ───────────────────────────────────────────────────────────

def compute_dynamic_weights(
    company_age_years: float = 5.0,
    loan_amount_cr: float = 1.0,
    sector_status: str = "STABLE",
    is_first_time_borrower: bool = False,
    has_existing_defaults: bool = False,
    cibil_score: Optional[int] = None,
    existing_exposure_cr: float = 0.0,
    scoring_mode: str = "EXPANDED",  # "EXPANDED" or "FIVE_CS"
) -> DynamicWeightConfig:
    """
    Compute dynamic weights based on borrower risk profile.

    This is the core function that adjusts parameter weights based on
    contextual risk factors. The philosophy:

    - LOW RISK borrowers: Use standard weights (balanced assessment)
    - HIGH RISK borrowers: Increase weights on verification, credit history,
      legal compliance; decrease reliance on self-reported financials

    Args:
        company_age_years: Age of the company in years
        loan_amount_cr: Requested loan amount in Crores (INR)
        sector_status: Industry health status (GROWING/STABLE/DECLINING/NEGATIVE_LIST)
        is_first_time_borrower: Whether this is a new banking relationship
        has_existing_defaults: Whether there's a history of defaults
        cibil_score: Commercial CIBIL score (300-900)
        existing_exposure_cr: Existing credit exposure in Crores
        scoring_mode: "EXPANDED" (9 params) or "FIVE_CS" (5 params)

    Returns:
        DynamicWeightConfig with computed weights and justifications
    """
    # Step 1: Calculate risk score
    risk_score, risk_factors = _calculate_risk_score(
        company_age_years=company_age_years,
        loan_amount_cr=loan_amount_cr,
        sector_status=sector_status,
        is_first_time_borrower=is_first_time_borrower,
        has_existing_defaults=has_existing_defaults,
        cibil_score=cibil_score,
        existing_exposure_cr=existing_exposure_cr,
    )

    # Step 2: Classify risk profile
    risk_profile = _classify_risk_profile(risk_score)

    # Step 3: Select base weights and multipliers based on scoring mode
    if scoring_mode.upper() == "FIVE_CS":
        base_weights = FIVE_CS_BASE_WEIGHTS.copy()
        multipliers = FIVE_CS_MULTIPLIERS.get(risk_profile, FIVE_CS_MULTIPLIERS[RiskProfile.STANDARD])
    else:
        base_weights = EXPANDED_BASE_WEIGHTS.copy()
        multipliers = RISK_MULTIPLIERS.get(risk_profile, RISK_MULTIPLIERS[RiskProfile.STANDARD])

    # Step 4: Apply multipliers to base weights
    adjusted_weights: Dict[str, float] = {}
    for param, base_weight in base_weights.items():
        multiplier = multipliers.get(param, 1.0)
        adjusted_weights[param] = base_weight * multiplier

    # Step 5: Normalize to sum = 1.0
    final_weights = _normalize_weights(adjusted_weights)

    # Step 6: Build justifications
    justifications = [
        f"Risk Profile: {risk_profile.value} (Score: {risk_score}/100)",
    ]
    justifications.extend(risk_factors)

    # Add weight adjustment summary
    significant_changes = []
    for param, final_w in final_weights.items():
        base_w = base_weights.get(param, 0)
        if base_w > 0:
            pct_change = ((final_w - base_w) / base_w) * 100
            if abs(pct_change) > 10:
                direction = "increased" if pct_change > 0 else "decreased"
                significant_changes.append(
                    f"{param}: {base_w*100:.0f}% -> {final_w*100:.1f}% ({direction} by {abs(pct_change):.0f}%)"
                )

    if significant_changes:
        justifications.append("Significant weight adjustments:")
        justifications.extend([f"  - {c}" for c in significant_changes])

    return DynamicWeightConfig(
        risk_profile=risk_profile,
        risk_score=risk_score,
        base_weights=base_weights,
        multipliers=multipliers,
        final_weights=final_weights,
        weight_justifications=justifications,
        scoring_mode=scoring_mode.upper(),
    )


# ─── Utility Functions ───────────────────────────────────────────────────────

def get_weight_for_parameter(
    config: DynamicWeightConfig,
    parameter: str,
) -> float:
    """Get the final weight for a specific parameter."""
    return config.final_weights.get(parameter, 0.0)


def compute_weighted_score(
    scores: Dict[str, float],
    config: DynamicWeightConfig,
) -> float:
    """
    Compute the weighted total score using dynamic weights.

    Args:
        scores: Dict of {parameter_name: score (0-100)}
        config: DynamicWeightConfig from compute_dynamic_weights()

    Returns:
        Weighted total score (0-100)
    """
    total = 0.0
    for param, score in scores.items():
        weight = config.final_weights.get(param, 0.0)
        total += score * weight
    return round(total, 2)


def map_five_cs_to_expanded(five_cs_scores: Dict[str, float]) -> Dict[str, float]:
    """
    Map Five Cs scores to expanded parameters (approximation).

    This allows backward compatibility when only Five Cs data is available.
    """
    return {
        "company_profile": five_cs_scores.get("character", 50) * 0.4 + 30,  # Partial mapping
        "cibil": five_cs_scores.get("character", 50),  # Character includes credit history
        "rcu": 70,  # Default if not available
        "nts_sector": five_cs_scores.get("conditions", 50),  # Conditions = sector
        "legal_mca": five_cs_scores.get("character", 50) * 0.6 + 20,  # Partial mapping
        "for_ratio": five_cs_scores.get("capacity", 50),  # Capacity includes debt servicing
        "financials": five_cs_scores.get("capacity", 50) * 0.5 + five_cs_scores.get("capital", 50) * 0.5,
        "working_capital": five_cs_scores.get("capital", 50),
        "collateral": five_cs_scores.get("collateral", 50),
    }


# ─── Example Usage ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Example 1: Established company with good track record
    config1 = compute_dynamic_weights(
        company_age_years=10,
        loan_amount_cr=5.0,
        sector_status="GROWING",
        is_first_time_borrower=False,
        has_existing_defaults=False,
        cibil_score=780,
    )
    print("=" * 60)
    print("EXAMPLE 1: Established Company")
    print(f"Risk Profile: {config1.risk_profile.value}")
    print(f"Risk Score: {config1.risk_score}")
    print("Final Weights:", config1.final_weights)
    print()

    # Example 2: New company requesting large loan
    config2 = compute_dynamic_weights(
        company_age_years=1.5,
        loan_amount_cr=15.0,
        sector_status="DECLINING",
        is_first_time_borrower=True,
        has_existing_defaults=False,
        cibil_score=650,
    )
    print("=" * 60)
    print("EXAMPLE 2: New Company, Large Loan, Declining Sector")
    print(f"Risk Profile: {config2.risk_profile.value}")
    print(f"Risk Score: {config2.risk_score}")
    print("Final Weights:", config2.final_weights)
    print("\nJustifications:")
    for j in config2.weight_justifications:
        print(f"  {j}")
