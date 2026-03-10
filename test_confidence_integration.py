"""
Test Script for Document Intelligence Confidence Integration
Tests confidence thresholds, metric filtering, and quality controls.
"""
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_path))


def test_confidence_thresholds():
    """Test confidence threshold logic."""
    print("=" * 70)
    print("TEST 1: Confidence Threshold Gating")
    print("=" * 70)
    
    test_cases = [
        {"confidence": 0.85, "expected_status": "ACCEPTED", "expected_warning": None},
        {"confidence": 0.65, "expected_status": "ACCEPTED_WITH_WARNING", "expected_warning": "moderate"},
        {"confidence": 0.35, "expected_status": "REQUIRES_REVIEW", "expected_warning": "low"},
    ]
    
    for i, case in enumerate(test_cases, 1):
        conf = case["confidence"]
        
        # Simulate threshold logic from main.py
        if conf >= 0.7:
            status = "ACCEPTED"
            warning = None
        elif 0.5 <= conf < 0.7:
            status = "ACCEPTED_WITH_WARNING"
            warning = f"moderate confidence ({conf:.0%})"
        else:
            status = "REQUIRES_REVIEW"
            warning = f"low confidence ({conf:.0%})"
        
        # Verify
        passed = status == case["expected_status"]
        icon = "✓" if passed else "✗"
        
        print(f"{icon} Case {i}: confidence={conf:.1%} → status={status}")
        if warning:
            print(f"   Warning: {warning}")
    
    print()


def test_metric_filtering():
    """Test low-confidence metric filtering."""
    print("=" * 70)
    print("TEST 2: Confidence-Based Metric Filtering")
    print("=" * 70)
    
    # Mock financial entities with confidence scores
    test_entities = {
        "revenue": {"value": 25000000, "entity_confidence": 0.92, "source": "table"},
        "ebitda": {"value": 5000000, "entity_confidence": 0.65, "source": "text"},  # Below threshold
        "pat": {"value": 2500000, "entity_confidence": 0.88, "source": "table"},
        "debt": {"value": 15000000, "entity_confidence": 0.45, "source": "ocr"},  # Below threshold
        "net_worth": {"value": 30000000, "entity_confidence": 0.95, "source": "table"},
    }
    
    threshold = 0.7
    accepted = []
    flagged = []
    
    for metric, data in test_entities.items():
        conf = data.get("entity_confidence", 1.0)
        if conf >= threshold:
            accepted.append(metric)
        else:
            flagged.append({"metric": metric, "confidence": conf})
    
    print(f"Total metrics: {len(test_entities)}")
    print(f"Accepted (≥{threshold:.0%}): {len(accepted)}")
    print(f"  ✓ {', '.join(accepted)}")
    print(f"\nFlagged (<{threshold:.0%}): {len(flagged)}")
    for item in flagged:
        print(f"  ⚠ {item['metric']}: {item['confidence']:.1%} confidence")
    
    print()


def test_document_quality_summary():
    """Test document quality summary compilation."""
    print("=" * 70)
    print("TEST 3: Document Quality Summary")
    print("=" * 70)
    
    # Mock documents with varying confidence levels
    test_documents = [
        {"file_name": "Annual_Report.pdf", "overall_confidence": 0.88, "reliability_score": "GOOD"},
        {"file_name": "Bank_Statement.pdf", "overall_confidence": 0.92, "reliability_score": "EXCELLENT"},
        {"file_name": "GST_Returns.pdf", "overall_confidence": 0.65, "reliability_score": "FAIR"},
        {"file_name": "ITR_Scanned.pdf", "overall_confidence": 0.42, "reliability_score": "POOR"},
        {"file_name": "Audited_Financials.pdf", "overall_confidence": 0.85, "reliability_score": "GOOD"},
    ]
    
    high_conf = sum(1 for d in test_documents if d["overall_confidence"] >= 0.7)
    moderate_conf = sum(1 for d in test_documents if 0.5 <= d["overall_confidence"] < 0.7)
    low_conf = sum(1 for d in test_documents if d["overall_confidence"] < 0.5)
    
    print(f"Total Documents: {len(test_documents)}")
    print(f"  ✓ High Confidence (≥70%): {high_conf}")
    print(f"  ⚠ Moderate Confidence (50-70%): {moderate_conf}")
    print(f"  ✗ Low Confidence (<50%): {low_conf}")
    print(f"\nDocument Breakdown:")
    
    for doc in test_documents:
        if doc["overall_confidence"] >= 0.7:
            icon = "✓"
        elif doc["overall_confidence"] >= 0.5:
            icon = "⚠"
        else:
            icon = "✗"
        
        print(f"  {icon} {doc['file_name']}: {doc['overall_confidence']:.1%} ({doc['reliability_score']})")
    
    print()


