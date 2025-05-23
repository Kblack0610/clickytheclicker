#!/usr/bin/env python3
"""
Smart XTest Autoclicker - Automatically find and click UI elements in windows

This enhanced version of the XTest autoclicker can:
1. Take screenshots of target windows
2. Recognize text and UI elements
3. Automatically click based on found elements
4. Execute keyboard actions
"""

import argparse
import time
import sys
import subprocess
import random
import os
import json
import re
import datetime
from typing import Tuple, Optional, List, Dict, Any, Union

try:
    from Xlib import display, X
    from Xlib.ext import xtest
    import numpy as np
    from PIL import Image, ImageGrab
    import pytesseract
    import cv2
except ImportError:
    print("Required dependencies not found. Installing...")
    subprocess.call([sys.executable, "-m", "pip", "install", "python-xlib", "pillow", "pytesseract", "opencv-python", "numpy"])
    from Xlib import display, X
    from Xlib.ext import xtest
    import numpy as np
    from PIL import Image, ImageGrab
    import pytesseract
    import cv2

# Default Tesseract path - change if necessary
TESSERACT_CMD = 'tesseract'
try:
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD
except Exception:
    print(f"Warning: Could not set tesseract path to {TESSERACT_CMD}")
    print("If OCR fails, install tesseract or set the correct path.")

