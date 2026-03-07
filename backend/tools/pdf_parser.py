"""
PDF parsing utilities using PyMuPDF and pdfplumber.
Extracts text and tables from uploaded financial documents.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List

import fitz  # PyMuPDF
import pdfplumber


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
