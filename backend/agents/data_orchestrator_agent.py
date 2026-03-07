"""
Data Orchestrator Agent — Enterprise Data Collection Hub

Coordinates parallel data collection from multiple external sources:
- Zauba Corp scraper
- NCLT insolvency checker
- Credit rating aggregator
- GST API
- Account aggregator
- Tofler API

Responsibilities:
1. Fire all external data agents in parallel
2. Merge results into unified company profile
3. Detect inconsistencies across data sources
4. Calculate confidence scores for cross-validated data

Output Schema:
{
    "company_profile": {},
    "source_data": {},
    "inconsistencies": [],
    "confidence_score": float
}

Author: Credit Intelligence System
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

# Import data collection agents
from tools.scrapers.zauba_scraper import scrape_zauba_data
from tools.scrapers.nclt_scraper import check_nclt_status
from tools.scrapers.rating_scraper import aggregate_credit_ratings
from tools.apis.gst_api import fetch_gst_data
from tools.apis.account_aggregator import fetch_account_aggregator_data
from tools.apis.tofler_api import fetch_tofler_data

logger = logging.getLogger(__name__)


@dataclass
class CompanyInput:
    """Input for data orchestrator."""
    company_name: str
    cin: str
    promoter_pan: Optional[str] = None
    gstin: Optional[str] = None


@dataclass
class DataInconsistency:
    """Represents a data inconsistency detected across sources."""
    field: str
    source1: str
    value1: Any
    source2: str
    value2: Any
    variance_pct: Optional[float] = None
    severity: str = "MEDIUM"  # LOW, MEDIUM, HIGH, CRITICAL


@dataclass
class DataOrchestratorResult:
    """Result from data orchestrator."""
    company_profile: Dict[str, Any]
    source_data: Dict[str, Any]
    inconsistencies: List[DataInconsistency]
    confidence_score: float
    execution_time: float
    errors: List[str] = field(default_factory=list)


async def run_data_orchestrator_agent(
    company_input: CompanyInput,
    timeout: int = 30
) -> DataOrchestratorResult:
    """
    Main orchestrator that fires all data collection agents in parallel
    and merges results.
    
    Args:
        company_input: Company identification details
        timeout: Max timeout for all parallel operations
        
    Returns:
        DataOrchestratorResult with merged profile and inconsistencies
    """
    start_time = asyncio.get_event_loop().time()
    logger.info(f"🚀 Starting data orchestration for {company_input.company_name}")
    
    # Fire all data collection agents in parallel
    tasks = {
        "zauba": scrape_zauba_data(company_input.cin, company_input.company_name),
        "nclt": check_nclt_status(company_input.cin, company_input.company_name),
        "ratings": aggregate_credit_ratings(company_input.company_name, company_input.cin),
        "gst": fetch_gst_data(company_input.gstin) if company_input.gstin else _empty_result("GST data unavailable - no GSTIN provided"),
        "account_aggregator": fetch_account_aggregator_data(company_input.cin),
        "tofler": fetch_tofler_data(company_input.cin, company_input.company_name),
    }
    
    # Execute with timeout
    try:
        results = await asyncio.wait_for(
            _gather_with_errors(tasks),
            timeout=timeout
        )
    except asyncio.TimeoutError:
        logger.error(f"⏱️  Data orchestration timeout after {timeout}s")
        results = {key: _empty_result(f"Timeout") for key in tasks.keys()}
    
    # Merge results into unified company profile
    company_profile = _merge_company_profile(results, company_input)
    
    # Detect inconsistencies
    inconsistencies = _detect_inconsistencies(results, company_profile)
    
    # Calculate confidence score
    confidence_score = _calculate_confidence_score(results, inconsistencies)
    
    execution_time = asyncio.get_event_loop().time() - start_time
    
    # Collect errors
    errors = [
        f"{source}: {result.get('error', '')}"
        for source, result in results.items()
        if result.get("error")
    ]
    
    logger.info(
        f"✅ Data orchestration complete in {execution_time:.2f}s | "
        f"Confidence: {confidence_score:.1%} | "
        f"Inconsistencies: {len(inconsistencies)}"
    )
    
    return DataOrchestratorResult(
        company_profile=company_profile,
        source_data=results,
        inconsistencies=inconsistencies,
        confidence_score=confidence_score,
        execution_time=execution_time,
        errors=errors
    )


async def _gather_with_errors(tasks: Dict[str, Any]) -> Dict[str, Any]:
    """Execute tasks in parallel and capture errors gracefully."""
    results = {}
    
    async def safe_execute(key: str, coro):
        try:
            return key, await coro
        except Exception as e:
            logger.error(f"❌ Error in {key}: {str(e)}")
            return key, {"error": str(e), "data": None}
    
    gathered = await asyncio.gather(
        *[safe_execute(k, v) for k, v in tasks.items()],
        return_exceptions=False
    )
    
    for key, result in gathered:
        results[key] = result
    
    return results


def _merge_company_profile(
    results: Dict[str, Any],
    company_input: CompanyInput
) -> Dict[str, Any]:
    """
    Merge data from all sources into unified company profile.
    
    Priority order for conflicts:
    1. Tofler (most authoritative for financials)
    2. MCA/Zauba (official registry)
    3. GST (tax data)
    4. Account aggregator (banking data)
    5. Ratings (external assessment)
    """
    profile = {
        "basic_info": {
            "company_name": company_input.company_name,
            "cin": company_input.cin,
            "gstin": company_input.gstin,
            "data_sources_used": list(results.keys()),
        },
        "directors": [],
        "financials": {},
        "compliance": {},
        "charges": [],
        "ratings": {},
        "insolvency_status": {},
        "banking": {},
        "gst_data": {},
    }
    
    # Extract Zauba data
    if results.get("zauba") and results["zauba"].get("data"):
        zauba_data = results["zauba"]["data"]
        profile["directors"] = zauba_data.get("directors", [])
        profile["charges"] = zauba_data.get("charges", [])
        profile["compliance"]["zauba"] = zauba_data.get("compliance", {})
        profile["basic_info"]["date_of_incorporation"] = zauba_data.get("date_of_incorporation")
        profile["basic_info"]["status"] = zauba_data.get("company_status")
    
    # Extract NCLT data
    if results.get("nclt") and results["nclt"].get("data"):
        profile["insolvency_status"] = results["nclt"]["data"]
    
    # Extract Rating data
    if results.get("ratings") and results["ratings"].get("data"):
        profile["ratings"] = results["ratings"]["data"]
    
    # Extract GST data
    if results.get("gst") and results["gst"].get("data"):
        gst_data = results["gst"]["data"]
        profile["gst_data"] = gst_data
        profile["financials"]["gst_turnover"] = gst_data.get("annual_turnover")
    
    # Extract Account Aggregator data
    if results.get("account_aggregator") and results["account_aggregator"].get("data"):
        profile["banking"] = results["account_aggregator"]["data"]
    
    # Extract Tofler data (highest priority for financials)
    if results.get("tofler") and results["tofler"].get("data"):
        tofler_data = results["tofler"]["data"]
        profile["financials"].update(tofler_data.get("financials", {}))
        profile["basic_info"]["subsidiaries"] = tofler_data.get("subsidiaries", [])
        profile["basic_info"]["auditor"] = tofler_data.get("auditor")
    
    return profile


def _detect_inconsistencies(
    results: Dict[str, Any],
    company_profile: Dict[str, Any]
) -> List[DataInconsistency]:
    """
    Detect inconsistencies across data sources.
    
    Key checks:
    1. Revenue: Financial statements vs GST vs Bank credits
    2. Directors: Zauba vs Tofler
    3. Company status: Multiple sources
    4. Address: Registry vs GST
    """
    inconsistencies = []
    
    # Check 1: Revenue reconciliation
    revenue_sources = {}
    
    # Get financial statement revenue
    if company_profile["financials"].get("revenue"):
        revenue_sources["financial_statements"] = company_profile["financials"]["revenue"]
    
    # Get GST turnover
    if company_profile["gst_data"].get("annual_turnover"):
        revenue_sources["gst"] = company_profile["gst_data"]["annual_turnover"]
    
    # Get bank credits (proxy for revenue)
    if company_profile["banking"].get("total_credits_annual"):
        revenue_sources["bank_credits"] = company_profile["banking"]["total_credits_annual"]
    
    # Compare revenues
    if len(revenue_sources) >= 2:
        sources = list(revenue_sources.items())
        for i in range(len(sources)):
            for j in range(i + 1, len(sources)):
                source1, value1 = sources[i]
                source2, value2 = sources[j]
                
                if value1 and value2 and value1 > 0:
                    variance = abs(value1 - value2) / value1 * 100
                    
                    if variance > 10:  # More than 10% variance
                        severity = "LOW" if variance < 25 else "MEDIUM" if variance < 40 else "HIGH"
                        inconsistencies.append(DataInconsistency(
                            field="revenue",
                            source1=source1,
                            value1=value1,
                            source2=source2,
                            value2=value2,
                            variance_pct=variance,
                            severity=severity
                        ))
    
    # Check 2: Director count mismatch
    zauba_directors = len(results.get("zauba", {}).get("data", {}).get("directors", []))
    tofler_directors = len(results.get("tofler", {}).get("data", {}).get("directors", []))
    
    if zauba_directors and tofler_directors and zauba_directors != tofler_directors:
        inconsistencies.append(DataInconsistency(
            field="director_count",
            source1="zauba",
            value1=zauba_directors,
            source2="tofler",
            value2=tofler_directors,
            severity="MEDIUM"
        ))
    
    # Check 3: Company status conflicts
    zauba_status = results.get("zauba", {}).get("data", {}).get("company_status")
    nclt_status = results.get("nclt", {}).get("data", {}).get("is_under_cirp")
    
    if zauba_status == "Active" and nclt_status:
        inconsistencies.append(DataInconsistency(
            field="company_status",
            source1="zauba",
            value1="Active",
            source2="nclt",
            value2="Under CIRP",
            severity="CRITICAL"
        ))
    
    return inconsistencies


def _calculate_confidence_score(
    results: Dict[str, Any],
    inconsistencies: List[DataInconsistency]
) -> float:
    """
    Calculate confidence score based on:
    1. Number of successful data sources
    2. Severity of inconsistencies
    3. Completeness of critical fields
    """
    # Base score: proportion of successful sources
    total_sources = len(results)
    successful_sources = sum(
        1 for result in results.values()
        if result.get("data") and not result.get("error")
    )
    
    base_score = successful_sources / total_sources if total_sources > 0 else 0
    
    # Penalty for inconsistencies
    inconsistency_penalty = 0
    for inc in inconsistencies:
        if inc.severity == "CRITICAL":
            inconsistency_penalty += 0.15
        elif inc.severity == "HIGH":
            inconsistency_penalty += 0.08
        elif inc.severity == "MEDIUM":
            inconsistency_penalty += 0.03
        else:
            inconsistency_penalty += 0.01
    
    confidence_score = max(0, base_score - inconsistency_penalty)
    
    return confidence_score


def _empty_result(reason: str) -> Dict[str, Any]:
    """Return empty result with error message."""
    return {
        "data": None,
        "error": reason,
        "timestamp": datetime.now().isoformat()
    }


# ─── Helper function for integration ─────────────────────────────────────────

def _log(agent: str, message: str, level: str = "INFO") -> Dict[str, Any]:
    """Standard logging format for orchestrator integration."""
    return {
        "timestamp": datetime.now().strftime("%H:%M:%S"),
        "agent": agent,
        "message": message,
        "level": level,
    }
