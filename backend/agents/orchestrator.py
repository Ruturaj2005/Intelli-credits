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
from typing import Any, Callable, Dict, List, Optional

from anthropic import Anthropic
from langgraph.graph import StateGraph, END

from agents.ingestor_agent import run_ingestor_agent
from agents.research_agent import run_research_agent
from agents.scorer_agent import run_scorer_agent
from agents.cam_generator import run_cam_generator
from agents.rcu_agent import run_rcu_verification_agent
from tools.cibil_api import fetch_cibil_report
from tools.mca_scraper import fetch_mca_report
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


def _call_claude(prompt: str, max_tokens: int = 2048) -> str:
    client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    msg = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )
    return msg.content[0].text


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
    """Run Claude arbitration step to reconcile conflicting signals."""
    logs: List[Dict[str, Any]] = [
        _log("ARBITRATOR", "⚡ CONFLICT DETECTED between Ingestor and Research findings.", level="WARN"),
        _log("ARBITRATOR", "Running Claude arbitration to reconcile signals..."),
    ]

    prompt = ARBITRATION_PROMPT.format(
        ingestor_output=json.dumps(state.get("extracted_financials", {}), indent=2)[:5000],
        research_output=json.dumps(state.get("research_findings", {}), indent=2)[:5000],
    )

    try:
        raw = _call_claude(prompt)
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


