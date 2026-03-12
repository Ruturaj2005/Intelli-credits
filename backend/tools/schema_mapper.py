"""
Schema Mapper - Configurable Output Schema for Document Extraction
Enables users to define/configure extraction schemas for structured data ingestion.
"""
from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
import re
from difflib import SequenceMatcher
import google.generativeai as genai


class FieldDataType(str, Enum):
    """Data types for schema fields"""
    STRING = "STRING"
    NUMBER = "NUMBER"
    DATE = "DATE"
    PERCENTAGE = "PERCENTAGE"
    CURRENCY = "CURRENCY"
    BOOLEAN = "BOOLEAN"
    ARRAY = "ARRAY"


class SchemaField(BaseModel):
    """Individual field definition in a schema template"""
    field_name: str
    field_label: str
    data_type: FieldDataType
    required: bool = False
    description: str
    extraction_hints: List[str]
    validation_rules: Optional[Dict[str, Any]] = None


class SchemaTemplate(BaseModel):
    """Complete schema template for a document type"""
    template_id: str
    template_name: str
    description: str
    applicable_document_types: List[str]
    fields: List[SchemaField]
    version: str = "1.0"


# ============================================================================
# PRE-BUILT SCHEMA TEMPLATES
# ============================================================================

FINANCIAL_ANALYSIS_SCHEMA = SchemaTemplate(
    template_id="SCH_FINANCIAL_001",
    template_name="Financial Analysis Schema",
    description="Extract key financial metrics from annual reports, financial statements, and ITR",
    applicable_document_types=["ANNUAL_REPORT", "FINANCIAL_STATEMENT", "ITR"],
    fields=[
        SchemaField(
            field_name="revenue",
            field_label="Total Revenue",
            data_type=FieldDataType.CURRENCY,
            required=True,
            description="Total revenue from operations for the fiscal year",
            extraction_hints=["revenue from operations", "total income", "turnover", "sales", "gross revenue"],
            validation_rules={"min": 0, "max": 999999999999}
        ),
        SchemaField(
            field_name="ebitda",
            field_label="EBITDA",
            data_type=FieldDataType.CURRENCY,
            required=True,
            description="Earnings before interest, tax, depreciation and amortization",
            extraction_hints=["ebitda", "operating profit", "profit before interest"],
            validation_rules={"min": -999999999999, "max": 999999999999}
        ),
        SchemaField(
            field_name="pat",
            field_label="Profit After Tax",
            data_type=FieldDataType.CURRENCY,
            required=True,
            description="Net profit after all expenses and taxes",
            extraction_hints=["profit after tax", "net profit", "pat", "profit for the year"],
            validation_rules={"min": -999999999999, "max": 999999999999}
        ),
        SchemaField(
            field_name="total_debt",
            field_label="Total Debt",
            data_type=FieldDataType.CURRENCY,
            required=True,
            description="Sum of short-term and long-term borrowings",
            extraction_hints=["total debt", "borrowings", "total liabilities", "long term borrowings", "short term borrowings"],
            validation_rules={"min": 0, "max": 999999999999}
        ),
        SchemaField(
            field_name="net_worth",
            field_label="Net Worth",
            data_type=FieldDataType.CURRENCY,
            required=True,
            description="Total shareholders' equity",
            extraction_hints=["net worth", "shareholders equity", "equity capital", "total equity"],
            validation_rules={"min": -999999999999, "max": 999999999999}
        ),
        SchemaField(
            field_name="current_assets",
            field_label="Current Assets",
            data_type=FieldDataType.CURRENCY,
            required=False,
            description="Assets expected to be converted to cash within one year",
            extraction_hints=["current assets", "short term assets", "liquid assets"],
            validation_rules={"min": 0, "max": 999999999999}
        ),
        SchemaField(
            field_name="current_liabilities",
            field_label="Current Liabilities",
            data_type=FieldDataType.CURRENCY,
            required=False,
            description="Liabilities due within one year",
            extraction_hints=["current liabilities", "short term liabilities"],
            validation_rules={"min": 0, "max": 999999999999}
        ),
        SchemaField(
            field_name="interest_expense",
            field_label="Interest Expense",
            data_type=FieldDataType.CURRENCY,
            required=False,
            description="Total interest paid on borrowings",
            extraction_hints=["interest expense", "finance cost", "interest paid"],
            validation_rules={"min": 0, "max": 999999999999}
        ),
        SchemaField(
            field_name="depreciation",
            field_label="Depreciation",
            data_type=FieldDataType.CURRENCY,
            required=False,
            description="Depreciation and amortization expense",
            extraction_hints=["depreciation", "depreciation and amortization", "d&a"],
            validation_rules={"min": 0, "max": 999999999999}
        ),
        SchemaField(
            field_name="cash_from_operations",
            field_label="Cash from Operations",
            data_type=FieldDataType.CURRENCY,
            required=False,
            description="Net cash generated from operating activities",
            extraction_hints=["cash from operations", "operating cash flow", "cash from operating activities"],
            validation_rules={"min": -999999999999, "max": 999999999999}
        ),
        SchemaField(
            field_name="revenue_fy_prev1",
            field_label="Revenue (Previous FY-1)",
            data_type=FieldDataType.CURRENCY,
            required=False,
            description="Revenue from previous fiscal year 1",
            extraction_hints=["previous year revenue", "fy-1 revenue", "prior year turnover"],
            validation_rules={"min": 0, "max": 999999999999}
        ),
        SchemaField(
            field_name="revenue_fy_prev2",
            field_label="Revenue (Previous FY-2)",
            data_type=FieldDataType.CURRENCY,
            required=False,
            description="Revenue from previous fiscal year 2",
            extraction_hints=["two years ago revenue", "fy-2 revenue"],
            validation_rules={"min": 0, "max": 999999999999}
        ),
    ]
)