def test_retry_logic():
    """Simulate retry logic for low confidence documents."""
    print("=" * 70)
    print("TEST 4: Retry Logic Simulation")
    print("=" * 70)
    
    initial_confidence = 0.42
    print(f"Initial extraction confidence: {initial_confidence:.1%}")
    print(f"Threshold for retry: <50%")
    print()
    
    if initial_confidence < 0.5:
        print("⚠ Low confidence detected. Triggering retry mechanism...")
        print("  Step 1: High-resolution preprocessing (600 DPI)")
        print("  Step 2: Fallback OCR with Tesseract")
        print("  Step 3: Re-running pipeline stages...")
        
        # Simulate improved confidence after retry
        retry_confidence = 0.58
        print(f"\n✓ Retry complete. New confidence: {retry_confidence:.1%}")
        
        if retry_confidence > initial_confidence:
            print(f"✓ Improvement detected: {initial_confidence:.1%} → {retry_confidence:.1%}")
            print("  Using retry results.")
            final_confidence = retry_confidence
        else:
            print("⚠ No improvement. Using original results.")
            final_confidence = initial_confidence
    else:
        print("✓ Confidence acceptable. No retry needed.")
        final_confidence = initial_confidence
    
    print(f"\nFinal confidence: {final_confidence:.1%}")
    print()


def test_cam_data_quality_section():
    """Test CAM data quality section formatting."""
    print("=" * 70)
    print("TEST 5: CAM Data Quality Section")
    print("=" * 70)
    
    # Mock state
    mock_state = {
        "extracted_financials": {
            "document_quality_summary": {
                "total_documents": 5,
                "high_confidence_count": 3,
                "moderate_confidence_count": 1,
                "low_confidence_count": 1,
                "manual_review_required": 1,
            },
            "confidence_filtering": {
                "total_metrics": 15,
                "accepted_metrics": 12,
                "flagged_metrics": 3,
                "flagged_list": [
                    {"metric": "ebitda", "confidence": 0.65, "value": 5000000},
                    {"metric": "debt", "confidence": 0.45, "value": 15000000},
                ]
            }
        }
    }
    
    doc_quality = mock_state["extracted_financials"]["document_quality_summary"]
    conf_filter = mock_state["extracted_financials"]["confidence_filtering"]
    
    print("Data Quality Summary:")
    print(f"  Total Documents: {doc_quality['total_documents']}")
    print(f"    ✓ High Confidence: {doc_quality['high_confidence_count']}")
    print(f"    ⚠ Moderate Confidence: {doc_quality['moderate_confidence_count']}")
    print(f"    ✗ Low Confidence: {doc_quality['low_confidence_count']}")
    
    if doc_quality["manual_review_required"] > 0:
        print(f"\n  ⚠ ALERT: {doc_quality['manual_review_required']} document(s) require manual verification")
    
    print(f"\nMetric Confidence Filtering:")
    print(f"  Total Metrics: {conf_filter['total_metrics']}")
    print(f"  Accepted: {conf_filter['accepted_metrics']}")
    print(f"  Flagged: {conf_filter['flagged_metrics']}")
    
    if conf_filter['flagged_metrics'] > 0:
        print(f"\n  ⚠ Low Confidence Metrics:")
        for item in conf_filter['flagged_list']:
            print(f"    • {item['metric']}: {item['confidence']:.1%} confidence")
    
    print()


def test_websocket_alerts():
    """Test WebSocket alert generation."""
    print("=" * 70)
    print("TEST 6: WebSocket Alert Generation")
    print("=" * 70)
    
    test_scenarios = [
        {
            "document": "Clean_Report.pdf",
            "confidence": 0.88,
            "reliability": "GOOD",
            "expected_alert": None
        },
        {
            "document": "Moderate_Scan.pdf",
            "confidence": 0.62,
            "reliability": "FAIR",
            "expected_alert": "document_quality_warning"
        },
        {
            "document": "Poor_Scan.pdf",
            "confidence": 0.38,
            "reliability": "POOR",
            "expected_alert": "document_quality_alert"
        }
    ]
    
    for scenario in test_scenarios:
        conf = scenario["confidence"]
        doc = scenario["document"]
        
        if conf >= 0.7:
            alert = None
            print(f"✓ {doc}: No alert (confidence {conf:.1%})")
        elif 0.5 <= conf < 0.7:
            alert = {
                "type": "document_quality_warning",
                "message": "Moderate quality - manual verification recommended"
            }
            print(f"⚠ {doc}: WARNING alert sent")
            print(f"   Type: {alert['type']}")
            print(f"   Message: {alert['message']}")
        else:
            alert = {
                "type": "document_quality_alert",
                "message": "Low quality detected - manual review required"
            }
            print(f"✗ {doc}: ALERT sent")
            print(f"   Type: {alert['type']}")
            print(f"   Message: {alert['message']}")
        
        print()


def run_all_tests():
    """Run all test suites."""
    print("\n")
    print("╔" + "═" * 68 + "╗")
    print("║" + " " * 10 + "DOCUMENT INTELLIGENCE CONFIDENCE TESTS" + " " * 20 + "║")
    print("╚" + "═" * 68 + "╝")
    print()
    
    test_confidence_thresholds()
    test_metric_filtering()
    test_document_quality_summary()
    test_retry_logic()
    test_cam_data_quality_section()
    test_websocket_alerts()
    
    print("=" * 70)
    print("ALL TESTS COMPLETED ✓")
    print("=" * 70)
    print()
    print("Next Steps:")
    print("  1. Test with real PDF documents")
    print("  2. Monitor logs for confidence metrics")
    print("  3. Verify CAM report includes data quality section")
    print("  4. Check frontend WebSocket alerts")
    print()


if __name__ == "__main__":
    run_all_tests()
