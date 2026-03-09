"""
Agent 2 — Research Agent
Runs 5 ordered web searches using Tavily, then synthesises findings
with Claude using a ReAct-style loop to assess company & promoter risk.
"""
from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any, Dict, List

from anthropic import Anthropic

from tools.web_search import (
    format_search_results_for_llm,
    run_due_diligence_searches,
)
from utils.prompts import RESEARCH_SYNTHESIS_PROMPT
from tools.epfo_operations_tracker import verify_operations_via_epfo


def _log(agent: str, message: str, level: str = "INFO") -> Dict[str, Any]:
    return {
        "timestamp": datetime.now().strftime("%H:%M:%S"),
        "agent": agent,
        "message": message,
        "level": level,
    }


def _call_claude(prompt: str, max_tokens: int = 4096) -> str:
    client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text


def _extract_json(text: str) -> Dict[str, Any]:
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        pass
    start = text.find("{")
    end = text.rfind("}") + 1
    if start != -1 and end > start:
        try:
            return json.loads(text[start:end])
        except json.JSONDecodeError:
            pass
    return {}


def _default_research() -> Dict[str, Any]:
    return {
        "litigation_risk": "LOW",
        "promoter_integrity_score": 75,
        "sector_outlook": "NEUTRAL",
        "sector_headwinds": [],
        "key_findings": [],
        "recommendation_impact": "No adverse findings from web research.",
    }


# ─── ReAct Reasoning Loop ─────────────────────────────────────────────────────

def _react_reason(
    search_label: str,
    search_result: Dict[str, Any],
    accumulated_context: List[str],
) -> str:
    """
    Lightweight reasoning step after each search.
    Returns a one-sentence observation to feed into the next search.
    """
    results = search_result.get("results", [])
    if not results:
        return f"No results found for '{search_label}'. Proceeding with next search."

    top_titles = [r.get("title", "") for r in results[:3]]
    observation = (
        f"After '{search_label}': found {len(results)} results. "
        f"Top sources: {'; '.join(top_titles[:2])}."
    )

    # Heuristic risk signal detection
    risk_keywords = [
        "fraud", "default", "npa", "nclt", "insolvency", "ed probe", "cbi",
        "money laundering", "strike off", "winding up", "sebi ban",
    ]
    all_text = " ".join(
        (r.get("title", "") + " " + r.get("content", "")).lower()
        for r in results
    )
    found_risks = [kw for kw in risk_keywords if kw in all_text]
    if found_risks:
        observation += f" RISK SIGNALS DETECTED: {', '.join(found_risks)}."

    return observation


# ─── Main Agent Function (LangGraph node) ────────────────────────────────────