BORROWING_ANALYSIS_SCHEMA = SchemaTemplate(
    template_id="SCH_BORROWING_001",
    template_name="Borrowing Analysis Schema",
    description="Extract borrowing details from borrowing profile, bank statements, and CIBIL reports",
    applicable_document_types=["BORROWING_PROFILE", "BANK_STATEMENT", "CIBIL_REPORT"],
    fields=[
        SchemaField(
            field_name="lender_name",
            field_label="Lender Name",
            data_type=FieldDataType.STRING,
            required=True,
            description="Name of the lending institution",
            extraction_hints=["lender", "bank name", "financial institution", "nbfc"],
            validation_rules={}
        ),
        SchemaField(
            field_name="facility_type",
            field_label="Facility Type",
            data_type=FieldDataType.STRING,
            required=True,
            description="Type of credit facility (e.g., term loan, working capital, overdraft)",
            extraction_hints=["facility type", "loan type", "credit type", "facility"],
            validation_rules={}
        ),
        SchemaField(
            field_name="sanction_amount",
            field_label="Sanction Amount",
            data_type=FieldDataType.CURRENCY,
            required=True,
            description="Original sanctioned loan amount",
            extraction_hints=["sanction amount", "sanctioned limit", "credit limit", "approved amount"],
            validation_rules={"min": 0, "max": 999999999999}
        ),
        SchemaField(
            field_name="outstanding_amount",
            field_label="Outstanding Amount",
            data_type=FieldDataType.CURRENCY,
            required=True,
            description="Current outstanding principal balance",
            extraction_hints=["outstanding", "outstanding balance", "current balance", "principal outstanding"],
            validation_rules={"min": 0, "max": 999999999999}
        ),
        SchemaField(
            field_name="interest_rate",
            field_label="Interest Rate",
            data_type=FieldDataType.PERCENTAGE,
            required=False,
            description="Annual interest rate on the facility",
            extraction_hints=["interest rate", "rate of interest", "roi", "cost of funds"],
            validation_rules={"min": 0, "max": 100}
        ),
        SchemaField(
            field_name="repayment_schedule",
            field_label="Repayment Schedule",
            data_type=FieldDataType.STRING,
            required=False,
            description="Repayment frequency and terms",
            extraction_hints=["repayment schedule", "installment frequency", "emi", "tenor"],
            validation_rules={}
        ),
        SchemaField(
            field_name="security_offered",
            field_label="Security Offered",
            data_type=FieldDataType.STRING,
            required=False,
            description="Collateral or security pledged",
            extraction_hints=["security", "collateral", "charge", "mortgage", "hypothecation"],
            validation_rules={}
        ),
        SchemaField(
            field_name="overdue_status",
            field_label="Overdue Status",
            data_type=FieldDataType.STRING,
            required=False,
            description="Current overdue status or DPD",
            extraction_hints=["overdue", "dpd", "delinquency", "past due", "default"],
            validation_rules={}
        ),
    ]
)

