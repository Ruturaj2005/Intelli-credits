"""
Agent 1 — Ingestor Agent
Parses uploaded financial documents, runs GST reconciliation,
and extracts structured financial data using Gemini.
"""
from __future__ import annotations

import json
import os
import re
from datetime import datetime
from typing import Any, Dict, List

import google.generativeai as genai

from tools.schema_mapper import SchemaMapper, SCHEMA_REGISTRY

from tools.gst_analyser import analyse_gst_documents
from tools.pdf_parser import format_documents_for_llm
from utils.prompts import INGESTOR_PROMPT
from tools.mda_sentiment_analyzer import analyze_mda_sentiment, MDASection
from tools.document_forgery_detector import screen_documents_batch


def _log(agent: str, message: str, level: str = "INFO") -> Dict[str, Any]:
    return {
        "timestamp": datetime.now().strftime("%H:%M:%S"),
        "agent": agent,
        "message": message,
        "level": level,
    }


def _call_gemini(prompt: str, max_tokens: int = 4096) -> str:
    """Call Gemini API and return the raw response text."""
    genai.configure(api_key=os.environ["GEMINI_API_KEY"])
    model = genai.GenerativeModel('gemini-1.5-pro')
    
    response = model.generate_content(
        prompt,
        generation_config=genai.types.GenerationConfig(
            max_output_tokens=max_tokens,
            temperature=0.7,
        )
    )
    return response.text


def _extract_json(text: str) -> Dict[str, Any]:
    """Extract the first JSON object found in Gemini's response."""
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

def _filter_low_confidence_metrics(
    financials: Dict[str, Any],
    documents: List[Dict[str, Any]],
    confidence_threshold: float = 0.7
) -> Dict[str, Any]:
    """
    Filter financial metrics based on entity-level confidence scores.
    
    Metrics with confidence < threshold are flagged for manual review.
    
    Args:
        financials: Extracted financial data
        documents: Parsed documents with confidence info
        confidence_threshold: Minimum acceptable confidence (default: 0.7)
    
    Returns:
        Filtering summary with counts and flagged metrics
    """
    flagged_list = []
    accepted_count = 0
    total_count = 0
    
    # Aggregate all financial entities from documents
    all_entities = {}
    for doc in documents:
        entities = doc.get("financial_entities", {})
        if entities:
            all_entities.update(entities)
    
    # Check each entity's confidence
    for metric_name, metric_data in all_entities.items():
        total_count += 1
        
        if isinstance(metric_data, dict):
            entity_conf = metric_data.get("entity_confidence", 1.0)
            
            if entity_conf < confidence_threshold:
                flagged_list.append({
                    "metric": metric_name,
                    "value": metric_data.get("value"),
                    "confidence": round(entity_conf, 3),
                    "reason": f"Confidence {entity_conf:.1%} below threshold {confidence_threshold:.0%}"
                })
            else:
                accepted_count += 1
    
    return {
        "total_count": total_count,
        "accepted_count": accepted_count,
        "filtered_count": len(flagged_list),
        "flagged_count": len(flagged_list),
        "flagged_list": flagged_list,
    }


