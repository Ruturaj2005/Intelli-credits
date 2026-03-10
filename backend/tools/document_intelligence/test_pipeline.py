"""
Document Intelligence Pipeline - Test Script
Demonstrates the full pipeline capability.
"""
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.pdf_parser import parse_with_intelligence
from tools.document_intelligence.confidence_scorer import generate_extraction_report


def test_pipeline(pdf_path: str):
    """
    Test the complete document intelligence pipeline.
    """
    print("=" * 70)
    print("DOCUMENT INTELLIGENCE PIPELINE - TEST")
    print("=" * 70)
    print(f"\nProcessing: {pdf_path}\n")
    
    # Run the pipeline
    print("⏳ Starting pipeline...")
    result = parse_with_intelligence(
        file_path=pdf_path,
        use_advanced_pipeline=True
    )
    
    if result.get("error"):
        print(f"❌ Error: {result['error']}")
        return
    
    print("✓ Pipeline completed successfully!\n")
    
    # Display results
    print("=" * 70)
    print("DOCUMENT CLASSIFICATION")
    print("=" * 70)
    doc_class = result.get("doc_classification", {})
    print(f"Document Type: {doc_class.get('document_type', 'unknown')}")
    print(f"Classification Confidence: {doc_class.get('confidence', 0):.1%}")
    print(f"Matched Patterns: {len(doc_class.get('matched_patterns', []))}")
    
    # Display extracted entities
    print("\n" + "=" * 70)
    print("EXTRACTED FINANCIAL ENTITIES")
    print("=" * 70)
    entities = result.get("financial_entities", {})
    
    key_metrics = ["revenue", "ebitda", "ebit", "pbt", "pat", "total_debt", "net_worth"]
    
    for metric in key_metrics:
        if metric in entities:
            entity_data = entities[metric]
            if isinstance(entity_data, dict):
                value = entity_data.get("value", 0)
                confidence = entity_data.get("entity_confidence", 0)
                source = entity_data.get("source", "unknown")
                
                # Format value in Crores
                value_cr = value / 10_000_000
                print(f"{metric.upper():<20} ₹ {value_cr:>12,.2f} Cr  (conf: {confidence:.1%}, source: {source})")
    
    # Display validation results
    print("\n" + "=" * 70)
    print("VALIDATION RESULTS")
    print("=" * 70)
    validation = result.get("validation", {})
    flags = validation.get("flags", [])
    warnings = validation.get("warnings", [])
    
    if not flags and not warnings:
        print("✓ All validation checks passed!")
    else:
        if flags:
            print(f"\n⚠️  {len(flags)} Flag(s) Detected:")
            for flag in flags[:5]:  # Show first 5
                print(f"  - [{flag.get('severity')}] {flag.get('message')}")
        
        if warnings:
            print(f"\n⚡ {len(warnings)} Warning(s):")
            for warning in warnings[:5]:  # Show first 5
                print(f"  - {warning.get('message')}")
    
    # Display confidence metrics
    print("\n" + "=" * 70)
    print("CONFIDENCE ASSESSMENT")
    print("=" * 70)
    
    overall = result.get("overall_confidence", 0)
    reliability = result.get("reliability_score", "UNKNOWN")
    breakdown = result.get("confidence_breakdown", {})
    
    print(f"Overall Confidence:     {overall:.1%}")
    print(f"Reliability Score:      {reliability}")
    print(f"\nBreakdown:")
    print(f"  - OCR Quality:        {breakdown.get('ocr_quality', 0):.1%}")
    print(f"  - Data Extraction:    {breakdown.get('data_extraction', 0):.1%}")
    print(f"  - Validation:         {breakdown.get('validation', 0):.1%}")
    print(f"  - Classification:     {breakdown.get('classification', 0):.1%}")
    
    # Display extraction report
    print("\n" + "=" * 70)
    report = generate_extraction_report({
        "overall_confidence": overall,
        "reliability_score": reliability,
        "confidence_breakdown": breakdown,
        "confidence_narrative": "Test pipeline execution",
        "entities": entities,
    })
    print(report)
    
    print("\n" + "=" * 70)
    print("TEST COMPLETE")
    print("=" * 70)
    
    return result


def demo_comparison(pdf_path: str):
    """
    Compare basic extraction vs advanced pipeline.
    """
    from tools.pdf_parser import parse_financial_document
    
    print("\n" + "=" * 70)
    print("COMPARISON: Basic vs Advanced Pipeline")
    print("=" * 70)
    
    # Basic extraction
    print("\n1. Basic Extraction (PyMuPDF only)...")
    basic_result = parse_financial_document(pdf_path, "annual_report")
    basic_text_length = len(basic_result.get("text", ""))
    basic_tables = basic_result.get("tables_text", "")
    
    print(f"   Text extracted: {basic_text_length} characters")
    print(f"   Tables: {len(basic_tables)} characters")
    print(f"   Structured data: None")
    
    # Advanced extraction
    print("\n2. Advanced Pipeline (Document Intelligence)...")
    advanced_result = parse_with_intelligence(pdf_path, use_advanced_pipeline=True)
    
    entities_count = len(advanced_result.get("financial_entities", {}))
    tables_count = advanced_result.get("tables_count", 0)
    confidence = advanced_result.get("overall_confidence", 0)
    
    print(f"   Text extracted: {len(advanced_result.get('text', ''))} characters")
    print(f"   Tables detected: {tables_count}")
    print(f"   Financial entities: {entities_count}")
    print(f"   Confidence: {confidence:.1%}")
    
    print("\n✓ Advanced pipeline provides structured, validated financial data!")
    print("  Ready for scoring engine without manual parsing.\n")


if __name__ == "__main__":
    # Example usage
    if len(sys.argv) > 1:
        pdf_file = sys.argv[1]
    else:
        # Default test file
        pdf_file = "uploads/sample_annual_report.pdf"
    
    if not Path(pdf_file).exists():
        print(f"Error: File not found: {pdf_file}")
        print("\nUsage: python test_pipeline.py <path_to_pdf>")
        sys.exit(1)
    
    # Run test
    result = test_pipeline(pdf_file)
    
    # Run comparison
    if result and not result.get("error"):
        demo_comparison(pdf_file)
