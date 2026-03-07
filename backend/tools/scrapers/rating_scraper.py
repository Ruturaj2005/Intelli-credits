"""
Credit Rating Aggregator — Rating Agency Data Collector

Aggregates credit ratings from major Indian rating agencies:
- CRISIL (Credit Rating Information Services of India Limited)
- ICRA (Investment Information and Credit Rating Agency)
- CARE (Credit Analysis & Research Limited)
- India Ratings (Fitch Group)
- Brickwork Ratings

Rating Scale Mapping to Score:
AAA → 100 (Highest safety)
AA+ → 92, AA → 85, AA- → 80
A+ → 75, A → 70, A- → 65
BBB+ → 60, BBB → 55, BBB- → 50
BB+ → 45, BB → 40, BB- → 35
B+ → 30, B → 25, B- → 20
C+ → 15, C → 10
D → 0 (Default)

Author: Credit Intelligence System
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# Rating to score mapping
RATING_SCORE_MAP = {
    "AAA": 100, "AA+": 92, "AA": 85, "AA-": 80,
    "A+": 75, "A": 70, "A-": 65,
    "BBB+": 60, "BBB": 55, "BBB-": 50,
    "BB+": 45, "BB": 40, "BB-": 35,
    "B+": 30, "B": 25, "B-": 20,
    "C+": 15, "C": 10, "D": 0
}


@dataclass
class Rating:
    """Credit rating from an agency."""
    agency: str
    rating: str
    rating_date: str
    outlook: str = "Stable"  # Positive, Stable, Negative
    rating_action: str = "Assigned"  # Assigned, Reaffirmed, Upgraded, Downgraded
    instrument_type: str = "Long Term"


@dataclass
class RatingResult:
    """Result from rating aggregator."""
    data: Optional[Dict[str, Any]]
    error: Optional[str] = None
    source: str = "rating_agencies"
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    is_mock: bool = False


async def aggregate_credit_ratings(
    company_name: str,
    cin: str,
    use_mock: bool = True,
    mock_scenario: str = "investment_grade"
) -> RatingResult:
    """
    Aggregate credit ratings from multiple agencies.
    
    Args:
        company_name: Company name
        cin: Corporate Identification Number
        use_mock: Use mock data
        mock_scenario: Mock scenario (investment_grade, speculative, default)
        
    Returns:
        RatingResult with aggregated ratings
    """
    logger.info(f"⭐ Aggregating credit ratings for {company_name}")
    
    if use_mock:
        await asyncio.sleep(1.5)  # Simulate API delay
        return _get_mock_ratings(company_name, cin, mock_scenario)
    
    # In production: Fetch from actual rating agency APIs/websites
    ratings = []
    
    try:
        # Fetch from CRISIL
        crisil_rating = await _fetch_crisil_rating(company_name, cin)
        if crisil_rating:
            ratings.append(crisil_rating)
    except Exception as e:
        logger.error(f"CRISIL fetch failed: {e}")
    
    try:
        # Fetch from ICRA
        icra_rating = await _fetch_icra_rating(company_name, cin)
        if icra_rating:
            ratings.append(icra_rating)
    except Exception as e:
        logger.error(f"ICRA fetch failed: {e}")
    
    try:
        # Fetch from CARE
        care_rating = await _fetch_care_rating(company_name, cin)
        if care_rating:
            ratings.append(care_rating)
    except Exception as e:
        logger.error(f"CARE fetch failed: {e}")
    
    if not ratings:
        return _get_mock_ratings(company_name, cin, "unrated")
    
    # Aggregate results
    data = _aggregate_ratings(ratings)
    
    return RatingResult(data=data, is_mock=False)


async def _fetch_crisil_rating(company_name: str, cin: str) -> Optional[Rating]:
    """Fetch rating from CRISIL (placeholder)."""
    # Placeholder - would implement actual web scraping or API call
    return None


async def _fetch_icra_rating(company_name: str, cin: str) -> Optional[Rating]:
    """Fetch rating from ICRA (placeholder)."""
    return None


async def _fetch_care_rating(company_name: str, cin: str) -> Optional[Rating]:
    """Fetch rating from CARE (placeholder)."""
    return None


def _get_mock_ratings(company_name: str, cin: str, scenario: str) -> RatingResult:
    """Generate mock rating data."""
    logger.info(f"🎭 Using mock rating data (scenario: {scenario})")
    
    if scenario == "investment_grade":
        ratings = [
            {
                "agency": "CRISIL",
                "rating": "A",
                "rating_date": "2024-01-15",
                "outlook": "Stable",
                "rating_action": "Reaffirmed",
                "instrument_type": "Long Term Bank Facilities"
            },
            {
                "agency": "ICRA",
                "rating": "A-",
                "rating_date": "2023-11-20",
                "outlook": "Stable",
                "rating_action": "Assigned",
                "instrument_type": "Long Term"
            }
        ]
        composite_rating = "A-"
        composite_score = 65
        
    elif scenario == "speculative":
        ratings = [
            {
                "agency": "CARE",
                "rating": "BB",
                "rating_date": "2024-02-10",
                "outlook": "Negative",
                "rating_action": "Downgraded",
                "instrument_type": "Long Term"
            },
            {
                "agency": "Brickwork",
                "rating": "BB-",
                "rating_date": "2023-12-05",
                "outlook": "Negative",
                "rating_action": "Reaffirmed",
                "instrument_type": "Bank Loan"
            }
        ]
        composite_rating = "BB"
        composite_score = 40
        
    elif scenario == "default":
        ratings = [
            {
                "agency": "CRISIL",
                "rating": "D",
                "rating_date": "2024-03-01",
                "outlook": "N/A",
                "rating_action": "Downgraded",
                "instrument_type": "Long Term"
            }
        ]
        composite_rating = "D"
        composite_score = 0
        
    elif scenario == "high_grade":
        ratings = [
            {
                "agency": "CRISIL",
                "rating": "AA",
                "rating_date": "2024-01-10",
                "outlook": "Positive",
                "rating_action": "Upgraded",
                "instrument_type": "Long Term"
            },
            {
                "agency": "ICRA",
                "rating": "AA-",
                "rating_date": "2023-12-15",
                "outlook": "Stable",
                "rating_action": "Reaffirmed",
                "instrument_type": "Long Term"
            },
            {
                "agency": "CARE",
                "rating": "AA",
                "rating_date": "2024-02-20",
                "outlook": "Stable",
                "rating_action": "Assigned",
                "instrument_type": "Bank Facilities"
            }
        ]
        composite_rating = "AA"
        composite_score = 85
        
    else:  # unrated
        ratings = []
        composite_rating = "Unrated"
        composite_score = 50  # Neutral
    
    data = {
        "company_name": company_name,
        "cin": cin,
        "is_rated": len(ratings) > 0,
        "ratings": ratings,
        "composite_rating": composite_rating,
        "composite_score": composite_score,
        "rating_count": len(ratings),
        "latest_rating_date": ratings[0]["rating_date"] if ratings else None,
        "has_negative_outlook": any(r["outlook"] == "Negative" for r in ratings),
        "recent_downgrade": any(r["rating_action"] == "Downgraded" for r in ratings)
    }
    
    return RatingResult(data=data, is_mock=True)


def _aggregate_ratings(ratings: List[Rating]) -> Dict[str, Any]:
    """Aggregate ratings from multiple agencies into composite view."""
    if not ratings:
        return {
            "is_rated": False,
            "ratings": [],
            "composite_rating": "Unrated",
            "composite_score": 50
        }
    
    # Convert ratings to scores
    scores = []
    for rating in ratings:
        score = RATING_SCORE_MAP.get(rating.rating, 50)
        scores.append(score)
    
    # Calculate composite score (weighted average)
    composite_score = sum(scores) / len(scores)
    
    # Determine composite rating
    composite_rating = _score_to_rating(composite_score)
    
    return {
        "is_rated": True,
        "ratings": [
            {
                "agency": r.agency,
                "rating": r.rating,
                "rating_date": r.rating_date,
                "outlook": r.outlook,
                "rating_action": r.rating_action
            }
            for r in ratings
        ],
        "composite_rating": composite_rating,
        "composite_score": composite_score,
        "rating_count": len(ratings),
        "latest_rating_date": max(r.rating_date for r in ratings),
        "has_negative_outlook": any(r.outlook == "Negative" for r in ratings),
        "recent_downgrade": any(r.rating_action == "Downgraded" for r in ratings)
    }


def _score_to_rating(score: float) -> str:
    """Convert numeric score back to rating category."""
    if score >= 92:
        return "AA+"
    elif score >= 85:
        return "AA"
    elif score >= 75:
        return "A+"
    elif score >= 70:
        return "A"
    elif score >= 60: 
        return "BBB+"
    elif score >= 55:
        return "BBB"
    elif score >= 45:
        return "BB+"
    elif score >= 40:
        return "BB"
    elif score >= 30:
        return "B+"
    elif score >= 25:
        return "B"
    elif score >= 10:
        return "C"
    else:
        return "D"


# ─── Integration Example ─────────────────────────────────────────────────────

async def main_example():
    """Example usage."""
    scenarios = [
        ("high_grade", "Blue Chip Corp Ltd"),
        ("investment_grade", "Stable Industries Pvt Ltd"),
        ("speculative", "Risky Ventures Ltd"),
        ("default", "Defaulted Company Ltd")
    ]
    
    for scenario, company in scenarios:
        print(f"\n{'='*60}")
        print(f"Scenario: {scenario.upper()}")
        print(f"Company: {company}")
        print('='*60)
        
        result = await aggregate_credit_ratings(
            company_name=company,
            cin=f"U12345DL2015PTC{scenario[:6].upper()}",
            use_mock=True,
            mock_scenario=scenario
        )
        
        if result.data:
            print(f"Composite Rating: {result.data['composite_rating']}")
            print(f"Composite Score: {result.data['composite_score']:.0f}/100")
            print(f"Number of Ratings: {result.data['rating_count']}")
            print(f"Negative Outlook: {result.data.get('has_negative_outlook', False)}")
            
            if result.data['ratings']:
                print("\nDetailed Ratings:")
                for rating in result.data['ratings']:
                    print(f"  {rating['agency']}: {rating['rating']} ({rating['outlook']}) - {rating['rating_action']}")


if __name__ == "__main__":
    asyncio.run(main_example())
