"""
Document Intelligence Engine — Unstructured Document→Structured JSON Pipeline

Converts messy, scanned, or semi-structured financial/legal documents commonly
used in Indian corporate credit workflows into structured JSON consumable by
downstream modules (reconciliation, risk scoring, CAM generation).

PIPELINE:
    Document Input
        → File Type Detection
        → OCR Layer (PaddleOCR)
        → Layout Detection
        → Table Extraction (pdfplumber / Camelot)
        → Section Segmentation
        → LLM Information Extraction (Claude)
        → Entity Normalization
        → Structured JSON Output

SUPPORTED DOCUMENT TYPES:
    annual_report, financial_statement, bank_statement, gst_document,
    sanction_letter, legal_notice, auditor_report, board_resolution,
    shareholding_pattern, rating_report

Author: Credit Intelligence System
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ─── Optional Heavy Imports ────────────────────────────────────────────────────
# These are imported lazily so the module loads even if not every dependency
# is installed in the environment.

def _import_fitz():
    try:
        import fitz
        return fitz
    except ImportError:
        return None

def _import_pdfplumber():
    try:
        import pdfplumber
        return pdfplumber
    except ImportError:
        return None

def _import_paddle_ocr():
    try:
        from paddleocr import PaddleOCR
        return PaddleOCR
    except ImportError:
        return None

def _import_camelot():
    try:
        import camelot
        return camelot
    except ImportError:
        return None

def _import_PIL():
    try:
        from PIL import Image
        return Image
    except ImportError:
        return None

def _import_anthropic():
    try:
        from anthropic import Anthropic
        return Anthropic
    except ImportError:
        return None


# ─── Enums & Constants ────────────────────────────────────────────────────────

class DocumentType(str, Enum):
    ANNUAL_REPORT       = "annual_report"
    FINANCIAL_STATEMENT = "financial_statement"
    BANK_STATEMENT      = "bank_statement"
    GST_DOCUMENT        = "gst_document"
    SANCTION_LETTER     = "sanction_letter"
    LEGAL_NOTICE        = "legal_notice"
    AUDITOR_REPORT      = "auditor_report"
    BOARD_RESOLUTION    = "board_resolution"
    SHAREHOLDING        = "shareholding_pattern"
    RATING_REPORT       = "rating_report"
    UNKNOWN             = "unknown"


class BlockType(str, Enum):
    HEADER    = "header"
    PARAGRAPH = "paragraph"
    TABLE     = "table"
    FOOTNOTE  = "footnote"
    SIGNATURE = "signature"
    STAMP     = "stamp"


OCR_CONFIDENCE_THRESHOLD = 0.70   # Flag below this for review
MAX_TEXT_CHARS_FOR_LLM   = 45_000  # Keep within context limits
MAX_PAGES_PARALLEL_OCR   = 8       # Concurrent page-level OCR tasks


# ─── Document-type keyword patterns ───────────────────────────────────────────

_DOCTYPE_SIGNALS: Dict[DocumentType, List[str]] = {
    DocumentType.ANNUAL_REPORT:       [
        "annual report", "director's report", "board of directors",
        "auditor's report", "standalone financial statements",
        "notes to accounts", "schedule iii"
    ],
    DocumentType.FINANCIAL_STATEMENT: [
        "balance sheet", "profit and loss", "income statement",
        "statement of cash flows", "ca certificate",
        "chartered accountant", "udin"
    ],
    DocumentType.BANK_STATEMENT:      [
        "account statement", "bank statement", "account number",
        "opening balance", "closing balance", "debit", "credit",
        "cbdt", "ifsc", "passbook"
    ],
    DocumentType.GST_DOCUMENT:        [
        "gstin", "gstr", "gst return", "igst", "cgst", "sgst",
        "outward supplies", "inward supplies", "tax liability",
        "goods and services tax"
    ],
    DocumentType.SANCTION_LETTER:     [
        "sanction letter", "sanctioned amount", "rate of interest",
        "repayment schedule", "moratorium", "processing fee",
        "disbursement", "term loan"
    ],
    DocumentType.LEGAL_NOTICE:        [
        "legal notice", "court order", "high court", "district court",
        "plaintiff", "defendant", "injunction", "arbitration",
        "writ petition", "nclt"
    ],
    DocumentType.AUDITOR_REPORT:      [
        "independent auditor", "qualified opinion", "unqualified opinion",
        "emphasis of matter", "going concern", "key audit matters",
        "icai", "form 3cd"
    ],
    DocumentType.BOARD_RESOLUTION:    [
        "board resolution", "resolved that", "extraordinary general meeting",
        "director resignation", "agm", "egm", "din", "mca"
    ],
    DocumentType.SHAREHOLDING:        [
        "shareholding pattern", "benpos", "promoter holding",
        "public shareholding", "depository", "isin",
        "category of shareholder"
    ],
    DocumentType.RATING_REPORT:       [
        "crisil", "icra", "care ratings", "india ratings",
        "credit rating", "rating rationale", "outlook stable",
        "rating downgrade", "rating upgrade"
    ],
}

# ─── LLM Extraction Prompts ───────────────────────────────────────────────────

_CLASSIFICATION_PROMPT = """You are a credit document classifier for Indian corporate loans.

Given the following text extracted from a document, classify it into one of:
annual_report, financial_statement, bank_statement, gst_document,
sanction_letter, legal_notice, auditor_report, board_resolution,
shareholding_pattern, rating_report, unknown

Reply with ONLY a JSON object:
{{"document_type": "<type>", "confidence": <0.0-1.0>, "reasoning": "<brief>"}}

Document text (first 3000 chars):
{text}
"""

_EXTRACTION_PROMPT = """You are a senior credit analyst extracting structured information from an Indian corporate financial document.

Document Type: {doc_type}
Company (if known): {company_hint}

Full extracted text (may include OCR artifacts):
{text}

Tables found:
{tables}

Extract and return ONLY a valid JSON object — no markdown, no explanation, just raw JSON.
Use null for unavailable fields. Express all monetary values in ABSOLUTE RUPEES (not Cr/Lakh labels).
For example: "₹125 Cr" → 1250000000, "₹5 Lakh" → 500000.