async def _enrichment_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Enrichment pipeline: Run all specialized verification tools.
    - RCU verification
    - CIBIL checks
    - MCA verification
    - FOR calculation
    - Working capital analysis
    - NTS sector analysis
    """
    logs: List[Dict[str, Any]] = []
    agent = "ENRICHMENT"

    logs.append(_log(agent, "Starting enrichment pipeline with specialized tools..."))

    # ── Step 1: NTS Sector Analysis ────────────────────────────────────────
    try:
        logs.append(_log(agent, "Analyzing sector health (NTS)..."))
        sector = state.get("sector_classification") or state.get("sector", "")
        if sector:
            nts_result = analyze_sector(sector)
            state["nts_analysis"] = {
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
                    f"NTS Analysis: {nts_result.classification.status} | Risk Score: {nts_result.classification.risk_score}/100",
                    level="SUCCESS",
                )
            )
        else:
            logs.append(_log(agent, "Sector not specified - skipping NTS analysis", level="WARN"))
    except Exception as exc:
        logs.append(_log(agent, f"NTS analysis error: {exc}", level="ERROR"))

    # ── Step 2: Working Capital Analysis ───────────────────────────────────
    try:
        logs.append(_log(agent, "Analyzing working capital position..."))
        current_assets = state.get("current_assets", 0)
        current_liabilities = state.get("current_liabilities", 0)

        if current_assets > 0 and current_liabilities > 0:
            wc_result = analyze_working_capital(
                company_name=state.get("company_name", ""),
                current_assets=current_assets,
                current_liabilities=current_liabilities,
                cash_and_bank=state.get("cash_and_bank", 0),
                debtors=state.get("debtors", 0),
                inventory=state.get("inventory", 0),
                creditors=state.get("creditors", 0),
                short_term_loans=state.get("short_term_loans", 0),
                annual_revenue=state.get("extracted_financials", {}).get("financials", {}).get("revenue_3yr", [0, 0, 0])[-1],
                total_assets=state.get("total_assets", 0),
            )
            state["working_capital_analysis"] = {
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
                    f"Working Capital: {wc_result.liquidity_status} | Score: {wc_result.liquidity_score}/100 | "
                    f"Current Ratio: {wc_result.ratios.current_ratio:.2f}",
                    level="SUCCESS",
                )
            )
        else:
            logs.append(_log(agent, "Insufficient data for working capital analysis", level="WARN"))
    except Exception as exc:
        logs.append(_log(agent, f"Working capital analysis error: {exc}", level="ERROR"))

    # ── Step 3: FOR (Fixed Obligation Ratio) Calculation ───────────────────
    try:
        logs.append(_log(agent, "Calculating Fixed Obligation Ratio (FOR)..."))
        existing_loans = state.get("existing_loans", [])
        financials = state.get("extracted_financials", {}).get("financials", {})
        revenue = financials.get("revenue_3yr", [0])[-1] if financials.get("revenue_3yr") else 0

        if revenue > 0:
            # Estimate monthly income
            gross_monthly_income = (revenue * 10000000) / 12  # Convert Cr to rupees, then monthly

            # Convert existing loans to LoanDetails format
            loan_details = []
            for loan in existing_loans:
                if loan.get("emi", 0) > 0:
                    loan_details.append(
                        LoanDetails(
                            outstanding_amount=loan.get("outstanding_amount", 0) * 10000000,
                            interest_rate=loan.get("interest_rate", 10.0),
                            remaining_tenure_months=loan.get("remaining_tenure_months", 60),
                        )
                    )

            # Calculate FOR with proposed loan
            proposed_loan = state.get("loan_amount_requested", 0) * 10000000  # Cr to rupees
            for_result = calculate_for(
                gross_monthly_income=gross_monthly_income,
                existing_loans=loan_details if loan_details else None,
                proposed_loan_amount=proposed_loan if proposed_loan > 0 else None,
                proposed_tenure=60,  # Default 5 years
                proposed_interest_rate=10.5,  # Default rate
            )

            state["for_analysis"] = {
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
        else:
            logs.append(_log(agent, "Insufficient revenue data for FOR calculation", level="WARN"))
    except Exception as exc:
        logs.append(_log(agent, f"FOR calculation error: {exc}", level="ERROR"))

    # ── Step 4: CIBIL Credit Bureau Check ──────────────────────────────────
    try:
        logs.append(_log(agent, "Fetching CIBIL credit report..."))
        cin = state.get("cin", "")
        promoter_details = state.get("promoter_details", [])

        if cin and promoter_details:
            promoter_names = [p.get("name", "") for p in promoter_details]
            promoter_pans = [p.get("pan", "") for p in promoter_details if p.get("pan")]

            cibil_report = fetch_cibil_report(
                company_name=state.get("company_name", ""),
                cin=cin,
                promoter_names=promoter_names,
                promoter_pans=promoter_pans if promoter_pans else None,
                use_mock=True,  # Use mock data for now; set to False in production
                mock_scenario="good",  # Can be dynamic based on other signals
            )

            state["cibil_report"] = {
                "company_score": cibil_report.company_score.score if cibil_report.company_score else 0,
                "company_wilful_defaulter": cibil_report.company_score.wilful_defaulter if cibil_report.company_score else False,
                "average_director_score": cibil_report.average_director_score,
                "lowest_director_score": cibil_report.lowest_director_score,
                "any_director_defaulter": cibil_report.any_director_wilful_defaulter,
                "report_date": cibil_report.report_date.isoformat(),
            }
            logs.append(
                _log(
                    agent,
                    f"CIBIL: Company Score: {cibil_report.company_score.score if cibil_report.company_score else 'N/A'} | "
                    f"Avg Director Score: {cibil_report.average_director_score:.0f}",
                    level="SUCCESS" if cibil_report.average_director_score >= 700 else "WARN",
                )
            )
        else:
            logs.append(_log(agent, "Insufficient data for CIBIL check (need CIN and promoter details)", level="WARN"))
    except Exception as exc:
        logs.append(_log(agent, f"CIBIL check error: {exc}", level="ERROR"))

    # ── Step 5: MCA (Ministry of Corporate Affairs) Verification ───────────
    try:
        logs.append(_log(agent, "Fetching MCA company master data..."))
        cin = state.get("cin", "")

        if cin:
            mca_report = fetch_mca_report(
                cin=cin,
                company_name=state.get("company_name", ""),
                use_mock=True,  # Use mock data for now
                mock_scenario="clean",  # Can be dynamic
            )

            state["mca_report"] = {
                "company_status": mca_report.company_master.company_status,
                "incorporation_date": mca_report.company_master.incorporation_date.isoformat() if mca_report.company_master.incorporation_date else "",
                "authorized_capital": mca_report.company_master.authorized_capital,
                "paid_up_capital": mca_report.company_master.paid_up_capital,
                "total_directors": len(mca_report.directors),
                "disqualified_directors": sum(1 for d in mca_report.directors if d.is_disqualified),
                "total_charges": len(mca_report.charges),
                "unsatisfied_charges": sum(1 for c in mca_report.charges if c.charge_status == "UNSATISFIED"),
                "strike_off_notice": mca_report.compliance.strike_off_notice,
                "defaulter_list": mca_report.compliance.defaulter_list,
            }

            # Update incorporation_date in state if not already set
            if not state.get("incorporation_date") and mca_report.company_master.incorporation_date:
                state["incorporation_date"] = mca_report.company_master.incorporation_date.isoformat()

            logs.append(
                _log(
                    agent,
                    f"MCA: Status: {mca_report.company_master.company_status} | Directors: {len(mca_report.directors)} | "
                    f"Charges: {len(mca_report.charges)}",
                    level="SUCCESS" if mca_report.company_master.company_status == "ACTIVE" else "ERROR",
                )
            )
        else:
            logs.append(_log(agent, "CIN not available - skipping MCA verification", level="WARN"))
    except Exception as exc:
        logs.append(_log(agent, f"MCA verification error: {exc}", level="ERROR"))

    # ── Step 6: RCU (Risk Containment Unit) Verification ───────────────────
    try:
        logs.append(_log(agent, "Running RCU field verification..."))
        rcu_updates = await run_rcu_verification_agent(state)
        state.update(rcu_updates)
        rcu_status = rcu_updates.get("rcu_status", "UNKNOWN")
        logs.append(
            _log(
                agent,
                f"RCU Verification: {rcu_status} | Score: {rcu_updates.get('rcu_verification', {}).get('overall_score', 0)}/100",
                level="SUCCESS" if rcu_status == "POSITIVE" else "WARN",
            )
        )
    except Exception as exc:
        logs.append(_log(agent, f"RCU verification error: {exc}", level="ERROR"))

    logs.append(_log(agent, "Enrichment pipeline complete.", level="SUCCESS"))

    return {
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
    """Build and compile the LangGraph StateGraph."""
    workflow = StateGraph(dict)

    workflow.add_node("parallel_ingest_research", _parallel_node)
    workflow.add_node("arbitration_check", _arbitration_check_node)
    workflow.add_node("enrichment", _enrichment_node)
    workflow.add_node("scorer", _scorer_node)
    workflow.add_node("cam_generator", _cam_node)

    workflow.set_entry_point("parallel_ingest_research")
    workflow.add_edge("parallel_ingest_research", "arbitration_check")
    workflow.add_edge("arbitration_check", "enrichment")
    workflow.add_edge("enrichment", "scorer")
    workflow.add_edge("scorer", "cam_generator")
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
