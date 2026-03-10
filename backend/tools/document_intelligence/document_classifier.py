"""
Document Classifier Module
Automatically detects the type of financial document.
"""
from __future__ import annotations

import logging
import re
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# Document type keywords (case-insensitive)
DOCUMENT_PATTERNS = {
    "annual_report": [
        r"annual\s+report",
        r"balance\s+sheet",
        r"profit\s+and\s+loss",
        r"p\s*&\s*l\s+statement",
        r"financial\s+statements",
        r"income\s+statement",
        r"cash\s+flow\s+statement",
        r"notes\s+to\s+accounts",
        r"auditor'?s\s+report",
    ],
    "bank_statement": [
        r"bank\s+statement",
        r"account\s+statement",
        r"transaction\s+summary",
        r"opening\s+balance",
        r"closing\s+balance",
        r"statement\s+of\s+account",
        r"customer\s+id",
        r"account\s+number",
    ],
    "gst_filing": [
        r"gstr[-\s]?[123][ab]?",
        r"gstin",
        r"goods\s+and\s+services\s+tax",
        r"input\s+tax\s+credit",
        r"output\s+tax",
        r"tax\s+invoice",
        r"igst|cgst|sgst",
        r"return\s+filing",
    ],
    "rating_report": [
        r"crisil",
        r"icra",
        r"care\s+ratings?",
        r"india\s+ratings",
        r"credit\s+rating",
        r"rating\s+rationale",
        r"rating\s+action",
        r"outlook\s*:\s*(stable|positive|negative)",
        r"long[- ]term\s+rating",
        r"short[- ]term\s+rating",
    ],
    "legal_notice": [
        r"legal\s+notice",
        r"show\s+cause\s+notice",
        r"summons",
        r"court\s+order",
        r"writ\s+petition",
        r"arbitration",
        r"litigation",
        r"plaintiff",
        r"defendant",
    ],
    "sanction_letter": [
        r"sanction\s+letter",
        r"loan\s+approval",
        r"credit\s+facility",
        r"terms\s+and\s+conditions",
        r"rate\s+of\s+interest",
        r"repayment\s+schedule",
        r"disbursement",
        r"hereby\s+sanctioned",
    ],
    "income_tax_return": [
        r"income\s+tax\s+return",
        r"itr[-\s]?[1-7]",
        r"acknowledgement\s+number",
        r"pan",
        r"assessment\s+year",
        r"total\s+income",
        r"tax\s+payable",
        r"refund",
    ],
    "memorandum_of_association": [
        r"memorandum\s+of\s+association",
        r"moa",
        r"articles\s+of\s+association",
        r"aoa",
        r"registered\s+office",
        r"authorized\s+capital",
        r"objects\s+clause",
    ],
    "board_resolution": [
        r"board\s+resolution",
        r"meeting\s+of\s+board",
        r"directors\s+present",
        r"resolved\s+that",
        r"chairman",
        r"quorum",
    ],
}


def classify_document(text: str, filename: str = "") -> Dict[str, any]:
    """
    Classify document type based on content and filename patterns.
    
    Args:
        text: Full text extracted from document
        filename: Original filename (optional, provides additional hints)
    
    Returns:
        Dictionary with:
        - document_type: Detected type or "unknown"
        - confidence: Confidence score (0-1)
        - matched_patterns: List of matched keywords
    """
    text_lower = text.lower()
    filename_lower = filename.lower()
    
    # Score each document type
    type_scores = {}
    matched_patterns_dict = {}
    
    for doc_type, patterns in DOCUMENT_PATTERNS.items():
        score = 0
        matched = []
        
        for pattern in patterns:
            # Search in document text
            if re.search(pattern, text_lower):
                score += 1
                matched.append(pattern)
            
            # Search in filename (bonus points)
            if filename and re.search(pattern, filename_lower):
                score += 0.5
        
        type_scores[doc_type] = score
        if matched:
            matched_patterns_dict[doc_type] = matched
    
    # Find best match
    if not type_scores or max(type_scores.values()) == 0:
        return {
            "document_type": "unknown",
            "confidence": 0.0,
            "matched_patterns": [],
            "secondary_types": [],
        }
    
    # Sort by score
    sorted_types = sorted(type_scores.items(), key=lambda x: x[1], reverse=True)
    best_type, best_score = sorted_types[0]
    
    # Calculate confidence based on score and total patterns
    total_patterns = len(DOCUMENT_PATTERNS[best_type])
    confidence = min(best_score / total_patterns, 1.0)
    
    # Identify secondary document types (multi-type documents)
    secondary_types = []
    for doc_type, score in sorted_types[1:]:
        if score >= 2:  # At least 2 pattern matches
            secondary_types.append({
                "type": doc_type,
                "score": score,
            })
    
    logger.info(f"Classified as '{best_type}' with confidence {confidence:.2f}")
    
    return {
        "document_type": best_type,
        "confidence": float(confidence),
        "matched_patterns": matched_patterns_dict.get(best_type, []),
        "secondary_types": secondary_types,
    }


