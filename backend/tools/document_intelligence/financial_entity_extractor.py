"""
Financial Entity Extraction Module
Extracts key financial metrics from text and tables using regex and NLP patterns.
"""
from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# Financial metric patterns with regex
FINANCIAL_PATTERNS = {
    "revenue": [
        r"revenue\s*[:-]?\s*([\d,\.]+)",
        r"sales\s*[:-]?\s*([\d,\.]+)",
        r"turnover\s*[:-]?\s*([\d,\.]+)",
        r"total\s+income\s*[:-]?\s*([\d,\.]+)",
    ],
    "ebitda": [
        r"ebitda\s*[:-]?\s*([\d,\.]+)",
        r"operating\s+profit\s+before\s+[^:]{0,30}\s*[:-]?\s*([\d,\.]+)",
    ],
    "ebit": [
        r"ebit\s*[:-]?\s*([\d,\.]+)",
        r"operating\s+profit\s*[:-]?\s*([\d,\.]+)",
        r"profit\s+before\s+interest\s+and\s+tax\s*[:-]?\s*([\d,\.]+)",
    ],
    "pbt": [
        r"pbt\s*[:-]?\s*([\d,\.]+)",
        r"profit\s+before\s+tax\s*[:-]?\s*([\d,\.]+)",
    ],
    "pat": [
        r"pat\s*[:-]?\s*([\d,\.]+)",
        r"net\s+profit\s*[:-]?\s*([\d,\.]+)",
        r"profit\s+after\s+tax\s*[:-]?\s*([\d,\.]+)",
    ],
    "total_assets": [
        r"total\s+assets\s*[:-]?\s*([\d,\.]+)",
    ],
    "total_debt": [
        r"total\s+debt\s*[:-]?\s*([\d,\.]+)",
        r"total\s+borrowings\s*[:-]?\s*([\d,\.]+)",
        r"outstanding\s+debt\s*[:-]?\s*([\d,\.]+)",
    ],
    "net_worth": [
        r"net\s+worth\s*[:-]?\s*([\d,\.]+)",
        r"shareholders?\s*'?\s*funds?\s*[:-]?\s*([\d,\.]+)",
        r"equity\s*[:-]?\s*([\d,\.]+)",
    ],
    "current_assets": [
        r"current\s+assets\s*[:-]?\s*([\d,\.]+)",
    ],
    "current_liabilities": [
        r"current\s+liabilities\s*[:-]?\s*([\d,\.]+)",
    ],
    "inventory": [
        r"inventory\s*[:-]?\s*([\d,\.]+)",
        r"stock\s*[:-]?\s*([\d,\.]+)",
    ],
    "receivables": [
        r"receivables\s*[:-]?\s*([\d,\.]+)",
        r"debtors\s*[:-]?\s*([\d,\.]+)",
        r"trade\s+receivables\s*[:-]?\s*([\d,\.]+)",
    ],
    "payables": [
        r"payables\s*[:-]?\s*([\d,\.]+)",
        r"creditors\s*[:-]?\s*([\d,\.]+)",
        r"trade\s+payables\s*[:-]?\s*([\d,\.]+)",
    ],
    "cash": [
        r"cash\s+and\s+bank\s*[:-]?\s*([\d,\.]+)",
        r"cash\s*[:-]?\s*([\d,\.]+)",
    ],
}


def extract_financial_entities(
    text: str,
    tables: List[Dict[str, Any]],
    doc_type: str = "unknown"
) -> Dict[str, Any]:
    """
    Extract financial metrics from text and tables.
    
    Args:
        text: Full document text
        tables: Extracted tables with classifications
        doc_type: Document type from classifier
    
    Returns:
        Dictionary of extracted financial metrics with confidence scores
    """
    entities = {}
    
    # Extract from plain text using regex
    text_entities = _extract_from_text(text)
    
    # Extract from tables
    table_entities = _extract_from_tables(tables)
    
    # Merge results (tables have priority over text)
    for metric in set(list(text_entities.keys()) + list(table_entities.keys())):
        if metric in table_entities:
            entities[metric] = table_entities[metric]
        elif metric in text_entities:
            entities[metric] = text_entities[metric]
    
    # Extract time series data (multi-year)
    time_series = _extract_time_series(tables)
    if time_series:
        entities["time_series"] = time_series
    
    logger.info(f"Extracted {len(entities)} financial entities")
    return entities