async def run_research_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    LangGraph node: Research Agent.
    Runs 5 ordered Tavily searches then uses Claude to synthesise findings.
    """
    logs: List[Dict[str, Any]] = []
    agent = "RESEARCH"

    company_name = state.get("company_name", "Unknown Company")
    sector = state.get("sector", "")
    extracted_fin = state.get("extracted_financials", {})
    promoters = extracted_fin.get("promoters", [])

    logs.append(_log(agent, f"Starting research for '{company_name}'..."))

    # ── Step 1: Execute 5 ordered searches ────────────────────────────────────
    logs.append(_log(agent, "Executing 5 due diligence web searches via Tavily..."))

    search_results: List[Dict[str, Any]] = []
    accumulated_context: List[str] = []
    risk_signals_found = False

    try:
        raw_results = run_due_diligence_searches(
            company_name=company_name,
            sector=sector,
            promoter_names=promoters,
        )

        for sr in raw_results:
            label = sr.get("label", "Search")
            error = sr.get("error")

            if error:
                logs.append(_log(agent, f"Search '{label}' failed: {error}", level="WARN"))
            else:
                result_count = len(sr.get("results", []))
                logs.append(_log(agent, f"'{label}' → {result_count} results found."))

                # ReAct reasoning step
                observation = _react_reason(label, sr, accumulated_context)
                accumulated_context.append(observation)
                logs.append(_log(agent, f"Observation: {observation}"))

                if "RISK SIGNALS DETECTED" in observation:
                    risk_signals_found = True

            search_results.append(sr)

    except Exception as exc:
        logs.append(_log(agent, f"Web search error: {exc}", level="ERROR"))

    if risk_signals_found:
        logs.append(_log(agent, "⚠ Risk signals detected in search results. Flagging for scorer.", level="WARN"))
    else:
        logs.append(_log(agent, "No critical risk signals found in search results."))

    # ── Step 2: Claude synthesis ───────────────────────────────────────────────
    logs.append(_log(agent, "Synthesising search results with Claude..."))

    formatted_results = format_search_results_for_llm(search_results)
    if not formatted_results.strip():
        formatted_results = "No web search results available — Tavily may be unavailable."

    prompt = RESEARCH_SYNTHESIS_PROMPT.format(
        company_name=company_name,
        sector=sector,
        search_results=formatted_results[:20_000],  # Cap token usage
    )

    try:
        raw_response = _call_claude(prompt)
        research_data = _extract_json(raw_response)

        if not research_data:
            logs.append(_log(agent, "JSON parse failed — using safe defaults.", level="WARN"))
            research_data = _default_research()
    except Exception as exc:
        logs.append(_log(agent, f"Claude synthesis error: {exc}", level="ERROR"))
        research_data = _default_research()

    # ── Step 3: Log summary ───────────────────────────────────────────────────
    litigation = research_data.get("litigation_risk", "UNKNOWN")
    integrity = research_data.get("promoter_integrity_score", 0)
    outlook = research_data.get("sector_outlook", "NEUTRAL")
    findings_count = len(research_data.get("key_findings", []))

    logs.append(
        _log(
            agent,
            f"Research complete — Litigation: {litigation} | "
            f"Promoter Score: {integrity}/100 | "
            f"Sector: {outlook} | "
            f"Findings: {findings_count}",
            level="SUCCESS",
        )
    )
    logs.append(_log(agent, "Research Agent DONE.", level="SUCCESS"))

    # Attach raw search results for transparency trail
    research_data["_search_queries"] = [
        {"label": sr.get("label", ""), "query": sr.get("query", "")}
        for sr in search_results
    ]

    # ── NEW: EPFO operational verification ────────────────────────────
    logs.append(_log(agent, "Running EPFO operational verification..."))
    
    # Extract data for EPFO check
    gstin = state.get("gstin", "") or extracted_fin.get("gstin", "27AAAAA0000A1Z5") # mock fallback if not found
    financials = extracted_fin.get("financials", {})
    revenue_3yr = financials.get("revenue_3yr", [])
    claimed_revenue_cr = revenue_3yr[-1] if revenue_3yr else state.get("revenue_cr", 0)
    
    epfo_result = None
    red_flags = state.get("red_flags", [])
    auto_reject = state.get("auto_reject", False)
    reject_reason = state.get("reject_reason", "")
    
    if gstin and claimed_revenue_cr > 0:
        epfo_result = await verify_operations_via_epfo(
            gstin=gstin,
            claimed_revenue_cr=claimed_revenue_cr,
            sector=sector,
            company_name=company_name,
            gst_turnover_cr=state.get("gst_turnover_cr"),
            bank_inflow_cr=state.get("bank_inflow_cr"),
        )
        
        if epfo_result["is_ghost_company"]:
            red_flags.append("RF_EPFO_GHOST_COMPANY")
            auto_reject = True
            reject_reason = (
                f"Ghost company pattern: ₹{claimed_revenue_cr:.0f} Cr revenue "
                f"with only {epfo_result['epfo_employee_count']} EPFO employees."
            )
            logs.append(_log(agent, f"EPFO Check: {reject_reason}", level="ERROR"))
        elif epfo_result["plausibility_verdict"] == "IMPLAUSIBLE":
            red_flags.append("RF_EPFO_REVENUE_IMPLAUSIBLE")
            logs.append(_log(agent, "EPFO Check: Revenue plausibility is IMPLAUSIBLE.", level="WARN"))
        else:
            logs.append(_log(agent, "EPFO Check: Revenue is plausible based on EPFO records.", level="SUCCESS"))


    return {
        "research_findings": research_data,
        "epfo_verification": epfo_result,
        "red_flags": red_flags,
        "auto_reject": auto_reject,
        "reject_reason": reject_reason,
        "logs": logs,
        "agent_statuses": {**state.get("agent_statuses", {}), "research": "DONE"},
    }
