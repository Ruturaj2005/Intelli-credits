"""
Document Classifier Module
Automatically detects the type of financial document.
"""
from __future__ import annotations

import logging
import re
from enum import Enum
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class DocumentType(str, Enum):
    """Enumeration of supported document types"""
    # Existing document types
    ANNUAL_REPORT = "ANNUAL_REPORT"
    FINANCIAL_STATEMENT = "FINANCIAL_STATEMENT"
    BANK_STATEMENT = "BANK_STATEMENT"
    GST_RETURN = "GST_RETURN"
    CIBIL_REPORT = "CIBIL_REPORT"
    ITR = "ITR"
    LEGAL_DOCUMENT = "LEGAL_DOCUMENT"
    MCA_FILING = "MCA_FILING"
    RATING_REPORT = "RATING_REPORT"
    SANCTION_LETTER = "SANCTION_LETTER"
    
    # Hackathon-specific document types
    ALM = "ALM"
    SHAREHOLDING_PATTERN = "SHAREHOLDING_PATTERN"
    BORROWING_PROFILE = "BORROWING_PROFILE"
    PORTFOLIO_PERFORMANCE = "PORTFOLIO_PERFORMANCE"
    
    # Unknown/fallback
    UNKNOWN = "UNKNOWN"


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

# Hackathon-specific document type keywords
EXTENDED_DOCUMENT_KEYWORDS = {
    "ALM": [
        "asset liability management",
        "maturity profile",
        "liquidity gap",
        "interest rate risk",
        "duration gap",
        "repricing gap",
        "alco",
        "negative gap",
        "positive gap",
        "rate sensitive assets",
    ],
    "SHAREHOLDING_PATTERN": [
        "shareholding pattern",
        "promoter holding",
        "public shareholding",
        "category of shareholder",
        "holding of specified securities",
        "regulation 31",
        "statement showing shareholding",
        "partly paid-up shares",
    ],
    "BORROWING_PROFILE": [
        "borrowing profile",
        "loan portfolio",
        "facility details",
        "credit facilities",
        "term loan details",
        "working capital limit",
        "outstanding borrowings",
        "bank-wise exposure",
        "sanction letter",
    ],
    "PORTFOLIO_PERFORMANCE": [
        "portfolio performance",
        "asset quality",
        "gross npa",
        "net npa",
        "provision coverage ratio",
        "loan book composition",
        "sector-wise exposure",
        "vintage analysis",
        "concentration risk",
        "npa ratio",
    ],
}


def _check_table_structure(tables: List[Dict], type_specific_check: str) -> bool:
    """
    Check if table structure matches document type requirements.
    
    Args:
        tables: List of extracted tables with column headers
        type_specific_check: Type of check ("shareholding" or "borrowing")
    
    Returns:
        True if table structure matches the expected pattern
    """
    if not tables:
        return False
    
    for table in tables:
        if not isinstance(table, dict):
            continue
        
        headers = table.get("headers", [])
        if not headers:
            continue
        
        headers_lower = [str(h).lower() for h in headers]
        
        if type_specific_check == "shareholding":
            # Check for promoter + share columns
            has_promoter = any("promoter" in h for h in headers_lower)
            has_share = any("share" in h or "holding" in h for h in headers_lower)
            if has_promoter and has_share:
                return True
        
        elif type_specific_check == "borrowing":
            # Check for bank/lender + sanction/outstanding/amount columns
            has_lender = any("bank" in h or "lender" in h or "institution" in h for h in headers_lower)
            has_amount = any(
                "sanction" in h or "outstanding" in h or "amount" in h or "limit" in h
                for h in headers_lower
            )
            if has_lender and has_amount:
                return True
    
    return False


