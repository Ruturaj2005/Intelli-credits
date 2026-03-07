"""
RCU (Risk Containment Unit) Verification Agent

RCU is a critical pre-disbursement check performed by banks to verify:
1. Physical existence of business operations
2. Genuineness of business activity
3. Verification of assets/inventory
4. Meeting with promoters/key personnel
5. Local market checks
6. Cross-verification of documents

RCU helps prevent:
- Fraudulent loan applications
- Ghost companies
- Inflated asset valuations
- Misrepresentation of business scale
- Identity fraud

The RCU agent orchestrates multiple verification checks and consolidates findings.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import date, datetime
from enum import Enum


class VerificationStatus(Enum):
    """Status of individual verification check"""
    VERIFIED = "VERIFIED"              # Successfully verified
    PARTIAL = "PARTIAL"                # Partially verified with minor discrepancies
    DISCREPANCY = "DISCREPANCY"        # Significant discrepancies found
    NOT_VERIFIED = "NOT_VERIFIED"      # Could not verify
    FRAUD_SUSPECTED = "FRAUD_SUSPECTED"  # Potential fraud indicators


class RCUOverallStatus(Enum):
    """Overall RCU assessment"""
    POSITIVE = "POSITIVE"              # All checks clear, recommend proceed
    POSITIVE_WITH_OBSERVATIONS = "POSITIVE_WITH_OBSERVATIONS"  # Minor issues, can proceed with conditions
    NEGATIVE = "NEGATIVE"              # Significant issues, do not proceed
    FRAUD_ALERT = "FRAUD_ALERT"        # Fraud indicators, reject immediately


@dataclass
class AddressVerification:
    """Physical address and premises verification"""
    registered_address_verified: bool = False
    registered_address_status: str = VerificationStatus.NOT_VERIFIED.value
    registered_address_remarks: str = ""

    business_address_verified: bool = False
    business_address_status: str = VerificationStatus.NOT_VERIFIED.value
    business_address_remarks: str = ""

    factory_address_verified: bool = False
    factory_address_status: str = VerificationStatus.NOT_VERIFIED.value
    factory_address_remarks: str = ""

    premises_ownership: str = "UNKNOWN"  # OWNED/RENTED/LEASED
    premises_condition: str = "UNKNOWN"  # EXCELLENT/GOOD/AVERAGE/POOR
    premises_size_match: bool = True  # Matches declared size

    # Red flags
    address_is_virtual_office: bool = False
    address_is_residential: bool = False
    no_business_signage: bool = False


@dataclass
class BusinessOperationsVerification:
    """Verification of actual business operations"""
    business_activity_observed: bool = False
    business_activity_matches_application: bool = True
    business_activity_remarks: str = ""

    employees_present: int = 0
    employees_match_declared: bool = True

    machinery_equipment_present: bool = False
    machinery_condition: str = "UNKNOWN"  # OPERATIONAL/IDLE/POOR
    machinery_matches_declared: bool = True

    inventory_present: bool = False
    inventory_quantity: str = "UNKNOWN"  # SUBSTANTIAL/MODERATE/MINIMAL/NONE
    inventory_matches_declared: bool = True

    # Red flags
    no_business_activity: bool = False
    minimal_infrastructure: bool = False
    operations_appear_dormant: bool = False


@dataclass
class PromoterMeeting:
    """Meeting with promoters/directors"""
    promoter_met: bool = False
    promoter_name: str = ""
    meeting_date: Optional[date] = None
    meeting_mode: str = "UNKNOWN"  # IN_PERSON/VIDEO_CALL/PHONE

    identity_verified: bool = False
    identity_document: str = ""  # PAN/Aadhaar/Passport

    promoter_knowledge_score: int = 0  # 0-10, knowledge about business
    promoter_cooperation: str = "UNKNOWN"  # COOPERATIVE/EVASIVE/UNCOOPERATIVE

    # Red flags
    promoter_unavailable: bool = False
    identity_mismatch: bool = False
    poor_business_knowledge: bool = False
    evasive_responses: bool = False


@dataclass
class MarketCheck:
    """Local market intelligence"""
    supplier_checks_done: int = 0
    supplier_confirmations: int = 0
    supplier_feedback: List[str] = field(default_factory=list)

    customer_checks_done: int = 0
    customer_confirmations: int = 0
    customer_feedback: List[str] = field(default_factory=list)

    competitor_checks_done: int = 0
    competitor_feedback: List[str] = field(default_factory=list)

    local_reputation: str = "UNKNOWN"  # GOOD/AVERAGE/POOR/UNKNOWN
    years_in_operation_confirmed: float = 0.0

    # Red flags
    no_supplier_confirmation: bool = False
    no_customer_confirmation: bool = False
    negative_market_feedback: bool = False


@dataclass
class DocumentVerification:
    """Cross-verification of submitted documents"""
    gst_certificate_verified: bool = False
    gst_verification_remarks: str = ""

    electricity_bill_verified: bool = False
    electricity_bill_remarks: str = ""

    rent_agreement_verified: bool = False
    rent_agreement_remarks: str = ""

    bank_statements_discussed: bool = False
    bank_statement_remarks: str = ""

    licenses_permits_verified: bool = False
    licenses_remarks: str = ""

    # Red flags
    document_tampering_suspected: bool = False
    address_mismatch_in_documents: bool = False


@dataclass
class PhotographicEvidence:
    """Photographic documentation"""
    premises_exterior_photos: int = 0
    premises_interior_photos: int = 0
    machinery_photos: int = 0
    inventory_photos: int = 0
    promoter_photo_taken: bool = False
    signage_photos: int = 0

    geo_tagged: bool = False
    timestamp_verified: bool = False


@dataclass
class RCUVerificationResult:
    """Complete RCU verification result"""
    company_name: str
    cin: str
    verification_date: date
    verifier_name: str
    verifier_id: str

    # Individual verification modules
    address_verification: AddressVerification
    operations_verification: BusinessOperationsVerification
    promoter_meeting: PromoterMeeting
    market_check: MarketCheck
    document_verification: DocumentVerification
    photographic_evidence: PhotographicEvidence

    # Overall assessment
    overall_status: str = RCUOverallStatus.POSITIVE.value
    overall_score: int = 0  # 0-100

    # Critical findings
    red_flags: List[str] = field(default_factory=list)
    positive_observations: List[str] = field(default_factory=list)
    discrepancies: List[str] = field(default_factory=list)

    # Recommendations
    recommendation: str = ""
    conditions_if_approved: List[str] = field(default_factory=list)

    # Additional fields
    verification_duration_minutes: int = 0
    follow_up_required: bool = False
    follow_up_items: List[str] = field(default_factory=list)


async def run_rcu_verification_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main RCU verification agent function.

    In production, this would:
    1. Assign RCU officer
    2. Schedule field visit
    3. Collect verification data
    4. Generate report

    For now, this is a mock implementation that simulates RCU verification.

    Args:
        state: AppraisalState dictionary

    Returns:
        Updated state with RCU verification results
    """
    company_name = state.get("company_name", "Unknown")
    cin = state.get("cin", "")

    # In production, would integrate with:
    # - Field officer mobile app
    # - GPS/geo-tagging system
    # - Photo upload system
    # - Market intelligence database

    # For now, simulate verification based on available data
    rcu_result = _simulate_rcu_verification(
        company_name=company_name,
        cin=cin,
        registered_address=state.get("registered_address", ""),
        business_address=state.get("business_address", ""),
        company_age_years=state.get("company_age_years", 5.0),
        declared_employees=state.get("number_of_employees", 10),
    )

    state["rcu_verification"] = {
        "overall_status": rcu_result.overall_status,
        "overall_score": rcu_result.overall_score,
        "red_flags_count": len(rcu_result.red_flags),
        "red_flags": rcu_result.red_flags,
        "discrepancies": rcu_result.discrepancies,
        "recommendation": rcu_result.recommendation,
        "verification_date": rcu_result.verification_date.isoformat(),
    }

    # Add to state for downstream agents
    state["rcu_red_flags"] = rcu_result.red_flags
    state["rcu_status"] = rcu_result.overall_status

    return state


