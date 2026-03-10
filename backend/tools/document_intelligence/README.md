# Document Intelligence Module

## Overview

The Document Intelligence module provides a **multi-stage pipeline** for extracting structured financial data from messy, scanned, or poorly formatted PDF documents. This addresses the primary weakness of simple text extraction by comprehensively handling:

- Scanned documents
- Skewed/rotated pages
- Noisy scans
- Complex table layouts
- Mixed Indian and international financial formatting

## Architecture

```
PDF Upload
    ↓
Image Preprocessing (OpenCV)
    ↓
OCR + Layout Detection (PaddleOCR)
    ↓
Document Classification
    ↓
Table Extraction (Camelot + OCR)
    ↓
Financial Entity Extraction
    ↓
Unit Normalization (Crore/Lakh → INR)
    ↓
Validation Layer
    ↓
Confidence Scoring
    ↓
Structured JSON Output
```

## Modules

### 1. **image_preprocessor.py**
Cleans messy scanned documents using OpenCV:
- Automatic deskewing (straightens rotated pages)
- Noise removal
- Contrast enhancement
- Adaptive thresholding for OCR

**Key Functions:**
- `preprocess_pdf_pages(pdf_path, dpi=300)` - Convert PDF to cleaned images
- `_deskew_image(img)` - Auto-correct page rotation
- `remove_shadows(img)` - Remove scanning artifacts

### 2. **ocr_engine.py**
Advanced OCR with layout detection using PaddleOCR:
- Text extraction with bounding boxes
- Table region detection
- Multi-language support
- Confidence scoring per text block

**Key Functions:**
- `extract_with_ocr(images, pdf_path)` - Main OCR pipeline
- `_detect_tables_from_layout(text_blocks)` - Identify table regions
- `_fallback_ocr(images)` - Pytesseract fallback

### 3. **document_classifier.py**
Automatically detects document type:
- Annual Report
- Bank Statement
- GST Filing (GSTR-1/2/3B)
- Credit Rating Report
- Legal Notice
- Sanction Letter

**Key Functions:**
- `classify_document(text, filename)` - Main classifier
- `extract_company_identifiers(text)` - Extract CIN, PAN, GSTIN
- `detect_financial_year(text)` - Extract FY information

### 4. **table_extractor.py**
Sophisticated table extraction:
- Camelot library for bordered tables
- OCR-based layout detection for borderless tables
- Table type classification (P&L, Balance Sheet, etc.)
- Direct financial metric extraction from tables

**Key Functions:**
- `extract_tables_advanced(pdf_path, ocr_tables)` - Multi-method extraction
- `_classify_table(table)` - Identify table type
- `extract_financial_table_data(table)` - Extract structured data

### 5. **financial_entity_extractor.py**
Extracts key financial metrics:
- Revenue, EBITDA, PAT, Total Debt, Net Worth
- Current Assets/Liabilities
- Inventory, Receivables, Payables
- Multi-year time series data

**Key Functions:**
- `extract_financial_entities(text, tables, doc_type)` - Main extractor
- `_extract_from_tables(tables)` - Table-based extraction (high confidence)
- `_extract_from_text(text)` - Regex-based fallback
- `_extract_time_series(tables)` - Multi-year trend data

### 6. **unit_normalizer.py**
Normalizes financial values to standard INR:
- Crore → 10,000,000 INR
- Lakh → 100,000 INR
- Million, Billion conversions
- Auto-detection of document units

**Key Functions:**
- `normalize_financial_values(entities, detected_unit)` - Normalize all values
- `detect_and_normalize(entities, full_text)` - Auto-detect and convert
- `format_indian_number(value)` - Display in Crore/Lakh format

### 7. **validation_layer.py**
Cross-validates extracted data:
- Internal consistency checks (EBITDA > EBIT > PBT > PAT)
- Balance sheet equation validation
- Financial ratio reasonableness checks
- Cross-document validation (e.g., GST vs Annual Report)

**Key Functions:**
- `validate_financial_data(entities, doc_type)` - Main validator
- `_check_internal_consistency(entities)` - Logic checks
- `_validate_financial_ratios(entities)` - Ratio bounds checking

### 8. **confidence_scorer.py**
Calculates confidence scores for data reliability:
- Per-entity confidence (based on source: table > OCR > text)
- Overall extraction confidence
- Reliability grading (EXCELLENT/GOOD/FAIR/POOR)
- Human-readable confidence narrative

**Key Functions:**
- `calculate_confidence_scores(entities, ocr_confidence, validation, classification)` - Main scorer
- `generate_extraction_report(confidence_result)` - Detailed report

## Usage

### Basic Usage

```python
from tools.pdf_parser import parse_with_intelligence

# Parse a messy scanned financial document
result = parse_with_intelligence(
    file_path="uploads/annual_report_scan.pdf",
    doc_type="annual_report",
    use_advanced_pipeline=True
)

# Access structured financial data
financial_data = result["financial_entities"]
revenue = financial_data.get("revenue", {}).get("value")
confidence = result["overall_confidence"]
reliability = result["reliability_score"]

print(f"Revenue: ₹{revenue:,.0f}")
print(f"Confidence: {confidence:.1%}")
print(f"Reliability: {reliability}")
```

### Advanced Usage - Full Pipeline Control

