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

class ActionController:
    """
    Controls the execution of automation actions and sequences.
    """
    
    def __init__(self, input_manager: InputManager, window_manager: WindowManager, 
                image_processor: ImageProcessor, debug_mode: bool = False):
        """
        Initialize the action controller.
        
        Args:
            input_manager: InputManager instance for input operations
            window_manager: WindowManager instance for window operations
            image_processor: ImageProcessor instance for image operations
            debug_mode: Whether to output debug information
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
    
    def load_actions(self, config_file: str) -> bool:
        """
        Load actions from a configuration file.
        
        Args:
            config_file: Path to the configuration file
            
        Returns:
            Whether loading was successful
        """
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
            
            # Extract actions from config
            self.actions = config.get('actions', [])
            
            # Extract other settings if present
            self.loop_actions = config.get('loop_actions', False)
            self.continuous_mode = config.get('continuous_mode', False)
            self.click_interval = config.get('click_interval', 0.1)
            
            if self.debug_mode:
                print(f"Loaded {len(self.actions)} actions from {config_file}")
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
    
    def run_automation(self, window_id: Optional[int] = None, max_cycles: int = 0) -> Dict[str, Any]:
        """
        Run the automation sequence.
        
        Args:
            window_id: Optional window ID to target
            max_cycles: Maximum number of cycles (0 = unlimited)
            
        Returns:
            Statistics about the automation run
        """
        # Reset statistics
        self.stats = self._create_stats()
        
        try:
            self.is_running = True
            action_index = 0
            
            print(f"Starting automation with {len(self.actions)} actions")
            
            while self.is_running:
                # Check if we've reached the maximum cycles
                if max_cycles > 0 and self.stats['cycles_completed'] >= max_cycles:
                    print(f"Reached maximum cycles ({max_cycles})")
                    break
                
                # Get the current action
                action = self.actions[action_index]
                
                if self.debug_mode:
                    print(f"\nPerforming action: {action.get('type', 'unknown')}")
                
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
                    
                    if not self.debug_mode:
                        print(f"✓ {action_desc}")
                else:
                    self.stats['failed_actions'] += 1
                    self.stats['action_counts'][action_type]['fail'] += 1
                    self.stats['failed_details'].append(action_desc)
                    
                    if not self.debug_mode:
                        print(f"✗ {action_desc}")
                
                # Handle required actions
                if not success and action.get('required', False):
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
                    
                    if self.debug_mode:
                        print(f"Looking for text: '{text}'")
                    
                    # Take screenshot
                    screenshot = self.image_processor.capture_window_screenshot(window_id)
                    if screenshot is None:
                        if self.debug_mode:
                            print("Failed to capture screenshot")
                        return False, action_desc
                    
                    # Find text in screenshot
                    result = self.image_processor.find_text_in_screenshot(text, screenshot)
                    if result:
                        x, y, confidence = result
                        
                        if self.debug_mode:
                            print(f"Found text at ({x}, {y}) with confidence {confidence:.2f}")
                        
                        # Click at the text position
                        success = self.input_manager.click(x, y, action.get('button', 1), window_id)
                    else:
                        if self.debug_mode:
                            print(f"Text '{text}' not found")
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
                if self.debug_mode:
                    print(f"Error performing action: {e}")
                
                # If we have more retries, continue to next attempt
                if attempt < retry_count:
                    time.sleep(0.5)  # Small delay between retries
        
        # If we get here, all attempts failed
        return False, action_desc
    
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
