"""
Agent 3 — Risk Scorer Agent (Enhanced with Dynamic Weighting)

Scores credit applications using:
1. Dynamic weight engine - context-aware weight adjustment
2. Red flag engine - auto-rejection triggers
3. Five Cs of Credit scoring (legacy mode) or Expanded 9-parameter model
4. SHAP-style attribution for explainability

Author: Credit Intelligence System
"""
from __future__ import annotations

import json
import os
from datetime import datetime, date
from typing import Any, Dict, List, Optional

import numpy as np
from anthropic import Anthropic

from tools.gst_analyser import compute_revenue_cagr, compute_collateral_cover
from utils.prompts import SCORER_PROMPT

# Import new scoring modules
from scoring.dynamic_weights import (
    compute_dynamic_weights,
    DynamicWeightConfig,
    RiskProfile,
    compute_weighted_score,
)
from scoring.red_flag_engine import (
    evaluate_red_flags,
    RedFlagResult,
    RedFlagSeverity,
)


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


# ─── Company Age Calculation ─────────────────────────────────────────────────

def _calculate_company_age(incorporation_date_str: Optional[str]) -> float:
    """Calculate company age in years from incorporation date string."""
    if not incorporation_date_str:
        return 5.0  # Default assumption if not available

    try:
        # Try various date formats
        for fmt in ["%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d"]:
            try:
                inc_date = datetime.strptime(incorporation_date_str, fmt).date()
                age_days = (date.today() - inc_date).days
                return max(age_days / 365.25, 0.1)
            except ValueError:
                continue
        return 5.0
    except Exception:
        return 5.0


# ─── FOR Calculation ─────────────────────────────────────────────────────────

def _calculate_for_ratio(
    monthly_income: float,
    existing_emis: float,
    proposed_emi: float,
) -> Dict[str, Any]:
    """
    Calculate Fixed Obligation to Income Ratio.

    FOR = (Total EMI Obligations) / (Gross Monthly Income) * 100
    """
    if monthly_income <= 0:
        return {
            "gross_monthly_income": monthly_income,
            "existing_emi_total": existing_emis,
            "proposed_emi": proposed_emi,
            "for_ratio": 100.0,
            "for_status": "UNKNOWN",
            "recommendation": "Cannot calculate - income data missing",
        }

    total_obligation = existing_emis + proposed_emi
    for_ratio = (total_obligation / monthly_income) * 100

    if for_ratio < 40:
        status = "HEALTHY"
        recommendation = "Borrower has comfortable debt servicing capacity"
    elif for_ratio < 50:
        status = "STRAINED"
        recommendation = "Consider reducing loan amount or extending tenure"
    else:
        status = "OVER-LEVERAGED"
        recommendation = "EMI burden exceeds safe threshold - review required"

    return {
        "gross_monthly_income": round(monthly_income, 2),
        "existing_emi_total": round(existing_emis, 2),
        "proposed_emi": round(proposed_emi, 2),
        "for_ratio": round(for_ratio, 2),
        "for_status": status,
        "recommendation": recommendation,
    }


# ─── SHAP-style Attribution ───────────────────────────────────────────────────

def compute_shap_attributions(
    scores: Dict[str, Any],
    dynamic_weights: Optional[Dict[str, float]] = None,
) -> Dict[str, float]:
    """
    Compute SHAP-style feature attributions for scores.

    If dynamic_weights provided, use those; otherwise fall back to weights in scores.
    """
    baseline = 50.0  # Expected score for a "neutral" applicant
    cs = ["character", "capacity", "capital", "collateral", "conditions"]
    attributions: Dict[str, float] = {}

    for c in cs:
        c_data = scores.get(c, {})
        c_score = float(c_data.get("score", 0))
        # Use dynamic weight if available, else fallback to score weight
        if dynamic_weights and c in dynamic_weights:
            c_weight = dynamic_weights[c]
        else:
            c_weight = float(c_data.get("weight", 0))
        # Deviation from baseline, weighted
        attributions[c] = round((c_score - baseline) * c_weight, 3)

    return attributions


