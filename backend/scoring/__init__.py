"""
Scoring module for Intelli-Credit.
Contains dynamic weighting, risk matrix, and red flag detection engines.
"""

from .dynamic_weights import (
    compute_dynamic_weights,
    RiskProfile,
    DynamicWeightConfig,
)
from .risk_matrix import (
    RiskFactor,
    CompanyRiskProfile,
    compute_company_risk_profile,
)
from .red_flag_engine import (
    RedFlag,
    RedFlagResult,
    evaluate_red_flags,
)

__all__ = [
    "compute_dynamic_weights",
    "RiskProfile",
    "DynamicWeightConfig",
    "RiskFactor",
    "CompanyRiskProfile",
    "compute_company_risk_profile",
    "RedFlag",
    "RedFlagResult",
    "evaluate_red_flags",
]
