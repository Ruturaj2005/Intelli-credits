"""
Unit Normalizer Module
Normalizes financial values from various units (lakh, crore, million) to standard INR.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


# Unit conversion factors to INR
UNIT_MULTIPLIERS = {
    "crore": 10_000_000,
    "crores": 10_000_000,
    "cr": 10_000_000,
    "lakh": 100_000,
    "lakhs": 100_000,
    "lac": 100_000,
    "million": 1_000_000,
    "mn": 1_000_000,
    "billion": 1_000_000_000,
    "bn": 1_000_000_000,
    "thousand": 1_000,
    "k": 1_000,
    "units": 1,
    "": 1,
}


def normalize_financial_values(
    entities: Dict[str, Any],
    detected_unit: str = "units"
) -> Dict[str, Any]:
    """
    Normalize all financial values to standard INR units.
    
    Args:
        entities: Dictionary of financial entities with values
        detected_unit: Unit detected in document (crore, lakh, etc.)
    
    Returns:
        Normalized entities dictionary with values in INR
    """
    normalized = {}
    
    # Get multiplier for detected unit
    multiplier = UNIT_MULTIPLIERS.get(detected_unit.lower(), 1)
    
    logger.info(f"Normalizing values with unit '{detected_unit}' (multiplier: {multiplier})")
    
    for key, value_data in entities.items():
        if isinstance(value_data, dict) and "value" in value_data:
            # Normalize the value
            original_value = value_data["value"]
            normalized_value = original_value * multiplier
            
            # Create normalized entity
            normalized[key] = {
                **value_data,
                "value": normalized_value,
                "original_value": original_value,
                "original_unit": detected_unit,
                "normalized_unit": "INR",
            }
        elif isinstance(value_data, list):
            # Handle time series data
            normalized[key] = [v * multiplier for v in value_data if isinstance(v, (int, float))]
        else:
            # Pass through non-numeric data
            normalized[key] = value_data
    
    return normalized


def detect_and_normalize(
    entities: Dict[str, Any],
    full_text: str
) -> Dict[str, Any]:
    """
    Auto-detect unit from text and normalize values.
    
    Args:
        entities: Extracted financial entities
        full_text: Full document text for unit detection
    
    Returns:
        Normalized entities
    """
    from .financial_entity_extractor import extract_unit_indicators
    
    # Detect unit from document
    detected_unit = extract_unit_indicators(full_text)
    
    # Normalize
    return normalize_financial_values(entities, detected_unit)


def convert_unit(value: float, from_unit: str, to_unit: str = "inr") -> float:
    """
    Convert a single value from one unit to another.
    
    Args:
        value: Numeric value
        from_unit: Source unit (crore, lakh, etc.)
        to_unit: Target unit (default: inr)
    
    Returns:
        Converted value
    """
    from_multiplier = UNIT_MULTIPLIERS.get(from_unit.lower(), 1)
    to_multiplier = UNIT_MULTIPLIERS.get(to_unit.lower(), 1)
    
    # Convert to base INR, then to target unit
    base_value = value * from_multiplier
    converted_value = base_value / to_multiplier
    
    return converted_value


def format_indian_number(value: float, precision: int = 2) -> str:
    """
    Format number in Indian numbering system (lakhs and crores).
    
    Examples:
        1000000 -> "10.00 Lakh"
        10000000 -> "1.00 Crore"
        50000 -> "50,000"
    """
    if value >= 10_000_000:
        # Crores
        crores = value / 10_000_000
        return f"{crores:.{precision}f} Crore"
    elif value >= 100_000:
        # Lakhs
        lakhs = value / 100_000
        return f"{lakhs:.{precision}f} Lakh"
    elif value >= 1_000:
        # Thousands with comma
        return f"{value:,.{precision}f}"
    else:
        return f"{value:.{precision}f}"


def validate_unit_consistency(entities: Dict[str, Any]) -> Dict[str, Any]:
    """
    Check if all values are in similar ranges (consistency check).
    
    Returns:
        Validation report with warnings
    """
    values = []
    
    for key, data in entities.items():
        if isinstance(data, dict) and "value" in data:
            values.append(data["value"])
    
    if not values:
        return {"consistent": True, "warnings": []}
    
    # Calculate range
    min_val = min(values)
    max_val = max(values)
    
    # Check if range is too wide (might indicate unit mismatch)
    if max_val > 0 and min_val > 0:
        range_ratio = max_val / min_val
        
        if range_ratio > 10_000_000:
            # Extremely wide range - possible unit error
            return {
                "consistent": False,
                "warnings": [
                    "Value range is extremely wide. Possible unit mismatch detected.",
                    f"Min: {format_indian_number(min_val)}, Max: {format_indian_number(max_val)}"
                ],
                "min_value": min_val,
                "max_value": max_val,
                "range_ratio": range_ratio,
            }
    
    return {
        "consistent": True,
        "warnings": [],
        "min_value": min_val,
        "max_value": max_val,
    }


def infer_unit_from_magnitude(value: float, context: str = "") -> str:
    """
    Infer the most likely unit based on value magnitude.
    
    For example:
    - If revenue is 150, and context mentions "large company", likely in Crores
    - If revenue is 15000, likely in Lakhs
    """
    # Common sense ranges (for revenue of mid-size companies)
    if 10 <= value <= 10_000:
        # Likely in Crores
        return "crore"
    elif 100 <= value <= 100_000:
        # Could be Lakhs or Crores
        if "small" in context.lower() or "msme" in context.lower():
            return "lakh"
        else:
            return "crore"
    elif value > 100_000:
        # Likely in actual INR or very large company in Crores
        if value > 1_000_000_000:
            return "units"  # Already in INR
        else:
            return "crore"
    else:
        return "units"
