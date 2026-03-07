"""
Observation Intelligence Engine — Qualitative Credit Signal Extractor

Transforms free-text observations written by credit officers during factory
visits, warehouse inspections, and management interactions into structured
operational risk indicators that influence the credit decision.

PIPELINE:
    Free-text Observation
        → Sentence Segmentation
        → Keyword & Phrase Detection
        → Semantic Context Analysis (negation / temporal / conditional)
        → Risk Signal Extraction (LLM-validated)
        → Industry Context Adjustment
        → Operational Risk Scoring
        → Manipulation Detection
        → Structured JSON Output

INTEGRATION TARGETS:
    red_flag_engine, risk_matrix, three_way_reconciliation, cam_generator,
    scoring/dynamic_weights

Author: Credit Intelligence System
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import time
from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ─── Optional dependency ──────────────────────────────────────────────────────

def _import_anthropic():
    try:
        from anthropic import Anthropic
        return Anthropic
    except ImportError:
        return None


# ─────────────────────────────────────────────────────────────────────────────
# ENUMS
# ─────────────────────────────────────────────────────────────────────────────

class Severity(str, Enum):
    LOW    = "low"
    MEDIUM = "medium"
    HIGH   = "high"
    NONE   = "none"          # used for positive/neutral signals


class IndustryType(str, Enum):
    MANUFACTURING   = "manufacturing"
    PHARMACEUTICALS = "pharmaceuticals"
    TEXTILES        = "textiles"
    IT_SERVICES     = "it_services"
    FOOD_PROCESSING = "food_processing"
    LOGISTICS       = "logistics"
    AGRICULTURE     = "agriculture"
    CHEMICALS       = "chemicals"
    REAL_ESTATE     = "real_estate"
    RETAIL          = "retail"
    UNKNOWN         = "unknown"


class FacilityType(str, Enum):
    PLANT     = "plant"
    WAREHOUSE = "warehouse"
    OFFICE    = "office"
    FARM      = "farm"
    UNKNOWN   = "unknown"


# ─────────────────────────────────────────────────────────────────────────────
# SIGNAL TAXONOMY
# ─────────────────────────────────────────────────────────────────────────────

# Each entry: signal_key → {"severity": Severity, "patterns": [regex,...], "weight": int}
_RISK_SIGNALS: Dict[str, Dict[str, Any]] = {

    # ── Capacity / Production ──────────────────────────────────────────────
    "low_capacity_utilization": {
        "severity": Severity.HIGH,
        "patterns": [
            r"\b([1-5]\d|[1-9])\s*%\s*(?:capacity|util)",
            r"low\s+capacity\s+util",
            r"under[- ]utiliz",
            r"partial\s+(?:production|operation)",
            r"running\s+(?:at\s+)?(?:low|below)\s+capacity",
            r"production\s+(?:running\s+)?(?:at\s+)?(?:low|minimal)\s+level",
            r"less\s+than\s+(?:half|50[.,]?\s*%)\s+(?:of\s+)?capacity",
        ],
        "positive_override": "high_production_activity",
    },
    "plant_shutdown": {
        "severity": Severity.HIGH,
        "patterns": [
            r"\bplant\s+(?:is\s+)?shut(?:down)?",
            r"\bfactory\s+(?:is\s+)?(?:closed|shut|not\s+operating)",
            r"production\s+(?:has\s+)?(?:stopped|halted|ceased|discontinued)",
            r"no\s+production\s+(?:activity|observed|happening)",
            r"\bunit\s+(?:is\s+)?closed",
        ],
        "seasonal_adjustment": True,   # seasonal industries may legitimately shutdown
        "maintenance_adjustment": True,
    },
    "idle_production_lines": {
        "severity": Severity.MEDIUM,
        "patterns": [
            r"(?:production\s+)?lines?\s+(?:are\s+)?idle",
            r"machines?\s+(?:are\s+)?(?:idle|sitting\s+idle|not\s+running|switched\s+off)",
            r"idle\s+(?:machines?|equipment|lines?|workers?)",
            r"equipments?\s+(?:lying\s+)?idle",
            r"unused\s+(?:machinery|production\s+lines?|equipment)",
        ],
        "seasonal_adjustment": True,
    },
    "obsolete_machinery": {
        "severity": Severity.MEDIUM,
        "patterns": [
            r"(?:machines?|machinery|equipment)\s+(?:appear|look|seem)\s+(?:old|outdated|obsolete|worn|aged)",
            r"old(?:er)?\s+(?:machines?|machinery|equipment)",
            r"outdated\s+(?:machines?|machinery|technology|equipment)",
            r"more\s+than\s+(?:\d+)\s+years?\s+old",
            r"obsolete\s+(?:technology|equipment|machinery)",
            r"rusted?\s+(?:machines?|equipment)",
        ],
    },
    "poor_facility_maintenance": {
        "severity": Severity.MEDIUM,
        "patterns": [
            r"poor\s+(?:maintenance|upkeep|condition)",
            r"(?:facility|plant|building|floor|roof|wall)\s+(?:is\s+)?(?:in\s+)?(?:poor|bad|dilapidated|run-?down|neglected)",
            r"(?:cracked|broken|damaged|dirty)\s+(?:walls?|floors?|roof|equipment|ceiling)",
            r"(?:leaking|rusted?|corroded?)\s+(?:pipes?|roofs?|tanks?|vessels?)",
            r"lack\s+of\s+(?:maintenance|upkeep|cleanliness)",
            r"unmaintained\s+(?:premises?|facility|equipment)",
        ],
    },

    # ── Inventory & Working Capital ────────────────────────────────────────
    "inventory_overstock": {
        "severity": Severity.MEDIUM,
        "patterns": [
            r"large\s+(?:amount\s+of\s+)?(?:unsold|accumulated|excess|surplus)\s+inventory",
            r"inventory\s+(?:pile[- ]?up|accumulation|build[- ]?up|overstock)",
            r"(?:full|overflowing|stacked)\s+(?:warehouse|godown|store)",
            r"(?:unsold|slow[- ]moving)\s+(?:stock|goods|inventory|finished\s+goods)",
            r"piled\s+up\s+(?:inventory|goods|stock|material)",
            r"high\s+(?:inventory\s+level|stock\s+level|WIP|work\s+in\s+progress)",
        ],
    },
    "excess_raw_material": {
        "severity": Severity.LOW,
        "patterns": [
            r"excess\s+raw\s+material",
            r"large\s+(?:stock|quantity)\s+of\s+raw\s+material",
            r"raw\s+material\s+(?:accumulation|pile[- ]?up|overstock)",
            r"(?:overstocked|overflowing)\s+(?:raw\s+material|RM\s+store)",
        ],
    },
    "supply_chain_disruption": {
        "severity": Severity.MEDIUM,
        "patterns": [
            r"supply\s+chain\s+(?:disruption|issue|problem|breakdown|challenge)",
            r"raw\s+material\s+(?:shortage|unavailability|delay|supply\s+issue)",
            r"(?:material|input)\s+(?:not\s+available|shortage|delay)",
            r"supplier\s+(?:issue|problem|default|failure)",
            r"input\s+(?:material\s+)?(?:shortage|disruption)",
        ],
    },

    # ── Labor & HR ──────────────────────────────────────────────────────────
    "labor_dissatisfaction": {
        "severity": Severity.HIGH,
        "patterns": [
            r"worker(?:s)?\s+(?:mentioned|complained|dissatisfied|unhappy|upset|agitated)",
            r"(?:employee|labour|labor|workforce)\s+(?:dissatisfi|unhappy|discontent|unrest|morale)",
            r"labour\s+unrest",
            r"workers?\s+(?:are\s+)?(?:unhappy|leaving|quitting|dissatisfied)",
            r"high\s+(?:employee|labour|labor|workforce)\s+attrition",
            r"mass\s+(?:layoffs?|retrenchment|resignation)",
        ],
    },
    "salary_delays": {
        "severity": Severity.HIGH,
        "patterns": [
            r"salary\s+(?:delay|not\s+paid|pending|arrears|dues)",
            r"wages?\s+(?:delay|not\s+paid|pending|arrears|dues)",
            r"(?:employees?|workers?|staff)\s+(?:not\s+(?:been\s+)?paid|salaries?\s+due|wages?\s+due)",
            r"payroll\s+(?:irregular|delayed|pending|issue)",
            r"delayed\s+(?:salary|wages?|payment\s+to\s+(?:staff|workers?|employees?))",
        ],
    },

    # ── Safety & Compliance ─────────────────────────────────────────────────
    "safety_violations": {
        "severity": Severity.HIGH,
        "patterns": [
            r"safety\s+(?:violation|non[- ]compliance|concern|hazard|risk|issue)",
            r"no\s+(?:safety|protective)\s+(?:gear|equipment|signage|measures)",
            r"(?:workers?|employees?)\s+(?:without|not\s+using|not\s+wearing)\s+(?:safety|protective|PPE)",
            r"(?:fire|electrical|chemical)\s+(?:hazard|safety\s+(?:issue|violation|failure))",
            r"(?:unsafe|dangerous)\s+(?:working|factory|plant|operational)\s+(?:conditions?|environment)",
            r"(?:accident|incident)\s+(?:history|record|reported)",
        ],
    },
    "environmental_non_compliance": {
        "severity": Severity.HIGH,
        "patterns": [
            r"environmental\s+(?:violation|non[- ]compliance|issue|concern|regulation|penalty)",
            r"pollution\s+(?:control|complaint|violation|non[- ]compliance)",
            r"effluent\s+(?:treatment|discharge|violation)",
            r"(?:discharge|dumping)\s+of\s+(?:waste|effluent|pollutant)",
            r"(?:PCB|CPCB|SPCB)\s+(?:notice|violation|non[- ]compliance|closure\s+notice)",
            r"no\s+(?:ETP|effluent\s+treatment|pollution\s+control)",
        ],
    },

    # ── Management & Governance ─────────────────────────────────────────────
    "management_evasion": {
        "severity": Severity.HIGH,
        "patterns": [
            r"management\s+(?:(?:was\s+)?(?:evasive|uncooperative|not\s+forthcoming|reluctant|refused)|(?:avoid|denied)\s+questions?)",
            r"(?:avoided|evaded|deflected)\s+(?:questions?|queries|scrutiny)",
            r"(?:refused|denied)\s+(?:access|entry)\s+(?:to\s+(?:certain\s+)?(?:areas?|sections?|parts?))",
            r"did\s+not\s+(?:allow|permit|provide|share)\s+(?:access|documents?|records?|information)",
            r"(?:information|records?|data)\s+(?:withheld|not\s+shared|not\s+provided|hidden)",
            r"(?:reluctant|unwilling)\s+to\s+(?:show|provide|share|disclose|reveal)",
        ],
    },
    "misleading_representations": {
        "severity": Severity.HIGH,
        "patterns": [
            r"(?:claims?|management\s+says?)\s+(?:orders?|business|demand)\s+(?:will|to)\s+(?:improve|increase|recover|pick\s+up)",
            r"management\s+(?:is(?:\s+very)?\s+(?:optimistic|confident|bullish)|claims?\s+(?:all\s+is\s+fine|everything\s+is\s+fine))",
            r"(?:over-?stated|exaggerated|inflated)\s+(?:orders?|capacity|production|revenue|demand)",
            r"promises?\s+(?:of\s+)?(?:future|upcoming|expected)\s+(?:orders?|clients?|contracts?|business)",
            r"unverified\s+(?:claims?|assertions?|statements?)",
        ],
    },
    "key_person_dependency": {
        "severity": Severity.MEDIUM,
        "patterns": [
            r"(?:rely|relies|dependent|depends)\s+(?:heavily\s+)?on\s+(?:single|one)\s+(?:person|individual|promoter|director|owner)",
            r"(?:entire|whole)\s+(?:business|operation)\s+(?:run|managed|controlled)\s+by\s+(?:one|single)",
            r"no\s+second[- ]tier\s+management",
            r"(?:promoter|owner)\s+(?:is\s+)?(?:the\s+only|sole)\s+(?:decision[- ]maker|person\s+managing)",
            r"(?:family[- ]run|family\s+managed)\s+with\s+(?:no|limited)\s+(?:professional|independent)\s+management",
        ],
    },

    # ── Financial Stress Indicators ─────────────────────────────────────────
    "cash_flow_stress": {
        "severity": Severity.HIGH,
        "patterns": [
            r"(?:cash\s+flow|liquidity)\s+(?:stress|crunch|problem|issue|squeeze|shortage|constraint)",
            r"struggling\s+to\s+(?:pay|meet)\s+(?:bills?|obligations?|dues?|expenses?|liabilities)",
            r"unable\s+to\s+(?:pay|service)\s+(?:debts?|dues?|suppliers?|loans?)",
            r"(?:suppliers?|vendors?|creditors?)\s+(?:not\s+being\s+paid|awaiting\s+payment|payment\s+overdue)",
            r"cheques?\s+(?:bounced?|dishonoured?|returned?)",
        ],
    },
    "high_receivables_stress": {
        "severity": Severity.MEDIUM,
        "patterns": [
            r"(?:large|high|significant|excessive)\s+(?:outstanding|overdue|pending)?\s+(?:receivables?|debtors?)",
            r"(?:debtors?|receivables?)\s+(?:aging|aged|outstanding\s+for\s+(?:long|months|years?))",
            r"(?:slow|delayed|poor)\s+collection(?:s)?",
            r"(?:customers?|buyers?)\s+(?:not\s+paying|delayed\s+payments?|defaulting)",
        ],
    },

    # ── Infrastructure & Assets ─────────────────────────────────────────────
    "asset_quality_concern": {
        "severity": Severity.MEDIUM,
        "patterns": [
            r"(?:collateral|asset|property|machinery)\s+(?:is\s+)?(?:overvalued|inflated|not\s+worth)",
            r"(?:plant|building|asset)\s+(?:in\s+)?(?:poor|bad|dilapidated|deteriorating)\s+(?:state|condition)",
            r"(?:assets?|machinery|equipment)\s+(?:fully\s+)?(?:depreciated|amortized|written\s+off)",
            r"poor\s+(?:asset|infrastructure|equipment)\s+quality",
        ],
    },
    "regulatory_issues": {
        "severity": Severity.HIGH,
        "patterns": [
            r"(?:regulatory|compliance|statutory|legal)\s+(?:notice|violation|issue|action|penalty|fine|shutdown\s+notice)",
            r"(?:received|served|issued)\s+(?:a\s+)?(?:notice|warning|order)\s+(?:from|by)\s+(?:government|regulatory|authority|municipal|GST|income\s+tax|SEBI|RBI)",
            r"(?:income\s+tax|GST|labour|factory)\s+(?:raid|survey|inspection|notice|demand)",
            r"(?:license|permit|registration|certification)\s+(?:cancelled|suspended|revoked|expired|lapsed|not\s+renewed)",
            r"(?:closed\s+down|ordered\s+to\s+close|sealed)\s+by\s+(?:authorities?|court|government)",
        ],
    },
}

# ─── Positive / favourable signals ────────────────────────────────────────────

_POSITIVE_SIGNALS: Dict[str, Dict[str, Any]] = {
    "high_production_activity": {
        "severity": Severity.NONE,
        "patterns": [
            r"(?:full|high|maximum|near\s+full|100\s*%)\s+(?:capacity|production|utilization|util)",
            r"(?:running\s+at|operating\s+at)\s+(?:full|high|maximum)\s+capacity",
            r"(?:brisk|active|high)\s+(?:production|manufacturing|activity|operation)",
            r"(?:good|strong|high)\s+order\s+(?:book|pipeline|flow|position)",
            r"(?:busy|bustling)\s+(?:factory|plant|facility|shop\s+floor)",
        ],
        "score_bonus": 20,
    },
    "capacity_expansion": {
        "severity": Severity.NONE,
        "patterns": [
            r"capacity\s+expan(?:sion|ding)",
            r"new\s+(?:plant|unit|line|facility|factory)\s+(?:under\s+construction|being\s+set\s+up|commissioned|coming\s+up)",
            r"(?:expanding|scaling\s+up)\s+(?:operations?|capacity|production)",
            r"(?:additional|new)\s+(?:production\s+)?lines?\s+(?:being\s+added|installed|commissioned)",
            r"capital\s+expansion",
        ],
        "score_bonus": 15,
    },
    "new_machinery": {
        "severity": Severity.NONE,
        "patterns": [
            r"new\s+(?:machines?|machinery|equipment|plant)\s+(?:installed|commissioned|acquired|purchased|imported)",
            r"(?:recently|just)\s+(?:installed|commissioned|upgraded|replaced)\s+(?:machines?|machinery|equipment)",
            r"modern\s+(?:technological|equipment|machinery|manufacturing|production)",
            r"state\s+of\s+the\s+art\s+(?:machinery|equipment|technology|plant)",
            r"upgraded\s+(?:machinery|equipment|technology|plant|facility)",
        ],
        "score_bonus": 15,
    },
    "good_facility_condition": {
        "severity": Severity.NONE,
        "patterns": [
            r"(?:well|properly|neatly)\s+(?:maintained|kept|organized|structured|managed)",
            r"(?:clean|tidy|organized|orderly)\s+(?:factory|plant|facility|floor|premises?|warehouse)",
            r"(?:good|excellent|impressive)\s+(?:housekeeping|maintenance|condition|upkeep)",
            r"(?:facility|plant|factory)\s+(?:in\s+)?(?:good|excellent|impressive|pristine)\s+(?:condition|shape|state)",
        ],
        "score_bonus": 10,
    },
    "no_labor_issues": {
        "severity": Severity.NONE,
        "patterns": [
            r"no\s+(?:labour|labor|worker|employee|HR|payroll)\s+(?:issues?|problems?|disputes?|unrest|grievances?)",
            r"(?:workers?|employees?|staff)\s+(?:appear|seem|look)\s+(?:content|happy|satisfied|motivated)",
            r"(?:good|healthy|positive)\s+(?:labour|labor|employee|workforce)\s+relations?",
            r"regular\s+(?:salary|wage|payroll)\s+(?:payments?|disbursement)",
            r"(?:adequate|sufficient|timely)\s+(?:staffing|manpower)",
        ],
        "score_bonus": 10,
    },
    "strong_management": {
        "severity": Severity.NONE,
        "patterns": [
            r"(?:experienced|professional|capable|competent|qualified)\s+management",
            r"management\s+(?:was\s+)?(?:cooperative|transparent|forthcoming|responsive|helpful|professional)",
            r"(?:strong|robust|mature)\s+(?:management|corporate\s+governance|internal\s+controls?)",
            r"(?:well|properly)\s+(?:run|managed|governed)\s+(?:organization|company|business|enterprise)",
            r"second[- ]tier\s+management\s+(?:in\s+place|present|strong|exists?)",
        ],
        "score_bonus": 10,
    },
    "healthy_order_pipeline": {
        "severity": Severity.NONE,
        "patterns": [
            r"(?:strong|healthy|robust|good|solid)\s+order\s+(?:book|pipeline|position|flow|backlog)",
            r"(?:orders?|enquiries?|repeat\s+orders?)\s+(?:coming\s+in|received|placed|growing|increasing)",
            r"(?:new|export|large)\s+(?:orders?|contracts?)\s+(?:secured|signed|received|in\s+pipeline)",
            r"(?:confirmed|existing)\s+(?:orders?|clientele|customer\s+base)\s+(?:strong|healthy|growing|solid)",
        ],
        "score_bonus": 15,
    },
}

# ─── Context Modifier Patterns ────────────────────────────────────────────────

_NEGATION_WORDS = [
    "no", "not", "none", "never", "neither", "nor",
    "without", "absent", "lack", "lacking", "free from",
    "didn't", "doesn't", "don't", "hasn't", "haven't",
    "wasn't", "weren't", "cannot", "can't", "couldn't",
    "no longer", "not any",
]

_NEGATION_RE = re.compile(
    r"\b(?:no|not|none|never|neither|nor|without|absent|free\s+from|"
    r"didn'?t|doesn'?t|don'?t|hasn'?t|haven'?t|wasn'?t|weren'?t|"
    r"cannot|can'?t|couldn'?t|no\s+longer|not\s+any)\b",
    re.IGNORECASE,
)

_TEMPORAL_RESOLVED_RE = re.compile(
    r"\b(?:previously|earlier|last\s+(?:year|month|quarter|time)|"
    r"(?:used\s+to|historically)|in\s+the\s+past|"
    r"(?:but\s+)?(?:now|currently|at\s+present|presently|since\s+then)\s+"
    r"(?:resolved|fixed|addressed|corrected|improved|better|fine|ok))\b",
    re.IGNORECASE,
)

_UNCERTAINTY_RE = re.compile(
    r"\b(?:claims?\s+(?:that|orders?|business)|management\s+(?:says?|claims?|believes?|expects?|hopes?)|"
    r"(?:expects?|hopes?|anticipates?|projects?|predicts?)\s+(?:to|that)|"
    r"(?:may|might|could|should|possibly|probably|likely|expected)\s+(?:improve|increase|grow|recover|pick\s+up)|"
    r"if\s+(?:demand|orders?|market)|(?:subject\s+to|contingent\s+on|depends?\s+on))\b",
    re.IGNORECASE,
)

_CONDITIONAL_RE = re.compile(
    r"\b(?:if|unless|provided|as\s+long\s+as|in\s+case|assuming)\b",
    re.IGNORECASE,
)

_SEASONAL_RE = re.compile(
    r"\b(?:seasonal|off[- ]season|lean\s+season|peak\s+season|harvest\s+(?:time|season)|"
    r"festival\s+(?:season|demand)|monsoon|rabi|kharif|cyclical)\b",
    re.IGNORECASE,
)

_MAINTENANCE_RE = re.compile(
    r"\b(?:annual\s+maintenance|scheduled\s+maintenance|planned\s+shutdown|"
    r"preventive\s+maintenance|maintenance\s+(?:shutdown|break|halt|stop)|"
    r"under\s+(?:renovation|repair|maintenance|overhaul))\b",
    re.IGNORECASE,
)

_EXPANSION_RE = re.compile(
    r"\b(?:expansion|expansion\s+phase|capacity\s+addition|greenfield|brownfield|"
    r"setting\s+up\s+new)\b",
    re.IGNORECASE,
)

# ─── Manipulation Conflict Pairs ──────────────────────────────────────────────
# If both signals in a pair are detected together, raise manipulation suspicion

_MANIPULATION_PAIRS: List[Tuple[str, str, str]] = [
    ("high_production_activity", "salary_delays",         "Active production contradicts salary delays"),
    ("high_production_activity", "labor_dissatisfaction", "Active production unlikely alongside severe labor unrest"),
    ("new_machinery",            "obsolete_machinery",     "Reports of both new and obsolete machinery are contradictory"),
    ("good_facility_condition",  "poor_facility_maintenance", "Good condition and poor maintenance are contradictory"),
    ("strong_management",        "management_evasion",     "Cooperative management claim contradicts evasive behavior"),
    ("healthy_order_pipeline",   "inventory_overstock",    "Strong orders contradict large unsold inventory"),
    ("high_production_activity", "plant_shutdown",         "High production contradicts plant being shut"),
    ("capacity_expansion",       "cash_flow_stress",       "Active expansion alongside cash flow stress needs verification"),
]

# ─── Scoring Constants ────────────────────────────────────────────────────────

_SEVERITY_DEDUCTION: Dict[Severity, int] = {
    Severity.HIGH:   50,
    Severity.MEDIUM: 25,
    Severity.LOW:    10,
    Severity.NONE:    0,
}

_BASE_HEALTH_SCORE = 100
_MIN_HEALTH_SCORE  = 0
_MAX_HEALTH_SCORE  = 100

# ─── Industry Context Profiles ────────────────────────────────────────────────

_INDUSTRY_PROFILES: Dict[IndustryType, Dict[str, Any]] = {
    IndustryType.TEXTILES: {
        "seasonal_signals":       ["low_capacity_utilization", "idle_production_lines"],
        "season_note":            "Textiles are highly seasonal; capacity dips in off-season are normal",
        "typical_risks":          ["labor_dissatisfaction", "inventory_overstock"],
        "low_capacity_threshold": 40,  # Flag only if below this %
    },
    IndustryType.FOOD_PROCESSING: {
        "seasonal_signals":       ["low_capacity_utilization", "plant_shutdown", "idle_production_lines"],
        "season_note":            "Food processing capacities vary sharply with harvest and festival cycles",
        "typical_risks":          ["inventory_overstock", "supply_chain_disruption"],
        "low_capacity_threshold": 35,
    },
    IndustryType.AGRICULTURE: {
        "seasonal_signals":       ["low_capacity_utilization", "plant_shutdown", "idle_production_lines"],
        "season_note":            "Agricultural operations are strongly seasonal",
        "typical_risks":          ["supply_chain_disruption"],
        "low_capacity_threshold": 30,
    },
    IndustryType.PHARMACEUTICALS: {
        "seasonal_signals":       [],
        "season_note":            "",
        "typical_risks":          ["regulatory_issues", "environmental_non_compliance", "safety_violations"],
        "key_compliance_signals": ["regulatory_issues", "environmental_non_compliance"],
        "low_capacity_threshold": 50,
    },
    IndustryType.LOGISTICS: {
        "seasonal_signals":       ["low_capacity_utilization"],
        "season_note":            "Logistics demand peaks around festivals and harvest months",
        "typical_risks":          ["asset_quality_concern", "high_receivables_stress"],
        "low_capacity_threshold": 45,
    },
    IndustryType.IT_SERVICES: {
        "seasonal_signals":       [],
        "season_note":            "",
        "typical_risks":          ["key_person_dependency", "high_receivables_stress"],
        "physical_irrelevant":    ["inventory_overstock", "obsolete_machinery",
                                   "poor_facility_maintenance", "plant_shutdown",
                                   "idle_production_lines"],
        "low_capacity_threshold": 60,
    },
    IndustryType.REAL_ESTATE: {
        "seasonal_signals":       ["low_capacity_utilization"],
        "season_note":            "Real estate has seasonal demand cycles",
        "typical_risks":          ["cash_flow_stress", "regulatory_issues"],
        "low_capacity_threshold": 40,
    },
    IndustryType.MANUFACTURING: {
        "seasonal_signals":       ["low_capacity_utilization"],
        "season_note":            "Some manufacturing sectors show seasonal dips",
        "typical_risks":          ["obsolete_machinery", "safety_violations", "labor_dissatisfaction"],
        "low_capacity_threshold": 50,
    },
    IndustryType.UNKNOWN: {
        "seasonal_signals":       [],
        "season_note":            "",
        "typical_risks":          [],
        "low_capacity_threshold": 50,
    },
}


# ─────────────────────────────────────────────────────────────────────────────
# DATA STRUCTURES
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ObservationMetadata:
    """Optional context accompanying the free-text observation."""
    industry_type:     IndustryType = IndustryType.UNKNOWN
    visit_date:        Optional[str] = None            # ISO date string
    facility_location: Optional[str] = None
    facility_type:     FacilityType = FacilityType.UNKNOWN
    analyst_name:      Optional[str] = None
    company_name:      Optional[str] = None


@dataclass
class RiskSignal:
    """A structured risk indicator extracted from the observation."""
    signal_type:  str
    severity:     Severity
    is_positive:  bool = False
    negated:      bool = False           # True if the signal was negated in text
    temporal_resolved: bool = False      # True if resolved in the past
    conditional:  bool = False           # True if contingent / uncertain
    matched_text: str = ""              # Evidence snippet
    confidence:   float = 1.0
    score_bonus:  int = 0               # For positive signals
    note:         Optional[str] = None   # Context note (e.g., seasonal adjustment)

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "type":      self.signal_type,
            "severity":  self.severity.value,
            "positive":  self.is_positive,
        }
        if self.negated:
            d["negated"] = True
        if self.temporal_resolved:
            d["temporal_resolved"] = True
        if self.conditional:
            d["conditional"] = True
        if self.note:
            d["note"] = self.note
        return d


@dataclass
class ManipulationFlag:
    """A detected contradiction suggesting staged presentation."""
    signal_a:    str
    signal_b:    str
    description: str
    confidence_penalty: float = 0.08  # Fraction to subtract from confidence

    def to_dict(self) -> Dict[str, Any]:
        return {
            "conflict_pair": [self.signal_a, self.signal_b],
            "description":   self.description,
        }


@dataclass
class ObservationResult:
    """Complete structured output from the Observation Intelligence Engine."""
    raw_text:                str
    metadata:                ObservationMetadata

    # Core outputs
    signals:                 List[RiskSignal] = field(default_factory=list)
    positive_signals:        List[RiskSignal] = field(default_factory=list)
    operational_health_score: int   = 100
    score_adjustment:        int    = 0
    confidence:              float  = 1.0

    # Narrative
    explanation:             List[str] = field(default_factory=list)
    sentences:               List[str] = field(default_factory=list)

    # Flags
    manipulation_flags:      List[ManipulationFlag] = field(default_factory=list)
    is_short_observation:    bool = False
    has_seasonal_context:    bool = False
    has_maintenance_context: bool = False
    has_expansion_context:   bool = False

    # Performance
    processing_time_sec:     float = 0.0
    llm_used:                bool  = False

    def to_dict(self) -> Dict[str, Any]:
        active_risks = [
            s for s in self.signals
            if not s.negated and not s.temporal_resolved
        ]
        active_positives = [
            s for s in self.positive_signals
            if not s.negated
        ]
        return {
            "signals": [s.to_dict() for s in active_risks],
            "positive_signals": [s.to_dict() for s in active_positives],
            "all_detected_signals": [s.to_dict() for s in self.signals + self.positive_signals],
            "operational_health_score": self.operational_health_score,
            "score_adjustment": self.score_adjustment,
            "confidence": round(self.confidence, 4),
            "explanation": self.explanation,
            "manipulation_flags": [f.to_dict() for f in self.manipulation_flags],
            "context_flags": {
                "is_short_observation":    self.is_short_observation,
                "has_seasonal_context":    self.has_seasonal_context,
                "has_maintenance_context": self.has_maintenance_context,
                "has_expansion_context":   self.has_expansion_context,
            },
            "metadata": {
                "industry_type":     self.metadata.industry_type.value,
                "facility_type":     self.metadata.facility_type.value,
                "visit_date":        self.metadata.visit_date,
                "facility_location": self.metadata.facility_location,
                "company_name":      self.metadata.company_name,
            },
            "processing_time_sec": round(self.processing_time_sec, 2),
            "llm_used": self.llm_used,
        }


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _log(agent: str, message: str, level: str = "INFO") -> Dict[str, str]:
    from datetime import datetime
    return {
        "timestamp": datetime.now().strftime("%H:%M:%S"),
        "agent":     agent,
        "message":   message,
        "level":     level,
    }


def _extract_json(text: str) -> Dict[str, Any]:
    """Extract the first JSON object from an LLM response string."""
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        start = text.find("{")
        end   = text.rfind("}") + 1
        if start != -1 and end > start:
            try:
                return json.loads(text[start:end])
            except json.JSONDecodeError:
                pass
    return {}


def _sentence_window_is_negated(window: str) -> bool:
    """
    Return True if a negation word appears within 6 tokens before the match.
    Works on a short window of text, not whole-document negation.
    """
    return bool(_NEGATION_RE.search(window))


# ─────────────────────────────────────────────────────────────────────────────
# STEP 1 — SENTENCE SEGMENTATION
# ─────────────────────────────────────────────────────────────────────────────

_SENT_SEP_RE = re.compile(
    r"(?<=[.!?;])\s+(?=[A-Z])"      # Sentence boundary
    r"|(?<=\n)\s*(?=[A-Z•\-\*•])"  # Bullet / newline boundary
    r"|(?<=[.!?])\s+(?=\d)"         # "... 40% capacity. 3 machines..."
)


def segment_sentences(text: str) -> List[str]:
    """
    Break free-text observation into individual sentences.
    Handles bullet points, numbered lists, and irregular punctuation common
    in field notes.
    """
    # Normalize whitespace
    text = re.sub(r"\r\n|\r", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)

    # Split on sentence boundaries
    raw_parts = _SENT_SEP_RE.split(text)

    sentences: List[str] = []
    for part in raw_parts:
        part = part.strip()
        if not part:
            continue
        # Further split on explicit bullet patterns
        sub = re.split(r"\n\s*[-•*]\s*", part)
        for s in sub:
            s = s.strip().rstrip(".")
            if len(s) >= 5:
                sentences.append(s)

    return sentences if sentences else [text.strip()]


# ─────────────────────────────────────────────────────────────────────────────
# STEP 2 — KEYWORD & PHRASE DETECTION
# ─────────────────────────────────────────────────────────────────────────────

def _precompile_patterns(signal_dict: Dict[str, Dict]) -> Dict[str, List[re.Pattern]]:
    compiled: Dict[str, List[re.Pattern]] = {}
    for key, cfg in signal_dict.items():
        compiled[key] = [re.compile(p, re.IGNORECASE) for p in cfg["patterns"]]
    return compiled


_COMPILED_RISK     = _precompile_patterns(_RISK_SIGNALS)
_COMPILED_POSITIVE = _precompile_patterns(_POSITIVE_SIGNALS)


def detect_keyword_signals(
    sentences: List[str],
) -> Tuple[List[RiskSignal], List[RiskSignal]]:
    """
    Run all regex patterns against each sentence.
    Returns (risk_signals, positive_signals).
    Negation context window is the sentence itself (up to the match position).
    """
    risk_out:     List[RiskSignal] = []
    positive_out: List[RiskSignal] = []
    seen_risk     = set()
    seen_positive = set()

    full_text = " ".join(sentences)

    # Detect context booleans once over full text
    seasonal_ctx    = bool(_SEASONAL_RE.search(full_text))
    maintenance_ctx = bool(_MAINTENANCE_RE.search(full_text))
    expansion_ctx   = bool(_EXPANSION_RE.search(full_text))

    for sent in sentences:
        sent_lower = sent.lower()

        # ── Risk signals ──────────────────────────────────────────────
        for sig_key, patterns in _COMPILED_RISK.items():
            if sig_key in seen_risk:
                continue
            for pat in patterns:
                m = pat.search(sent)
                if m:
                    # Pre-match window for negation check  (up to 40 chars before match)
                    window = sent[max(0, m.start() - 40): m.start()]
                    negated          = _sentence_window_is_negated(window)
                    temporal_res     = bool(_TEMPORAL_RESOLVED_RE.search(sent))
                    conditional_flag = bool(_CONDITIONAL_RE.search(sent))
                    uncertain        = bool(_UNCERTAINTY_RE.search(sent))

                    sev = _RISK_SIGNALS[sig_key]["severity"]

                    # Reduce to MEDIUM if uncertain/conditional
                    if (uncertain or conditional_flag) and sev == Severity.HIGH:
                        sev         = Severity.MEDIUM
                        conditional_flag = True

                    note = None
                    if seasonal_ctx and _RISK_SIGNALS[sig_key].get("seasonal_adjustment"):
                        note = "Possible seasonal factor; verify with industry norms"
                        if sev == Severity.HIGH:
                            sev = Severity.MEDIUM
                    if maintenance_ctx and _RISK_SIGNALS[sig_key].get("maintenance_adjustment"):
                        note = "Possible scheduled maintenance; verify timeline"
                        if sev == Severity.HIGH:
                            sev = Severity.MEDIUM

                    risk_out.append(RiskSignal(
                        signal_type       = sig_key,
                        severity          = sev,
                        is_positive       = False,
                        negated           = negated,
                        temporal_resolved = temporal_res,
                        conditional       = conditional_flag,
                        matched_text      = sent[:120],
                        confidence        = 0.9,
                        note              = note,
                    ))
                    seen_risk.add(sig_key)
                    break  # first matching pattern per signal is enough

        # ── Positive signals ──────────────────────────────────────────
        for sig_key, patterns in _COMPILED_POSITIVE.items():
            if sig_key in seen_positive:
                continue
            for pat in patterns:
                m = pat.search(sent)
                if m:
                    window  = sent[max(0, m.start() - 40): m.start()]
                    negated = _sentence_window_is_negated(window)
                    positive_out.append(RiskSignal(
                        signal_type  = sig_key,
                        severity     = Severity.NONE,
                        is_positive  = True,
                        negated      = negated,
                        matched_text = sent[:120],
                        confidence   = 0.9,
                        score_bonus  = _POSITIVE_SIGNALS[sig_key].get("score_bonus", 10),
                    ))
                    seen_positive.add(sig_key)
                    break

    return risk_out, positive_out, seasonal_ctx, maintenance_ctx, expansion_ctx


# ─────────────────────────────────────────────────────────────────────────────
# STEP 3+4 — LLM SEMANTIC CONTEXT ANALYSIS
# ─────────────────────────────────────────────────────────────────────────────

_LLM_ANALYSIS_PROMPT = """\
You are a senior credit analyst reviewing a field visit note written by a credit officer.

