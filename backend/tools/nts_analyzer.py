"""
NTS (Negative-To-Sensitive Sector) Analyzer Tool

This module analyzes sector health and classifies sectors based on:
- Industry growth trends
- NPA (Non-Performing Asset) ratios
- Regulatory environment
- Market conditions
- RBI/Government sector-specific guidelines

Banks maintain a "Negative List" or "Sensitive Sectors List" which includes:
- Sectors currently facing headwinds (e.g., airlines, real estate during downturns)
- Sectors with high NPA rates
- Over-leveraged sectors
- Cyclical sectors in downturn phase
- Sectors under regulatory scrutiny

Credit managers use NTS classification to:
1. Apply sector-specific risk premiums
2. Set exposure limits
3. Adjust lending terms
4. Apply enhanced due diligence for sensitive sectors
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import date
from enum import Enum


class SectorStatus(Enum):
    """Sector health classification"""
    POSITIVE = "POSITIVE"          # Growing sector, low NPA, favorable outlook
    STABLE = "STABLE"              # Mature sector, stable performance
    WATCH = "WATCH"                # Sector showing early warning signs
    SENSITIVE = "SENSITIVE"        # Sector under stress, needs enhanced due diligence
    NEGATIVE = "NEGATIVE"          # Sector in decline, high risk
    RESTRICTED = "RESTRICTED"      # Sector on bank's negative list, minimal exposure


class SectorCyclicality(Enum):
    """How cyclical is the sector"""
    NON_CYCLICAL = "NON_CYCLICAL"      # Defensive sectors (FMCG, pharma)
    MILDLY_CYCLICAL = "MILDLY_CYCLICAL"  # Moderate sensitivity (IT services)
    CYCLICAL = "CYCLICAL"              # High sensitivity (auto, cement)
    HIGHLY_CYCLICAL = "HIGHLY_CYCLICAL"  # Extreme sensitivity (real estate, commodities)


@dataclass
class SectorMetrics:
    """Key sector performance metrics"""
    # Growth metrics
    revenue_growth_yoy: float = 0.0      # Year-over-year revenue growth %
    projected_growth_rate: float = 0.0   # Next 2-3 years projected growth %

    # Credit quality
    sector_npa_ratio: float = 0.0        # Sector-wide NPA ratio %
    restructuring_ratio: float = 0.0     # % of restructured loans in sector

    # Market conditions
    capacity_utilization: float = 75.0   # Operating capacity utilization %
    demand_outlook: str = "STABLE"       # STRONG/STABLE/WEAK/DECLINING

    # Regulatory
    regulatory_score: int = 70           # 0-100, higher is better
    policy_support: str = "NEUTRAL"      # SUPPORTIVE/NEUTRAL/RESTRICTIVE

    # Competition
    market_concentration: str = "MODERATE"  # LOW/MODERATE/HIGH (monopoly)
    entry_barriers: str = "MODERATE"        # LOW/MODERATE/HIGH


@dataclass
class SectorRiskFactors:
    """Risk factors specific to the sector"""
    high_leverage: bool = False           # Sector typically high leveraged
    commodity_price_sensitive: bool = False  # Exposed to commodity volatility
    forex_sensitive: bool = False         # Exposed to forex risk
    policy_dependent: bool = False        # Heavily dependent on govt policy
    environmental_concerns: bool = False  # ESG/environmental issues
    technology_disruption: bool = False   # Risk of tech disruption
    credit_intensive: bool = False        # Requires significant working capital


@dataclass
class NTSClassification:
    """Final NTS classification with reasoning"""
    sector_name: str
    sector_code: str  # NIC code or internal classification
    status: str       # SectorStatus value
    risk_score: int   # 0-100, higher is more risky

    # Classification drivers
    key_strengths: List[str] = field(default_factory=list)
    key_concerns: List[str] = field(default_factory=list)

    # Lending implications
    recommended_exposure_limit: str = ""  # e.g., "< 15% of portfolio"
    enhanced_due_diligence_required: bool = False
    sector_specific_covenants: List[str] = field(default_factory=list)

    # Credit adjustments
    risk_premium_bps: int = 0        # Basis points to add to base rate
    max_ltv_ratio: float = 0.75      # Maximum loan-to-value
    preferred_tenure_years: int = 5   # Recommended max tenure

    # Monitoring
    review_frequency: str = "QUARTERLY"  # MONTHLY/QUARTERLY/HALF_YEARLY/ANNUAL
    early_warning_indicators: List[str] = field(default_factory=list)


@dataclass
class SectorAnalysisResult:
    """Complete sector analysis result"""
    sector_name: str
    analysis_date: date

    # Core classification
    classification: NTSClassification

    # Detailed metrics
    metrics: SectorMetrics
    risk_factors: SectorRiskFactors

    # Cyclical assessment
    cyclicality: str = SectorCyclicality.CYCLICAL.value
    current_cycle_phase: str = "EXPANSION"  # EXPANSION/PEAK/CONTRACTION/TROUGH

    # Historical context
    historical_npa_trend: str = "STABLE"  # IMPROVING/STABLE/DETERIORATING
    sector_stress_events_last_5y: int = 0

    # Overall assessment
    overall_recommendation: str = ""


# Sector database (simplified - in production would be from database/API)
SECTOR_DATABASE = {
    # Positive/Stable sectors
    "INFORMATION_TECHNOLOGY": {
        "name": "Information Technology / IT Services",
        "code": "NIC-62",
        "status": SectorStatus.POSITIVE.value,
        "metrics": {
            "revenue_growth_yoy": 12.5,
            "projected_growth_rate": 10.0,
            "sector_npa_ratio": 1.2,
            "capacity_utilization": 85.0,
            "demand_outlook": "STRONG",
            "regulatory_score": 85,
            "policy_support": "SUPPORTIVE",
        },
        "risk_factors": {
            "forex_sensitive": True,
            "technology_disruption": True,
        },
        "risk_score": 25,
        "risk_premium_bps": 0,
    },
    "PHARMACEUTICALS": {
        "name": "Pharmaceuticals & Healthcare",
        "code": "NIC-21",
        "status": SectorStatus.STABLE.value,
        "metrics": {
            "revenue_growth_yoy": 8.5,
            "projected_growth_rate": 9.0,
            "sector_npa_ratio": 2.1,
            "capacity_utilization": 78.0,
            "demand_outlook": "STABLE",
            "regulatory_score": 75,
            "policy_support": "SUPPORTIVE",
        },
        "risk_factors": {
            "policy_dependent": True,
            "environmental_concerns": True,
        },
        "risk_score": 30,
        "risk_premium_bps": 25,
    },
    "FMCG": {
        "name": "FMCG / Consumer Goods",
        "code": "NIC-10",
        "status": SectorStatus.STABLE.value,
        "metrics": {
            "revenue_growth_yoy": 6.5,
            "projected_growth_rate": 7.0,
            "sector_npa_ratio": 1.8,
            "capacity_utilization": 80.0,
            "demand_outlook": "STABLE",
            "regulatory_score": 80,
            "policy_support": "NEUTRAL",
        },
        "risk_factors": {
            "commodity_price_sensitive": True,
        },
        "risk_score": 28,
        "risk_premium_bps": 15,
    },

    # Watch/Sensitive sectors
    "TEXTILES": {
        "name": "Textiles & Garments",
        "code": "NIC-13",
        "status": SectorStatus.WATCH.value,
        "metrics": {
            "revenue_growth_yoy": 3.2,
            "projected_growth_rate": 4.0,
            "sector_npa_ratio": 8.5,
            "capacity_utilization": 68.0,
            "demand_outlook": "WEAK",
            "regulatory_score": 60,
            "policy_support": "SUPPORTIVE",
        },
        "risk_factors": {
            "high_leverage": True,
            "commodity_price_sensitive": True,
            "forex_sensitive": True,
            "credit_intensive": True,
        },
        "risk_score": 55,
        "risk_premium_bps": 100,
    },
    "CONSTRUCTION": {
        "name": "Construction & Infrastructure",
        "code": "NIC-42",
        "status": SectorStatus.SENSITIVE.value,
        "metrics": {
            "revenue_growth_yoy": 2.5,
            "projected_growth_rate": 5.0,
            "sector_npa_ratio": 12.3,
            "capacity_utilization": 65.0,
            "demand_outlook": "WEAK",
            "regulatory_score": 55,
            "policy_support": "SUPPORTIVE",
        },
        "risk_factors": {
            "high_leverage": True,
            "policy_dependent": True,
            "credit_intensive": True,
        },
        "risk_score": 65,
        "risk_premium_bps": 150,
    },
    "REAL_ESTATE": {
        "name": "Real Estate Development",
        "code": "NIC-68",
        "status": SectorStatus.SENSITIVE.value,
        "metrics": {
            "revenue_growth_yoy": 1.8,
            "projected_growth_rate": 3.5,
            "sector_npa_ratio": 15.2,
            "capacity_utilization": 60.0,
            "demand_outlook": "WEAK",
            "regulatory_score": 50,
            "policy_support": "NEUTRAL",
        },
        "risk_factors": {
            "high_leverage": True,
            "policy_dependent": True,
            "credit_intensive": True,
        },
        "risk_score": 70,
        "risk_premium_bps": 175,
    },

    # Negative/Restricted sectors
    "AIRLINES": {
        "name": "Airlines & Aviation",
        "code": "NIC-51",
        "status": SectorStatus.NEGATIVE.value,
        "metrics": {
            "revenue_growth_yoy": -2.5,
            "projected_growth_rate": 2.0,
            "sector_npa_ratio": 24.5,
            "capacity_utilization": 72.0,
            "demand_outlook": "WEAK",
            "regulatory_score": 45,
            "policy_support": "NEUTRAL",
        },
        "risk_factors": {
            "high_leverage": True,
            "commodity_price_sensitive": True,
            "forex_sensitive": True,
            "policy_dependent": True,
        },
        "risk_score": 85,
        "risk_premium_bps": 250,
    },
    "TELECOM": {
        "name": "Telecommunications",
        "code": "NIC-61",
        "status": SectorStatus.NEGATIVE.value,
        "metrics": {
            "revenue_growth_yoy": -1.2,
            "projected_growth_rate": 1.5,
            "sector_npa_ratio": 18.7,
            "capacity_utilization": 75.0,
            "demand_outlook": "DECLINING",
            "regulatory_score": 40,
            "policy_support": "RESTRICTIVE",
        },
        "risk_factors": {
            "high_leverage": True,
            "policy_dependent": True,
            "technology_disruption": True,
        },
        "risk_score": 78,
        "risk_premium_bps": 200,
    },
    "STEEL": {
        "name": "Steel & Iron",
        "code": "NIC-24",
        "status": SectorStatus.WATCH.value,
        "metrics": {
            "revenue_growth_yoy": 4.2,
            "projected_growth_rate": 5.5,
            "sector_npa_ratio": 9.8,
            "capacity_utilization": 70.0,
            "demand_outlook": "STABLE",
            "regulatory_score": 65,
            "policy_support": "SUPPORTIVE",
        },
        "risk_factors": {
            "high_leverage": True,
            "commodity_price_sensitive": True,
            "environmental_concerns": True,
        },
        "risk_score": 58,
        "risk_premium_bps": 125,
    },
    "POWER_GENERATION": {
        "name": "Power Generation (Thermal)",
        "code": "NIC-35",
        "status": SectorStatus.SENSITIVE.value,
        "metrics": {
            "revenue_growth_yoy": 1.5,
            "projected_growth_rate": 2.5,
            "sector_npa_ratio": 16.5,
            "capacity_utilization": 60.0,
            "demand_outlook": "WEAK",
            "regulatory_score": 50,
            "policy_support": "RESTRICTIVE",
        },
        "risk_factors": {
            "high_leverage": True,
            "policy_dependent": True,
            "environmental_concerns": True,
            "commodity_price_sensitive": True,
        },
        "risk_score": 72,
        "risk_premium_bps": 180,
    },
    "RENEWABLE_ENERGY": {
        "name": "Renewable Energy",
        "code": "NIC-35-RE",
        "status": SectorStatus.POSITIVE.value,
        "metrics": {
            "revenue_growth_yoy": 18.5,
            "projected_growth_rate": 15.0,
            "sector_npa_ratio": 3.2,
            "capacity_utilization": 82.0,
            "demand_outlook": "STRONG",
            "regulatory_score": 90,
            "policy_support": "SUPPORTIVE",
        },
        "risk_factors": {
            "policy_dependent": True,
            "technology_disruption": True,
        },
        "risk_score": 35,
        "risk_premium_bps": 50,
    },
}


def analyze_sector(
    sector_name: str,
    custom_sector_code: Optional[str] = None,
    analysis_date: Optional[date] = None,
) -> SectorAnalysisResult:
    """
    Analyze a sector and provide NTS classification.

    Args:
        sector_name: Name or key of the sector (e.g., "INFORMATION_TECHNOLOGY", "Airlines")
        custom_sector_code: Optional custom sector code
        analysis_date: Date of analysis

    Returns:
        SectorAnalysisResult with complete assessment
    """
    if analysis_date is None:
        analysis_date = date.today()

    # Normalize sector name
    sector_key = _normalize_sector_name(sector_name)

    # Get sector data
    sector_data = SECTOR_DATABASE.get(sector_key)

    if sector_data is None:
        # Unknown sector - apply conservative assessment
        return _create_unknown_sector_analysis(sector_name, analysis_date)

    # Build sector metrics
    metrics = SectorMetrics(**sector_data["metrics"])

    # Build risk factors
    risk_factors = SectorRiskFactors(**sector_data["risk_factors"])

    # Assess cyclicality
    cyclicality = _assess_cyclicality(sector_key, risk_factors)

    # Determine cycle phase (mock - would use economic indicators in production)
    cycle_phase = _determine_cycle_phase(metrics, cyclicality)

    # Build NTS classification
    classification = _build_nts_classification(
        sector_name=sector_data["name"],
        sector_code=custom_sector_code or sector_data["code"],
        status=sector_data["status"],
        risk_score=sector_data["risk_score"],
        risk_premium_bps=sector_data["risk_premium_bps"],
        metrics=metrics,
        risk_factors=risk_factors,
        cyclicality=cyclicality,
    )

    # Overall recommendation
    recommendation = _generate_recommendation(classification, metrics, risk_factors)

    return SectorAnalysisResult(
        sector_name=sector_data["name"],
        analysis_date=analysis_date,
        classification=classification,
        metrics=metrics,
        risk_factors=risk_factors,
        cyclicality=cyclicality,
        current_cycle_phase=cycle_phase,
        historical_npa_trend=_assess_npa_trend(metrics.sector_npa_ratio),
        sector_stress_events_last_5y=_count_stress_events(sector_key),
        overall_recommendation=recommendation,
    )


def _normalize_sector_name(sector_name: str) -> str:
    """Normalize sector name to match database keys"""
    # Convert to uppercase and replace spaces/special chars
    normalized = sector_name.upper().replace(" ", "_").replace("-", "_").replace("&", "")

    # Try exact match first
    if normalized in SECTOR_DATABASE:
        return normalized

    # Try fuzzy matching
    for key in SECTOR_DATABASE.keys():
        if key in normalized or normalized in key:
            return key

    # Common aliases
    aliases = {
        "IT": "INFORMATION_TECHNOLOGY",
        "SOFTWARE": "INFORMATION_TECHNOLOGY",
        "PHARMA": "PHARMACEUTICALS",
        "HEALTHCARE": "PHARMACEUTICALS",
        "CONSUMER_GOODS": "FMCG",
        "AVIATION": "AIRLINES",
        "REALESTATE": "REAL_ESTATE",
        "INFRA": "CONSTRUCTION",
        "INFRASTRUCTURE": "CONSTRUCTION",
        "TELECOM": "TELECOM",
        "RENEWABLES": "RENEWABLE_ENERGY",
        "SOLAR": "RENEWABLE_ENERGY",
        "WIND": "RENEWABLE_ENERGY",
    }

    for alias, key in aliases.items():
        if alias in normalized:
            return key

    return normalized


def _create_unknown_sector_analysis(sector_name: str, analysis_date: date) -> SectorAnalysisResult:
    """Create conservative analysis for unknown sectors"""
    metrics = SectorMetrics(
        revenue_growth_yoy=5.0,
        projected_growth_rate=5.0,
        sector_npa_ratio=7.5,
        capacity_utilization=70.0,
        demand_outlook="STABLE",
        regulatory_score=60,
        policy_support="NEUTRAL",
    )

    risk_factors = SectorRiskFactors()

    classification = NTSClassification(
        sector_name=sector_name,
        sector_code="UNKNOWN",
        status=SectorStatus.WATCH.value,
        risk_score=50,
        key_concerns=["Sector data not available - applying conservative assessment"],
        recommended_exposure_limit="< 10% of portfolio",
        enhanced_due_diligence_required=True,
        risk_premium_bps=100,
        max_ltv_ratio=0.65,
        review_frequency="QUARTERLY",
    )

    return SectorAnalysisResult(
        sector_name=sector_name,
        analysis_date=analysis_date,
        classification=classification,
        metrics=metrics,
        risk_factors=risk_factors,
        cyclicality=SectorCyclicality.CYCLICAL.value,
        current_cycle_phase="UNKNOWN",
        overall_recommendation="Sector not in database - proceed with enhanced due diligence and conservative terms",
    )


def _assess_cyclicality(sector_key: str, risk_factors: SectorRiskFactors) -> str:
    """Assess how cyclical the sector is"""
    # Non-cyclical (defensive) sectors
    non_cyclical = ["PHARMACEUTICALS", "FMCG", "UTILITIES"]
    if sector_key in non_cyclical:
        return SectorCyclicality.NON_CYCLICAL.value

    # Mildly cyclical
    mildly_cyclical = ["INFORMATION_TECHNOLOGY", "HEALTHCARE"]
    if sector_key in mildly_cyclical:
        return SectorCyclicality.MILDLY_CYCLICAL.value

    # Highly cyclical
    highly_cyclical = ["REAL_ESTATE", "AIRLINES", "STEEL", "CONSTRUCTION", "POWER_GENERATION"]
    if sector_key in highly_cyclical:
        return SectorCyclicality.HIGHLY_CYCLICAL.value

    # Default to cyclical
    return SectorCyclicality.CYCLICAL.value


def _determine_cycle_phase(metrics: SectorMetrics, cyclicality: str) -> str:
    """Determine current cycle phase"""
    if cyclicality == SectorCyclicality.NON_CYCLICAL.value:
        return "STABLE"

    # Simple heuristic based on growth and capacity utilization
    if metrics.revenue_growth_yoy > 8 and metrics.capacity_utilization > 80:
        return "EXPANSION"
    elif metrics.revenue_growth_yoy > 5 and metrics.capacity_utilization > 75:
        return "PEAK"
    elif metrics.revenue_growth_yoy < 0 or metrics.capacity_utilization < 65:
        return "CONTRACTION"
    else:
        return "TROUGH"


def _build_nts_classification(
    sector_name: str,
    sector_code: str,
    status: str,
    risk_score: int,
    risk_premium_bps: int,
    metrics: SectorMetrics,
    risk_factors: SectorRiskFactors,
    cyclicality: str,
) -> NTSClassification:
    """Build detailed NTS classification"""

    # Identify strengths
    strengths = []
    if metrics.revenue_growth_yoy > 8:
        strengths.append(f"Strong revenue growth ({metrics.revenue_growth_yoy:.1f}% YoY)")
    if metrics.sector_npa_ratio < 3:
        strengths.append(f"Low sector NPA ratio ({metrics.sector_npa_ratio:.1f}%)")
    if metrics.capacity_utilization > 80:
        strengths.append(f"High capacity utilization ({metrics.capacity_utilization:.0f}%)")
    if metrics.demand_outlook == "STRONG":
        strengths.append("Strong demand outlook")
    if metrics.policy_support == "SUPPORTIVE":
        strengths.append("Government policy support")
    if cyclicality == SectorCyclicality.NON_CYCLICAL.value:
        strengths.append("Non-cyclical defensive sector")

    # Identify concerns
    concerns = []
    if metrics.sector_npa_ratio > 10:
        concerns.append(f"High sector NPA ratio ({metrics.sector_npa_ratio:.1f}%) - significant credit stress")
    if metrics.revenue_growth_yoy < 2:
        concerns.append(f"Weak revenue growth ({metrics.revenue_growth_yoy:.1f}%)")
    if metrics.capacity_utilization < 65:
        concerns.append(f"Low capacity utilization ({metrics.capacity_utilization:.0f}%) - demand weakness")
    if metrics.demand_outlook in ["WEAK", "DECLINING"]:
        concerns.append(f"Weak demand outlook")
    if risk_factors.high_leverage:
        concerns.append("Sector typically operates with high leverage")
    if risk_factors.commodity_price_sensitive:
        concerns.append("Exposed to commodity price volatility")
    if risk_factors.policy_dependent:
        concerns.append("Heavily dependent on government policy/subsidies")
    if cyclicality == SectorCyclicality.HIGHLY_CYCLICAL.value:
        concerns.append("Highly cyclical - vulnerable to economic downturns")

    # Determine lending parameters
    if status == SectorStatus.POSITIVE.value:
        exposure_limit = "< 25% of portfolio"
        enhanced_dd = False
        max_ltv = 0.80
        tenure = 7
        review = "HALF_YEARLY"
    elif status == SectorStatus.STABLE.value:
        exposure_limit = "< 20% of portfolio"
        enhanced_dd = False
        max_ltv = 0.75
        tenure = 5
        review = "QUARTERLY"
    elif status == SectorStatus.WATCH.value:
        exposure_limit = "< 15% of portfolio"
        enhanced_dd = True
        max_ltv = 0.70
        tenure = 5
        review = "QUARTERLY"
    elif status == SectorStatus.SENSITIVE.value:
        exposure_limit = "< 10% of portfolio"
        enhanced_dd = True
        max_ltv = 0.60
        tenure = 3
        review = "QUARTERLY"
    else:  # NEGATIVE or RESTRICTED
        exposure_limit = "< 5% of portfolio or avoid"
        enhanced_dd = True
        max_ltv = 0.50
        tenure = 3
        review = "MONTHLY"

    # Sector-specific covenants
    covenants = []
    if risk_factors.high_leverage:
        covenants.append("Maintain Debt-to-Equity ratio below 2.0:1")
    if risk_factors.credit_intensive:
        covenants.append("Quarterly working capital reporting")
    if risk_factors.commodity_price_sensitive:
        covenants.append("Evidence of commodity price hedging for >50% of exposure")
    if status in [SectorStatus.SENSITIVE.value, SectorStatus.NEGATIVE.value]:
        covenants.append("Monthly financial reporting required")
        covenants.append("No dividend distribution without lender consent")

    # Early warning indicators
    ewi = [
        f"Sector NPA ratio exceeds {metrics.sector_npa_ratio + 3:.0f}%",
        "Company's revenue growth falls below sector average",
        "Capacity utilization drops below 60%",
    ]
    if risk_factors.policy_dependent:
        ewi.append("Adverse policy changes or subsidy reductions")

    return NTSClassification(
        sector_name=sector_name,
        sector_code=sector_code,
        status=status,
        risk_score=risk_score,
        key_strengths=strengths,
        key_concerns=concerns,
        recommended_exposure_limit=exposure_limit,
        enhanced_due_diligence_required=enhanced_dd,
        sector_specific_covenants=covenants,
        risk_premium_bps=risk_premium_bps,
        max_ltv_ratio=max_ltv,
        preferred_tenure_years=tenure,
        review_frequency=review,
        early_warning_indicators=ewi,
    )


def _assess_npa_trend(current_npa: float) -> str:
    """Assess NPA trend (mock - would need historical data)"""
    if current_npa < 3:
        return "STABLE"
    elif current_npa < 5:
        return "IMPROVING"
    elif current_npa < 10:
        return "STABLE"
    else:
        return "DETERIORATING"


def _count_stress_events(sector_key: str) -> int:
    """Count stress events in last 5 years (mock data)"""
    high_stress_sectors = ["AIRLINES", "TELECOM", "REAL_ESTATE", "POWER_GENERATION"]
    medium_stress_sectors = ["CONSTRUCTION", "TEXTILES", "STEEL"]

    if sector_key in high_stress_sectors:
        return 3
    elif sector_key in medium_stress_sectors:
        return 1
    else:
        return 0


def _generate_recommendation(
    classification: NTSClassification,
    metrics: SectorMetrics,
    risk_factors: SectorRiskFactors,
) -> str:
    """Generate overall lending recommendation"""
    status = classification.status

    if status == SectorStatus.POSITIVE.value:
        return (
            f"FAVORABLE sector for lending. Apply standard credit assessment with "
            f"{classification.risk_premium_bps} bps risk premium. "
            f"Monitor key sector metrics {classification.review_frequency.lower()}."
        )
    elif status == SectorStatus.STABLE.value:
        return (
            f"ACCEPTABLE sector for lending. Apply standard due diligence with "
            f"{classification.risk_premium_bps} bps risk premium. "
            f"Ensure borrower has strong fundamentals relative to sector peers."
        )
    elif status == SectorStatus.WATCH.value:
        return (
            f"CAUTION advised. Sector showing signs of stress. "
            f"Enhanced due diligence required. Apply {classification.risk_premium_bps} bps risk premium. "
            f"Conservative lending terms recommended (Max LTV: {classification.max_ltv_ratio:.0%}, "
            f"Max tenure: {classification.preferred_tenure_years} years)."
        )
    elif status == SectorStatus.SENSITIVE.value:
        return (
            f"HIGH RISK sector. Lend only to top-tier borrowers with strong fundamentals. "
            f"Mandatory enhanced due diligence. Apply {classification.risk_premium_bps} bps risk premium. "
            f"Strict monitoring required ({classification.review_frequency}). "
            f"Conservative terms: Max LTV {classification.max_ltv_ratio:.0%}, "
            f"tenure {classification.preferred_tenure_years} years."
        )
    else:  # NEGATIVE or RESTRICTED
        return (
            f"AVOID or MINIMIZE exposure. Sector in significant distress. "
            f"New lending not recommended unless exceptional circumstances. "
            f"If proceeding, require substantial promoter equity, parent/group guarantees, "
            f"and apply {classification.risk_premium_bps} bps premium."
        )


if __name__ == "__main__":
    # Test the module
    print("Testing NTS Sector Analyzer\n")
    print("=" * 100)

    test_sectors = [
        ("INFORMATION_TECHNOLOGY", "Positive"),
        ("TEXTILES", "Watch"),
        ("REAL_ESTATE", "Sensitive"),
        ("AIRLINES", "Negative"),
        ("RENEWABLE_ENERGY", "Positive"),
    ]

    for sector, expected in test_sectors:
        print(f"\n{sector} (Expected: {expected})")
        print("-" * 100)

        result = analyze_sector(sector)

        print(f"Sector: {result.sector_name}")
        print(f"Status: {result.classification.status} | Risk Score: {result.classification.risk_score}/100")
        print(f"Cyclicality: {result.cyclicality} | Current Phase: {result.current_cycle_phase}")
        print(f"Sector NPA: {result.metrics.sector_npa_ratio:.1f}% | Growth: {result.metrics.revenue_growth_yoy:.1f}%")
        print(f"Risk Premium: +{result.classification.risk_premium_bps} bps")
        print(f"\nKey Strengths ({len(result.classification.key_strengths)}):")
        for s in result.classification.key_strengths[:2]:
            print(f"  ✓ {s}")
        print(f"\nKey Concerns ({len(result.classification.key_concerns)}):")
        for c in result.classification.key_concerns[:2]:
            print(f"  ⚠ {c}")
        print(f"\nRecommendation: {result.overall_recommendation[:150]}...")
