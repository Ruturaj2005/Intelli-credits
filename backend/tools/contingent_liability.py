"""
Contingent Liability Scanner — Hidden Obligation Detector

Identifies contingent (potential) liabilities that may crystallize:
1. Tax disputes (Income Tax, GST, Customs)
2. Corporate guarantees given to group companies
3. Pending litigation (customer claims, supplier disputes)
4. Disputed statutory dues
5. Contractual obligations (penalties, liquidated damages)
6. Environmental liabilities
7. Employee-related claims

Red Flag Rules:
- Contingent liabilities >50% of net worth → High risk
- Tax disputes >₹10 Cr → Critical flag
- Multiple litigation cases → Concern

Purpose:
Contingent liabilities don't appear on balance sheet but can
materialize and impact repayment ability.

Author: Credit Intelligence System
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ContingentLiability:
    """A contingent liability."""
    category: str  # Tax, Legal, Guarantee, Contractual
    description: str
    amount: float
    probability: str  # High, Medium, Low
    status: str  # Pending, Under Appeal, etc.
    source: str  # Financial statements, Court records, etc.
    filing_date: Optional[str] = None


@dataclass
class ContingentLiabilityResult:
    """Result from contingent liability scanner."""
    score: float  # 0-100
    flags: List[str]
    data: Dict[str, Any]
    confidence: float
    
    total_contingent_amount: float = 0.0
    high_probability_amount: float = 0.0
    contingent_to_networth_ratio: float = 0.0
    liabilities: List[ContingentLiability] = field(default_factory=list)


async def scan_contingent_liabilities(
    company_data: Dict[str, Any],
    use_mock: bool = True,
    mock_scenario: str = "low_risk"
) -> ContingentLiabilityResult:
    """
    Scan for contingent liabilities.
    
    Args:
        company_data: Company financial and legal data
        use_mock: Use mock data
        mock_scenario: Mock scenario (low_risk, medium_risk, high_risk)
        
    Returns:
        ContingentLiabilityResult with assessment
    """
    logger.info(f"🔍 Scanning contingent liabilities for {company_data.get('company_name', 'company')}")
    
    if use_mock:
        return _get_mock_contingent_data(company_data, mock_scenario)
    
    # In production: Aggregate from multiple sources
    liabilities = []
    
    # Source 1: Financial statement notes
    fs_liabilities = _extract_from_financials(company_data)
    liabilities.extend(fs_liabilities)
    
    # Source 2: Court records
    court_liabilities = await _fetch_court_records(company_data.get('cin'))
    liabilities.extend(court_liabilities)
    
    # Source 3: Tax department notices
    tax_liabilities = await _fetch_tax_disputes(company_data.get('pan'))
    liabilities.extend(tax_liabilities)
    
    # Calculate metrics and generate result
    return _analyze_contingent_liabilities(liabilities, company_data)


def _extract_from_financials(company_data: Dict[str, Any]) -> List[ContingentLiability]:
    """Extract contingent liabilities from financial statement notes."""
    # Placeholder
    return []


async def _fetch_court_records(cin: str) -> List[ContingentLiability]:
    """Fetch pending litigation from court records."""
    # Placeholder
    return []


async def _fetch_tax_disputes(pan: str) -> List[ContingentLiability]:
    """Fetch tax disputes."""
    # Placeholder
    return []


def _get_mock_contingent_data(company_data: Dict[str, Any], scenario: str) -> ContingentLiabilityResult:
    """Generate mock contingent liability data."""
    logger.info(f"🎭 Using mock contingent liability data (scenario: {scenario})")
    
    company_name = company_data.get('company_name', 'Company')
    net_worth = company_data.get('net_worth', 100_000_000)
    
    if scenario == "low_risk":
        liabilities = [
            ContingentLiability(
                category="Tax",
                description="Income Tax demand for AY 2021-22 under appeal",
                amount=2_000_000,
                probability="Low",
                status="Under Appeal at CIT(A)",
                source="Financial Statements - Note 28",
                filing_date="2022-09-15"
            ),
            ContingentLiability(
                category="Legal",
                description="Customer dispute - product quality claim",
                amount=1_500_000,
                probability="Medium",
                status="Pending at District Court",
                source="Legal Department Records",
                filing_date="2023-04-10"
            )
        ]
        
        total_amount = 3_500_000
        high_prob_amount = 1_500_000
        
    elif scenario == "medium_risk":
        liabilities = [
            ContingentLiability(
                category="Tax",
                description="GST demand with interest and penalty",
                amount=15_000_000,
                probability="Medium",
                status="Show Cause Notice received",
                source="GST Portal",
                filing_date="2023-11-20"
            ),
            ContingentLiability(
                category="Guarantee",
                description="Corporate guarantee for subsidiary company loan",
                amount=50_000_000,
                probability="Medium",
                status="Subsidiary under stress",
                source="Financial Statements - Note 30"
            ),
            ContingentLiability(
                category="Legal",
                description="Employee termination dispute",
                amount=3_000_000,
                probability="High",
                status="Labor Court proceedings",
                source="HR Department",
                filing_date="2023-08-15"
            ),
            ContingentLiability(
                category="Contractual",
                description="Penalty clause in supply contract",
                amount=8_000_000,
                probability="Low",
                status="Disputed delivery timeline",
                source="Contracts Department"
            )
        ]
        
        total_amount = 76_000_000
        high_prob_amount = 53_000_000  # High + Medium probability
        
    elif scenario == "high_risk":
        liabilities = [
            ContingentLiability(
                category="Tax",
                description="Income Tax demand - Transfer Pricing adjustment",
                amount=120_000_000,
                probability="High",
                status="ITAT proceedings",
                source="Tax Consultant Report",
                filing_date="2021-12-10"
            ),
            ContingentLiability(
                category="Tax",
                description="GST evasion proceedings",
                amount=45_000_000,
                probability="High",
                status="Under investigation",
                source="DGGI Notice",
                filing_date="2023-06-25"
            ),
            ContingentLiability(
                category="Guarantee",
                description="Corporate guarantees for 3 group companies",
                amount=200_000_000,
                probability="Medium",
                status="2 out of 3 companies defaulting",
                source="Financial Statements"
            ),
            ContingentLiability(
                category="Legal",
                description="Major customer lawsuit - breach of contract",
                amount=80_000_000,
                probability="High",
                status="High Court proceedings",
                source="Legal Notice",
                filing_date="2023-01-15"
            ),
            ContingentLiability(
                category="Environmental",
                description="Pollution Control Board penalty",
                amount=10_000_000,
                probability="Medium",
                status="Show cause notice",
                source="PCB Notice",
                filing_date="2023-10-05"
            ),
            ContingentLiability(
                category="Legal",
                description="Supplier payment disputes (multiple)",
                amount=25_000_000,
                probability="Medium",
                status="Various courts",
                source="Legal Department"
            )
        ]
        
        total_amount = 480_000_000
        high_prob_amount = 245_000_000
        
    else:
        return _get_mock_contingent_data(company_data, "low_risk")
    
    # Calculate ratio
    contingent_to_networth = (total_amount / net_worth * 100) if net_worth > 0 else 0
    
    # Generate flags
    flags = _generate_contingent_flags(
        total_amount,
        high_prob_amount,
        contingent_to_networth,
        liabilities,
        net_worth
    )
    
    # Calculate score
    score = _calculate_contingent_score(
        contingent_to_networth,
        high_prob_amount,
        liabilities
    )
    
    # Build detailed data
    data = {
        "company_name": company_name,
        "total_contingent_liabilities": total_amount,
        "high_probability_liabilities": high_prob_amount,
        "company_net_worth": net_worth,
        "contingent_to_networth_pct": contingent_to_networth,
        "liability_count": len(liabilities),
        "category_breakdown": _categorize_liabilities(liabilities),
        "liabilities_detail": [
            {
                "category": cl.category,
                "description": cl.description,
                "amount": cl.amount,
                "probability": cl.probability,
                "status": cl.status
            }
            for cl in liabilities
        ]
    }
    
    confidence = 0.75
    
    logger.info(
        f"✅ Contingent liability scan complete | Score: {score:.1f}/100 | "
        f"Total: ₹{total_amount:,.0f} | Ratio: {contingent_to_networth:.1f}%"
    )
    
    return ContingentLiabilityResult(
        score=score,
        flags=flags,
        data=data,
        confidence=confidence,
        total_contingent_amount=total_amount,
        high_probability_amount=high_prob_amount,
        contingent_to_networth_ratio=contingent_to_networth,
        liabilities=liabilities
    )


def _categorize_liabilities(liabilities: List[ContingentLiability]) -> Dict[str, float]:
    """Categorize liabilities by type."""
    categories = {}
    for cl in liabilities:
        categories[cl.category] = categories.get(cl.category, 0) + cl.amount
    return categories


def _generate_contingent_flags(
    total_amount: float,
    high_prob_amount: float,
    ratio: float,
    liabilities: List[ContingentLiability],
    net_worth: float
) -> List[str]:
    """Generate red flags based on contingent liabilities."""
    flags = []
    
    # High ratio flag
    if ratio > 50:
        flags.append(
            f"CRITICAL: Contingent liabilities (₹{total_amount:,.0f}) exceed 50% of net worth ({ratio:.1f}%)"
        )
    elif ratio > 30:
        flags.append(
            f"HIGH: Contingent liabilities at {ratio:.1f}% of net worth"
        )
    
    # High probability amount
    if high_prob_amount > net_worth * 0.3:
        flags.append(
            f"High-probability contingent liabilities (₹{high_prob_amount:,.0f}) significant"
        )
    
    # Large tax disputes
    tax_liabilities = [cl for cl in liabilities if cl.category == "Tax"]
    total_tax = sum(cl.amount for cl in tax_liabilities)
    if total_tax > 100_000_000:
        flags.append(f"Major tax disputes pending (₹{total_tax:,.0f})")
    
    # Multiple guarantees
    guarantees = [cl for cl in liabilities if cl.category == "Guarantee"]
    if len(guarantees) > 2:
        total_guarantees = sum(g.amount for g in guarantees)
        flags.append(f"{len(guarantees)} corporate guarantees outstanding (₹{total_guarantees:,.0f})")
    
    # High-value litigation
    legal_liabilities = [cl for cl in liabilities if cl.category == "Legal"]
    high_value_legal = [cl for cl in legal_liabilities if cl.amount > 50_000_000]
    if high_value_legal:
        flags.append(f"{len(high_value_legal)} high-value litigation case(s)")
    
    return flags


def _calculate_contingent_score(
    ratio: float,
    high_prob_amount: float,
    liabilities: List[ContingentLiability]
) -> float:
    """Calculate contingent liability score."""
    score = 100.0
    
    # Penalty based on ratio
    if ratio > 50:
        score -= 50
    elif ratio > 30:
        score -= 30
    elif ratio > 20:
        score -= 15
    
    # Penalty for high-probability liabilities
    if high_prob_amount > 100_000_000:
        score -= 20
    elif high_prob_amount > 50_000_000:
        score -= 15
    
    # Penalty for number of liabilities
    if len(liabilities) > 10:
        score -= 15
    elif len(liabilities) > 5:
        score -= 8
    
    return max(0, score)


def _analyze_contingent_liabilities(
    liabilities: List[ContingentLiability],
    company_data: Dict[str, Any]
) -> ContingentLiabilityResult:
    """Analyze contingent liabilities (for real data)."""
    # Implementation for real data
    pass


# ─── Integration Example ─────────────────────────────────────────────────────

async def main_example():
    """Example usage."""
    scenarios = [
        ("low_risk", 150_000_000),
        ("medium_risk", 100_000_000),
        ("high_risk", 200_000_000)
    ]
    
    for scenario, net_worth in scenarios:
        print(f"\n{'='*60}")
        print(f"Scenario: {scenario.upper()}")
        print('='*60)
        
        company_data = {
            "company_name": f"Test Company ({scenario})",
            "net_worth": net_worth
        }
        
        result = await scan_contingent_liabilities(
            company_data=company_data,
            use_mock=True,
            mock_scenario=scenario
        )
        
        print(f"Score: {result.score:.1f}/100")
        print(f"Total Contingent Liabilities: ₹{result.total_contingent_amount:,.0f}")
        print(f"High Probability Amount: ₹{result.high_probability_amount:,.0f}")
        print(f"Ratio to Net Worth: {result.contingent_to_networth_ratio:.1f}%")
        print(f"Number of Liabilities: {len(result.liabilities)}")
        
        if result.flags:
            print(f"\n🚨 Red Flags:")
            for flag in result.flags:
                print(f"  • {flag}")


if __name__ == "__main__":
    asyncio.run(main_example())