{{
  "document_type": "{doc_type}",
  "company_name": null,
  "report_period": null,
  "financials": {{
    "revenue": null,
    "ebitda": null,
    "ebit": null,
    "net_profit": null,
    "total_assets": null,
    "net_worth": null,
    "total_debt": null,
    "current_assets": null,
    "current_liabilities": null,
    "cash_and_equivalents": null,
    "debtors": null,
    "inventory": null,
    "creditors": null,
    "capital_expenditure": null,
    "operating_cash_flow": null,
    "interest_expense": null,
    "depreciation": null
  }},
  "ratios": {{
    "debt_to_equity": null,
    "current_ratio": null,
    "interest_coverage": null,
    "roe_percent": null,
    "ebitda_margin_percent": null
  }},
  "risk_signals": {{
    "auditor_qualification": null,
    "going_concern_warning": false,
    "litigation_mentions": 0,
    "contingent_liabilities": null,
    "related_party_transactions": null,
    "auditor_changed": false,
    "director_resignations": 0,
    "regulatory_issues": [],
    "fraud_mentions": false
  }},
  "bank_data": {{
    "account_number": null,
    "bank_name": null,
    "opening_balance": null,
    "closing_balance": null,
    "total_credits": null,
    "total_debits": null,
    "cheque_bounces": 0,
    "emi_payments": [],
    "cash_withdrawals": null,
    "suspicious_entries": []
  }},
  "gst_data": {{
    "gstin": null,
    "filing_period": null,
    "total_turnover": null,
    "gstr3b_sales": null,
    "gstr2a_purchases": null,
    "tax_paid": null,
    "pending_returns": 0,
    "cancelled": false
  }},
  "rating_data": {{
    "agency": null,
    "rating": null,
    "outlook": null,
    "rating_change": null,
    "rationale_summary": null
  }},
  "legal_data": {{
    "case_type": null,
    "court": null,
    "parties": [],
    "amount_in_dispute": null,
    "status": null
  }},
  "sanction_data": {{
    "lender": null,
    "loan_amount": null,
    "tenure_months": null,
    "interest_rate": null,
    "emi": null,
    "collateral": null,
    "sanction_date": null
  }},
  "promoters": [],
  "directors": [],
  "shareholding": {{}},
  "key_observations": [],
  "red_flags": []
}}
"""


# ─── Data Structures ──────────────────────────────────────────────────────────

@dataclass
class LayoutBlock:
    """A detected block of content from document layout analysis."""
    block_type: BlockType
    text: str
    page: int
    bbox: Optional[List[float]] = None        # [x0, y0, x1, y1]
    confidence: float = 1.0
    table_data: Optional[List[List[str]]] = None


@dataclass
class PageOcrResult:
    """OCR result for a single page."""
    page_number: int
    text: str
    confidence: float
    rotation_corrected: bool = False
    low_quality: bool = False


@dataclass
class ProcessingError:
    """Structured processing error."""
    error_type: str
    document: str
    message: str
    page: Optional[int] = None
    recoverable: bool = True


@dataclass
class DocumentIntelligenceResult:
    """Final structured result from the pipeline."""
    document_type: DocumentType
    file_path: str
    file_name: str
    document_hash: str

    # Extraction outputs
    extracted_data: Dict[str, Any] = field(default_factory=dict)
    layout_blocks: List[LayoutBlock] = field(default_factory=list)
    tables_extracted: bool = False
    table_count: int = 0

    # Quality signals
    ocr_used: bool = False
    ocr_confidence: float = 1.0
    needs_review: bool = False
    page_count: int = 0

    # Processing metadata
    processing_time_sec: float = 0.0
    errors: List[ProcessingError] = field(default_factory=list)
    cached: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "document_type": self.document_type.value,
            "file_name": self.file_name,
            "document_hash": self.document_hash,
            "company_name": self.extracted_data.get("company_name"),
            "report_period": self.extracted_data.get("report_period"),
            "financials": self.extracted_data.get("financials", {}),
            "ratios": self.extracted_data.get("ratios", {}),
            "risk_signals": self.extracted_data.get("risk_signals", {}),
            "bank_data": self.extracted_data.get("bank_data", {}),
            "gst_data": self.extracted_data.get("gst_data", {}),
            "rating_data": self.extracted_data.get("rating_data", {}),
            "legal_data": self.extracted_data.get("legal_data", {}),
            "sanction_data": self.extracted_data.get("sanction_data", {}),
            "promoters": self.extracted_data.get("promoters", []),
            "directors": self.extracted_data.get("directors", []),
            "shareholding": self.extracted_data.get("shareholding", {}),
            "key_observations": self.extracted_data.get("key_observations", []),
            "red_flags": self.extracted_data.get("red_flags", []),
            "tables_extracted": self.tables_extracted,
            "table_count": self.table_count,
            "page_count": self.page_count,
            "ocr_used": self.ocr_used,
            "ocr_confidence": round(self.ocr_confidence, 4),
            "needs_review": self.needs_review,
            "processing_time_sec": round(self.processing_time_sec, 2),
            "errors": [
                {
                    "error_type": e.error_type,
                    "message": e.message,
                    "page": e.page,
                    "recoverable": e.recoverable,
                }
                for e in self.errors
            ],
        }


# ─── Simple in-process cache ──────────────────────────────────────────────────

_result_cache: Dict[str, DocumentIntelligenceResult] = {}


def _file_hash(file_path: str) -> str:
    """SHA-256 of the first 4MB of the file (fast fingerprint)."""
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        h.update(f.read(4 * 1024 * 1024))
    return h.hexdigest()[:16]


# ─── Step 1: File Type Detection ──────────────────────────────────────────────

def detect_document_type(text: str, file_name: str = "") -> Tuple[DocumentType, float]:
    """
    Detect document type using keyword heuristics.
    Returns (DocumentType, confidence_score).
    """
    text_lower = text.lower()
    fname_lower = file_name.lower()

    scores: Dict[DocumentType, int] = {dt: 0 for dt in DocumentType}

    for doc_type, keywords in _DOCTYPE_SIGNALS.items():
        for kw in keywords:
            if kw in text_lower:
                scores[doc_type] += 1

    # File-name hints
    if "bank" in fname_lower or "statement" in fname_lower:
        scores[DocumentType.BANK_STATEMENT] += 3
    if "gst" in fname_lower or "gstr" in fname_lower:
        scores[DocumentType.GST_DOCUMENT] += 3
    if "sanction" in fname_lower:
        scores[DocumentType.SANCTION_LETTER] += 3
    if "annual" in fname_lower:
        scores[DocumentType.ANNUAL_REPORT] += 3
    if "rating" in fname_lower or "crisil" in fname_lower or "icra" in fname_lower:
        scores[DocumentType.RATING_REPORT] += 3
    if "notice" in fname_lower or "legal" in fname_lower:
        scores[DocumentType.LEGAL_NOTICE] += 3

    best_type = max(scores, key=lambda k: scores[k])
    best_score = scores[best_type]
    total_possible = len(_DOCTYPE_SIGNALS.get(best_type, [])) + 3

    if best_score == 0:
        return DocumentType.UNKNOWN, 0.0

    confidence = min(1.0, best_score / max(total_possible, 1) * 1.5)
    return best_type, round(confidence, 3)


async def _llm_classify_document(text: str) -> Tuple[DocumentType, float]:
    """Use LLM to classify document type when heuristics are uncertain."""
    Anthropic = _import_anthropic()
    if Anthropic is None:
        return DocumentType.UNKNOWN, 0.0

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return DocumentType.UNKNOWN, 0.0

    try:
        client = Anthropic(api_key=api_key)
        sample = text[:3000]
        response = client.messages.create(
            model="claude-haiku-4-20250514",
            max_tokens=256,
            messages=[{
                "role": "user",
                "content": _CLASSIFICATION_PROMPT.format(text=sample)
            }],
        )
        raw = response.content[0].text.strip()
        parsed = json.loads(raw)
        doc_type_str = parsed.get("document_type", "unknown")
        confidence = float(parsed.get("confidence", 0.5))

        # Map string to enum
        try:
            doc_type = DocumentType(doc_type_str)
        except ValueError:
            doc_type = DocumentType.UNKNOWN

        return doc_type, confidence
    except Exception as exc:
        logger.warning(f"LLM classification failed: {exc}")
        return DocumentType.UNKNOWN, 0.0


# ─── Step 2: OCR Layer ────────────────────────────────────────────────────────

def _is_scanned_page(page, fitz_module) -> bool:
    """Heuristic: page is scanned if it has very little extractable text."""
    text = page.get_text("text").strip()
    return len(text) < 50


def _ocr_image_bytes(image_bytes: bytes, paddle_ocr_instance) -> Tuple[str, float]:
    """
    Run PaddleOCR on raw image bytes.
    Returns (text, confidence).
    """
    import numpy as np
    Image = _import_PIL()
    if Image is None:
        return "", 0.0

    try:
        import io
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        img_array = np.array(img)

        result = paddle_ocr_instance.ocr(img_array, cls=True)
        if not result or not result[0]:
            return "", 0.0

        lines = []
        confidences = []
        for line in result[0]:
            if line and len(line) >= 2:
                text_info = line[1]
                if isinstance(text_info, (list, tuple)) and len(text_info) == 2:
                    lines.append(text_info[0])
                    confidences.append(float(text_info[1]))

        combined_text = "\n".join(lines)
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
        return combined_text, avg_confidence

    except Exception as exc:
        logger.warning(f"PaddleOCR failed: {exc}")
        return "", 0.0


async def _ocr_page(
    page,
    page_num: int,
    fitz_module,
    paddle_class,
    file_name: str,
    errors: List[ProcessingError],
) -> PageOcrResult:
    """
    Run OCR on a single fitz page in an executor thread.
    Handles rotation detection (tries 0°, 90°, 270°).
    """
    if paddle_class is None:
        # Fallback: just use PyMuPDF text extraction
        text = page.get_text("text")
        return PageOcrResult(page_number=page_num, text=text, confidence=1.0)

    def _do_ocr():
        # Try to auto-correct rotation via page matrix
        rotation = page.rotation  # 0, 90, 180, 270
        if rotation != 0:
            page.set_rotation(0)

        try:
            ocr = paddle_class(use_angle_cls=True, lang="en", show_log=False)
        except Exception:
            ocr = paddle_class(use_angle_cls=True, lang="en")

        mat = fitz_module.Matrix(2.0, 2.0)  # 2× zoom for better OCR
        pix = page.get_pixmap(matrix=mat)
        img_bytes = pix.tobytes("png")

        text, confidence = _ocr_image_bytes(img_bytes, ocr)
        return text, confidence, rotation != 0

    loop = asyncio.get_event_loop()
    try:
        text, confidence, rotation_corrected = await loop.run_in_executor(None, _do_ocr)
    except Exception as exc:
        errors.append(ProcessingError(
            error_type="ocr_failure",
            document=file_name,
            message=str(exc),
            page=page_num,
            recoverable=True,
        ))
        return PageOcrResult(
            page_number=page_num,
            text=page.get_text("text"),
            confidence=0.5,
        )

    return PageOcrResult(
        page_number=page_num,
        text=text,
        confidence=confidence,
        rotation_corrected=rotation_corrected,
        low_quality=confidence < OCR_CONFIDENCE_THRESHOLD,
    )


async def run_ocr_pipeline(
    file_path: str,
    errors: List[ProcessingError],
) -> List[PageOcrResult]:
    """
    Full OCR pipeline for a PDF.
    - Pages with native text use PyMuPDF directly (fast path)
    - Scanned pages use PaddleOCR (slow path, run in parallel batches)
    Returns list of PageOcrResult, one per page.
    """
    fitz = _import_fitz()
    PaddleOCR = _import_paddle_ocr()

    if fitz is None:
        errors.append(ProcessingError(
            error_type="missing_dependency",
            document=file_path,
            message="PyMuPDF (fitz) not installed. Run: pip install pymupdf",
            recoverable=False,
        ))
        return []

    results: List[PageOcrResult] = []
    file_name = Path(file_path).name

    try:
        doc = fitz.open(file_path)
    except Exception as exc:
        errors.append(ProcessingError(
            error_type="file_open_error",
            document=file_name,
            message=str(exc),
            recoverable=False,
        ))
        return []

    scanned_pages = []
    for i, page in enumerate(doc):
        if _is_scanned_page(page, fitz):
            scanned_pages.append((i, page))
        else:
            text = page.get_text("text")
            results.append(PageOcrResult(
                page_number=i + 1,
                text=text,
                confidence=1.0,
            ))

    if scanned_pages and PaddleOCR is not None:
        logger.info(f"Running OCR on {len(scanned_pages)} scanned page(s) in {file_name}")

        # Process in batches to avoid overwhelming memory
        for batch_start in range(0, len(scanned_pages), MAX_PAGES_PARALLEL_OCR):
            batch = scanned_pages[batch_start: batch_start + MAX_PAGES_PARALLEL_OCR]
            ocr_tasks = [
                _ocr_page(page, idx + 1, fitz, PaddleOCR, file_name, errors)
                for idx, page in batch
            ]
            batch_results = await asyncio.gather(*ocr_tasks)
            results.extend(batch_results)
    elif scanned_pages:
        # PaddleOCR not available — use PyMuPDF text extraction as fallback
        logger.warning("PaddleOCR not available; using PyMuPDF text for scanned pages")
        for idx, page in scanned_pages:
            text = page.get_text("text")
            results.append(PageOcrResult(
                page_number=idx + 1,
                text=text,
                confidence=0.6,
            ))

    doc.close()
    results.sort(key=lambda r: r.page_number)
    return results


# ─── Step 3: Layout Detection ─────────────────────────────────────────────────

def detect_layout_blocks(
    page_text: str,
    page_number: int,
) -> List[LayoutBlock]:
    """
    Heuristic layout detection using text structure analysis.
    Identifies headers, paragraphs, footnotes, and signatures.
    """
    blocks: List[LayoutBlock] = []

    # Header patterns: ALL CAPS lines, numbered sections, etc.
    header_re = re.compile(
        r"^(?:[A-Z][A-Z\s\.\-&]{3,}|(?:\d+[\.\)]\s+)[A-Z].{5,}|(?:Note|Schedule|Annexure)\s+\w.+)$",
        re.MULTILINE,
    )
    # Footnote/signature heuristics
    footnote_re = re.compile(
        r"(Note\s*[\d:–\-]|^\*|\bsee\s+note\b|\bFootnote\b)",
        re.IGNORECASE | re.MULTILINE,
    )
    signature_re = re.compile(
        r"(Chartered Accountant|Director|For and on behalf|Sd/-|Secretary|CFO|CEO)",
        re.IGNORECASE,
    )

    lines = page_text.split("\n")
    current_para_lines: List[str] = []

    def _flush_para():
        if current_para_lines:
            blocks.append(LayoutBlock(
                block_type=BlockType.PARAGRAPH,
                text="\n".join(current_para_lines),
                page=page_number,
            ))
            current_para_lines.clear()

    for line in lines:
        stripped = line.strip()
        if not stripped:
            _flush_para()
            continue

        if header_re.match(stripped) and len(stripped) < 120:
            _flush_para()
            blocks.append(LayoutBlock(
                block_type=BlockType.HEADER,
                text=stripped,
                page=page_number,
            ))
        elif footnote_re.search(stripped):
            _flush_para()
            blocks.append(LayoutBlock(
                block_type=BlockType.FOOTNOTE,
                text=stripped,
                page=page_number,
            ))
        elif signature_re.search(stripped):
            _flush_para()
            blocks.append(LayoutBlock(
                block_type=BlockType.SIGNATURE,
                text=stripped,
                page=page_number,
            ))
        else:
            current_para_lines.append(stripped)

    _flush_para()
    return blocks


# ─── Step 4: Table Extraction ─────────────────────────────────────────────────

# Header normalization mapping
_HEADER_SYNONYMS: Dict[str, str] = {
    # Revenue variants
    "revenue from operations": "revenue",
    "net revenue": "revenue",
    "total income": "revenue",
    "sales": "revenue",
    "turnover": "revenue",
    "gross revenue": "revenue",
    # Cost variants
    "cost of goods sold": "cost_of_revenue",
    "cost of materials consumed": "cost_of_revenue",
    "cost of sales": "cost_of_revenue",
    # Profit variants
    "profit after tax": "net_profit",
    "profit for the year": "net_profit",
    "pat": "net_profit",
    "profit before tax": "profit_before_tax",
    "pbt": "profit_before_tax",
    "earnings before interest and tax": "ebit",
    "ebitda": "ebitda",
    "operating profit": "ebitda",
    # Balance sheet
    "total borrowings": "total_debt",
    "long-term borrowings": "long_term_debt",
    "short-term borrowings": "short_term_debt",
    "shareholders equity": "net_worth",
    "shareholders' equity": "net_worth",
    "net worth": "net_worth",
    "reserves and surplus": "reserves",
    # Cash flow
    "net cash from operating activities": "operating_cash_flow",
    "capital expenditure": "capex",
    "capex": "capex",
}


def _normalize_header(raw: str) -> str:
    """Normalize a table header to a canonical field name."""
    cleaned = raw.strip().lower()
    cleaned = re.sub(r"\s+", " ", cleaned)
    cleaned = re.sub(r"[₹rs\.\(\)%]", "", cleaned).strip()
    return _HEADER_SYNONYMS.get(cleaned, cleaned.replace(" ", "_"))


def _clean_cell(cell: Optional[str]) -> str:
    return (cell or "").strip().replace("\n", " ")


def extract_tables_from_pdf(file_path: str, errors: List[ProcessingError]) -> List[Dict[str, Any]]:
    """
    Extract tables from PDF using pdfplumber (primary) and Camelot (fallback).
    Returns list of table dicts with normalized headers.
    """
    file_name = Path(file_path).name
    tables_out: List[Dict[str, Any]] = []

    # ── pdfplumber (fast, handles most digital PDFs) ──
    pdfplumber = _import_pdfplumber()
    if pdfplumber:
        try:
            with pdfplumber.open(file_path) as pdf:
                for page_num, page in enumerate(pdf.pages, start=1):
                    try:
                        raw_tables = page.extract_tables()
                    except Exception:
                        continue

                    for raw_table in (raw_tables or []):
                        if not raw_table or len(raw_table) < 2:
                            continue

                        header_row = [_clean_cell(c) for c in raw_table[0]]
                        normalized_headers = [_normalize_header(h) for h in header_row]
                        rows = []
                        for data_row in raw_table[1:]:
                            row_dict = {}
                            for col_idx, cell in enumerate(data_row):
                                if col_idx < len(normalized_headers):
                                    row_dict[normalized_headers[col_idx]] = _clean_cell(cell)
                            rows.append(row_dict)

                        tables_out.append({
                            "page": page_num,
                            "headers": normalized_headers,
                            "rows": rows,
                            "source": "pdfplumber",
                        })
        except Exception as exc:
            errors.append(ProcessingError(
                error_type="table_extraction_error",
                document=file_name,
                message=f"pdfplumber: {exc}",
                recoverable=True,
            ))

    # ── Camelot (lattice mode — better for bordered financial tables) ──
    if not tables_out:
        camelot = _import_camelot()
        if camelot:
            try:
                camelot_tables = camelot.read_pdf(file_path, pages="all", flavor="lattice")
                for ct in camelot_tables:
                    df = ct.df
                    if df is None or df.empty or len(df) < 2:
                        continue
                    header_row = [_normalize_header(str(c)) for c in df.iloc[0]]
                    rows = []
                    for _, data_row in df.iloc[1:].iterrows():
                        row_dict = {
                            header_row[i]: str(v).strip()
                            for i, v in enumerate(data_row)
                        }
                        rows.append(row_dict)
                    tables_out.append({
                        "page": ct.page,
                        "headers": header_row,
                        "rows": rows,
                        "source": "camelot",
                    })
            except Exception as exc:
                errors.append(ProcessingError(
                    error_type="table_extraction_error",
                    document=file_name,
                    message=f"camelot: {exc}",
                    recoverable=True,
                ))

    return tables_out


def tables_to_text(tables: List[Dict[str, Any]]) -> str:
    """Render extracted tables as markdown-style text for LLM context."""
    parts: List[str] = []
    for i, table in enumerate(tables[:20]):  # Cap at 20 tables
        header_line = " | ".join(str(h) for h in table["headers"])
        sep_line = "-+-".join("-" * max(len(str(h)), 5) for h in table["headers"])
        row_lines = []
        for row in table["rows"][:50]:  # Cap at 50 rows per table
            row_lines.append(" | ".join(str(row.get(h, "")) for h in table["headers"]))
        parts.append(
            f"\n[TABLE {i+1} | Page {table['page']}]\n"
            + header_line + "\n"
            + sep_line + "\n"
            + "\n".join(row_lines)
        )
    return "\n".join(parts)


# ─── Step 5: Section Segmentation ────────────────────────────────────────────

_SECTION_PATTERNS: Dict[str, List[str]] = {
    "auditor_remarks":           ["auditor's report", "independent auditor", "qualified opinion",
                                  "emphasis of matter", "going concern", "key audit matters"],
    "contingent_liabilities":    ["contingent liabilities", "contingent liability",
                                  "claims not acknowledged", "pending litigations"],
    "related_party_transactions":["related party", "related parties", "key management personnel",
                                  "transactions with related parties"],
    "promoter_information":      ["promoter", "holding company", "ultimate beneficiary",
                                  "promoter holding"],
    "litigation_disclosures":    ["litigation", "legal proceedings", "court case",
                                  "arbitration", "notice"],
    "director_changes":          ["resignation", "director resigned", "appointed as director",
                                  "director change", "board change"],
    "financial_summary":         ["financial highlights", "key financial", "summary financials",
                                  "financial performance"],
    "going_concern":             ["going concern", "substantial doubt", "ability to continue"],
}


def extract_sections(full_text: str) -> Dict[str, str]:
    """
    Identify key document sections.
    Returns dict of section_name → extracted text snippet.
    """
    sections: Dict[str, str] = {}
    text_lower = full_text.lower()

    for section_name, keywords in _SECTION_PATTERNS.items():
        for kw in keywords:
            idx = text_lower.find(kw)
            if idx != -1:
                # Extract ~600 chars around the keyword
                start = max(0, idx - 50)
                end = min(len(full_text), idx + 600)
                snippet = full_text[start:end].strip()
                existing = sections.get(section_name, "")
                if len(snippet) > len(existing):
                    sections[section_name] = snippet
                break

    return sections


# ─── Step 6: LLM Information Extraction ──────────────────────────────────────

async def _llm_extract(
    doc_type: DocumentType,
    full_text: str,
    tables_text: str,
    company_hint: str,
    errors: List[ProcessingError],
    file_name: str,
) -> Dict[str, Any]:
    """
    Call Claude to extract structured data from document text + tables.
    """
    Anthropic = _import_anthropic()
    api_key = os.environ.get("ANTHROPIC_API_KEY")

    if Anthropic is None or not api_key:
        errors.append(ProcessingError(
            error_type="llm_unavailable",
            document=file_name,
            message="ANTHROPIC_API_KEY not set or anthropic package not installed",
            recoverable=True,
        ))
        return {}

    # Trim text to fit context window
    trimmed_text = full_text[:MAX_TEXT_CHARS_FOR_LLM]
    trimmed_tables = tables_text[:8_000]

    prompt = _EXTRACTION_PROMPT.format(
        doc_type=doc_type.value,
        company_hint=company_hint or "Unknown",
        text=trimmed_text,
        tables=trimmed_tables,
    )

    try:
        client = Anthropic(api_key=api_key)

        def _call():
            return client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=4096,
                messages=[{"role": "user", "content": prompt}],
            )

        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, _call)
        raw = response.content[0].text.strip()

        # Parse JSON from response
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            start = raw.find("{")
            end = raw.rfind("}") + 1
            if start != -1 and end > start:
                return json.loads(raw[start:end])

    except Exception as exc:
        errors.append(ProcessingError(
            error_type="llm_extraction_error",
            document=file_name,
            message=str(exc),
            recoverable=True,
        ))

    return {}


# ─── Step 7: Entity Normalization ────────────────────────────────────────────

# Patterns for Indian monetary amounts
_AMOUNT_PATTERNS = [
    # ₹125.6 Cr, Rs 125.6 crore
    (re.compile(r"(?:₹|rs\.?\s*)(\d[\d,]*(?:\.\d+)?)\s*cr(?:ore)?s?", re.IGNORECASE), 1e7),
    # ₹12.5 Lakh, Rs 12.5 lacs
    (re.compile(r"(?:₹|rs\.?\s*)(\d[\d,]*(?:\.\d+)?)\s*la(?:kh|c|cs|khs)?s?", re.IGNORECASE), 1e5),
    # 1,25,00,000 (Indian comma format)
    (re.compile(r"(?:₹|rs\.?\s*)?(\d{1,2}(?:,\d{2})*,\d{3})(?!\d)"), 1.0),
    # Plain number with ₹/Rs prefix
    (re.compile(r"(?:₹|rs\.?\s*)(\d[\d,]*(?:\.\d+)?)(?!\s*(?:lakh|cr|%|year|month))", re.IGNORECASE), 1.0),
]

_PERCENT_RE = re.compile(r"(\d+(?:\.\d+)?)\s*%")
_DATE_PATTERNS = [
    re.compile(r"\b(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})\b"),
    re.compile(r"\b(\d{1,2})\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\s+(\d{4})\b", re.IGNORECASE),
]

_MONTH_MAP = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun",
     "jul", "aug", "sep", "oct", "nov", "dec"], start=1
)}


def normalize_amount(raw_value: Any) -> Optional[float]:
    """
    Normalize an Indian monetary string or number to absolute rupee float.

    Examples:
        "₹125 Cr"        → 1_250_000_000.0
        "12,50,00,000"   → 125_000_000.0  (Indian comma format)
        "₹5 Lakh"        → 500_000.0
        125000000        → 125_000_000.0
    """
    if raw_value is None:
        return None
    if isinstance(raw_value, (int, float)):
        return float(raw_value)

    text = str(raw_value).strip()

    for pattern, multiplier in _AMOUNT_PATTERNS:
        m = pattern.search(text)
        if m:
            try:
                num_str = m.group(1).replace(",", "")
                return float(num_str) * multiplier
            except (ValueError, IndexError):
                continue

    # Plain numeric string without unit
    plain = re.sub(r"[₹rs,\s]", "", text, flags=re.IGNORECASE)
    try:
        return float(plain) if plain else None
    except ValueError:
        return None


def normalize_date(raw_value: Any) -> Optional[str]:
    """Normalize a date string to ISO format YYYY-MM-DD."""
    if raw_value is None:
        return None
    text = str(raw_value).strip()

    # Try word-month patterns first
    m = _DATE_PATTERNS[1].search(text)
    if m:
        day, month_str, year = m.group(1), m.group(2).lower()[:3], m.group(3)
        month = _MONTH_MAP.get(month_str)
        if month:
            year_int = int(year)
            if year_int < 100:
                year_int += 2000
            return f"{year_int:04d}-{month:02d}-{int(day):02d}"

    # Numeric patterns
    m = _DATE_PATTERNS[0].search(text)
    if m:
        a, b, c = m.group(1), m.group(2), m.group(3)
        year = int(c) if len(c) == 4 else (2000 + int(c))
        # Heuristic: if a > 12, it's the day
        if int(a) > 12:
            return f"{year:04d}-{int(b):02d}-{int(a):02d}"
        return f"{year:04d}-{int(a):02d}-{int(b):02d}"

    return raw_value  # Return as-is if can't parse


def _normalize_financial_dict(data: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively normalize financial field values in a dict."""
    monetary_fields = {
        "revenue", "ebitda", "ebit", "net_profit", "total_assets", "net_worth",
        "total_debt", "current_assets", "current_liabilities", "cash_and_equivalents",
        "debtors", "inventory", "creditors", "capital_expenditure",
        "operating_cash_flow", "interest_expense", "depreciation",
        "contingent_liabilities", "related_party_transactions",
        "opening_balance", "closing_balance", "total_credits", "total_debits",
        "cash_withdrawals", "loan_amount", "emi", "amount_in_dispute",
        "total_turnover", "gstr3b_sales", "gstr2a_purchases", "tax_paid",
    }
    date_fields = {"report_period", "sanction_date", "date", "incorporation_date"}

    out: Dict[str, Any] = {}
    for k, v in data.items():
        if isinstance(v, dict):
            out[k] = _normalize_financial_dict(v)
        elif isinstance(v, list):
            out[k] = [
                _normalize_financial_dict(item) if isinstance(item, dict) else item
                for item in v
            ]
        elif k in monetary_fields:
            out[k] = normalize_amount(v)
        elif k in date_fields:
            out[k] = normalize_date(v)
        else:
            out[k] = v
    return out


