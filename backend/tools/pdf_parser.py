"""
PDF parsing utilities using PyMuPDF and pdfplumber.
Extracts text and tables from uploaded financial documents.

Now includes advanced Document Intelligence Pipeline for messy/scanned documents.
"""
from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any, Dict, List

import fitz  # PyMuPDF
import pdfplumber

logger = logging.getLogger(__name__)


# ─── Advanced Document Intelligence Pipeline ──────────────────────────────────

def parse_with_intelligence(
    file_path: str,
    doc_type: str = "unknown",
    use_advanced_pipeline: bool = True
) -> Dict[str, Any]:
    """
    Parse financial document using advanced Document Intelligence Pipeline.
    
    This pipeline handles messy scanned documents, rotated pages, tables,
    and extracts structured financial data with confidence scores.
    
    Args:
        file_path: Path to PDF file
        doc_type: Optional document type hint
        use_advanced_pipeline: If True, uses full pipeline; if False, falls back to basic
    
    Returns:
        Comprehensive document analysis with structured financial data
    """
    if not use_advanced_pipeline:
        # Fallback to basic extraction
        return parse_financial_document(file_path, doc_type)
    
    try:
        from tools.document_intelligence import (
            preprocess_pdf_pages,
            extract_with_ocr,
            classify_document,
            extract_tables_advanced,
            extract_financial_entities,
            normalize_financial_values,
            validate_financial_data,
            calculate_confidence_scores,
        )
        from tools.document_intelligence.unit_normalizer import detect_and_normalize
        
        logger.info(f"Starting advanced document intelligence pipeline for {file_path}")
        
        # Stage 1: Image Preprocessing
        logger.info("Stage 1: Preprocessing PDF pages...")
        preprocessed_images = preprocess_pdf_pages(file_path, dpi=300)
        
        if not preprocessed_images:
            logger.warning("Preprocessing failed, falling back to basic extraction")
            return parse_financial_document(file_path, doc_type)
        
        # Stage 2: OCR with Layout Detection
        logger.info("Stage 2: Running OCR with layout detection...")
        ocr_result = extract_with_ocr(preprocessed_images, file_path)
        
        full_text = ocr_result.get("full_text", "")
        text_blocks = ocr_result.get("text_blocks", [])
        ocr_tables = ocr_result.get("tables", [])
        ocr_confidence = ocr_result.get("confidence", 0.0)
        
        # Stage 3: Document Classification
        logger.info("Stage 3: Classifying document type...")
        doc_classification = classify_document(full_text, Path(file_path).name)
        detected_doc_type = doc_classification.get("document_type", doc_type)
        
        logger.info(f"Detected document type: {detected_doc_type}")
        
        # Stage 4: Advanced Table Extraction
        logger.info("Stage 4: Extracting tables...")
        tables = extract_tables_advanced(file_path, ocr_tables, use_camelot=True)
        
        # Stage 5: Financial Entity Extraction
        logger.info("Stage 5: Extracting financial entities...")
        entities = extract_financial_entities(full_text, tables, detected_doc_type)
        
        # Stage 6: Unit Normalization
        logger.info("Stage 6: Normalizing units...")
        normalized_entities = detect_and_normalize(entities, full_text)
        
        # Stage 7: Validation
        logger.info("Stage 7: Validating extracted data...")
        validation_report = validate_financial_data(normalized_entities, detected_doc_type)
        
        # Stage 8: Confidence Scoring
        logger.info("Stage 8: Calculating confidence scores...")
        confidence_result = calculate_confidence_scores(
            normalized_entities,
            ocr_confidence,
            validation_report,
            doc_classification
        )
        
        # Compile comprehensive result
        result = {
            "file_path": file_path,
            "file_name": Path(file_path).name,
            "doc_type": detected_doc_type,
            "doc_classification": doc_classification,
            
            # Raw extracted content
            "text": full_text[:40_000],
            "text_blocks_count": len(text_blocks),
            "page_count": len(preprocessed_images),
            
            # Structured financial data
            "financial_entities": confidence_result["entities"],
            "tables": tables,
            "tables_count": len(tables),
            
            # Quality metrics
            "ocr_confidence": ocr_confidence,
            "overall_confidence": confidence_result["overall_confidence"],
            "confidence_breakdown": confidence_result["confidence_breakdown"],
            "reliability_score": confidence_result["reliability_score"],
            
            # Validation
            "validation": validation_report,
            "is_valid": validation_report.get("valid", True),
            
            # Metadata
            "extraction_method": "advanced_intelligence_pipeline",
            "pipeline_version": "2.0",
            "error": None,
        }
        
        logger.info(f"Pipeline complete. Confidence: {result['overall_confidence']:.1%}, Reliability: {result['reliability_score']}")
        
        return result
        
    except ImportError as e:
        logger.warning(f"Document intelligence modules not available: {e}. Falling back to basic extraction.")
        return parse_financial_document(file_path, doc_type)
    except Exception as e:
        logger.error(f"Error in advanced pipeline: {e}. Falling back to basic extraction.")
        return parse_financial_document(file_path, doc_type)


# ─── Core Extraction ──────────────────────────────────────────────────────────

