"""
Qualitative Scorer — Primary Due Diligence Assessment for Indian Corporate Lending

This module scores qualitative inputs from:
- Factory and Site Visit observations
- Management Interview assessments
- Sentiment analysis of text narratives

Author: Credit Intelligence System v3.0
Date: March 2026
"""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, Optional

import google.generativeai as genai

logger = logging.getLogger(__name__)

# ─── Scoring Weights ──────────────────────────────────────────────────────────

QUALITATIVE_SCORE_WEIGHTS = {
    "factory_visit": {
        "overall_weight": 0.50,
        "sub_weights": {
            "capacity_utilization": 0.25,
            "asset_condition": 0.20,
            "workforce_observations": 0.20,
            "inventory_levels": 0.10,
            "environmental_compliance": 0.10,
            "collateral_verification": 0.10,
            "overall_impression": 0.05
        }
    },
    "management_interview": {
        "overall_weight": 0.50,
        "sub_weights": {
            "promoter_experience": 0.20,
            "second_line_management": 0.15,
            "transparency": 0.20,
            "business_vision": 0.15,
            "order_book_visibility": 0.15,
            "promoter_contribution": 0.10,
            "related_party_concerns": 0.05
        }
    }
}

# ─── Field Scoring Maps ───────────────────────────────────────────────────────

FIELD_SCORES = {
    # Capacity Utilization
    "capacity_utilization": {
        "above_80": 100,
        "60_to_80": 80,
        "40_to_60": 55,
        "20_to_40": 25,
        "below_20": 0
    },
    # Asset Condition
    "asset_condition": {
        "excellent": 100,
        "good": 75,
        "average": 40,
        "poor": 10
    },
    # Workforce Observations
    "workforce_observations": {
        "full_active": 100,
        "partial": 65,
        "skeleton": 25,
        "unrest": 0
    },
    # Inventory Levels
    "inventory_levels": {
        "normal": 100,
        "high": 40,
        "low": 40,
        "none": 70
    },
    # Environmental Compliance
    "environmental_compliance": {
        "all_valid": 100,
        "minor_gaps": 60,
        "significant_issues": 20,
        "non_compliant": 0
    },
    # Collateral Verification
    "collateral_verification": {
        "verified": 100,
        "minor_discrepancy": 60,
        "significant_discrepancy": 10,
        "not_accessible": 0
    },
    # Overall Impression
    "overall_impression": {
        "positive": 100,
        "neutral": 60,
        "negative": 20,
        "highly_negative": 0
    },
    # Promoter Experience
    "promoter_experience": {
        "more_than_15": 100,
        "10_to_15": 80,
        "5_to_10": 55,
        "less_than_5": 25
    },
    # Second Line Management
    "second_line_management": {
        "strong": 100,
        "adequate": 75,
        "promoter_dependent": 40,
        "single_person": 10
    },
    # Transparency
    "transparency": {
        "very_transparent": 100,
        "mostly_transparent": 70,
        "somewhat_evasive": 25,
        "not_cooperative": 0
    },
    # Business Vision
    "business_vision": {
        "clear": 100,
        "reasonable": 70,
        "vague": 35,
        "no_direction": 0
    },
    # Order Book Visibility
    "order_book_visibility": {
        "strong": 100,
        "moderate": 70,
        "limited": 35,
        "none": 0
    },
    # Promoter Contribution
    "promoter_contribution": {
        "more_than_33": 100,
        "25_to_33": 75,
        "less_than_25": 30,
        "none": 0
    },
    # Related Party Concerns
    "related_party_concerns": {
        "none": 100,
        "minor": 70,
        "significant": 30,
        "undisclosed": 0
    }
}


# ─── Main Scoring Functions ───────────────────────────────────────────────────

def calculate_factory_score(factory_inputs: Dict[str, Any], sector: str) -> Dict[str, Any]:
    """
    Calculate factory visit score based on qualitative inputs.
    """
    weights = QUALITATIVE_SCORE_WEIGHTS["factory_visit"]["sub_weights"]
    scores = {}
    total_weight = 0
    weighted_sum = 0
    
    # Score each field
    for field, weight in weights.items():
        value = factory_inputs.get(field, "")
        if value and field in FIELD_SCORES:
            score = FIELD_SCORES[field].get(value, 50)
            scores[field] = {
                "value": value,
                "score": score,
                "weight": weight
            }
            weighted_sum += score * weight
            total_weight += weight
        else:
            # Skip fields not applicable to this sector
            if not _is_field_applicable(field, sector):
                continue
            # Assign neutral score if field is empty but applicable
            scores[field] = {
                "value": None,
                "score": 50,
                "weight": weight
            }
            weighted_sum += 50 * weight
            total_weight += weight
    
    # Normalize to 0-100
    final_score = (weighted_sum / total_weight) if total_weight > 0 else 50
    
    return {
        "total": round(final_score, 2),
        "scores": scores,
        "note": None
    }


