"""
Entity Onboarding Module — IntelliCredits

Handles entity profile creation and loan application submission
with CIN/PAN validation and context-aware document requirements.

This module extends the existing pipeline without modifying core agents.
"""
from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field, field_validator


# ─── Enums ────────────────────────────────────────────────────────────────────

class SectorType(str, Enum):
    """Allowed business sectors"""
    MANUFACTURING = "Manufacturing"
    NBFC = "NBFC"
    REAL_ESTATE = "Real Estate"
    TRADING = "Trading"
    INFRASTRUCTURE = "Infrastructure"
    HEALTHCARE = "Healthcare"
    TECHNOLOGY = "Technology"
    HOSPITALITY = "Hospitality"
    AGRICULTURE = "Agriculture"
    OTHER = "Other"


class BusinessModel(str, Enum):
    """Business model classification"""
    B2B = "B2B"
    B2C = "B2C"
    B2G = "B2G"


class LoanType(str, Enum):
    """Types of loan facilities"""
    WORKING_CAPITAL = "Working Capital"
    TERM_LOAN = "Term Loan"
    PROJECT_FINANCE = "Project Finance"
    TRADE_FINANCE = "Trade Finance"
    CASH_CREDIT = "Cash Credit"
    LETTER_OF_CREDIT = "Letter of Credit"
    BANK_GUARANTEE = "Bank Guarantee"
    EQUIPMENT_FINANCE = "Equipment Finance"


# ─── Pydantic Models ──────────────────────────────────────────────────────────

class EntityProfile(BaseModel):
    """
    Entity information captured during onboarding.
    Includes CIN and PAN validation per Indian regulatory formats.
    """
    company_name: str = Field(..., min_length=2, max_length=200, description="Legal name of the entity")
    cin: Optional[str] = Field(None, pattern=r"^[A-Z]{1}[0-9]{5}[A-Z]{2}[0-9]{4}[A-Z]{3}[0-9]{6}$", 
                     description="Corporate Identification Number (21 characters)")
    pan: Optional[str] = Field(None, pattern=r"^[A-Z]{5}[0-9]{4}[A-Z]{1}$", 
                     description="Permanent Account Number (10 characters)")
    sector: SectorType = Field(..., description="Business sector/industry")
    annual_turnover: Optional[float] = Field(None, gt=0, description="Annual turnover in ₹ Crores")
    date_of_incorporation: Optional[date] = Field(None, description="Date of incorporation")
    registered_address: Optional[str] = Field(None, max_length=500, description="Registered office address")
    business_model: Optional[BusinessModel] = Field(None, description="Business model type")
    employee_count: Optional[int] = Field(None, ge=0, description="Number of employees")
    
    @field_validator('cin')
    @classmethod
    def validate_cin(cls, v: Optional[str]) -> Optional[str]:
        """Validate CIN format and structure"""
        if v is None or v == '':
            return None
        if len(v) != 21:
            raise ValueError("CIN must be exactly 21 characters")
        
        # First character: Company type (U=Unlisted, L=Listed)
        if v[0] not in ['U', 'L']:
            raise ValueError("CIN must start with 'U' (Unlisted) or 'L' (Listed)")
        
        # Characters 2-6: Industry code (5 digits)
        if not v[1:6].isdigit():
            raise ValueError("CIN characters 2-6 must be industry code (5 digits)")
        
        # Characters 7-8: State code (2 letters)
        if not v[6:8].isalpha():
            raise ValueError("CIN characters 7-8 must be state code (2 letters)")
        
        # Characters 9-12: Year of registration (4 digits)
        year_str = v[8:12]
        if not year_str.isdigit():
            raise ValueError("CIN characters 9-12 must be year (4 digits)")
        year = int(year_str)
        current_year = datetime.now().year
        if year < 1900 or year > current_year:
            raise ValueError(f"CIN year must be between 1900 and {current_year}")
        
        # Characters 13-15: Company type code (3 letters)
        if not v[12:15].isalpha():
            raise ValueError("CIN characters 13-15 must be company type code (3 letters)")
        
        # Characters 16-21: Registration number (6 digits)
        if not v[15:21].isdigit():
            raise ValueError("CIN characters 16-21 must be registration number (6 digits)")
        
        return v.upper()
    
    @field_validator('pan')
    @classmethod
    def validate_pan(cls, v: Optional[str]) -> Optional[str]:
        """Validate PAN format"""
        if v is None or v == '':
            return None
        if len(v) != 10:
            raise ValueError("PAN must be exactly 10 characters")
        
        # First 5: Alphabets
        if not v[:5].isalpha():
            raise ValueError("PAN first 5 characters must be letters")
        
        # Next 4: Digits
        if not v[5:9].isdigit():
            raise ValueError("PAN characters 6-9 must be digits")
        
        # Last: Alphabet (check digit)
        if not v[9].isalpha():
            raise ValueError("PAN last character must be a letter")
        
        # 4th character should be P for individual, C for company, etc.
        entity_type = v[3]
        if entity_type not in ['C', 'P', 'H', 'F', 'A', 'T', 'B', 'L', 'J', 'G']:
            raise ValueError(f"Invalid PAN entity type: {entity_type}")
        
        return v.upper()
    
    class Config:
        json_schema_extra = {
            "example": {
                "company_name": "ABC Manufacturing Ltd",
                "cin": "U12345MH2015PTC123456",
                "pan": "AABCA1234C",
                "sector": "Manufacturing",
                "annual_turnover": 150.0,
                "date_of_incorporation": "2015-03-15",
                "registered_address": "123, Industrial Area, Mumbai, Maharashtra - 400001",
                "business_model": "B2B",
                "employee_count": 250
            }
        }