def compute_weighted_total(
    scores: Dict[str, Any],
    dynamic_weights: Optional[Dict[str, float]] = None,
) -> float:
    """
    Compute weighted total from scores using dynamic weights if available.
    """
    cs = ["character", "capacity", "capital", "collateral", "conditions"]
    total = 0.0

    for c in cs:
        c_data = scores.get(c, {})
        c_score = float(c_data.get("score", 0))
        # Use dynamic weight if available
        if dynamic_weights and c in dynamic_weights:
            c_weight = dynamic_weights[c]
        else:
            c_weight = float(c_data.get("weight", 0))
        total += c_score * c_weight

    return round(total, 2)


# ─── Auto-Override Logic (Enhanced with Red Flag Engine) ─────────────────────

def check_auto_override(
    research_findings: Dict[str, Any],
    fraud_flags: List[str],
    scores: Dict[str, Any],
    red_flag_result: Optional[RedFlagResult] = None,
) -> Optional[str]:
    """
    Returns an override reason string if any AUTO-REJECT conditions are met.
    Now integrates with the Red Flag Engine for comprehensive checks.
    """
    # First, check red flag engine results
    if red_flag_result and red_flag_result.should_auto_reject:
        return f"Auto-Reject triggered by Red Flag Engine: {red_flag_result.rejection_reason}"

    # HIGH severity litigation or criminal finding
    for finding in research_findings.get("key_findings", []):
        if finding.get("severity") == "HIGH":
            return (
                f"Auto-Reject triggered: HIGH severity research finding — "
                f"'{finding.get('finding', '')}'. Source: {finding.get('source', 'N/A')}. "
                "This overrides all financial metrics."
            )

    # HIGH severity GST fraud flag
    high_fraud = [f for f in fraud_flags if "high" in f.lower() or "gst fraud" in f.lower()]
    if high_fraud:
        return (
            f"Auto-Reject triggered: HIGH severity fraud signal detected — "
            f"{high_fraud[0]}. Cannot approve under any circumstance."
        )

    return None


# ─── Qualitative Override ─────────────────────────────────────────────────────

def apply_qualitative_adjustment(
    scores: Dict[str, Any],
    qualitative_notes: str,
) -> Dict[str, Any]:
    """
    Adjust scores based on qualitative notes using simple heuristics.
    """
    if not qualitative_notes.strip():
        return scores

    notes_lower = qualitative_notes.lower()
    adjustments: List[str] = []

    # Factory/Operations capacity signals
    if any(phrase in notes_lower for phrase in ["40% capacity", "low capacity", "idle capacity", "underutilised"]):
        adjustments.append("Capacity score reduced: Low factory utilisation noted by credit officer")

    # Promoter evasiveness
    if any(phrase in notes_lower for phrase in ["evasive", "refused to answer", "unresponsive"]):
        adjustments.append("Character score reduced: Management evasiveness noted in field visit")

    # Positive signals
    if any(phrase in notes_lower for phrase in ["additional orders", "new contract", "export order"]):
        adjustments.append("Capacity score boosted: Upcoming revenue visibility from new orders")

    # Provident Fund compliance
    if any(phrase in notes_lower for phrase in ["pf default", "pf dues", "epf arrears"]):
        adjustments.append("Character score reduced: Statutory compliance issues with PF")

    # Factory visit insights
    if any(phrase in notes_lower for phrase in ["good housekeeping", "well maintained", "organized"]):
        adjustments.append("Operations score boosted: Positive factory visit observations")

    return {"_qualitative_adjustments": adjustments, **scores}


# ─── Default Score Fallback ───────────────────────────────────────────────────

def _default_scores(
    loan_amount: float = 0,
    dynamic_weights: Optional[Dict[str, float]] = None,
) -> Dict[str, Any]:
    """Generate default scores with dynamic weights if available."""
    weights = dynamic_weights or {
        "character": 0.25,
        "capacity": 0.30,
        "capital": 0.20,
        "collateral": 0.15,
        "conditions": 0.10,
    }

    return {
        "character":   {"score": 50, "reasons": ["Insufficient data"], "weight": weights.get("character", 0.25)},
        "capacity":    {"score": 50, "reasons": ["Insufficient data"], "weight": weights.get("capacity", 0.30)},
        "capital":     {"score": 50, "reasons": ["Insufficient data"], "weight": weights.get("capital", 0.20)},
        "collateral":  {"score": 50, "reasons": ["Insufficient data"], "weight": weights.get("collateral", 0.15)},
        "conditions":  {"score": 50, "reasons": ["Insufficient data"], "weight": weights.get("conditions", 0.10)},
        "weighted_total": 50.0,
        "recommendation": "REJECT",
        "suggested_loan_amount": 0.0,
        "suggested_interest_rate": "N/A",
        "decision_reason": "Unable to generate score due to insufficient data.",
        "overriding_factors": [],
    }