OWNERSHIP_ANALYSIS_SCHEMA = SchemaTemplate(
    template_id="SCH_OWNERSHIP_001",
    template_name="Ownership Analysis Schema",
    description="Extract shareholding and ownership details from shareholding patterns and MCA filings",
    applicable_document_types=["SHAREHOLDING_PATTERN", "MCA_FILING"],
    fields=[
        SchemaField(
            field_name="shareholder_category",
            field_label="Shareholder Category",
            data_type=FieldDataType.STRING,
            required=True,
            description="Category of shareholder (Promoter, Public, Institutional)",
            extraction_hints=["shareholder category", "category of shareholder", "promoter", "public", "institutional"],
            validation_rules={}
        ),
        SchemaField(
            field_name="number_of_shares",
            field_label="Number of Shares",
            data_type=FieldDataType.NUMBER,
            required=True,
            description="Total number of shares held",
            extraction_hints=["number of shares", "shares held", "shareholding", "total shares"],
            validation_rules={"min": 0}
        ),
        SchemaField(
            field_name="percentage_holding",
            field_label="Percentage Holding",
            data_type=FieldDataType.PERCENTAGE,
            required=True,
            description="Percentage of total shares held",
            extraction_hints=["percentage", "% holding", "share %", "percentage of shareholding"],
            validation_rules={"min": 0, "max": 100}
        ),
        SchemaField(
            field_name="pledged_shares",
            field_label="Pledged Shares",
            data_type=FieldDataType.NUMBER,
            required=False,
            description="Number of shares pledged as collateral",
            extraction_hints=["pledged", "pledged shares", "encumbered shares"],
            validation_rules={"min": 0}
        ),
        SchemaField(
            field_name="demat_shares",
            field_label="Demat Shares",
            data_type=FieldDataType.NUMBER,
            required=False,
            description="Shares held in dematerialized form",
            extraction_hints=["demat", "dematerialized", "demat shares"],
            validation_rules={"min": 0}
        ),
        SchemaField(
            field_name="promoter_group_names",
            field_label="Promoter Group Names",
            data_type=FieldDataType.ARRAY,
            required=False,
            description="Names of individuals/entities in promoter group",
            extraction_hints=["promoter name", "promoter group", "directors", "key managerial personnel"],
            validation_rules={}
        ),
    ]
)

