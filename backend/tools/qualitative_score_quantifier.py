from typing import Dict, Any

async def quantify_qualitative_notes(
    credit_officer_notes: str,
    five_c_scores: Dict[str, float],
    company_name: str,
    use_llm: bool = True
) -> Dict[str, Any]:
    """
    Mock implementation for converting credit officer notes -> Five C adjustments.
    """
    return {
        "score_before": sum(five_c_scores.values()) / 5,  # simple avg for mock
        "adjustments_by_dimension": {
            dim: {"adjusted_score": score, "adjustment_reason": "No change"} 
            for dim, score in five_c_scores.items()
        }
    }