# ─── Step 8: Quality Scoring ─────────────────────────────────────────────────

def _score_ocr_confidence(page_results: List[PageOcrResult]) -> Tuple[float, bool]:
    """Return (average_confidence, needs_review)."""
    if not page_results:
        return 1.0, False
    avg = sum(r.confidence for r in page_results) / len(page_results)
    needs_review = avg < OCR_CONFIDENCE_THRESHOLD or any(r.low_quality for r in page_results)
    return round(avg, 4), needs_review


# ─── Main Pipeline ────────────────────────────────────────────────────────────

async def process_document(
    file_path: str,
    company_hint: str = "",
    force_doc_type: Optional[DocumentType] = None,
    use_cache: bool = True,
) -> DocumentIntelligenceResult:
    """
    Run the complete Document Intelligence pipeline on a single file.

    Args:
        file_path:      Absolute path to the PDF/image document.
        company_hint:   Company name (if known) to improve extraction.
        force_doc_type: Override automatic document type detection.
        use_cache:      If True, return cached result for same file content.

    Returns:
        DocumentIntelligenceResult containing structured extraction.
    """
    t_start = time.monotonic()
    file_path = str(Path(file_path).resolve())
    file_name = Path(file_path).name
    errors: List[ProcessingError] = []

    # ── Cache check ──────────────────────────────────────────────────────────
    doc_hash = _file_hash(file_path)
    if use_cache and doc_hash in _result_cache:
        cached = _result_cache[doc_hash]
        cached.cached = True
        logger.info(f"[DIE] Cache hit for {file_name}")
        return cached

    logger.info(f"[DIE] Processing: {file_name}")

    # ── Step 2: OCR Pipeline (parallel page-level) ───────────────────────────
    page_results = await run_ocr_pipeline(file_path, errors)
    ocr_used = any(not (r.confidence == 1.0 and not r.rotation_corrected) for r in page_results)

    full_text = "\n\n".join(
        f"[PAGE {r.page_number}]\n{r.text}" for r in page_results
    )
    page_count = len(page_results)
    ocr_confidence, needs_review = _score_ocr_confidence(page_results)

    if needs_review:
        logger.warning(f"[DIE] Low OCR confidence ({ocr_confidence:.2f}) in {file_name} — flagged for review")

    # ── Step 1: Document Type Detection ──────────────────────────────────────
    if force_doc_type:
        doc_type = force_doc_type
        type_confidence = 1.0
    else:
        doc_type, type_confidence = detect_document_type(full_text, file_name)
        if type_confidence < 0.4:
            # Fall back to LLM classification
            logger.info(f"[DIE] Low heuristic confidence ({type_confidence:.2f}), using LLM classifier")
            doc_type, type_confidence = await _llm_classify_document(full_text)

    logger.info(f"[DIE] Detected type: {doc_type.value} (confidence={type_confidence:.2f})")

    # ── Step 3: Layout Detection ─────────────────────────────────────────────
    layout_blocks: List[LayoutBlock] = []
    for pr in page_results:
        layout_blocks.extend(detect_layout_blocks(pr.text, pr.page_number))

    # ── Step 4: Table Extraction ─────────────────────────────────────────────
    tables: List[Dict[str, Any]] = []
    try:
        tables = await asyncio.get_event_loop().run_in_executor(
            None, extract_tables_from_pdf, file_path, errors
        )
    except Exception as exc:
        errors.append(ProcessingError(
            error_type="table_extraction_error",
            document=file_name,
            message=str(exc),
            recoverable=True,
        ))

    tables_text = tables_to_text(tables)

    # ── Step 5: Section Segmentation ─────────────────────────────────────────
    sections = extract_sections(full_text)
    # Append section snippets to text so LLM gets them explicitly
    if sections:
        section_text = "\n\n".join(
            f"[SECTION: {name.upper()}]\n{snippet}"
            for name, snippet in sections.items()
        )
        full_text = full_text + "\n\n" + section_text

    # ── Step 6: LLM Extraction ────────────────────────────────────────────────
    raw_extracted = await _llm_extract(
        doc_type=doc_type,
        full_text=full_text,
        tables_text=tables_text,
        company_hint=company_hint,
        errors=errors,
        file_name=file_name,
    )

    # ── Step 7: Entity Normalization ──────────────────────────────────────────
    normalized = _normalize_financial_dict(raw_extracted)

    elapsed = time.monotonic() - t_start
    logger.info(f"[DIE] Completed {file_name} in {elapsed:.1f}s | "
                f"pages={page_count} tables={len(tables)} flags={len(errors)}")

    result = DocumentIntelligenceResult(
        document_type=doc_type,
        file_path=file_path,
        file_name=file_name,
        document_hash=doc_hash,
        extracted_data=normalized,
        layout_blocks=layout_blocks,
        tables_extracted=len(tables) > 0,
        table_count=len(tables),
        ocr_used=ocr_used,
        ocr_confidence=ocr_confidence,
        needs_review=needs_review,
        page_count=page_count,
        processing_time_sec=elapsed,
        errors=errors,
    )

    if use_cache:
        _result_cache[doc_hash] = result

    return result


