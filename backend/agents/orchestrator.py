"""
Orchestrator — LangGraph StateGraph
Wires all agents, handles parallel execution, enrichment pipeline,
arbitration, and streams live log updates via WebSocket callback.
"""
from __future__ import annotations

import asyncio
import json
import os
from datetime import datetime, date
from typing import Any, Callable, Dict, List, Optional, Tuple

import google.generativeai as genai
from langgraph.graph import StateGraph, END

from agents.ingestor_agent import run_ingestor_agent
from agents.research_agent import run_research_agent
from agents.compliance_agent import run_compliance_agent
from agents.explainable_scoring_agent import run_explainable_scoring_agent
from agents.bank_capacity_agent import run_bank_capacity_agent
from agents.scorer_agent import run_scorer_agent
from agents.cam_generator import run_cam_generator
from agents.rcu_agent import run_rcu_verification_agent
from tools.cibil_api import fetch_cibil_report, get_cibil_score_enhanced
from tools.mca_scraper import fetch_mca_report, run_mca_scraper
from tools.document_forgery_detector import screen_documents_batch
from tools.for_calculator import calculate_for, LoanDetails
from tools.working_capital import analyze_working_capital
from tools.nts_analyzer import analyze_sector
from utils.prompts import ARBITRATION_PROMPT


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _log(agent: str, message: str, level: str = "INFO") -> Dict[str, Any]:
    return {
        "timestamp": datetime.now().strftime("%H:%M:%S"),
        "agent": agent,
        "message": message,
        "level": level,
    }


def _call_gemini(prompt: str, max_tokens: int = 2048) -> str:
    """Call Gemini API with the given prompt."""
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable not set")
    
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-2.0-flash')
    
    response = model.generate_content(
        prompt,
        generation_config=genai.types.GenerationConfig(
            max_output_tokens=max_tokens,
            temperature=0.7,
        )
    )
    return response.text


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


# ─── Enrichment Configuration ─────────────────────────────────────────────────
# Hard ceiling (seconds) for each parallel enrichment sub-task.
# One stalled external API call cannot block the others or hold up the pipeline.
_ENRICHMENT_TASK_TIMEOUT_SECS: int = 30


# ─── Arbitration ──────────────────────────────────────────────────────────────

def _should_arbitrate(state: Dict[str, Any]) -> bool:
    """
    Detect conflict: financials look healthy BUT research found HIGH risks,
    or vice versa.
    """
    fin = state.get("extracted_financials", {})
    research = state.get("research_findings", {})

    dscr = fin.get("financials", {}).get("dscr", 0)
    d2e = fin.get("financials", {}).get("debt_to_equity", 0)
    litigation = research.get("litigation_risk", "LOW")
    integrity = research.get("promoter_integrity_score", 75)

    # Strong financials → weak character
    financials_ok = dscr >= 1.25 and d2e <= 3
    research_bad = litigation == "HIGH" or integrity < 40
    research_good = litigation == "LOW" and integrity >= 70
    financials_bad = dscr < 1.0 or d2e > 4

    return (financials_ok and research_bad) or (research_good and financials_bad)


async def _run_arbitration(state: Dict[str, Any]) -> Dict[str, Any]:
    """Run Gemini arbitration step to reconcile conflicting signals."""
    logs: List[Dict[str, Any]] = [
        _log("ARBITRATOR", "⚡ CONFLICT DETECTED between Ingestor and Research findings.", level="WARN"),
        _log("ARBITRATOR", "Running Gemini arbitration to reconcile signals..."),
    ]

    prompt = ARBITRATION_PROMPT.format(
        ingestor_output=json.dumps(state.get("extracted_financials", {}), indent=2)[:5000],
        research_output=json.dumps(state.get("research_findings", {}), indent=2)[:5000],
    )

    try:
        raw = _call_gemini(prompt)
        arb_result = _extract_json(raw)
        if not arb_result:
            arb_result = {
                "conflict_detected": True,
                "reconciliation_reasoning": "Arbitration parsing failed — defaulting to conservative risk weighting.",
                "adjusted_risk_weight": 1.2,
                "favors": "RESEARCH",
                "recommended_adjustments": [],
            }
    except Exception as exc:
        arb_result = {
            "conflict_detected": True,
            "reconciliation_reasoning": f"Arbitration error: {exc}. Defaulting to conservative assessment.",
            "adjusted_risk_weight": 1.2,
            "favors": "RESEARCH",
        }

    logs.append(
        _log(
            "ARBITRATOR",
            f"Arbitration complete — Favors: {arb_result.get('favors')} | "
            f"Risk weight: {arb_result.get('adjusted_risk_weight')}x",
            level="SUCCESS",
        )
    )
    logs.append(
        _log("ARBITRATOR", f"Reasoning: {arb_result.get('reconciliation_reasoning', '')}")
    )

    return {
        "arbitration_result": arb_result,
        "conflict_detected": True,
        "logs": logs,
    }