Your job is to:
1. Validate which of the pre-detected signals are genuine vs. false positives due to negation, historical context, or uncertainty.
2. Detect any additional risk signals that keyword matching missed.
3. Assess the overall quality and reliability of the observation note.

PRE-DETECTED RISK SIGNALS: {risk_signals}
PRE-DETECTED POSITIVE SIGNALS: {positive_signals}

OBSERVATION TEXT:
\"\"\"
{observation}
\"\"\"

INDUSTRY: {industry}
FACILITY TYPE: {facility_type}
SEASONAL CONTEXT DETECTED: {seasonal}
MAINTENANCE CONTEXT DETECTED: {maintenance}
EXPANSION CONTEXT DETECTED: {expansion}

Return ONLY a valid JSON object with no markdown:
{{
  "validated_signals": [
    {{
      "type": "<signal_type>",
      "verdict": "confirmed|negated|historical|uncertain|irrelevant",
      "confidence": 0.0_to_1.0,
      "note": "<brief explanation>"
    }}
  ],
  "additional_signals": [
    {{
      "type": "<new_signal_key>",
      "severity": "high|medium|low",
      "description": "<what was observed>",
      "positive": false
    }}
  ],
  "overall_confidence": 0.0_to_1.0,
  "manipulation_suspicion": 0.0_to_1.0,
  "manipulation_reason": "<null or brief explanation>",
  "summary": "<2-3 sentence synthesis of key operational risks>"
}}
"""


async def _llm_analyze(
    observation: str,
    risk_signals: List[RiskSignal],
    positive_signals: List[RiskSignal],
    metadata: ObservationMetadata,
    seasonal_ctx: bool,
    maintenance_ctx: bool,
    expansion_ctx: bool,
) -> Dict[str, Any]:
    """Call Claude to validate keyword-detected signals and discover missed signals."""
    Anthropic = _import_anthropic()
    api_key   = os.environ.get("ANTHROPIC_API_KEY")

    if Anthropic is None or not api_key:
        return {}

    risk_list = [
        {"type": s.signal_type, "severity": s.severity.value,
         "negated": s.negated, "temporal_resolved": s.temporal_resolved}
        for s in risk_signals
    ]
    pos_list = [
        {"type": s.signal_type} for s in positive_signals
    ]

    prompt = _LLM_ANALYSIS_PROMPT.format(
        risk_signals     = json.dumps(risk_list, indent=2),
        positive_signals = json.dumps(pos_list,  indent=2),
        observation      = observation[:6000],
        industry         = metadata.industry_type.value,
        facility_type    = metadata.facility_type.value,
        seasonal         = seasonal_ctx,
        maintenance      = maintenance_ctx,
        expansion        = expansion_ctx,
    )

    try:
        client = Anthropic(api_key=api_key)

        def _call():
            return client.messages.create(
                model      = "claude-sonnet-4-20250514",
                max_tokens = 1500,
                messages   = [{"role": "user", "content": prompt}],
            )

        loop     = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, _call)
        raw      = response.content[0].text.strip()
        return _extract_json(raw)

    except Exception as exc:
        logger.warning(f"[OIE] LLM analysis failed: {exc}")
        return {}


# ─────────────────────────────────────────────────────────────────────────────
# STEP 4+5 — SIGNAL REFINEMENT & INDUSTRY ADJUSTMENT
# ─────────────────────────────────────────────────────────────────────────────

def _apply_llm_verdicts(
    risk_signals: List[RiskSignal],
    llm_result: Dict[str, Any],
) -> List[RiskSignal]:
    """Apply LLM-generated verdicts to update signal flags."""
    validation_map: Dict[str, Dict] = {}
    for v in llm_result.get("validated_signals", []):
        validation_map[v["type"]] = v

    updated: List[RiskSignal] = []
    for sig in risk_signals:
        verdict_info = validation_map.get(sig.signal_type)
        if verdict_info:
            verdict = verdict_info.get("verdict", "confirmed")
            note    = verdict_info.get("note")
            conf    = float(verdict_info.get("confidence", sig.confidence))
            if verdict == "negated":
                sig.negated    = True
                sig.confidence = conf
            elif verdict == "historical":
                sig.temporal_resolved = True
                sig.confidence = conf
            elif verdict == "uncertain":
                sig.conditional = True
                if sig.severity == Severity.HIGH:
                    sig.severity = Severity.MEDIUM
                sig.confidence = conf
            elif verdict == "irrelevant":
                sig.negated    = True      # Treat as inactive
                sig.confidence = conf
            else:
                sig.confidence = conf
            if note:
                sig.note = note
        updated.append(sig)

    # Add LLM-discovered additional signals
    for add_sig in llm_result.get("additional_signals", []):
        sev_str = add_sig.get("severity", "medium").lower()
        sev     = Severity.MEDIUM
        if sev_str == "high":
            sev = Severity.HIGH
        elif sev_str == "low":
            sev = Severity.LOW
        is_pos = bool(add_sig.get("positive", False))
        updated.append(RiskSignal(
            signal_type  = add_sig.get("type", "unknown_risk"),
            severity     = sev,
            is_positive  = is_pos,
            matched_text = add_sig.get("description", ""),
            confidence   = 0.75,   # Slightly lower confidence for LLM-only signals
            note         = "Detected by LLM semantic analysis",
        ))

    return updated


def adjust_for_industry(
    risk_signals: List[RiskSignal],
    positive_signals: List[RiskSignal],
    metadata: ObservationMetadata,
    seasonal_ctx: bool,
    expansion_ctx: bool,
) -> Tuple[List[RiskSignal], List[str]]:
    """
    Apply industry-specific adjustments to reduce false positives.
    Returns (adjusted_signals, adjustment_notes).
    """
    profile = _INDUSTRY_PROFILES.get(metadata.industry_type, _INDUSTRY_PROFILES[IndustryType.UNKNOWN])
    notes:   List[str] = []

    # Signals that are physically irrelevant for this industry (e.g., inventory for IT)
    irrelevant = set(profile.get("physical_irrelevant", []))

    adjusted: List[RiskSignal] = []
    for sig in risk_signals:
        if sig.signal_type in irrelevant:
            sig.negated = True
            sig.note    = f"Not applicable for {metadata.industry_type.value} industry"
            notes.append(f"Signal '{sig.signal_type}' marked irrelevant for {metadata.industry_type.value}")
        elif seasonal_ctx and sig.signal_type in profile.get("seasonal_signals", []):
            if sig.severity == Severity.HIGH:
                sig.severity = Severity.MEDIUM
            sig.note = profile.get("season_note", "Possible seasonal factor")
            notes.append(f"Signal '{sig.signal_type}' downgraded to MEDIUM due to seasonal context ({metadata.industry_type.value})")
        elif expansion_ctx and sig.signal_type in ("idle_production_lines", "low_capacity_utilization"):
            if sig.severity == Severity.HIGH:
                sig.severity = Severity.MEDIUM
            sig.note = "Expansion phase may temporarily show idle equipment — verify"
            notes.append(f"Signal '{sig.signal_type}' downgraded due to capacity expansion context")
        adjusted.append(sig)

    return adjusted, notes


# ─────────────────────────────────────────────────────────────────────────────
# STEP 6 — OPERATIONAL RISK SCORING
# ─────────────────────────────────────────────────────────────────────────────

def calculate_operational_score(
    risk_signals:     List[RiskSignal],
    positive_signals: List[RiskSignal],
    observation_length: int,
) -> Tuple[int, int]:
    """
    Returns (operational_health_score, score_adjustment).

    Scoring logic:
      Start at 100.
      Deduct per active (non-negated, non-resolved) risk signal by severity.
      Add back for active positive signals.
      Floor at 0.
    """
    total_deduction = 0
    total_bonus     = 0

    for sig in risk_signals:
        if sig.negated or sig.temporal_resolved:
            continue
        weight = _SEVERITY_DEDUCTION.get(sig.severity, 0)
        # Reduce weight for uncertain/conditional signals
        if sig.conditional:
            weight = int(weight * 0.5)
        # Reduce weight for low-confidence signals
        weight = int(weight * sig.confidence)
        total_deduction += weight

    for sig in positive_signals:
        if sig.negated:
            continue
        total_bonus += sig.score_bonus

    # Dampen bonuses if observation is very short (less reliable)
    if observation_length < 80:
        total_bonus = int(total_bonus * 0.5)

    score_adjustment = total_bonus - total_deduction
    raw_score        = _BASE_HEALTH_SCORE + score_adjustment
    final_score      = max(_MIN_HEALTH_SCORE, min(_MAX_HEALTH_SCORE, raw_score))

    return final_score, score_adjustment


# ─────────────────────────────────────────────────────────────────────────────
# STEP 7 — MANIPULATION DETECTION
# ─────────────────────────────────────────────────────────────────────────────

def detect_manipulation_flags(
    risk_signals:     List[RiskSignal],
    positive_signals: List[RiskSignal],
    llm_suspicion:    float,
) -> Tuple[List[ManipulationFlag], float]:
    """
    Detect contradictory signal pairs that may indicate staged or misleading visits.
    Returns (flags, confidence_after_penalty).
    """
    active_risk = {
        s.signal_type for s in risk_signals
        if not s.negated and not s.temporal_resolved
    }
    active_pos  = {
        s.signal_type for s in positive_signals
        if not s.negated
    }
    all_active  = active_risk | active_pos

    flags: List[ManipulationFlag] = []
    confidence_penalty = 0.0

    for sig_a, sig_b, description in _MANIPULATION_PAIRS:
        if sig_a in all_active and sig_b in all_active:
            flags.append(ManipulationFlag(
                signal_a=sig_a, signal_b=sig_b,
                description=description,
            ))
            confidence_penalty += ManipulationFlag(sig_a, sig_b, description).confidence_penalty

    # LLM-driven suspicion also reduces confidence
    if llm_suspicion > 0.5:
        confidence_penalty += (llm_suspicion - 0.5) * 0.3

    return flags, min(0.40, confidence_penalty)   # Max 40% penalty


# ─────────────────────────────────────────────────────────────────────────────
# STEP 8 — CONFIDENCE CALCULATION
# ─────────────────────────────────────────────────────────────────────────────

def calculate_confidence(
    observation:      str,
    risk_signals:     List[RiskSignal],
    manipulation_pen: float,
    llm_used:         bool,
) -> float:
    """
    Derive a confidence score for the overall extraction result.
    High-confidence = long observation, few contradictions, LLM validated.
    """
    base      = 0.85 if llm_used else 0.70

    # Length bonus: longer notes are more reliable
    length    = len(observation)
    if length > 500:
        base += 0.10
    elif length > 200:
        base += 0.05
    elif length < 80:
        base -= 0.15   # Very short — could be unreliable

    # Average signal confidence
    if risk_signals:
        avg_sig_conf = sum(s.confidence for s in risk_signals) / len(risk_signals)
        base = base * 0.5 + avg_sig_conf * 0.5

    # Manipulation penalty
    base -= manipulation_pen

    return round(max(0.20, min(1.0, base)), 4)


# ─────────────────────────────────────────────────────────────────────────────
# STEP 9 — EXPLANATION BUILDER
# ─────────────────────────────────────────────────────────────────────────────

_SIGNAL_EXPLANATIONS: Dict[str, str] = {
    "low_capacity_utilization":    "Facility appears to be operating significantly below capacity",
    "plant_shutdown":              "Production appears stopped or the facility is closed",
    "idle_production_lines":       "Production lines / machines observed idle",
    "obsolete_machinery":          "Machinery appears old or technologically outdated",
    "poor_facility_maintenance":   "Facility is not well-maintained — structural or housekeeping concerns",
    "inventory_overstock":         "Large accumulation of unsold finished goods observed",
    "excess_raw_material":         "Excess raw material stock observed — possible order slowdown",
    "supply_chain_disruption":     "Evidence of supply chain or raw material procurement issues",
    "labor_dissatisfaction":       "Workers/employees appear dissatisfied or mention grievances",
    "salary_delays":               "Salary or wage payment delays indicated",
    "safety_violations":           "Safety non-compliance or hazardous working conditions observed",
    "environmental_non_compliance":"Environmental regulation violations or pollution concerns noted",
    "management_evasion":          "Management was evasive, uncooperative, or withheld information",
    "misleading_representations":  "Management made unverifiable claims or seemed over-optimistic",
    "key_person_dependency":       "Business appears highly dependent on a single person or promoter",
    "cash_flow_stress":            "Signs of cash flow strain — delayed payments to suppliers/creditors",
    "high_receivables_stress":     "Large or aged outstanding receivables — collection challenges",
    "asset_quality_concern":       "Asset condition raises questions about collateral valuation",
    "regulatory_issues":           "Regulatory notices, penalties, or compliance concerns flagged",
}

_POSITIVE_EXPLANATIONS: Dict[str, str] = {
    "high_production_activity":  "Facility operating at high capacity with active production",
    "capacity_expansion":        "Capacity expansion or new unit construction underway",
    "new_machinery":             "New or upgraded machinery observed",
    "good_facility_condition":   "Facility is well-maintained and in good condition",
    "no_labor_issues":           "No labor disputes or wage-payment issues observed",
    "strong_management":         "Management was professional, transparent, and cooperative",
    "healthy_order_pipeline":    "Strong order book or confirmed future orders in place",
}


def build_explanation(
    risk_signals:     List[RiskSignal],
    positive_signals: List[RiskSignal],
    adjustment_notes: List[str],
    llm_summary:      Optional[str] = None,
) -> List[str]:
    explanation: List[str] = []

    for sig in risk_signals:
        if sig.negated:
            explanation.append(
                f"No '{sig.signal_type.replace('_',' ')}' detected (negated in text)"
            )
        elif sig.temporal_resolved:
            explanation.append(
                f"'{sig.signal_type.replace('_',' ')}' was reported as a past issue — now resolved"
            )
        elif sig.conditional:
            explanation.append(
                _SIGNAL_EXPLANATIONS.get(sig.signal_type, sig.signal_type.replace("_", " "))
                + " (conditional / uncertain)"
            )
        else:
            explanation.append(
                _SIGNAL_EXPLANATIONS.get(sig.signal_type, sig.signal_type.replace("_", " "))
            )

    for sig in positive_signals:
        if not sig.negated:
            explanation.append(
                "✓ " + _POSITIVE_EXPLANATIONS.get(sig.signal_type, sig.signal_type.replace("_", " "))
            )

    explanation.extend(adjustment_notes)

    if llm_summary:
        explanation.append(f"LLM synthesis: {llm_summary}")

    return explanation


# ─────────────────────────────────────────────────────────────────────────────
# MAIN PIPELINE
# ─────────────────────────────────────────────────────────────────────────────

async def process_observation(
    observation_text:  str,
    metadata:          Optional[ObservationMetadata] = None,
    attachments:       Optional[List[str]] = None,   # photo/doc paths (for future use)
    use_llm:           bool = True,
) -> ObservationResult:
    """
    Full Observation Intelligence pipeline.

    Args:
        observation_text: Free-text note from the credit officer.
        metadata:         Optional visit context (industry, facility type, etc.).
        attachments:      Paths to attached files (reserved for future extension).
        use_llm:          If True and ANTHROPIC_API_KEY is set, run LLM analysis.

    Returns:
        ObservationResult — structured risk signals + scoring.
    """
    t_start  = time.monotonic()
    metadata = metadata or ObservationMetadata()
    observation_text = observation_text.strip()

    # ── Validate input ───────────────────────────────────────────────────────
    is_short = len(observation_text) < 80

    # ── Step 1: Sentence segmentation ────────────────────────────────────────
    sentences = segment_sentences(observation_text)

    # ── Step 2: Keyword detection ─────────────────────────────────────────────
    risk_kw, positive_kw, seasonal_ctx, maintenance_ctx, expansion_ctx = \
        detect_keyword_signals(sentences)

    # ── Step 3+4: LLM semantic validation ────────────────────────────────────
    llm_result:  Dict[str, Any] = {}
    llm_summary: Optional[str]  = None
    llm_used = False

    if use_llm and not is_short and (risk_kw or positive_kw):
        llm_result = await _llm_analyze(
            observation_text, risk_kw, positive_kw, metadata,
            seasonal_ctx, maintenance_ctx, expansion_ctx,
        )
        llm_used    = bool(llm_result)
        llm_summary = llm_result.get("summary")

    # Apply LLM verdicts to risk signals
    if llm_result:
        all_signals = _apply_llm_verdicts(risk_kw + positive_kw, llm_result)
        risk_signals     = [s for s in all_signals if not s.is_positive]
        positive_signals = [s for s in all_signals if s.is_positive]
    else:
        risk_signals     = risk_kw
        positive_signals = positive_kw

    # ── Step 5: Industry context adjustment ───────────────────────────────────
    risk_signals, adjustment_notes = adjust_for_industry(
        risk_signals, positive_signals, metadata, seasonal_ctx, expansion_ctx
    )

    # ── Step 6: Score ─────────────────────────────────────────────────────────
    health_score, score_adj = calculate_operational_score(
        risk_signals, positive_signals, len(observation_text)
    )

    # ── Step 7: Manipulation detection ───────────────────────────────────────
    llm_suspicion = float(llm_result.get("manipulation_suspicion", 0.0))
    manip_flags, confidence_penalty = detect_manipulation_flags(
        risk_signals, positive_signals, llm_suspicion
    )
    if llm_result.get("manipulation_reason"):
        logger.warning(f"[OIE] Manipulation suspicion: {llm_result['manipulation_reason']}")

    # ── Step 8: Confidence ────────────────────────────────────────────────────
    confidence = calculate_confidence(
        observation_text, risk_signals, confidence_penalty, llm_used
    )

    # ── Step 9: Explanation ───────────────────────────────────────────────────
    explanation = build_explanation(
        risk_signals, positive_signals, adjustment_notes, llm_summary
    )

    elapsed = time.monotonic() - t_start

    return ObservationResult(
        raw_text                 = observation_text,
        metadata                 = metadata,
        signals                  = risk_signals,
        positive_signals         = positive_signals,
        operational_health_score = health_score,
        score_adjustment         = score_adj,
        confidence               = confidence,
        explanation              = explanation,
        sentences                = sentences,
        manipulation_flags       = manip_flags,
        is_short_observation     = is_short,
        has_seasonal_context     = seasonal_ctx,
        has_maintenance_context  = maintenance_ctx,
        has_expansion_context    = expansion_ctx,
        processing_time_sec      = elapsed,
        llm_used                 = llm_used,
    )


# ─── Batch Processing ─────────────────────────────────────────────────────────

async def process_observations_batch(
    observations: List[Dict[str, Any]],
    max_concurrent: int = 4,
) -> List[ObservationResult]:
    """
    Process multiple observation notes concurrently.

    Args:
        observations: List of dicts with keys:
                      "text"     — observation text (required)
                      "metadata" — ObservationMetadata (optional)
                      "use_llm"  — bool (optional, default True)
        max_concurrent: Semaphore limit.

    Returns:
        List of ObservationResult in same order as input.
    """
    semaphore = asyncio.Semaphore(max_concurrent)

    async def _bounded(obs_dict: Dict[str, Any]) -> ObservationResult:
        async with semaphore:
            return await process_observation(
                observation_text = obs_dict["text"],
                metadata         = obs_dict.get("metadata"),
                use_llm          = obs_dict.get("use_llm", True),
            )

    return list(await asyncio.gather(*[_bounded(o) for o in observations]))


# ─── Integration Helpers ──────────────────────────────────────────────────────

def extract_for_red_flag_engine(result: ObservationResult) -> Dict[str, Any]:
    """
    Map ObservationResult to parameters consumable by
    scoring.red_flag_engine.evaluate_red_flags().
    """
    active = {
        s.signal_type for s in result.signals
        if not s.negated and not s.temporal_resolved
    }
    return {
        "gst_status":              "Cancelled" if "regulatory_issues" in active else "Active",
        "cheque_bounce_count":     1 if "cash_flow_stress" in active else 0,
        "going_concern_flag":      result.operational_health_score < 40,
        "has_criminal_cases":      False,
        "auditor_changes_count":   0,
        "pending_cases":           1 if "regulatory_issues" in active else 0,
        # Operational flags
        "low_capacity_utilization": "low_capacity_utilization" in active,
        "labor_stress":             "salary_delays" in active or "labor_dissatisfaction" in active,
        "management_evasion":       "management_evasion" in active,
        "safety_violations":        "safety_violations" in active,
        "environmental_issues":     "environmental_non_compliance" in active,
        "inventory_overstock":      "inventory_overstock" in active,
    }


def extract_for_risk_matrix(result: ObservationResult) -> Dict[str, Any]:
    """
    Return a risk-matrix-friendly summary.
    """
    active = [
        s for s in result.signals
        if not s.negated and not s.temporal_resolved
    ]
    high_count   = sum(1 for s in active if s.severity == Severity.HIGH)
    medium_count = sum(1 for s in active if s.severity == Severity.MEDIUM)
    low_count    = sum(1 for s in active if s.severity == Severity.LOW)

    if high_count >= 3 or result.operational_health_score < 35:
        risk_category = "HIGH"
    elif high_count >= 1 or medium_count >= 3 or result.operational_health_score < 60:
        risk_category = "MEDIUM"
    else:
        risk_category = "LOW"

    return {
        "operational_risk_category": risk_category,
        "operational_health_score":  result.operational_health_score,
        "high_severity_signals":     high_count,
        "medium_severity_signals":   medium_count,
        "low_severity_signals":      low_count,
        "manipulation_suspected":    len(result.manipulation_flags) > 0,
        "confidence":                result.confidence,
    }


def extract_for_cam_generator(result: ObservationResult) -> Dict[str, Any]:
    """
    Return structured data suitable for inclusion in a CAM report's
    operational due diligence section.
    """
    active_risks = [
        {
            "signal":   s.signal_type.replace("_", " ").title(),
            "severity": s.severity.value.upper(),
            "note":     s.note or "",
        }
        for s in result.signals
        if not s.negated and not s.temporal_resolved
    ]
    active_pos = [
        s.signal_type.replace("_", " ").title()
        for s in result.positive_signals
        if not s.negated
    ]
    return {
        "section":                   "Operational Due Diligence",
        "visit_date":                result.metadata.visit_date,
        "facility_location":         result.metadata.facility_location,
        "facility_type":             result.metadata.facility_type.value,
        "industry":                  result.metadata.industry_type.value,
        "operational_health_score":  result.operational_health_score,
        "risk_signals":              active_risks,
        "positive_observations":     active_pos,
        "explanation":               result.explanation,
        "manipulation_flags":        [f.to_dict() for f in result.manipulation_flags],
        "confidence":                result.confidence,
        "analyst_assessment":        result.raw_text,
    }


def extract_for_scoring_engine(result: ObservationResult) -> Dict[str, Any]:
    """
    Return the score adjustment and category for integration with
    scoring/dynamic_weights.py.
    """
    return {
        "operational_health_score":  result.operational_health_score,
        "score_adjustment":          result.score_adjustment,
        "confidence":                result.confidence,
        "manipulation_detected":     len(result.manipulation_flags) > 0,
        "high_severity_count":       sum(
            1 for s in result.signals
            if s.severity == Severity.HIGH and not s.negated and not s.temporal_resolved
        ),
    }


# ─────────────────────────────────────────────────────────────────────────────
# DEMO / SMOKE TEST
# ─────────────────────────────────────────────────────────────────────────────

_DEMO_OBSERVATIONS = [
    {
        "label": "Stressed textile manufacturer",
        "text": (
            "Factory operating at roughly 40% capacity. "
            "Machines appear more than 10 years old and in poor condition. "
            "Workers mentioned salary delays of about 45 days. "
            "Large unsold inventory observed in warehouse — stock piled up. "
            "Management was cooperative but acknowledged demand slowdown."
        ),
        "metadata": ObservationMetadata(
            industry_type=IndustryType.TEXTILES,
            facility_type=FacilityType.PLANT,
            visit_date="2026-03-05",
            facility_location="Surat, Gujarat",
            company_name="ABC Textiles Ltd",
        ),
    },
    {
        "label": "Expanding pharmaceutical plant",
        "text": (
            "Plant is operating at near full capacity. "
            "New machinery installed last quarter — state of the art. "
            "Facility is very well maintained and clean. "
            "Management was professional and forthcoming. "
            "New production line being commissioned for export orders. "
            "Strong order book visible from confirmed orders."
        ),
        "metadata": ObservationMetadata(
            industry_type=IndustryType.PHARMACEUTICALS,
            facility_type=FacilityType.PLANT,
            visit_date="2026-02-20",
            facility_location="Baddi, Himachal Pradesh",
            company_name="PharmaHealth Pvt Ltd",
        ),
    },
    {
        "label": "Manipulation-suspected visit",
        "text": (
            "Factory appeared very active during the visit. "
            "All machines were running. "
            "However, workers mentioned they had not received salaries for 3 months. "
            "Management claimed strong order pipeline but could not show purchase orders. "
            "Inventory was high despite claimed high production."
        ),
        "metadata": ObservationMetadata(
            industry_type=IndustryType.MANUFACTURING,
            facility_type=FacilityType.PLANT,
            visit_date="2026-03-01",
            company_name="Suspicious Mfg Co",
        ),
    },
    {
        "label": "Seasonal food processor (off-season shutdown)",
        "text": (
            "Plant is currently shut for the off-season. "
            "Production was halted last month as expected during lean season. "
            "No labor issues reported. "
            "Management confirmed orders will resume with harvest season."
        ),
        "metadata": ObservationMetadata(
            industry_type=IndustryType.FOOD_PROCESSING,
            facility_type=FacilityType.PLANT,
            visit_date="2026-01-15",
            company_name="Agro Foods Ltd",
        ),
    },
    {
        "label": "Short / minimal observation",
        "text": "Factory visit done. Nothing major to report.",
        "metadata": ObservationMetadata(industry_type=IndustryType.UNKNOWN),
    },
]


async def main_example():
    """
    Run the Observation Intelligence Engine on demo scenarios (no real LLM calls).
    """
    print("=" * 72)
    print("OBSERVATION INTELLIGENCE ENGINE — DEMO")
    print("=" * 72)

    for scenario in _DEMO_OBSERVATIONS:
        print(f"\n{'─'*72}")
        print(f"Scenario : {scenario['label']}")
        print(f"Industry : {scenario['metadata'].industry_type.value}")

        # Run without LLM to avoid API calls in demo
        result = await process_observation(
            observation_text = scenario["text"],
            metadata         = scenario["metadata"],
            use_llm          = False,
        )
        out = result.to_dict()

        print(f"\n  ▶ Operational Health Score : {out['operational_health_score']}/100")
        print(f"  ▶ Score Adjustment          : {out['score_adjustment']}")
        print(f"  ▶ Confidence               : {out['confidence']}")
        print(f"  ▶ Processing Time          : {out['processing_time_sec']}s")
        print(f"  ▶ Short Observation        : {out['context_flags']['is_short_observation']}")
        print(f"  ▶ Seasonal Context         : {out['context_flags']['has_seasonal_context']}")
        print(f"  ▶ Expansion Context        : {out['context_flags']['has_expansion_context']}")

        if out["signals"]:
            print(f"\n  ⚠ Risk Signals ({len(out['signals'])}):")
            for s in out["signals"]:
                tag = ""
                if s.get("conditional"):
                    tag = " [conditional]"
                elif s.get("temporal_resolved"):
                    tag = " [historical/resolved]"
                print(f"    • [{s['severity'].upper():6s}] {s['type'].replace('_',' ').title()}{tag}")
                if s.get("note"):
                    print(f"              ↳ {s['note']}")

        if out["positive_signals"]:
            print(f"\n  ✓ Positive Signals ({len(out['positive_signals'])}):")
            for s in out["positive_signals"]:
                print(f"    • {s['type'].replace('_',' ').title()}")

        if out["manipulation_flags"]:
            print(f"\n  🔴 Manipulation Flags ({len(out['manipulation_flags'])}):")
            for f in out["manipulation_flags"]:
                print(f"    • {f['description']}")

        print(f"\n  ▶ Explanation:")
        for line in out["explanation"][:6]:
            print(f"    - {line}")

        # Integration helpers
        rf  = extract_for_red_flag_engine(result)
        rm  = extract_for_risk_matrix(result)
        cam = extract_for_cam_generator(result)
        scr = extract_for_scoring_engine(result)
        print(f"\n  ▶ Risk Matrix Category : {rm['operational_risk_category']}")
        print(f"  ▶ Scoring Engine adj   : {scr['score_adjustment']}")
        print(f"  ▶ High signals (RF)    : {scr['high_severity_count']}")

    print("\n" + "=" * 72)
    print("NORMALIZATION / NEGATION TEST")
    print("=" * 72)
    tests = [
        # Negation — signal must NOT be active
        ("No labour issues reported.", "labor_dissatisfaction", True),
        # Direct detection — signal MUST be active
        ("Workers mentioned salary delays.", "salary_delays", False),
        # Temporal resolution — signal must NOT be active
        ("Salary delays occurred last year but now resolved.", "salary_delays", True),
        # Conditional present capacity signal — signal IS active (at 30%, conditional)
        ("Factory currently running at 30% capacity, though improvements expected if new orders arrive.", "low_capacity_utilization", False),
    ]
    for text, expected_signal, expect_inactive in tests:
        r = await process_observation(text, use_llm=False)
        active = {
            s.signal_type for s in r.signals
            if not s.negated and not s.temporal_resolved
        }
        signal_inactive = expected_signal not in active
        status = "✓" if signal_inactive == expect_inactive else "✗"
        label  = "inactive" if expect_inactive else "active"
        print(f"  {status} '{text[:60]}' → {expected_signal} expected {label}: "
              f"{'inactive' if signal_inactive else 'active'}")


if __name__ == "__main__":
    asyncio.run(main_example())