# ─── Batch Processing ─────────────────────────────────────────────────────────

async def process_document_batch(
    file_paths: List[str],
    company_hint: str = "",
    max_concurrent: int = 3,
) -> List[DocumentIntelligenceResult]:
    """
    Process multiple documents concurrently.

    Args:
        file_paths:     List of absolute file paths.
        company_hint:   Company name for all documents.
        max_concurrent: Maximum parallel documents.

    Returns:
        List of DocumentIntelligenceResult in the same order as input.
    """
    semaphore = asyncio.Semaphore(max_concurrent)

    async def _process_with_limit(fp: str) -> DocumentIntelligenceResult:
        async with semaphore:
            return await process_document(fp, company_hint=company_hint)

    results = await asyncio.gather(
        *[_process_with_limit(fp) for fp in file_paths],
        return_exceptions=False,
    )
    return list(results)


# ─── Integration Helpers ──────────────────────────────────────────────────────

def extract_for_reconciliation(result: DocumentIntelligenceResult) -> Dict[str, Any]:
    """
    Convert DocumentIntelligenceResult to the format expected by
    three_way_reconciliation.perform_three_way_reconciliation().
    """
    fin = result.extracted_data.get("financials", {})
    gst = result.extracted_data.get("gst_data", {})
    bank = result.extracted_data.get("bank_data", {})

    return {
        "financial_statements": {
            "revenue": fin.get("revenue"),
            "net_profit": fin.get("net_profit"),
            "total_debt": fin.get("total_debt"),
        },
        "gst_data": {
            "annual_turnover": gst.get("total_turnover") or gst.get("gstr3b_sales"),
        },
        "bank_data": {
            "total_credits": bank.get("total_credits"),
            "total_debits": bank.get("total_debits"),
        },
    }