# ─── LangGraph Node Wrappers ──────────────────────────────────────────────────
# LangGraph expects synchronous or async callables: (state) -> dict

async def _ingestor_node(state: Dict[str, Any]) -> Dict[str, Any]:
    updates = await run_ingestor_agent(state)
    updates["agent_statuses"] = {
        **state.get("agent_statuses", {}),
        "ingestor": "DONE",
    }
    return updates


async def _research_node(state: Dict[str, Any]) -> Dict[str, Any]:
    updates = await run_research_agent(state)
    updates["agent_statuses"] = {
        **state.get("agent_statuses", {}),
        **updates.get("agent_statuses", {}),
        "research": "DONE",
    }
    return updates


async def _forgery_check_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Node 0: Forgery screening (Gateway)"""
    logs: List[Dict[str, Any]] = [_log("FORGERY_CHECK", "Running document forgery pre-screening...")]
    docs = state.get("documents", [])
    
    if not docs:
        logs.append(_log("FORGERY_CHECK", "No documents to screen."))
        return {"logs": logs}
        
    results = screen_documents_batch(docs)
    logs.append(_log("FORGERY_CHECK", f"Forgery check recommendation: {results.get('overall_recommendation', 'PROCEED')}"))
    
    auto_reject = results.get("overall_recommendation") == "REJECT"
    reject_reason = results.get("rejection_reason", "")
    
    if auto_reject:
        logs.append(_log("FORGERY_CHECK", f"ORCHESTRATOR ALERT: {reject_reason}", level="ERROR"))
    
    return {
        "forgery_analysis": results,
        "auto_reject": auto_reject,
        "reject_reason": reject_reason,
        "logs": logs,
    }


def _check_forgery_result(state: Dict[str, Any]) -> str:
    """Conditional edge for forgery screening."""
    if state.get("auto_reject"):
        return "REJECT"
    return "CONTINUE"


async def _parallel_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Run Ingestor and Research concurrently using asyncio.gather,
    then merge their state updates.
    """
    ingestor_updates, research_updates = await asyncio.gather(
        run_ingestor_agent(state),
        run_research_agent(state),
    )

    merged_logs = (
        ingestor_updates.get("logs", []) + research_updates.get("logs", [])
    )
    merged_statuses = {
        **state.get("agent_statuses", {}),
        "ingestor": "DONE",
        "research": "DONE",
    }

    return {
        **ingestor_updates,
        **research_updates,
        "logs": merged_logs,
        "agent_statuses": merged_statuses,
    }