def calculate_management_score(management_inputs: Dict[str, Any], sector: str) -> Dict[str, Any]:
    """
    Calculate management interview score based on qualitative inputs.
    """
    weights = QUALITATIVE_SCORE_WEIGHTS["management_interview"]["sub_weights"]
    scores = {}
    total_weight = 0
    weighted_sum = 0
    
    # Score each field
    for field, weight in weights.items():
        value = management_inputs.get(field, "")
        if value and field in FIELD_SCORES:
            score = FIELD_SCORES[field].get(value, 50)
            scores[field] = {
                "value": value,
                "score": score,
                "weight": weight
            }
            weighted_sum += score * weight
            total_weight += weight
        else:
            # Skip fields not applicable to this sector
            if not _is_field_applicable(field, sector):
                continue
            # Assign neutral score if field is empty but applicable
            scores[field] = {
                "value": None,
                "score": 50,
                "weight": weight
            }
            weighted_sum += 50 * weight
            total_weight += weight
    
    # Normalize to 0-100
    final_score = (weighted_sum / total_weight) if total_weight > 0 else 50
    
    return {
        "total": round(final_score, 2),
        "scores": scores,
        "note": None
    }


def _is_field_applicable(field: str, sector: str) -> bool:
    """
    Check if a field is applicable to the given sector.
    """
    # Capacity utilization
    if field == "capacity_utilization":
        return sector in ['Manufacturing', 'Infrastructure', 'Healthcare', 'Agriculture', 'Hospitality']
    
    # Inventory levels
    if field == "inventory_levels":
        return sector in ['Manufacturing', 'Trading', 'Agriculture', 'Healthcare']
    
    # Environmental compliance
    if field == "environmental_compliance":
        return sector in ['Manufacturing', 'Agriculture', 'Healthcare', 'Infrastructure', 'Hospitality']
    
    # Order book visibility
    if field == "order_book_visibility":
        return sector in ['Manufacturing', 'Real Estate', 'Infrastructure', 'Healthcare', 'Agriculture', 'Hospitality']
    
    # All other fields applicable to all sectors
    return True


def analyze_qualitative_text(
    site_observations: str,
    key_positives: str,
    key_concerns: str,
    gemini_api_key: str
) -> Dict[str, Any]:
    """
    Analyze free-text qualitative observations using Gemini to extract signals
    and calculate score adjustment.
    """
    if not any([site_observations, key_positives, key_concerns]):
        return {
            "score_adjustment": 0,
            "positive_signals": [],
            "negative_signals": [],
            "red_flags": [],
            "summary": "No qualitative text provided for analysis"
        }

    try:
        genai.configure(api_key=gemini_api_key)
        model = genai.GenerativeModel('gemini-2.0-flash')
        
        prompt = f"""
You are a senior Indian bank credit officer analyzing qualitative observations 
from a corporate site visit and management interview.

Site Visit Observations: {site_observations}
Key Positives from Interview: {key_positives}
Key Concerns from Interview: {key_concerns}

Analyze these inputs and return ONLY a valid JSON object with this exact structure:
{{
    "score_adjustment": <integer between -15 and +15>,
    "positive_signals": [<list of positive signals found>],
    "negative_signals": [<list of negative signals found>],
    "red_flags": [<list of serious concerns if any>],
    "summary": "<2-3 line summary of qualitative assessment>"
}}

Score adjustment rules:
+10 to +15 for very strong positive signals
+5 to +10 for moderately positive signals
0 for neutral observations
-5 to -10 for moderate concerns
-10 to -15 for serious red flags

Indian context to watch for:
NEGATIVE SIGNALS:
- Capacity utilization below 40 percent is serious concern
- Labour unrest signals in India often precede defaults
- Related party transaction mentions are red flags
- Promoter evasiveness on group company questions is red flag
- High inventory buildup suggests demand issues
- Multiple production lines idle suggests order book problems

POSITIVE SIGNALS:
- Long standing customer relationships mentioned
- Export orders mentioned shows demand strength
- Recent capex shows growth confidence
- Strong order pipeline visibility
- Experienced management team
- Transparent financial disclosures

Return ONLY valid JSON, no markdown formatting, no extra text.
"""
        
        response = model.generate_content(prompt)
        result_text = response.text.strip()
        
        # Clean up markdown formatting if present
        if result_text.startswith('```json'):
            result_text = result_text[7:]
        if result_text.startswith('```'):
            result_text = result_text[3:]
        if result_text.endswith('```'):
            result_text = result_text[:-3]
        result_text = result_text.strip()
        
        result = json.loads(result_text)
        
        # Validate score_adjustment is within bounds
        if not isinstance(result.get("score_adjustment"), (int, float)):
            result["score_adjustment"] = 0
        else:
            result["score_adjustment"] = max(-15, min(15, int(result["score_adjustment"])))
        
        return result
        
    except Exception as e:
        logger.error(f"Error analyzing qualitative text with Gemini: {e}")
        return {
            "score_adjustment": 0,
            "positive_signals": [],
            "negative_signals": [],
            "red_flags": [],
            "summary": f"Text analysis failed: {str(e)}"
        }