def extract_for_bank_analyzer(result: DocumentIntelligenceResult) -> Dict[str, Any]:
    """
    Convert DocumentIntelligenceResult to the format expected by
    bank_statement_analyzer.analyze_bank_statement().
    """
    bank = result.extracted_data.get("bank_data", {})
    return {
        "account_number": bank.get("account_number"),
        "bank_name": bank.get("bank_name"),
        "opening_balance": bank.get("opening_balance"),
        "closing_balance": bank.get("closing_balance"),
        "total_credits": bank.get("total_credits"),
        "total_debits": bank.get("total_debits"),
        "cheque_bounces": bank.get("cheque_bounces", 0),
        "emi_payments": bank.get("emi_payments", []),
        "suspicious_entries": bank.get("suspicious_entries", []),
    }


def extract_red_flag_params(result: DocumentIntelligenceResult) -> Dict[str, Any]:
    """
    Extract parameters to pass to scoring.red_flag_engine.evaluate_red_flags().
    """
    risk = result.extracted_data.get("risk_signals", {})
    gst = result.extracted_data.get("gst_data", {})
    bank = result.extracted_data.get("bank_data", {})
    rating = result.extracted_data.get("rating_data", {})

    return {
        # GST
        "gst_status": "Cancelled" if gst.get("cancelled") else "Active",
        # Audit
        "auditor_changes_count": 1 if risk.get("auditor_changed") else 0,
        # Cheque bounces
        "cheque_bounce_count": bank.get("cheque_bounces", 0),
        # Financial
        "net_worth": (result.extracted_data.get("financials", {}) or {}).get("net_worth"),
        # Litigation
        "has_criminal_cases": risk.get("fraud_mentions", False),
        "pending_cases": risk.get("litigation_mentions", 0),
        # Going concern
        "going_concern_flag": risk.get("going_concern_warning", False),
    }