async def _arbitration_check_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Check for conflict and run arbitration if needed."""
    if _should_arbitrate(state):
        return await _run_arbitration(state)
    return {
        "conflict_detected": False,
        "arbitration_result": {},
        "logs": [_log("ARBITRATOR", "No conflicting signals detected. Skipping arbitration.")],
    }


# ─── Enrichment Subtask Helpers ──────────────────────────────────────────────
# Each function:
#   • receives a read-only snapshot of state (no shared mutable object)
#   • returns (data_dict, log_entries) so the caller can merge cleanly
#   • is wrapped in asyncio.wait_for by the caller for per-task timeouts
#
# Sync-bound helpers (NTS, WC, FOR) are dispatched to a thread-pool via
# asyncio.to_thread so they never block the event loop.

async def _enrichment_task_nts(
    snap: Dict[str, Any],
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """NTS sector health analysis — sync computation, runs in thread pool."""
    agent = "ENRICHMENT"
    logs: List[Dict[str, Any]] = []
    data: Dict[str, Any] = {}

    sector = snap.get("sector_classification") or snap.get("sector", "")
    if not sector:
        logs.append(_log(agent, "Sector not specified — skipping NTS analysis", level="WARN"))
        return data, logs

    nts_result = await asyncio.to_thread(analyze_sector, sector)
    data["nts_analysis"] = {
        "sector_name": nts_result.sector_name,
        "sector_status": nts_result.classification.status,
        "risk_score": nts_result.classification.risk_score,
        "risk_premium_bps": nts_result.classification.risk_premium_bps,
        "key_strengths": nts_result.classification.key_strengths,
        "key_concerns": nts_result.classification.key_concerns,
        "recommendation": nts_result.overall_recommendation,
    }
    logs.append(
        _log(
            agent,
            f"NTS: {nts_result.classification.status} | Risk Score: {nts_result.classification.risk_score}/100",
            level="SUCCESS",
        )
    )
    return data, logs


async def _enrichment_task_wc(
    snap: Dict[str, Any],
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """Working capital analysis — sync computation, runs in thread pool."""
    agent = "ENRICHMENT"
    logs: List[Dict[str, Any]] = []
    data: Dict[str, Any] = {}

    current_assets = snap.get("current_assets", 0)
    current_liabilities = snap.get("current_liabilities", 0)
    if current_assets <= 0 or current_liabilities <= 0:
        logs.append(_log(agent, "Insufficient data for working capital analysis", level="WARN"))
        return data, logs

    wc_result = await asyncio.to_thread(
        analyze_working_capital,
        company_name=snap.get("company_name", ""),
        current_assets=current_assets,
        current_liabilities=current_liabilities,
        cash_and_bank=snap.get("cash_and_bank", 0),
        debtors=snap.get("debtors", 0),
        inventory=snap.get("inventory", 0),
        creditors=snap.get("creditors", 0),
        short_term_loans=snap.get("short_term_loans", 0),
        annual_revenue=snap.get("extracted_financials", {}).get("financials", {}).get("revenue_3yr", [0, 0, 0])[-1],
        total_assets=snap.get("total_assets", 0),
    )
    data["working_capital_analysis"] = {
        "working_capital": wc_result.working_capital,
        "liquidity_status": wc_result.liquidity_status,
        "liquidity_score": wc_result.liquidity_score,
        "current_ratio": wc_result.ratios.current_ratio,
        "quick_ratio": wc_result.ratios.quick_ratio,
        "working_capital_adequacy": wc_result.working_capital_adequacy,
        "risk_flags": wc_result.risk_flags,
        "recommendations": wc_result.recommendations,
    }
    logs.append(
        _log(
            agent,
            f"Working Capital: {wc_result.liquidity_status} | Score: {wc_result.liquidity_score}/100 "
            f"| Current Ratio: {wc_result.ratios.current_ratio:.2f}",
            level="SUCCESS",
        )
    )
    return data, logs


async def _enrichment_task_for(
    snap: Dict[str, Any],
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """Fixed Obligation Ratio (FOR) calculation — sync computation, runs in thread pool."""
    agent = "ENRICHMENT"
    logs: List[Dict[str, Any]] = []
    data: Dict[str, Any] = {}

    existing_loans = snap.get("existing_loans", [])
    financials = snap.get("extracted_financials", {}).get("financials", {})
    revenue = financials.get("revenue_3yr", [0])[-1] if financials.get("revenue_3yr") else 0
    if revenue <= 0:
        logs.append(_log(agent, "Insufficient revenue data for FOR calculation", level="WARN"))
        return data, logs

    # Convert Cr → ₹, derive monthly income
    gross_monthly_income = (revenue * 10_000_000) / 12
    loan_details = [
        LoanDetails(
            outstanding_amount=loan.get("outstanding_amount", 0) * 10_000_000,
            interest_rate=loan.get("interest_rate", 10.0),
            remaining_tenure_months=loan.get("remaining_tenure_months", 60),
        )
        for loan in existing_loans
        if loan.get("emi", 0) > 0
    ]
    proposed_loan = snap.get("loan_amount_requested", 0) * 10_000_000

    for_result = await asyncio.to_thread(
        calculate_for,
        gross_monthly_income=gross_monthly_income,
        existing_loans=loan_details if loan_details else None,
        proposed_loan_amount=proposed_loan if proposed_loan > 0 else None,
        proposed_tenure=60,
        proposed_interest_rate=10.5,
    )
    data["for_analysis"] = {
        "for_ratio": for_result.for_ratio,
        "for_status": for_result.for_status,
        "total_monthly_obligation": for_result.monthly_obligation,
        "gross_monthly_income": for_result.income_used,
        "recommendation": for_result.recommendation,
        "risk_level": for_result.risk_level,
    }
    logs.append(
        _log(
            agent,
            f"FOR Ratio: {for_result.for_ratio:.1f}% | Status: {for_result.for_status}",
            level="SUCCESS" if for_result.for_ratio < 50 else "WARN",
        )
    )
    return data, logs


async def _enrichment_task_cibil(
    snap: Dict[str, Any],
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """CIBIL enhanced credit bureau check — async I/O-bound."""
    agent = "ENRICHMENT"
    logs: List[Dict[str, Any]] = []
    data: Dict[str, Any] = {}

    cin = snap.get("cin", "")
    promoter_details = snap.get("promoter_details", [])
    if not cin or not promoter_details:
        logs.append(
            _log(agent, "Insufficient data for CIBIL check (need CIN and promoter details)", level="WARN")
        )
        return data, logs

    promoter_names = [p.get("name", "") for p in promoter_details]
    promoter_pans = [p.get("pan", "") for p in promoter_details if p.get("pan")]
    cibil_res = await get_cibil_score_enhanced(
        company_name=snap.get("company_name", ""),
        cin=cin,
        promoter_names=promoter_names,
        promoter_pans=promoter_pans if promoter_pans else None,
        use_mock=True,
        mock_scenario="good",
    )
    cibil_score = cibil_res.get("company_score", 0)
    data["cibil_report"] = cibil_res
    data["cibil_score"] = cibil_score
    data["cibil_enhanced"] = cibil_res.get("cibil_enhanced")
    logs.append(
        _log(
            agent,
            f"CIBIL Enhanced: Score: {cibil_score} | Avg Director Score: {cibil_res.get('average_director_score', 0):.0f}",
            level="SUCCESS" if cibil_score >= 650 else "WARN",
        )
    )
    return data, logs


async def _enrichment_task_mca(
    snap: Dict[str, Any],
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """MCA master data & director network analysis — async I/O-bound."""
    agent = "ENRICHMENT"
    logs: List[Dict[str, Any]] = []
    data: Dict[str, Any] = {}

    cin = snap.get("cin", "")
    if not cin:
        logs.append(_log(agent, "CIN not available — skipping MCA verification", level="WARN"))
        return data, logs

    mca_res = await run_mca_scraper(
        cin=cin,
        company_name=snap.get("company_name", ""),
        use_mock=True,
        mock_scenario="clean",
    )
    data["mca_report"] = mca_res
    data["director_network"] = mca_res
    data["mca_status"] = mca_res.get("company_status")
    logs.append(
        _log(
            agent,
            f"MCA: Status: {mca_res.get('company_status')} | Risk Level: {mca_res.get('network_risk_level')}",
            level="SUCCESS" if mca_res.get("network_risk_level") != "HIGH" else "ERROR",
        )
    )
    return data, logs


async def _enrichment_task_rcu(
    snap: Dict[str, Any],
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """RCU field verification — async I/O-bound."""
    agent = "ENRICHMENT"
    logs: List[Dict[str, Any]] = []

    rcu_updates = await run_rcu_verification_agent(snap)
    rcu_status = rcu_updates.get("rcu_status", "UNKNOWN")
    logs.append(
        _log(
            agent,
            f"RCU: {rcu_status} | Score: {rcu_updates.get('rcu_verification', {}).get('overall_score', 0)}/100",
            level="SUCCESS" if rcu_status == "POSITIVE" else "WARN",
        )
    )
    # rcu_updates itself is the data dict (contains rcu_status, rcu_verification, etc.)
    return rcu_updates, logs


async def _enrichment_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parallel enrichment pipeline — all 6 independent tools fire concurrently.

    Dependency analysis
    -------------------
    Every sub-task reads exclusively from the incoming state snapshot and
    writes to a distinct set of state keys.  There are zero cross-task data
    dependencies, making full concurrency safe:

      Task          Input keys read            Output keys written
      ──────────────────────────────────────────────────────────────
      NTS           sector / sector_classific.  nts_analysis
      WorkingCap    current_assets / liabilit.  working_capital_analysis
      FOR           existing_loans / revenue    for_analysis
      CIBIL         cin / promoter_details       cibil_report, cibil_score
      MCA           cin / company_name           mca_report, director_network
      RCU           (full state snapshot)        rcu_status, rcu_verification

    Implementation notes
    --------------------
    • asyncio.to_thread wraps sync-bound functions (NTS, WC, FOR) so they
      run in a thread-pool and never block the event loop.
    • asyncio.wait_for gives every task its own hard deadline
      (_ENRICHMENT_TASK_TIMEOUT_SECS); a single slow API cannot stall others.
    • All results are returned explicitly in the node's return dict — no
      direct state mutation — ensuring LangGraph's state merge is the sole
      source of truth.
    """
    agent = "ENRICHMENT"
    logs: List[Dict[str, Any]] = [
        _log(agent, "⚡ Launching 6 enrichment tasks in parallel (NTS · WC · FOR · CIBIL · MCA · RCU)...")
    ]

    # Immutable snapshot so all coroutines share a stable, consistent view
    # of the state without risking concurrent mutation.
    snap = dict(state)

    _timeout = _ENRICHMENT_TASK_TIMEOUT_SECS
    task_definitions: List[Tuple[str, Any]] = [
        ("NTS",          _enrichment_task_nts(snap)),
        ("WorkingCap",   _enrichment_task_wc(snap)),
        ("FOR",          _enrichment_task_for(snap)),
        ("CIBIL",        _enrichment_task_cibil(snap)),
        ("MCA",          _enrichment_task_mca(snap)),
        ("RCU",          _enrichment_task_rcu(snap)),
    ]

    timed_coroutines = [
        asyncio.wait_for(coro, timeout=_timeout)
        for _, coro in task_definitions
    ]

    # gather with return_exceptions=True so a failure in one task never
    # cancels the others — partial enrichment is better than none.
    raw_results = await asyncio.gather(*timed_coroutines, return_exceptions=True)

    merged_data: Dict[str, Any] = {}
    for (task_name, _), result in zip(task_definitions, raw_results):
        if isinstance(result, asyncio.TimeoutError):
            logs.append(
                _log(agent, f"{task_name} timed out after {_timeout}s — result omitted", level="ERROR")
            )
        elif isinstance(result, Exception):
            logs.append(_log(agent, f"{task_name} failed: {result}", level="ERROR"))
        else:
            task_data, task_logs = result
            merged_data.update(task_data)
            logs.extend(task_logs)

    logs.append(_log(agent, "✅ Parallel enrichment pipeline complete.", level="SUCCESS"))

    # Return ALL enrichment data explicitly so LangGraph's state merge
    # propagates every key — no silent state mutations.
    return {
        **merged_data,
        "logs": logs,
        "agent_statuses": {**state.get("agent_statuses", {}), "enrichment": "DONE"},
    }