def _extract_from_text(text: str) -> Dict[str, Dict[str, Any]]:
    """
    Extract financial metrics from plain text using regex patterns.
    """
    entities = {}
    text_lower = text.lower()
    
    for metric, patterns in FINANCIAL_PATTERNS.items():
        for pattern in patterns:
            matches = re.finditer(pattern, text_lower, re.IGNORECASE)
            
            for match in matches:
                try:
                    # Extract the numeric group
                    value_str = match.group(1)
                    
                    # Parse number
                    value = _parse_number(value_str)
                    
                    if value is not None and value > 0:
                        # Store if not already found or if higher confidence
                        if metric not in entities:
                            entities[metric] = {
                                "value": value,
                                "confidence": 0.6,  # Text extraction has lower confidence
                                "source": "text_regex",
                                "raw_text": match.group(0),
                            }
                except (IndexError, ValueError):
                    continue
    
    return entities


def _extract_from_tables(tables: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """
    Extract financial metrics from structured tables.
    """
    entities = {}
    
    for table in tables:
        table_type = table.get("table_type", "unknown")
        page = table.get("page", 1)
        grid = table.get("grid", [])
        
        if not grid:
            continue
        
        # Extract based on table type
        if table_type == "income_statement":
            metrics = _extract_income_metrics(grid, page)
            entities.update(metrics)
        
        elif table_type == "balance_sheet":
            metrics = _extract_balance_metrics(grid, page)
            entities.update(metrics)
        
        elif table_type == "cash_flow":
            metrics = _extract_cashflow_metrics(grid, page)
            entities.update(metrics)
        
        elif table_type == "financial_ratios":
            metrics = _extract_ratio_metrics(grid, page)
            entities.update(metrics)
    
    return entities


def _extract_income_metrics(grid: List[List[Any]], page: int) -> Dict[str, Dict[str, Any]]:
    """
    Extract metrics from Income Statement table.
    """
    metrics = {}
    
    targets = {
        "revenue": ["revenue", "sales", "turnover", "total income"],
        "ebitda": ["ebitda"],
        "ebit": ["ebit", "operating profit"],
        "pbt": ["pbt", "profit before tax"],
        "pat": ["pat", "net profit", "profit after tax"],
        "depreciation": ["depreciation", "amortization"],
    }
    
    for row in grid[1:]:  # Skip header
        if not row or len(row) < 2:
            continue
        
        label = str(row[0]).lower().strip()
        
        for metric, keywords in targets.items():
            if any(kw in label for kw in keywords):
                # Find numeric value in row
                for cell in row[1:]:
                    value = _parse_number(str(cell))
                    if value is not None:
                        metrics[metric] = {
                            "value": value,
                            "confidence": 0.9,  # High confidence from tables
                            "source": f"table_page_{page}",
                            "label": row[0],
                        }
                        break
    
    return metrics


def _extract_balance_metrics(grid: List[List[Any]], page: int) -> Dict[str, Dict[str, Any]]:
    """
    Extract metrics from Balance Sheet table.
    """
    metrics = {}
    
    targets = {
        "total_assets": ["total assets"],
        "current_assets": ["current assets"],
        "fixed_assets": ["fixed assets", "non-current assets", "non current assets"],
        "total_debt": ["total debt", "borrowings", "total borrowings"],
        "net_worth": ["net worth", "shareholders funds", "equity"],
        "current_liabilities": ["current liabilities"],
        "inventory": ["inventory", "inventories", "stock"],
        "receivables": ["receivables", "debtors", "trade receivables"],
        "payables": ["payables", "creditors", "trade payables"],
        "cash": ["cash and bank", "cash & bank", "cash"],
    }
    
    for row in grid[1:]:
        if not row or len(row) < 2:
            continue
        
        label = str(row[0]).lower().strip()
        
        for metric, keywords in targets.items():
            if any(kw in label for kw in keywords):
                for cell in row[1:]:
                    value = _parse_number(str(cell))
                    if value is not None:
                        metrics[metric] = {
                            "value": value,
                            "confidence": 0.9,
                            "source": f"table_page_{page}",
                            "label": row[0],
                        }
                        break
    
    return metrics


def _extract_cashflow_metrics(grid: List[List[Any]], page: int) -> Dict[str, Dict[str, Any]]:
    """
    Extract cash flow metrics.
    """
    metrics = {}
    
    targets = {
        "operating_cash_flow": ["operating", "operations"],
        "investing_cash_flow": ["investing"],
        "financing_cash_flow": ["financing"],
        "free_cash_flow": ["free cash"],
    }
    
    for row in grid[1:]:
        if not row or len(row) < 2:
            continue
        
        label = str(row[0]).lower().strip()
        
        for metric, keywords in targets.items():
            if any(kw in label for kw in keywords):
                for cell in row[1:]:
                    value = _parse_number(str(cell))
                    if value is not None:
                        metrics[metric] = {
                            "value": value,
                            "confidence": 0.85,
                            "source": f"table_page_{page}",
                            "label": row[0],
                        }
                        break
    
    return metrics


def _extract_ratio_metrics(grid: List[List[Any]], page: int) -> Dict[str, Dict[str, Any]]:
    """
    Extract financial ratios.
    """
    metrics = {}
    
    for row in grid[1:]:
        if not row or len(row) < 2:
            continue
        
        label = str(row[0]).strip()
        
        for cell in row[1:]:
            value = _parse_number(str(cell))
            if value is not None:
                # Create metric key from label
                metric_key = label.lower().replace(" ", "_").replace("/", "_")
                metrics[metric_key] = {
                    "value": value,
                    "confidence": 0.85,
                    "source": f"ratios_page_{page}",
                    "label": label,
                }
                break
    
    return metrics


def _extract_time_series(tables: List[Dict[str, Any]]) -> Dict[str, List[float]]:
    """
    Extract multi-year time series data from tables.
    
    Looks for tables with year columns (FY 2021, FY 2022, etc.)
    """
    time_series = {}
    
    for table in tables:
        grid = table.get("grid", [])
        if not grid or len(grid) < 2:
            continue
        
        header = grid[0]
        
        # Detect year columns
        year_columns = []
        for idx, col_name in enumerate(header):
            if _is_year_header(str(col_name)):
                year_columns.append(idx)
        
        if len(year_columns) < 2:  # Need at least 2 years for time series
            continue
        
        # Extract time series for key metrics
        for row in grid[1:]:
            if not row:
                continue
            
            label = str(row[0]).lower().strip()
            
            # Check if this row is a key metric
            metric_key = _map_label_to_metric(label)
            if not metric_key:
                continue
            
            # Extract values for each year
            values = []
            for year_idx in year_columns:
                if year_idx < len(row):
                    value = _parse_number(str(row[year_idx]))
                    if value is not None:
                        values.append(value)
            
            if len(values) >= 2:
                time_series[metric_key] = values
    
    return time_series


def _is_year_header(text: str) -> bool:
    """
    Check if column header represents a year.
    """
    patterns = [
        r"fy\s*\d{2,4}",
        r"20\d{2}",
        r"19\d{2}",
        r"year\s+\d{4}",
    ]
    
    text_lower = text.lower()
    return any(re.search(p, text_lower) for p in patterns)


def _map_label_to_metric(label: str) -> Optional[str]:
    """
    Map table row label to standard metric key.
    """
    mappings = {
        "revenue": ["revenue", "sales", "turnover"],
        "ebitda": ["ebitda"],
        "pat": ["pat", "net profit", "profit after tax"],
        "total_debt": ["total debt", "borrowings"],
        "net_worth": ["net worth", "equity", "shareholders funds"],
    }
    
    for metric, keywords in mappings.items():
        if any(kw in label for kw in keywords):
            return metric
    
    return None


def _parse_number(text: str) -> Optional[float]:
    """
    Parse numeric value from text, handling Indian and international formats.
    
    Handles:
    - Commas: 1,234.56
    - Parentheses for negatives: (123)
    - Currency symbols: ₹ $ £
    - Percentage: 12.5%
    """
    if not isinstance(text, str):
        text = str(text)
    
    # Remove whitespace
    text = text.strip()
    
    if not text or text == '-' or text == '':
        return None
    
    # Check for percentage
    is_percentage = '%' in text
    
    # Remove currency symbols and other non-numeric chars (except .,-)
    cleaned = re.sub(r'[^\d\.\,\-\(\)]', '', text)
    
    if not cleaned or cleaned in ['-', '.', ',', '(', ')']:
        return None
    
    # Handle parentheses as negative
    is_negative = '(' in cleaned and ')' in cleaned
    cleaned = cleaned.replace('(', '').replace(')', '')
    
    # Handle comma as thousand separator
    cleaned = cleaned.replace(',', '')
    
    try:
        value = float(cleaned)
        
        if is_negative:
            value = -value
        
        if is_percentage:
            value = value / 100
        
        return value
        
    except ValueError:
        return None


def extract_unit_indicators(text: str) -> str:
    """
    Detect the unit of measurement used in the document.
    
    Returns:
        Unit string: 'crore', 'lakh', 'million', 'billion', 'thousand', or 'units'
    """
    text_lower = text.lower()
    
    # Check for explicit unit statements
    unit_patterns = [
        (r"in\s+crores?", "crore"),
        (r"₹\s+crores?", "crore"),
        (r"rs\.?\s+crores?", "crore"),
        (r"in\s+lakhs?", "lakh"),
        (r"₹\s+lakhs?", "lakh"),
        (r"in\s+millions?", "million"),
        (r"in\s+billions?", "billion"),
        (r"in\s+thousands?", "thousand"),
    ]
    
    for pattern, unit in unit_patterns:
        if re.search(pattern, text_lower):
            logger.info(f"Detected unit: {unit}")
            return unit
    
    # Default
    return "units"