# ─── Extract Risk Indicators ─────────────────────────────────────────────────

def _extract_risk_indicators(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract risk indicators from state for dynamic weight calculation.
    """
    extracted_fin = state.get("extracted_financials", {})
    research_findings = state.get("research_findings", {})
    company_profile = state.get("company_profile", {})

    fin = extracted_fin.get("financials", {})

    # Company age
    incorporation_date = (
        company_profile.get("incorporation_date") or
        state.get("incorporation_date") or
        extracted_fin.get("incorporation_date")
    )
    company_age = _calculate_company_age(incorporation_date)

    # Loan amount in Crores
    loan_amount_cr = state.get("loan_amount_requested", 0)

    # Sector status from research
    sector_outlook = research_findings.get("sector_outlook", "NEUTRAL")

    # Check for first-time borrower (if no CIBIL data available)
    is_first_time = not bool(state.get("cibil_score"))

    # Check for defaults
    has_defaults = any(
        "default" in str(f).lower() or "npa" in str(f).lower()
        for f in state.get("fraud_flags", [])
    )

    # CIBIL score (if available)
    cibil_score = state.get("cibil_score")

    # GST discrepancy
    gst_disc = extracted_fin.get("gst_vs_bank_discrepancy", {})
    gst_discrepancy_pct = 0.0
    if gst_disc.get("detected"):
        # Try to extract percentage from details
        details = gst_disc.get("details", "")
        try:
            import re
            match = re.search(r"(\d+(?:\.\d+)?)\s*%", details)
            if match:
                gst_discrepancy_pct = float(match.group(1))
        except Exception:
            # If HIGH severity, assume high discrepancy
            if gst_disc.get("severity") == "HIGH":
                gst_discrepancy_pct = 25.0
            elif gst_disc.get("severity") == "MEDIUM":
                gst_discrepancy_pct = 15.0

    # Net worth and DSCR
    net_worth = fin.get("net_worth", 0)
    dscr = fin.get("dscr", 1.5)

    return {
        "company_age_years": company_age,
        "loan_amount_cr": loan_amount_cr,
        "sector_status": sector_outlook,
        "is_first_time_borrower": is_first_time,
        "has_existing_defaults": has_defaults,
        "cibil_score": cibil_score,
        "gst_discrepancy_percent": gst_discrepancy_pct,
        "net_worth": net_worth,
        "dscr": dscr,
        "incorporation_date": incorporation_date,
    }


# ─── Main Agent Function ──────────────────────────────────────────────────────

async def run_scorer_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    LangGraph node: Enhanced Risk Scorer Agent with Dynamic Weighting.

    This agent now:
    1. Evaluates red flags first (gateway check)
    2. Computes dynamic weights based on risk profile
    3. Scores using Five Cs with dynamic weights
    4. Provides SHAP attributions for explainability
    """
    logs: List[Dict[str, Any]] = []
    agent = "SCORER"

    company_name = state.get("company_name", "Unknown Company")
    extracted_fin = state.get("extracted_financials", {})
    research_findings = state.get("research_findings", {})
    fraud_flags = state.get("fraud_flags", [])
    qualitative_notes = state.get("qualitative_notes", "")
    loan_amount = state.get("loan_amount_requested", 0)
    arbitration = state.get("arbitration_result", {})
    sector = state.get("sector", "")

    logs.append(_log(agent, f"Starting ENHANCED risk scoring for '{company_name}'..."))

    # ─── Step 1: Extract Risk Indicators ─────────────────────────────────────
    risk_indicators = _extract_risk_indicators(state)
    logs.append(_log(agent, f"Company age: {risk_indicators['company_age_years']:.1f} years"))
    logs.append(_log(agent, f"Sector outlook: {risk_indicators['sector_status']}"))

    # ─── Step 2: Red Flag Evaluation (Gateway Check) ─────────────────────────
    logs.append(_log(agent, "Running Red Flag Engine..."))

    red_flag_result = evaluate_red_flags(
        cibil_score=risk_indicators.get("cibil_score"),
        is_wilful_defaulter=False,  # Would come from CIBIL API
        for_ratio=0.0,  # Not calculated yet
        net_worth=risk_indicators.get("net_worth", 0),
        dscr=risk_indicators.get("dscr", 1.5),
        company_age_years=risk_indicators.get("company_age_years", 5.0),
        loan_amount_cr=risk_indicators.get("loan_amount_cr", 1.0),
        company_status=state.get("company_profile", {}).get("company_status", "ACTIVE"),
        sector=sector,
        is_negative_list=False,  # Would come from sector analysis
        gst_discrepancy_percent=risk_indicators.get("gst_discrepancy_percent", 0),
    )

    red_flag_dict = red_flag_result.to_dict()

    if red_flag_result.total_flag_count > 0:
        logs.append(_log(
            agent,
            f"Red Flag Engine: {red_flag_result.recommendation}",
            level="WARN" if not red_flag_result.should_auto_reject else "ERROR"
        ))
        for flag in red_flag_result.flags[:3]:  # Log top 3 flags
            logs.append(_log(agent, f"  [{flag.severity.value}] {flag.name}: {flag.description}", level="WARN"))
    else:
        logs.append(_log(agent, "Red Flag Engine: CLEAR - No red flags detected", level="SUCCESS"))

    # ─── Step 3: Compute Dynamic Weights ─────────────────────────────────────
    logs.append(_log(agent, "Computing dynamic weights based on risk profile..."))

    dynamic_config = compute_dynamic_weights(
        company_age_years=risk_indicators.get("company_age_years", 5.0),
        loan_amount_cr=risk_indicators.get("loan_amount_cr", 1.0),
        sector_status=risk_indicators.get("sector_status", "STABLE"),
        is_first_time_borrower=risk_indicators.get("is_first_time_borrower", False),
        has_existing_defaults=risk_indicators.get("has_existing_defaults", False),
        cibil_score=risk_indicators.get("cibil_score"),
        scoring_mode="FIVE_CS",  # Use Five Cs for backward compatibility
    )

    dynamic_weights = dynamic_config.final_weights
    dynamic_config_dict = dynamic_config.to_dict()

    logs.append(_log(
        agent,
        f"Risk Profile: {dynamic_config.risk_profile.value} (Score: {dynamic_config.risk_score}/100)"
    ))

    # Log significant weight adjustments
    for justification in dynamic_config.weight_justifications[1:4]:  # Skip first (profile summary)
        logs.append(_log(agent, f"  {justification}"))

    # ─── Step 4: Check for Auto-Reject before scoring ────────────────────────
    if red_flag_result.should_auto_reject:
        logs.append(_log(agent, "AUTO-REJECT triggered by Red Flag Engine", level="ERROR"))

        scores = _default_scores(loan_amount, dynamic_weights)
        scores["recommendation"] = "REJECT"
        scores["decision_reason"] = red_flag_result.rejection_reason
        scores["overriding_factors"] = [
            f"[{flag.code}] {flag.name}: {flag.description}"
            for flag in red_flag_result.flags
            if flag.severity == RedFlagSeverity.CRITICAL
        ]

        return {
            "five_cs_scores": scores,
            "final_recommendation": {
                "recommendation": "REJECT",
                "suggested_loan_amount": 0.0,
                "suggested_interest_rate": "N/A",
                "weighted_total": 0.0,
                "decision_reason": red_flag_result.rejection_reason,
                "overriding_factors": scores["overriding_factors"],
            },
            "dynamic_weight_config": dynamic_config_dict,
            "risk_profile": dynamic_config.risk_profile.value,
            "red_flag_evaluation": red_flag_dict,
            "pre_override_scores": {},
            "override_applied": True,
            "logs": logs,
            "agent_statuses": {**state.get("agent_statuses", {}), "scorer": "DONE"},
        }

    # ─── Step 5: Compute supplementary metrics ───────────────────────────────
    fin = extracted_fin.get("financials", {})
    revenue_3yr = fin.get("revenue_3yr", [])
    cagr = compute_revenue_cagr(revenue_3yr)
    cagr_str = f"{cagr:.1f}%" if cagr is not None else "N/A"
    logs.append(_log(agent, f"Revenue CAGR (2yr): {cagr_str} | DSCR: {fin.get('dscr', 0):.2f}x"))

    collateral_val = extracted_fin.get("collateral", {}).get("estimated_value", 0)
    cover = compute_collateral_cover(collateral_val, loan_amount)
    cover_str = f"{cover:.2f}x" if cover else "N/A"
    logs.append(_log(agent, f"Collateral cover: {cover_str}"))

    # ─── Step 6: Arbitration note ────────────────────────────────────────────
    arbitration_note = ""
    if arbitration.get("conflict_detected"):
        arbitration_note = (
            f"Arbitration result: {arbitration.get('reconciliation_reasoning', '')} "
            f"Adjusted risk weight: {arbitration.get('adjusted_risk_weight', 1.0)}x "
            f"(Favors: {arbitration.get('favors', 'N/A')})"
        )
        logs.append(_log(agent, f"Incorporating arbitration: {arbitration_note}", level="WARN"))

    # ─── Step 7: Build enhanced scorer prompt ────────────────────────────────
    financials_json = json.dumps(extracted_fin, indent=2)
    research_json = json.dumps(research_findings, indent=2)

    # Add dynamic weight context to prompt
    weight_context = f"""
DYNAMIC WEIGHT CONTEXT:
- Risk Profile: {dynamic_config.risk_profile.value} (Score: {dynamic_config.risk_score}/100)
- Weights to use:
  * Character: {dynamic_weights.get('character', 0.25)*100:.1f}%
  * Capacity: {dynamic_weights.get('capacity', 0.30)*100:.1f}%
  * Capital: {dynamic_weights.get('capital', 0.20)*100:.1f}%
  * Collateral: {dynamic_weights.get('collateral', 0.15)*100:.1f}%
  * Conditions: {dynamic_weights.get('conditions', 0.10)*100:.1f}%
- Risk Factors: {'; '.join(dynamic_config.weight_justifications[1:4])}

IMPORTANT: Use the weights specified above in your scoring. These weights have been
dynamically adjusted based on the borrower's risk profile.
"""

    prompt = SCORER_PROMPT.format(
        financials_json=financials_json[:8_000],
        research_json=research_json[:6_000],
        qualitative_notes=qualitative_notes or "None provided.",
        arbitration_note=arbitration_note or "No arbitration required.",
    )

    # Prepend dynamic weight context
    prompt = weight_context + "\n\n" + prompt

    logs.append(_log(agent, "Calling Claude for Five Cs scoring with dynamic weights..."))

    try:
        raw_response = _call_claude(prompt, max_tokens=6144)
        scores = _extract_json(raw_response)
        if not scores:
            logs.append(_log(agent, "JSON parse error — using default scores.", level="WARN"))
            scores = _default_scores(loan_amount, dynamic_weights)
    except Exception as exc:
        logs.append(_log(agent, f"Claude API error: {exc}", level="ERROR"))
        scores = _default_scores(loan_amount, dynamic_weights)

    # ─── Step 8: Apply dynamic weights to scores ─────────────────────────────
    for c in ["character", "capacity", "capital", "collateral", "conditions"]:
        c_data = scores.get(c, {})
        if c_data and c in dynamic_weights:
            c_data["weight"] = dynamic_weights[c]
            c_data["dynamic_weight_applied"] = True
            scores[c] = c_data

    # ─── Step 9: Log individual C scores ─────────────────────────────────────
    for c in ["character", "capacity", "capital", "collateral", "conditions"]:
        c_data = scores.get(c, {})
        weight_str = f"(w={c_data.get('weight', 0)*100:.0f}%)"
        logs.append(
            _log(agent, f"{c.upper()} score: {c_data.get('score', 0)}/100 {weight_str} — "
                 f"{c_data.get('reasons', [''])[0]}")
        )

    # ─── Step 10: Apply auto-override check ──────────────────────────────────
    override_reason = check_auto_override(
        research_findings, fraud_flags, scores, red_flag_result
    )
    if override_reason:
        logs.append(_log(agent, f"OVERRIDE: {override_reason}", level="ERROR"))
        scores["recommendation"] = "REJECT"
        overrides = scores.get("overriding_factors", [])
        if override_reason not in overrides:
            overrides.insert(0, override_reason)
        scores["overriding_factors"] = overrides

    # ─── Step 11: Recompute weighted total with dynamic weights ──────────────
    scores["weighted_total"] = compute_weighted_total(scores, dynamic_weights)

    # ─── Step 12: SHAP attributions ──────────────────────────────────────────
    scores["shap_attributions"] = compute_shap_attributions(scores, dynamic_weights)

    # ─── Step 13: Supplementary metrics for Results page ─────────────────────
    scores["supplementary"] = {
        "revenue_cagr_pct": round(cagr, 2) if cagr else 0.0,
        "collateral_cover": round(cover, 2) if cover else 0.0,
        "dscr": fin.get("dscr", 0),
        "debt_to_equity": fin.get("debt_to_equity", 0),
        "promoter_integrity_score": research_findings.get("promoter_integrity_score", 0),
        "company_age_years": risk_indicators.get("company_age_years", 0),
        "risk_profile": dynamic_config.risk_profile.value,
    }

    # ─── Step 14: Qualitative override BEFORE/AFTER ──────────────────────────
    pre_override_scores: Dict[str, Any] = {}
    override_applied = False
    if qualitative_notes.strip():
        qual_data = apply_qualitative_adjustment({}, qualitative_notes)
        if qual_data.get("_qualitative_adjustments"):
            override_applied = True
            pre_override_scores = {
                "note": "Qualitative notes were factored into Claude's scoring.",
                "adjustments": qual_data["_qualitative_adjustments"],
            }
            for adj in qual_data["_qualitative_adjustments"]:
                logs.append(_log(agent, f"Qualitative adjustment: {adj}", level="WARN"))

    # ─── Step 15: Add escalation note if required ────────────────────────────
    if red_flag_result.escalation_required:
        scores["escalation_required"] = True
        scores["escalation_reason"] = f"{len(red_flag_result.flags_by_severity.get('HIGH', []))} high-severity flags require management approval"
        logs.append(_log(agent, f"ESCALATION REQUIRED: {scores['escalation_reason']}", level="WARN"))

    rec = scores.get("recommendation", "REJECT")
    total = scores.get("weighted_total", 0)
    logs.append(
        _log(
            agent,
            f"Scoring complete — Recommendation: {rec} | Weighted Total: {total:.1f}/100 | "
            f"Risk Profile: {dynamic_config.risk_profile.value}",
            level="SUCCESS",
        )
    )
    logs.append(_log(
        agent,
        f"Suggested: Rs.{scores.get('suggested_loan_amount', 0):.1f} Cr @ {scores.get('suggested_interest_rate', 'N/A')}",
        level="SUCCESS",
    ))
    logs.append(_log(agent, "Enhanced Risk Scorer Agent DONE.", level="SUCCESS"))

    return {
        "five_cs_scores": scores,
        "final_recommendation": {
            "recommendation": scores.get("recommendation"),
            "suggested_loan_amount": scores.get("suggested_loan_amount"),
            "suggested_interest_rate": scores.get("suggested_interest_rate"),
            "weighted_total": scores.get("weighted_total"),
            "decision_reason": scores.get("decision_reason"),
            "overriding_factors": scores.get("overriding_factors", []),
            "escalation_required": scores.get("escalation_required", False),
        },
        "dynamic_weight_config": dynamic_config_dict,
        "risk_profile": dynamic_config.risk_profile.value,
        "red_flag_evaluation": red_flag_dict,
        "pre_override_scores": pre_override_scores,
        "override_applied": override_applied,
        "logs": logs,
        "agent_statuses": {**state.get("agent_statuses", {}), "scorer": "DONE"},
    }