async def _scorer_node(state: Dict[str, Any]) -> Dict[str, Any]:
    updates = await run_scorer_agent(state)
    updates["agent_statuses"] = {
        **state.get("agent_statuses", {}),
        **updates.get("agent_statuses", {}),
        "scorer": "DONE",
    }
    return updates


async def _compliance_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compliance Agent Node - Runs all Indian regulatory checks.
    
    If hard reject is triggered, sets state to skip scoring.
    """
    updates = await run_compliance_agent(state)
    updates["agent_statuses"] = {
        **state.get("agent_statuses", {}),
        **updates.get("agent_statuses", {}),
        "compliance": "DONE",
    }
    return updates


def _check_compliance_result(state: Dict[str, Any]) -> str:
    """
    Conditional edge for compliance checks.
    
    GATE 1: Compliance Check
    If hard reject, skip all scoring/capacity checks and go directly to CAM with rejection.
    """
    compliance_result = state.get("compliance_result", {})
    hard_reject = compliance_result.get("hard_reject", False)
    
    if hard_reject:
        return "HARD_REJECT"
    return "CONTINUE"


async def _bank_capacity_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    GATE 2: Bank Capacity Check
    Assess if bank can lend based on exposure limits and regulatory constraints.
    """
    from models.schemas import BankConfig
    
    # Get bank configuration from state or use defaults
    # In production, this would come from database/configuration service
    bank_config_dict = state.get("bank_config", {
        "tier1_capital": 50000.0,  # ₹50,000 Cr
        "tier2_capital": 10000.0,  # ₹10,000 Cr
        "current_crar": 14.5,  # 14.5%
        "anbc": 400000.0,  # ₹4,00,000 Cr
        "psl_achieved_pct": 37.5,  # 37.5% (below 40% target)
        "pca_status": False,  # Not under PCA
        "sector_exposures": {},
        "sector_limits": {
            "Manufacturing": 25.0,
            "Services": 20.0,
            "Trading": 15.0,
            "Construction": 10.0,
            "Real Estate": 8.0,
        },
        "internal_policy_thresholds": {
            "min_business_vintage_years": 3,
            "min_promoter_contribution_pct": 25.0,
            "min_collateral_coverage": 1.25,
        },
    })
    
    bank_config = BankConfig(**bank_config_dict)
    
    updates = await run_bank_capacity_agent(state, bank_config)
    updates["agent_statuses"] = {
        **state.get("agent_statuses", {}),
        **updates.get("agent_statuses", {}),
        "bank_capacity": "DONE",
    }
    return updates


