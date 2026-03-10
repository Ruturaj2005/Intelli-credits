"""
Table Extraction Module
Advanced table extraction from financial documents using Camelot and layout analysis.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

logger = logging.getLogger(__name__)


def extract_tables_advanced(
    pdf_path: str,
    ocr_tables: List[Dict[str, Any]],
    use_camelot: bool = True
) -> List[Dict[str, Any]]:
    """
    Extract tables using multiple methods and merge results.
    
    Args:
        pdf_path: Path to PDF file
        ocr_tables: Tables detected from OCR engine
        use_camelot: Whether to use Camelot for table extraction
    
    Returns:
        List of structured tables with enhanced metadata
    """
    all_tables = []
    
    # Method 1: Use Camelot for high-quality table extraction
    if use_camelot:
        camelot_tables = _extract_with_camelot(pdf_path)
        all_tables.extend(camelot_tables)
    
    # Method 2: Use OCR-detected tables
    ocr_enhanced = _enhance_ocr_tables(ocr_tables)
    all_tables.extend(ocr_enhanced)
    
    # Deduplicate tables
    unique_tables = _deduplicate_tables(all_tables)
    
    # Classify table types
    classified_tables = [_classify_table(t) for t in unique_tables]
    
    logger.info(f"Extracted {len(classified_tables)} unique tables")
    return classified_tables


def _extract_with_camelot(pdf_path: str) -> List[Dict[str, Any]]:
    """
    Extract tables using Camelot library.
    
    Camelot is excellent for well-formatted PDFs with clear table borders.
    """
    tables = []
    
    try:
        import camelot
        
        # Try lattice method first (for tables with borders)
        logger.info(f"Extracting tables with Camelot (lattice method)")
        lattice_tables = camelot.read_pdf(
            pdf_path,
            pages='all',
            flavor='lattice',
            strip_text='\n'
        )
        
        for idx, table in enumerate(lattice_tables):
            if table.accuracy > 50:  # Only include high-confidence tables
                df = table.df
                tables.append({
                    "source": "camelot_lattice",
                    "page": table.page,
                    "accuracy": table.accuracy,
                    "dataframe": df,
                    "grid": df.values.tolist(),
                    "header": df.iloc[0].tolist() if len(df) > 0 else [],
                    "rows": len(df),
                    "cols": len(df.columns),
                })
        
        # Try stream method (for tables without borders)
        logger.info(f"Extracting tables with Camelot (stream method)")
        stream_tables = camelot.read_pdf(
            pdf_path,
            pages='all',
            flavor='stream',
            strip_text='\n'
        )
        
        for idx, table in enumerate(stream_tables):
            if table.accuracy > 50:
                df = table.df
                tables.append({
                    "source": "camelot_stream",
                    "page": table.page,
                    "accuracy": table.accuracy,
                    "dataframe": df,
                    "grid": df.values.tolist(),
                    "header": df.iloc[0].tolist() if len(df) > 0 else [],
                    "rows": len(df),
                    "cols": len(df.columns),
                })
        
        logger.info(f"Camelot extracted {len(tables)} tables")
        
    except ImportError:
        logger.warning("Camelot not installed, skipping Camelot extraction")
    except Exception as e:
        logger.error(f"Camelot extraction error: {e}")
    
    return tables


def _enhance_ocr_tables(ocr_tables: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Enhance OCR-detected tables with additional structure.
    """
    enhanced = []
    
    for table in ocr_tables:
        if "grid" not in table or not table["grid"]:
            continue
        
        # Convert to DataFrame for easier manipulation
        df = pd.DataFrame(table["grid"])
        
        # Clean empty rows/columns
        df = df.replace('', pd.NA).dropna(how='all').dropna(axis=1, how='all')
        
        if df.empty:
            continue
        
        enhanced_table = {
            "source": "ocr",
            "page": table.get("page", 1),
            "accuracy": 75.0,  # Default OCR table confidence
            "dataframe": df,
            "grid": df.values.tolist(),
            "header": df.iloc[0].tolist() if len(df) > 0 else [],
            "rows": len(df),
            "cols": len(df.columns),
            "bbox": table.get("bbox"),
        }
        enhanced.append(enhanced_table)
    
    return enhanced


