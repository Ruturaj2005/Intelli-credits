"""
Agent 4 — CAM Generator Agent
Generates a professional Credit Appraisal Memo as a .docx Word document
using python-docx, covering all mandatory sections.
"""
from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import google.generativeai as genai
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from docx.shared import Inches, Pt, RGBColor

from utils.prompts import CAM_EXECUTIVE_SUMMARY_PROMPT


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _log(agent: str, message: str, level: str = "INFO") -> Dict[str, Any]:
    return {
        "timestamp": datetime.now().strftime("%H:%M:%S"),
        "agent": agent,
        "message": message,
        "level": level,
    }


def _call_gemini_for_summary(state: Dict[str, Any]) -> str:
    """Ask Gemini to write the Executive Summary section."""
    scores = state.get("five_cs_scores", {})
    research = state.get("research_findings", {})
    extracted = state.get("extracted_financials", {})
    rec = state.get("final_recommendation", {})

    five_cs_summary = "\n".join(
        f"  {c.upper()}: {scores.get(c, {}).get('score', 0)}/100"
        for c in ["character", "capacity", "capital", "collateral", "conditions"]
    )
    red_flags = extracted.get("red_flags", [])
    key_findings = [
        f"[{f.get('severity')}] {f.get('finding')} ({f.get('source', '')})"
        for f in research.get("key_findings", [])[:5]
    ]

    prompt = CAM_EXECUTIVE_SUMMARY_PROMPT.format(
        company_name=state.get("company_name", ""),
        sector=state.get("sector", ""),
        recommendation=rec.get("recommendation", "REJECT"),
        loan_amount=rec.get("suggested_loan_amount", 0),
        interest_rate=rec.get("suggested_interest_rate", "N/A"),
        weighted_total=round(scores.get("weighted_total", 0), 1),
        five_cs_summary=five_cs_summary,
        red_flags="\n".join(f"  - {f}" for f in red_flags[:10]) or "  None",
        research_findings="\n".join(f"  - {f}" for f in key_findings) or "  None",
    )
    try:
        genai.configure(api_key=os.environ["GEMINI_API_KEY"])
        model = genai.GenerativeModel('gemini-1.5-pro')
        
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                max_output_tokens=2048,
                temperature=0.7,
            )
        )
        return response.text
    except Exception:
        return (
            f"This Credit Appraisal Memo summarises the credit assessment for "
            f"{state.get('company_name', 'the applicant')}. "
            f"The final recommendation is {rec.get('recommendation', 'PENDING')} "
            f"based on a Five Cs weighted score of {round(scores.get('weighted_total', 0), 1)}/100. "
            f"{rec.get('decision_reason', '')}"
        )


# ─── Document Styling ─────────────────────────────────────────────────────────

def _set_heading_style(paragraph, level: int = 1):
    run = paragraph.runs[0] if paragraph.runs else paragraph.add_run()
    run.bold = True
    if level == 1:
        run.font.size = Pt(16)
        run.font.color.rgb = RGBColor(0x00, 0xD4, 0xAA)  # Teal
    elif level == 2:
        run.font.size = Pt(13)
        run.font.color.rgb = RGBColor(0x00, 0x99, 0xFF)  # Blue
    else:
        run.font.size = Pt(11)
        run.font.color.rgb = RGBColor(0x4A, 0x60, 0x70)  # Muted


def _add_section_heading(doc: Document, text: str, level: int = 1):
    p = doc.add_heading(text, level=level)
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    if p.runs:
        p.runs[0].font.color.rgb = (
            RGBColor(0x00, 0xD4, 0xAA) if level == 1
            else RGBColor(0x00, 0x99, 0xFF)
        )
    return p


def _add_table(doc: Document, headers: List[str], rows: List[List[str]]):
    table = doc.add_table(rows=1, cols=len(headers))
    table.style = "Table Grid"
    hdr_row = table.rows[0].cells
    for i, h in enumerate(headers):
        hdr_row[i].text = h
        hdr_row[i].paragraphs[0].runs[0].bold = True if hdr_row[i].paragraphs[0].runs else None

    for row_data in rows:
        row = table.add_row().cells
        for i, cell_text in enumerate(row_data):
            row[i].text = str(cell_text)
    doc.add_paragraph()  # Spacing after table


def _severity_emoji(severity: str) -> str:
    return {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "🟢"}.get(severity.upper(), "⚪")


def _rec_label(rec: str) -> str:
    labels = {
        "APPROVE": "✅ APPROVED",
        "CONDITIONAL APPROVE": "⚠ CONDITIONAL APPROVAL",
        "REJECT": "❌ REJECTED",
    }
    return labels.get(rec, rec)


# ─── Section Builders ─────────────────────────────────────────────────────────

