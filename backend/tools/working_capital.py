"""
Working Capital Analyzer Tool

This module analyzes the working capital position of a company:
- Current Ratio (Current Assets / Current Liabilities)
- Quick Ratio (Liquid Assets / Current Liabilities)
- Working Capital Days (Operating Cycle Analysis)
- Cash Conversion Cycle
- Liquidity Risk Assessment

Working capital is critical for:
1. Day-to-day operations funding
2. Short-term obligation servicing
3. Business continuity assessment
4. Seasonal business cycle management
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import date
from enum import Enum


class LiquidityStatus(Enum):
    """Liquidity health classification"""
    EXCELLENT = "EXCELLENT"      # Strong liquidity position
    GOOD = "GOOD"                # Adequate liquidity
    MODERATE = "MODERATE"        # Acceptable but needs monitoring
    POOR = "POOR"                # Liquidity concerns
    CRITICAL = "CRITICAL"        # Severe liquidity crisis


class WorkingCapitalAdequacy(Enum):
    """Working capital adequacy levels"""
    SURPLUS = "SURPLUS"          # More than adequate
    ADEQUATE = "ADEQUATE"        # Sufficient for operations
    TIGHT = "TIGHT"              # Just sufficient
    INSUFFICIENT = "INSUFFICIENT"  # Below requirements
    NEGATIVE = "NEGATIVE"        # Negative working capital


@dataclass
class WorkingCapitalComponents:
    """Detailed breakdown of working capital components"""
    # Current Assets
    cash_and_bank: float = 0.0
    debtors: float = 0.0
    inventory: float = 0.0
    other_current_assets: float = 0.0

    # Current Liabilities
    creditors: float = 0.0
    short_term_loans: float = 0.0
    other_current_liabilities: float = 0.0

    # Calculated
    total_current_assets: float = 0.0
    total_current_liabilities: float = 0.0

    def __post_init__(self):
        """Calculate totals"""
        self.total_current_assets = (
            self.cash_and_bank +
            self.debtors +
            self.inventory +
            self.other_current_assets
        )
        self.total_current_liabilities = (
            self.creditors +
            self.short_term_loans +
            self.other_current_liabilities
        )


@dataclass
class OperatingCycleMetrics:
    """Operating cycle and cash conversion metrics"""
    # Days metrics
    debtor_days: float = 0.0      # Average collection period
    creditor_days: float = 0.0    # Average payment period
    inventory_days: float = 0.0   # Average inventory holding period

    # Calculated cycles
    operating_cycle_days: float = 0.0      # Inventory days + Debtor days
    cash_conversion_cycle: float = 0.0     # Operating cycle - Creditor days

    # Efficiency indicators
    working_capital_turnover: float = 0.0  # Sales / Working Capital

    def __post_init__(self):
        """Calculate derived metrics"""
        self.operating_cycle_days = self.inventory_days + self.debtor_days
        self.cash_conversion_cycle = self.operating_cycle_days - self.creditor_days


@dataclass
class LiquidityRatios:
    """Key liquidity ratios"""
    current_ratio: float = 0.0           # Current Assets / Current Liabilities
    quick_ratio: float = 0.0             # (CA - Inventory) / CL
    cash_ratio: float = 0.0              # Cash / Current Liabilities
    working_capital_ratio: float = 0.0   # Working Capital / Total Assets

    # Status indicators
    current_ratio_status: str = ""
    quick_ratio_status: str = ""


@dataclass
class WorkingCapitalAnalysis:
    """Complete working capital analysis result"""
    company_name: str
    analysis_date: date

    # Components
    components: WorkingCapitalComponents

    # Ratios
    ratios: LiquidityRatios

    # Operating cycle
    operating_metrics: OperatingCycleMetrics

    # Working capital amount
    working_capital: float = 0.0
    working_capital_adequacy: str = WorkingCapitalAdequacy.ADEQUATE.value

    # Overall assessment
    liquidity_status: str = LiquidityStatus.GOOD.value
    liquidity_score: int = 70  # 0-100 scale

    # Risk flags
    risk_flags: List[str] = field(default_factory=list)
    strengths: List[str] = field(default_factory=list)

    # Recommendations
    recommendations: List[str] = field(default_factory=list)

    # Supporting data
    annual_revenue: float = 0.0
    total_assets: float = 0.0


def analyze_working_capital(
    company_name: str,
    current_assets: float,
    current_liabilities: float,
    cash_and_bank: float = 0.0,
    debtors: float = 0.0,
    inventory: float = 0.0,
    creditors: float = 0.0,
    short_term_loans: float = 0.0,
    annual_revenue: float = 0.0,
    total_assets: float = 0.0,
    cogs: Optional[float] = None,  # Cost of Goods Sold
    debtor_days: Optional[float] = None,
    creditor_days: Optional[float] = None,
    inventory_days: Optional[float] = None,
    analysis_date: Optional[date] = None,
) -> WorkingCapitalAnalysis:
    """
    Analyze working capital position of a company.

    Args:
        company_name: Name of the company
        current_assets: Total current assets
        current_liabilities: Total current liabilities
        cash_and_bank: Cash and bank balances
        debtors: Trade debtors / receivables
        inventory: Inventory value
        creditors: Trade creditors / payables
        short_term_loans: Short-term borrowings
        annual_revenue: Annual sales revenue
        total_assets: Total assets
        cogs: Cost of goods sold (for calculating inventory days)
        debtor_days: Average collection period (if known)
        creditor_days: Average payment period (if known)
        inventory_days: Average inventory holding period (if known)
        analysis_date: Date of analysis

    Returns:
        WorkingCapitalAnalysis with complete assessment
    """
    if analysis_date is None:
        analysis_date = date.today()

    # Step 1: Build components
    other_current_assets = max(0, current_assets - cash_and_bank - debtors - inventory)
    other_current_liabilities = max(0, current_liabilities - creditors - short_term_loans)

    components = WorkingCapitalComponents(
        cash_and_bank=cash_and_bank,
        debtors=debtors,
        inventory=inventory,
        other_current_assets=other_current_assets,
        creditors=creditors,
        short_term_loans=short_term_loans,
        other_current_liabilities=other_current_liabilities,
    )

    # Step 2: Calculate working capital
    working_capital = current_assets - current_liabilities

    # Step 3: Calculate liquidity ratios
    current_ratio = current_assets / current_liabilities if current_liabilities > 0 else 0

    quick_assets = current_assets - inventory
    quick_ratio = quick_assets / current_liabilities if current_liabilities > 0 else 0

    cash_ratio = cash_and_bank / current_liabilities if current_liabilities > 0 else 0

    working_capital_ratio = working_capital / total_assets if total_assets > 0 else 0

    # Ratio status assessment
    current_ratio_status = _assess_current_ratio(current_ratio)
    quick_ratio_status = _assess_quick_ratio(quick_ratio)

    ratios = LiquidityRatios(
        current_ratio=current_ratio,
        quick_ratio=quick_ratio,
        cash_ratio=cash_ratio,
        working_capital_ratio=working_capital_ratio,
        current_ratio_status=current_ratio_status,
        quick_ratio_status=quick_ratio_status,
    )

    # Step 4: Calculate operating cycle metrics
    # If days not provided, estimate from components
    if debtor_days is None and annual_revenue > 0:
        debtor_days = (debtors / annual_revenue) * 365
    elif debtor_days is None:
        debtor_days = 0

    if creditor_days is None and cogs is not None and cogs > 0:
        creditor_days = (creditors / cogs) * 365
    elif creditor_days is None:
        creditor_days = 0

    if inventory_days is None and cogs is not None and cogs > 0:
        inventory_days = (inventory / cogs) * 365
    elif inventory_days is None:
        inventory_days = 0

    working_capital_turnover = annual_revenue / working_capital if working_capital > 0 else 0

    operating_metrics = OperatingCycleMetrics(
        debtor_days=debtor_days,
        creditor_days=creditor_days,
        inventory_days=inventory_days,
        working_capital_turnover=working_capital_turnover,
    )

    # Step 5: Assess working capital adequacy
    wc_adequacy = _assess_working_capital_adequacy(
        working_capital=working_capital,
        annual_revenue=annual_revenue,
        current_ratio=current_ratio,
    )

    # Step 6: Overall liquidity assessment
    liquidity_status, liquidity_score = _assess_overall_liquidity(
        current_ratio=current_ratio,
        quick_ratio=quick_ratio,
        cash_ratio=cash_ratio,
        working_capital=working_capital,
        cash_conversion_cycle=operating_metrics.cash_conversion_cycle,
    )

    # Step 7: Identify risk flags and strengths
    risk_flags = _identify_risk_flags(
        current_ratio=current_ratio,
        quick_ratio=quick_ratio,
        working_capital=working_capital,
        cash_conversion_cycle=operating_metrics.cash_conversion_cycle,
        debtor_days=debtor_days,
        inventory_days=inventory_days,
    )

    strengths = _identify_strengths(
        current_ratio=current_ratio,
        quick_ratio=quick_ratio,
        cash_ratio=cash_ratio,
        working_capital=working_capital,
        cash_conversion_cycle=operating_metrics.cash_conversion_cycle,
    )

    # Step 8: Generate recommendations
    recommendations = _generate_recommendations(
        liquidity_status=liquidity_status,
        wc_adequacy=wc_adequacy,
        risk_flags=risk_flags,
        current_ratio=current_ratio,
        quick_ratio=quick_ratio,
        debtor_days=debtor_days,
        creditor_days=creditor_days,
        inventory_days=inventory_days,
    )

    return WorkingCapitalAnalysis(
        company_name=company_name,
        analysis_date=analysis_date,
        components=components,
        ratios=ratios,
        operating_metrics=operating_metrics,
        working_capital=working_capital,
        working_capital_adequacy=wc_adequacy,
        liquidity_status=liquidity_status,
        liquidity_score=liquidity_score,
        risk_flags=risk_flags,
        strengths=strengths,
        recommendations=recommendations,
        annual_revenue=annual_revenue,
        total_assets=total_assets,
    )


def _assess_current_ratio(current_ratio: float) -> str:
    """Assess current ratio health"""
    if current_ratio >= 2.0:
        return "EXCELLENT"
    elif current_ratio >= 1.5:
        return "GOOD"
    elif current_ratio >= 1.2:
        return "ACCEPTABLE"
    elif current_ratio >= 1.0:
        return "MARGINAL"
    else:
        return "POOR"


def _assess_quick_ratio(quick_ratio: float) -> str:
    """Assess quick ratio health"""
    if quick_ratio >= 1.5:
        return "EXCELLENT"
    elif quick_ratio >= 1.0:
        return "GOOD"
    elif quick_ratio >= 0.75:
        return "ACCEPTABLE"
    elif quick_ratio >= 0.5:
        return "MARGINAL"
    else:
        return "POOR"


def _assess_working_capital_adequacy(
    working_capital: float,
    annual_revenue: float,
    current_ratio: float,
) -> str:
    """Assess if working capital is adequate for business needs"""
    if working_capital < 0:
        return WorkingCapitalAdequacy.NEGATIVE.value

    if annual_revenue > 0:
        wc_to_revenue = working_capital / annual_revenue
        if wc_to_revenue >= 0.25:
            return WorkingCapitalAdequacy.SURPLUS.value
        elif wc_to_revenue >= 0.15:
            return WorkingCapitalAdequacy.ADEQUATE.value
        elif wc_to_revenue >= 0.08:
            return WorkingCapitalAdequacy.TIGHT.value
        else:
            return WorkingCapitalAdequacy.INSUFFICIENT.value

    # Fallback to current ratio assessment
    if current_ratio >= 2.0:
        return WorkingCapitalAdequacy.SURPLUS.value
    elif current_ratio >= 1.5:
        return WorkingCapitalAdequacy.ADEQUATE.value
    elif current_ratio >= 1.2:
        return WorkingCapitalAdequacy.TIGHT.value
    else:
        return WorkingCapitalAdequacy.INSUFFICIENT.value


def _assess_overall_liquidity(
    current_ratio: float,
    quick_ratio: float,
    cash_ratio: float,
    working_capital: float,
    cash_conversion_cycle: float,
) -> tuple[str, int]:
    """
    Overall liquidity assessment with score (0-100).

    Returns:
        Tuple of (LiquidityStatus, score)
    """
    score = 0

    # Current ratio component (30 points)
    if current_ratio >= 2.0:
        score += 30
    elif current_ratio >= 1.5:
        score += 25
    elif current_ratio >= 1.2:
        score += 20
    elif current_ratio >= 1.0:
        score += 10
    else:
        score += 0

    # Quick ratio component (30 points)
    if quick_ratio >= 1.5:
        score += 30
    elif quick_ratio >= 1.0:
        score += 25
    elif quick_ratio >= 0.75:
        score += 20
    elif quick_ratio >= 0.5:
        score += 10
    else:
        score += 0

    # Cash ratio component (20 points)
    if cash_ratio >= 0.5:
        score += 20
    elif cash_ratio >= 0.3:
        score += 15
    elif cash_ratio >= 0.15:
        score += 10
    elif cash_ratio >= 0.05:
        score += 5
    else:
        score += 0

    # Cash conversion cycle component (20 points)
    if cash_conversion_cycle <= 30:
        score += 20
    elif cash_conversion_cycle <= 60:
        score += 15
    elif cash_conversion_cycle <= 90:
        score += 10
    elif cash_conversion_cycle <= 120:
        score += 5
    else:
        score += 0

    # Determine status
    if score >= 85:
        status = LiquidityStatus.EXCELLENT.value
    elif score >= 70:
        status = LiquidityStatus.GOOD.value
    elif score >= 50:
        status = LiquidityStatus.MODERATE.value
    elif score >= 30:
        status = LiquidityStatus.POOR.value
    else:
        status = LiquidityStatus.CRITICAL.value

    return status, score


def _identify_risk_flags(
    current_ratio: float,
    quick_ratio: float,
    working_capital: float,
    cash_conversion_cycle: float,
    debtor_days: float,
    inventory_days: float,
) -> List[str]:
    """Identify liquidity and working capital risk flags"""
    flags = []

    if working_capital < 0:
        flags.append("NEGATIVE working capital - company operating on credit")

    if current_ratio < 1.0:
        flags.append("Current ratio below 1.0 - current liabilities exceed current assets")

    if quick_ratio < 0.5:
        flags.append("Quick ratio critically low - insufficient liquid assets")

    if cash_conversion_cycle > 120:
        flags.append(f"Long cash conversion cycle ({cash_conversion_cycle:.0f} days) - cash locked in operations")

    if debtor_days > 90:
        flags.append(f"High debtor days ({debtor_days:.0f}) - poor collection efficiency")

    if inventory_days > 120:
        flags.append(f"High inventory days ({inventory_days:.0f}) - slow-moving inventory or overstocking")

    if current_ratio < 1.2 and quick_ratio < 0.75:
        flags.append("Both current and quick ratios are weak - acute liquidity stress")

    return flags


def _identify_strengths(
    current_ratio: float,
    quick_ratio: float,
    cash_ratio: float,
    working_capital: float,
    cash_conversion_cycle: float,
) -> List[str]:
    """Identify working capital strengths"""
    strengths = []

    if current_ratio >= 2.0:
        strengths.append(f"Strong current ratio ({current_ratio:.2f}) - comfortable liquidity cushion")

    if quick_ratio >= 1.0:
        strengths.append(f"Healthy quick ratio ({quick_ratio:.2f}) - good immediate liquidity")

    if cash_ratio >= 0.3:
        strengths.append(f"Good cash ratio ({cash_ratio:.2f}) - strong cash position")

    if working_capital > 0 and current_ratio >= 1.5:
        strengths.append("Positive working capital with healthy ratios - strong short-term financial health")

    if cash_conversion_cycle <= 60:
        strengths.append(f"Efficient cash conversion cycle ({cash_conversion_cycle:.0f} days) - good working capital management")

    return strengths


def _generate_recommendations(
    liquidity_status: str,
    wc_adequacy: str,
    risk_flags: List[str],
    current_ratio: float,
    quick_ratio: float,
    debtor_days: float,
    creditor_days: float,
    inventory_days: float,
) -> List[str]:
    """Generate actionable recommendations"""
    recommendations = []

    # Critical liquidity issues
    if liquidity_status in [LiquidityStatus.CRITICAL.value, LiquidityStatus.POOR.value]:
        recommendations.append("URGENT: Improve liquidity position before considering additional debt")
        recommendations.append("Consider working capital loan or overdraft facility to manage short-term obligations")

    # Working capital adequacy
    if wc_adequacy in [WorkingCapitalAdequacy.INSUFFICIENT.value, WorkingCapitalAdequacy.NEGATIVE.value]:
        recommendations.append("Infuse additional working capital through equity or long-term loans")
        recommendations.append("Review and optimize operating cycle to free up cash")

    # Debtor management
    if debtor_days > 90:
        recommendations.append(f"Improve receivables collection - current debtor days ({debtor_days:.0f}) are high")
        recommendations.append("Consider invoice discounting or factoring to improve cash flow")

    # Inventory management
    if inventory_days > 120:
        recommendations.append(f"Optimize inventory levels - current holding period ({inventory_days:.0f} days) is excessive")
        recommendations.append("Review for slow-moving or obsolete stock")

    # Creditor management
    if creditor_days < 30 and debtor_days > 60:
        recommendations.append("Negotiate better payment terms with suppliers to match collection cycle")

    # Ratio-specific
    if current_ratio < 1.2:
        recommendations.append("Current ratio needs improvement - consider restructuring short-term liabilities")

    if quick_ratio < 0.75:
        recommendations.append("Build liquid asset reserves to improve immediate solvency")

    # Positive signals
    if not risk_flags and liquidity_status == LiquidityStatus.EXCELLENT.value:
        recommendations.append("Working capital position is strong - company can comfortably service new debt")

    return recommendations


# Mock data generator for testing
def get_mock_working_capital_analysis(
    company_name: str,
    scenario: str = "healthy"
) -> WorkingCapitalAnalysis:
    """
    Generate mock working capital analysis for testing.

    Args:
        company_name: Company name
        scenario: One of "healthy", "tight", "stressed", "critical"

    Returns:
        WorkingCapitalAnalysis with mock data
    """
    scenarios = {
        "healthy": {
            "current_assets": 500_00_000,  # 5 Cr
            "current_liabilities": 250_00_000,  # 2.5 Cr
            "cash_and_bank": 100_00_000,
            "debtors": 200_00_000,
            "inventory": 150_00_000,
            "creditors": 120_00_000,
            "short_term_loans": 80_00_000,
            "annual_revenue": 2000_00_000,  # 20 Cr
            "total_assets": 1000_00_000,
            "cogs": 1400_00_000,
            "debtor_days": 36,
            "creditor_days": 31,
            "inventory_days": 39,
        },
        "tight": {
            "current_assets": 300_00_000,
            "current_liabilities": 240_00_000,
            "cash_and_bank": 30_00_000,
            "debtors": 150_00_000,
            "inventory": 100_00_000,
            "creditors": 100_00_000,
            "short_term_loans": 100_00_000,
            "annual_revenue": 1500_00_000,
            "total_assets": 800_00_000,
            "cogs": 1100_00_000,
            "debtor_days": 73,
            "creditor_days": 33,
            "inventory_days": 63,
        },
        "stressed": {
            "current_assets": 200_00_000,
            "current_liabilities": 220_00_000,
            "cash_and_bank": 15_00_000,
            "debtors": 120_00_000,
            "inventory": 50_00_000,
            "creditors": 80_00_000,
            "short_term_loans": 120_00_000,
            "annual_revenue": 1000_00_000,
            "total_assets": 600_00_000,
            "cogs": 750_00_000,
            "debtor_days": 110,
            "creditor_days": 39,
            "inventory_days": 98,
        },
        "critical": {
            "current_assets": 150_00_000,
            "current_liabilities": 300_00_000,
            "cash_and_bank": 10_00_000,
            "debtors": 90_00_000,
            "inventory": 40_00_000,
            "creditors": 100_00_000,
            "short_term_loans": 180_00_000,
            "annual_revenue": 800_00_000,
            "total_assets": 500_00_000,
            "cogs": 620_00_000,
            "debtor_days": 137,
            "creditor_days": 59,
            "inventory_days": 155,
        },
    }

    data = scenarios.get(scenario, scenarios["healthy"])

    return analyze_working_capital(
        company_name=company_name,
        **data
    )


if __name__ == "__main__":
    # Test the module
    print("Testing Working Capital Analyzer\n")
    print("=" * 80)

    # Test healthy scenario
    print("\n1. HEALTHY SCENARIO")
    print("-" * 80)
    result = get_mock_working_capital_analysis("Tech Solutions Pvt Ltd", "healthy")
    print(f"Company: {result.company_name}")
    print(f"Liquidity Status: {result.liquidity_status} (Score: {result.liquidity_score}/100)")
    print(f"Working Capital: Rs. {result.working_capital:,.0f}")
    print(f"Current Ratio: {result.ratios.current_ratio:.2f} ({result.ratios.current_ratio_status})")
    print(f"Quick Ratio: {result.ratios.quick_ratio:.2f} ({result.ratios.quick_ratio_status})")
    print(f"Cash Conversion Cycle: {result.operating_metrics.cash_conversion_cycle:.0f} days")
    print(f"\nStrengths: {len(result.strengths)}")
    for s in result.strengths:
        print(f"  ✓ {s}")

    # Test critical scenario
    print("\n\n2. CRITICAL SCENARIO")
    print("-" * 80)
    result = get_mock_working_capital_analysis("Struggling Co Ltd", "critical")
    print(f"Company: {result.company_name}")
    print(f"Liquidity Status: {result.liquidity_status} (Score: {result.liquidity_score}/100)")
    print(f"Working Capital: Rs. {result.working_capital:,.0f}")
    print(f"Current Ratio: {result.ratios.current_ratio:.2f} ({result.ratios.current_ratio_status})")
    print(f"Quick Ratio: {result.ratios.quick_ratio:.2f} ({result.ratios.quick_ratio_status})")
    print(f"\nRisk Flags: {len(result.risk_flags)}")
    for flag in result.risk_flags:
        print(f"  ⚠ {flag}")
    print(f"\nRecommendations: {len(result.recommendations)}")
    for rec in result.recommendations[:3]:
        print(f"  → {rec}")
