"""
GST Reconciliation Tool.

Compares GSTR-3B (self-declared outward supplies) against GSTR-2A
(auto-populated inward supplies from counterparty filings) to detect
potential revenue inflation — a common fraud signal in Indian corporate lending.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional


# ─── Data Structures ──────────────────────────────────────────────────────────

class GSTAnalysisResult:
    def __init__(
        self,
        detected: bool,
        details: str,
        severity: str,
        gstr3b_total: float,
        gstr2a_total: float,
        discrepancy_pct: float,
        period_analysis: List[Dict[str, Any]],
    ):
        self.detected = detected
        self.details = details
        self.severity = severity
        self.gstr3b_total = gstr3b_total
        self.gstr2a_total = gstr2a_total
        self.discrepancy_pct = discrepancy_pct
        self.period_analysis = period_analysis

    def to_dict(self) -> Dict[str, Any]:
        return {
            "detected": self.detected,
            "details": self.details,
            "severity": self.severity,
            "gstr3b_total": self.gstr3b_total,
            "gstr2a_total": self.gstr2a_total,
            "discrepancy_pct": round(self.discrepancy_pct, 2),
            "period_analysis": self.period_analysis,
        }

    def to_prompt_text(self) -> str:
        if not self.detected:
            return (
                "GST Analysis: No significant discrepancy detected between "
                f"GSTR-3B (Rs.{self.gstr3b_total:.2f} Cr) and GSTR-2A "
                f"(Rs.{self.gstr2a_total:.2f} Cr). Discrepancy: {self.discrepancy_pct:.1f}%."
            )
        return (
            f"GST Analysis WARNING [{self.severity}]: GSTR-3B declared "
            f"Rs.{self.gstr3b_total:.2f} Cr vs GSTR-2A Rs.{self.gstr2a_total:.2f} Cr. "
            f"Discrepancy: {self.discrepancy_pct:.1f}%. {self.details}"
        )


# ─── Regex Helpers ────────────────────────────────────────────────────────────

_AMOUNT_RE = re.compile(r"(?:Rs\.?|INR|₹)?\s*([\d,]+(?:\.\d+)?)", re.IGNORECASE)
_PERIOD_RE = re.compile(
    r"((?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*[-\s]?\d{2,4})",
    re.IGNORECASE,
)


def _extract_amounts(text: str) -> List[float]:
    """Extract all monetary amounts from text."""
    matches = _AMOUNT_RE.findall(text)
    results: List[float] = []
    for m in matches:
        try:
            val = float(m.replace(",", ""))
            if val > 0:
                results.append(val)
        except ValueError:
            pass
    return results


def _parse_gst_section(text: str, form_type: str) -> Optional[float]:
    """
    Attempt to parse a total taxable value from a GST form section.
    Looks for the form identifier nearby and extracts the largest plausible value.
    """
    pattern = re.compile(
        rf"{re.escape(form_type)}[\s\S]{{0,500}}",
        re.IGNORECASE,
    )
    match = pattern.search(text)
    if not match:
        return None
    snippet = match.group(0)
    amounts = _extract_amounts(snippet)
    if not amounts:
        return None
    # Return the largest amount found — likely the total turnover figure
    return max(amounts)


# ─── Main Analysis Function ───────────────────────────────────────────────────

def analyse_gst_documents(
    gst_document_texts: List[str],
    bank_statement_text: str = "",
) -> GSTAnalysisResult:
    """
    Reconcile GSTR-3B vs GSTR-2A figures extracted from uploaded GST return PDFs.

    Threshold rule (per Indian banking norms):
    - Discrepancy < 5%  → No finding (LOW)
    - Discrepancy 5-15% → Caution flag (MEDIUM)
    - Discrepancy > 15% → Revenue inflation flag (HIGH)

    Args:
        gst_document_texts: List of text strings from GST return PDFs.
        bank_statement_text: Optional bank statement text for cross-validation.
    """
    combined_text = "\n".join(gst_document_texts)

    gstr3b_total = _parse_gst_section(combined_text, "GSTR-3B") or 0.0
    gstr2a_total = _parse_gst_section(combined_text, "GSTR-2A") or 0.0

    # Fallback: look for "3B" and "2A" labels in the text
    if gstr3b_total == 0.0:
        for label in ["3b", "form 3b", "outward supplies"]:
            val = _parse_gst_section(combined_text, label)
            if val:
                gstr3b_total = val
                break

    if gstr2a_total == 0.0:
        for label in ["2a", "form 2a", "inward supplies"]:
            val = _parse_gst_section(combined_text, label)
            if val:
                gstr2a_total = val
                break

    # If we couldn't parse both, return a neutral result with a note
    if gstr3b_total == 0.0 and gstr2a_total == 0.0:
        return GSTAnalysisResult(
            detected=False,
            details="Could not extract GSTR-3B/2A figures from uploaded documents. Manual verification required.",
            severity="LOW",
            gstr3b_total=0.0,
            gstr2a_total=0.0,
            discrepancy_pct=0.0,
            period_analysis=[],
        )

    # Compute discrepancy
    if gstr2a_total > 0:
        discrepancy_pct = ((gstr3b_total - gstr2a_total) / gstr2a_total) * 100
    elif gstr3b_total > 0:
        discrepancy_pct = 100.0  # No GSTR-2A to compare against
    else:
        discrepancy_pct = 0.0

    # Classify severity
    detected = False
    severity = "LOW"
    details = ""

    if discrepancy_pct > 15:
        detected = True
        severity = "HIGH"
        details = (
            f"GSTR-3B self-declared sales exceed GSTR-2A auto-populated data by "
            f"{discrepancy_pct:.1f}% (threshold: 15%). "
            "This is a strong indicator of potential revenue inflation. "
            "Independent verification of actual sales via bank credits is recommended. "
            "DO NOT approve without reconciliation."
        )
    elif discrepancy_pct > 5:
        detected = True
        severity = "MEDIUM"
        details = (
            f"GSTR-3B vs GSTR-2A discrepancy of {discrepancy_pct:.1f}% detected. "
            "Marginal gap — may be due to timing differences or ITC mismatches. "
            "Request month-wise reconciliation from borrower."
        )
    else:
        severity = "LOW"
        details = (
            f"GSTR-3B and GSTR-2A figures are broadly consistent "
            f"(discrepancy: {discrepancy_pct:.1f}%). No manipulation signals detected."
        )

    # Cross-check with bank statement if available
    bank_validation_note = ""
    if bank_statement_text:
        bank_amounts = _extract_amounts(bank_statement_text)
        if bank_amounts:
            bank_total_estimate = sum(bank_amounts[:12])  # Rough 12-month sum
            if gstr3b_total > 0 and bank_total_estimate > 0:
                bank_gst_ratio = gstr3b_total / bank_total_estimate
                if bank_gst_ratio > 1.5:
                    bank_validation_note = (
                        " Bank statement credits appear significantly lower than "
                        "declared GST sales — corroborates inflation risk."
                    )
                    if severity != "HIGH":
                        severity = "MEDIUM"
                        detected = True

    if bank_validation_note:
        details += bank_validation_note

    return GSTAnalysisResult(
        detected=detected,
        details=details,
        severity=severity,
        gstr3b_total=gstr3b_total,
        gstr2a_total=gstr2a_total,
        discrepancy_pct=discrepancy_pct,
        period_analysis=[],  # Can be extended to parse month-wise data
    )


def compute_revenue_cagr(revenue_3yr: list[float]) -> Optional[float]:
    """Compute 2-year CAGR from a 3-element revenue list [yr1, yr2, yr3]."""
    if len(revenue_3yr) < 2:
        return None
    base = revenue_3yr[0]
    final = revenue_3yr[-1]
    years = len(revenue_3yr) - 1
    if base <= 0:
        return None
    try:
        return ((final / base) ** (1 / years) - 1) * 100
    except (ZeroDivisionError, ValueError):
        return None


def compute_collateral_cover(collateral_value: float, loan_amount: float) -> Optional[float]:
    """Compute collateral cover ratio."""
    if loan_amount <= 0:
        return None
    return collateral_value / loan_amount