def _build_cover_page(doc: Document, state: Dict[str, Any], rec: Dict[str, Any]):
    doc.add_paragraph()
    title = doc.add_heading("CREDIT APPRAISAL MEMORANDUM", 0)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER

    doc.add_paragraph()
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run(state.get("company_name", "").upper())
    run.bold = True
    run.font.size = Pt(20)

    doc.add_paragraph()
    meta = [
        f"Job ID: {state.get('job_id', 'N/A')}",
        f"Sector: {state.get('sector', 'N/A')}",
        f"Date: {datetime.now().strftime('%d %B %Y')}",
        f"Loan Requested: Rs. {state.get('loan_amount_requested', 0):.2f} Cr",
        f"Prepared by: Intelli-Credit AI Engine",
    ]
    for line in meta:
        p = doc.add_paragraph(line)
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER

    doc.add_paragraph()

    # Decision stamp
    recommendation = rec.get("recommendation", "REJECT")
    stamp_text = _rec_label(recommendation)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run(stamp_text)
    run.bold = True
    run.font.size = Pt(18)
    if "APPROVE" in recommendation and "REJECT" not in recommendation:
        run.font.color.rgb = RGBColor(0x00, 0xD4, 0xAA)
    else:
        run.font.color.rgb = RGBColor(0xEF, 0x47, 0x6F)

    if rec.get("suggested_loan_amount"):
        p2 = doc.add_paragraph()
        p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r2 = p2.add_run(
            f"Rs. {rec.get('suggested_loan_amount', 0):.2f} Cr  |  "
            f"{rec.get('suggested_interest_rate', 'N/A')}"
        )
        r2.bold = True
        r2.font.size = Pt(14)

    doc.add_page_break()


def _build_executive_summary(doc: Document, summary_text: str):
    _add_section_heading(doc, "1. Executive Summary")
    doc.add_paragraph(summary_text)
    doc.add_paragraph()


def _build_company_background(doc: Document, extracted: Dict[str, Any]):
    _add_section_heading(doc, "2. Company Background")
    name = extracted.get("company_name", "N/A")
    promoters = extracted.get("promoters", [])
    doc.add_paragraph(f"Company Name: {name}")
    doc.add_paragraph(f"Promoters / Key Management: {', '.join(promoters) or 'Not identified'}")
    collateral = extracted.get("collateral", {})
    doc.add_paragraph(
        f"Collateral Offered: {collateral.get('type', 'N/A')} — "
        f"Estimated Value: Rs. {collateral.get('estimated_value', 0):.2f} Cr"
    )
    doc.add_paragraph()


def _build_financial_analysis(doc: Document, extracted: Dict[str, Any], loan_amount: float):
    _add_section_heading(doc, "3. Financial Analysis")

    fin = extracted.get("financials", {})
    revenue = fin.get("revenue_3yr", [0, 0, 0])
    ebitda = fin.get("ebitda_3yr", [0, 0, 0])
    pat = fin.get("pat_3yr", [0, 0, 0])

    years = ["FY22", "FY23", "FY24"]

    # Pad to 3 years
    while len(revenue) < 3:
        revenue = [0] + revenue
    while len(ebitda) < 3:
        ebitda = [0] + ebitda
    while len(pat) < 3:
        pat = [0] + pat

    _add_section_heading(doc, "3.1 3-Year Financial Performance (Rs. Crore)", level=2)
    headers = ["Metric"] + years
    rows = [
        ["Revenue (Net Sales)"] + [f"{v:.2f}" for v in revenue[-3:]],
        ["EBITDA"] + [f"{v:.2f}" for v in ebitda[-3:]],
        ["PAT (Net Profit)"] + [f"{v:.2f}" for v in pat[-3:]],
    ]
    _add_table(doc, headers, rows)

    _add_section_heading(doc, "3.2 Key Financial Ratios", level=2)
    ratio_headers = ["Ratio", "Value", "Benchmark", "Assessment"]
    dscr = fin.get("dscr", 0)
    d2e = fin.get("debt_to_equity", 0)
    ratio_rows = [
        ["DSCR", f"{dscr:.2f}x", "> 1.25x", "✅ Adequate" if dscr >= 1.25 else "❌ Weak"],
        ["Debt-to-Equity", f"{d2e:.2f}x", "< 3x", "✅ Acceptable" if d2e <= 3 else "❌ Over-leveraged"],
        ["Net Worth", f"Rs. {fin.get('net_worth', 0):.2f} Cr", "—", "—"],
        ["Total Debt", f"Rs. {fin.get('total_debt', 0):.2f} Cr", "—", "—"],
        ["CFO", f"Rs. {fin.get('cash_flow_from_operations', 0):.2f} Cr", "> 0", "✅ Positive" if fin.get("cash_flow_from_operations", 0) > 0 else "❌ Negative"],
    ]
    _add_table(doc, ratio_headers, ratio_rows)


