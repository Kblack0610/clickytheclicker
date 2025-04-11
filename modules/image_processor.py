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
    
    def capture_window_screenshot(self, window_id: int) -> Optional[Union[str, np.ndarray, 'Image.Image']]:
        """
        Capture a screenshot of a specific window.
        
        Args:
            window_id: X11 window ID
            
        Returns:
            PIL Image object, numpy array, or path to image file depending on available libraries
            None if capture failed
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
            
            # Prioritize PIL Image for better compatibility with various operations
            if HAVE_PIL:
                try:
                    image = Image.open(screenshot_path)
                    # Keep a copy in memory before removing the file
                    image_copy = image.copy()
                    os.unlink(screenshot_path)
                    return image_copy
                except Exception as e:
                    if self.debug_mode:
                        print(f"Error loading with PIL: {e}")
                    # Continue to try with OpenCV if PIL fails
            
            # If opencv is available, load the image as a numpy array
            if self.has_template_matching:
                try:
                    image = cv2.imread(screenshot_path)
                    # Remove the temporary file since we have the array
                    os.unlink(screenshot_path)
                    
                    # Convert OpenCV BGR to PIL RGB Image if PIL is available for better compatibility
                    if HAVE_PIL:
                        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
                        return Image.fromarray(image_rgb)
                    return image
                except Exception as e:
                    if self.debug_mode:
                        print(f"Error loading with OpenCV: {e}")
            
            # If we reach here, we couldn't load with PIL or OpenCV, but the file exists
            if os.path.exists(screenshot_path):
                # Return the path to the image file as a last resort
                return screenshot_path
            
            return None
            
        except Exception as e:
            if self.debug_mode:
                print(f"Error capturing window screenshot: {e}")
            return None
    
    def find_text_in_screenshot(self, text: str, screenshot: Union[str, np.ndarray, 'Image.Image'], 
                               min_confidence: float = 0.5) -> Optional[Tuple[int, int, float]]:
        """
        Find text in a screenshot using OCR with enhanced preprocessing.
        
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
            # Store the original text for debugging
            original_text = text
            # Create a debug directory
            debug_dir = "/tmp/clicky_debug"
            if self.debug_mode:
                os.makedirs(debug_dir, exist_ok=True)
                debug_time = int(time.time())
        
            # Load and prepare the image
            pil_image = None
            np_image = None
            
            # Handle different input types
            if isinstance(screenshot, str):
                if os.path.exists(screenshot):
                    pil_image = Image.open(screenshot)
                else:
                    if self.debug_mode:
                        print(f"Screenshot file not found: {screenshot}")
                    return None
            elif isinstance(screenshot, np.ndarray):
                np_image = screenshot
                # Convert BGR to RGB if needed
                if len(np_image.shape) == 3 and np_image.shape[2] == 3:
                    np_image_rgb = cv2.cvtColor(np_image, cv2.COLOR_BGR2RGB)
                    pil_image = Image.fromarray(np_image_rgb)
                else:
                    pil_image = Image.fromarray(np_image)
            elif HAVE_PIL and isinstance(screenshot, Image.Image):
                pil_image = screenshot
            else:
                if self.debug_mode:
                    print(f"Unsupported screenshot type: {type(screenshot)}")
                return None
            
            # Save the original image for debugging
            if self.debug_mode:
                original_path = f"{debug_dir}/original_{debug_time}.png"
                pil_image.save(original_path)
                print(f"Saved original image to {original_path}")
            
            # Create a list of processed images with different filters for better OCR
            processed_images = []
            
            # Original image (always include first)
            processed_images.append(("original", pil_image))
            
            # Get numpy representation for transformations if needed
            if np_image is None and self.has_template_matching:
                np_image = np.array(pil_image)
                
            # Only apply these transformations if we have OpenCV available
            if self.has_template_matching:
                # Convert to grayscale
                gray = cv2.cvtColor(np_image, cv2.COLOR_RGB2GRAY) if len(np_image.shape) == 3 else np_image
                
                # Apply different thresholds for better text detection
                _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
                processed_images.append(("binary", Image.fromarray(binary)))
                
                # Inverted binary (for white text on dark backgrounds)
                inverted = cv2.bitwise_not(binary)
                processed_images.append(("inverted", Image.fromarray(inverted)))
                
                # Adaptive threshold (better for varying backgrounds)
                adaptive = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
                processed_images.append(("adaptive", Image.fromarray(adaptive)))
                
            # Debug log the processing steps
            if self.debug_mode:
                print(f"Looking for text: '{text}'")
                print(f"Created {len(processed_images)} image variations for OCR processing")
                
                # Save all processed images
                for name, img in processed_images:
                    img_path = f"{debug_dir}/{name}_{debug_time}.png"
                    img.save(img_path)
                    print(f"Saved {name} image to {img_path}")
            
            # Try different OCR configurations with all processed images
            ocr_configs = [
                "",  # Default configuration
                "--psm 6",  # Assume single block of text
                "--psm 11 --oem 1"  # Sparse text detection
            ]
            
            # Store all detected text blocks from all processing attempts
            all_blocks = []
            for proc_name, proc_image in processed_images:
                for config in ocr_configs:
                    try:
                        # Run OCR on this processed image with this config
                        ocr_data = pytesseract.image_to_data(proc_image, output_type=pytesseract.Output.DICT, config=config)
                        
                        # Extract and store text blocks with positions
                        for i, detected_text in enumerate(ocr_data['text']):
                            # Skip empty results
                            if not detected_text.strip():
                                continue
                            
                            # Get confidence and position
                            conf = float(ocr_data['conf'][i]) / 100.0
                            if conf < 0.2:  # Filter extremely low confidence to reduce noise
                                continue
                                
                            # Get position and size
                            x = ocr_data['left'][i]
                            y = ocr_data['top'][i]
                            w = ocr_data['width'][i]
                            h = ocr_data['height'][i]
                            
                            # Add to our block collection
                            all_blocks.append({
                                'text': detected_text.strip(),
                                'x': x,
                                'y': y,
                                'width': w,
                                'height': h,
                                'conf': conf,
                                'source': f"{proc_name}_{config}"
                            })
                            
                            if self.debug_mode and conf > 0.3:
                                print(f"Detected: '{detected_text}' at ({x}, {y}) with conf {conf:.2f} [{proc_name} {config}]")
                    except Exception as e:
                        if self.debug_mode:
                            print(f"OCR error with {proc_name} using config '{config}': {e}")
            
            # Sort all blocks by confidence (highest first)
            all_blocks.sort(key=lambda b: b['conf'], reverse=True)
            
            # ===== Try different matching strategies =====
            # 1. Direct text matches (exact or fuzzy)
            direct_matches = []
            for block in all_blocks:
                if self._text_matches(block['text'], text):
                    # Calculate center of the text block
                    x = block['x'] + block['width'] // 2
                    y = block['y'] + block['height'] // 2
                    direct_matches.append({
                        'x': x, 
                        'y': y, 
                        'conf': block['conf'],
                        'text': block['text'],
                        'source': block['source']
                    })
            
            if direct_matches:
                # Take the match with highest confidence
                best_match = direct_matches[0]
                if self.debug_mode:
                    print(f"Found direct match: '{best_match['text']}' at ({best_match['x']}, {best_match['y']}) "  
                          f"with conf {best_match['conf']:.2f} [{best_match['source']}]")
                return (best_match['x'], best_match['y'], best_match['conf'])
                
            # 2. Partial word matching for multi-word text
            if ' ' in text:
                # Tokenize the search text into words
                search_parts = text.lower().split()
                if self.debug_mode:
                    print(f"Searching for words: {search_parts}")
                
                # Track which blocks match which search parts
                word_matches = {}
                for block in all_blocks:
                    block_text = block['text'].lower()
                    # Check each search word against this block
                    for word in search_parts:
                        # Use improved text matching for fuzzy comparison
                        if self._text_matches(block_text, word, fuzzy_threshold=0.8) or word in block_text:
                            if word not in word_matches or block['conf'] > word_matches[word]['conf']:
                                word_matches[word] = block
                
                # Find how many words we matched and their quality
                matched_words = list(word_matches.keys())
                matched_word_pct = len(matched_words) / len(search_parts)
                
                if self.debug_mode:
                    print(f"Matched {len(matched_words)}/{len(search_parts)} words: {matched_words}")
                
                # If we matched at least 50% of the words, consider it a match
                if matched_word_pct >= 0.5:
                    # Find the center of the matched blocks
                    blocks = list(word_matches.values())
                    min_x = min(b['x'] for b in blocks)
                    max_x = max(b['x'] + b['width'] for b in blocks)
                    min_y = min(b['y'] for b in blocks)
                    max_y = max(b['y'] + b['height'] for b in blocks)
                    
                    center_x = min_x + (max_x - min_x) // 2
                    center_y = min_y + (max_y - min_y) // 2
                    
                    # Calculate overall match quality
                    avg_conf = sum(b['conf'] for b in blocks) / len(blocks)
                    quality = matched_word_pct * avg_conf
                    
                    if self.debug_mode:
                        print(f"Found partial match for '{original_text}' at ({center_x}, {center_y})")
                        print(f"  Quality: {quality:.2f} (words: {matched_word_pct:.2f}, conf: {avg_conf:.2f})")
                    
                    return (center_x, center_y, quality)
            
            # No matches found
            if self.debug_mode:
                print(f"No matches found for '{text}'")
            return None
            
        except Exception as e:
            if self.debug_mode:
                print(f"Error finding text in screenshot: {e}")
                import traceback
                traceback.print_exc()
            return None
    
    def _text_matches(self, found_text: str, target_text: str, fuzzy_threshold: float = 0.75) -> bool:
        """
        Check if found text matches the target text, with some flexibility.
        
        Args:
            found_text: Text found in the image
            target_text: Text we're looking for
            fuzzy_threshold: Threshold for fuzzy matching (0.0 to 1.0)
            
        Returns:
            Whether the texts match
        """
        import re
        from difflib import SequenceMatcher
        
        # Skip empty texts
        if not found_text or not target_text:
            return False
        
        # Convert both to lowercase for case-insensitive matching
        found_lower = found_text.lower()
        target_lower = target_text.lower()
        
        # 1. Check for exact match (ignoring case)
        if found_lower == target_lower:
            return True
        
        # 2. Check for substring match
        if target_lower in found_lower:
            return True
            
        # 3. Allow for common OCR errors and fuzzy matching
        # Remove non-alphanumeric characters and whitespace
        found_clean = re.sub(r'[^a-z0-9]', '', found_lower)
        target_clean = re.sub(r'[^a-z0-9]', '', target_lower)
        
        # Handle empty strings after cleaning
        if not found_clean or not target_clean:
            return False
            
        # Fuzzy matching for similar but not identical text
        similarity = SequenceMatcher(None, found_clean, target_clean).ratio()
        if similarity >= fuzzy_threshold:
            return True
            
        return False
        
    def get_all_text_regions(self, screenshot: Union[str, np.ndarray, 'Image.Image'], 
                           min_confidence: float = 0.3) -> List[Tuple[str, int, int, float]]:
        """
        Get all text regions in the screenshot with at least the minimum confidence.
        
        Args:
            screenshot: Path to screenshot image or numpy array
            min_confidence: Minimum confidence level (0-1)
            
        Returns:
            List of tuples (text, x, y, confidence) for each text region
        """
        if not self.has_ocr:
            return []
            
        # Process the image using the same code as in find_text_in_screenshot
        pil_image = None
        
        if isinstance(screenshot, str):
            if os.path.exists(screenshot):
                pil_image = Image.open(screenshot)
            else:
                return []
        elif isinstance(screenshot, np.ndarray):
            np_image = screenshot
            # Convert BGR to RGB if needed
            if len(np_image.shape) == 3 and np_image.shape[2] == 3:
                np_image_rgb = cv2.cvtColor(np_image, cv2.COLOR_BGR2RGB)
                pil_image = Image.fromarray(np_image_rgb)
            else:
                pil_image = Image.fromarray(np_image)
        elif HAVE_PIL and isinstance(screenshot, Image.Image):
            pil_image = screenshot
        else:
            return []
            
        # Get all text from the image
        results = []
        
        try:
            # Use multiple OCR configurations for better results
            ocr_configs = ["", "--psm 6", "--psm 11 --oem 1"]
            
            for config in ocr_configs:
                ocr_data = pytesseract.image_to_data(pil_image, output_type=pytesseract.Output.DICT, config=config)
                
                for i, text in enumerate(ocr_data['text']):
                    if not text.strip():
                        continue
                        
                    conf = float(ocr_data['conf'][i]) / 100.0
                    if conf < min_confidence:
                        continue
                        
                    x = ocr_data['left'][i] + ocr_data['width'][i] // 2
                    y = ocr_data['top'][i] + ocr_data['height'][i] // 2
                    
                    results.append((text.strip(), x, y, conf))
        except Exception as e:
            if self.debug_mode:
                print(f"Error getting all text regions: {e}")
                
        return results
    
    def find_template_in_screenshot(self, template_path: str, screenshot: Union[str, np.ndarray], 
                                    threshold: float = 0.7) -> Optional[Tuple[int, int, float]]:
        """
        Find a template image in a screenshot using template matching.
        
        Args:
            template_path: Path to template image
            screenshot: Path to screenshot image or numpy array
            threshold: Minimum confidence level for a match (0-1)
            
        Returns:
            Tuple of (x, y, confidence) for the best match, or None if no matches
        """
        if not self.has_template_matching:
            if self.debug_mode:
                print("Template matching not available. Install OpenCV.")
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