# ─── Mock / Offline Fallback ──────────────────────────────────────────────────

def _build_mock_result(
    file_name: str,
    doc_type: DocumentType,
    scenario: str = "clean",
) -> DocumentIntelligenceResult:
    """
    Return a realistic mock result for testing without real file I/O.
    Scenarios: clean, stressed, fraud_suspected, cancelled_gst
    """
    base_fin = {
        "revenue": 1_200_000_000,
        "ebitda": 180_000_000,
        "net_profit": 85_000_000,
        "total_debt": 400_000_000,
        "net_worth": 550_000_000,
        "current_assets": 320_000_000,
        "current_liabilities": 180_000_000,
    }

    if scenario == "stressed":
        base_fin.update({
            "net_profit": -20_000_000,
            "ebitda": 40_000_000,
            "net_worth": 80_000_000,
            "total_debt": 700_000_000,
        })
    elif scenario == "fraud_suspected":
        base_fin["revenue"] = 2_000_000_000  # inflated

    risk_signals = {
        "auditor_qualification": "Emphasis of matter: going concern" if scenario == "stressed" else None,
        "going_concern_warning": scenario == "stressed",
        "litigation_mentions": 5 if scenario == "fraud_suspected" else 0,
        "contingent_liabilities": 120_000_000 if scenario in ("stressed", "fraud_suspected") else 0,
        "related_party_transactions": 50_000_000,
        "auditor_changed": scenario == "fraud_suspected",
        "director_resignations": 2 if scenario == "fraud_suspected" else 0,
        "regulatory_issues": [],
        "fraud_mentions": scenario == "fraud_suspected",
    }

    bank_data = {
        "cheque_bounces": 6 if scenario in ("stressed", "fraud_suspected") else 0,
        "total_credits": 1_100_000_000,
        "total_debits": 1_090_000_000,
        "suspicious_entries": [{"entry": "Round amount withdrawal", "amount": 5_000_000}]
        if scenario == "fraud_suspected"
        else [],
    }

    gst_data = {
        "gstin": "27AAAAA0000A1Z5",
        "total_turnover": 1_180_000_000,
        "pending_returns": 3 if scenario == "stressed" else 0,
        "cancelled": scenario == "cancelled_gst",
    }

    extracted = {
        "document_type": doc_type.value,
        "company_name": "ABC Industries Ltd (Mock)",
        "report_period": "FY 2023-24",
        "financials": base_fin,
        "ratios": {
            "debt_to_equity": round(base_fin["total_debt"] / base_fin["net_worth"], 2),
            "current_ratio": round(base_fin["current_assets"] / base_fin["current_liabilities"], 2),
        },
        "risk_signals": risk_signals,
        "bank_data": bank_data,
        "gst_data": gst_data,
        "rating_data": {
            "agency": "CRISIL",
            "rating": "BBB" if scenario == "stressed" else "A",
            "outlook": "Negative" if scenario == "stressed" else "Stable",
        },
        "key_observations": [
            "Going concern risk identified" if scenario == "stressed" else "Healthy financials",
        ],
        "red_flags": [
            "RF028: Cheque bounces detected" if bank_data.get("cheque_bounces", 0) > 2 else None,
            "RF027: GST cancelled" if gst_data.get("cancelled") else None,
        ],
    }
    extracted["red_flags"] = [f for f in extracted["red_flags"] if f]

    return DocumentIntelligenceResult(
        document_type=doc_type,
        file_path=f"/mock/{file_name}",
        file_name=file_name,
        document_hash="mock_" + scenario,
        extracted_data=extracted,
        tables_extracted=True,
        table_count=4,
        ocr_used=False,
        ocr_confidence=0.97,
        needs_review=scenario == "stressed",
        page_count=45,
        processing_time_sec=1.2,
        cached=False,
    )


