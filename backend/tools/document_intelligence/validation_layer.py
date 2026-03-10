"""
Validation Layer Module
Cross-validates extracted financial data across multiple sources.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


def validate_financial_data(
    entities: Dict[str, Any],
    doc_type: str,
    multiple_docs: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """
    Validate extracted financial data for consistency and accuracy.
    
    Args:
        entities: Extracted and normalized financial entities
        doc_type: Type of document
        multiple_docs: List of entities from multiple documents for cross-validation
    
    Returns:
        Validation report with flags and warnings
    """
    validation_report = {
        "valid": True,
        "flags": [],
        "warnings": [],
        "cross_checks": [],
    }
    
    # 1. Internal consistency checks
    consistency = _check_internal_consistency(entities)
    if consistency["flags"]:
        validation_report["flags"].extend(consistency["flags"])
        validation_report["valid"] = False
    if consistency["warnings"]:
        validation_report["warnings"].extend(consistency["warnings"])
    
    # 2. Ratio validation
    ratio_checks = _validate_financial_ratios(entities)
    if ratio_checks["flags"]:
        validation_report["flags"].extend(ratio_checks["flags"])
        validation_report["valid"] = False
    if ratio_checks["warnings"]:
        validation_report["warnings"].extend(ratio_checks["warnings"])
    
    # 3. Trend validation (for time series data)
    if "time_series" in entities:
        trend_checks = _validate_trends(entities["time_series"])
        if trend_checks["warnings"]:
            validation_report["warnings"].extend(trend_checks["warnings"])
    
    # 4. Cross-document validation
    if multiple_docs and len(multiple_docs) > 1:
        cross_validation = _cross_validate_documents(entities, multiple_docs)
        validation_report["cross_checks"] = cross_validation["checks"]
        if cross_validation["flags"]:
            validation_report["flags"].extend(cross_validation["flags"])
            validation_report["valid"] = False
    
    # 5. Missing critical fields
    missing = _check_missing_fields(entities, doc_type)
    if missing:
        validation_report["warnings"].append({
            "type": "MISSING_FIELDS",
            "message": f"Missing critical fields: {', '.join(missing)}",
            "severity": "MEDIUM",
        })
    
    logger.info(f"Validation complete: {len(validation_report['flags'])} flags, {len(validation_report['warnings'])} warnings")
    
    return validation_report


def _check_internal_consistency(entities: Dict[str, Any]) -> Dict[str, List]:
    """
    Check internal consistency of financial statements.
    
    Examples:
    - Balance Sheet: Total Assets = Total Liabilities + Equity
    - P&L: EBITDA > EBIT > PBT > PAT
    """
    flags = []
    warnings = []
    
    # Get values safely
    def get_value(key: str) -> Optional[float]:
        if key in entities:
            data = entities[key]
            if isinstance(data, dict) and "value" in data:
                return data["value"]
        return None
    
    # Check: EBITDA >= EBIT
    ebitda = get_value("ebitda")
    ebit = get_value("ebit")
    if ebitda is not None and ebit is not None:
        if ebit > ebitda:
            flags.append({
                "type": "LOGIC_ERROR",
                "message": f"EBIT ({ebit:,.0f}) cannot be greater than EBITDA ({ebitda:,.0f})",
                "severity": "HIGH",
            })
    
    # Check: EBIT >= PBT (usually, unless there's significant interest income)
    pbt = get_value("pbt")
    if ebit is not None and pbt is not None:
        if pbt > ebit * 1.5:  # Allow some tolerance for interest income
            warnings.append({
                "type": "UNUSUAL_RELATIONSHIP",
                "message": f"PBT ({pbt:,.0f}) significantly higher than EBIT ({ebit:,.0f}). Check for interest income.",
                "severity": "LOW",
            })
    
    # Check: PBT > PAT (PAT is after tax)
    pat = get_value("pat")
    if pbt is not None and pat is not None:
        if pat > pbt:
            flags.append({
                "type": "LOGIC_ERROR",
                "message": f"PAT ({pat:,.0f}) cannot be greater than PBT ({pbt:,.0f})",
                "severity": "HIGH",
            })
    
    # Check: Balance Sheet equation
    total_assets = get_value("total_assets")
    total_debt = get_value("total_debt")
    net_worth = get_value("net_worth")
    
    if total_assets and total_debt and net_worth:
        # Simplified: Assets = Debt + Equity (ignoring other liabilities)
        implied_liabilities = total_debt + net_worth
        difference_pct = abs(total_assets - implied_liabilities) / total_assets * 100
        
        if difference_pct > 20:  # More than 20% difference
            warnings.append({
                "type": "BALANCE_SHEET_MISMATCH",
                "message": f"Assets ({total_assets:,.0f}) don't balance with Debt+Equity ({implied_liabilities:,.0f}). Difference: {difference_pct:.1f}%",
                "severity": "MEDIUM",
            })
    
    # Check: Current RatioComponents
    current_assets = get_value("current_assets")
    current_liabilities = get_value("current_liabilities")
    
    if current_assets and current_liabilities:
        current_ratio = current_assets / current_liabilities
        if current_ratio < 0.5:
            flags.append({
                "type": "LIQUIDITY_CRISIS",
                "message": f"Current ratio is critically low: {current_ratio:.2f}. Severe liquidity risk.",
                "severity": "HIGH",
            })
        elif current_ratio < 1.0:
            warnings.append({
                "type": "LOW_LIQUIDITY",
                "message": f"Current ratio below 1.0: {current_ratio:.2f}. Liquidity concerns.",
                "severity": "MEDIUM",
            })
    
    # Check: Negative values where they shouldn't be
    for metric in ["revenue", "total_assets", "current_assets"]:
        value = get_value(metric)
        if value is not None and value < 0:
            flags.append({
                "type": "NEGATIVE_VALUE",
                "message": f"{metric} cannot be negative: {value:,.0f}",
                "severity": "HIGH",
            })
    
    return {"flags": flags, "warnings": warnings}


def _validate_financial_ratios(entities: Dict[str, Any]) -> Dict[str, List]:
    """
    Validate financial ratios are within reasonable bounds.
    """
    flags = []
    warnings = []
    
    def get_value(key: str) -> Optional[float]:
        if key in entities:
            data = entities[key]
            if isinstance(data, dict) and "value" in data:
                return data["value"]
        return None
    
    revenue = get_value("revenue")
    pat = get_value("pat")
    ebitda = get_value("ebitda")
    total_assets = get_value("total_assets")
    total_debt = get_value("total_debt")
    net_worth = get_value("net_worth")
    
    # PAT Margin check
    if revenue and pat:
        pat_margin = (pat / revenue) * 100
        if pat_margin < -50:
            flags.append({
                "type": "EXTREME_LOSS",
                "message": f"PAT margin is {pat_margin:.1f}%. Company is making severe losses.",
                "severity": "HIGH",
            })
        elif pat_margin > 50:
            warnings.append({
                "type": "UNUSUALLY_HIGH_MARGIN",
                "message": f"PAT margin is {pat_margin:.1f}%. Unusually high profitability.",
                "severity": "LOW",
            })
    
    # EBITDA Margin check
    if revenue and ebitda:
        ebitda_margin = (ebitda / revenue) * 100
        if ebitda_margin < -20:
            flags.append({
                "type": "NEGATIVE_EBITDA",
                "message": f"EBITDA margin is {ebitda_margin:.1f}%. Operating losses.",
                "severity": "HIGH",
            })
    
    # Debt-to-Equity Ratio
    if total_debt and net_worth:
        d_e_ratio = total_debt / net_worth
        if d_e_ratio > 5:
            flags.append({
                "type": "EXCESSIVE_LEVERAGE",
                "message": f"Debt-to-Equity ratio is {d_e_ratio:.2f}. Highly leveraged.",
                "severity": "HIGH",
            })
        elif d_e_ratio > 2:
            warnings.append({
                "type": "HIGH_LEVERAGE",
                "message": f"Debt-to-Equity ratio is {d_e_ratio:.2f}. Above industry norms.",
                "severity": "MEDIUM",
            })
    
    # Asset Turnover
    if revenue and total_assets:
        asset_turnover = revenue / total_assets
        if asset_turnover < 0.3:
            warnings.append({
                "type": "LOW_ASSET_EFFICIENCY",
                "message": f"Asset turnover is {asset_turnover:.2f}. Assets not generating adequate revenue.",
                "severity": "MEDIUM",
            })
        elif asset_turnover > 5:
            warnings.append({
                "type": "HIGH_ASSET_TURNOVER",
                "message": f"Asset turnover is {asset_turnover:.2f}. Verify asset values.",
                "severity": "LOW",
            })
    
    return {"flags": flags, "warnings": warnings}


def _validate_trends(time_series: Dict[str, List[float]]) -> Dict[str, List]:
    """
    Validate trends in time series data.
    """
    warnings = []
    
    for metric, values in time_series.items():
        if len(values) < 2:
            continue
        
        # Calculate year-over-year growth
        growths = []
        for i in range(1, len(values)):
            if values[i-1] != 0:
                growth = ((values[i] - values[i-1]) / abs(values[i-1])) * 100
                growths.append(growth)
        
        if not growths:
            continue
        
        avg_growth = sum(growths) / len(growths)
        
        # Check for extreme volatility
        if any(abs(g) > 200 for g in growths):
            warnings.append({
                "type": "EXTREME_VOLATILITY",
                "message": f"{metric} shows extreme year-over-year changes (>200%). Verify data accuracy.",
                "severity": "MEDIUM",
            })
        
        # Check for consistent decline
        if all(g < 0 for g in growths):
            warnings.append({
                "type": "DECLINING_TREND",
                "message": f"{metric} has been declining consistently over the years.",
                "severity": "MEDIUM",
            })
    
    return {"warnings": warnings}


def _cross_validate_documents(
    primary: Dict[str, Any],
    other_docs: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Cross-validate data across multiple documents.
    
    Example: GST returns vs Annual Report revenue
    """
    checks = []
    flags = []
    
    def get_value(entities: Dict[str, Any], key: str) -> Optional[float]:
        if key in entities:
            data = entities[key]
            if isinstance(data, dict) and "value" in data:
                return data["value"]
        return None
    
    # Compare revenue across documents
    primary_revenue = get_value(primary, "revenue")
    
    for doc in other_docs:
        doc_revenue = get_value(doc, "revenue")
        
        if primary_revenue and doc_revenue:
            variance_pct = abs(primary_revenue - doc_revenue) / primary_revenue * 100
            
            checks.append({
                "metric": "revenue",
                "primary_value": primary_revenue,
                "secondary_value": doc_revenue,
                "variance_pct": variance_pct,
            })
            
            if variance_pct > 15:
                flags.append({
                    "type": "REVENUE_MISMATCH",
                    "message": f"Revenue mismatch of {variance_pct:.1f}% between documents. Primary: {primary_revenue:,.0f}, Secondary: {doc_revenue:,.0f}",
                    "severity": "HIGH",
                })
    
    return {"checks": checks, "flags": flags}


def _check_missing_fields(entities: Dict[str, Any], doc_type: str) -> List[str]:
    """
    Check for missing critical fields based on document type.
    """
    critical_fields = {
        "annual_report": ["revenue", "pat", "total_assets", "net_worth"],
        "bank_statement": ["cash"],
        "gst_filing": ["revenue"],
        "rating_report": ["total_debt", "revenue"],
    }
    
    required = critical_fields.get(doc_type, [])
    missing = []
    
    for field in required:
        if field not in entities:
            missing.append(field)
    
    return missing
