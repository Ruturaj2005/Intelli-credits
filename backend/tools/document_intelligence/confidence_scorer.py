"""
Confidence Scorer Module
Calculates confidence scores for extracted financial data.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def calculate_confidence_scores(
    entities: Dict[str, Any],
    ocr_confidence: float,
    validation_report: Dict[str, Any],
    doc_classification: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Calculate overall confidence scores for extracted data.
    
    Factors considered:
    - OCR quality
    - Data source reliability (table vs text)
    - Validation results
    - Document classification confidence
    - Cross-checks and consistency
    
    Args:
        entities: Extracted financial entities
        ocr_confidence: Overall OCR confidence (0-1)
        validation_report: Validation results
        doc_classification: Document classification results
    
    Returns:
        Enhanced entities with confidence scores and overall assessment
    """
    # Calculate per-entity confidence scores
    scored_entities = _score_individual_entities(entities, ocr_confidence)
    
    # Calculate overall confidence
    overall_confidence = _calculate_overall_confidence(
        scored_entities,
        ocr_confidence,
        validation_report,
        doc_classification
    )
    
    # Generate confidence narrative
    narrative = _generate_confidence_narrative(
        overall_confidence,
        validation_report,
        doc_classification
    )
    
    result = {
        "entities": scored_entities,
        "overall_confidence": overall_confidence,
        "confidence_breakdown": {
            "ocr_quality": ocr_confidence,
            "data_extraction": _calculate_extraction_confidence(scored_entities),
            "validation": _calculate_validation_confidence(validation_report),
            "classification": doc_classification.get("confidence", 0.5),
        },
        "reliability_score": _calculate_reliability_score(overall_confidence, validation_report),
        "confidence_narrative": narrative,
    }
    
    logger.info(f"Overall confidence: {overall_confidence:.2%}, Reliability: {result['reliability_score']}")
    
    return result


def _score_individual_entities(
    entities: Dict[str, Any],
    ocr_confidence: float
) -> Dict[str, Any]:
    """
    Calculate confidence scores for each extracted entity.
    """
    scored = {}
    
    for key, data in entities.items():
        if not isinstance(data, dict) or "value" not in data:
            scored[key] = data
            continue
        
        # Start with base confidence from extraction method
        base_confidence = data.get("confidence", 0.5)
        source = data.get("source", "unknown")
        
        # Apply source-based weighting
        source_weight = _get_source_weight(source)
        
        # Factor in OCR quality
        ocr_factor = 0.3 * ocr_confidence + 0.7  # OCR contributes 30%
        
        # Calculate final confidence
        entity_confidence = base_confidence * source_weight * ocr_factor
        
        # Cap at 1.0
        entity_confidence = min(entity_confidence, 1.0)
        
        scored[key] = {
            **data,
            "entity_confidence": entity_confidence,
            "source_weight": source_weight,
        }
    
    return scored


def _get_source_weight(source: str) -> float:
    """
    Weight confidence based on data source reliability.
    
    Tables > OCR Grid > Text Regex
    """
    if "table" in source.lower():
        return 1.0  # Tables are most reliable
    elif "grid" in source.lower() or "ocr" in source.lower():
        return 0.85  # OCR grids are good
    elif "text" in source.lower() or "regex" in source.lower():
        return 0.7  # Text extraction is less reliable
    else:
        return 0.6  # Unknown source


def _calculate_extraction_confidence(entities: Dict[str, Any]) -> float:
    """
    Calculate average extraction confidence across all entities.
    """
    confidences = []
    
    for key, data in entities.items():
        if isinstance(data, dict) and "entity_confidence" in data:
            confidences.append(data["entity_confidence"])
    
    if not confidences:
        return 0.5
    
    return sum(confidences) / len(confidences)


def _calculate_validation_confidence(validation_report: Dict[str, Any]) -> float:
    """
    Calculate confidence based on validation results.
    
    High flag count = low confidence
    """
    flags = validation_report.get("flags", [])
    warnings = validation_report.get("warnings", [])
    
    # Start at 1.0
    confidence = 1.0
    
    # Subtract for each flag (serious issues)
    high_severity_flags = [f for f in flags if f.get("severity") == "HIGH"]
    medium_severity_flags = [f for f in flags if f.get("severity") == "MEDIUM"]
    
    confidence -= len(high_severity_flags) * 0.2
    confidence -= len(medium_severity_flags) * 0.1
    
    # Subtract for warnings (minor issues)
    confidence -= len(warnings) * 0.05
    
    # Floor at 0.0
    return max(confidence, 0.0)


