"""
Agent 1 — Ingestor Agent
Parses uploaded financial documents, runs GST reconciliation,
and extracts structured financial data using Claude.
"""
from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any, Dict, List

from anthropic import Anthropic

from tools.gst_analyser import analyse_gst_documents
from tools.pdf_parser import format_documents_for_llm
from utils.prompts import INGESTOR_PROMPT


def _log(agent: str, message: str, level: str = "INFO") -> Dict[str, Any]:
    return {
        "timestamp": datetime.now().strftime("%H:%M:%S"),
        "agent": agent,
        "message": message,
        "level": level,
    }


def _call_claude(prompt: str, max_tokens: int = 4096) -> str:
    """Call Claude claude-sonnet-4-20250514 and return the raw response text."""
    client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text


def _extract_json(text: str) -> Dict[str, Any]:
    """Extract the first JSON object found in Claude's response."""
    # Try direct parse first
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        pass

    # Find JSON block via braces
    start = text.find("{")
    end = text.rfind("}") + 1
    if start != -1 and end > start:
        try:
            return json.loads(text[start:end])
        except json.JSONDecodeError:
            pass

    return {}


# ─── Default Fallback Payload ─────────────────────────────────────────────────

def _default_financials() -> Dict[str, Any]:
    return {
        "company_name": "",
        "cin": "",
        "incorporation_date": "",
        "registered_address": "",
        "business_address": "",
        "sector_classification": "",
        "number_of_employees": 0,
        "promoters": [],
        "promoter_details": [],
        "financials": {
            "revenue_3yr": [0, 0, 0],
            "ebitda_3yr": [0, 0, 0],
            "pat_3yr": [0, 0, 0],
            "total_debt": 0,
            "net_worth": 0,
            "dscr": 0,
            "debt_to_equity": 0,
            "cash_flow_from_operations": 0,
            "current_assets": 0,
            "current_liabilities": 0,
            "cash_and_bank": 0,
            "debtors": 0,
            "inventory": 0,
            "creditors": 0,
            "short_term_loans": 0,
            "total_assets": 0,
        },
        "existing_loans": [],
        "collateral": {"type": "", "estimated_value": 0},
        "gst_vs_bank_discrepancy": {"detected": False, "details": "", "severity": "LOW"},
        "red_flags": [],
    }


# ─── Additional Red Flag Rules ────────────────────────────────────────────────

def _apply_rule_based_flags(data: Dict[str, Any], loan_amount: float) -> List[str]:
    """Apply deterministic Indian banking rule flags on top of LLM output."""
    flags: List[str] = list(data.get("red_flags", []))
    fin = data.get("financials", {})

    d2e = fin.get("debt_to_equity", 0)
    dscr = fin.get("dscr", 0)
    collateral_val = data.get("collateral", {}).get("estimated_value", 0)

    if d2e > 3:
        flag = f"Over-leveraged: Debt-to-Equity ratio is {d2e:.2f}x (threshold: 3x)"
        if flag not in flags:
            flags.append(flag)

    if 0 < dscr < 1.25:
        flag = f"Insufficient debt service cover: DSCR is {dscr:.2f}x (minimum: 1.25x)"
        if flag not in flags:
            flags.append(flag)

    if loan_amount > 0 and collateral_val > 0:
        cover = collateral_val / loan_amount
        if cover < 1.0:
            flags.append(
                f"Collateral shortfall: Cover ratio is {cover:.2f}x (collateral Rs.{collateral_val:.1f} Cr vs loan Rs.{loan_amount:.1f} Cr)"
            )

    gst = data.get("gst_vs_bank_discrepancy", {})
    if gst.get("detected") and gst.get("severity") == "HIGH":
        flag = f"GST fraud signal: GSTR-3B vs GSTR-2A discrepancy detected. {gst.get('details', '')}"
        if flag not in flags:
            flags.append(flag)

    return flags


# ─── Main Agent Function (LangGraph node) ────────────────────────────────────

