import json
import os

# ============================================================================
# STEP 1 - LOAD ALL FILES
# ============================================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def load_json(filename):
    with open(os.path.join(BASE_DIR, filename), "r") as f:
        return json.load(f)

BENCHMARKS = load_json("benchmarks.json")
WEIGHT_PROFILES = load_json("weight_profiles.json")
SCORING_BANDS = load_json("scoring_bands.json")
RBI_FLOORS = load_json("rbi_floors.json")


# ============================================================================
# STEP 2 - NIC CODE TO SECTOR MAPPING
# ============================================================================

def get_sector_from_nic(nic_code: str) -> str:
    """
    Map NIC code to sector bucket in benchmarks.json.
    Returns 'all_industry' as fallback if NIC code not found.
    """
    for sector, data in BENCHMARKS["sectors"].items():
        if nic_code in data.get("nic_codes", []):
            return sector
    return "all_industry"


# ============================================================================
# STEP 3 - BENCHMARK LOOKUP FUNCTION
# ============================================================================

def get_benchmark(nic_code: str, ratio: str) -> dict:
    """
    Return P25, median, P75 for any ratio in any sector.
    Always includes source and companies sampled.
    """
    sector = get_sector_from_nic(nic_code)
    sector_data = BENCHMARKS["sectors"][sector]
    ratio_data = sector_data["ratios"].get(ratio)

    if ratio_data is None:
        sector_data = BENCHMARKS["sectors"]["all_industry"]
        ratio_data = sector_data["ratios"][ratio]
        fallback_used = True
    else:
        fallback_used = False

    return {
        "p25": ratio_data["p25"],
        "median": ratio_data["median"],
        "p75": ratio_data["p75"],
        "higher_is_better": ratio_data.get("higher_is_better", True),
        "sector": sector,
        "companies_sampled": sector_data.get("companies_sampled", []),
        "source": BENCHMARKS["metadata"]["source"],
        "collection_date": BENCHMARKS["metadata"]["collection_date"],
        "fallback_used": fallback_used,
        "fallback_reason": (
            "NIC code not found — using all industry median"
            if fallback_used else None
        )
    }


# ============================================================================
# STEP 4 - RBI FLOOR LOOKUP FUNCTION
# ============================================================================

def get_rbi_floor(ratio: str) -> dict:
    """
    Return RBI hard floor for any ratio along with circular reference.
    """
    floor_data = RBI_FLOORS.get(ratio)
    if floor_data is None:
        return {
            "has_floor": False,
            "floor": None,
            "source": None,
            "breach_action": None
        }
    return {
        "has_floor": True,
        **floor_data
    }


# ============================================================================
# STEP 5 - WEIGHT PROFILE LOOKUP FUNCTION
# ============================================================================

def get_weight_profile(loan_type: str) -> dict:
    """
    Return scoring weights for a given loan type.
    """
    profile = WEIGHT_PROFILES.get(
        loan_type,
        WEIGHT_PROFILES["term_loan"]
    )
    return {
        "weights": profile["weights"],
        "rationale": profile["rationale"],
        "loan_type": loan_type
    }


# ============================================================================
# STEP 7 - ABSOLUTE SCORING FUNCTION
# ============================================================================

def score_absolute(
    ratio_name: str,
    company_value: float,
    rbi_floor: dict,
    company_name: str
) -> dict:
    """
    Score using absolute bands from scoring_bands.json.
    """
    bands = SCORING_BANDS[ratio_name]["bands"]

    for band in bands:
        min_val = band.get("min")
        max_val = band.get("max")

        in_band = (
            (min_val is None or company_value >= min_val) and
            (max_val is None or company_value < max_val)
        )

        if in_band:
            return {
                "ratio": ratio_name,
                "company_value": company_value,
                "score": band["score"],
                "flag": band["flag"],
                "rbi_floor": rbi_floor.get("floor"),
                "rbi_source": rbi_floor.get("source"),
                "reason": (
                    f"{company_name} {ratio_name} is {company_value}. "
                    f"{band['label']}. "
                    f"RBI minimum: {rbi_floor.get('floor', 'N/A')}. "
                    f"Source: {rbi_floor.get('source', 'Bank policy')}."
                ),
                "scoring_method": "absolute_bands",
                "exclude_from_average": False
            }

    return {
        "ratio": ratio_name,
        "company_value": company_value,
        "score": 0,
        "flag": "RED",
        "reason": "Value outside all defined bands",
        "exclude_from_average": False
    }


# ============================================================================
# STEP 8 - BENCHMARK SCORING FUNCTION
# ============================================================================