def _calculate_overall_confidence(
    entities: Dict[str, Any],
    ocr_confidence: float,
    validation_report: Dict[str, Any],
    doc_classification: Dict[str, Any],
) -> float:
    """
    Calculate weighted overall confidence score.
    
    Weights:
    - OCR Quality: 25%
    - Extraction Quality: 35%
    - Validation: 30%
    - Classification: 10%
    """
    extraction_conf = _calculate_extraction_confidence(entities)
    validation_conf = _calculate_validation_confidence(validation_report)
    classification_conf = doc_classification.get("confidence", 0.5)
    
    overall = (
        0.25 * ocr_confidence +
        0.35 * extraction_conf +
        0.30 * validation_conf +
        0.10 * classification_conf
    )
    
    return overall


def _calculate_reliability_score(
    overall_confidence: float,
    validation_report: Dict[str, Any]
) -> str:
    """
    Convert confidence to reliability grade.
    
    Returns:
        Grade: EXCELLENT, GOOD, FAIR, POOR
    """
    flags = validation_report.get("flags", [])
    
    # Downgrade if critical flags present
    if any(f.get("severity") == "HIGH" for f in flags):
        return "POOR"
    
    if overall_confidence >= 0.9:
        return "EXCELLENT"
    elif overall_confidence >= 0.75:
        return "GOOD"
    elif overall_confidence >= 0.6:
        return "FAIR"
    else:
        return "POOR"


def _generate_confidence_narrative(
    overall_confidence: float,
    validation_report: Dict[str, Any],
    doc_classification: Dict[str, Any],
) -> str:
    """
    Generate human-readable confidence assessment narrative.
    """
    reliability = _calculate_reliability_score(overall_confidence, validation_report)
    doc_type = doc_classification.get("document_type", "unknown")
    
    # Base narrative
    if reliability == "EXCELLENT":
        base = f"Extracted data from {doc_type} is highly reliable with excellent confidence ({overall_confidence:.0%})."
    elif reliability == "GOOD":
        base = f"Extracted data from {doc_type} is reliable with good confidence ({overall_confidence:.0%})."
    elif reliability == "FAIR":
        base = f"Extracted data from {doc_type} has fair confidence ({overall_confidence:.0%}). Some validation concerns noted."
    else:
        base = f"Extracted data from {doc_type} has low confidence ({overall_confidence:.0%}). Significant validation issues detected."
    
    # Add context about issues
    flags = validation_report.get("flags", [])
    warnings = validation_report.get("warnings", [])
    
    issues = []
    if flags:
        high_flags = [f for f in flags if f.get("severity") == "HIGH"]
        if high_flags:
            issues.append(f"{len(high_flags)} critical issue(s)")
    
    if len(warnings) > 3:
        issues.append(f"{len(warnings)} warning(s)")
    
    if issues:
        base += " " + ", ".join(issues) + " identified."
    else:
        base += " No significant issues detected."
    
    return base


def get_entity_metadata(entity_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract comprehensive metadata for a single entity.
    
    Returns metadata for explainability.
    """
    return {
        "value": entity_data.get("value"),
        "original_value": entity_data.get("original_value"),
        "unit": entity_data.get("normalized_unit", "INR"),
        "original_unit": entity_data.get("original_unit", "units"),
        "confidence": entity_data.get("entity_confidence", 0.0),
        "source": entity_data.get("source", "unknown"),
        "source_page": entity_data.get("source", "").split("_")[-1] if "_page_" in entity_data.get("source", "") else None,
        "extraction_method": _determine_extraction_method(entity_data.get("source", "")),
        "label": entity_data.get("label", ""),
    }


def _determine_extraction_method(source: str) -> str:
    """
    Determine the extraction method from source string.
    """
    if "table" in source.lower():
        return "Table Extraction"
    elif "text" in source.lower() or "regex" in source.lower():
        return "Text Pattern Matching"
    elif "ocr" in source.lower():
        return "OCR Layout Analysis"
    else:
        return "Unknown"


def generate_extraction_report(confidence_result: Dict[str, Any]) -> str:
    """
    Generate a detailed extraction quality report.
    """
    overall = confidence_result["overall_confidence"]
    reliability = confidence_result["reliability_score"]
    breakdown = confidence_result["confidence_breakdown"]
    
    report = f"""
=== DOCUMENT INTELLIGENCE - EXTRACTION REPORT ===

Overall Confidence: {overall:.1%}
Reliability Grade: {reliability}

Confidence Breakdown:
  - OCR Quality:        {breakdown['ocr_quality']:.1%}
  - Data Extraction:    {breakdown['data_extraction']:.1%}
  - Validation:         {breakdown['validation']:.1%}
  - Classification:     {breakdown['classification']:.1%}

Assessment:
{confidence_result['confidence_narrative']}

Extracted Entities: {len(confidence_result['entities'])}
"""
    
    return report.strip()