def _check_capacity_result(state: Dict[str, Any]) -> str:
    """
    Conditional edge for bank capacity check.
    
    GATE 2: If bank cannot lend (exposure limits breached), skip scoring and go to CAM.
    """
    capacity_result = state.get("capacity_result", {})
    can_lend = capacity_result.get("can_lend", True)
    
    if not can_lend:
        return "HARD_REJECT"
    return "CONTINUE"


async def _explainable_scoring_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    GATE 3: Explainable Scoring
    Calculate transparent credit score with RBI benchmarks and industry comparisons.
    """
    updates = await run_explainable_scoring_agent(state)
    updates["agent_statuses"] = {
        **state.get("agent_statuses", {}),
        **updates.get("agent_statuses", {}),
        "explainable_scoring": "DONE",
    }
    return updates


async def _decision_engine_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    GATE 4: Final Decision Engine
    
    Calculate final approved amount as minimum of:
    - Requested amount
    - Score-based maximum (from decision band)
    - Capacity-based maximum (from exposure limits)
    
    Create EnhancedFinalDecision with full explainability.
    """
    from models.schemas import EnhancedFinalDecision, AmountCalculation, DecisionGate
    
    logs: List[Dict[str, Any]] = []
    agent = "DECISION_ENGINE"
    
    logs.append(_log(agent, "Running 4-gate decision engine..."))
    
    # Gather inputs from previous gates
    compliance_result = state.get("compliance_result", {})
    capacity_result = state.get("capacity_result", {})
    scorecard_result = state.get("scorecard_result", {})
    
    loan_amount_requested = state.get("loan_amount_requested", 0.0)
    
    # ═══════════════════════════════════════════════════════════════════════
    # GATE 1: Compliance (already checked, but document here)
    # ═══════════════════════════════════════════════════════════════════════
    gate1_pass = not compliance_result.get("hard_reject", False)
    gate1_reason = "All compliance checks passed" if gate1_pass else compliance_result.get("hard_reject_reason", "")
    
    # ═══════════════════════════════════════════════════════════════════════
    # GATE 2: Capacity (already checked, but document here)
    # ═══════════════════════════════════════════════════════════════════════
    gate2_pass = capacity_result.get("can_lend", True)
    gate2_reason = capacity_result.get("capacity_remarks", "") if gate2_pass else "Exposure limits breached"
    
    # ═══════════════════════════════════════════════════════════════════════
    # GATE 3: Credit Score Decision Band
    # ═══════════════════════════════════════════════════════════════════════
    final_score = scorecard_result.get("final_score", 0.0)
    decision_band = scorecard_result.get("decision_band", "REJECT")
    
    # Map decision band to score-based max amount multiplier
    score_based_multipliers = {
        "APPROVE": 1.0,  # Full amount
        "REFER_TO_COMMITTEE": 0.75,  # 75% of requested
        "CONDITIONAL_APPROVE": 0.50,  # 50% of requested
        "REJECT": 0.0,
        "HARD_REJECT": 0.0,
    }
    
    score_multiplier = score_based_multipliers.get(decision_band, 0.0)
    score_based_max = loan_amount_requested * score_multiplier
    gate3_reason = f"Score {final_score:.1f}/100 → {decision_band} → {score_multiplier*100:.0f}% of requested amount"
    
    logs.append(_log(agent, f"Gate 3 - Score: {final_score:.1f} → Decision Band: {decision_band}"))
    
    # ═══════════════════════════════════════════════════════════════════════
    # GATE 4: Amount Calculation
    # ═══════════════════════════════════════════════════════════════════════
    capacity_max = capacity_result.get("suggested_max_amount", loan_amount_requested)
    
    # Final amount is minimum of all constraints
    final_approved_amount = min(loan_amount_requested, score_based_max, capacity_max)
    
    # Determine which constraint was binding
    if final_approved_amount == 0:
        binding_constraint = "Rejected due to compliance/capacity/score"
        final_decision = "REJECT"
    elif final_approved_amount == capacity_max < score_based_max:
        binding_constraint = f"Capacity Limit (₹{capacity_max:,.0f})"
        final_decision = decision_band
    elif final_approved_amount == score_based_max < loan_amount_requested:
        binding_constraint = f"Score-Based Limit ({decision_band})"
        final_decision = decision_band
    else:
        binding_constraint = "None - Full amount approved"
        final_decision = "APPROVE"
    
    gate4_reason = f"Final amount: min(Requested: ₹{loan_amount_requested:,.0f}, Score-based: ₹{score_based_max:,.0f}, Capacity: ₹{capacity_max:,.0f}) = ₹{final_approved_amount:,.0f}"
    
    logs.append(_log(agent, gate4_reason))
    logs.append(_log(agent, f"Binding constraint: {binding_constraint}"))
    logs.append(_log(agent, f"Final decision: {final_decision} for ₹{final_approved_amount:,.0f}", level="SUCCESS"))
    
    # Create EnhancedFinalDecision using current schema fields
    enhanced_decision = EnhancedFinalDecision(
        recommendation=final_decision,
        deciding_gate=DecisionGate.GATE_4_AMOUNT,
        amount_calculation=AmountCalculation(
            requested_amount=loan_amount_requested,
            score_based_max=score_based_max,
            score_based_reason=gate3_reason,
            capacity_based_max=capacity_max,
            capacity_based_reason=gate2_reason,
            final_approved_amount=final_approved_amount,
            amount_reduced=final_approved_amount < loan_amount_requested,
            reduction_reason=binding_constraint if final_approved_amount < loan_amount_requested else None,
        ),
        rejection_reason=gate1_reason if final_decision == "REJECT" else None,
        rejection_gate="GATE_1_COMPLIANCE" if not gate1_pass else ("GATE_2_CAPACITY" if not gate2_pass else None),
        final_interest_rate_pct=capacity_result.get("final_interest_rate_pct", 0.0) if final_approved_amount > 0 else 0.0,
        explainability={
            "gate_1_compliance": {"passed": gate1_pass, "reason": gate1_reason},
            "gate_2_capacity": {"passed": gate2_pass, "reason": gate2_reason},
            "gate_3_score": {"score": final_score, "decision_band": decision_band, "reason": gate3_reason},
            "gate_4_amount": {"reason": gate4_reason, "binding_constraint": binding_constraint},
            "scorecard_summary": {
                "final_score": final_score,
                "decision_band": decision_band,
                "approved_amount": final_approved_amount,
            },
            "top_strengths": [],
            "top_concerns": [],
            "committee_notes": f"{final_decision}: ₹{final_approved_amount:,.0f} approved at {capacity_result.get('final_interest_rate_pct', 0.0):.2f}% p.a.",
        },
    )
    
    return {
        "enhanced_final_decision": enhanced_decision.model_dump(),
        "final_decision": final_decision,
        "approved_amount": final_approved_amount,
        "logs": logs,
        "agent_statuses": {
            **state.get("agent_statuses", {}),
            "decision_engine": "DONE",
        }
    }