def _build_five_cs(doc: Document, scores: Dict[str, Any]):
    _add_section_heading(doc, "4. Five Cs of Credit Assessment")

    cs_labels = {
        "character": "Character (Promoter Integrity & Track Record)",
        "capacity": "Capacity (Ability to Repay)",
        "capital": "Capital (Financial Strength)",
        "collateral": "Collateral (Security Cover)",
        "conditions": "Conditions (Market & Sector Outlook)",
    }
    weights = {"character": "25%", "capacity": "30%", "capital": "20%", "collateral": "15%", "conditions": "10%"}

    for c_key, c_label in cs_labels.items():
        c_data = scores.get(c_key, {})
        score = c_data.get("score", 0)
        reasons = c_data.get("reasons", [])
        weight = weights.get(c_key, "")

        _add_section_heading(doc, f"4.{list(cs_labels.keys()).index(c_key)+1}  {c_label}  [{weight} weight]", level=2)
        p = doc.add_paragraph()
        r = p.add_run(f"Score: {score}/100")
        r.bold = True
        r.font.size = Pt(13)

        for reason in reasons:
            doc.add_paragraph(f"• {reason}", style="List Bullet")
        doc.add_paragraph()


def _build_score_breakdown_table(doc: Document, scores: Dict[str, Any]):
    _add_section_heading(doc, "5. Score Breakdown", level=1)
    headers = ["Five C", "Score (/100)", "Weight", "Weighted Score"]
    cs = ["character", "capacity", "capital", "collateral", "conditions"]
    rows = []
    for c in cs:
        c_data = scores.get(c, {})
        s = float(c_data.get("score", 0))
        w = float(c_data.get("weight", 0))
        rows.append([c.capitalize(), f"{s:.0f}", f"{w*100:.0f}%", f"{s*w:.1f}"])
    rows.append(["TOTAL", "", "", f"{scores.get('weighted_total', 0):.1f}"])
    _add_table(doc, headers, rows)


def _build_risk_flags(doc: Document, extracted: Dict[str, Any]):
    _add_section_heading(doc, "6. Risk Flags")
    flags = extracted.get("red_flags", [])
    if not flags:
        doc.add_paragraph("No significant risk flags identified from document analysis.")
        return
    for i, flag in enumerate(flags, 1):
        doc.add_paragraph(f"{i}. {flag}", style="List Number")
    doc.add_paragraph()


def _build_research_findings(doc: Document, research: Dict[str, Any]):
    _add_section_heading(doc, "7. Research & Due Diligence Findings")

    doc.add_paragraph(f"Litigation Risk: {research.get('litigation_risk', 'N/A')}")
    doc.add_paragraph(f"Promoter Integrity Score: {research.get('promoter_integrity_score', 'N/A')}/100")
    doc.add_paragraph(f"Sector Outlook: {research.get('sector_outlook', 'N/A')}")

    headwinds = research.get("sector_headwinds", [])
    if headwinds:
        _add_section_heading(doc, "Sector Headwinds", level=2)
        for hw in headwinds:
            doc.add_paragraph(f"• {hw}", style="List Bullet")

    findings = research.get("key_findings", [])
    if findings:
        _add_section_heading(doc, "Key Findings", level=2)
        headers = ["#", "Finding", "Severity", "Source", "Date"]
        rows = [
            [
                str(i),
                f.get("finding", "")[:80],
                f"{_severity_emoji(f.get('severity','LOW'))} {f.get('severity','LOW')}",
                f.get("source", "N/A"),
                f.get("date", "N/A"),
            ]
            for i, f in enumerate(findings, 1)
        ]
        _add_table(doc, headers, rows)

    impact = research.get("recommendation_impact", "")
    if impact:
        doc.add_paragraph(f"Impact on Decision: {impact}")
    doc.add_paragraph()