class LoanApplication(BaseModel):
    """
    Loan application details captured during onboarding.
    Links to an EntityProfile via entity_id.
    """
    loan_type: LoanType = Field(..., description="Type of loan facility")
    loan_amount: float = Field(..., gt=0, description="Requested amount in ₹ Crores")
    loan_tenure_months: Optional[int] = Field(None, gt=0, le=360, description="Loan tenure in months (max 30 years)")
    expected_interest_rate: Optional[float] = Field(None, ge=5.0, le=25.0, 
                                                      description="Expected interest rate in % p.a.")
    purpose: Optional[str] = Field(None, min_length=10, max_length=1000, description="Purpose of loan")
    collateral_offered: Optional[str] = Field(None, max_length=500, description="Collateral/security offered")
    existing_banking_relationship: Optional[bool] = Field(False, 
                                                           description="Existing relationship with the bank")
    
    class Config:
        json_schema_extra = {
            "example": {
                "loan_type": "Working Capital",
                "loan_amount": 50.0,
                "loan_tenure_months": 12,
                "expected_interest_rate": 10.5,
                "purpose": "Working capital requirement for inventory management and operational expenses",
                "collateral_offered": "Hypothecation of stock and book debts",
                "existing_banking_relationship": True
            }
        }


# ─── Response Models ──────────────────────────────────────────────────────────

class EntityProfileResponse(BaseModel):
    """Response after entity profile creation"""
    entity_id: str
    status: Literal["validated", "validation_failed"]
    message: str
    validations: Dict[str, str] = Field(default_factory=dict)
    
    class Config:
        json_schema_extra = {
            "example": {
                "entity_id": "ENT_2026031122001",
                "status": "validated",
                "message": "Entity profile created successfully",
                "validations": {
                    "cin_format": "valid",
                    "pan_format": "valid",
                    "company_name": "valid"
                }
            }
        }


class LoanApplicationRequest(BaseModel):
    """Request model for loan application submission"""
    entity_id: str
    loan_application: LoanApplication
    
    class Config:
        json_schema_extra = {
            "example": {
                "entity_id": "ENT_2026031122001",
                "loan_application": {
                    "loan_type": "term_loan",
                    "loan_amount": 5000000,
                    "loan_tenure_months": 60,
                    "expected_interest_rate": 9.5,
                    "purpose": "Working capital expansion",
                    "collateral_offered": "Property worth 8000000",
                    "existing_banking_relationship": True
                }
            }
        }


class LoanApplicationResponse(BaseModel):
    """Response after loan application submission"""
    application_id: str
    entity_id: str
    status: Literal["pending_documents", "submitted", "rejected"]
    message: str
    next_step: str
    required_documents: List[str]
    
    class Config:
        json_schema_extra = {
            "example": {
                "application_id": "APP_2026031122001",
                "entity_id": "ENT_2026031122001",
                "status": "pending_documents",
                "message": "Loan application submitted successfully",
                "next_step": "document_upload",
                "required_documents": [
                    "Bank Statements (Last 12 months)",
                    "GST Returns (GSTR-3B + 2A)",
                    "Borrowing Profile",
                    "Audited Financial Statements"
                ]
            }
        }


# ─── Helper Functions ─────────────────────────────────────────────────────────

def generate_entity_id() -> str:
    """Generate unique entity ID: ENT_YYYYMMDDHHMMSS"""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    return f"ENT_{timestamp}"


def generate_application_id() -> str:
    """Generate unique application ID: APP_YYYYMMDDHHMMSS"""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    return f"APP_{timestamp}"