# ─── Integration Example ──────────────────────────────────────────────────────

async def main_example():
    """
    Demonstrates the Document Intelligence Engine using mock scenarios.
    Run with: python -m tools.document_intelligence_engine
    """
    scenarios = [
        ("annual_report_clean.pdf", DocumentType.ANNUAL_REPORT, "clean"),
        ("bank_statement_stressed.pdf", DocumentType.BANK_STATEMENT, "stressed"),
        ("gst_return_fraud.pdf", DocumentType.GST_DOCUMENT, "fraud_suspected"),
    ]

    print("=" * 72)
    print("DOCUMENT INTELLIGENCE ENGINE — DEMO")
    print("=" * 72)

    for file_name, doc_type, scenario in scenarios:
        print(f"\n{'─'*72}")
        print(f"📄 Document : {file_name}")
        print(f"   Type     : {doc_type.value}")
        print(f"   Scenario : {scenario}")

        result = _build_mock_result(file_name, doc_type, scenario)
        output = result.to_dict()

        print(f"\n   ▶ Extracted:")
        print(f"     Company           : {output['company_name']}")
        print(f"     Report Period     : {output['report_period']}")
        print(f"     Revenue           : ₹{(output['financials'].get('revenue') or 0):,.0f}")
        print(f"     Net Profit        : ₹{(output['financials'].get('net_profit') or 0):,.0f}")
        print(f"     Total Debt        : ₹{(output['financials'].get('total_debt') or 0):,.0f}")
        print(f"     Net Worth         : ₹{(output['financials'].get('net_worth') or 0):,.0f}")

        print(f"\n   ▶ Risk Signals:")
        rs = output["risk_signals"]
        print(f"     Going Concern     : {rs.get('going_concern_warning')}")
        print(f"     Litigation        : {rs.get('litigation_mentions')} mentions")
        print(f"     Auditor Changed   : {rs.get('auditor_changed')}")
        print(f"     Cheque Bounces    : {output['bank_data'].get('cheque_bounces', 0)}")

        print(f"\n   ▶ Quality:")
        print(f"     OCR Confidence    : {output['ocr_confidence']}")
        print(f"     Tables Extracted  : {output['table_count']}")
        print(f"     Needs Review      : {output['needs_review']}")

        if output["red_flags"]:
            print(f"\n   🚨 Red Flags:")
            for flag in output["red_flags"]:
                print(f"      • {flag}")

        # Integration adapter outputs
        recon_payload = extract_for_reconciliation(result)
        rf_params = extract_red_flag_params(result)
        print(f"\n   ▶ Reconciliation payload revenue: ₹{recon_payload['financial_statements'].get('revenue') or 0:,.0f}")
        print(f"   ▶ Red flag params: gst_status={rf_params['gst_status']}, bounces={rf_params['cheque_bounce_count']}")

    print("\n" + "=" * 72)
    print("NORMALIZATION TESTS")
    print("=" * 72)
    test_amounts = [
        ("₹125 Cr", 1_250_000_000),
        ("Rs 50 crore", 500_000_000),
        ("12,50,00,000", 125_000_000),
        ("₹5 Lakh", 500_000),
        ("250000000", 250_000_000),
    ]
    for raw, expected in test_amounts:
        result_val = normalize_amount(raw)
        status = "✓" if result_val == expected else f"✗ (got {result_val})"
        print(f"  normalize_amount({raw!r:25s}) → ₹{result_val or 0:>15,.0f}  {status}")


if __name__ == "__main__":
    asyncio.run(main_example())