def extract_text_pymupdf(file_path: str) -> str:
    """Extract plain text from every page of a PDF using PyMuPDF."""
    doc = fitz.open(file_path)
    pages_text: List[str] = []
    for page in doc:
        pages_text.append(page.get_text("text"))
    doc.close()
    return "\n".join(pages_text)


def extract_tables_pdfplumber(file_path: str) -> List[List[List[str | None]]]:
    """Extract all tables from a PDF using pdfplumber."""
    tables: List[List[List[str | None]]] = []
    try:
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                page_tables = page.extract_tables()
                if page_tables:
                    tables.extend(page_tables)
    except Exception:
        pass
    # Limit to avoid bloating the LLM context
    return tables[:25]


def _clean_table(table: List[List[str | None]]) -> List[List[str]]:
    """Replace None cells with empty strings."""
    return [[cell or "" for cell in row] for row in table]


def table_to_text(table: List[List[str | None]]) -> str:
    """Convert a table (list of rows) to a readable Markdown-like string."""
    cleaned = _clean_table(table)
    if not cleaned:
        return ""
    col_widths = [
        max(len(str(row[i])) for row in cleaned if i < len(row))
        for i in range(len(cleaned[0]))
    ]
    lines: List[str] = []
    for idx, row in enumerate(cleaned):
        cells = [str(row[i]).ljust(col_widths[i]) if i < len(row) else " " * col_widths[i]
                 for i in range(len(cleaned[0]))]
        lines.append(" | ".join(cells))
        if idx == 0:
            lines.append("-+-".join("-" * w for w in col_widths))
    return "\n".join(lines)


# ─── Document Parser ──────────────────────────────────────────────────────────

def parse_financial_document(file_path: str, doc_type: str) -> Dict[str, Any]:
    """
    Parse a financial document (PDF) and return structured payload.

    Returns a dict with text, tables-as-text, page count, and metadata.
    Text is capped at 40 000 chars to stay within LLM context limits.
    """
    try:
        raw_text = extract_text_pymupdf(file_path)
        tables = extract_tables_pdfplumber(file_path)

        tables_text = "\n\n".join(table_to_text(t) for t in tables if t)

        doc = fitz.open(file_path)
        page_count = doc.page_count
        doc.close()

        return {
            "file_path": file_path,
            "file_name": Path(file_path).name,
            "doc_type": doc_type,
            "text": raw_text[:40_000],
            "tables_text": tables_text[:10_000],
            "page_count": page_count,
            "error": None,
        }
    except Exception as exc:
        return {
            "file_path": file_path,
            "file_name": Path(file_path).name,
            "doc_type": doc_type,
            "text": f"[Error parsing document: {exc}]",
            "tables_text": "",
            "page_count": 0,
            "error": str(exc),
        }


# ─── Numeric Extractor (fallback / supplement) ────────────────────────────────

_MONEY_UNIT = r"(?:cr(?:ore)?s?|lakh(?:s)?|million|mn|bn|billion)?"
_MONEY_RE = re.compile(
    r"(?:Rs\.?|INR|₹)?\s*([\d,]+(?:\.\d+)?)\s*" + _MONEY_UNIT,
    re.IGNORECASE,
)

_FIELD_PATTERNS: Dict[str, str] = {
    "revenue":    r"(?:revenue|turnover|net sales|total income)",
    "ebitda":     r"(?:ebitda|operating profit)",
    "pat":        r"(?:pat|profit after tax|net profit|net income)",
    "total_debt": r"(?:total debt|total borrowings|long.term debt)",
    "net_worth":  r"(?:net worth|shareholders.? equity|book value)",
    "dscr":       r"dscr",
    "d_to_e":     r"(?:debt.to.equity|d/e ratio)",
}


def extract_financial_numbers(text: str) -> Dict[str, float]:
    """
    Quick regex fallback to pull key financial numbers from raw text.
    Values are returned in the unit stated — caller must normalise to Crore INR.
    """
    extracted: Dict[str, float] = {}
    text_lower = text.lower()
    for key, field_re in _FIELD_PATTERNS.items():
        pattern = re.compile(
            rf"{field_re}\s*[:\-–]?\s*(?:Rs\.?|INR|₹)?\s*([\d,]+(?:\.\d+)?)",
            re.IGNORECASE,
        )
        match = pattern.search(text_lower)
        if match:
            try:
                extracted[key] = float(match.group(1).replace(",", ""))
            except ValueError:
                pass
    return extracted


def format_documents_for_llm(documents: List[Dict[str, Any]]) -> str:
    """
    Concatenate all parsed documents into a single string for the LLM prompt.
    Each document is prefixed with a header identifying the doc type.
    """
    parts: List[str] = []
    for doc in documents:
        header = f"=== {doc.get('doc_type', 'DOCUMENT').upper()} | {doc.get('file_name', '')} ==="
        body = doc.get("text", "")
        tables = doc.get("tables_text", "")
        section = f"{header}\n{body}"
        if tables:
            section += f"\n\n--- TABLES ---\n{tables}"
        parts.append(section)
    return "\n\n".join(parts)
