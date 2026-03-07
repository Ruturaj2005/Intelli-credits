"""
Early Warning System — Post-Disbursement Risk Monitoring

Monitors borrower health after loan disbursement to detect early signs of stress:
1. GST filing delays or non-filing
2. Cheque bounces (outward)
3. Credit rating downgrades
4. Account balance deterioration
5. Director resignations
6. Regulatory actions or penalties
7. Negative news/media coverage
8. Payment defaults on other facilities

Alert Levels:
- GREEN: All parameters healthy
- AMBER: Minor concerns - monitor closely
- RED: Significant deterioration - immediate action
- CRITICAL: Imminent default risk - recovery mode

Monitoring Frequency:
- GST: Monthly
- Bank statements: Weekly
- Ratings: Quarterly
- News: Daily

Author: Credit Intelligence System
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class AlertLevel(str, Enum):
    """Alert severity levels."""
    GREEN = "GREEN"
    AMBER = "AMBER"
    RED = "RED"
    CRITICAL = "CRITICAL"


@dataclass
class Alert:
    """An early warning alert."""
    alert_type: str
    description: str
    severity: AlertLevel
    date_detected: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    action_required: str = ""


@dataclass
class EarlyWarningResult:
    """Result from early warning system."""
    overall_alert_level: AlertLevel
    alerts: List[Alert]
    score: float  # 0-100 (health score)
    monitoring_date: str
    borrower_id: str
    loan_account_number: str
    
    # Indicators
    gst_filing_status: str = "Current"
    recent_bounces: int = 0
    account_balance_trend: str = "Stable"
    rating_change: Optional[str] = None
    director_changes: int = 0
    
    recommendation: str = ""


async def monitor_borrower_health(
    borrower_id: str,
    loan_account: str,
    monitoring_data: Dict[str, Any]
) -> EarlyWarningResult:
    """
    Monitor borrower's post-disbursement health.
    
    Args:
        borrower_id: Borrower identifier
        loan_account: Loan account number
        monitoring_data: Latest monitoring data
        
    Returns:
        EarlyWarningResult with alerts and recommendations
    """
    logger.info(f"⚠️  Monitoring borrower health: {borrower_id}, Account: {loan_account}")
    
    alerts = []
    
    # Check 1: GST filing compliance
    gst_alerts = _check_gst_filing(monitoring_data.get('gst_data', {}))
    alerts.extend(gst_alerts)
    
    # Check 2: Cheque bounces
    bounce_alerts = _check_cheque_bounces(monitoring_data.get('banking_data', {}))
    alerts.extend(bounce_alerts)
    
    # Check 3: Account balance trends
    balance_alerts = _check_account_balance(monitoring_data.get('banking_data', {}))
    alerts.extend(balance_alerts)
    
    # Check 4: Credit rating changes
    rating_alerts = _check_rating_changes(monitoring_data.get('rating_data', {}))
    alerts.extend(rating_alerts)
    
    # Check 5: Director changes
    director_alerts = _check_director_changes(monitoring_data.get('corporate_data', {}))
    alerts.extend(director_alerts)
    
    # Check 6: Payment defaults
    default_alerts = _check_payment_defaults(monitoring_data.get('credit_bureau_data', {}))
    alerts.extend(default_alerts)
    
    # Check 7: Loan covenant breaches
    covenant_alerts = _check_covenant_breaches(monitoring_data.get('financial_data', {}))
    alerts.extend(covenant_alerts)
    
    # Determine overall alert level
    overall_alert_level = _determine_overall_alert_level(alerts)
    
    # Calculate health score
    health_score = _calculate_health_score(alerts, monitoring_data)
    
    # Generate recommendation
    recommendation = _generate_recommendation(overall_alert_level, alerts)
    
    # Extract summary indicators
    gst_status = monitoring_data.get('gst_data', {}).get('filing_status', 'Current')
    recent_bounces = monitoring_data.get('banking_data', {}).get('cheque_bounces_last_3m', 0)
    balance_trend = monitoring_data.get('banking_data', {}).get('balance_trend', 'Stable')
    rating_change = monitoring_data.get('rating_data', {}).get('recent_change')
    director_changes = monitoring_data.get('corporate_data', {}).get('director_changes_last_6m', 0)
    
    logger.info(
        f"✅ Monitoring complete | Alert Level: {overall_alert_level.value} | "
        f"Health Score: {health_score:.1f}/100 | Alerts: {len(alerts)}"
    )
    
    return EarlyWarningResult(
        overall_alert_level=overall_alert_level,
        alerts=alerts,
        score=health_score,
        monitoring_date=datetime.now().isoformat(),
        borrower_id=borrower_id,
        loan_account_number=loan_account,
        gst_filing_status=gst_status,
        recent_bounces=recent_bounces,
        account_balance_trend=balance_trend,
        rating_change=rating_change,
        director_changes=director_changes,
        recommendation=recommendation
    )


def _check_gst_filing(gst_data: Dict[str, Any]) -> List[Alert]:
    """Check GST filing compliance."""
    alerts = []
    
    filing_status = gst_data.get('filing_status', 'Current')
    pending_returns = gst_data.get('pending_returns', 0)
    
    if filing_status == "Cancelled":
        alerts.append(Alert(
            alert_type="GST_CANCELLED",
            description="GST registration cancelled - CRITICAL",
            severity=AlertLevel.CRITICAL,
            date_detected=datetime.now().isoformat(),
            action_required="Immediate recovery action - recall loan"
        ))
    elif pending_returns >= 3:
        alerts.append(Alert(
            alert_type="GST_NON_FILING",
            description=f"{pending_returns} GST returns pending - business stress indicator",
            severity=AlertLevel.RED,
            date_detected=datetime.now().isoformat(),
            parameters={"pending_returns": pending_returns},
            action_required="Contact borrower, investigate business status"
        ))
    elif pending_returns > 0:
        alerts.append(Alert(
            alert_type="GST_DELAYED_FILING",
            description=f"{pending_returns} GST return(s) pending",
            severity=AlertLevel.AMBER,
            date_detected=datetime.now().isoformat(),
            parameters={"pending_returns": pending_returns},
            action_required="Monitor next filing cycle"
        ))
    
    return alerts


def _check_cheque_bounces(banking_data: Dict[str, Any]) -> List[Alert]:
    """Check for cheque bounces."""
    alerts = []
    
    bounces_3m = banking_data.get('cheque_bounces_last_3m', 0)
    bounces_1m = banking_data.get('cheque_bounces_last_1m', 0)
    
    if bounces_3m > 3:
        alerts.append(Alert(
            alert_type="CHEQUE_BOUNCES",
            description=f"{bounces_3m} cheque bounces in last 3 months - liquidity crisis",
            severity=AlertLevel.RED,
            date_detected=datetime.now().isoformat(),
            parameters={"bounces_3m": bounces_3m},
            action_required="Review additional security, increase monitoring frequency"
        ))
    elif bounces_1m > 0:
        alerts.append(Alert(
            alert_type="CHEQUE_BOUNCE_RECENT",
            description=f"Recent cheque bounce detected",
            severity=AlertLevel.AMBER,
            date_detected=datetime.now().isoformat(),
            parameters={"bounces_1m": bounces_1m},
            action_required="Verify reason, monitor cash flow"
        ))
    
    return alerts


def _check_account_balance(banking_data: Dict[str, Any]) -> List[Alert]:
    """Check account balance trends."""
    alerts = []
    
    balance_trend = banking_data.get('balance_trend', 'Stable')
    avg_balance = banking_data.get('avg_balance_current', 0)
    avg_balance_prev = banking_data.get('avg_balance_previous', 0)
    
    if balance_trend == "Sharply Declining":
        decline_pct = ((avg_balance_prev - avg_balance) / avg_balance_prev * 100) if avg_balance_prev > 0 else 0
        alerts.append(Alert(
            alert_type="BALANCE_DETERIORATION",
            description=f"Account balance declined {decline_pct:.1f}% - cash flow stress",
            severity=AlertLevel.RED,
            date_detected=datetime.now().isoformat(),
            parameters={"decline_pct": decline_pct},
            action_required="Investigate working capital stress, review EMI payment ability"
        ))
    elif balance_trend == "Declining":
        alerts.append(Alert(
            alert_type="BALANCE_DECLINING",
            description="Account balance showing downward trend",
            severity=AlertLevel.AMBER,
            date_detected=datetime.now().isoformat(),
            action_required="Monitor cash flow closely"
        ))
    
    # Check for minimum balance
    if avg_balance < 100_000:  # Example threshold
        alerts.append(Alert(
            alert_type="LOW_BALANCE",
            description=f"Very low average balance (₹{avg_balance:,.0f})",
            severity=AlertLevel.AMBER,
            date_detected=datetime.now().isoformat(),
            action_required="Verify business operations status"
        ))
    
    return alerts


def _check_rating_changes(rating_data: Dict[str, Any]) -> List[Alert]:
    """Check for credit rating downgrades."""
    alerts = []
    
    recent_change = rating_data.get('recent_change')
    current_rating = rating_data.get('current_rating')
    previous_rating = rating_data.get('previous_rating')
    
    if recent_change == "Downgrade":
        alerts.append(Alert(
            alert_type="RATING_DOWNGRADE",
            description=f"Credit rating downgraded from {previous_rating} to {current_rating}",
            severity=AlertLevel.RED,
            date_detected=datetime.now().isoformat(),
            parameters={"current_rating": current_rating, "previous_rating": previous_rating},
            action_required="Review financial performance, consider restructuring"
        ))
    elif recent_change == "Negative Outlook":
        alerts.append(Alert(
            alert_type="RATING_OUTLOOK_NEGATIVE",
            description=f"Rating outlook changed to Negative",
            severity=AlertLevel.AMBER,
            date_detected=datetime.now().isoformat(),
            action_required="Enhanced monitoring"
        ))
    
    return alerts


def _check_director_changes(corporate_data: Dict[str, Any]) -> List[Alert]:
    """Check for director resignations."""
    alerts = []
    
    director_changes = corporate_data.get('director_changes_last_6m', 0)
    key_person_resigned = corporate_data.get('key_person_resigned', False)
    
    if key_person_resigned:
        alerts.append(Alert(
            alert_type="KEY_PERSON_RESIGNATION",
            description="Key management person resigned - governance concern",
            severity=AlertLevel.RED,
            date_detected=datetime.now().isoformat(),
            action_required="Meet with remaining management, assess continuity risk"
        ))
    elif director_changes >= 2:
        alerts.append(Alert(
            alert_type="DIRECTOR_CHURN",
            description=f"{director_changes} director changes in 6 months - instability",
            severity=AlertLevel.AMBER,
            date_detected=datetime.now().isoformat(),
            parameters={"director_changes": director_changes},
            action_required="Understand reasons for changes"
        ))
    
    return alerts


def _check_payment_defaults(credit_bureau_data: Dict[str, Any]) -> List[Alert]:
    """Check for payment defaults on other facilities."""
    alerts = []
    
    has_defaults = credit_bureau_data.get('has_recent_defaults', False)
    overdue_count = credit_bureau_data.get('overdue_accounts', 0)
    dpd_max = credit_bureau_data.get('max_dpd', 0)  # Days Past Due
    
    if dpd_max > 90:
        alerts.append(Alert(
            alert_type="PAYMENT_DEFAULT",
            description=f"Payment default detected - {dpd_max} days past due on other facilities",
            severity=AlertLevel.CRITICAL,
            date_detected=datetime.now().isoformat(),
            parameters={"max_dpd": dpd_max, "overdue_accounts": overdue_count},
            action_required="IMMEDIATE: Check our loan payments, initiate recovery if needed"
        ))
    elif dpd_max > 30:
        alerts.append(Alert(
            alert_type="PAYMENT_DELAY",
            description=f"Payment delays observed - {dpd_max} DPD",
            severity=AlertLevel.RED,
            date_detected=datetime.now().isoformat(),
            parameters={"max_dpd": dpd_max},
            action_required="Contact borrower, assess repayment capacity"
        ))
    
    return alerts


def _check_covenant_breaches(financial_data: Dict[str, Any]) -> List[Alert]:
    """Check for loan covenant breaches."""
    alerts = []
    
    covenant_breaches = financial_data.get('covenant_breaches', [])
    
    for breach in covenant_breaches:
        covenant_name = breach.get('covenant')
        actual_value = breach.get('actual')
        threshold = breach.get('threshold')
        
        alerts.append(Alert(
            alert_type="COVENANT_BREACH",
            description=f"Covenant breach: {covenant_name} ({actual_value} vs threshold {threshold})",
            severity=AlertLevel.RED,
            date_detected=datetime.now().isoformat(),
            parameters=breach,
            action_required="Obtain waiver or corrective action plan from borrower"
        ))
    
    return alerts


def _determine_overall_alert_level(alerts: List[Alert]) -> AlertLevel:
    """Determine overall alert level based on individual alerts."""
    if not alerts:
        return AlertLevel.GREEN
    
    # Check for CRITICAL alerts
    if any(a.severity == AlertLevel.CRITICAL for a in alerts):
        return AlertLevel.CRITICAL
    
    # Count RED alerts
    red_count = sum(1 for a in alerts if a.severity == AlertLevel.RED)
    if red_count >= 2:
        return AlertLevel.CRITICAL
    elif red_count >= 1:
        return AlertLevel.RED
    
    # Count AMBER alerts
    amber_count = sum(1 for a in alerts if a.severity == AlertLevel.AMBER)
    if amber_count >= 3:
        return AlertLevel.RED
    elif amber_count >= 1:
        return AlertLevel.AMBER
    
    return AlertLevel.GREEN


def _calculate_health_score(alerts: List[Alert], monitoring_data: Dict[str, Any]) -> float:
    """Calculate borrower health score (0-100)."""
    score = 100.0
    
    # Deduct points based on alert severity
    for alert in alerts:
        if alert.severity == AlertLevel.CRITICAL:
            score -= 40
        elif alert.severity == AlertLevel.RED:
            score -= 20
        elif alert.severity == AlertLevel.AMBER:
            score -= 8
    
    return max(0, score)


def _generate_recommendation(alert_level: AlertLevel, alerts: List[Alert]) -> str:
    """Generate actionable recommendation."""
    if alert_level == AlertLevel.CRITICAL:
        return "CRITICAL: Initiate recovery procedures. Loan at imminent default risk. Consider asset seizure or restructuring."
    elif alert_level == AlertLevel.RED:
        return "HIGH RISK: Increase monitoring to weekly. Schedule immediate meeting with borrower. Review additional security."
    elif alert_level == AlertLevel.AMBER:
        return "MODERATE RISK: Enhanced monitoring required. Contact borrower to understand issues. Monitor next 2-3 cycles closely."
    else:
        return "Account healthy. Continue standard monitoring protocols."


# ─── Integration Example ─────────────────────────────────────────────────────

async def main_example():
    """Example usage."""
    
    # Scenario 1: Healthy borrower
    print("="*70)
    print("SCENARIO 1: Healthy Borrower")
    print("="*70)
    
    monitoring_data_1 = {
        "gst_data": {"filing_status": "Current", "pending_returns": 0},
        "banking_data": {
            "cheque_bounces_last_3m": 0,
            "balance_trend": "Stable",
            "avg_balance_current": 5_000_000
        },
        "rating_data": {"current_rating": "A", "recent_change": None},
        "corporate_data": {"director_changes_last_6m": 0},
        "credit_bureau_data": {"has_recent_defaults": False, "max_dpd": 0}
    }
    
    result1 = await monitor_borrower_health(
        borrower_id="BRW001",
        loan_account="LA1234567",
        monitoring_data=monitoring_data_1
    )
    
    print(f"Alert Level: {result1.overall_alert_level.value}")
    print(f"Health Score: {result1.score:.1f}/100")
    print(f"Alerts: {len(result1.alerts)}")
    print(f"Recommendation: {result1.recommendation}")
    
    # Scenario 2: Stressed borrower
    print("\n" + "="*70)
    print("SCENARIO 2: Stressed Borrower")
    print("="*70)
    
    monitoring_data_2 = {
        "gst_data": {"filing_status": "Delayed", "pending_returns": 2},
        "banking_data": {
            "cheque_bounces_last_3m": 4,
            "balance_trend": "Sharply Declining",
            "avg_balance_current": 150_000,
            "avg_balance_previous": 2_000_000
        },
        "rating_data": {"current_rating": "BB", "previous_rating": "A", "recent_change": "Downgrade"},
        "corporate_data": {"director_changes_last_6m": 1},
        "credit_bureau_data": {"has_recent_defaults": True, "max_dpd": 45, "overdue_accounts": 2}
    }
    
    result2 = await monitor_borrower_health(
        borrower_id="BRW002",
        loan_account="LA7654321",
        monitoring_data=monitoring_data_2
    )
    
    print(f"Alert Level: {result2.overall_alert_level.value}")
    print(f"Health Score: {result2.score:.1f}/100")
    print(f"Number of Alerts: {len(result2.alerts)}")
    print(f"\n🚨 Alerts:")
    for alert in result2.alerts:
        print(f"  [{alert.severity.value}] {alert.description}")
    print(f"\n📋 Recommendation:")
    print(f"  {result2.recommendation}")


if __name__ == "__main__":
    asyncio.run(main_example())