async def run_ingestor_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    LangGraph node: Ingestor Agent.
    Input : state dict (full CreditAppraisalState)
    Output: partial state dict with updated keys
    """
    logs: List[Dict[str, Any]] = []
    agent = "INGESTOR"

    logs.append(_log(agent, f"Starting document ingestion for {state['company_name']}"))

    documents: List[Dict[str, Any]] = state.get("documents", [])
    company_name = state.get("company_name", "Unknown Company")
    sector = state.get("sector", "")
    loan_amount = state.get("loan_amount_requested", 0)

    # ── Step 1: GST Reconciliation ────────────────────────────────────────────
    logs.append(_log(agent, "Running GST GSTR-3B vs GSTR-2A reconciliation..."))

    gst_texts = [
        doc["text"]
        for doc in documents
        if doc.get("doc_type", "").lower() in ("gst_returns", "gst", "gstr")
        and doc.get("text")
    ]
    bank_texts = [
        doc["text"]
        for doc in documents
        if doc.get("doc_type", "").lower() in ("bank_statement", "bank_statements")
        and doc.get("text")
    ]
    bank_text_combined = "\n".join(bank_texts)

    gst_result = analyse_gst_documents(gst_texts, bank_text_combined)

    if gst_result.detected:
        logs.append(
            _log(
                agent,
                f"GST discrepancy detected — Severity: {gst_result.severity} | "
                f"Discrepancy: {gst_result.discrepancy_pct:.1f}%",
                level="WARN" if gst_result.severity != "HIGH" else "ERROR",
            )
        )
    else:
        logs.append(_log(agent, "GST reconciliation: No significant discrepancy found."))

    # ── Step 2: Format documents for LLM ─────────────────────────────────────
    logs.append(_log(agent, f"Formatting {len(documents)} document(s) for LLM analysis..."))

    doc_text = format_documents_for_llm(documents)
    if not doc_text.strip():
        doc_text = f"No documents uploaded. Company: {company_name}, Sector: {sector}."

    # Truncate to avoid token limit
    doc_text = doc_text[:30_000]

    # ── Step 3: LLM Extraction ────────────────────────────────────────────────
    logs.append(_log(agent, "Sending documents to Claude for financial data extraction..."))

    prompt = INGESTOR_PROMPT.format(
        company_name=company_name,
        sector=sector,
        loan_amount=loan_amount,
        documents=doc_text,
        gst_analysis=gst_result.to_prompt_text(),
    )

    try:
        raw_response = _call_claude(prompt)
        logs.append(_log(agent, "LLM extraction complete. Parsing JSON response..."))
        extracted = _extract_json(raw_response)

        if not extracted:
            logs.append(_log(agent, "JSON parse failed — using defaults.", level="WARN"))
            extracted = _default_financials()
    except Exception as exc:
        logs.append(_log(agent, f"Claude API error: {exc}", level="ERROR"))
        extracted = _default_financials()

    # Ensure company name is populated
    if not extracted.get("company_name"):
        extracted["company_name"] = company_name

    # Inject GST result into extracted data (override LLM if tool found discrepancy)
    if gst_result.detected or not extracted.get("gst_vs_bank_discrepancy", {}).get("details"):
        extracted["gst_vs_bank_discrepancy"] = gst_result.to_dict()

    # ── Step 4: Rule-based flag augmentation ──────────────────────────────────
    extracted["red_flags"] = _apply_rule_based_flags(extracted, loan_amount)

    fraud_flags = [
        f for f in extracted["red_flags"]
        if any(kw in f.lower() for kw in ("high", "fraud", "npa", "default", "nclt", "gst"))
    ]

    # Log summary
    fin = extracted.get("financials", {})
    logs.append(
        _log(
            agent,
            f"Extraction complete — DSCR: {fin.get('dscr', 0):.2f}x | "
            f"D/E: {fin.get('debt_to_equity', 0):.2f}x | "
            f"Flags: {len(extracted['red_flags'])}",
            level="SUCCESS",
        )
    )
    logs.append(_log(agent, "Ingestor Agent DONE.", level="SUCCESS"))

    # Propagate extracted fields to state for downstream agents
    return {
        "extracted_financials": extracted,
        "fraud_flags": fraud_flags,
        "logs": logs,
        "agent_statuses": {**state.get("agent_statuses", {}), "ingestor": "DONE"},
        # Additional fields for new tools
        "cin": extracted.get("cin", ""),
        "incorporation_date": extracted.get("incorporation_date", ""),
        "registered_address": extracted.get("registered_address", ""),
        "business_address": extracted.get("business_address", ""),
        "sector_classification": extracted.get("sector_classification", state.get("sector", "")),
        "number_of_employees": extracted.get("number_of_employees", 0),
        "promoter_details": extracted.get("promoter_details", []),
        "existing_loans": extracted.get("existing_loans", []),
        # Financial fields for working capital analysis
        "current_assets": extracted.get("financials", {}).get("current_assets", 0),
        "current_liabilities": extracted.get("financials", {}).get("current_liabilities", 0),
        "cash_and_bank": extracted.get("financials", {}).get("cash_and_bank", 0),
        "debtors": extracted.get("financials", {}).get("debtors", 0),
        "inventory": extracted.get("financials", {}).get("inventory", 0),
        "creditors": extracted.get("financials", {}).get("creditors", 0),
        "short_term_loans": extracted.get("financials", {}).get("short_term_loans", 0),
        "total_assets": extracted.get("financials", {}).get("total_assets", 0),
    }