def classify_document_type_extended(
    text: str,
    tables: Optional[List[Dict]] = None,
    filename: str = "",
    metadata: Optional[Dict] = None,
) -> Tuple[DocumentType, float, str, List[Tuple[DocumentType, float]]]:
    """
    Extended document classification for hackathon-specific document types.
    Uses keyword matching with confidence scoring.
    
    Args:
        text: Extracted document text
        tables: Extracted tables (optional)
        filename: Original filename
        metadata: Additional metadata
    
    Returns:
        Tuple of (document_type, confidence, reasoning, alternatives)
        - document_type: Detected DocumentType enum value
        - confidence: Float between 0 and 1
        - reasoning: String explaining the detection
        - alternatives: List of (DocumentType, confidence) tuples for top 2 alternatives
    """
    if not text:
        return (DocumentType.UNKNOWN, 0.35, "Empty document content", [])
    
    text_lower = text.lower()
    tables = tables or []
    
    # Track scores for each extended type
    type_scores = {}
    matched_keywords = {}
    
    # Check ALM keywords
    alm_matches = []
    for keyword in EXTENDED_DOCUMENT_KEYWORDS["ALM"]:
        if keyword.lower() in text_lower:
            alm_matches.append(keyword)
    
    if len(alm_matches) >= 3:
        confidence = min(0.60 + (len(alm_matches) * 0.05), 0.95)
        type_scores[DocumentType.ALM] = confidence
        matched_keywords[DocumentType.ALM] = alm_matches[:5]  # Top 5 for reasoning
    
    # Check SHAREHOLDING_PATTERN keywords
    shareholding_matches = []
    for keyword in EXTENDED_DOCUMENT_KEYWORDS["SHAREHOLDING_PATTERN"]:
        if keyword.lower() in text_lower:
            shareholding_matches.append(keyword)
    
    # Bonus for table structure
    table_bonus = 0.0
    if _check_table_structure(tables, "shareholding"):
        table_bonus = 0.10
    
    if len(shareholding_matches) >= 3:
        confidence = min(0.70 + (len(shareholding_matches) * 0.05) + table_bonus, 0.95)
        type_scores[DocumentType.SHAREHOLDING_PATTERN] = confidence
        matched_keywords[DocumentType.SHAREHOLDING_PATTERN] = shareholding_matches[:5]
    
    # Check BORROWING_PROFILE keywords
    borrowing_matches = []
    for keyword in EXTENDED_DOCUMENT_KEYWORDS["BORROWING_PROFILE"]:
        if keyword.lower() in text_lower:
            borrowing_matches.append(keyword)
    
    # Bonus for table structure
    table_bonus = 0.0
    if _check_table_structure(tables, "borrowing"):
        table_bonus = 0.10
    
    if len(borrowing_matches) >= 3:
        confidence = min(0.70 + (len(borrowing_matches) * 0.05) + table_bonus, 0.95)
        type_scores[DocumentType.BORROWING_PROFILE] = confidence
        matched_keywords[DocumentType.BORROWING_PROFILE] = borrowing_matches[:5]
    
    # Check PORTFOLIO_PERFORMANCE keywords
    portfolio_matches = []
    for keyword in EXTENDED_DOCUMENT_KEYWORDS["PORTFOLIO_PERFORMANCE"]:
        if keyword.lower() in text_lower:
            portfolio_matches.append(keyword)
    
    if len(portfolio_matches) >= 3:
        confidence = min(0.60 + (len(portfolio_matches) * 0.05), 0.95)
        type_scores[DocumentType.PORTFOLIO_PERFORMANCE] = confidence
        matched_keywords[DocumentType.PORTFOLIO_PERFORMANCE] = portfolio_matches[:5]
    
    # If no extended type matched, return None to fall back to existing classifier
    if not type_scores:
        return (None, 0.0, "No extended type matched", [])
    
    # Sort by confidence
    sorted_types = sorted(type_scores.items(), key=lambda x: x[1], reverse=True)
    best_type, best_confidence = sorted_types[0]
    
    # Build reasoning string
    keywords = matched_keywords[best_type]
    keyword_counts = {kw: text_lower.count(kw.lower()) for kw in keywords}
    reasoning_parts = [f"{kw} ({keyword_counts[kw]})" for kw in keywords[:3]]
    reasoning = f"Detected keywords: {', '.join(reasoning_parts)}"
    
    # Get alternatives (top 2 other types)
    alternatives = [(doc_type, conf) for doc_type, conf in sorted_types[1:3]]
    
    logger.info(f"Extended classifier: {best_type.value} with confidence {best_confidence:.2f}")
    
    return (best_type, best_confidence, reasoning, alternatives)


