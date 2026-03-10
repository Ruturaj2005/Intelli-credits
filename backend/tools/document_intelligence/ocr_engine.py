"""
OCR Engine Module
Advanced OCR with layout detection using PaddleOCR.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)

# PaddleOCR will be imported dynamically to handle optional dependency
_paddle_ocr_instance = None


def _get_paddle_ocr():
    """Lazy load PaddleOCR to handle import errors gracefully."""
    global _paddle_ocr_instance
    
    if _paddle_ocr_instance is not None:
        return _paddle_ocr_instance
    
    try:
        from paddleocr import PaddleOCR
        
        # Initialize PaddleOCR with optimal settings for financial documents
        _paddle_ocr_instance = PaddleOCR(
            use_angle_cls=True,  # Enable angle classification for rotated text
            lang='en',  # English language
            show_log=False,  # Disable verbose logging
            use_gpu=False,  # Use CPU (set True if GPU available)
        )
        logger.info("PaddleOCR initialized successfully")
        return _paddle_ocr_instance
        
    except ImportError:
        logger.warning("PaddleOCR not installed. Falling back to basic OCR.")
        return None


def extract_with_ocr(
    images: List[np.ndarray],
    pdf_path: str = "",
) -> Dict[str, Any]:
    """
    Extract text, tables, and layout information from preprocessed images.
    
    Args:
        images: List of preprocessed images (numpy arrays)
        pdf_path: Original PDF path for reference
    
    Returns:
        Dictionary containing:
        - text_blocks: List of extracted text with bounding boxes
        - tables: Detected table regions
        - full_text: Complete extracted text
        - page_layouts: Layout information per page
        - confidence: Overall OCR confidence score
    """
    ocr_engine = _get_paddle_ocr()
    
    if ocr_engine is None:
        # Fallback to basic text extraction
        return _fallback_ocr(images, pdf_path)
    
    all_text_blocks = []
    all_tables = []
    full_text_parts = []
    page_layouts = []
    confidence_scores = []
    
    for page_num, img in enumerate(images, 1):
        logger.info(f"Running OCR on page {page_num}/{len(images)}")
        
        try:
            # Run PaddleOCR
            result = ocr_engine.ocr(img, cls=True)
            
            if not result or not result[0]:
                logger.warning(f"No OCR results for page {page_num}")
                continue
            
            # Process OCR results
            page_blocks = []
            page_text_parts = []
            
            for line in result[0]:
                bbox = line[0]  # Bounding box coordinates
                text_info = line[1]  # (text, confidence)
                text = text_info[0]
                confidence = text_info[1]
                
                # Create structured text block
                text_block = {
                    "text": text,
                    "bbox": bbox,
                    "confidence": confidence,
                    "page": page_num,
                }
                page_blocks.append(text_block)
                page_text_parts.append(text)
                confidence_scores.append(confidence)
            
            all_text_blocks.extend(page_blocks)
            full_text_parts.append("\n".join(page_text_parts))
            
            # Detect tables based on layout patterns
            tables = _detect_tables_from_layout(page_blocks, page_num)
            all_tables.extend(tables)
            
            # Analyze page layout
            layout = _analyze_page_layout(page_blocks, img.shape)
            page_layouts.append(layout)
            
        except Exception as e:
            logger.error(f"OCR error on page {page_num}: {e}")
            continue
    
    # Calculate overall confidence
    avg_confidence = np.mean(confidence_scores) if confidence_scores else 0.0
    
    return {
        "text_blocks": all_text_blocks,
        "tables": all_tables,
        "full_text": "\n\n".join(full_text_parts),
        "page_layouts": page_layouts,
        "confidence": float(avg_confidence),
        "total_pages": len(images),
        "source": pdf_path,
    }


def _detect_tables_from_layout(
    text_blocks: List[Dict[str, Any]],
    page_num: int
) -> List[Dict[str, Any]]:
    """
    Detect table regions based on text block alignment patterns.
    
    Tables typically have:
    - Multiple text blocks aligned vertically and horizontally
    - Regular spacing patterns
    - Consistent column structure
    """
    if len(text_blocks) < 4:
        return []
    
    tables = []
    
    # Group blocks by vertical position (rows)
    rows = _group_by_rows(text_blocks)
    
    # Identify table regions
    table_rows = []
    for row in rows:
        if len(row) >= 2:  # At least 2 columns
            # Check if columns are regularly spaced
            if _is_table_row(row):
                table_rows.append(row)
        elif table_rows:
            # End of table region
            if len(table_rows) >= 3:  # At least 3 rows for a valid table
                table = _create_table_structure(table_rows, page_num)
                tables.append(table)
            table_rows = []
    
    # Catch final table
    if len(table_rows) >= 3:
        table = _create_table_structure(table_rows, page_num)
        tables.append(table)
    
    return tables


def _group_by_rows(text_blocks: List[Dict[str, Any]], threshold: float = 10.0) -> List[List[Dict]]:
    """
    Group text blocks into rows based on vertical position.
    """
    if not text_blocks:
        return []
    
    # Sort by vertical position (top of bounding box)
    sorted_blocks = sorted(text_blocks, key=lambda b: b["bbox"][0][1])
    
    rows = []
    current_row = [sorted_blocks[0]]
    current_y = sorted_blocks[0]["bbox"][0][1]
    
    for block in sorted_blocks[1:]:
        block_y = block["bbox"][0][1]
        
        if abs(block_y - current_y) < threshold:
            # Same row
            current_row.append(block)
        else:
            # New row
            # Sort current row by horizontal position
            current_row.sort(key=lambda b: b["bbox"][0][0])
            rows.append(current_row)
            current_row = [block]
            current_y = block_y
    
    # Add last row
    if current_row:
        current_row.sort(key=lambda b: b["bbox"][0][0])
        rows.append(current_row)
    
    return rows


def _is_table_row(row: List[Dict[str, Any]]) -> bool:
    """
    Check if a row of text blocks represents a table row.
    """
    if len(row) < 2:
        return False
    
    # Check if blocks are evenly spaced (indication of table columns)
    x_positions = [block["bbox"][0][0] for block in row]
    spacings = [x_positions[i+1] - x_positions[i] for i in range(len(x_positions)-1)]
    
    if not spacings:
        return False
    
    # Check spacing variance
    avg_spacing = np.mean(spacings)
    spacing_variance = np.std(spacings)
    
    # Low variance indicates regular column structure
    return spacing_variance < avg_spacing * 0.5


def _create_table_structure(
    table_rows: List[List[Dict[str, Any]]],
    page_num: int
) -> Dict[str, Any]:
    """
    Create structured table from grouped rows.
    """
    # Extract cell values in grid format
    num_cols = max(len(row) for row in table_rows)
    
    grid = []
    for row in table_rows:
        grid_row = [block["text"] for block in row]
        # Pad short rows
        while len(grid_row) < num_cols:
            grid_row.append("")
        grid.append(grid_row)
    
    # Determine table bounding box
    all_blocks = [block for row in table_rows for block in row]
    min_x = min(block["bbox"][0][0] for block in all_blocks)
    min_y = min(block["bbox"][0][1] for block in all_blocks)
    max_x = max(block["bbox"][2][0] for block in all_blocks)
    max_y = max(block["bbox"][2][1] for block in all_blocks)
    
    return {
        "type": "table",
        "page": page_num,
        "bbox": [[min_x, min_y], [max_x, min_y], [max_x, max_y], [min_x, max_y]],
        "rows": len(grid),
        "cols": num_cols,
        "grid": grid,
        "header": grid[0] if grid else [],
    }


def _analyze_page_layout(
    text_blocks: List[Dict[str, Any]],
    image_shape: Tuple[int, int]
) -> Dict[str, Any]:
    """
    Analyze overall page layout structure.
    """
    if not text_blocks:
        return {"layout_type": "empty", "regions": []}
    
    height, width = image_shape[:2]
    
    # Classify layout type based on text distribution
    avg_y = np.mean([block["bbox"][0][1] for block in text_blocks])
    
    layout_type = "single_column"
    if len(text_blocks) > 10:
        # Check for multi-column layout
        left_blocks = [b for b in text_blocks if b["bbox"][0][0] < width / 2]
        right_blocks = [b for b in text_blocks if b["bbox"][0][0] >= width / 2]
        
        if len(left_blocks) > 3 and len(right_blocks) > 3:
            layout_type = "two_column"
    
    return {
        "layout_type": layout_type,
        "width": width,
        "height": height,
        "text_block_count": len(text_blocks),
        "avg_confidence": np.mean([b["confidence"] for b in text_blocks]),
    }


def _fallback_ocr(images: List[np.ndarray], pdf_path: str) -> Dict[str, Any]:
    """
    Fallback OCR using pytesseract when PaddleOCR is not available.
    """
    logger.warning("Using fallback OCR (Tesseract)")
    
    try:
        import pytesseract
        from PIL import Image
        
        all_text = []
        for page_num, img in enumerate(images, 1):
            # Convert numpy array to PIL Image
            pil_img = Image.fromarray(img)
            
            # Extract text
            text = pytesseract.image_to_string(pil_img)
            all_text.append(text)
        
        full_text = "\n\n".join(all_text)
        
        return {
            "text_blocks": [],
            "tables": [],
            "full_text": full_text,
            "page_layouts": [],
            "confidence": 0.7,  # Default confidence for fallback
            "total_pages": len(images),
            "source": pdf_path,
        }
        
    except ImportError:
        logger.error("Neither PaddleOCR nor Tesseract available")
        return {
            "text_blocks": [],
            "tables": [],
            "full_text": "",
            "page_layouts": [],
            "confidence": 0.0,
            "total_pages": len(images),
            "source": pdf_path,
        }