PORTFOLIO_RISK_SCHEMA = SchemaTemplate(
    template_id="SCH_PORTFOLIO_001",
    template_name="Portfolio Risk Schema",
    description="Extract portfolio quality and risk metrics from portfolio performance reports",
    applicable_document_types=["PORTFOLIO_PERFORMANCE", "ANNUAL_REPORT"],
    fields=[
        SchemaField(
            field_name="gross_npa",
            field_label="Gross NPA",
            data_type=FieldDataType.CURRENCY,
            required=True,
            description="Gross non-performing assets",
            extraction_hints=["gross npa", "gross non-performing assets", "gnpa"],
            validation_rules={"min": 0}
        ),
        SchemaField(
            field_name="net_npa",
            field_label="Net NPA",
            data_type=FieldDataType.CURRENCY,
            required=True,
            description="Net non-performing assets after provisions",
            extraction_hints=["net npa", "net non-performing assets", "nnpa"],
            validation_rules={"min": 0}
        ),
        SchemaField(
            field_name="gnpa_ratio",
            field_label="GNPA Ratio",
            data_type=FieldDataType.PERCENTAGE,
            required=True,
            description="Gross NPA as percentage of total advances",
            extraction_hints=["gnpa ratio", "gross npa ratio", "npa percentage"],
            validation_rules={"min": 0, "max": 100}
        ),
        SchemaField(
            field_name="provision_coverage_ratio",
            field_label="Provision Coverage Ratio",
            data_type=FieldDataType.PERCENTAGE,
            required=False,
            description="Provisions made against NPAs as percentage of total NPAs",
            extraction_hints=["provision coverage", "pcr", "provision ratio"],
            validation_rules={"min": 0, "max": 100}
        ),
        SchemaField(
            field_name="total_advances",
            field_label="Total Advances",
            data_type=FieldDataType.CURRENCY,
            required=True,
            description="Total loan portfolio outstanding",
            extraction_hints=["total advances", "total loans", "loan portfolio", "credit portfolio"],
            validation_rules={"min": 0}
        ),
        SchemaField(
            field_name="sector_concentration",
            field_label="Sector Concentration",
            data_type=FieldDataType.STRING,
            required=False,
            description="Top sector exposure details",
            extraction_hints=["sector concentration", "industry exposure", "sectoral distribution"],
            validation_rules={}
        ),
        SchemaField(
            field_name="vintage_30_dpd",
            field_label="30+ DPD Vintage",
            data_type=FieldDataType.PERCENTAGE,
            required=False,
            description="Percentage of portfolio 30+ days past due",
            extraction_hints=["30 dpd", "30+ dpd", "30 days past due"],
            validation_rules={"min": 0, "max": 100}
        ),
        SchemaField(
            field_name="vintage_90_dpd",
            field_label="90+ DPD Vintage",
            data_type=FieldDataType.PERCENTAGE,
            required=False,
            description="Percentage of portfolio 90+ days past due",
            extraction_hints=["90 dpd", "90+ dpd", "90 days past due"],
            validation_rules={"min": 0, "max": 100}
        ),
    ]
)