def detect_document_language(text: str) -> str:
    """
    Detect primary language of document.
    
    Returns:
        Language code: 'en', 'hi', 'mixed', or 'unknown'
    """
    # Simple heuristic based on character ranges
    if not text:
        return "unknown"
    
    # Count English characters
    english_chars = sum(1 for c in text if ord('a') <= ord(c.lower()) <= ord('z'))
    
    # Count Hindi/Devanagari characters
    hindi_chars = sum(1 for c in text if 0x0900 <= ord(c) <= 0x097F)
    
    total_alpha = english_chars + hindi_chars
    
    if total_alpha == 0:
        return "unknown"
    
    english_ratio = english_chars / total_alpha
    
    if english_ratio > 0.9:
        return "en"
    elif english_ratio < 0.3:
        return "hi"
    else:
        return "mixed"


def detect_financial_year(text: str) -> Optional[str]:
    """
    Extract financial year from document.
    
    Returns:
        Financial year string like "FY 2023-24" or None
    """
    # Common patterns for Indian financial year
    patterns = [
        r"fy\s*(\d{4})[-–]?(\d{2,4})",  # FY 2023-24
        r"financial\s+year\s*(\d{4})[-–]?(\d{2,4})",
        r"f\.?y\.?\s*(\d{4})[-–]?(\d{2,4})",
        r"for\s+the\s+year\s+ended\s+(\d{1,2})[/-](\d{1,2})[/-](\d{4})",
    ]
    
    text_lower = text.lower()
    
    for pattern in patterns:
        match = re.search(pattern, text_lower)
        if match:
            groups = match.groups()
            if len(groups) >= 2:
                year1 = groups[0]
                year2 = groups[1]
                
                # Normalize to FY YYYY-YY format
                if len(year2) == 2:
                    return f"FY {year1}-{year2}"
                elif len(year2) == 4:
                    return f"FY {year1}-{year2[2:]}"
    
    return None


def extract_company_identifiers(text: str) -> Dict[str, Optional[str]]:
    """
    Extract company identifiers like CIN, PAN, GSTIN.
    
    Returns:
        Dictionary with extracted identifiers
    """
    identifiers = {
        "cin": None,
        "pan": None,
        "gstin": None,
    }
    
    # CIN pattern: L12345AB1234PLC123456
    cin_pattern = r"\b[LU]\d{5}[A-Z]{2}\d{4}[A-Z]{3}\d{6}\b"
    cin_match = re.search(cin_pattern, text)
    if cin_match:
        identifiers["cin"] = cin_match.group(0)
    
    # PAN pattern: AAAAA1234A
    pan_pattern = r"\b[A-Z]{5}\d{4}[A-Z]\b"
    pan_match = re.search(pan_pattern, text)
    if pan_match:
        identifiers["pan"] = pan_match.group(0)
    
    # GSTIN pattern: 22AAAAA0000A1Z5
    gstin_pattern = r"\b\d{2}[A-Z]{5}\d{4}[A-Z]\d[A-Z]\d\b"
    gstin_match = re.search(gstin_pattern, text)
    if gstin_match:
        identifiers["gstin"] = gstin_match.group(0)
    
    return identifiers


def is_scanned_document(ocr_confidence: float, text_length: int) -> bool:
    """
    Determine if document is scanned (vs digitally generated).
    
    Indicators:
    - Low OCR confidence
    - Irregular text extraction
    - Short text despite many pages
    """
    if ocr_confidence < 0.7:
        return True
    
    if text_length < 100:
        return True
    
    return False


def detect_table_heavy_document(tables_count: int, text_blocks_count: int) -> bool:
    """
    Detect if document is table-heavy (like bank statements).
    """
    if tables_count == 0:
        return False
    
    # If more than 30% of content is tables
    ratio = tables_count / max(text_blocks_count, 1)
    return ratio > 0.3
