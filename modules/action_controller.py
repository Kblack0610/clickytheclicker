#!/usr/bin/env python3
"""
Action Controller Module

Orchestrates the execution of automation sequences, managing the flow
between different types of actions (clicks, typing, waiting, etc.).
"""

import os
import time
import json
import threading
from typing import List, Dict, Tuple, Optional, Any, Callable

from .input_manager import InputManager
from .window_manager import WindowManager
from .image_processor import ImageProcessor
from .error_recovery import ErrorRecoveryManager, RecoveryAction, RecoveryStrategy

class ActionController:
    """
    Controls the execution of automation actions and sequences.
    """
    
    def __init__(self, input_manager: InputManager, window_manager: WindowManager, 
                image_processor: ImageProcessor, debug_mode: bool = False,
                enable_recovery: bool = True, create_checkpoints: bool = True):
        """
        Initialize the action controller.
        
        Args:
            input_manager: InputManager instance for input operations
            window_manager: WindowManager instance for window operations
            image_processor: ImageProcessor instance for image operations
            debug_mode: Whether to output debug information
            enable_recovery: Whether to enable error recovery mechanisms
            create_checkpoints: Whether to create checkpoints during automation
        """
        self.input_manager = input_manager
        self.window_manager = window_manager
        self.image_processor = image_processor
        self.debug_mode = debug_mode
        
        # Action sequence and control variables
        self.actions = []
        self.is_running = False
        self.loop_actions = False
        self.continuous_mode = False
        self.click_interval = 0.1  # Time between actions in seconds
        
        # Error recovery options
        self.enable_recovery = enable_recovery
        self.create_checkpoints = create_checkpoints
        
        # Initialize error recovery manager if enabled
        self.recovery_manager = None
        if enable_recovery:
            self.recovery_manager = ErrorRecoveryManager(
                window_manager=window_manager,
                image_processor=image_processor,
                debug_mode=debug_mode
            )
        
        # Statistics tracking
        self.stats = self._create_stats()
    
    def _create_stats(self) -> Dict[str, Any]:
        """Create a new statistics tracking dictionary."""
        return {
            'start_time': time.time(),
            'successful_actions': 0,
            'failed_actions': 0,
            'cycles_completed': 0,
            'action_counts': {},
            'successful_details': [],
            'failed_details': []
        }
    
    def load_actions(self, config_file: str, config_manager=None) -> bool:
        """
        Load actions from a configuration file.
        
        Args:
            config_file: Path to the configuration file
            config_manager: Optional ConfigManager for resolving paths
            
        Returns:
            Whether loading was successful
        """
        try:
            # If config_manager is provided, use it to load the config
            if config_manager is not None:
                config = config_manager.load_config(config_file)
                if config is None:
                    return False
            else:
                # Direct file loading (fallback)
                with open(config_file, 'r') as f:
                    config = json.load(f)
            
            # Extract actions from config
            self.actions = config.get('actions', [])
            
            # Extract other settings if present
            self.loop_actions = config.get('loop_actions', False)
            self.continuous_mode = config.get('continuous_mode', False)
            self.click_interval = config.get('click_interval', 0.1)
            
            if self.debug_mode:
                print(f"Loaded {len(self.actions)} actions from config")
                print(f"Settings: loop={self.loop_actions}, continuous={self.continuous_mode}, interval={self.click_interval}")
            
            return True
            
        except Exception as e:
            if self.debug_mode:
                print(f"Error loading actions: {e}")
            return False
    
    def add_action(self, action: Dict[str, Any]) -> None:
        """
        Add an action to the sequence.
        
        Args:
            action: Action dictionary with type and parameters
        """
        self.actions.append(action)
        
        if self.debug_mode:
            print(f"Added action: {action.get('type', 'unknown')}")
    
    def save_actions(self, config_file: str) -> bool:
        """
        Save current actions to a configuration file.
        
        Args:
            config_file: Path to save the configuration
            
        Returns:
            Whether saving was successful
        """
        try:
            config = {
                'actions': self.actions,
                'loop_actions': self.loop_actions,
                'continuous_mode': self.continuous_mode,
                'click_interval': self.click_interval
            }
            
            with open(config_file, 'w') as f:
                json.dump(config, f, indent=2)
            
            if self.debug_mode:
                print(f"Saved {len(self.actions)} actions to {config_file}")
            
            return True
            
        except Exception as e:
            if self.debug_mode:
                print(f"Error saving actions: {e}")
            return False
    
    def run_automation(self, window_id: Optional[int] = None, max_cycles: int = 0,
                      max_failures: int = 10) -> Dict[str, Any]:
        """
        Run the automation sequence.
        
        Args:
            window_id: Optional window ID to target
            max_cycles: Maximum number of cycles (0 = unlimited)
            max_failures: Maximum consecutive failures before stopping (0 = unlimited)
            
        Returns:
            Statistics about the automation run
        """
        # Reset statistics
        self.stats = self._create_stats()
        
        try:
            self.is_running = True
            action_index = 0
            consecutive_failures = 0
            retry_count = 0
            checkpoint_interval = max(5, len(self.actions) // 5)  # Create checkpoints every ~20% of actions
            
            print(f"Starting automation with {len(self.actions)} actions")
            
            while self.is_running:
                # Check if we've reached the maximum cycles
                if max_cycles > 0 and self.stats['cycles_completed'] >= max_cycles:
                    print(f"Reached maximum cycles ({max_cycles})")
                    break
                
                # Check if we've had too many consecutive failures
                if max_failures > 0 and consecutive_failures >= max_failures:
                    print(f"Stopping after {consecutive_failures} consecutive failures")
                    break
                
                # Get the current action
                action = self.actions[action_index]
                
                # Create checkpoint if enabled and it's time for one
                if (self.enable_recovery and self.recovery_manager and self.create_checkpoints and
                    action_index % checkpoint_interval == 0 and retry_count == 0):
                    screenshot = None
                    if window_id:
                        try:
                            screenshot = self.image_processor.capture_window_screenshot(window_id)
                        except Exception:
                            pass  # Ignore screenshot errors
                    
                    self.recovery_manager.create_checkpoint(action_index, window_id, screenshot)
                    if self.debug_mode:
                        print(f"Created checkpoint at action index {action_index}")
                
                if self.debug_mode:
                    print(f"\nPerforming action: {action.get('type', 'unknown')}")
                    if retry_count > 0:
                        print(f"Retry attempt {retry_count}")
                
                # Perform the action
                success, action_desc = self.perform_action(action, window_id)
                
                # Update statistics
                action_type = action.get('type', 'unknown')
                
                if action_type not in self.stats['action_counts']:
                    self.stats['action_counts'][action_type] = {'success': 0, 'fail': 0}
                
                if success:
                    self.stats['successful_actions'] += 1
                    self.stats['action_counts'][action_type]['success'] += 1
                    self.stats['successful_details'].append(action_desc)
                    
                    # Reset consecutive failures and retry count
                    consecutive_failures = 0
                    retry_count = 0
                    
                    if not self.debug_mode:
                        print(f"✓ {action_desc}")
                else:
                    self.stats['failed_actions'] += 1
                    self.stats['action_counts'][action_type]['fail'] += 1
                    self.stats['failed_details'].append(action_desc)
                    consecutive_failures += 1
                    
                    if not self.debug_mode:
                        print(f"✗ {action_desc}")
                
                # Handle failures with recovery mechanisms if enabled
                if not success:
                    if self.enable_recovery and self.recovery_manager:
                        # Get recovery strategy for this action
                        recovery = self.recovery_manager.get_recovery_for_action(action)
                        
                        # Apply recovery strategy
                        recovery_success, next_action, next_index = self.recovery_manager.apply_recovery_strategy(
                            failed_action=action,
                            recovery=recovery,
                            action_index=action_index,
                            window_id=window_id
                        )
                        
                        if recovery_success:
                            if next_action is not None:
                                # Use the next action (either original or fallback)
                                action = next_action
                                
                                # If it's the same action, increment retry count
                                if next_index == action_index:
                                    retry_count += 1
                                    
                                    # Check if we've exceeded max retries
                                    max_retries = recovery.params.get('max_retries', 3)
                                    if retry_count > max_retries:
                                        print(f"Exceeded maximum retries ({max_retries}) for action")
                                        retry_count = 0
                                        action_index = (action_index + 1) % len(self.actions)
                                    else:
                                        # Stay on the same action
                                        continue
                                else:
                                    # Going to a different action index
                                    action_index = next_index
                                    retry_count = 0
                                    continue
                            else:
                                # No next action specified, go to next index
                                action_index = next_index
                                retry_count = 0
                                if action_index < 0:  # Special case for abort
                                    print("Aborting automation sequence")
                                    break
                                continue
                        else:
                            # Recovery strategy failed
                            print(f"Recovery strategy failed for action")
                    
                    # Without recovery, handle required actions
                    if action.get('required', False):
                        if self.continuous_mode:
                            print(f"Required action failed, will retry in 2 seconds (continuous mode)")
                            time.sleep(2)
                            # Stay on the same action index to retry
                            continue
                        else:
                            print(f"Required action failed, stopping automation")
                            break
                
                # Move to next action (cycling through the list if loop is enabled)
                action_index = (action_index + 1) % len(self.actions)
                
                # Check if we've completed all actions
                if action_index == 0:
                    self.stats['cycles_completed'] += 1
                    
                    # Display summary after each cycle
                    print(f"\nCompleted cycle {self.stats['cycles_completed']}")
                    
                    # Only show detailed summary in debug mode
                    if self.debug_mode:
                        self._display_automation_summary(self.stats)
                    else:
                        # Simplified summary for non-debug mode that still shows which actions succeeded/failed
                        print(f"Success: {self.stats['successful_actions']}, Failed: {self.stats['failed_actions']}")
                        
                        # Show successful actions
                        if self.stats['successful_details']:
                            print("Successful:")
                            # Only show the most recent actions (current cycle)
                            cycle_length = len(self.actions)
                            recent_successes = self.stats['successful_details'][-cycle_length:] if cycle_length > 0 else []
                            for action_desc in recent_successes:
                                print(f"  ✓ {action_desc}")
                        
                        # Show failed actions
                        if self.stats['failed_details']:
                            print("Failed:")
                            # Only show the most recent actions (current cycle)
                            cycle_length = len(self.actions)
                            recent_failures = self.stats['failed_details'][-cycle_length:] if cycle_length > 0 else []
                            for action_desc in recent_failures:
                                print(f"  ✗ {action_desc}")
                    
                    # Check if we should continue or stop
                    if not self.loop_actions:
                        print("Automation complete")
                        break
                    else:
                        if self.debug_mode:
                            print("\nStarting next cycle...")
                        else:
                            print("Starting next cycle...")
                
                # Wait between actions
                time.sleep(self.click_interval)
                
        except KeyboardInterrupt:
            print("\nStopping automation")
            self.is_running = False
        finally:
            # Display summary
            self._display_automation_summary(self.stats)
            return self.stats
    
    def perform_action(self, action: Dict[str, Any], window_id: Optional[int] = None) -> Tuple[bool, str]:
        """
        Perform a single action.
        
        Args:
            action: Action dictionary with type and parameters
            window_id: Optional window ID to target
            
        Returns:
            Tuple of (success, action_description)
        """
        action_type = action.get('type', 'unknown')
        retry_count = action.get('retry_count', 0)
        
        # Get action description
        action_desc = self._get_action_description(action)
        
        # Try the action multiple times if retry_count > 0
        for attempt in range(retry_count + 1):
            if attempt > 0 and self.debug_mode:
                print(f"Retry attempt {attempt}/{retry_count}")
            
            try:
                # Different handling based on action type
                if action_type == 'click_position':
                    x = action.get('x', 0)
                    y = action.get('y', 0)
                    button = action.get('button', 1)
                    
                    if self.debug_mode:
                        print(f"Clicking at position ({x}, {y}) with button {button}")
                    
                    success = self.input_manager.click(x, y, button, window_id)
                    
                elif action_type == 'click_text':
                    text = action.get('text', '')
                    
                    print(f"Looking for text: '{text}'")
                    
                    # If text contains key phrases that indicate common UI elements,
                    # try using our special handling directly first - no need for OCR
                    norm_text = text.lower().strip()
                    if any(phrase in norm_text for phrase in ['resume the conversation', 'try again', 'accept']):
                        print(f"Using direct position handling for '{text}'")
                        
                        # First, take a screenshot to verify if the text is present via OCR
                        screenshot = self.image_processor.capture_window_screenshot(window_id)
                        if screenshot is not None:
                            # Try to find the text using OCR first
                            ocr_result = self.image_processor.find_text_in_screenshot(text, screenshot)
                            if ocr_result:
                                # Text was found by OCR, use those coordinates instead of fixed positions
                                x, y, confidence = ocr_result
                                print(f"Text '{text}' found via OCR at ({x}, {y})")
                                
                                # Create a visual debug marker showing click target
                                if self.debug_mode:
                                    self._create_visual_click_marker(screenshot, x, y, text)
                                
                                # Add offset for better button targeting (slightly below text center)
                                y_offset = int(10)  # Offset 10px down from text center
                                print(f"Adding Y offset of {y_offset}px for better button targeting")
                                
                                # Try clicking the target with grid pattern for better accuracy
                                success = self._perform_grid_click(x, y + y_offset, window_id, action.get('button', 1))
                                return success, action_desc

                        # OCR didn't find it or couldn't capture screenshot
                        # Try fixed positions as last resort
                        result = self._find_common_ui_element(text, window_id)
                        if result:
                            x, y, confidence = result
                            print(f"Found direct position for '{text}' at ({x}, {y})")
                            print(f"WARNING: Using fallback position - text not verified by OCR")
                            success = self.input_manager.click(x, y, action.get('button', 1), window_id)
                            return success, action_desc
                        else:
                            print(f"Text '{text}' not found, and fixed positions failed")
                            return False, action_desc
                    
                    # Standard flow for non-special UI elements
                    try:
                        # Try to take screenshot for OCR
                        screenshot = self.image_processor.capture_window_screenshot(window_id)
                        if screenshot is None:
                            print("Failed to capture screenshot")
                            # Fall back to special handling without screenshot
                            result = self._find_common_ui_element(text, window_id)
                            if result:
                                x, y, confidence = result
                                print(f"Using fallback position for '{text}' at ({x}, {y})")
                                success = self.input_manager.click(x, y, action.get('button', 1), window_id)
                                return success, action_desc
                            return False, action_desc
                        
                        # Try direct OCR first
                        result = self.image_processor.find_text_in_screenshot(text, screenshot)
                        
                        # If OCR failed, try special handling for common UI elements
                        if not result:
                            result = self._find_common_ui_element(text, window_id)
                            if result:
                                print(f"Found UI element '{text}' using special handling")
                        
                        if result:
                            x, y, confidence = result
                            print(f"Found text at ({x}, {y}) with confidence {confidence:.2f}")
                            
                            # Create a visual debug marker showing click target
                            if self.debug_mode:
                                self._create_visual_click_marker(screenshot, x, y, text)
                            
                            # Add offset for better button targeting (slightly below text center)
                            y_offset = int(10)  # Offset 10px down from text center
                            print(f"Adding Y offset of {y_offset}px for better button targeting")
                            
                            # Try clicking the target with grid pattern for better accuracy
                            success = self._perform_grid_click(x, y + y_offset, window_id, action.get('button', 1))
                        else:
                            print(f"Text '{text}' not found")
                            success = False
                    except Exception as e:
                        print(f"Error during text processing: {e}")
                        # Last resort fallback for critical UI elements
                        result = self._find_common_ui_element(text, window_id)
                        if result:
                            x, y, confidence = result
                            print(f"Using emergency fallback for '{text}' at ({x}, {y})")
                            success = self.input_manager.click(x, y, action.get('button', 1), window_id)
                            return success, action_desc
                        success = False
                
                elif action_type == 'click_template':
                    template = action.get('template', '')
                    
                    if not os.path.exists(template):
                        if self.debug_mode:
                            print(f"Template file not found: {template}")
                        return False, action_desc
                    
                    if self.debug_mode:
                        print(f"Looking for template: {template}")
                    
                    # Take screenshot
                    screenshot = self.image_processor.capture_window_screenshot(window_id)
                    if screenshot is None:
                        if self.debug_mode:
                            print("Failed to capture screenshot")
                        return False, action_desc
                    
                    # Find template in screenshot
                    result = self.image_processor.find_template_in_screenshot(
                        template, screenshot, threshold=action.get('threshold', 0.7)
                    )
                    
                    if result:
                        x, y, confidence = result
                        
                        if self.debug_mode:
                            print(f"Found template at ({x}, {y}) with confidence {confidence:.2f}")
                        
                        # Click at the template position
                        success = self.input_manager.click(x, y, action.get('button', 1), window_id)
                    else:
                        if self.debug_mode:
                            print(f"Template not found")
                        success = False
                
                elif action_type == 'type_text':
                    text = action.get('text', '')
                    
                    if self.debug_mode:
                        print(f"Typing text: '{text}'")
                    else:
                        print(f"Typing text ({len(text)} chars)")
                    
                    success = self.input_manager.type_text(text, window_id)
                
                elif action_type == 'wait':
                    duration = action.get('duration', 1.0)
                    
                    if self.debug_mode:
                        print(f"Waiting for {duration} seconds")
                    
                    time.sleep(duration)
                    success = True
                
                else:
                    if self.debug_mode:
                        print(f"Unknown action type: {action_type}")
                    success = False
                
                # If successful, return
                if success:
                    return True, action_desc
                
                # If not successful and we have more retries, continue to next attempt
                if attempt < retry_count:
                    time.sleep(0.5)  # Small delay between retries
            
            except Exception as e:
                print(f"Error during text processing: {e}")
                # Last resort fallback for critical UI elements
                result = self._find_common_ui_element(action.get('text', ''), window_id)
                if result:
                    x, y, confidence = result
                    print(f"Using emergency fallback for '{action.get('text', '')}' at ({x}, {y})")
                    success = self.input_manager.click(x, y, action.get('button', 1), window_id)
                    return success, action_desc
                success = False
        
        # If we get here, all attempts failed
        return False, action_desc
    
    def _find_common_ui_element(self, text: str, window_id: int) -> Optional[Tuple[int, int, float]]:
        """
        Specialized helper to find common UI elements that OCR might miss.
        
        Args:
            text: The text to find
            window_id: The window ID to search in
            
        Returns:
            Tuple of (x, y, confidence) if found, None otherwise
        """
        # Get window dimensions
        window_info = self.window_manager.get_window_by_id(window_id)
        if not window_info:
            print(f"Could not get window info for window ID {window_id}")
            return None
            
        width, height = window_info['width'], window_info['height']
        print(f"Window dimensions: {width}x{height}")
        
        # Normalized text for case-insensitive comparison
        norm_text = text.lower().strip()
        
        # Handle specific UI elements
        if "resume the conversation" in norm_text or "resume conversation" in norm_text:
            # Usually appears at the bottom of message windows
            # Try multiple possible positions from most likely to least likely
            print(f"Trying multiple positions for 'resume the conversation'")
            
            # Create a list of potential positions to try for this element
            # Format: [(x_ratio, y_ratio, description)]
            # Where x_ratio and y_ratio are proportions of window width/height
            positions = [
                (0.5, 0.9, "bottom center"),            # 90% down from top, centered
                (0.5, 0.85, "slightly above bottom"),  # 85% down from top, centered
                (0.5, 0.95, "very bottom center"),     # 95% down from top, centered
                (0.5, 0.8, "lower center"),           # 80% down from top, centered
                (0.5, 0.75, "mid-lower center"),      # 75% down from top, centered
                (0.5, 0.5, "window center")           # Center of window (last resort)
            ]
            
            # Log each position we're trying
            for ratio_x, ratio_y, desc in positions:
                x = int(width * ratio_x)
                y = int(height * ratio_y)
                print(f"  - Trying {desc} position at ({x}, {y})")
            
            # Return the position we think is most likely to work
            x = int(width * 0.5)  # Center horizontally
            y = int(height * 0.9)  # Near bottom
            return (x, y, 0.95)  # High confidence
            
        elif "try again" in norm_text:
            # Usually appears as a button, often at bottom or center
            print(f"Trying multiple positions for 'Try Again'")
            
            positions = [
                (0.5, 0.9, "bottom center"),          # Bottom center
                (0.5, 0.8, "lower center"),         # Lower center
                (0.5, 0.5, "window center")         # Center of window
            ]
            
            # Log positions we're trying
            for ratio_x, ratio_y, desc in positions:
                x = int(width * ratio_x)
                y = int(height * ratio_y)
                print(f"  - Trying {desc} position at ({x}, {y})")
            
            # Return the most likely position
            x = int(width * 0.5)  # Center horizontally
            y = int(height * 0.9)  # Bottom of window
            return (x, y, 0.9)  # Good confidence
            
        elif "accept" in norm_text or "continue" in norm_text or "ok" in norm_text:
            # Usually appears as a button at the bottom of dialog windows
            print(f"Trying multiple positions for '{text}'")
            
            positions = [
                (0.5, 0.85, "dialog bottom button"),   # Standard dialog button position
                (0.75, 0.9, "bottom right"),         # Bottom right (common for "OK")
                (0.5, 0.75, "lower center"),        # Lower center
                (0.5, 0.5, "window center")         # Center of window (last resort)
            ]
            
            # Log positions we're trying
            for ratio_x, ratio_y, desc in positions:
                x = int(width * ratio_x)
                y = int(height * ratio_y)
                print(f"  - Trying {desc} position at ({x}, {y})")
            
            # Return position most likely to work
            x = int(width * 0.75)  # Slightly to the right
            y = int(height * 0.9)  # Near bottom
            return (x, y, 0.9)  # Good confidence
        
        # Handle general UI patterns based on window size
        elif any(pattern in norm_text for pattern in ["yes", "no", "cancel", "confirm", "submit", "send", "done"]):
            print(f"Trying common button positions for '{text}'")
            
            # Different button patterns based on dialog/window type
            button_patterns = {
                "yes": [(0.4, 0.85, "yes button")],      # Yes is usually on the left side of No
                "no": [(0.6, 0.85, "no button")],       # No is usually on the right side of Yes
                "cancel": [(0.7, 0.85, "cancel button")], # Cancel usually on right side
                "confirm": [(0.5, 0.85, "confirm button")],
                "submit": [(0.5, 0.9, "submit button")],
                "send": [(0.9, 0.9, "send button")],    # Send often bottom right
                "done": [(0.5, 0.9, "done button")]
            }
            
            # Find matching pattern
            for pattern, positions in button_patterns.items():
                if pattern in norm_text:
                    for ratio_x, ratio_y, desc in positions:
                        x = int(width * ratio_x)
                        y = int(height * ratio_y)
                        print(f"  - Trying {desc} position at ({x}, {y})")
                        return (x, y, 0.8)
        
        # No special handling for this text
        return None
        
    def _get_action_description(self, action: Dict[str, Any]) -> str:
        """
        Get a descriptive string for an action.
        
        Args:
            action: Action dictionary
            
        Returns:
            Description string
        """
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
    
    def _display_automation_summary(self, stats: Dict[str, Any]) -> None:
        """
        Display a summary of automation statistics.
        
        Args:
            stats: Statistics dictionary
        """
        run_time = time.time() - stats['start_time']
        
        print("\n" + "-"*40)
        print("Automation Summary")
        print("-"*40)
        print(f"Total run time: {run_time:.1f} seconds")
        print(f"Cycles completed: {stats['cycles_completed']}")
        print(f"Successful actions: {stats['successful_actions']}")
        print(f"Failed actions: {stats['failed_actions']}")
        
        # In non-debug mode, only show the specific successful/failed actions
        # In debug mode, also show the type breakdown
        if stats['action_counts'] and self.debug_mode:
            print("\nAction type breakdown:")
            for action_type, counts in stats['action_counts'].items():
                success = counts['success']
                fail = counts['fail']
                total = success + fail
                if total > 0:
                    success_rate = (success / total) * 100
                    print(f"  {action_type}: {success} successes, {fail} failures ({success_rate:.1f}% success rate)")
        
        # Always show successful and failed actions in the summary
        if stats['successful_details']:
            print("\nSuccessful actions:")
            # Take only the most recent cycle's worth of actions
            cycle_length = len(self.actions)
            recent_successes = stats['successful_details'][-cycle_length:] if cycle_length > 0 else []
            for action_desc in recent_successes:
                print(f"  ✓ {action_desc}")
                
        if stats['failed_details']:
            print("\nFailed actions:")
            # Take only the most recent cycle's worth of actions
            cycle_length = len(self.actions)
            recent_failures = stats['failed_details'][-cycle_length:] if cycle_length > 0 else []
            for action_desc in recent_failures:
                print(f"  ✗ {action_desc}")
                
        print("-"*40)
    
    def stop(self) -> None:
        """Stop the current automation."""
        self.is_running = False
        print("Stopping automation")
    
    def cleanup(self) -> None:
        """Clean up resources."""
        self.input_manager.cleanup()
        self.window_manager.cleanup()
        self.image_processor.cleanup()
    
    def _screenshots_are_different(self, screenshot1, screenshot2, threshold=0.02):
        """
        Compare two screenshots to see if they're significantly different.
        
        Args:
            screenshot1: First screenshot
            screenshot2: Second screenshot
            threshold: Difference threshold (0-1)
            
        Returns:
            Whether the screenshots are different
        """
        try:
            # Convert to numpy arrays if they're PIL images
            if hasattr(screenshot1, 'getdata') and hasattr(screenshot2, 'getdata'):
                import numpy as np
                screenshot1 = np.array(screenshot1)
                screenshot2 = np.array(screenshot2)
            
            # Check if dimensions match
            if screenshot1.shape != screenshot2.shape:
                return True  # Different dimensions means they're different
            
            # Calculate difference
            import numpy as np
            diff = np.abs(screenshot1.astype(np.float32) - screenshot2.astype(np.float32))
            diff_ratio = np.mean(diff) / 255.0  # Normalize to 0-1 range
            
            if self.debug_mode:
                print(f"Screenshot difference: {diff_ratio:.4f} (threshold: {threshold})")
            
            return diff_ratio > threshold
            
        except Exception as e:
            if self.debug_mode:
                print(f"Error comparing screenshots: {e}")
            # If we can't compare, assume they're the same
            return False
    
    def _perform_grid_click(self, center_x, center_y, window_id, button=1, grid_size=3, spacing=5):
        """
        Perform a grid of clicks around a central point for better accuracy.
        
        Args:
            center_x: Center X coordinate
            center_y: Center Y coordinate
            window_id: Window ID
            button: Mouse button (1=left, 2=middle, 3=right)
            grid_size: Grid size (e.g., 3 for 3x3 grid)
            spacing: Spacing between grid points in pixels
            
        Returns:
            Whether any click was successful
        """
        # First, try center point
        if self.debug_mode:
            print(f"Performing grid click centered at ({center_x}, {center_y})")
            
        # First try direct center
        success = self.input_manager.click(center_x, center_y, button, window_id)
        if success and not self.debug_mode:
            return True
            
        # If center didn't work or we're debugging, try grid pattern
        half_size = grid_size // 2
        for dx in range(-half_size, half_size + 1):
            for dy in range(-half_size, half_size + 1):
                # Skip center point as we already tried it
                if dx == 0 and dy == 0:
                    continue
                    
                # Calculate grid point
                x = center_x + dx * spacing
                y = center_y + dy * spacing
                
                if self.debug_mode:
                    print(f"  Grid click at offset ({dx*spacing}, {dy*spacing}) -> ({x}, {y})")
                    
                # Try click
                click_success = self.input_manager.click(x, y, button, window_id)
                success = success or click_success
                
                # Small delay between clicks
                time.sleep(0.05)
                
        return success
        
    def _create_visual_click_marker(self, screenshot, x, y, text, radius=30):
        """
        Create a debug image showing where a click will happen.
        
        Args:
            screenshot: Screenshot to mark up
            x: Click X coordinate
            y: Click Y coordinate
            text: Text being clicked
            radius: Radius of marker circle
        """
        try:
            import cv2
            import numpy as np
            from PIL import Image
            import os
            
            # Convert PIL to OpenCV if needed
            if hasattr(screenshot, 'getdata'):
                screenshot_cv = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
            else:
                screenshot_cv = screenshot.copy()
                
            # Create a copy for marking
            marked = screenshot_cv.copy()
            
            # Draw targeting elements
            # Outer circle
            cv2.circle(marked, (x, y), radius, (0, 0, 255), 2)
            # Cross-hairs
            cv2.line(marked, (x-radius, y), (x+radius, y), (0, 0, 255), 1)
            cv2.line(marked, (x, y-radius), (x, y+radius), (0, 0, 255), 1)
            # Center dot
            cv2.circle(marked, (x, y), 3, (0, 255, 0), -1)
            
            # Draw text label with target element
            font = cv2.FONT_HERSHEY_SIMPLEX
            cv2.putText(marked, f"Target: {text}", (x+10, y-10), font, 0.5, (0, 255, 0), 2)
            
            # Y-offset target dot (where we're actually clicking)
            y_offset = y + 10
            cv2.circle(marked, (x, y_offset), 5, (255, 0, 0), -1)
            cv2.putText(marked, "Click", (x+10, y_offset), font, 0.5, (255, 0, 0), 2)
            
            # Save the image
            app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            debug_dir = os.path.join(app_dir, "debug")
            os.makedirs(debug_dir, exist_ok=True)
            debug_path = os.path.join(debug_dir, f"click_target_{int(time.time())}.png")
            
            cv2.imwrite(debug_path, marked)
            print(f"\n*** Visual click indicator saved to: {debug_path} ***\n")
            
        except Exception as e:
            print(f"Error creating visual click marker: {e}")