ALM_SCHEMA = SchemaTemplate(
    template_id="SCH_ALM_001",
    template_name="Asset Liability Management Schema",
    description="Extract ALM metrics including liquidity gaps and duration analysis",
    applicable_document_types=["ALM"],
    fields=[
        SchemaField(
            field_name="bucket_0_30days_assets",
            field_label="Assets (0-30 Days)",
            data_type=FieldDataType.CURRENCY,
            required=True,
            description="Assets maturing in 0-30 days bucket",
            extraction_hints=["0-30 days assets", "0-1 month assets", "assets upto 30 days"],
            validation_rules={"min": 0}
        ),
        SchemaField(
            field_name="bucket_0_30days_liabilities",
            field_label="Liabilities (0-30 Days)",
            data_type=FieldDataType.CURRENCY,
            required=True,
            description="Liabilities maturing in 0-30 days bucket",
            extraction_hints=["0-30 days liabilities", "0-1 month liabilities", "liabilities upto 30 days"],
            validation_rules={"min": 0}
        ),
        SchemaField(
            field_name="liquidity_gap_1m",
            field_label="Liquidity Gap (1 Month)",
            data_type=FieldDataType.CURRENCY,
            required=True,
            description="Liquidity gap for 1 month maturity bucket",
            extraction_hints=["liquidity gap", "1 month gap", "1m gap", "maturity gap"],
            validation_rules={"min": -999999999999, "max": 999999999999}
        ),
        SchemaField(
            field_name="liquidity_gap_3m",
            field_label="Liquidity Gap (3 Months)",
            data_type=FieldDataType.CURRENCY,
            required=False,
            description="Liquidity gap for 3 month maturity bucket",
            extraction_hints=["liquidity gap 3m", "3 month gap", "quarterly gap"],
            validation_rules={"min": -999999999999, "max": 999999999999}
        ),
        SchemaField(
            field_name="rate_sensitive_assets",
            field_label="Rate Sensitive Assets",
            data_type=FieldDataType.CURRENCY,
            required=False,
            description="Assets sensitive to interest rate changes",
            extraction_hints=["rate sensitive assets", "rsa", "interest rate sensitive assets"],
            validation_rules={"min": 0}
        ),
        SchemaField(
            field_name="rate_sensitive_liabilities",
            field_label="Rate Sensitive Liabilities",
            data_type=FieldDataType.CURRENCY,
            required=False,
            description="Liabilities sensitive to interest rate changes",
            extraction_hints=["rate sensitive liabilities", "rsl", "interest rate sensitive liabilities"],
            validation_rules={"min": 0}
        ),
        SchemaField(
            field_name="duration_gap",
            field_label="Duration Gap",
            data_type=FieldDataType.NUMBER,
            required=False,
            description="Difference between asset and liability duration",
            extraction_hints=["duration gap", "duration mismatch"],
            validation_rules={"min": -100, "max": 100}
        ),
        SchemaField(
            field_name="nii_sensitivity",
            field_label="NII Sensitivity",
            data_type=FieldDataType.PERCENTAGE,
            required=False,
            description="Net interest income sensitivity to rate changes",
            extraction_hints=["nii sensitivity", "net interest income sensitivity", "earnings at risk"],
            validation_rules={"min": -100, "max": 100}
        ),
    ]
)

# Schema Registry
SCHEMA_REGISTRY: Dict[str, SchemaTemplate] = {
    "SCH_FINANCIAL_001": FINANCIAL_ANALYSIS_SCHEMA,
    "SCH_BORROWING_001": BORROWING_ANALYSIS_SCHEMA,
    "SCH_OWNERSHIP_001": OWNERSHIP_ANALYSIS_SCHEMA,
    "SCH_PORTFOLIO_001": PORTFOLIO_RISK_SCHEMA,
    "SCH_ALM_001": ALM_SCHEMA,
}


# ============================================================================
# SCHEMA MAPPER CLASS
# ============================================================================