def _simulate_rcu_verification(
    company_name: str,
    cin: str,
    registered_address: str,
    business_address: str,
    company_age_years: float,
    declared_employees: int,
) -> RCUVerificationResult:
    """
    Simulate RCU verification for testing.

    In production, this would be real field verification data.
    """
    # Simulate based on company characteristics
    is_young_company = company_age_years < 3
    is_small_company = declared_employees < 20

    # Address verification
    address_verification = AddressVerification(
        registered_address_verified=True,
        registered_address_status=VerificationStatus.VERIFIED.value,
        registered_address_remarks="Address verified through GPS coordinates and signage",
        business_address_verified=True,
        business_address_status=VerificationStatus.VERIFIED.value if not is_young_company else VerificationStatus.PARTIAL.value,
        business_address_remarks="Business premises found operational" if not is_young_company else "Small office space, minimal infrastructure",
        factory_address_verified=not is_small_company,
        factory_address_status=VerificationStatus.VERIFIED.value if not is_small_company else VerificationStatus.NOT_VERIFIED.value,
        factory_address_remarks="Factory operational with visible activity" if not is_small_company else "No factory premises",
        premises_ownership="RENTED" if is_young_company else "OWNED",
        premises_condition="GOOD" if not is_young_company else "AVERAGE",
        premises_size_match=True,
        address_is_virtual_office=False,
        address_is_residential=is_young_company and is_small_company,
        no_business_signage=is_young_company,
    )

    # Operations verification
    operations_verification = BusinessOperationsVerification(
        business_activity_observed=not is_young_company,
        business_activity_matches_application=True,
        business_activity_remarks="Active operations observed with ongoing work" if not is_young_company else "Limited activity observed",
        employees_present=int(declared_employees * 0.8) if not is_young_company else max(2, int(declared_employees * 0.5)),
        employees_match_declared=not is_young_company,
        machinery_equipment_present=not is_small_company,
        machinery_condition="OPERATIONAL" if not is_small_company else "UNKNOWN",
        machinery_matches_declared=True,
        inventory_present=not is_small_company,
        inventory_quantity="MODERATE" if not is_small_company else "MINIMAL",
        inventory_matches_declared=not is_young_company,
        no_business_activity=False,
        minimal_infrastructure=is_young_company and is_small_company,
        operations_appear_dormant=False,
    )

    # Promoter meeting
    promoter_meeting = PromoterMeeting(
        promoter_met=True,
        promoter_name="Managing Director",
        meeting_date=date.today(),
        meeting_mode="IN_PERSON",
        identity_verified=True,
        identity_document="PAN and Aadhaar",
        promoter_knowledge_score=8 if not is_young_company else 7,
        promoter_cooperation="COOPERATIVE",
        promoter_unavailable=False,
        identity_mismatch=False,
        poor_business_knowledge=False,
        evasive_responses=False,
    )

    # Market check
    market_check = MarketCheck(
        supplier_checks_done=3 if not is_young_company else 1,
        supplier_confirmations=2 if not is_young_company else 1,
        supplier_feedback=["Regular payments", "3 years relationship"] if not is_young_company else ["New customer"],
        customer_checks_done=2 if not is_young_company else 1,
        customer_confirmations=2 if not is_young_company else 0,
        customer_feedback=["Satisfied with service", "Timely delivery"] if not is_young_company else [],
        competitor_checks_done=1,
        competitor_feedback=["Known in local market"] if not is_young_company else ["New player"],
        local_reputation="GOOD" if not is_young_company else "AVERAGE",
        years_in_operation_confirmed=company_age_years if not is_young_company else max(1, company_age_years * 0.8),
        no_supplier_confirmation=False,
        no_customer_confirmation=is_young_company,
        negative_market_feedback=False,
    )

    # Document verification
    document_verification = DocumentVerification(
        gst_certificate_verified=True,
        gst_verification_remarks="GST certificate matches, address confirmed",
        electricity_bill_verified=True,
        electricity_bill_remarks="Bill for business premises verified",
        rent_agreement_verified=True if address_verification.premises_ownership == "RENTED" else False,
        rent_agreement_remarks="Rent agreement verified with landlord" if address_verification.premises_ownership == "RENTED" else "N/A - Owned premises",
        bank_statements_discussed=True,
        bank_statement_remarks="Discussed major transactions",
        licenses_permits_verified=not is_small_company,
        licenses_remarks="Trade license and factory license verified" if not is_small_company else "Licenses pending verification",
        document_tampering_suspected=False,
        address_mismatch_in_documents=False,
    )

    # Photographic evidence
    photographic_evidence = PhotographicEvidence(
        premises_exterior_photos=3,
        premises_interior_photos=5 if not is_small_company else 2,
        machinery_photos=4 if not is_small_company else 0,
        inventory_photos=3 if not is_small_company else 1,
        promoter_photo_taken=True,
        signage_photos=2 if not is_young_company else 0,
        geo_tagged=True,
        timestamp_verified=True,
    )

    # Identify red flags
    red_flags = []
    if address_verification.address_is_residential:
        red_flags.append("Business operated from residential premises - may indicate small scale")
    if address_verification.no_business_signage:
        red_flags.append("No business signage at premises")
    if operations_verification.minimal_infrastructure:
        red_flags.append("Minimal infrastructure observed - scale may be smaller than claimed")
    if not operations_verification.employees_match_declared:
        red_flags.append(f"Only {operations_verification.employees_present} employees present vs {declared_employees} declared")
    if market_check.no_customer_confirmation:
        red_flags.append("Unable to verify customer relationships")
    if operations_verification.operations_appear_dormant:
        red_flags.append("CRITICAL: Operations appear dormant or minimal")
    if promoter_meeting.evasive_responses:
        red_flags.append("CRITICAL: Promoter provided evasive responses")
    if document_verification.document_tampering_suspected:
        red_flags.append("FRAUD ALERT: Document tampering suspected")

    # Positive observations
    positive_observations = []
    if address_verification.registered_address_status == VerificationStatus.VERIFIED.value:
        positive_observations.append("Registered address verified successfully")
    if operations_verification.business_activity_observed:
        positive_observations.append("Active business operations confirmed")
    if promoter_meeting.promoter_knowledge_score >= 8:
        positive_observations.append("Promoter demonstrated strong business knowledge")
    if market_check.local_reputation == "GOOD":
        positive_observations.append("Positive local market reputation")
    if photographic_evidence.geo_tagged:
        positive_observations.append("All verification photos are geo-tagged and timestamped")

    # Discrepancies
    discrepancies = []
    if not operations_verification.employees_match_declared:
        discrepancies.append(f"Employee count discrepancy: {operations_verification.employees_present} present vs {declared_employees} declared")
    if not operations_verification.inventory_matches_declared:
        discrepancies.append("Inventory levels lower than declared in application")
    if abs(market_check.years_in_operation_confirmed - company_age_years) > 0.5:
        discrepancies.append(f"Market feedback suggests {market_check.years_in_operation_confirmed:.1f} years vs {company_age_years:.1f} years claimed")

    # Calculate overall score
    score = 100
    score -= len(red_flags) * 10
    score -= len(discrepancies) * 5
    if not operations_verification.business_activity_observed:
        score -= 20
    if not address_verification.business_address_verified:
        score -= 15
    if not promoter_meeting.promoter_met:
        score -= 25
    score = max(0, min(100, score))

    # Determine overall status
    if any("FRAUD" in flag or "CRITICAL" in flag for flag in red_flags):
        overall_status = RCUOverallStatus.FRAUD_ALERT.value
    elif score < 50:
        overall_status = RCUOverallStatus.NEGATIVE.value
    elif score < 70 or len(red_flags) > 0:
        overall_status = RCUOverallStatus.POSITIVE_WITH_OBSERVATIONS.value
    else:
        overall_status = RCUOverallStatus.POSITIVE.value

    # Generate recommendation
    if overall_status == RCUOverallStatus.FRAUD_ALERT.value:
        recommendation = "REJECT - Fraud indicators detected. Do not proceed with loan."
    elif overall_status == RCUOverallStatus.NEGATIVE.value:
        recommendation = "NOT RECOMMENDED - Significant discrepancies and red flags. High risk of default."
    elif overall_status == RCUOverallStatus.POSITIVE_WITH_OBSERVATIONS.value:
        recommendation = f"PROCEED WITH CAUTION - {len(red_flags)} red flag(s) identified. Recommend additional conditions and monitoring."
    else:
        recommendation = "RECOMMENDED - RCU verification positive. Business operations and premises verified."

    # Conditions if approved
    conditions = []
    if is_young_company:
        conditions.append("Require additional promoter guarantee due to limited operating history")
    if is_small_company:
        conditions.append("Lower disbursement amount considering observed scale")
    if len(red_flags) > 0:
        conditions.append("Monthly monitoring for first 6 months")
    if not operations_verification.employees_match_declared:
        conditions.append("Re-verification of employee strength after 3 months")

    # Follow-up items
    follow_up = []
    if not document_verification.licenses_permits_verified:
        follow_up.append("Verify pending licenses and permits")
    if market_check.customer_confirmations < 2:
        follow_up.append("Obtain at least 2 customer references")

    return RCUVerificationResult(
        company_name=company_name,
        cin=cin,
        verification_date=date.today(),
        verifier_name="RCU Officer - Field Team",
        verifier_id="RCU-001",
        address_verification=address_verification,
        operations_verification=operations_verification,
        promoter_meeting=promoter_meeting,
        market_check=market_check,
        document_verification=document_verification,
        photographic_evidence=photographic_evidence,
        overall_status=overall_status,
        overall_score=score,
        red_flags=red_flags,
        positive_observations=positive_observations,
        discrepancies=discrepancies,
        recommendation=recommendation,
        conditions_if_approved=conditions,
        verification_duration_minutes=120 if not is_small_company else 60,
        follow_up_required=len(follow_up) > 0,
        follow_up_items=follow_up,
    )