def calculate_qualitative_score(
    factory_inputs: Dict[str, Any],
    management_inputs: Dict[str, Any],
    sector: str,
    gemini_api_key: str
) -> Dict[str, Any]:
    """
    Main function to calculate comprehensive qualitative score.
    Combines factory visit and management interview scores with text analysis.
    """
    factory_score = calculate_factory_score(factory_inputs, sector)
    management_score = calculate_management_score(management_inputs, sector)
    
    # Check if visits were conducted
    if factory_inputs.get("visit_conducted") in ["no", "not_applicable"]:
        factory_score["total"] = 50
        factory_score["note"] = "Site visit not conducted - neutral score applied"
    
    if management_inputs.get("interview_conducted") == "no":
        management_score["total"] = 50
        management_score["note"] = "Interview not conducted - neutral score applied"
    
    # Combined score
    combined_score = (
        factory_score["total"] * 0.50 +
        management_score["total"] * 0.50
    )
    
    # Analyze text narratives
    text_analysis = analyze_qualitative_text(
        factory_inputs.get("specific_observations", ""),
        management_inputs.get("key_positives", ""),
        management_inputs.get("key_concerns", ""),
        gemini_api_key
    )
    
    # Apply text adjustment
    text_adjustment = text_analysis.get("score_adjustment", 0)
    final_score = min(100, max(0, combined_score + text_adjustment))
    
    return {
        "qualitative_score": round(final_score, 2),
        "factory_score": factory_score,
        "management_score": management_score,
        "text_analysis": text_analysis,
        "text_adjustment_applied": text_adjustment,
        "visit_conducted": factory_inputs.get("visit_conducted") == "yes",
        "interview_conducted": management_inputs.get("interview_conducted") == "yes",
        "flag": (
            "GREEN" if final_score >= 70
            else "AMBER" if final_score >= 45
            else "RED"
        ),
        "five_c_mapping": "Character and Conditions",
        "rbi_basis": (
            "RBI Master Direction on Credit Risk Management requires qualitative assessment "
            "including site visit and management evaluation as part of comprehensive credit appraisal. "
            "Site visit mandatory for loans above ₹25 lakh as per bank policy aligned with RBI guidelines."
        )
    }


# ─── Testing ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Test factory scoring
    test_factory = {
        "visit_conducted": "yes",
        "capacity_utilization": "60_to_80",
        "asset_condition": "good",
        "workforce_observations": "full_active",
        "inventory_levels": "normal",
        "environmental_compliance": "all_valid",
        "collateral_verification": "verified",
        "overall_impression": "positive",
        "specific_observations": "All production lines operational. Good housekeeping observed. Workers appeared motivated."
    }
    
    test_management = {
        "interview_conducted": "yes",
        "promoter_experience": "10_to_15",
        "second_line_management": "adequate",
        "transparency": "very_transparent",
        "business_vision": "clear",
        "order_book_visibility": "strong",
        "promoter_contribution": "more_than_33",
        "related_party_concerns": "none",
        "key_positives": "Strong export order book. Recent capex in automation.",
        "key_concerns": "None significant observed."
    }
    
    # Note: You need to set GEMINI_API_KEY environment variable for testing
    import os
    api_key = os.environ.get("GEMINI_API_KEY", "")
    
    if api_key:
        result = calculate_qualitative_score(
            test_factory,
            test_management,
            "Manufacturing",
            api_key
        )
        print(json.dumps(result, indent=2))
    else:
        print("Set GEMINI_API_KEY environment variable to test fully.")
        # Test without Gemini
        factory_score = calculate_factory_score(test_factory, "Manufacturing")
        management_score = calculate_management_score(test_management, "Manufacturing")
        print(f"Factory Score: {factory_score['total']}")
        print(f"Management Score: {management_score['total']}")
