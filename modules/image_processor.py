#!/usr/bin/env python3
"""
Image Processor Module

Handles screenshot capture, text recognition (OCR), and template matching
for finding UI elements within application windows.
"""

import os
import time
import tempfile
import subprocess
from typing import List, Tuple, Dict, Optional, Any, Union
import numpy as np

# Check for optional dependencies
try:
    import cv2
    HAVE_CV2 = True
except ImportError:
    HAVE_CV2 = False

try:
    from PIL import Image
    HAVE_PIL = True
except ImportError:
    HAVE_PIL = False

try:
    import pytesseract
    HAVE_TESSERACT = True
except ImportError:
    HAVE_TESSERACT = False

class ImageProcessor:
    """
    Handles image processing tasks like OCR and template matching.
    """
    
    def __init__(self, debug_mode: bool = False):
        """
        Initialize the image processor.
        
        Args:
            debug_mode: Whether to output debug information
        """
        self.debug_mode = debug_mode
        
        # Check for required dependencies
        self.has_ocr = HAVE_TESSERACT
        self.has_template_matching = HAVE_CV2
        self.has_screenshot = HAVE_PIL
        
        # Print capability information in debug mode
        if debug_mode:
            print("ImageProcessor capabilities:")
            print(f"- OCR: {'Available' if self.has_ocr else 'Not available (install pytesseract)'}")
            print(f"- Template matching: {'Available' if self.has_template_matching else 'Not available (install opencv-python)'}")
            print(f"- Screenshot: {'Available' if self.has_screenshot else 'Not available (install Pillow)'}")
    
    def capture_window_screenshot(self, window_id: int) -> Optional[Union[str, np.ndarray]]:
        """
        Capture a screenshot of a specific window.
        
        Args:
            window_id: X11 window ID
            
        Returns:
            Path to screenshot image or numpy array if opencv is available, None if failed
        """
        try:
            # Create a temporary file for the screenshot
            temp_file = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
            temp_file.close()
            screenshot_path = temp_file.name
            
            # Capture window using xwd and convert with imagemagick
            subprocess.run([
                "xwd", "-silent", "-id", str(window_id), "-out", "/tmp/window_temp.xwd"
            ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            subprocess.run([
                "convert", "/tmp/window_temp.xwd", screenshot_path
            ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            # Clean up the temporary xwd file
            if os.path.exists("/tmp/window_temp.xwd"):
                os.unlink("/tmp/window_temp.xwd")
            
            if not os.path.exists(screenshot_path):
                if self.debug_mode:
                    print("Screenshot capture failed: output file not created")
                return None
            
            # If opencv is available, load the image as a numpy array
            if self.has_template_matching:
                image = cv2.imread(screenshot_path)
                # Remove the temporary file since we have the array
                os.unlink(screenshot_path)
                return image
            else:
                # Return the path to the image file
                return screenshot_path
            
        except Exception as e:
            if self.debug_mode:
                print(f"Error capturing window screenshot: {e}")
            return None
    
    def find_text_in_screenshot(self, text: str, screenshot: Union[str, np.ndarray], 
                               min_confidence: float = 0.6) -> Optional[Tuple[int, int, float]]:
        """
        Find text in a screenshot using OCR.
        
        Args:
            text: Text to find
            screenshot: Path to screenshot image or numpy array
            min_confidence: Minimum confidence level for a match (0-1)
            
        Returns:
            Tuple of (x, y, confidence) for the best match, or None if no matches
        """
        if not self.has_ocr:
            if self.debug_mode:
                print("OCR not available. Install pytesseract.")
            return None
        
        try:
            # Load the image if it's a file path
            if isinstance(screenshot, str):
                image = Image.open(screenshot)
            else:
                # Convert from OpenCV format to PIL
                image = Image.fromarray(cv2.cvtColor(screenshot, cv2.COLOR_BGR2RGB))
            
            # Get OCR data with detailed info including coordinates
            ocr_data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
            
            # Process the OCR results
            best_match = None
            best_confidence = 0
            
            for i, word_text in enumerate(ocr_data['text']):
                # Skip empty results
                if not word_text.strip():
                    continue
                
                # Check confidence
                confidence = float(ocr_data['conf'][i]) / 100.0
                if confidence < min_confidence:
                    continue
                
                # Check for direct or fuzzy match
                if self._text_matches(word_text, text):
                    # Calculate center of the word
                    x = ocr_data['left'][i] + ocr_data['width'][i] // 2
                    y = ocr_data['top'][i] + ocr_data['height'][i] // 2
                    
                    if confidence > best_confidence:
                        best_confidence = confidence
                        best_match = (x, y, confidence)
                        
                    if self.debug_mode:
                        print(f"Text match: '{word_text}' at ({x}, {y}) with confidence {confidence:.2f}")
            
            return best_match
            
        except Exception as e:
            if self.debug_mode:
                print(f"Error finding text in screenshot: {e}")
            return None
    
    def _text_matches(self, found_text: str, target_text: str) -> bool:
        """
        Check if found text matches the target text, with some flexibility.
        
        Args:
            found_text: Text found in the image
            target_text: Text we're looking for
            
        Returns:
            Whether the texts match
        """
        # Convert both to lowercase for comparison
        found_lower = found_text.lower()
        target_lower = target_text.lower()
        
        # Direct match
        if found_lower == target_lower:
            return True
        
        # Check if found text contains target
        if target_lower in found_lower:
            return True
        
        # Split into parts and check for partial matches
        target_parts = target_lower.split()
        found_parts = found_lower.split()
        
        # Check if all target parts appear in the found text parts
        if all(part in found_parts for part in target_parts):
            return True
        
        # If we have multiple words, check for partial matches
        if len(target_parts) > 1 and len(found_parts) > 0:
            # Check for any word in target appearing in found text
            matching_parts = [part for part in target_parts if part in found_lower]
            if matching_parts:
                match_ratio = len(matching_parts) / len(target_parts)
                if self.debug_mode:
                    print(f"Partial match: '{found_text}' contains {len(matching_parts)}/{len(target_parts)} target words")
                
                # Return True if we match at least 70% of the words
                return match_ratio >= 0.7
        
        return False
    
    def find_template_in_screenshot(self, template_path: str, screenshot: Union[str, np.ndarray],
                                   threshold: float = 0.7) -> Optional[Tuple[int, int, float]]:
        """
        Find a template image in a screenshot using template matching.
        
        Args:
            template_path: Path to template image
            screenshot: Path to screenshot image or numpy array
            threshold: Minimum confidence threshold (0-1)
            
        Returns:
            Tuple of (x, y, confidence) for the best match, or None if no matches
        """
        if not self.has_template_matching:
            if self.debug_mode:
                print("Template matching not available. Install opencv-python.")
            return None
        
        try:
            # Load the template
            template = cv2.imread(template_path)
            if template is None:
                if self.debug_mode:
                    print(f"Could not load template image: {template_path}")
                return None
            
            # Load the screenshot if it's a file path
            if isinstance(screenshot, str):
                screenshot_img = cv2.imread(screenshot)
                if screenshot_img is None:
                    if self.debug_mode:
                        print(f"Could not load screenshot image: {screenshot}")
                    return None
            else:
                screenshot_img = screenshot
            
            # Get dimensions of template for later use
            h, w = template.shape[:2]
            
            # Perform template matching
            result = cv2.matchTemplate(screenshot_img, template, cv2.TM_CCOEFF_NORMED)
            
            # Find the best match location
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
            
            if self.debug_mode:
                print(f"Template match confidence: {max_val:.4f} (threshold: {threshold:.4f})")
            
            # Check if the match meets the threshold
            if max_val >= threshold:
                # Calculate the center point of the match
                x = max_loc[0] + w // 2
                y = max_loc[1] + h // 2
                
                if self.debug_mode:
                    print(f"Template match found at ({x}, {y}) with confidence {max_val:.4f}")
                
                return (x, y, max_val)
            else:
                if self.debug_mode:
                    print(f"No template match above threshold {threshold:.4f}")
                return None
            
        except Exception as e:
            if self.debug_mode:
                print(f"Error finding template in screenshot: {e}")
            return None
    
    def cleanup(self) -> None:
        """Clean up any resources or temporary files."""
        pass