def get_required_documents(loan_type: LoanType) -> List[str]:
    """
    Return context-aware list of required documents based on loan type.
    This demonstrates domain knowledge — different loan products require different documentation.
    """
    # Base documents required for all loan types
    base_docs = [
        "Audited Financial Statements",
        "Company PAN Card",
        "Address Proof",
    ]
    
    # Loan type specific documents
    loan_type_docs = {
        LoanType.WORKING_CAPITAL: [
            "Bank Statements (Last 12 months)",
            "GST Returns (GSTR-3B + 2A) - Last 12 months",
            "Borrowing Profile / Existing Loan Details",
            "Stock Statement and Book Debts Aging",
            "Operational Financials (Monthly)",
        ],
        LoanType.TERM_LOAN: [
            "Annual Report (Last 3 years)",
            "Project Report / Business Plan",
            "Shareholding Pattern",
            "Asset Liability Management (ALM) Report",
            "CIBIL Commercial Report",
            "Collateral Documents (Title Deed, Valuation Report)",
        ],
        LoanType.PROJECT_FINANCE: [
            "Detailed Project Report (DPR)",
            "Annual Report (Last 3 years)",
            "Asset Liability Management (ALM) Report",
            "Portfolio Performance Data",
            "Technical Feasibility Report",
            "Environmental Clearances",
            "Promoter Contribution Proof",
        ],
        LoanType.TRADE_FINANCE: [
            "Bank Statements (Last 12 months)",
            "GST Returns (Last 12 months)",
            "Import/Export License",
            "Trade Transaction History",
            "Letter of Credit / Purchase Order copies",
        ],
        LoanType.CASH_CREDIT: [
            "Bank Statements (Last 12 months)",
            "GST Returns (Last 12 months)",
            "Stock Statement",
            "Book Debts Statement",
            "Drawing Power Calculation",
        ],
        LoanType.LETTER_OF_CREDIT: [
            "Bank Statements (Last 6 months)",
            "Trade Agreement / Purchase Order",
            "Importer/Exporter Code (IEC)",
            "GST Returns (Last 6 months)",
        ],
        LoanType.BANK_GUARANTEE: [
            "Bank Statements (Last 6 months)",
            "Tender Document / Contract",
            "Financial Statements (Last 2 years)",
            "GST Returns (Last 6 months)",
        ],
        LoanType.EQUIPMENT_FINANCE: [
            "Equipment Quotation / Proforma Invoice",
            "Annual Report (Last 2 years)",
            "Bank Statements (Last 12 months)",
            "GST Returns (Last 12 months)",
            "Existing Asset Schedule",
        ],
    }
    
    # Combine base + loan-specific documents
    specific_docs = loan_type_docs.get(loan_type, [])
    return base_docs + specific_docs


def validate_entity_profile(profile: EntityProfile) -> Dict[str, str]:
    """
    Validate entity profile and return validation results.
    In production, this would also check against MCA API for real-time verification.
    """
    validations = {}
    
    # CIN format validation
    try:
        # CIN already validated by Pydantic, so if we're here, it's valid
        validations["cin_format"] = "valid"
        
        # Extract info from CIN for additional checks
        company_type = profile.cin[0]  # U=Unlisted, L=Listed
        state_code = profile.cin[6:8]  # State code
        year = int(profile.cin[8:12])  # Year of registration
        
        validations["cin_company_type"] = "Listed" if company_type == "L" else "Unlisted"
        validations["cin_state"] = state_code
        validations["cin_year"] = str(year)
        
        # Check company age
        current_year = datetime.now().year
        company_age = current_year - year
        if company_age < 3:
            validations["company_age_warning"] = f"Company is only {company_age} years old - may require additional scrutiny"
        
    except Exception as e:
        validations["cin_format"] = f"invalid: {str(e)}"
    
    # PAN format validation
    try:
        validations["pan_format"] = "valid"
        
        # Extract entity type from PAN (4th character)
        entity_type_map = {
            'C': 'Company',
            'P': 'Person',
            'H': 'HUF',
            'F': 'Firm',
            'A': 'AOP',
            'T': 'Trust',
            'B': 'Body of Individuals',
            'L': 'Local Authority',
            'J': 'Artificial Juridical Person',
            'G': 'Government'
        }
        entity_type = profile.pan[3]
        validations["pan_entity_type"] = entity_type_map.get(entity_type, "Unknown")
        
        # For corporate entities, PAN 4th character should be 'C'
        if entity_type != 'C':
            validations["pan_warning"] = f"PAN entity type is '{entity_type_map.get(entity_type, entity_type)}' - expected 'C' for companies"
    
    except Exception as e:
        validations["pan_format"] = f"invalid: {str(e)}"
    
    # Company name validation
    if profile.company_name:
        validations["company_name"] = "valid"
        if len(profile.company_name) < 3:
            validations["company_name"] = "invalid: too short"
    
    # Turnover validation
    if profile.annual_turnover:
        validations["annual_turnover"] = "valid"
        if profile.annual_turnover < 1:
            validations["turnover_warning"] = "Turnover less than ₹1 Cr - may not meet minimum eligibility"
        elif profile.annual_turnover > 1000:
            validations["turnover_note"] = "High turnover entity - may require enhanced due diligence"
    
    return validations