def _classify_existing_types(text: str, filename: str = "") -> Dict[str, any]:
    """
    [INTERNAL] Classify using existing document type patterns.
    This is called as a fallback when extended classification doesn't match.
    
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


def classify_document_type(
    text: str,
    tables: Optional[List[Dict]] = None,
    filename: str = "",
    metadata: Optional[Dict] = None,
) -> Tuple[DocumentType, float, str, List[Tuple[DocumentType, float]]]:
    """
    Main document classification function with support for hackathon-specific types.
    
    This function first tries extended classification (ALM, Shareholding Pattern, etc.),
    then falls back to existing types if no match is found.
    
    Args:
        text: Extracted document text
        tables: Extracted tables (optional)
        filename: Original filename
        metadata: Additional metadata
    
    Returns:
        Tuple of (document_type, confidence, reasoning, alternatives)
        - document_type: Detected DocumentType enum value
        - confidence: Float between 0 and 1 (returns 0.35 if all types < 0.50)
        - reasoning: String explaining the detection
        - alternatives: List of (DocumentType, confidence) tuples for top 2 alternatives
    """
    # Try extended classification first
    doc_type, confidence, reasoning, alternatives = classify_document_type_extended(
        text, tables, filename, metadata
    )
    
    if doc_type is not None:
        # Extended classification succeeded
        return (doc_type, confidence, reasoning, alternatives)
    
    # Fall back to existing classification
    result = _classify_existing_types(text, filename)
    
    # Map existing types to DocumentType enum
    type_mapping = {
        "annual_report": DocumentType.ANNUAL_REPORT,
        "bank_statement": DocumentType.BANK_STATEMENT,
        "gst_filing": DocumentType.GST_RETURN,
        "rating_report": DocumentType.RATING_REPORT,
        "legal_notice": DocumentType.LEGAL_DOCUMENT,
        "sanction_letter": DocumentType.SANCTION_LETTER,
        "income_tax_return": DocumentType.ITR,
        "memorandum_of_association": DocumentType.MCA_FILING,
        "board_resolution": DocumentType.LEGAL_DOCUMENT,
        "unknown": DocumentType.UNKNOWN,
    }
    
    detected_type = result.get("document_type", "unknown")
    confidence = result.get("confidence", 0.0)
    matched_patterns = result.get("matched_patterns", [])
    
    # Map to DocumentType enum
    doc_type_enum = type_mapping.get(detected_type, DocumentType.UNKNOWN)
    
    # Build reasoning
    if matched_patterns:
        pattern_list = ", ".join(matched_patterns[:3])
        reasoning = f"Pattern matches: {pattern_list}"
    else:
        reasoning = "No strong patterns matched"
    
    # Get alternatives from secondary types
    alternatives = []
    for secondary in result.get("secondary_types", [])[:2]:
        sec_type = type_mapping.get(secondary["type"], DocumentType.UNKNOWN)
        sec_conf = min(secondary["score"] / 10.0, 0.80)  # Rough conversion
        alternatives.append((sec_type, sec_conf))
    
    # If confidence < 0.50 for all types, trigger human review
    if confidence < 0.50 and all(alt_conf < 0.50 for _, alt_conf in alternatives):
        logger.warning(f"Low confidence classification: {confidence:.2f}")
        return (DocumentType.UNKNOWN, 0.35, "Low confidence - requires human review", [])
    
    return (doc_type_enum, confidence, reasoning, alternatives)


def classify_document(text: str, filename: str = "") -> Dict[str, any]:
    """
    Legacy wrapper for backward compatibility.
    Delegates to classify_document_type and returns dict format.
    
    Args:
        text: Full text extracted from document
        filename: Original filename (optional)
    
    Returns:
        Dictionary with:
        - document_type: Detected type string
        - confidence: Confidence score (0-1)
        - matched_patterns: List of matched keywords
        - reasoning: Detection explanation
        - alternatives: List of alternative types
    """
    doc_type, confidence, reasoning, alternatives = classify_document_type(
        text=text, filename=filename
    )
    
    return {
        "document_type": doc_type.value if doc_type else "UNKNOWN",
        "confidence": float(confidence),
        "reasoning": reasoning,
        "alternatives": [
            {"type": alt_type.value, "confidence": alt_conf}
            for alt_type, alt_conf in alternatives
        ],
        "matched_patterns": [],  # Not available in new format
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