def generate_rcu_report(result: RCUVerificationResult) -> str:
    """Generate formatted RCU report"""
    report = f"""
{'='*80}
RCU VERIFICATION REPORT
{'='*80}

Company: {result.company_name}
CIN: {result.cin}
Verification Date: {result.verification_date.strftime('%d-%b-%Y')}
Verifier: {result.verifier_name} (ID: {result.verifier_id})
Duration: {result.verification_duration_minutes} minutes

{'='*80}
OVERALL ASSESSMENT
{'='*80}
Status: {result.overall_status}
Score: {result.overall_score}/100
Recommendation: {result.recommendation}

{'='*80}
ADDRESS VERIFICATION
{'='*80}
Registered Address: {result.address_verification.registered_address_status}
Business Address: {result.address_verification.business_address_status}
Premises: {result.address_verification.premises_ownership} | {result.address_verification.premises_condition}
Remarks: {result.address_verification.business_address_remarks}

{'='*80}
OPERATIONS VERIFICATION
{'='*80}
Business Activity: {"Observed" if result.operations_verification.business_activity_observed else "Not observed"}
Employees Present: {result.operations_verification.employees_present}
Machinery: {result.operations_verification.machinery_condition}
Inventory: {result.operations_verification.inventory_quantity}

{'='*80}
PROMOTER MEETING
{'='*80}
Promoter Met: {"Yes" if result.promoter_meeting.promoter_met else "No"}
Identity Verified: {"Yes" if result.promoter_meeting.identity_verified else "No"}
Business Knowledge: {result.promoter_meeting.promoter_knowledge_score}/10
Cooperation: {result.promoter_meeting.promoter_cooperation}

{'='*80}
MARKET INTELLIGENCE
{'='*80}
Supplier Checks: {result.market_check.supplier_confirmations}/{result.market_check.supplier_checks_done} confirmed
Customer Checks: {result.market_check.customer_confirmations}/{result.market_check.customer_checks_done} confirmed
Local Reputation: {result.market_check.local_reputation}

{'='*80}
RED FLAGS ({len(result.red_flags)})
{'='*80}
"""
    if result.red_flags:
        for i, flag in enumerate(result.red_flags, 1):
            report += f"{i}. ⚠ {flag}\n"
    else:
        report += "No red flags identified.\n"

    report += f"""
{'='*80}
DISCREPANCIES ({len(result.discrepancies)})
{'='*80}
"""
    if result.discrepancies:
        for i, disc in enumerate(result.discrepancies, 1):
            report += f"{i}. {disc}\n"
    else:
        report += "No discrepancies identified.\n"

    report += f"""
{'='*80}
CONDITIONS (IF APPROVED)
{'='*80}
"""
    if result.conditions_if_approved:
        for i, cond in enumerate(result.conditions_if_approved, 1):
            report += f"{i}. {cond}\n"
    else:
        report += "No additional conditions.\n"

    report += f"\n{'='*80}\n"

    return report


if __name__ == "__main__":
    # Test RCU verification
    print("Testing RCU Verification Agent\n")

    # Test case 1: Established company
    print("\n1. ESTABLISHED COMPANY")
    result1 = _simulate_rcu_verification(
        company_name="ABC Manufacturing Ltd",
        cin="U12345MH2015PTC123456",
        registered_address="123 Industrial Area",
        business_address="123 Industrial Area",
        company_age_years=8.0,
        declared_employees=50,
    )
    print(generate_rcu_report(result1))

    # Test case 2: Young startup
    print("\n2. YOUNG STARTUP")
    result2 = _simulate_rcu_verification(
        company_name="Tech Startup Pvt Ltd",
        cin="U12345KA2023PTC789012",
        registered_address="45 Residential Complex",
        business_address="45 Residential Complex",
        company_age_years=1.5,
        declared_employees=8,
    )
    print(generate_rcu_report(result2))