async def _cam_node(state: Dict[str, Any]) -> Dict[str, Any]:
    updates = await run_cam_generator(state)
    updates["agent_statuses"] = {
        **state.get("agent_statuses", {}),
        **updates.get("agent_statuses", {}),
        "cam_generator": "DONE",
    }
    return updates


# ─── Graph Construction ───────────────────────────────────────────────────────

def build_graph() -> Any:
    """
    Build and compile the LangGraph StateGraph with 4-gate decision logic.
    
    Pipeline Flow:
    1. Forgery Check (Gateway)
    2. Parallel Ingest + Research
    3. Arbitration Check (if conflict detected)
    4. Enrichment (RCU, CIBIL, MCA, FOR, WC, NTS)
    5. GATE 1: Compliance (Hard reject → CAM | Pass → Continue)
    6. GATE 2: Bank Capacity (Can't lend → CAM | Can lend → Continue)
    7. GATE 3: Explainable Scoring (Transparent scorecard with RBI benchmarks)
    8. GATE 4: Decision Engine (Calculate final amount with 4-gate explainability)
    9. CAM Generator (Final report)
    """
    workflow = StateGraph(dict)

    # Add all nodes
    workflow.add_node("forgery_check", _forgery_check_node)
    workflow.add_node("parallel_ingest_research", _parallel_node)
    workflow.add_node("arbitration_check", _arbitration_check_node)
    workflow.add_node("enrichment", _enrichment_node)
    workflow.add_node("compliance", _compliance_node)
    workflow.add_node("bank_capacity", _bank_capacity_node)
    workflow.add_node("explainable_scoring", _explainable_scoring_node)
    workflow.add_node("decision_engine", _decision_engine_node)
    workflow.add_node("cam_generator", _cam_node)

    # Entry point
    workflow.set_entry_point("forgery_check")
    
    # Flow: Forgery → Parallel Ingest/Research
    workflow.add_conditional_edges(
        "forgery_check",
        _check_forgery_result,
        {
            "REJECT": END,
            "CONTINUE": "parallel_ingest_research"
        }
    )
    
    # Flow: Parallel → Arbitration → Enrichment → GATE 1 (Compliance)
    workflow.add_edge("parallel_ingest_research", "arbitration_check")
    workflow.add_edge("arbitration_check", "enrichment")
    workflow.add_edge("enrichment", "compliance")
    
    # GATE 1: Compliance Check
    workflow.add_conditional_edges(
        "compliance",
        _check_compliance_result,
        {
            "HARD_REJECT": "cam_generator",  # Skip capacity/scoring if compliance hard rejects
            "CONTINUE": "bank_capacity"
        }
    )
    
    # GATE 2: Bank Capacity Check
    workflow.add_conditional_edges(
        "bank_capacity",
        _check_capacity_result,
        {
            "HARD_REJECT": "cam_generator",  # Skip scoring if bank can't lend
            "CONTINUE": "explainable_scoring"
        }
    )
    
    # GATE 3 & 4: Scoring → Decision Engine → CAM
    workflow.add_edge("explainable_scoring", "decision_engine")
    workflow.add_edge("decision_engine", "cam_generator")
    workflow.add_edge("cam_generator", END)

    return workflow.compile()