def _build_recommendation(doc: Document, state: Dict[str, Any], rec: Dict[str, Any], scores: Dict[str, Any]):
    _add_section_heading(doc, "8. Final Recommendation")

    recommendation = rec.get("recommendation", "REJECT")
    p = doc.add_paragraph()
    r = p.add_run(_rec_label(recommendation))
    r.bold = True
    r.font.size = Pt(16)

    doc.add_paragraph(f"Suggested Loan Amount: Rs. {rec.get('suggested_loan_amount', 0):.2f} Crore")
    doc.add_paragraph(f"Suggested Interest Rate: {rec.get('suggested_interest_rate', 'N/A')}")
    doc.add_paragraph(f"Five Cs Weighted Score: {scores.get('weighted_total', 0):.1f}/100")
    doc.add_paragraph()

    doc.add_paragraph(rec.get("decision_reason", ""))
    doc.add_paragraph()

    overrides = rec.get("overriding_factors", [])
    if overrides:
        _add_section_heading(doc, "Overriding Factors / Conditions", level=2)
        for factor in overrides:
            doc.add_paragraph(f"• {factor}", style="List Bullet")
    doc.add_paragraph()

    # Turnaround time
    started = state.get("started_at", "")
    completed = state.get("completed_at", datetime.now().isoformat())
    if started:
        try:
            from datetime import timezone
            t0 = datetime.fromisoformat(started)
            t1 = datetime.fromisoformat(completed)
            delta = t1 - t0
            mins, secs = divmod(int(delta.total_seconds()), 60)
            doc.add_paragraph(
                f"Appraisal completed in: {mins}m {secs}s  "
                f"(Industry average: 10–15 business days)"
            )
        except Exception:
            pass


def _build_appendix(doc: Document, state: Dict[str, Any]):
    doc.add_page_break()
    _add_section_heading(doc, "Appendix — Raw Data")

    extracted = state.get("extracted_financials", {})
    research = state.get("research_findings", {})

    _add_section_heading(doc, "A1. Extracted Financials (raw)", level=2)
    doc.add_paragraph(json.dumps(extracted, indent=2))

    _add_section_heading(doc, "A2. Research Findings (raw)", level=2)
    doc.add_paragraph(json.dumps(research, indent=2))

    _add_section_heading(doc, "A3. Arbitration Record", level=2)
    arb = state.get("arbitration_result", {})
    doc.add_paragraph(json.dumps(arb, indent=2) if arb else "No arbitration was required.")

    searches = research.get("_search_queries", [])
    if searches:
        _add_section_heading(doc, "A4. Web Search Queries Executed", level=2)
        for s in searches:
            doc.add_paragraph(f"[{s.get('label')}] {s.get('query')}", style="List Bullet")


# ─── Main Agent Function ──────────────────────────────────────────────────────

async def run_cam_generator(state: Dict[str, Any]) -> Dict[str, Any]:
    """LangGraph node: CAM Generator Agent."""
    logs: List[Dict[str, Any]] = []
    agent = "CAM"

    company_name = state.get("company_name", "Company")
    job_id = state.get("job_id", "unknown")
    scores = state.get("five_cs_scores", {})
    rec = state.get("final_recommendation", {})
    extracted = state.get("extracted_financials", {})
    research = state.get("research_findings", {})

    logs.append(_log(agent, f"Generating Credit Appraisal Memo for '{company_name}'..."))

    # ── Get executive summary from Gemini ─────────────────────────────────────
    logs.append(_log(agent, "Requesting Executive Summary from Gemini..."))
    exec_summary = _call_gemini_for_summary(state)
    logs.append(_log(agent, "Executive Summary generated."))

    # ── Build Word document ───────────────────────────────────────────────────
    doc = Document()

    # Page margins
    for section in doc.sections:
        section.top_margin = Inches(1)
        section.bottom_margin = Inches(1)
        section.left_margin = Inches(1.2)
        section.right_margin = Inches(1.2)

    logs.append(_log(agent, "Building CAM document sections..."))

    state_with_completed = {**state, "completed_at": state.get("completed_at") or datetime.now().isoformat()}

    _build_cover_page(doc, state_with_completed, rec)
    _build_executive_summary(doc, exec_summary)
    _build_company_background(doc, extracted)
    _build_financial_analysis(doc, extracted, state.get("loan_amount_requested", 0))
    _build_five_cs(doc, scores)
    _build_score_breakdown_table(doc, scores)
    _build_risk_flags(doc, extracted)
    _build_research_findings(doc, research)
    _build_recommendation(doc, state_with_completed, rec, scores)
    _build_appendix(doc, state_with_completed)

    # ── Save document ─────────────────────────────────────────────────────────
    upload_dir = os.getenv("UPLOAD_DIR", "./uploads")
    output_dir = Path(upload_dir) / job_id
    output_dir.mkdir(parents=True, exist_ok=True)

    safe_name = "".join(c for c in company_name if c.isalnum() or c in " _-").strip().replace(" ", "_")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    cam_filename = f"CAM_{safe_name}_{timestamp}.docx"
    cam_path = str(output_dir / cam_filename)

    doc.save(cam_path)

    logs.append(_log(agent, f"CAM document saved: {cam_filename}", level="SUCCESS"))
    logs.append(_log(agent, "CAM Generator Agent DONE.", level="SUCCESS"))

    return {
        "cam_path": cam_path,
        "completed_at": datetime.now().isoformat(),
        "status": "COMPLETED",
        "logs": logs,
        "agent_statuses": {**state.get("agent_statuses", {}), "cam_generator": "DONE"},
    }