```python
from tools.document_intelligence import (
    preprocess_pdf_pages,
    extract_with_ocr,
    classify_document,
    extract_tables_advanced,
    extract_financial_entities,
    detect_and_normalize,
    validate_financial_data,
    calculate_confidence_scores,
)

# Stage 1: Preprocess
images = preprocess_pdf_pages("document.pdf", dpi=300)

# Stage 2: OCR
ocr_result = extract_with_ocr(images, "document.pdf")

# Stage 3: Classify
doc_class = classify_document(ocr_result["full_text"], "document.pdf")

# Stage 4: Extract tables
tables = extract_tables_advanced("document.pdf", ocr_result["tables"])

# Stage 5: Extract entities
entities = extract_financial_entities(
    ocr_result["full_text"],
    tables,
    doc_class["document_type"]
)

# Stage 6: Normalize
normalized = detect_and_normalize(entities, ocr_result["full_text"])

# Stage 7: Validate
validation = validate_financial_data(normalized, doc_class["document_type"])

# Stage 8: Score confidence
confidence_result = calculate_confidence_scores(
    normalized,
    ocr_result["confidence"],
    validation,
    doc_class
)
```

## Integration with Existing INGESTOR Agent

The pipeline integrates seamlessly with the existing ingestor agent. Update `ingestor_agent.py`:

```python
from tools.pdf_parser import parse_with_intelligence

def run_ingestor(documents: List[str], state: Dict) -> Dict:
    logs = []
    
    for doc_path in documents:
        # Use advanced pipeline instead of basic parse_financial_document
        result = parse_with_intelligence(
            file_path=doc_path,
            use_advanced_pipeline=True
        )
        
        # Extract structured financial data
        financial_entities = result.get("financial_entities", {})
        
        # Log confidence metrics
        logs.append({
            "message": f"Extracted with {result['overall_confidence']:.1%} confidence",
            "reliability": result["reliability_score"],
        })
        
        # Pass to LLM for further processing
        state["extracted_financials"] = financial_entities
        state["extraction_confidence"] = result["overall_confidence"]
    
    return state
```

## Output Format

The pipeline returns structured data in this format:

```json
{
  "file_name": "annual_report.pdf",
  "doc_type": "annual_report",
  "doc_classification": {
    "document_type": "annual_report",
    "confidence": 0.92
  },
  
  "financial_entities": {
    "revenue": {
      "value": 1200000000,
      "original_value": 120,
      "original_unit": "crore",
      "normalized_unit": "INR",
      "confidence": 0.95,
      "source": "table_page_12",
      "label": "Total Revenue"
    },
    "pat": {
      "value": 150000000,
      "confidence": 0.90,
      ...
    }
  },
  
  "overall_confidence": 0.88,
  "reliability_score": "GOOD",
  "confidence_breakdown": {
    "ocr_quality": 0.85,
    "data_extraction": 0.92,
    "validation": 0.87,
    "classification": 0.92
  },
  
  "validation": {
    "valid": true,
    "flags": [],
    "warnings": [...]
  }
}
```

## Dependencies

Install new dependencies:

```bash
pip install opencv-python pdf2image paddleocr paddlepaddle camelot-py[cv] pytesseract
```

**Note:** Tesseract OCR binary must be installed separately:
- Ubuntu: `apt-get install tesseract-ocr`
- macOS: `brew install tesseract`
- Windows: Download from [GitHub](https://github.com/UB-Mannheim/tesseract/wiki)

## Performance Considerations

- **DPI Setting**: Higher DPI (300) improves OCR accuracy but increases processing time
- **GPU Acceleration**: Install `paddlepaddle-gpu` for faster OCR on GPU
- **Parallel Processing**: Process multiple pages in parallel for large documents
- **Caching**: Cache preprocessed images for repeated processing

## Fallback Behavior

The pipeline gracefully degrades if components are unavailable:
1. If PaddleOCR fails → Falls back to Pytesseract
2. If Camelot fails → Uses OCR-based table detection
3. If entire pipeline fails → Falls back to basic PyMuPDF extraction

## Confidence Interpretation

| Confidence | Reliability | Interpretation |
|-----------|-------------|----------------|
| > 90% | EXCELLENT | Data is highly reliable, suitable for automated decisions |
| 75-90% | GOOD | Data is reliable, minor manual review recommended |
| 60-75% | FAIR | Data acceptable, significant manual review needed |
| < 60% | POOR | Data unreliable, manual re-entry recommended |

## Troubleshooting

### Issue: Low OCR Confidence
**Solution:** Increase DPI (set to 400), ensure document is not password-protected

### Issue: Tables Not Detected
**Solution:** Check if document has table borders. Use `use_camelot=True` for bordered tables

### Issue: Wrong Document Classification
**Solution:** Provide explicit `doc_type` parameter, improve document quality

### Issue: Unit Normalization Errors
**Solution:** Ensure document clearly states units (Crore/Lakh). Check for mixed units in tables.

## Future Enhancements

- [ ] Deep learning-based table structure recognition
- [ ] Multi-document reconciliation engine
- [ ] Historical trend analysis and anomaly detection
- [ ] Integration with external data sources (MCA, GST portal)
- [ ] Real-time processing with streaming pipeline

## License

Part of IntelliCredits AI-Powered Credit Appraisal System