def _compile_document_quality_summary(documents: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Compile overall document quality statistics.
    
    Returns summary of confidence levels across all documents.
    """
    total_docs = len(documents)
    high_confidence = 0  # >= 0.7
    moderate_confidence = 0  # 0.5 - 0.7
    low_confidence = 0  # < 0.5
    manual_review_required = 0
    
    confidence_details = []
    
    for doc in documents:
        conf = doc.get("overall_confidence", 1.0)
        reliability = doc.get("reliability_score", "UNKNOWN")
        status = doc.get("extraction_status", "UNKNOWN")
        
        confidence_details.append({
            "file_name": doc.get("file_name", "unknown"),
            "confidence": round(conf, 3),
            "reliability": reliability,
            "status": status,
        })
        
        if conf >= 0.7:
            high_confidence += 1
        elif conf >= 0.5:
            moderate_confidence += 1
        else:
            low_confidence += 1
        
        if doc.get("requires_manual_review"):
            manual_review_required += 1
    
    return {
        "total_documents": total_docs,
        "high_confidence_count": high_confidence,
        "moderate_confidence_count": moderate_confidence,
        "low_confidence_count": low_confidence,
        "manual_review_required": manual_review_required,
        "document_details": confidence_details,
    }


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

async def _extract_mda_section(full_text: str) -> str:
    """Extract MD&A section from annual report text."""
    # Look for common MD&A headers in Indian annual reports
    patterns = [
        r"Management Discussion.*?(?=(?:Standalone|Consolidated|Report on)|$)",
        r"Management's Discussion.*?(?=(?:Standalone|Report)|$)",
        r"MD&A.*?(?=(?:Annexure|Schedule|Notes to)|$)",
    ]
    for pat in patterns:
        match = re.search(pat, full_text, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(0)[:8000]  # cap at 8k chars
    return full_text[:4000]  # fallback: use first 4k chars


# ─── Main Agent Function (LangGraph node) ────────────────────────────────────

async def run_ingestor_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    LangGraph node: Ingestor Agent.
    Input : state dict (full CreditAppraisalState)
    Output: partial state dict with updated keys
    """
    logs: List[Dict[str, Any]] = []
    agent = "INGESTOR"

    # ── Step 0: Forgery screening ─────────────────────────────────────
    uploaded_files = state.get("uploaded_files", []) or state.get("raw_document_bytes", [])
    if uploaded_files:
        forgery_check = screen_documents_batch(uploaded_files)
        if forgery_check["overall_recommendation"] == "REJECT":
            logs.append(_log(agent, f"Pipeline blocked. Document forgery detected: {forgery_check['critical_documents']}", level="ERROR"))
            return {
                **state,
                "pipeline_blocked": True,
                "block_reason": "DOCUMENT_FORGERY_DETECTED",
                "block_detail": f"Critical forgery risk in: {forgery_check['critical_documents']}",
                "forgery_screening": forgery_check,
                "logs": logs,
                "agent_statuses": {**state.get("agent_statuses", {}), "ingestor": "ERROR"},
            }
        if forgery_check["overall_recommendation"] == "MANUAL_REVIEW":
            state["forgery_warning"] = forgery_check
            state["requires_manual_document_review"] = True
            logs.append(_log(agent, "Document forgery warning generated.", level="WARN"))

    logs.append(_log(agent, f"Starting document ingestion for {state.get('company_name', 'Unknown')}"))

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
        raw_response = _call_gemini(prompt)
        logs.append(_log(agent, "LLM extraction complete. Parsing JSON response..."))
        extracted = _extract_json(raw_response)

        if not extracted:
            logs.append(_log(agent, "JSON parse failed — using defaults.", level="WARN"))
            extracted = _default_financials()
    except Exception as exc:
        logs.append(_log(agent, f"Gemini API error: {exc}", level="ERROR"))
        extracted = _default_financials()

    # Ensure company name is populated
    if not extracted.get("company_name"):
        extracted["company_name"] = company_name

    # Inject GST result into extracted data (override LLM if tool found discrepancy)
    if gst_result.detected or not extracted.get("gst_vs_bank_discrepancy", {}).get("details"):
        extracted["gst_vs_bank_discrepancy"] = gst_result.to_dict()

    # ── Step 3.5: Confidence-Based Metric Filtering ────────────────────────────
    logs.append(_log(agent, "Filtering financial metrics by confidence..."))
    
    filtered_metrics = _filter_low_confidence_metrics(
        extracted.get("financials", {}),
        documents,
        confidence_threshold=0.7
    )
    
    if filtered_metrics["filtered_count"] > 0:
        logs.append(
            _log(
                agent,
                f"Filtered {filtered_metrics['filtered_count']} low-confidence metrics. "
                f"Accepted: {filtered_metrics['accepted_count']}, "
                f"Flagged: {filtered_metrics['flagged_count']}",
                level="WARN"
            )
        )
        extracted["confidence_filtering"] = {
            "total_metrics": filtered_metrics["total_count"],
            "accepted_metrics": filtered_metrics["accepted_count"],
            "flagged_metrics": filtered_metrics["flagged_count"],
            "flagged_list": filtered_metrics["flagged_list"],
        }
    
    # Store document quality summary
    doc_quality_summary = _compile_document_quality_summary(documents)
    extracted["document_quality_summary"] = doc_quality_summary
    
    if doc_quality_summary["low_confidence_count"] > 0:
        logs.append(
            _log(
                agent,
                f"⚠ {doc_quality_summary['low_confidence_count']} document(s) have low extraction confidence",
                level="WARN"
            )
        )

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

    # ── Step 5: MD&A Sentiment Analysis ──────────────────────────────────────
    mda_texts = {}
    annual_reports = [
        doc for doc in documents 
        if "annual" in doc.get("doc_type", "").lower() or "financial" in doc.get("doc_type", "").lower()
    ]
    
    for idx, doc in enumerate(annual_reports):
        text = doc.get("text", "")
        if text:
            year = doc.get("metadata", {}).get("year", f"Year_{idx}")
            mda_texts[year] = await _extract_mda_section(text)

    mda_analysis = None
    if mda_texts:
        logs.append(_log(agent, f"Running MD&A sentiment analysis on {len(mda_texts)} reports..."))
        mda_analysis = await analyze_mda_sentiment(
            mda_texts=mda_texts,
            company_name=company_name,
            use_llm=True,
        )
        
        # Auto-escalate if CRITICAL/HIGH
        if mda_analysis["mda_risk_level"] in ("CRITICAL", "HIGH"):
            fraud_flags.extend(mda_analysis.get("red_flags", []))
            extracted.setdefault("red_flags", []).extend(mda_analysis.get("red_flags", []))

    # ── Step 6: Schema-Guided Extraction ──────────────────────────────────────
    schema_extraction_results = {}
    selected_schemas = state.get("selected_schemas", {})
    document_classifications = state.get("document_classifications", {})
    
    if selected_schemas:
        logs.append(_log(agent, f"Running schema-guided extraction on {len(selected_schemas)} documents..."))
        
        # Configure Gemini model for schema extraction
        genai.configure(api_key=os.environ["GEMINI_API_KEY"])
        gemini_model = genai.GenerativeModel('gemini-1.5-pro')
        
        for file_id, schema_config in selected_schemas.items():
            schema_id = schema_config.get("schema_id")
            custom_hints = schema_config.get("custom_hints", {})
            
            # Find the document in the documents list
            document = None
            for doc in documents:
                if doc.get("file_id") == file_id or doc.get("filename") == file_id:
                    document = doc
                    break
            
            if not document:
                logs.append(_log(agent, f"Document {file_id} not found for schema extraction", level="WARN"))
                continue
            
            # Get schema template
            if schema_id not in SCHEMA_REGISTRY:
                logs.append(_log(agent, f"Invalid schema ID: {schema_id}", level="WARN"))
                continue
            
            schema = SCHEMA_REGISTRY[schema_id]
            doc_type = document_classifications.get(file_id, {}).get("confirmed_type", "UNKNOWN")
            
            logs.append(_log(agent, f"Extracting {schema.template_name} from {doc_type} ({file_id[:8]}...)"))
            
            try:
                # Prepare document for extraction (text + tables)
                extraction_doc = {
                    "text": document.get("text", ""),
                    "tables": document.get("tables", []),
                    "metadata": document.get("metadata", {})
                }
                
                # Run schema extraction
                result = SchemaMapper.extract_with_schema(
                    document=extraction_doc,
                    schema=schema,
                    gemini_model=gemini_model,
                    custom_hints=custom_hints if custom_hints else None
                )
                
                schema_extraction_results[file_id] = result
                
                # Log completion
                completion_pct = result["completion_percentage"]
                missing_count = len(result["missing_required_fields"])
                
                log_level = "SUCCESS" if completion_pct >= 70 else "WARN" if completion_pct >= 50 else "ERROR"
                log_msg = f"Schema extraction: {file_id[:8]} ({doc_type}) → {completion_pct:.1f}% complete"
                
                if missing_count > 0:
                    log_msg += f", {missing_count} required field(s) missing"
                
                logs.append(_log(agent, log_msg, level=log_level))
                
            except Exception as exc:
                logs.append(_log(agent, f"Schema extraction failed for {file_id}: {exc}", level="ERROR"))
                schema_extraction_results[file_id] = {
                    "schema_id": schema_id,
                    "schema_name": schema.template_name,
                    "error": str(exc),
                    "completion_percentage": 0.0,
                    "fields": {},
                    "missing_required_fields": [f.field_label for f in schema.fields if f.required]
                }
        
        # ── Step 6.1: Merge FINANCIAL_ANALYSIS_SCHEMA results into extracted_financials ───
        for file_id, result in schema_extraction_results.items():
            if result.get("schema_id") == "SCH_FINANCIAL_001":  # FINANCIAL_ANALYSIS_SCHEMA
                logs.append(_log(agent, "Merging schema-extracted financials into extracted_financials..."))
                
                schema_fields = result.get("fields", {})
                financials = extracted.setdefault("financials", {})
                
                # Field mapping: schema_field_name → extracted_financials key
                field_mapping = {
                    "revenue": "revenue",
                    "ebitda": "ebitda",
                    "pat": "net_profit",
                    "total_debt": "total_debt",
                    "net_worth": "net_worth",
                    "current_assets": "current_assets",
                    "current_liabilities": "current_liabilities",
                    "interest_expense": "interest_expense",
                    "depreciation": "depreciation",
                    "cash_from_operations": "operating_cash_flow",
                }
                
                for schema_field, extracted_key in field_mapping.items():
                    field_data = schema_fields.get(schema_field, {})
                    
                    if field_data.get("status") == "EXTRACTED" and field_data.get("confidence", 0) >= 0.6:
                        schema_value = field_data["value"]
                        existing_value = financials.get(extracted_key)
                        
                        # Convert to float for comparison
                        try:
                            schema_val_float = float(str(schema_value).replace(',', ''))
                            existing_val_float = float(existing_value) if existing_value else 0.0
                            
                            # Check for >10% difference
                            if existing_val_float > 0 and schema_val_float > 0:
                                diff_pct = abs(schema_val_float - existing_val_float) / existing_val_float * 100
                                
                                if diff_pct > 10:
                                    logs.append(
                                        _log(
                                            agent,
                                            f"⚠ Schema vs LLM mismatch for {extracted_key}: "
                                            f"Schema={schema_val_float:.2f}, LLM={existing_val_float:.2f} ({diff_pct:.1f}% diff)",
                                            level="WARN"
                                        )
                                    )
                                    # Keep both values
                                    financials[f"{extracted_key}_schema"] = schema_val_float
                                    financials[f"{extracted_key}_parsed"] = existing_val_float
                                else:
                                    # Use schema value (higher confidence method)
                                    financials[extracted_key] = schema_val_float
                            else:
                                # Use schema value if existing is missing
                                financials[extracted_key] = schema_val_float
                                
                        except (ValueError, TypeError) as e:
                            logs.append(_log(agent, f"Failed to parse {schema_field}: {e}", level="WARN"))
        
        # ── Step 6.2: Compile Ingestion Summary ───────────────────────────────────
        total_docs = len(documents)
        schema_guided_count = len(schema_extraction_results)
        
        completion_pcts = [
            result["completion_percentage"]
            for result in schema_extraction_results.values()
            if "completion_percentage" in result
        ]
        avg_completion = sum(completion_pcts) / len(completion_pcts) if completion_pcts else 0.0
        
        docs_needing_review = [
            file_id
            for file_id, result in schema_extraction_results.items()
            if result.get("completion_percentage", 0) < 70
        ]
        
        ingestion_summary = {
            "total_documents": total_docs,
            "schema_guided_count": schema_guided_count,
            "avg_completion_pct": round(avg_completion, 2),
            "documents_needing_review": docs_needing_review,
            "high_confidence_count": sum(1 for pct in completion_pcts if pct >= 80),
            "medium_confidence_count": sum(1 for pct in completion_pcts if 50 <= pct < 80),
            "low_confidence_count": sum(1 for pct in completion_pcts if pct < 50),
        }
        
        logs.append(
            _log(
                agent,
                f"Schema extraction summary: {schema_guided_count} docs processed, "
                f"{avg_completion:.1f}% avg completion, "
                f"{len(docs_needing_review)} need review",
                level="SUCCESS"
            )
        )
    else:
        # No schemas selected, use default summary
        ingestion_summary = {
            "total_documents": len(documents),
            "schema_guided_count": 0,
            "avg_completion_pct": 0.0,
            "documents_needing_review": [],
            "high_confidence_count": 0,
            "medium_confidence_count": 0,
            "low_confidence_count": 0,
        }

    # Propagate extracted fields to state for downstream agents
    out_state = {
        "extracted_financials": extracted,
        "fraud_flags": fraud_flags,
        "logs": logs,
        "agent_statuses": {**state.get("agent_statuses", {}), "ingestor": "DONE"},
        "forgery_warning": state.get("forgery_warning"),
        "requires_manual_document_review": state.get("requires_manual_document_review"),
        "mda_sentiment": mda_analysis,
        "schema_extraction_results": schema_extraction_results,
        "ingestion_summary": ingestion_summary,
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

    return out_state
