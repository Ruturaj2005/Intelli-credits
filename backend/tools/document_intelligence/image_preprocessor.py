"""
Image Preprocessing Module
Cleans messy scanned documents before OCR using OpenCV techniques.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import List, Tuple

import cv2
import numpy as np
from pdf2image import convert_from_path
from PIL import Image

logger = logging.getLogger(__name__)


def preprocess_pdf_pages(pdf_path: str, dpi: int = 300) -> List[np.ndarray]:
    """
    Convert PDF to images and preprocess each page for optimal OCR.
    
    Args:
        pdf_path: Path to PDF file
        dpi: Resolution for PDF to image conversion (default 300 for quality OCR)
    
    Returns:
        List of preprocessed images as numpy arrays
    """
    try:
        # Convert PDF pages to images
        logger.info(f"Converting PDF to images: {pdf_path}")
        pil_images = convert_from_path(pdf_path, dpi=dpi)
        
        preprocessed_images = []
        for page_num, pil_image in enumerate(pil_images, 1):
            logger.info(f"Preprocessing page {page_num}/{len(pil_images)}")
            
            # Convert PIL to OpenCV format
            img_array = np.array(pil_image)
            img = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
            
            # Apply preprocessing pipeline
            cleaned_img = _clean_image(img)
            preprocessed_images.append(cleaned_img)
        
        logger.info(f"Successfully preprocessed {len(preprocessed_images)} pages")
        return preprocessed_images
        
    except Exception as e:
        logger.error(f"Error preprocessing PDF: {e}")
        return []


def _clean_image(img: np.ndarray) -> np.ndarray:
    """
    Apply comprehensive cleaning pipeline to a single image.
    
    Pipeline:
    1. Deskew (straighten rotated pages)
    2. Convert to grayscale
    3. Noise removal
    4. Contrast enhancement
    5. Adaptive thresholding
    """
    # Step 1: Deskew the image
    img = _deskew_image(img)
    
    # Step 2: Convert to grayscale
    if len(img.shape) == 3:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    else:
        gray = img
    
    # Step 3: Noise removal with median blur
    denoised = cv2.medianBlur(gray, 3)
    
    # Step 4: Contrast enhancement using CLAHE
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(denoised)
    
    # Step 5: Adaptive thresholding for better OCR
    # Use binary threshold with Otsu's method
    _, binary = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    
    return binary


def _deskew_image(img: np.ndarray) -> np.ndarray:
    """
    Automatically detect and correct skew/rotation in scanned documents.
    
    Uses Hough Line Transform to detect dominant text lines and calculate skew angle.
    """
    # Convert to grayscale if needed
    if len(img.shape) == 3:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    else:
        gray = img.copy()
    
    # Apply edge detection
    edges = cv2.Canny(gray, 50, 150, apertureSize=3)
    
    # Detect lines using Hough Transform
    lines = cv2.HoughLinesP(
        edges, 
        rho=1, 
        theta=np.pi/180, 
        threshold=100,
        minLineLength=100,
        maxLineGap=10
    )
    
    if lines is None or len(lines) == 0:
        return img
    
    # Calculate angles of all detected lines
    angles = []
    for line in lines:
        x1, y1, x2, y2 = line[0]
        angle = np.degrees(np.arctan2(y2 - y1, x2 - x1))
        angles.append(angle)
    
    if not angles:
        return img
    
    # Calculate median angle (more robust than mean)
    median_angle = np.median(angles)
    
    # Only deskew if angle is significant (> 0.5 degrees)
    if abs(median_angle) < 0.5:
        return img
    
    # Rotate image to correct skew
    height, width = img.shape[:2]
    center = (width // 2, height // 2)
    rotation_matrix = cv2.getRotationMatrix2D(center, median_angle, 1.0)
    
    # Calculate new bounding dimensions
    cos = np.abs(rotation_matrix[0, 0])
    sin = np.abs(rotation_matrix[0, 1])
    new_width = int((height * sin) + (width * cos))
    new_height = int((height * cos) + (width * sin))
    
    # Adjust rotation matrix for new dimensions
    rotation_matrix[0, 2] += (new_width / 2) - center[0]
    rotation_matrix[1, 2] += (new_height / 2) - center[1]
    
    # Perform rotation with white background
    rotated = cv2.warpAffine(
        img, 
        rotation_matrix, 
        (new_width, new_height),
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=(255, 255, 255)
    )
    
    logger.debug(f"Deskewed image by {median_angle:.2f} degrees")
    return rotated


def _detect_page_rotation(img: np.ndarray) -> int:
    """
    Detect if page is rotated 90, 180, or 270 degrees.
    
    Returns rotation angle needed to correct (0, 90, 180, or 270).
    """
    # Convert to grayscale
    if len(img.shape) == 3:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    else:
        gray = img
    
    # Apply edge detection
    edges = cv2.Canny(gray, 50, 150)
    
    # Detect lines
    lines = cv2.HoughLinesP(
        edges,
        rho=1,
        theta=np.pi/180,
        threshold=100,
        minLineLength=100,
        maxLineGap=10
    )
    
    if lines is None or len(lines) == 0:
        return 0
    
    # Count predominantly horizontal vs vertical lines
    horizontal_count = 0
    vertical_count = 0
    
    for line in lines:
        x1, y1, x2, y2 = line[0]
        angle = abs(np.degrees(np.arctan2(y2 - y1, x2 - x1)))
        
        if angle < 45 or angle > 135:
            horizontal_count += 1
        else:
            vertical_count += 1
    
    # If more vertical lines than horizontal, page might be rotated 90/270
    if vertical_count > horizontal_count * 1.5:
        # Check aspect ratio to determine 90 or 270
        height, width = gray.shape
        if height > width:
            return 90
        else:
            return 270
    
    return 0


def enhance_contrast(img: np.ndarray) -> np.ndarray:
    """
    Enhance contrast for low-quality scans.
    """
    if len(img.shape) == 3:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    else:
        gray = img
    
    # Apply histogram equalization
    enhanced = cv2.equalizeHist(gray)
    return enhanced


def remove_shadows(img: np.ndarray) -> np.ndarray:
    """
    Remove shadows and uneven illumination from scanned documents.
    """
    if len(img.shape) == 3:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    else:
        gray = img
    
    # Dilate to create background mask
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (7, 7))
    dilated = cv2.dilate(gray, kernel, iterations=3)
    
    # Apply median blur to background
    background = cv2.medianBlur(dilated, 21)
    
    # Subtract background from original
    diff = 255 - cv2.absdiff(gray, background)
    
    # Normalize
    normalized = cv2.normalize(diff, None, alpha=0, beta=255, norm_type=cv2.NORM_MINMAX)
    
    return normalized


def save_preprocessed_images(images: List[np.ndarray], output_dir: str, base_name: str) -> List[str]:
    """
    Save preprocessed images to disk for inspection or further processing.
    
    Returns:
        List of saved file paths
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    saved_paths = []
    for idx, img in enumerate(images, 1):
        filename = f"{base_name}_page_{idx:03d}.png"
        filepath = output_path / filename
        cv2.imwrite(str(filepath), img)
        saved_paths.append(str(filepath))
        logger.debug(f"Saved preprocessed image: {filepath}")
    
    return saved_paths