def _deduplicate_tables(tables: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Remove duplicate tables extracted by multiple methods.
    
    Tables are considered duplicates if:
    - Same page
    - Similar dimensions
    - Similar content overlap
    """
    if len(tables) <= 1:
        return tables
    
    unique = []
    seen_signatures = set()
    
    for table in tables:
        signature = _table_signature(table)
        
        if signature not in seen_signatures:
            unique.append(table)
            seen_signatures.add(signature)
    
    return unique


def _table_signature(table: Dict[str, Any]) -> str:
    """
    Generate a signature for table deduplication.
    """
    page = table.get("page", 0)
    rows = table.get("rows", 0)
    cols = table.get("cols", 0)
    
    # Use first few cells as content signature
    grid = table.get("grid", [])
    content_sample = ""
    if grid and len(grid) > 0:
        first_row = grid[0]
        content_sample = "".join(str(cell) for cell in first_row[:3])
    
    return f"{page}_{rows}x{cols}_{content_sample[:50]}"


def _classify_table(table: Dict[str, Any]) -> Dict[str, Any]:
    """
    Classify table type based on header and content patterns.
    """
    header = table.get("header", [])
    grid = table.get("grid", [])
    
    if not header:
        table["table_type"] = "unknown"
        return table
    
    header_text = " ".join(str(h).lower() for h in header)
    
    # Financial statement patterns
    if any(kw in header_text for kw in ["revenue", "income", "expenses", "profit", "loss"]):
        table["table_type"] = "income_statement"
    elif any(kw in header_text for kw in ["assets", "liabilities", "equity", "capital"]):
        table["table_type"] = "balance_sheet"
    elif any(kw in header_text for kw in ["cash flow", "operating", "investing", "financing"]):
        table["table_type"] = "cash_flow"
    elif any(kw in header_text for kw in ["ratio", "liquidity", "solvency", "profitability"]):
        table["table_type"] = "financial_ratios"
    
    # Transaction tables
    elif any(kw in header_text for kw in ["date", "transaction", "debit", "credit", "balance"]):
        table["table_type"] = "transaction_history"
    
    # GST tables
    elif any(kw in header_text for kw in ["gstin", "invoice", "igst", "cgst", "sgst"]):
        table["table_type"] = "gst_summary"
    
    # Rating tables
    elif any(kw in header_text for kw in ["rating", "outlook", "grade", "score"]):
        table["table_type"] = "credit_rating"
    
    else:
        table["table_type"] = "generic"
    
    return table


def extract_financial_table_data(table: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract structured financial data from classified tables.
    
    Returns key financial metrics with values.
    """
    table_type = table.get("table_type", "unknown")
    grid = table.get("grid", [])
    
    if not grid or len(grid) < 2:
        return {}
    
    extracted = {}
    
    if table_type == "income_statement":
        extracted = _extract_income_statement(grid)
    elif table_type == "balance_sheet":
        extracted = _extract_balance_sheet(grid)
    elif table_type == "cash_flow":
        extracted = _extract_cash_flow(grid)
    elif table_type == "financial_ratios":
        extracted = _extract_ratios(grid)
    
    return extracted


def _extract_income_statement(grid: List[List[Any]]) -> Dict[str, Any]:
    """
    Extract key metrics from Income Statement table.
    """
    metrics = {}
    
    # Common P&L line items
    targets = {
        "revenue": ["revenue", "sales", "turnover", "total income"],
        "ebitda": ["ebitda", "operating profit before"],
        "ebit": ["ebit", "operating profit", "pbit"],
        "pbt": ["pbt", "profit before tax"],
        "pat": ["pat", "net profit", "profit after tax"],
        "depreciation": ["depreciation", "amortization"],
    }
    
    for row in grid:
        if not row or len(row) < 2:
            continue
        
        label = str(row[0]).lower()
        
        for metric, keywords in targets.items():
            if any(kw in label for kw in keywords):
                # Extract numeric value (usually in 2nd or 3rd column)
                for cell in row[1:]:
                    value = _extract_number(str(cell))
                    if value is not None:
                        metrics[metric] = value
                        break
    
    return metrics


def _extract_balance_sheet(grid: List[List[Any]]) -> Dict[str, Any]:
    """
    Extract key metrics from Balance Sheet table.
    """
    metrics = {}
    
    targets = {
        "total_assets": ["total assets"],
        "current_assets": ["current assets"],
        "fixed_assets": ["fixed assets", "non-current assets"],
        "total_liabilities": ["total liabilities"],
        "current_liabilities": ["current liabilities"],
        "debt": ["total debt", "borrowings", "term loans"],
        "equity": ["equity", "shareholders funds", "net worth"],
        "reserves": ["reserves", "surplus"],
    }
    
    for row in grid:
        if not row or len(row) < 2:
            continue
        
        label = str(row[0]).lower()
        
        for metric, keywords in targets.items():
            if any(kw in label for kw in keywords):
                for cell in row[1:]:
                    value = _extract_number(str(cell))
                    if value is not None:
                        metrics[metric] = value
                        break
    
    return metrics


def _extract_cash_flow(grid: List[List[Any]]) -> Dict[str, Any]:
    """
    Extract cash flow metrics.
    """
    metrics = {}
    
    targets = {
        "operating_cash_flow": ["operating activities", "cash from operations"],
        "investing_cash_flow": ["investing activities"],
        "financing_cash_flow": ["financing activities"],
        "free_cash_flow": ["free cash flow"],
    }
    
    for row in grid:
        if not row or len(row) < 2:
            continue
        
        label = str(row[0]).lower()
        
        for metric, keywords in targets.items():
            if any(kw in label for kw in keywords):
                for cell in row[1:]:
                    value = _extract_number(str(cell))
                    if value is not None:
                        metrics[metric] = value
                        break
    
    return metrics


def _extract_ratios(grid: List[List[Any]]) -> Dict[str, Any]:
    """
    Extract financial ratios.
    """
    ratios = {}
    
    for row in grid:
        if not row or len(row) < 2:
            continue
        
        label = str(row[0]).lower()
        
        # Extract ratio value
        for cell in row[1:]:
            value = _extract_number(str(cell))
            if value is not None:
                # Store with cleaned label
                clean_label = label.strip().replace(" ", "_")
                ratios[clean_label] = value
                break
    
    return ratios


def _extract_number(text: str) -> Optional[float]:
    """
    Extract numeric value from text, handling various formats.
    """
    import re
    
    # Remove common non-numeric characters but keep decimal point, comma, and minus
    cleaned = re.sub(r'[^\d.,\-()]', '', text)
    
    if not cleaned or cleaned in ['-', '.', ',']:
        return None
    
    # Handle parentheses as negative
    is_negative = '(' in text and ')' in text
    cleaned = cleaned.replace('(', '').replace(')', '')
    
    # Remove commas
    cleaned = cleaned.replace(',', '')
    
    try:
        value = float(cleaned)
        return -value if is_negative else value
    except ValueError:
        return None
