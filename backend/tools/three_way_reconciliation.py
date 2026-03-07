"""
Three-Way Financial Reconciliation — Financial Fraud Detection Engine

Compares financial data from multiple sources to detect discrepancies:
1. Audited Financial Statements (Balance Sheet, P&L)
2. GST Returns (GSTR-1, GSTR-3B)
3. Bank Statement Credits (actual money inflow)
4. Income Tax Returns (declared income)

Variance Thresholds:
- 0-10%: ✅ Acceptable (normal business variation)
- 10-25%: ⚠️  Minor discrepancy (requires explanation)
- 25-40%: 🔶 High discrepancy (red flag for review)
- >40%: 🚨 RF025 (Potential financial fraud - auto-escalate)

Purpose:
Detect revenue inflation, tax evasion, or financial manipulation by
cross-verifying declared income across independent sources.

Author: Credit Intelligence System
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class FinancialSource:
    """Financial data from a single source."""
    source_name: str
    revenue: Optional[float] = None
    profit: Optional[float] = None
    period: str = "FY 2023-24"
    verified: bool = False
    confidence: float = 0.8


@dataclass
class Discrepancy:
    """Represents a financial discrepancy."""
    metric: str  # revenue, profit, etc.
    source1: str
    value1: float
    source2: str
    value2: float
    variance_pct: float
    variance_amount: float
    severity: str  # OK, MINOR, HIGH, CRITICAL
    explanation: Optional[str] = None


@dataclass
class ReconciliationResult:
    """Result from three-way reconciliation."""
    reconciled_revenue: Optional[float]
    reconciled_profit: Optional[float]
    discrepancies: List[Discrepancy]
    overall_variance: float
    fraud_risk_score: float  # 0-100 (higher = higher risk)
    flags: List[str]
    confidence: float
    data_quality_score: float


async def perform_three_way_reconciliation(
    financial_statements: Dict[str, Any],
    gst_data: Dict[str, Any],
    bank_statements: Dict[str, Any],
    itr_data: Optional[Dict[str, Any]] = None,
    tolerance_pct: float = 10.0
) -> ReconciliationResult:
    """
    Perform three-way (or four-way) financial reconciliation.
    
    Args:
        financial_statements: Audited financials (P&L, Balance Sheet)
        gst_data: GST returns data
        bank_statements: Bank account data
        itr_data: Income tax returns (optional)
        tolerance_pct: Acceptable variance percentage
        
    Returns:
        ReconciliationResult with discrepancies and fraud risk
    """
    logger.info("🔍 Starting three-way financial reconciliation")
    
    # Extract financial data from each source
    sources = _extract_financial_sources(
        financial_statements,
        gst_data,
        bank_statements,
        itr_data
    )
    
    # Perform pairwise comparisons
    discrepancies = _compare_sources(sources, tolerance_pct)
    
    # Calculate reconciled values (weighted average based on confidence)
    reconciled_revenue = _calculate_reconciled_value(
        sources, "revenue"
    )
    reconciled_profit = _calculate_reconciled_value(
        sources, "profit"
    )
    
    # Calculate overall variance
    overall_variance = _calculate_overall_variance(discrepancies)
    
    # Calculate fraud risk score
    fraud_risk_score = _calculate_fraud_risk(discrepancies, overall_variance)
    
    # Generate flags
    flags = _generate_flags(discrepancies, fraud_risk_score)
    
    # Calculate data quality score
    data_quality = _calculate_data_quality(sources)
    
    # Calculate confidence in reconciliation
    confidence = _calculate_reconciliation_confidence(
        sources, discrepancies
    )
    
    logger.info(
        f"✅ Reconciliation complete | "
        f"Variance: {overall_variance:.1f}% | "
        f"Fraud Risk: {fraud_risk_score:.1f}/100 | "
        f"Discrepancies: {len(discrepancies)}"
    )
    
    return ReconciliationResult(
        reconciled_revenue=reconciled_revenue,
        reconciled_profit=reconciled_profit,
        discrepancies=discrepancies,
        overall_variance=overall_variance,
        fraud_risk_score=fraud_risk_score,
        flags=flags,
        confidence=confidence,
        data_quality_score=data_quality
    )


def _extract_financial_sources(
    financials: Dict[str, Any],
    gst: Dict[str, Any],
    bank: Dict[str, Any],
    itr: Optional[Dict[str, Any]]
) -> List[FinancialSource]:
    """Extract comparable financial data from all sources."""
    sources = []
    
    # Source 1: Financial Statements (most authoritative if audited)
    if financials:
        sources.append(FinancialSource(
            source_name="Financial Statements",
            revenue=financials.get("revenue") or financials.get("total_revenue"),
            profit=financials.get("net_profit") or financials.get("profit_after_tax"),
            period=financials.get("period", "FY 2023-24"),
            verified=financials.get("is_audited", False),
            confidence=0.9 if financials.get("is_audited") else 0.7
        ))
    
    # Source 2: GST Returns
    if gst:
        gst_revenue = gst.get("annual_turnover") or gst.get("total_taxable_value")
        if gst_revenue:
            sources.append(FinancialSource(
                source_name="GST Returns",
                revenue=gst_revenue,
                profit=None,  # GST doesn't report profit
                period=gst.get("period", "FY 2023-24"),
                verified=True,  # GST is verified by tax authority
                confidence=0.85
            ))
    
    # Source 3: Bank Statements
    if bank:
        bank_credits = bank.get("total_credits_annual") or bank.get("annual_inflow")
        if bank_credits:
            sources.append(FinancialSource(
                source_name="Bank Statements",
                revenue=bank_credits,  # Credits as proxy for revenue
                profit=None,  # Can't determine profit from bank statements
                period=bank.get("period", "FY 2023-24"),
                verified=True,
                confidence=0.8
            ))
    
    # Source 4: Income Tax Returns (if available)
    if itr:
        itr_revenue = itr.get("gross_receipts") or itr.get("turnover")
        itr_profit = itr.get("taxable_income") or itr.get("net_profit")
        if itr_revenue:
            sources.append(FinancialSource(
                source_name="ITR",
                revenue=itr_revenue,
                profit=itr_profit,
                period=itr.get("assessment_year", "AY 2024-25"),
                verified=True,
                confidence=0.9
            ))
    
    return sources


def _compare_sources(
    sources: List[FinancialSource],
    tolerance_pct: float
) -> List[Discrepancy]:
    """Compare all sources pairwise to detect discrepancies."""
    discrepancies = []
    
    # Compare revenues
    revenue_sources = [s for s in sources if s.revenue is not None]
    
    for i in range(len(revenue_sources)):
        for j in range(i + 1, len(revenue_sources)):
            source1 = revenue_sources[i]
            source2 = revenue_sources[j]
            
            variance_pct = abs(source1.revenue - source2.revenue) / source1.revenue * 100
            variance_amount = abs(source1.revenue - source2.revenue)
            
            # Determine severity
            if variance_pct <= tolerance_pct:
                severity = "OK"
            elif variance_pct <= 25:
                severity = "MINOR"
            elif variance_pct <= 40:
                severity = "HIGH"
            else:
                severity = "CRITICAL"
            
            if severity != "OK":
                discrepancies.append(Discrepancy(
                    metric="revenue",
                    source1=source1.source_name,
                    value1=source1.revenue,
                    source2=source2.source_name,
                    value2=source2.revenue,
                    variance_pct=variance_pct,
                    variance_amount=variance_amount,
                    severity=severity,
                    explanation=_generate_explanation(
                        source1.source_name,
                        source2.source_name,
                        variance_pct
                    )
                ))
    
    # Compare profits (if available from multiple sources)
    profit_sources = [s for s in sources if s.profit is not None]
    
    for i in range(len(profit_sources)):
        for j in range(i + 1, len(profit_sources)):
            source1 = profit_sources[i]
            source2 = profit_sources[j]
            
            if source1.profit <= 0 or source2.profit <= 0:
                continue  # Skip negative profits
            
            variance_pct = abs(source1.profit - source2.profit) / abs(source1.profit) * 100
            variance_amount = abs(source1.profit - source2.profit)
            
            if variance_pct <= tolerance_pct:
                severity = "OK"
            elif variance_pct <= 25:
                severity = "MINOR"
            elif variance_pct <= 40:
                severity = "HIGH"
            else:
                severity = "CRITICAL"
            
            if severity != "OK":
                discrepancies.append(Discrepancy(
                    metric="profit",
                    source1=source1.source_name,
                    value1=source1.profit,
                    source2=source2.source_name,
                    value2=source2.profit,
                    variance_pct=variance_pct,
                    variance_amount=variance_amount,
                    severity=severity,
                    explanation=f"Profit variance of {variance_pct:.1f}% between {source1.source_name} and {source2.source_name}"
                ))
    
    return discrepancies


def _calculate_reconciled_value(
    sources: List[FinancialSource],
    metric: str
) -> Optional[float]:
    """
    Calculate reconciled value using weighted average based on confidence.
    
    Args:
        sources: List of financial sources
        metric: "revenue" or "profit"
        
    Returns:
        Weighted average value
    """
    values = []
    weights = []
    
    for source in sources:
        value = getattr(source, metric)
        if value is not None and value > 0:
            values.append(value)
            weights.append(source.confidence)
    
    if not values:
        return None
    
    # Weighted average
    weighted_avg = sum(v * w for v, w in zip(values, weights)) / sum(weights)
    
    return weighted_avg


def _calculate_overall_variance(discrepancies: List[Discrepancy]) -> float:
    """Calculate overall variance across all discrepancies."""
    if not discrepancies:
        return 0.0
    
    # Use weighted average based on severity
    severity_weights = {
        "MINOR": 1.0,
        "HIGH": 2.0,
        "CRITICAL": 3.0
    }
    
    total_variance = 0.0
    total_weight = 0.0
    
    for disc in discrepancies:
        weight = severity_weights.get(disc.severity, 1.0)
        total_variance += disc.variance_pct * weight
        total_weight += weight
    
    return total_variance / total_weight if total_weight > 0 else 0.0


def _calculate_fraud_risk(
    discrepancies: List[Discrepancy],
    overall_variance: float
) -> float:
    """
    Calculate fraud risk score (0-100).
    
    Higher score = Higher risk of financial manipulation
    """
    base_score = 0.0
    
    # Score based on overall variance
    if overall_variance > 40:
        base_score = 80
    elif overall_variance > 25:
        base_score = 60
    elif overall_variance > 15:
        base_score = 40
    elif overall_variance > 10:
        base_score = 20
    else:
        base_score = 10
    
    # Add points for critical discrepancies
    critical_count = sum(1 for d in discrepancies if d.severity == "CRITICAL")
    base_score += critical_count * 15
    
    # Add points for high discrepancies
    high_count = sum(1 for d in discrepancies if d.severity == "HIGH")
    base_score += high_count * 8
    
    # Cap at 100
    return min(100, base_score)


def _generate_flags(
    discrepancies: List[Discrepancy],
    fraud_risk_score: float
) -> List[str]:
    """Generate red flags based on discrepancies."""
    flags = []
    
    # Critical discrepancies
    critical = [d for d in discrepancies if d.severity == "CRITICAL"]
    if critical:
        flags.append(
            f"RF025: Financial reconciliation fraud - "
            f"{len(critical)} critical discrepanc{'y' if len(critical) == 1 else 'ies'} detected"
        )
    
    # High variance in revenue
    revenue_discs = [d for d in discrepancies if d.metric == "revenue"]
    if revenue_discs:
        max_variance = max(d.variance_pct for d in revenue_discs)
        if max_variance > 40:
            flags.append(f"Revenue variance >40% across sources ({max_variance:.1f}%)")
    
    # Multiple high-severity issues
    high_count = sum(1 for d in discrepancies if d.severity in ["HIGH", "CRITICAL"])
    if high_count >= 3:
        flags.append(f"Multiple financial discrepancies detected ({high_count})")
    
    # Fraud risk assessment
    if fraud_risk_score >= 70:
        flags.append(f"High fraud risk score: {fraud_risk_score:.1f}/100")
    
    return flags


def _calculate_data_quality(sources: List[FinancialSource]) -> float:
    """Calculate data quality score based on source availability and verification."""
    if not sources:
        return 0.0
    
    # Base score: number of sources available
    base_score = min(len(sources) / 4.0, 1.0) * 50  # Max 50 points for 4 sources
    
    # Additional points for verified sources
    verified_count = sum(1 for s in sources if s.verified)
    verification_score = (verified_count / len(sources)) * 30  # Max 30 points
    
    # Additional points for high confidence sources
    avg_confidence = sum(s.confidence for s in sources) / len(sources)
    confidence_score = avg_confidence * 20  # Max 20 points
    
    return base_score + verification_score + confidence_score


def _calculate_reconciliation_confidence(
    sources: List[FinancialSource],
    discrepancies: List[Discrepancy]
) -> float:
    """Calculate confidence in reconciliation results."""
    if not sources:
        return 0.0
    
    # Start with average source confidence
    base_confidence = sum(s.confidence for s in sources) / len(sources)
    
    # Reduce confidence for discrepancies
    if discrepancies:
        critical_penalty = sum(0.15 for d in discrepancies if d.severity == "CRITICAL")
        high_penalty = sum(0.08 for d in discrepancies if d.severity == "HIGH")
        minor_penalty = sum(0.03 for d in discrepancies if d.severity == "MINOR")
        
        total_penalty = critical_penalty + high_penalty + minor_penalty
        base_confidence -= total_penalty
    
    return max(0.1, min(1.0, base_confidence))


def _generate_explanation(source1: str, source2: str, variance_pct: float) -> str:
    """Generate human-readable explanation for discrepancy."""
    if variance_pct > 40:
        return (
            f"Significant {variance_pct:.1f}% variance between {source1} and {source2}. "
            "This suggests potential revenue inflation, undisclosed income, or data errors. "
            "Immediate investigation required."
        )
    elif variance_pct > 25:
        return (
            f"High {variance_pct:.1f}% variance between {source1} and {source2}. "
            "This warrants detailed scrutiny and explanation from the borrower."
        )
    elif variance_pct > 10:
        return (
            f"Moderate {variance_pct:.1f}% variance between {source1} and {source2}. "
            "May be due to timing differences, accounting methods, or legitimate business factors."
        )
    else:
        return f"Minor {variance_pct:.1f}% variance - within acceptable range."


# ─── Integration Example ─────────────────────────────────────────────────────

async def main_example():
    """Example usage of three-way reconciliation."""
    
    # Scenario 1: Clean company with minimal variance
    print("="*70)
    print("SCENARIO 1: Clean Company (Minimal Variance)")
    print("="*70)
    
    result1 = await perform_three_way_reconciliation(
        financial_statements={
            "revenue": 500_000_000,
            "net_profit": 50_000_000,
            "is_audited": True,
            "period": "FY 2023-24"
        },
        gst_data={
            "annual_turnover": 485_000_000,  # 3% lower (acceptable)
            "period": "FY 2023-24"
        },
        bank_statements={
            "total_credits_annual": 510_000_000,  # 2% higher (acceptable)
            "period": "FY 2023-24"
        }
    )
    
    print(f"Reconciled Revenue: ₹{result1.reconciled_revenue:,.0f}")
    print(f"Overall Variance: {result1.overall_variance:.2f}%")
    print(f"Fraud Risk Score: {result1.fraud_risk_score:.1f}/100")
    print(f"Discrepancies: {len(result1.discrepancies)}")
    print(f"Flags: {result1.flags if result1.flags else 'None'}")
    
    # Scenario 2: Suspicious company with high variance
    print("\n" + "="*70)
    print("SCENARIO 2: Suspicious Company (High Variance - Potential Fraud)")
    print("="*70)
    
    result2 = await perform_three_way_reconciliation(
        financial_statements={
            "revenue": 800_000_000,  # Inflated
            "net_profit": 80_000_000,
            "is_audited": False,  # Not audited!
            "period": "FY 2023-24"
        },
        gst_data={
            "annual_turnover": 450_000_000,  # 44% lower - major red flag!
            "period": "FY 2023-24"
        },
        bank_statements={
            "total_credits_annual": 420_000_000,  # 48% lower - critical!
            "period": "FY 2023-24"
        },
        itr_data={
            "gross_receipts": 480_000_000,  # 40% lower
            "taxable_income": 35_000_000,
            "assessment_year": "AY 2024-25"
        }
    )
    
    print(f"Reconciled Revenue: ₹{result2.reconciled_revenue:,.0f}")
    print(f"Overall Variance: {result2.overall_variance:.2f}%")
    print(f"Fraud Risk Score: {result2.fraud_risk_score:.1f}/100")
    print(f"Discrepancies: {len(result2.discrepancies)}")
    print("\nFlags:")
    for flag in result2.flags:
        print(f"  🚨 {flag}")
    
    print("\nDetailed Discrepancies:")
    for disc in result2.discrepancies:
        print(f"\n  {disc.metric.upper()} - {disc.severity}")
        print(f"    {disc.source1}: ₹{disc.value1:,.0f}")
        print(f"    {disc.source2}: ₹{disc.value2:,.0f}")
        print(f"    Variance: {disc.variance_pct:.1f}% (₹{disc.variance_amount:,.0f})")
        if disc.explanation:
            print(f"    ⚠️  {disc.explanation}")


if __name__ == "__main__":
    asyncio.run(main_example())