class SmartAutoclicker:
    def __init__(self):
        self.display = display.Display()
        self.root = self.display.screen().root
        self.selected_window = None
        self.window_geometry = None
        self.is_running = False
        self.click_interval = 1.0  # Default: 1 second between clicks
        self.actions = []  # List of automation actions
        self.current_screenshot = None
        self.debug_mode = False
        self.retry_count = 0  # Default: try each action once (0 retries)
        self.activate_window = True
        self.config_file = None
        self.continuous_mode = False  # Flag for continuous mode
        
    def select_window_by_click(self):
        """Prompt user to click on a window to select it"""
        print("Click on the window you want to automate (you have 3 seconds)...")
        time.sleep(3)
        
        try:
            # Use xdotool to get the window ID under the cursor
            result = subprocess.run(["xdotool", "getmouselocation", "--shell"], 
                                  capture_output=True, text=True, check=True)
            
            window_id = None
            for line in result.stdout.splitlines():
                if line.startswith("WINDOW="):
                    try:
                        window_id_str = line.split("=")[1]
                        # Handle both decimal and hex formats
                        if window_id_str.startswith("0x"):
                            window_id = int(window_id_str, 16)
                        else:
                            window_id = int(window_id_str)
                        break
                    except (ValueError, IndexError):
                        pass
            
            if window_id:
                self.selected_window = window_id
                window_name = self.get_window_name(window_id)
                print(f"Selected window: {window_name} (id: {window_id:x})")
                
                # Try different methods to get window geometry for i3
                geometry_methods = [
                    self.get_window_geometry,
                    self.get_window_geometry_alternative
                ]
                
                for method in geometry_methods:
                    self.window_geometry = method(window_id)
                    if self.window_geometry:
                        x, y, width, height = self.window_geometry
                        print(f"Window geometry: x={x}, y={y}, width={width}, height={height}")
                        return True
                
                # If we couldn't get the geometry, try a fallback method
                print("Warning: Could not determine window geometry using standard methods.")
                print("Attempting fallback method for i3 window manager...")
                
                # For i3, we can try to get the active window size
                self.window_geometry = self.get_i3_window_geometry(window_id)
                if self.window_geometry:
                    x, y, width, height = self.window_geometry
                    print(f"Window geometry (i3 fallback): x={x}, y={y}, width={width}, height={height}")
                    return True
                    
                # Last resort: ask user for manual confirmation
                print("Could not automatically determine window geometry.")
                confirm = input("Do you want to continue anyway? This may affect click accuracy. (y/n): ")
                if confirm.lower() == 'y':
                    # Use screen dimensions as fallback
                    screen = self.display.screen()
                    self.window_geometry = (0, 0, screen.width_in_pixels, screen.height_in_pixels)
                    print(f"Using screen dimensions as fallback: {self.window_geometry}")
                    return True
        except subprocess.SubprocessError as e:
            print(f"Error running xdotool: {e}")
            
        print("Failed to select window. Please try again.")
        return False
        
    def get_window_geometry_alternative(self, window_id):
        """Alternative method to get window geometry, useful for i3 and other tiling WMs"""
        try:
            # Try using xwininfo
            result = subprocess.run(["xwininfo", "-id", str(window_id)], 
                                 capture_output=True, text=True, check=True)
            
            x, y, width, height = None, None, None, None
            for line in result.stdout.splitlines():
                if "Absolute upper-left X:" in line:
                    x = int(line.split(":")[-1].strip())
                elif "Absolute upper-left Y:" in line:
                    y = int(line.split(":")[-1].strip())
                elif "Width:" in line:
                    width = int(line.split(":")[-1].strip())
                elif "Height:" in line:
                    height = int(line.split(":")[-1].strip())
            
            if all(v is not None for v in [x, y, width, height]):
                return (x, y, width, height)
        except (subprocess.SubprocessError, ValueError, IndexError) as e:
            print(f"Alternative geometry method failed: {e}")
            
        return None
    
    def get_i3_window_geometry(self, window_id):
        """Get window geometry specifically for i3 window manager"""
        try:
            # Try using i3-msg to get window position
            result = subprocess.run(["i3-msg", "-t", "get_tree"], 
                                 capture_output=True, text=True, check=True)
            
            import json
            tree = json.loads(result.stdout)
            
            # Function to recursively search for window
            def find_window(node, target_id):
                if node.get('window') == target_id:
                    rect = node.get('rect', {})
                    return (rect.get('x', 0), rect.get('y', 0), 
                            rect.get('width', 0), rect.get('height', 0))
                
                for child in node.get('nodes', []) + node.get('floating_nodes', []):
                    result = find_window(child, target_id)
                    if result:
                        return result
                return None
            
            # Search for window in i3 tree
            geometry = find_window(tree, window_id)
            if geometry and all(v > 0 for v in geometry[2:]):
                return geometry
            
        except (subprocess.SubprocessError, json.JSONDecodeError) as e:
            print(f"i3 geometry method failed: {e}")
            
        return None
        
    def select_window_by_name(self, window_name):
        """Select a window by its name/title"""
        try:
            result = subprocess.run(["xdotool", "search", "--name", window_name], 
                                  capture_output=True, text=True, check=True)
            
            if result.stdout.strip():
                window_ids = result.stdout.strip().split("\n")
                if window_ids:
                    window_id = int(window_ids[0])
                    self.selected_window = window_id
                    print(f"Selected window: {window_name} (id: {window_id:x})")
                    
                    # Get window geometry
                    self.window_geometry = self.get_window_geometry(window_id)
                    if self.window_geometry:
                        x, y, width, height = self.window_geometry
                        print(f"Window geometry: x={x}, y={y}, width={width}, height={height}")
                        return True
        except (subprocess.SubprocessError, ValueError) as e:
            print(f"Error selecting window by name: {e}")
            
        print(f"Failed to find window with name: {window_name}")
        return False
    
    def get_window_name(self, window_id):
        """Get the window name from its ID"""
        try:
            result = subprocess.run(["xdotool", "getwindowname", str(window_id)], 
                                  capture_output=True, text=True, check=True)
            return result.stdout.strip()
        except subprocess.SubprocessError:
            return "Unknown"
    
    def get_window_geometry(self, window_id):
        """Get the geometry (position and size) of a window"""
        try:
            result = subprocess.run(["xdotool", "getwindowgeometry", "--shell", str(window_id)], 
                                  capture_output=True, text=True, check=True)
            
            x, y, width, height = None, None, None, None
            for line in result.stdout.splitlines():
                if line.startswith("X="):
                    x = int(line.split("=")[1])
                elif line.startswith("Y="):
                    y = int(line.split("=")[1])
                elif line.startswith("WIDTH="):
                    width = int(line.split("=")[1])
                elif line.startswith("HEIGHT="):
                    height = int(line.split("=")[1])
            
            if all(v is not None for v in [x, y, width, height]):
                return (x, y, width, height)
        except (subprocess.SubprocessError, ValueError, IndexError):
            pass
            
        return None
    
    def send_click_event(self, x, y, button=1):
        """Send a synthetic click event using XTest at absolute coordinates without moving the real cursor"""
        try:
            # IMPORTANT: Do NOT use MotionNotify as it moves the actual cursor
            # Instead, pass coordinates directly to button events
            
            # Simulate mouse down and up (click)
            if self.debug_mode:
                print(f"Sending click at absolute coordinates: ({x}, {y})")
                
            xtest.fake_input(self.display, X.ButtonPress, button, x=x, y=y)
            self.display.sync()
            time.sleep(0.15)  # Longer delay between press and release
            xtest.fake_input(self.display, X.ButtonRelease, button, x=x, y=y)
            self.display.sync()
            
            # Additional time for processing
            time.sleep(0.1)
            
            if self.debug_mode:
                print(f"Sent synthetic click at ({x}, {y}) without moving cursor")
            
            return True
        except Exception as e:
            print(f"Error sending XTest click event: {e}")
            return False
            
    def send_key_event(self, keycode):
        """Send a synthetic keyboard event using XTest"""
        try:
            # Key press and release
            xtest.fake_input(self.display, X.KeyPress, keycode)
            xtest.fake_input(self.display, X.KeyRelease, keycode)
            
            # Make sure events are processed
            self.display.sync()
            return True
        except Exception as e:
            print(f"Error sending XTest key event: {e}")
            return False
            
    def send_text(self, text):
        """Send a text string as keyboard events"""
        try:
            # Map from character to X11 keysym and keycode
            for char in text:
                # This is a simplification - a full implementation would need 
                # a complete mapping of characters to X11 keycodes
                if char.isalnum() or char in " ,.;'[]\\-=/`":
                    keysym = ord(char.lower())
                    keycode = self.display.keysym_to_keycode(keysym)
                    if keycode:
                        # Handle shift for uppercase letters
                        if char.isupper():
                            shift_keycode = self.display.keysym_to_keycode(50)  # 50 is Shift keysym
                            xtest.fake_input(self.display, X.KeyPress, shift_keycode)
                            xtest.fake_input(self.display, X.KeyPress, keycode)
                            xtest.fake_input(self.display, X.KeyRelease, keycode)
                            xtest.fake_input(self.display, X.KeyRelease, shift_keycode)
                        else:
                            xtest.fake_input(self.display, X.KeyPress, keycode)
                            xtest.fake_input(self.display, X.KeyRelease, keycode)
                        
                        # Make sure events are processed
                        self.display.sync()
                        time.sleep(0.01)  # Small delay between keypresses
            
            return True
        except Exception as e:
            print(f"Error sending text via XTest: {e}")
            return False
    
    def capture_window_screenshot(self):
        """Capture a screenshot of the selected window"""
        if not self.selected_window or not self.window_geometry:
            print("No window selected. Cannot take screenshot.")
            return None
        
        # Get window coordinates and dimensions
        x, y, width, height = self.window_geometry
        
        try:
            # Take screenshot
            screenshot = ImageGrab.grab(bbox=(x, y, x+width, y+height))
            return screenshot
        except Exception as e:
            print(f"Error capturing screenshot: {e}")
            return None
    
    def preprocess_image(self, image, preprocess_type="default"):
        """Apply various preprocessing techniques to improve OCR accuracy"""
        # Convert PIL image to OpenCV format
        img = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        
        if preprocess_type == "default":
            # Basic preprocessing (grayscale)
            return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        elif preprocess_type == "threshold":
            # Basic thresholding
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            return cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]
        
        elif preprocess_type == "adaptive":
            # Adaptive thresholding
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            return cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                        cv2.THRESH_BINARY, 11, 2)
        
        elif preprocess_type == "contrast":
            # Increase contrast
            lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)
            clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
            cl = clahe.apply(l)
            limg = cv2.merge((cl, a, b))
            return cv2.cvtColor(limg, cv2.COLOR_LAB2BGR)
        
        return img
        
    def find_text_in_screenshot(self, target_text, screenshot=None):
        """Find text in the window screenshot and return its coordinates"""
        if screenshot is None:
            screenshot = self.capture_window_screenshot()
            if screenshot is None:
                return None
        
        try:
            # Save original image for tesseract processing and debugging
            temp_file = "/tmp/smart_autoclicker_temp.png"
            debug_file = "/tmp/smart_autoclicker_debug.png"
            screenshot.save(temp_file)
            
            # Make a copy for debug visualization
            debug_img = screenshot.copy()
            
            # Try different preprocessing techniques to improve OCR
            preprocessing_methods = ["default", "threshold", "adaptive", "contrast"]
            all_ocr_data = {}
            
            for method in preprocessing_methods:
                # Preprocess image
                processed_img = self.preprocess_image(screenshot, method)
                
                # Save processed image for debugging
                processed_file = f"/tmp/smart_autoclicker_{method}.png"
                cv2.imwrite(processed_file, processed_img)
                
                # Perform OCR with positioning data
                try:
                    if method == "default":
                        # For default, use original image
                        ocr_data = pytesseract.image_to_data(screenshot, output_type=pytesseract.Output.DICT)
                    else:
                        ocr_data = pytesseract.image_to_data(processed_img, output_type=pytesseract.Output.DICT)
                    
                    all_ocr_data[method] = ocr_data
                    if self.debug_mode:
                        print(f"\nProcessing using {method} preprocessing:")
                except Exception as e:
                    if self.debug_mode:
                        print(f"Error with {method} preprocessing: {e}")
                    continue
            
            # Combine results from all preprocessing methods
            if self.debug_mode:
                print("\n--- All text found in window ---")
                print(f"Target text: '{target_text}'")
                print(f"Attempted preprocessing methods: {', '.join(all_ocr_data.keys())}")
                print("\nText found with different preprocessing methods:")
            
            # Normalize target text for better matching
            normalized_target = target_text.lower().strip()
            
            # Find exact matches
            all_candidates = []
            
            # First try exact matches
            for method_name, ocr_data in all_ocr_data.items():
                texts = ocr_data.get('text', [])
                
                # Look for exact matches
                for i, text in enumerate(texts):
                    # Skip empty results
                    if not text or str(text).strip() == '':
                        continue
                    
                    # Normalize detected text
                    normalized_text = text.lower().strip()
                    
                    # Check for exact or close match
                    if normalized_text == normalized_target:
                        # Get bounding box and center
                        x = ocr_data['left'][i]
                        y = ocr_data['top'][i]
                        w = ocr_data['width'][i]
                        h = ocr_data['height'][i]
                        
                        # Calculate center of the text box
                        center_x = x + w // 2
                        center_y = y + h // 2
                        
                        # For UI elements like buttons, aim slightly below the text
                        # as many buttons have text in the upper portion
                        click_y = center_y + int(h * 0.2)  # Aim 20% below center
                        
                        candidate = {
                            'text': text,
                            'method': method_name,
                            'x': center_x,
                            'y': click_y,
                            'bbox': (x, y, w, h),
                            'conf': ocr_data['conf'][i] if 'conf' in ocr_data else 0,
                            'exact_match': True
                        }
                        all_candidates.append(candidate)
                        
                        if self.debug_mode:
                            print(f"Exact match: '{text}' at ({center_x}, {click_y}), method: {method_name}")
            
            # If no exact matches, look for partial matches
            if not all_candidates:
                for method_name, ocr_data in all_ocr_data.items():
                    texts = ocr_data.get('text', [])
                    
                    # Fuzzy matching - look for target text within detected text
                    for i, text in enumerate(texts):
                        # Skip empty results
                        if not text or str(text).strip() == '':
                            continue
                        
                        # Normalize detected text
                        normalized_text = text.lower().strip()
                        
                        # Check if target is part of detected text or vice versa
                        if normalized_target in normalized_text or normalized_text in normalized_target:
                            # Get bounding box and center
                            x = ocr_data['left'][i]
                            y = ocr_data['top'][i]
                            w = ocr_data['width'][i]
                            h = ocr_data['height'][i]
                            
                            # Calculate center of the text box with offset for buttons
                            center_x = x + w // 2
                            click_y = y + h // 2 + int(h * 0.2)  # Aim 20% below center for UI elements
                            
                            candidate = {
                                'text': text,
                                'match_type': 'contains',
                                'method': method_name,
                                'x': center_x,
                                'y': click_y,
                                'bbox': (x, y, w, h),
                                'conf': ocr_data['conf'][i] if 'conf' in ocr_data else 0,
                                'exact_match': False
                            }
                            all_candidates.append(candidate)
                            
                            if self.debug_mode:
                                if normalized_target in normalized_text:
                                    print(f"Partial match: '{text}' contains '{target_text}' at ({center_x}, {click_y})")
                                else:
                                    print(f"Partial match: '{text}' is part of '{target_text}' at ({center_x}, {click_y})")
            
            if all_candidates:
                # Sort by exact match first, then by confidence
                all_candidates.sort(key=lambda c: (-1 if c['exact_match'] else 0, c.get('conf', 0)), reverse=True)
                
                # Get best candidate
                best_candidate = all_candidates[0]
                
                # Draw bounding box on debug image for visualization
                if self.debug_mode:
                    # Convert PIL to OpenCV
                    debug_cv = cv2.cvtColor(np.array(debug_img), cv2.COLOR_RGB2BGR)
                    
                    # Get bbox
                    x, y, w, h = best_candidate['bbox']
                    
                    # Draw rectangle around text
                    cv2.rectangle(debug_cv, (x, y), (x+w, y+h), (0, 255, 0), 2)
                    
                    # Draw click point
                    cv2.circle(debug_cv, (best_candidate['x'], best_candidate['y']), 5, (0, 0, 255), -1)
                    
                    # Add text label
                    cv2.putText(debug_cv, best_candidate['text'], (x, y-5), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
                    
                    # Save debug image
                    cv2.imwrite(debug_file, debug_cv)
                    print(f"Debug image saved to {debug_file}")
                
                if self.debug_mode:
                    print(f"\nBest match: '{best_candidate['text']}' with method {best_candidate['method']}")
                    print(f"Click position: ({best_candidate['x']}, {best_candidate['y']})")
                    
                return (best_candidate['x'], best_candidate['y'])
            
            if self.debug_mode:
                print(f"Text '{target_text}' not found in window (neither exact nor fuzzy match)")
            return None
        except Exception as e:
            if self.debug_mode:
                print(f"Error finding text: {e}")
                import traceback
                traceback.print_exc()
            return None
    
    def find_element_by_template(self, template_path, threshold=0.8, screenshot=None, near_text_coords=None):
        """Find an element using template matching and return its coordinates
        
        If near_text_coords is provided, will select the match closest to that text position"""
        if screenshot is None:
            screenshot = self.capture_window_screenshot()
            if screenshot is None:
                return None
        
        try:
            # Convert PIL image to OpenCV format
            screenshot_cv = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
            
            # Read template image
            template = cv2.imread(template_path)
            if template is None:
                print(f"Error: Could not load template image from {template_path}")
                return None
            
            # Get template dimensions
            h, w = template.shape[:2]
            
            # Perform template matching
            result = cv2.matchTemplate(screenshot_cv, template, cv2.TM_CCOEFF_NORMED)
            
            # Find all locations where match exceeds threshold
            locations = np.where(result >= threshold)
            
            if len(locations[0]) > 0:
                # Get all matches above threshold
                matches = []
                for pt_y, pt_x in zip(locations[0], locations[1]):
                    match_val = result[pt_y, pt_x]
                    # Calculate center position
                    center_x = pt_x + w // 2
                    center_y = pt_y + h // 2
                    matches.append({
                        'position': (center_x, center_y),
                        'confidence': match_val,
                        'distance': float('inf')  # Will be calculated later if near_text_coords is provided
                    })
                
                # If we have a reference text position, find the closest match
                if near_text_coords is not None:
                    text_x, text_y = near_text_coords
                    if self.debug_mode:
                        print(f"Finding template closest to text at ({text_x}, {text_y})")
                    
                    # Calculate distance from each match to the text
                    for match in matches:
                        match_x, match_y = match['position']
                        # Calculate Euclidean distance
                        distance = math.sqrt((match_x - text_x)**2 + (match_y - text_y)**2)
                        match['distance'] = distance
                    
                    # Sort by distance (closest first)
                    matches.sort(key=lambda m: m['distance'])
                    
                    best_match = matches[0]
                    if self.debug_mode:
                        print(f"Found {len(matches)} template matches, selecting closest to text:")
                        for i, match in enumerate(matches[:min(3, len(matches))]):
                            print(f"  Match {i+1}: pos={match['position']}, distance={match['distance']:.1f}px, confidence={match['confidence']:.2f}")
                    
                    if self.debug_mode:
                        print(f"Selected match at {best_match['position']} (distance: {best_match['distance']:.1f}px)")
                    return best_match['position']
                else:
                    # No text reference, just use the best confidence match
                    matches.sort(key=lambda m: m['confidence'], reverse=True)
                    best_match = matches[0]
                    
                    if self.debug_mode and len(matches) > 1:
                        print(f"Found {len(matches)} template matches, selecting best confidence:")
                        for i, match in enumerate(matches[:min(3, len(matches))]):
                            print(f"  Match {i+1}: pos={match['position']}, confidence={match['confidence']:.2f}")
                    
                    if self.debug_mode:
                        print(f"Found template with {best_match['confidence']:.2f} confidence at {best_match['position']}")
                    
                    return best_match['position']
            
            if self.debug_mode:
                print(f"Template not found (threshold: {threshold})")
            
            return None
        except Exception as e:
            print(f"Error finding template: {e}")
            traceback.print_exc()  # More detailed error information
            return None
    
    def perform_action(self, action):
        """Perform a single automation action"""
        if not self.selected_window:
            print("No window selected. Cannot perform action.")
            return False
        
        # Ensure window geometry is up to date
        self.window_geometry = self.get_window_geometry(self.selected_window)
        if not self.window_geometry:
            print("Could not get window geometry. Cannot perform action.")
            return False
        
        # Activate window if needed
        if self.activate_window:
            try:
                subprocess.run(["xdotool", "windowactivate", "--sync", str(self.selected_window)], 
                             check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except subprocess.SubprocessError:
                print("Warning: Could not activate window")
        
        # Get action type and parameters
        action_type = action.get('type', '').lower()
        
        # Take a screenshot for element finding
        screenshot = self.capture_window_screenshot()
        self.current_screenshot = screenshot
        
        if action_type == 'click_text':
            # Find and click text
            text = action.get('text', '')
            if not text:
                print("Error: No text specified for click_text action")
                return False
            
            # Get action-specific retry count or use global default
            retry_count = action.get('retry_count', self.retry_count)
            # Try to find the text (once initially, then retry up to retry_count times)
            max_attempts = retry_count + 1  # Initial attempt + retries
            
            # Debug vs. normal mode output
            if self.debug_mode:
                print(f"Looking for text '{text}' (max attempts: {max_attempts})")
                
            for attempt in range(max_attempts):
                coords = self.find_text_in_screenshot(text, screenshot)
                
                # If text is not found, check if we should try direct position handling
                if not coords:
                    # Check if this is a fallback attempt with direct positions
                    direct_positions = action.get('direct_positions', False)
                    
                    if direct_positions and self.window_geometry:
                        # This is a debug/logging statement from the logs
                        print(f"Using direct position handling for '{text}'")
                        x, y, width, height = self.window_geometry
                        print(f"Window dimensions: {width}x{height}")
                        
                        # IMPORTANT - THIS SHOULD NOT RETURN TRUE IF TEXT WASN'T FOUND
                        # When text isn't found on screen, direct position attempts should not count as success
                        print(f"Text '{text}' not found in window. Direct position handling will not be used.")
                        return False
                    else:
                        # Not the last attempt?
                        if attempt < max_attempts - 1:
                            if self.debug_mode:
                                print(f"Text '{text}' not found, retrying in 1 second... (attempt {attempt+1}/{max_attempts})")
                            else:
                                print(f"'{text}' not found, retry {attempt+1}/{max_attempts}")
                            time.sleep(1)
                            screenshot = self.capture_window_screenshot()
                            continue
                        else:
                            # After all attempts
                            if self.debug_mode:
                                print(f"Error: Could not find text '{text}' after {max_attempts} attempt(s)")
                            else:
                                print(f"Failed to find: '{text}'")
                            return False
                
                window_x, window_y, _, _ = self.window_geometry
                abs_x = window_x + coords[0]
                abs_y = window_y + coords[1]
                
                if self.debug_mode:
                    print(f"Clicking on text '{text}' at position ({coords[0]}, {coords[1]})")
                    print(f"Window geometry: x={window_x}, y={window_y}")
                    print(f"Absolute coordinates: ({abs_x}, {abs_y})")
                else:
                    print(f"Clicking: '{text}'")
                
                # Let's try multiple click strategies to ensure the button gets pressed
                success = False
                
                # First try: direct position
                if self.debug_mode:
                    print("Attempt 1: Direct click at detected position")
                success = self.send_click_event(abs_x, abs_y)
                
                if not success or self.debug_mode:
                    # Second try: offset slightly downward (buttons often have text at top)
                    offset_y = 10  # Additional 10 pixels down
                    if self.debug_mode:
                        print(f"Attempt 2: Click offset down {offset_y}px")
                    success = self.send_click_event(abs_x, abs_y + offset_y) or success
                    time.sleep(0.3)
                
                if not success or self.debug_mode:
                    # Third try: small area around the center point with multiple clicks
                    if self.debug_mode:
                        print("Attempt 3: Multiple clicks in small area")
                    # Try clicking in small grid around the point (3x3 grid with 5px spacing)
                    for dx in [-5, 0, 5]:
                        for dy in [-5, 0, 5]:
                            success = self.send_click_event(abs_x + dx, abs_y + dy) or success
                            time.sleep(0.1)
                
                # VERIFY THE CLICK HAD THE EXPECTED EFFECT
                time.sleep(0.5)  # Wait for UI to update
                if self.debug_mode:
                    print("Verifying click effect...")
                
                # Take a new screenshot to verify the UI changed
                verification_screenshot = self.capture_window_screenshot()
                if verification_screenshot:
                    # Check if the clicked text is no longer present, which would indicate success
                    verification_coords = self.find_text_in_screenshot(text, verification_screenshot)
                    
                    if verification_coords:
                        # Text still found - could mean the click didn't have the expected effect
                        if self.debug_mode:
                            print(f"Warning: Text '{text}' still found after clicking. The click may not have had the expected effect.")
                            
                        # Calculate distance between original and verification positions
                        original_x, original_y = coords
                        verify_x, verify_y = verification_coords
                        distance = ((original_x - verify_x)**2 + (original_y - verify_y)**2)**0.5
                        
                        if distance < 5:  # If positions are very close, text probably didn't change
                            if self.debug_mode:
                                print(f"Text position barely changed ({distance:.1f}px). Click likely had no effect.")
                            success = False
                        else:
                            if self.debug_mode:
                                print(f"Text position changed significantly ({distance:.1f}px). UI may have updated.")
                    else:
                        # Text no longer found - this usually indicates the click worked!
                        if self.debug_mode:
                            print(f"Text '{text}' no longer found after clicking. Click appears successful!")
                        success = True
                
                return success
        elif action_type == 'click_template':
            # Find and click template
            template = action.get('template', '')
            threshold = action.get('threshold', 0.8)
            near_text = action.get('near_text', '')
            
            if not template or not os.path.exists(template):
                print(f"Error: Template file '{template}' not found")
                return False
            
            # If near_text is specified, find that text first
            text_coords = None
            if near_text:
                print(f"Looking for template near text: '{near_text}'")
                text_coords = self.find_text_in_screenshot(near_text, screenshot)
                if not text_coords:
                    print(f"Warning: Specified text '{near_text}' not found, will find template without text reference")
            
            # Get action-specific retry count or use global default
            retry_count = action.get('retry_count', self.retry_count)
            # Try to find the template (once initially, then retry up to retry_count times)
            max_attempts = retry_count + 1  # Initial attempt + retries
            
            # Debug vs. normal mode output
            template_name = os.path.basename(template)
            if self.debug_mode:
                print(f"Looking for template '{template_name}' (max attempts: {max_attempts})")
            
            for attempt in range(max_attempts):
                coords = self.find_element_by_template(template, threshold, screenshot, text_coords)
                if coords:
                    window_x, window_y, _, _ = self.window_geometry
                    abs_x = window_x + coords[0]
                    abs_y = window_y + coords[1]
                    
                    if self.debug_mode:
                        print(f"Clicking on template '{template_name}' at position ({coords[0]}, {coords[1]})")
                    else:
                        print(f"Clicking: '{template_name}'")
                    return self.send_click_event(abs_x, abs_y)
                
                # Not the last attempt?
                if attempt < max_attempts - 1:
                    if self.debug_mode:
                        print(f"Template '{template_name}' not found, retrying in 1 second... (attempt {attempt+1}/{max_attempts})")
                    else:
                        print(f"'{template_name}' not found, retry {attempt+1}/{max_attempts}")
                    time.sleep(1)
                    screenshot = self.capture_window_screenshot()
                    # If we had text coordinates but couldn't find the template, try to find the text again
                    if near_text:
                        text_coords = self.find_text_in_screenshot(near_text, screenshot)
            
            # After all attempts
            if self.debug_mode:
                print(f"Error: Could not find template '{template_name}' after {max_attempts} attempt(s)")
            else:
                print(f"Failed to find: '{template_name}'")
            return False
        
        elif action_type == 'click_position':
            # Click at specific position
            x = action.get('x', 0)
            y = action.get('y', 0)
            
            window_x, window_y, _, _ = self.window_geometry
            abs_x = window_x + x
            abs_y = window_y + y
            
            if self.debug_mode:
                print(f"Clicking at position ({x}, {y})")
            else:
                print(f"Clicking at position")
            return self.send_click_event(abs_x, abs_y)
        
        elif action_type == 'type_text':
            # Type text
            text = action.get('text', '')
            if not text:
                print("Error: No text specified for type_text action")
                return False
            
            if self.debug_mode:
                print(f"Typing text: '{text}'")
            else:
                # For privacy, don't show full text in non-debug mode
                print(f"Typing text ({len(text)} chars)")
            return self.send_text(text)
        
        elif action_type == 'wait':
            # Wait for specified duration
            duration = action.get('duration', 1.0)
            if self.debug_mode:
                print(f"Waiting for {duration} seconds")
            else:
                print(f"Waiting...")
            time.sleep(duration)
            return True
        
        else:
            print(f"Error: Unknown action type '{action_type}'")
            return False
    
    def run_automation(self):
        """Run the automation sequence"""
        if not self.actions:
            print("No actions defined. Please set up actions first.")
            return
        
        if not self.selected_window:
            print("No window selected. Please select a window first.")
            return
        
        self.is_running = True
        print(f"\nRunning automation on window: {self.get_window_name(self.selected_window)}")
        
        try:
            cycle = 0
            stats = {
                'total': 0,
                'successful': 0,
                'failed': 0,
                'failed_details': []
            }
            
            # Temporary storage for the last time we saw each action succeed
            # This helps track which actions are still active/available
            action_last_seen = {i: 0 for i in range(len(self.actions))}
            
            while self.is_running:
                cycle += 1
                print(f"\n--- Cycle {cycle} ---")
                
                # Take a new screenshot at the beginning of each cycle
                screenshot = self.capture_window_screenshot()
                if not screenshot:
                    print("Could not capture window screenshot. Is the window visible?")
                    time.sleep(1)
                    continue
                    
                self.current_screenshot = screenshot
                
                # Check if we should stop based on cycles or all actions being completed
                any_action_available = False
                
                # Perform each action in sequence
                for i, action in enumerate(self.actions):
                    action_desc = self._get_action_description(action)
                    
                    print(f"\nAction {i+1}/{len(self.actions)}: {action_desc}")
                    
                    # Keep track of total actions
                    stats['total'] += 1
                    
                    # Perform the action
                    result = self.perform_action(action)
                    
                    if result:
                        stats['successful'] += 1
                        action_last_seen[i] = cycle  # Update when this action was last seen/successful
                        print(f"✓ Success")
                    else:
                        stats['failed'] += 1
                        stats['failed_details'].append(action_desc)
                        print(f"✗ Failed")
                        
                        # In continuous mode, we'll keep retrying indefinitely
                        if self.continuous_mode:
                            any_action_available = True
                        
                    # Add delay between actions
                    time.sleep(self.click_interval)
                
                # If not in continuous mode, we stop after one cycle
                if not self.continuous_mode:
                    break
                    
                # Check if we've gone too long without seeing any actions succeed
                # This helps prevent infinite loops when no actions are available anymore
                cycles_since_last_success = cycle - max(action_last_seen.values())
                if cycles_since_last_success > 5 and cycle > 5:  # Allow a few cycles to start
                    print("\nNo actions have succeeded in the last 5 cycles. Stopping automation.")
                    break
                    
                # Only continue if actions are still available (relevant in continuous mode)
                if not any_action_available and not self.continuous_mode:
                    break
                
            # Display summary
            self._display_automation_summary(stats)
            
        except KeyboardInterrupt:
            print("\nAutomation stopped by user.")
        finally:
            self.is_running = False
    
    def _get_action_description(self, action):
        """Get a descriptive string for an action"""
        action_type = action.get('type', 'unknown')
        
        if action_type == 'click_text':
            return f"Click text: '{action.get('text', 'unknown')}'" 
        elif action_type == 'click_template':
            template = action.get('template', 'unknown')
            return f"Click template: '{os.path.basename(template)}'" 
        elif action_type == 'click_position':
            return f"Click at position: ({action.get('x', 0)}, {action.get('y', 0)})"
        elif action_type == 'type_text':
            text = action.get('text', '')
            if self.debug_mode:
                return f"Type text: '{text}'"
            else:
                return f"Type text ({len(text)} chars)"
        elif action_type == 'wait':
            return f"Wait ({action.get('duration', 1.0)} seconds)" 
        else:
            return f"Unknown action: {action_type}"
            
    def _display_automation_summary(self, stats):
        """Display a summary of automation statistics"""
        print("\n" + "-"*40)
        print("Automation Summary")
        print("-"*40)
        print(f"Total actions: {stats['total']}")
        print(f"Successful actions: {stats['successful']}")
        print(f"Failed actions: {stats['failed']}")
        
        # Show failed actions
        if stats['failed_details']:
            print("\nFailed actions:")
            for action_desc in stats['failed_details']:
                print(f"  ✗ {action_desc}")
                
        print("-"*40)
    
    def get_config_files(self, config_dir=None):
        """List all available configuration files"""
        if config_dir is None:
            # Default to ~/.config/smart_autoclicker/
            config_dir = os.path.expanduser("~/.config/smart_autoclicker")
        
        # Create config directory if it doesn't exist
        if not os.path.exists(config_dir):
            os.makedirs(config_dir)
            print(f"Created configuration directory: {config_dir}")
            return []
    
        # Get all JSON files in the config directory
        config_files = [f for f in os.listdir(config_dir) if f.endswith('.json')]
        config_files.sort()
        
        # Return full paths
        return [os.path.join(config_dir, f) for f in config_files]
    
    def get_config_metadata(self, config_file):
        """Get basic metadata about a configuration file"""
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
            
            # Get basic info
            name = config.get('name', os.path.basename(config_file))
            num_actions = len(config.get('actions', []))
            created = config.get('created', 'Unknown')
            modified = config.get('modified', 'Unknown')
            description = config.get('description', '')
            
            return {
                'path': config_file,
                'name': name, 
                'num_actions': num_actions,
                'created': created,
                'modified': modified,
                'description': description
            }
        except Exception as e:
            return {
                'path': config_file,
                'name': os.path.basename(config_file),
                'error': str(e)
            }
    
    def list_config_files(self):
        """Display a list of available configuration files"""
        config_files = self.get_config_files()
        
        if not config_files:
            print("No saved configurations found.")
            print(f"Configurations will be saved to: {os.path.expanduser('~/.config/smart_autoclicker')}")
            return None
        
        print("\nAvailable Configurations:")
        print("-------------------------")
        
        for i, config_file in enumerate(config_files):
            metadata = self.get_config_metadata(config_file)
            print(f"{i+1}. {metadata['name']}")
            if 'error' in metadata:
                print(f"   [Error: {metadata['error']}]")
            else:
                print(f"   Actions: {metadata['num_actions']}")
                if metadata['description']:
                    print(f"   Description: {metadata['description']}")
                print(f"   Path: {metadata['path']}")
        
        return config_files
    
    def interactive_load_config(self):
        """Interactive menu to load a configuration"""
        config_files = self.list_config_files()
        
        if not config_files:
            return False
        
        while True:
            choice = input("\nEnter number to load (or 'q' to cancel): ")
            if choice.lower() == 'q':
                return False
            
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(config_files):
                    config_file = config_files[idx]
                    # Actually load the configuration file
                    return self.load_config(config_file)
                else:
                    print(f"Invalid choice. Please enter a number between 1 and {len(config_files)}")
            except ValueError:
                print("Invalid input. Please enter a number or 'q' to cancel.")
        
        return False
    
    def load_config(self, config_file=None):
        """Load automation configuration from JSON file"""
        # If no config file specified, show interactive menu
        if config_file is None:
            return self.interactive_load_config()
            # Note: interactive_load_config now handles the actual loading
        
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
            
            print(f"Loading configuration from: {config_file}")
            
            # Set configuration parameters
            if 'interval' in config:
                self.click_interval = config['interval']
                print(f"  Interval: {self.click_interval} seconds")
            
            if 'activate_window' in config:
                self.activate_window = config['activate_window']
                print(f"  Activate window: {self.activate_window}")
            
            if 'retry_count' in config:
                self.retry_count = config['retry_count']
                print(f"  Retry count: {self.retry_count}")
            
            if 'debug_mode' in config:
                self.debug_mode = config['debug_mode']
                print(f"  Debug mode: {self.debug_mode}")
            
            if 'retry_count' in config:
                self.retry_count = config['retry_count']
                print(f"  Default retry count: {self.retry_count}")
                
            if 'loop_actions' in config:
                self.loop_actions = config['loop_actions']
            else:
                self.loop_actions = True
            print(f"  Loop actions: {self.loop_actions}")
            
            # Load actions
            if 'actions' in config and isinstance(config['actions'], list):
                self.actions = config['actions']
                print(f"  Loaded {len(self.actions)} actions")
                
                # Store the current config file path
                self.config_file = config_file
                return True
            else:
                print("Error: No actions found in configuration")
                return False
            
        except Exception as e:
            print(f"Error loading configuration: {e}")
            traceback.print_exc()  # More detailed error information
            return False
    
    def save_config(self, config_file=None, name=None, description=None):
        """Save automation configuration to JSON file"""
        if config_file is None:
            # Use default config directory
            config_dir = os.path.expanduser("~/.config/smart_autoclicker")
            # Create directory if it doesn't exist
            if not os.path.exists(config_dir):
                os.makedirs(config_dir)
            
            # Interactive naming if not provided
            if name is None:
                name = input("Enter a name for this configuration: ")
            
            # Generate filename from name (replacing spaces with underscores)
            safe_name = name.replace(" ", "_").replace("/", "").replace("\\", "")
            filename = f"{safe_name}.json"
            config_file = os.path.join(config_dir, filename)
            
            # If file exists, confirm overwrite
            if os.path.exists(config_file):
                confirm = input(f"Configuration '{name}' already exists. Overwrite? (y/n): ")
                if confirm.lower() != 'y':
                    print("Save canceled.")
                    return False
            
            # Interactive description if not provided
            if description is None:
                description = input("Enter a description (optional): ")
        
        # Current timestamp for metadata
        timestamp = datetime.datetime.now().isoformat()
        
        # Check if this is a new file or an update
        is_new = not os.path.exists(config_file)
        
        # If updating existing file, try to preserve some metadata
        created_timestamp = timestamp
        if not is_new:
            try:
                with open(config_file, 'r') as f:
                    old_config = json.load(f)
                    created_timestamp = old_config.get('created', timestamp)
            except Exception:
                pass  # If reading fails, use current time for created
        
        # Assemble config with metadata
        config = {
            'name': name or os.path.basename(config_file).replace('.json', ''),
            'description': description or '',
            'created': created_timestamp,
            'modified': timestamp,
            'interval': self.click_interval,
            'activate_window': self.activate_window,
            'retry_count': self.retry_count,
            'debug_mode': self.debug_mode,
            'loop_actions': self.loop_actions,
            'continuous_mode': self.continuous_mode,
            'actions': self.actions
        }
        
        try:
            with open(config_file, 'w') as f:
                json.dump(config, f, indent=2)
            print(f"Configuration saved to {config_file}")
            self.config_file = config_file  # Store current config file
            return True
        except Exception as e:
            print(f"Error saving configuration: {e}")
            traceback.print_exc()  # More detailed error information
            return False
            
    def interactive_save_config(self):
        """Interactive menu to save a configuration"""
        if not self.actions:
            print("No actions to save. Please create at least one action first.")
            return False
        
        print("\nSave Configuration")
        print("-----------------")
        
        name = input("Enter a name for this configuration: ")
        description = input("Enter a description (optional): ")
        
        return self.save_config(name=name, description=description)
    
    def create_action_interactively(self):
        """Create an action interactively"""
        print("\nCreate New Action")
        print("-----------------")
        print("Action types:")
        print("1. Click on text")
        print("2. Click on image template")
        print("3. Click at specific position")
        print("4. Type text")
        print("5. Wait")
        
        choice = input("Choose action type (1-5): ")
        
        if choice == "1":
            # Click on text
            text = input("Enter text to find and click: ")
            retry_input = input("Enter number of retries if text not found initially (default 0): ").strip()
            retry_count = int(retry_input) if retry_input and retry_input.isdigit() else self.retry_count
            
            action = {
                'type': 'click_text',
                'text': text,
                'required': input("Is this action required? (y/n): ").lower() == 'y',
                'retry_count': retry_count
            }
            
        elif choice == "2":
            # Click on template
            template = input("Enter path to template image: ")
            threshold = float(input("Enter matching threshold (0.0-1.0, default 0.8): ") or "0.8")
            retry_input = input("Enter number of retries if template not found initially (default 0): ").strip()
            retry_count = int(retry_input) if retry_input and retry_input.isdigit() else self.retry_count
            
            action = {
                'type': 'click_template',
                'template': template,
                'threshold': threshold,
                'required': input("Is this action required? (y/n): ").lower() == 'y',
                'retry_count': retry_count
            }
            
        elif choice == "3":
            # Click at position
            print("Move your cursor to the desired position and press Enter...")
            input()
            
            # Get cursor position relative to window
            try:
                result = subprocess.run(["xdotool", "getmouselocation", "--shell"], 
                                      capture_output=True, text=True, check=True)
                
                mouse_x, mouse_y = None, None
                for line in result.stdout.splitlines():
                    if line.startswith("X="):
                        mouse_x = int(line.split("=")[1])
                    elif line.startswith("Y="):
                        mouse_y = int(line.split("=")[1])
                
                if mouse_x is not None and mouse_y is not None:
                    window_x, window_y, _, _ = self.window_geometry
                    rel_x = mouse_x - window_x
                    rel_y = mouse_y - window_y
                    
                    action = {
                        'type': 'click_position',
                        'x': rel_x,
                        'y': rel_y,
                        'required': input("Is this action required? (y/n): ").lower() == 'y'
                    }
                else:
                    print("Could not get mouse position.")
                    return None
            except subprocess.SubprocessError as e:
                print(f"Error getting mouse position: {e}")
                return None
            
        elif choice == "4":
            # Type text
            text = input("Enter text to type: ")
            action = {
                'type': 'type_text',
                'text': text,
                'required': input("Is this action required? (y/n): ").lower() == 'y'
            }
            
        elif choice == "5":
            # Wait
            duration = float(input("Enter wait duration in seconds: ") or "1.0")
            action = {
                'type': 'wait',
                'duration': duration,
                'required': False
            }
            
        else:
            print("Invalid choice")
            return None
        
        return action
    
    def interactive_setup(self):
        """Run interactive setup to create automation sequence"""
        # Set defaults
        self.loop_actions = True
        
        # Step 1: Select window
        window_selected = self.select_window_by_click()
        if not window_selected:
            return False
        
        # Step 2: Configure general settings
        print("\nGeneral Settings")
        print("---------------")
        
        self.click_interval = float(input("Enter time between actions in seconds (default 1.0): ") or "1.0")
        self.debug_mode = input("Enable debug mode? (y/n, default n): ").lower() == 'y'
        self.loop_actions = input("Loop actions? (y/n, default y): ").lower() != 'n'
        
        # Configure default retry count
        retry_input = input("Default number of retries for actions if not found initially (default 0): ").strip()
        self.retry_count = int(retry_input) if retry_input and retry_input.isdigit() else 0
        
        # Step 3: Create actions
        self.actions = []
        
        while True:
            print("\nCurrent Actions:")
            for i, action in enumerate(self.actions):
                action_type = action.get('type', 'unknown')
                if action_type == 'click_text':
                    print(f"  {i+1}. Click on text: '{action.get('text', '')}'")
                elif action_type == 'click_template':
                    print(f"  {i+1}. Click on template: '{action.get('template', '')}'")
                elif action_type == 'click_position':
                    print(f"  {i+1}. Click at position: ({action.get('x', 0)}, {action.get('y', 0)})")
                elif action_type == 'type_text':
                    print(f"  {i+1}. Type text: '{action.get('text', '')}'")
                elif action_type == 'wait':
                    print(f"  {i+1}. Wait for {action.get('duration', 1.0)} seconds")
            
            print("\nOptions:")
            print("  1. Add an action")
            print("  2. Remove an action")
            print("  3. Save configuration")
            print("  4. Load configuration")
            print("  5. Start automation")
            print("  6. Exit")
            
            choice = input("Choose an option (1-6): ")
            
            if choice == "1":
                action = self.create_action_interactively()
                if action:
                    self.actions.append(action)
                    print("Action added")
            elif choice == "2":
                if not self.actions:
                    print("No actions to remove")
                else:
                    index = int(input(f"Enter action number to remove (1-{len(self.actions)}): ")) - 1
                    if 0 <= index < len(self.actions):
                        del self.actions[index]
                        print("Action removed")
                    else:
                        print("Invalid action number")
            elif choice == "3":
                # Use the interactive save function that handles paths properly
                self.interactive_save_config()
            elif choice == "4":
                # Use the interactive load function that lists available configs
                self.interactive_load_config()
            elif choice == "5":
                if self.actions:
                    return True
                else:
                    print("Please add at least one action first")
            elif choice == "6":
                return False
            else:
                print("Invalid choice")
        
        return False

def list_all_windows():
    """List all available windows with their IDs"""
    try:
        # Get all window IDs
        result = subprocess.run(["xdotool", "search", "--onlyvisible", "--all"], 
                             capture_output=True, text=True, check=True)
        window_ids = result.stdout.strip().split('\n')
        
        print("Available windows:")
        print("-" * 80)
        print(f"{'Window ID':<12} | {'Window Name':<50} | {'Geometry':>15}")
        print("-" * 80)
        
        for wid in window_ids:
            if not wid:
                continue
                
            try:
                # Get window name
                name_result = subprocess.run(["xdotool", "getwindowname", wid], 
                                          capture_output=True, text=True, check=True)
                window_name = name_result.stdout.strip()
                
                # Get window geometry
                geo_result = subprocess.run(["xdotool", "getwindowgeometry", "--shell", wid], 
                                         capture_output=True, text=True, check=True)
                
                # Parse geometry
                width, height = "?", "?"
                for line in geo_result.stdout.splitlines():
                    if line.startswith("WIDTH="):
                        width = line.split("=")[1]
                    elif line.startswith("HEIGHT="):
                        height = line.split("=")[1]
                        
                geometry = f"{width}x{height}"
                print(f"{wid:<12} | {window_name[:50]:<50} | {geometry:>15}")
            except subprocess.SubprocessError:
                print(f"{wid:<12} | <unable to get window info>")
                
        print("-" * 80)
        print("\nTo use a specific window, run with: --window-id <WINDOW_ID>")
        return True
    except subprocess.SubprocessError as e:
        print(f"Error listing windows: {e}")
        return False

def select_window_by_id(window_id):
    """Validate and select a window by its ID"""
    try:
        # Verify the window exists
        subprocess.run(["xdotool", "getwindowname", window_id], 
                     capture_output=True, text=True, check=True)
        
        # Convert to int (might be hex or decimal)
        if window_id.startswith("0x"):
            return int(window_id, 16)
        else:
            return int(window_id)
    except (subprocess.SubprocessError, ValueError) as e:
        print(f"Error selecting window {window_id}: {e}")
        return None

def main():
    parser = argparse.ArgumentParser(description="Smart XTest Autoclicker - find and click UI elements without moving your cursor")
    parser.add_argument("--config", type=str, help="Path to configuration file")
    parser.add_argument("--list-windows", action="store_true", help="List all available windows with their IDs")
    parser.add_argument("--window-name", type=str, help="Select window by name instead of clicking on it")
    parser.add_argument("--window-id", type=str, help="Directly specify window ID (useful for i3 and other tiling managers)")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    parser.add_argument("--no-activate", action="store_true", help="Don't activate the window before clicking")
    parser.add_argument("--test-click", action="store_true", help="Perform a test click to verify XTest functionality")
    parser.add_argument("--i3", action="store_true", help="Use i3-specific window handling methods")
    parser.add_argument("--continuous", action="store_true", help="Continuous mode - keep retrying actions until they succeed")
    # Configuration management options
    parser.add_argument("--list-configs", action="store_true", help="List all available saved configurations")
    # Removed the --save flag as it's unnecessary - saving is always offered when appropriate
    parser.add_argument("--load", action="store_true", help="Load configuration interactively")
    
    args = parser.parse_args()
    
    try:
        # Check if xdotool is installed
        subprocess.run(["xdotool", "--version"], capture_output=True, check=True)
    except (subprocess.SubprocessError, FileNotFoundError):
        print("Error: xdotool is required but not found. Please install it:")
        print("  sudo apt-get install xdotool")
        return 1
    
    # List windows and exit if requested
    if args.list_windows:
        list_all_windows()
        return 0
        
    try:
        # Check if tesseract is installed
        subprocess.run(["tesseract", "--version"], capture_output=True, check=True)
    except (subprocess.SubprocessError, FileNotFoundError):
        print("Warning: tesseract is not found. Text recognition will not work.")
        print("  Install it with: sudo apt-get install tesseract-ocr")
    
    # Initialize the clicker
    clicker = SmartAutoclicker()
    clicker.debug_mode = args.debug
    clicker.activate_window = not args.no_activate
    
    # Handle configuration management options first
    if args.list_configs:
        clicker.list_config_files()
        return 0
        
    if args.load:
        if clicker.interactive_load_config():
            print("Configuration loaded successfully.")
        else:
            print("Configuration loading was cancelled or failed.")
            return 1
            
    if args.config:
        if not clicker.load_config(args.config):
            print(f"Failed to load configuration from {args.config}")
            return 1
        print(f"Loaded configuration from {args.config}")
        
    if args.continuous:
        clicker.continuous_mode = True
        print("Continuous mode enabled - will keep retrying actions until they succeed")
    
    # Setup window
    window_selected = False
    
    # Priority: window-id > window-name > interactive selection
    if args.window_id:
        try:
            # Convert window ID from string to integer
            if args.window_id.startswith('0x'):
                window_id = int(args.window_id, 16)
            else:
                window_id = int(args.window_id)
                
            # No need for a separate function, just use the ID directly
            clicker.selected_window = window_id
            clicker.window_geometry = clicker.get_window_geometry(window_id) or \
                                    clicker.get_window_geometry_alternative(window_id) or \
                                    clicker.get_i3_window_geometry(window_id)
            if clicker.window_geometry:
                window_name = clicker.get_window_name(window_id)
                print(f"Selected window: {window_name} (id: {window_id:x})")
                x, y, width, height = clicker.window_geometry
                print(f"Window geometry: x={x}, y={y}, width={width}, height={height}")
                window_selected = True
            else:
                print(f"Warning: Could not get geometry for window ID {args.window_id}")
                if input("Continue without geometry? (y/n): ").lower() == 'y':
                    # Use screen dimensions as fallback
                    screen = clicker.display.screen()
                    clicker.window_geometry = (0, 0, screen.width_in_pixels, screen.height_in_pixels)
                    print(f"Using screen dimensions as fallback: {clicker.window_geometry}")
                    window_selected = True
        except (ValueError, TypeError) as e:
            print(f"Error with window ID {args.window_id}: {e}")
            print("Please use a valid window ID (decimal or hexadecimal with 0x prefix).")
    elif args.window_name:        
        window_selected = clicker.select_window_by_name(args.window_name)
    
    # Handle i3 window manager specifics
    if args.i3:
        print("Using i3 window manager specific methods")
        # Prioritize i3 geometry methods
        clicker.get_window_geometry = clicker.get_i3_window_geometry
    
    # Run a test click if requested
    if args.test_click and window_selected:
        print("\nPerforming test click...")
        test_x, test_y = 100, 100  # Default position relative to window
        
        if clicker.window_geometry:
            window_x, window_y, _, _ = clicker.window_geometry
            abs_x = window_x + test_x
            abs_y = window_y + test_y
            
            print(f"Clicking at position ({test_x}, {test_y}) relative to window")
            print(f"Absolute screen position: ({abs_x}, {abs_y})")
            
            if clicker.send_click_event(abs_x, abs_y):
                print("Test click successful!")
                return 0
            else:
                print("Test click failed. XTest events may not be working correctly.")
                return 1
        else:
            print("Cannot perform test click without window geometry information.")
            return 1
    
    # If we have loaded actions but no window selected, offer to run them
    if clicker.actions and not window_selected:
        if input("Configuration loaded. Select a window to run? (y/n): ").lower() == 'y':
            window_selected = clicker.select_window_by_click()
        else:
            return 0
    
    # Update window geometry if we just selected a window
    if window_selected and clicker.selected_window:
        clicker.window_geometry = clicker.get_window_geometry(clicker.selected_window) or \
                                clicker.get_window_geometry_alternative(clicker.selected_window) or \
                                clicker.get_i3_window_geometry(clicker.selected_window)
        print("Window selected. Ready to run automation.")
    
    # If window is selected and we have actions, we can run the automation
    if window_selected and clicker.actions:
        # Offer to save the configuration if it was created interactively
        if clicker.config_file is None and input("Save this configuration before running? (y/n): ").lower() == 'y':
            clicker.interactive_save_config()
        clicker.run_automation()
        return 0
    
    # If no actions loaded and window selected, run interactive setup
    if window_selected and not clicker.actions:
        print("No actions defined. Running interactive setup...")
        if clicker.interactive_setup():
            clicker.run_automation()
            return 0
    
    # If we haven't done anything specific yet, show the default interface
    # Default interactive mode if no specific options were provided
    if not (args.config or args.load or args.list_configs) and not window_selected:
        print("Smart XTest Autoclicker")
        print("----------------------")
        print("This tool can find and click UI elements without moving your cursor")
        
        # Run interactive setup which includes window selection
        if clicker.interactive_setup():
            clicker.run_automation()
    
    return 0

if __name__ == "__main__":
    sys.exit(main())