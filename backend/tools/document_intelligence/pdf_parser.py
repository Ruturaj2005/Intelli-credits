"""
PDF financial extraction for annual reports.

This module focuses on extracting NBFC/company financial metrics from annual
report PDFs using a layered strategy:
1) PyMuPDF text extraction
2) Camelot table extraction
3) Regex and table scanning fallbacks
"""

from __future__ import annotations


def extract_financials_from_pdf(file_path: str, sector: str = "NBFC") -> dict:
    """
    3-layer extraction: PyMuPDF text -> Camelot tables -> regex/table fallback.
    Returns a flat dict of financial fields with metadata.
    """
    import re

    result = {}
    full_text = ""
    all_tables = []

    # -- LAYER 1: PyMuPDF text extraction -------------------------------------
    try:
        fitz = __import__("fitz")  # PyMuPDF
        doc = fitz.open(file_path)
        pages_text = []
        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text("text")
            pages_text.append(text)
        full_text = "\n".join(pages_text)
        doc.close()
        print(f"[PDF_PARSER] Extracted {len(full_text)} chars from {len(pages_text)} pages")
    except Exception as e:
        print(f"[PDF_PARSER] PyMuPDF failed: {e}")
        full_text = ""

    # -- LAYER 2: Camelot table extraction ------------------------------------
    try:
        camelot = __import__("camelot")

        for flavor in ["lattice", "stream"]:
            try:
                tables = camelot.read_pdf(
                    file_path,
                    pages="1-end",
                    flavor=flavor,
                    suppress_stdout=True,
                )
                for table in tables:
                    df = table.df
                    if getattr(df, "shape", (0, 0))[0] > 1 and getattr(df, "shape", (0, 0))[1] > 1:
                        all_tables.append(df)
                if all_tables:
                    print(f"[PDF_PARSER] Camelot ({flavor}) extracted {len(all_tables)} tables")
                    break
            except Exception as e:
                print(f"[PDF_PARSER] Camelot {flavor} failed: {e}")
                continue
    except ImportError:
        print("[PDF_PARSER] Camelot not installed - skipping table extraction")

    # -- LAYER 3: Regex extraction from text ----------------------------------
    def extract_number(text, patterns):
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE | re.MULTILINE)
            for m in matches:
                raw = m if isinstance(m, str) else m[0] if m else ""
                cleaned = re.sub(r"[RsINR₹,\s]", "", str(raw))
                cleaned = cleaned.replace("Cr", "").replace("crore", "")
                try:
                    val = float(cleaned)
                    if val > 0:
                        return val
                except Exception:
                    continue
        return None

    def extract_pct(text, patterns):
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE | re.MULTILINE)
            for m in matches:
                raw = m if isinstance(m, str) else m[0] if m else ""
                cleaned = str(raw).replace("%", "").replace(",", "").strip()
                try:
                    val = float(cleaned)
                    if 0 < val < 100:
                        return val
                except Exception:
                    continue
        return None

    num = r"[\s:₹]+([\d,]+\.?\d*)"
    pct = r"[\s:]+([\d.]+)\s*%?"

    result["revenue"] = extract_number(full_text, [
        r"Revenue from [Oo]perations" + num,
        r"Total [Ii]ncome" + num,
        r"Net [Rr]evenue" + num,
        r"[Ii]ncome from [Oo]perations" + num,
        r"[Tt]urnover" + num,
    ])

    result["nim_absolute"] = extract_number(full_text, [
        r"Net [Ii]nterest [Ii]ncome" + num,
        r"\bNII\b" + num,
        r"Interest [Ii]ncome.{0,50}Interest [Ee]xpense" + num,
    ])

    result["ebitda"] = extract_number(full_text, [
        r"[Ee]arnings [Bb]efore [Ii]nterest.{0,30}Tax.{0,30}Depreciation" + num,
        r"\bEBITDA\b" + num,
        r"[Oo]perating [Pp]rofit" + num,
        r"Profit [Bb]efore [Tt]ax.{0,30}[Dd]epreciation" + num,
    ])

    result["pat"] = extract_number(full_text, [
        r"Profit [Aa]fter [Tt]ax" + num,
        r"\bPAT\b" + num,
        r"[Nn]et [Pp]rofit.{0,20}after tax" + num,
        r"[Pp]rofit for the [Yy]ear" + num,
    ])

    result["total_assets"] = extract_number(full_text, [
        r"[Tt]otal [Aa]ssets" + num,
        r"[Bb]alance [Ss]heet [Ss]ize" + num,
    ])

    result["net_worth"] = extract_number(full_text, [
        r"[Nn]et [Ww]orth" + num,
        r"[Ss]hareholders.{0,10}[Ee]quity" + num,
        r"[Tt]otal [Ee]quity" + num,
        r"[Ee]quity [Ss]hare [Cc]apital.{0,200}[Rr]eserves" + num,
    ])

    result["total_debt"] = extract_number(full_text, [
        r"[Tt]otal [Bb]orrowings" + num,
        r"[Bb]orrowed [Ff]unds" + num,
        r"[Tt]otal [Dd]ebt" + num,
        r"[Dd]ebt [Ff]unds" + num,
    ])

    result["aum"] = extract_number(full_text, [
        r"Assets [Uu]nder [Mm]anagement" + num,
        r"\bAUM\b" + num,
        r"[Ll]oan [Bb]ook" + num,
        r"[Pp]ortfolio [Ss]ize" + num,
        r"[Tt]otal [Ll]oan [Pp]ortfolio" + num,
    ])

    result["car"] = extract_pct(full_text, [
        r"[Cc]apital [Aa]dequacy [Rr]atio.{0,30}" + pct,
        r"\bCAR\b.{0,20}" + pct,
        r"\bCRAR\b.{0,20}" + pct,
        r"[Cc]apital to [Rr]isk.{0,30}" + pct,
    ])

    result["gnpa_ratio"] = extract_pct(full_text, [
        r"[Gg]ross NPA.{0,20}" + pct,
        r"\bGNPA\b.{0,20}" + pct,
        r"[Gg]ross [Nn]on.?[Pp]erforming.{0,20}" + pct,
    ])

    result["nnpa_ratio"] = extract_pct(full_text, [
        r"[Nn]et NPA.{0,20}" + pct,
        r"\bNNPA\b.{0,20}" + pct,
        r"[Nn]et [Nn]on.?[Pp]erforming.{0,20}" + pct,
    ])

    result["nim"] = extract_pct(full_text, [
        r"[Nn]et [Ii]nterest [Mm]argin.{0,20}" + pct,
        r"\bNIM\b.{0,20}" + pct,
    ])

    result["roa"] = extract_pct(full_text, [
        r"[Rr]eturn on [Aa]ssets.{0,20}" + pct,
        r"\bROA\b.{0,20}" + pct,
        r"[Rr]eturn on [Aa]verage [Aa]ssets.{0,20}" + pct,
    ])

    result["roe"] = extract_pct(full_text, [
        r"[Rr]eturn on [Ee]quity.{0,20}" + pct,
        r"\bROE\b.{0,20}" + pct,
        r"[Rr]eturn on [Nn]et [Ww]orth.{0,20}" + pct,
    ])

    result["cost_to_income"] = extract_pct(full_text, [
        r"[Cc]ost.?to.?[Ii]ncome.{0,20}" + pct,
        r"[Oo]pex [Rr]atio.{0,20}" + pct,
        r"[Oo]perating [Cc]ost [Rr]atio.{0,20}" + pct,
    ])

    result["pcr"] = extract_pct(full_text, [
        r"[Pp]rovision [Cc]overage.{0,20}" + pct,
        r"\bPCR\b.{0,20}" + pct,
    ])

    result["dscr"] = extract_number(full_text, [
        r"[Dd]ebt [Ss]ervice [Cc]overage.{0,20}" + num,
        r"\bDSCR\b.{0,20}" + num,
    ])

    result["debt_to_equity"] = extract_number(full_text, [
        r"[Dd]ebt.?[Tt]o.?[Ee]quity.{0,20}" + num,
        r"[Gg]earing [Rr]atio.{0,20}" + num,
        r"[Ll]everage [Rr]atio.{0,20}" + num,
    ])

    # -- Table fallback for PAT ------------------------------------------------
    if all_tables and not result.get("pat"):
        for df in all_tables:
            df_str = df.to_string().lower()
            if "profit after tax" in df_str or " pat " in f" {df_str} ":
                for _, row in df.iterrows():
                    row_values = [str(v) for v in row.values]
                    row_str = " ".join(row_values).lower()
                    if "profit after tax" in row_str or " pat " in f" {row_str} ":
                        for val in row_values:
                            cleaned = re.sub(r"[₹,\s]", "", str(val))
                            try:
                                num_val = float(cleaned)
                                if num_val > 0:
                                    result["pat"] = num_val
                                    break
                            except Exception:
                                continue

    # -- Derived metrics -------------------------------------------------------
    if result.get("pat") and result.get("revenue"):
        result["pat_margin"] = round(result["pat"] / result["revenue"] * 100, 2)

    if result.get("ebitda") and result.get("revenue"):
        result["ebitda_margin"] = round(result["ebitda"] / result["revenue"] * 100, 2)

    if result.get("total_debt") and result.get("net_worth"):
        result["debt_to_equity"] = result.get("debt_to_equity") or round(
            result["total_debt"] / result["net_worth"], 2
        )

    if result.get("aum") and result.get("total_assets"):
        result["aum_to_assets"] = round(result["aum"] / result["total_assets"] * 100, 2)

    if not result.get("dscr") and result.get("pat") and result.get("nim_absolute"):
        interest_expense_est = result.get("nim_absolute", 0) * 0.6
        if interest_expense_est > 0:
            result["dscr"] = round((result["pat"] + interest_expense_est) / interest_expense_est, 2)

    # -- Metadata --------------------------------------------------------------
    extracted_values = [
        v for k, v in result.items()
        if not str(k).startswith("_") and v is not None
    ]
    result["_extraction_source"] = "pdf_parser_v2"
    result["_fields_extracted"] = len(extracted_values)
    result["_raw_text_length"] = len(full_text)
    result["_tables_found"] = len(all_tables)

    print(
        f"[PDF_PARSER] Extracted {result['_fields_extracted']} fields. "
        f"Text: {result['_raw_text_length']} chars, Tables: {result['_tables_found']}"
    )

    return {k: v for k, v in result.items() if v is not None}
