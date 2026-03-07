"""
Promoter Background Checker — Promoter Due Diligence Module

Evaluates promoter credibility and track record:
1. Past business history
2. Failed/defaulted companies
3. Personal net worth verification
4. Personal credit score (CIBIL)
5. Litigation history (criminal, civil, regulatory)
6. Personal guarantees given
7. Directorship in other companies
8. Industry experience and expertise

Red Flag Rules:
- Promoter linked to >2 defaulted firms → RF029 (Auto-escalate)
- Criminal proceedings → Critical flag
- Personal CIBIL <650 → High risk
- Serial entrepreneur with multiple failures → Red flag
- Undisclosed directorships → Transparency issue

Purpose:
Banks lend to people, not just companies. Promoter integrity
and capability are critical for credit decisions.

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
class Promoter:
    """Promoter/Director details."""
    name: str
    pan: str
    din: Optional[str] = None
    age: int = 0
    qualification: str = ""
    experience_years: int = 0
    
    # Credit
    personal_cibil_score: int = 0
    personal_net_worth: float = 0.0
    
    # Track record
    current_directorships: int = 0
    past_directorships: int = 0
    successful_ventures: int = 0
    failed_ventures: int = 0
    defaulted_ventures: int = 0
    
    # Legal
    criminal_cases: int = 0
    civil_cases: int = 0
    regulatory_actions: int = 0
    
    # Guarantees
    personal_guarantees_given: List[Dict[str, Any]] = field(default_factory=list)
    total_guarantee_exposure: float = 0.0


@dataclass
class PromoterBackgroundResult:
    """Result from promoter background check."""
    score: float  # 0-100
    flags: List[str]
    data: Dict[str, Any]
    confidence: float
    
    promoters: List[Promoter] = field(default_factory=list)
    overall_integrity_score: float = 0.0
    overall_capability_score: float = 0.0


async def check_promoter_background(
    promoters_data: List[Dict[str, Any]],
    use_mock: bool = True
) -> PromoterBackgroundResult:
    """
    Check promoter background and track record.
    
    Args:
        promoters_data: List of promoter details
        use_mock: Use mock data for demonstration
        
    Returns:
        PromoterBackgroundResult with assessment
    """
    logger.info(f"👤 Checking background of {len(promoters_data)} promoter(s)")
    
    # Parse and enrich promoter data
    promoters = []
    for p_data in promoters_data:
        promoter = _parse_promoter(p_data)
        
        # Enrich with external data (mock or real)
        promoter = await _enrich_promoter_data(promoter, use_mock)
        
        promoters.append(promoter)
    
    # Calculate integrity score
    integrity_score = _calculate_integrity_score(promoters)
    
    # Calculate capability score
    capability_score = _calculate_capability_score(promoters)
    
    # Generate flags
    flags = _generate_promoter_flags(promoters)
    
    # Calculate overall score
    score = (integrity_score + capability_score) / 2
    
    # Build detailed data
    data = {
        "total_promoters": len(promoters),
        "overall_integrity_score": integrity_score,
        "overall_capability_score": capability_score,
        "promoters_summary": [
            {
                "name": p.name,
                "pan": p.pan,
                "cibil_score": p.personal_cibil_score,
                "net_worth": p.personal_net_worth,
                "experience_years": p.experience_years,
                "current_directorships": p.current_directorships,
                "failed_ventures": p.failed_ventures,
                "defaulted_ventures": p.defaulted_ventures,
                "criminal_cases": p.criminal_cases,
                "total_guarantee_exposure": p.total_guarantee_exposure
            }
            for p in promoters
        ]
    }
    
    confidence = 0.85
    
    logger.info(
        f"✅ Promoter check complete | Score: {score:.1f}/100 | "
        f"Integrity: {integrity_score:.1f} | Capability: {capability_score:.1f}"
    )
    
    return PromoterBackgroundResult(
        score=score,
        flags=flags,
        data=data,
        confidence=confidence,
        promoters=promoters,
        overall_integrity_score=integrity_score,
        overall_capability_score=capability_score
    )


def _parse_promoter(data: Dict[str, Any]) -> Promoter:
    """Parse promoter data."""
    return Promoter(
        name=data['name'],
        pan=data.get('pan', ''),
        din=data.get('din'),
        age=data.get('age', 0),
        qualification=data.get('qualification', ''),
        experience_years=data.get('experience_years', 0),
        personal_cibil_score=data.get('cibil_score', 0),
        personal_net_worth=float(data.get('net_worth', 0)),
        current_directorships=data.get('current_directorships', 0),
        past_directorships=data.get('past_directorships', 0),
        successful_ventures=data.get('successful_ventures', 0),
        failed_ventures=data.get('failed_ventures', 0),
        defaulted_ventures=data.get('defaulted_ventures', 0),
        criminal_cases=data.get('criminal_cases', 0),
        civil_cases=data.get('civil_cases', 0),
        regulatory_actions=data.get('regulatory_actions', 0),
        total_guarantee_exposure=float(data.get('total_guarantee_exposure', 0))
    )


async def _enrich_promoter_data(promoter: Promoter, use_mock: bool) -> Promoter:
    """
    Enrich promoter data from external sources.
    
    In production, would fetch from:
    - MCA portal (directorships)
    - Court databases (litigation)
    - CIBIL (personal credit)
    - Income tax records
    """
    if use_mock:
        # Add mock enrichment
        import random
        
        if not promoter.personal_cibil_score:
            promoter.personal_cibil_score = random.randint(650, 800)
        
        if not promoter.current_directorships:
            promoter.current_directorships = random.randint(1, 5)
        
        # Check if mock scenario should flag issues
        if "default" in promoter.name.lower():
            promoter.defaulted_ventures = 3
            promoter.personal_cibil_score = 580
        
        if "fraud" in promoter.name.lower():
            promoter.criminal_cases = 2
    
    return promoter


def _calculate_integrity_score(promoters: List[Promoter]) -> float:
    """
    Calculate integrity score based on:
    - Past defaults
    - Litigation
    - Transparency
    """
    scores = []
    
    for p in promoters:
        score = 100.0
        
        # Defaulted ventures (critical)
        if p.defaulted_ventures > 2:
            score -= 50  # RF029
        elif p.defaulted_ventures > 0:
            score -= p.defaulted_ventures * 15
        
        # Criminal cases (critical)
        if p.criminal_cases > 0:
            score -= 40
        
        # Regulatory actions
        score -= p.regulatory_actions * 10
        
        # Civil litigation
        score -= min(p.civil_cases * 5, 20)
        
        # CIBIL score
        if p.personal_cibil_score < 650:
            score -= 25
        elif p.personal_cibil_score < 700:
            score -= 10
        
        scores.append(max(0, score))
    
    return sum(scores) / len(scores) if scores else 0


def _calculate_capability_score(promoters: List[Promoter]) -> float:
    """
    Calculate capability score based on:
    - Experience
    - Track record of success
    - Net worth
    - Industry expertise
    """
    scores = []
    
    for p in promoters:
        score = 50.0  # Base score
        
        # Experience bonus
        if p.experience_years > 20:
            score += 20
        elif p.experience_years > 10:
            score += 15
        elif p.experience_years > 5:
            score += 10
        
        # Successful ventures bonus
        if p.successful_ventures > 3:
            score += 15
        elif p.successful_ventures > 1:
            score += 10
        
        # Failed ventures penalty
        if p.failed_ventures > 3:
            score -= 20
        elif p.failed_ventures > 1:
            score -= 10
        
        # Net worth bonus
        if p.personal_net_worth > 50_000_000:
            score += 15
        elif p.personal_net_worth > 10_000_000:
            score += 10
        elif p.personal_net_worth < 1_000_000:
            score -= 10
        
        scores.append(max(0, min(100, score)))
    
    return sum(scores) / len(scores) if scores else 0


def _generate_promoter_flags(promoters: List[Promoter]) -> List[str]:
    """Generate red flags based on promoter background."""
    flags = []
    
    for p in promoters:
        # RF029: Multiple defaults
        if p.defaulted_ventures > 2:
            flags.append(
                f"RF029: {p.name} linked to {p.defaulted_ventures} defaulted companies - "
                f"High integrity risk"
            )
        
        # Criminal cases
        if p.criminal_cases > 0:
            flags.append(
                f"CRITICAL: {p.name} has {p.criminal_cases} criminal case(s) pending/recorded"
            )
        
        # Low personal CIBIL
        if p.personal_cibil_score < 650:
            flags.append(
                f"{p.name} personal CIBIL score {p.personal_cibil_score} below threshold (650)"
            )
        
        # Regulatory actions
        if p.regulatory_actions > 0:
            flags.append(
                f"{p.name} subject to {p.regulatory_actions} regulatory action(s)"
            )
        
        # High guarantee exposure
        if p.total_guarantee_exposure > p.personal_net_worth * 2:
            flags.append(
                f"{p.name} guarantee exposure (₹{p.total_guarantee_exposure:,.0f}) "
                f"exceeds 2x personal net worth"
            )
        
        # Serial failures
        if p.failed_ventures > 3:
            flags.append(
                f"{p.name} has {p.failed_ventures} failed ventures - track record concern"
            )
    
    return flags


# ─── Integration Example ─────────────────────────────────────────────────────

async def main_example():
    """Example usage of promoter background checker."""
    
    # Scenario 1: Strong promoter
    promoters1 = [
        {
            "name": "Rajesh Kumar",
            "pan": "ABCDE1234F",
            "din": "01234567",
            "age": 52,
            "qualification": "MBA, B.Tech",
            "experience_years": 25,
            "cibil_score": 780,
            "net_worth": 75_000_000,
            "current_directorships": 3,
            "successful_ventures": 2,
            "failed_ventures": 0,
            "defaulted_ventures": 0,
            "criminal_cases": 0,
            "civil_cases": 1,
            "regulatory_actions": 0
        }
    ]
    
    print("="*70)
    print("SCENARIO 1: Strong Promoter")
    print("="*70)
    
    result1 = await check_promoter_background(promoters1, use_mock=True)
    
    print(f"Score: {result1.score:.1f}/100")
    print(f"Integrity Score: {result1.overall_integrity_score:.1f}/100")
    print(f"Capability Score: {result1.overall_capability_score:.1f}/100")
    print(f"Flags: {len(result1.flags)}")
    if result1.flags:
        for flag in result1.flags:
            print(f"  ⚠️  {flag}")
    
    # Scenario 2: Risky promoter
    promoters2 = [
        {
            "name": "Vikram Default",
            "pan": "XYZAB9876C",
            "din": "09876543",
            "age": 45,
            "qualification": "B.Com",
            "experience_years": 15,
            "cibil_score": 590,
            "net_worth": 5_000_000,
            "current_directorships": 7,
            "successful_ventures": 1,
            "failed_ventures": 4,
            "defaulted_ventures": 3,  # RF029!
            "criminal_cases": 0,
            "civil_cases": 5,
            "regulatory_actions": 1
        }
    ]
    
    print("\n" + "="*70)
    print("SCENARIO 2: High-Risk Promoter")
    print("="*70)
    
    result2 = await check_promoter_background(promoters2, use_mock=True)
    
    print(f"Score: {result2.score:.1f}/100")
    print(f"Integrity Score: {result2.overall_integrity_score:.1f}/100")
    print(f"Capability Score: {result2.overall_capability_score:.1f}/100")
    
    if result2.flags:
        print(f"\n🚨 Red Flags:")
        for flag in result2.flags:
            print(f"  • {flag}")


if __name__ == "__main__":
    asyncio.run(main_example())