def score_against_benchmark(
    ratio_name: str,
    company_value: float,
    nic_code: str,
    company_name: str
) -> dict:
    """
    Score by comparing company value against industry benchmarks.
    """
    benchmark = get_benchmark(nic_code, ratio_name)
    higher_is_better = benchmark["higher_is_better"]
    p25 = benchmark["p25"]
    median = benchmark["median"]
    p75 = benchmark["p75"]

    if higher_is_better:
        if company_value >= p75:
            score, flag = 100, "GREEN"
            label = "Top quartile in industry"
        elif company_value >= median:
            score, flag = 75, "GREEN"
            label = "Above industry median"
        elif company_value >= p25:
            score, flag = 50, "AMBER"
            label = "Below industry median"
        else:
            score, flag = 25, "RED"
            label = "Bottom quartile — weak vs peers"
    else:
        if company_value <= p25:
            score, flag = 100, "GREEN"
            label = "Top quartile in industry"
        elif company_value <= median:
            score, flag = 75, "GREEN"
            label = "Better than industry median"
        elif company_value <= p75:
            score, flag = 50, "AMBER"
            label = "Worse than industry median"
        else:
            score, flag = 25, "RED"
            label = "Bottom quartile — high vs peers"

    return {
        "ratio": ratio_name,
        "company_value": company_value,
        "score": score,
        "flag": flag,
        "industry_p25": p25,
        "industry_median": median,
        "industry_p75": p75,
        "sector": benchmark["sector"],
        "companies_sampled": benchmark["companies_sampled"],
        "source": benchmark["source"],
        "collection_date": benchmark["collection_date"],
        "fallback_used": benchmark["fallback_used"],
        "reason": (
            f"{company_name} {ratio_name} is {company_value}. "
            f"{benchmark['sector']} industry median is {median} "
            f"based on {len(benchmark['companies_sampled'])} "
            f"listed companies. {label}. "
            f"Source: {benchmark['source']} "
            f"{benchmark['collection_date']}."
        ),
        "scoring_method": "benchmark_comparison",
        "exclude_from_average": False
    }


# ============================================================================
# STEP 6 - MASTER SCORING FUNCTION
# ============================================================================

def score_ratio(
    ratio_name: str,
    company_value: float,
    nic_code: str,
    company_name: str = "Company"
) -> dict:
    """
    Master function to score any ratio.
    Decides automatically whether to use absolute bands or benchmark comparison.
    Checks RBI floors first.
    """
    if company_value is None:
        return {
            "ratio": ratio_name,
            "company_value": None,
            "score": None,
            "flag": "MANUAL_VERIFICATION_REQUIRED",
            "reason": "Data not available — manual review needed",
            "exclude_from_average": True
        }

    rbi_floor = get_rbi_floor(ratio_name)

    if rbi_floor["has_floor"]:
        floor_val = rbi_floor.get("floor") or rbi_floor.get("ceiling")
        breach_action = rbi_floor["breach_action"]
        is_ceiling = "ceiling" in rbi_floor

        breached = (
            company_value > floor_val if is_ceiling
            else company_value < floor_val
        )

        if breached:
            return {
                "ratio": ratio_name,
                "company_value": company_value,
                "rbi_floor": floor_val,
                "rbi_source": rbi_floor["source"],
                "score": 0,
                "flag": breach_action,
                "reason": (
                    f"{company_name} {ratio_name} of {company_value} "
                    f"breaches RBI floor of {floor_val}. "
                    f"Source: {rbi_floor['source']}. "
                    f"Action: {breach_action}."
                ),
                "exclude_from_average": breach_action == "HARD_REJECT"
            }

    if ratio_name in SCORING_BANDS:
        return score_absolute(ratio_name, company_value,
                              rbi_floor, company_name)
    else:
        return score_against_benchmark(ratio_name, company_value,
                                       nic_code, company_name)


# ============================================================================
# STEP 9 - WEIGHTED FINAL SCORE FUNCTION
# ============================================================================

def calculate_weighted_score(
    ratio_scores: list,
    loan_type: str
) -> dict:
    """
    Calculate final weighted score from all ratio scores.
    Excludes ratios marked as exclude_from_average.
    Adjusts weights proportionally for missing ratios.
    """
    profile = get_weight_profile(loan_type)
    weights = profile["weights"]

    valid_scores = [
        r for r in ratio_scores
        if r["score"] is not None
        and not r.get("exclude_from_average", False)
    ]

    excluded = [
        r for r in ratio_scores
        if r.get("exclude_from_average", False)
    ]

    total_weight = sum(
        weights.get(r["ratio"], 0) for r in valid_scores
    )

    if total_weight == 0:
        return {
            "weighted_score": 0,
            "flag": "RED",
            "reason": "No valid ratios available for scoring"
        }

    weighted_sum = sum(
        r["score"] * weights.get(r["ratio"], 0)
        for r in valid_scores
    )

    final_score = (weighted_sum / total_weight)

    return {
        "weighted_score": round(final_score, 2),
        "total_weight_used": total_weight,
        "ratios_scored": len(valid_scores),
        "ratios_excluded": len(excluded),
        "excluded_ratios": [r["ratio"] for r in excluded],
        "weight_profile": loan_type,
        "weight_rationale": profile["rationale"],
        "flag": (
            "GREEN" if final_score >= 75
            else "AMBER" if final_score >= 45
            else "RED"
        )
    }


# ============================================================================
# STEP 10 - SINGLE TEST TO VERIFY EVERYTHING WORKS
# ============================================================================

if __name__ == "__main__":

    test_cases = [
        {"ratio": "dscr", "value": 1.1, "nic": "13"},
        {"ratio": "dscr", "value": 1.8, "nic": "13"},
        {"ratio": "current_ratio", "value": 1.1, "nic": "62"},
        {"ratio": "debt_to_equity", "value": 2.5, "nic": "13"},
        {"ratio": "ebitda_margin", "value": 25.0, "nic": "21"},
        {"ratio": "gst_mismatch", "value": 0.22, "nic": "46"},
        {"ratio": "dscr", "value": None, "nic": "10"},
    ]

    print("="*80)
    print("REFERENCE DATA SCORING TEST")
    print("="*80)
    print()

    for test in test_cases:
        result = score_ratio(
            test["ratio"],
            test["value"],
            test["nic"],
            "Test Company"
        )
        print(f"RATIO: {test['ratio']} = {test['value']}")
        print(f"Score: {result['score']} | Flag: {result['flag']}")
        print(f"Reason: {result['reason']}")
        print("-"*80)
        print()