# ─── Orchestrator Entry Point ─────────────────────────────────────────────────

async def run_orchestrator(
    initial_state: Dict[str, Any],
    on_update: Optional[Callable[[Dict[str, Any]], None]] = None,
) -> Dict[str, Any]:
    """
    Run the full LangGraph appraisal pipeline.

    Args:
        initial_state: Full CreditAppraisalState-compatible dict.
        on_update: Async callback invoked after each agent completes,
                   receives the current state snapshot.
    Returns:
        Final state dict after all agents have run.
    """
    app = build_graph()
    current_state = dict(initial_state)
    current_state["status"] = "RUNNING"
    current_state["started_at"] = current_state.get("started_at") or datetime.now().isoformat()

    if on_update:
        await on_update(current_state)

    # Stream state updates from LangGraph
    try:
        async for event in app.astream(current_state):
            # event is a dict of {node_name: updates}
            for node_name, node_updates in event.items():
                if not isinstance(node_updates, dict):
                    continue

                # Merge logs (append, don't replace)
                existing_logs = current_state.get("logs", [])
                new_logs = node_updates.get("logs", [])
                merged_logs = existing_logs + new_logs

                current_state.update(node_updates)
                current_state["logs"] = merged_logs

                if on_update:
                    await on_update(current_state)
    except Exception as exc:
        error_log = _log("ORCHESTRATOR", f"Pipeline error: {exc}", level="ERROR")
        current_state.setdefault("logs", []).append(error_log)
        current_state["status"] = "FAILED"
        current_state["error_message"] = str(exc)
        if on_update:
            await on_update(current_state)
        return current_state

    current_state["status"] = "COMPLETED"
    current_state["completed_at"] = datetime.now().isoformat()
    current_state.setdefault("logs", []).append(
        _log("ORCHESTRATOR", "✅ Full appraisal pipeline complete.", level="SUCCESS")
    )

    if on_update:
        await on_update(current_state)

    return current_state