class SchemaMapper:
    """
    Schema mapping and extraction engine.
    Provides methods to recommend schemas and extract structured data.
    """

    @staticmethod
    def get_recommended_schema(document_type: str) -> List[SchemaTemplate]:
        """
        Get recommended schema templates for a document type.
        Returns templates in priority order.
        """
        recommendations = []
        
        for template in SCHEMA_REGISTRY.values():
            if document_type in template.applicable_document_types:
                recommendations.append(template)
        
        # If no exact match, return all schemas (user can choose)
        if not recommendations:
            recommendations = list(SCHEMA_REGISTRY.values())
        
        return recommendations

    @staticmethod
    def extract_with_schema(
        document: dict,
        schema: SchemaTemplate,
        gemini_model=None,
        custom_hints: Optional[Dict[str, List[str]]] = None
    ) -> dict:
        """
        Extract structured data from document using specified schema.
        
        Args:
            document: Parsed document with 'text', 'tables', 'metadata'
            schema: SchemaTemplate to apply
            gemini_model: Optional Gemini model for AI extraction fallback
            custom_hints: Optional custom extraction hints per field
        
        Returns:
            {
                "schema_id": str,
                "schema_name": str,
                "extraction_timestamp": str,
                "completion_percentage": float,
                "fields": {
                    "field_name": {
                        "value": Any,
                        "status": "EXTRACTED" | "MISSING" | "VALIDATION_FAILED",
                        "confidence": float,
                        "extraction_method": str,
                        "field_label": str
                    }
                },
                "missing_required_fields": List[str]
            }
        """
        from datetime import datetime
        
        extracted_data = {}
        text = document.get("text", "")
        tables = document.get("tables", [])
        
        for field in schema.fields:
            # Use custom hints if provided, otherwise use default
            hints = custom_hints.get(field.field_name, field.extraction_hints) if custom_hints else field.extraction_hints
            
            # Try extraction methods in order of confidence
            result = SchemaMapper._extract_field(
                field, hints, text, tables, gemini_model
            )
            
            # Validate extracted value
            if result["value"] is not None:
                validated = SchemaMapper._validate_field(result["value"], field.validation_rules or {})
                if validated is not None:
                    result["value"] = validated
                    result["status"] = "EXTRACTED"
                else:
                    result["status"] = "VALIDATION_FAILED"
            else:
                result["status"] = "MISSING"
            
            result["field_label"] = field.field_label
            extracted_data[field.field_name] = result
        
        # Calculate metrics
        completion = SchemaMapper._calculate_completion(extracted_data, schema)
        missing_required = SchemaMapper._get_missing_required(extracted_data, schema)
        
        return {
            "schema_id": schema.template_id,
            "schema_name": schema.template_name,
            "extraction_timestamp": datetime.now().isoformat(),
            "completion_percentage": completion,
            "fields": extracted_data,
            "missing_required_fields": missing_required
        }

    @staticmethod
    def _extract_field(
        field: SchemaField,
        hints: List[str],
        text: str,
        tables: List[dict],
        gemini_model=None
    ) -> dict:
        """
        Extract a single field using multiple methods.
        Returns best result with confidence score.
        """
        results = []
        
        # Method 1: Exact match in tables (confidence 0.9)
        table_exact = SchemaMapper._extract_from_tables_exact(hints, tables)
        if table_exact:
            results.append({
                "value": table_exact,
                "confidence": 0.9,
                "extraction_method": "table_exact_match"
            })
        
        # Method 2: Fuzzy match in tables (confidence 0.7)
        table_fuzzy = SchemaMapper._extract_from_tables_fuzzy(hints, tables)
        if table_fuzzy:
            results.append({
                "value": table_fuzzy,
                "confidence": 0.7,
                "extraction_method": "table_fuzzy_match"
            })
        
        # Method 3: Regex from text (confidence 0.6)
        text_regex = SchemaMapper._extract_from_text_regex(hints, text, field.data_type)
        if text_regex:
            results.append({
                "value": text_regex,
                "confidence": 0.6,
                "extraction_method": "text_regex"
            })
        
        # Method 4: Gemini AI extraction (confidence 0.5)
        if gemini_model:
            ai_extract = SchemaMapper._extract_with_gemini(field, hints, text, gemini_model)
            if ai_extract:
                results.append({
                    "value": ai_extract,
                    "confidence": 0.5,
                    "extraction_method": "ai_extraction"
                })
        
        # Return best result (highest confidence)
        if results:
            best = max(results, key=lambda x: x["confidence"])
            return best
        
        return {
            "value": None,
            "confidence": 0.0,
            "extraction_method": "not_found"
        }

    @staticmethod
    def _extract_from_tables_exact(hints: List[str], tables: List[dict]) -> Optional[Any]:
        """Extract value from tables using exact string matching"""
        for table in tables:
            headers = table.get("headers", [])
            rows = table.get("rows", [])
            
            # Check if any hint matches a header exactly (case-insensitive)
            for hint in hints:
                for col_idx, header in enumerate(headers):
                    if hint.lower() in header.lower():
                        # Return first non-empty value in this column
                        for row in rows:
                            if col_idx < len(row) and row[col_idx]:
                                return row[col_idx]
        return None

    @staticmethod
    def _extract_from_tables_fuzzy(hints: List[str], tables: List[dict]) -> Optional[Any]:
        """Extract value from tables using fuzzy string matching"""
        for table in tables:
            headers = table.get("headers", [])
            rows = table.get("rows", [])
            
            for hint in hints:
                for col_idx, header in enumerate(headers):
                    # Use SequenceMatcher for fuzzy matching
                    similarity = SequenceMatcher(None, hint.lower(), header.lower()).ratio()
                    if similarity > 0.6:  # 60% similarity threshold
                        for row in rows:
                            if col_idx < len(row) and row[col_idx]:
                                return row[col_idx]
        return None

    @staticmethod
    def _extract_from_text_regex(hints: List[str], text: str, data_type: FieldDataType) -> Optional[Any]:
        """Extract value from text using regex patterns"""
        for hint in hints:
            # Build regex pattern based on hint
            # Look for pattern: "hint: value" or "hint value"
            pattern = rf"{re.escape(hint)}\s*[:=]?\s*([^\n]+)"
            match = re.search(pattern, text, re.IGNORECASE)
            
            if match:
                value_str = match.group(1).strip()
                
                # Parse based on data type
                if data_type in [FieldDataType.CURRENCY, FieldDataType.NUMBER]:
                    # Extract numeric value (handle commas, lakhs, crores)
                    numeric_match = re.search(r'[\d,]+\.?\d*', value_str)
                    if numeric_match:
                        return numeric_match.group(0).replace(',', '')
                elif data_type == FieldDataType.PERCENTAGE:
                    percent_match = re.search(r'([\d.]+)\s*%?', value_str)
                    if percent_match:
                        return float(percent_match.group(1))
                else:
                    return value_str
        
        return None

    @staticmethod
    def _extract_with_gemini(
        field: SchemaField,
        hints: List[str],
        text: str,
        model
    ) -> Optional[Any]:
        """Use Gemini AI to extract field value"""
        try:
            prompt = f"""
Extract the following field from the document text:

Field: {field.field_label}
Description: {field.description}
Data Type: {field.data_type}
Keywords to look for: {', '.join(hints)}

Document Text (excerpt):
{text[:3000]}

Return ONLY the extracted value, nothing else. If not found, return "NOT_FOUND".
"""
            response = model.generate_content(prompt)
            value = response.text.strip()
            
            if value and value != "NOT_FOUND":
                return value
        except Exception as e:
            print(f"Gemini extraction error: {e}")
        
        return None

    @staticmethod
    def _validate_field(value: Any, rules: Dict[str, Any]) -> Optional[Any]:
        """Validate field value against validation rules"""
        try:
            if not rules:
                return value
            
            # Convert to appropriate type
            if "min" in rules or "max" in rules:
                # Numeric validation
                try:
                    num_val = float(str(value).replace(',', ''))
                    if "min" in rules and num_val < rules["min"]:
                        return None
                    if "max" in rules and num_val > rules["max"]:
                        return None
                    return num_val
                except ValueError:
                    return None
            
            return value
        except Exception:
            return None

    @staticmethod
    def _calculate_completion(extracted_data: dict, schema: SchemaTemplate) -> float:
        """Calculate percentage of fields successfully extracted"""
        total_fields = len(schema.fields)
        extracted_fields = sum(
            1 for field_data in extracted_data.values()
            if field_data.get("status") == "EXTRACTED"
        )
        return (extracted_fields / total_fields * 100) if total_fields > 0 else 0.0

    @staticmethod
    def _get_missing_required(extracted_data: dict, schema: SchemaTemplate) -> List[str]:
        """Get list of required fields that are missing"""
        missing = []
        for field in schema.fields:
            if field.required:
                field_result = extracted_data.get(field.field_name, {})
                if field_result.get("status") != "EXTRACTED":
                    missing.append(field.field_label)
        return missing
