#!/usr/bin/env python3
"""
Error Recovery Module

Provides strategies for recovering from failures during automation.
Implements retry logic, fallback actions, and checkpoint verification.
"""

import os
import time
import json
import logging
from typing import List, Dict, Tuple, Optional, Any, Callable
from enum import Enum

from .window_manager import WindowManager
from .image_processor import ImageProcessor

class RecoveryStrategy(Enum):
    """Types of recovery strategies."""
    RETRY = "retry"               # Simply retry the same action
    WAIT_AND_RETRY = "wait"       # Wait longer and retry
    FALLBACK = "fallback"         # Use an alternative fallback action
    CHECKPOINT = "checkpoint"     # Return to last successful checkpoint
    SKIP = "skip"                 # Skip the failed action and continue
    ABORT = "abort"               # Abort the automation sequence

class RecoveryAction:
    """
    Represents a recovery action to take when a primary action fails.
    """
    
    def __init__(self, strategy: RecoveryStrategy, 
                 params: Optional[Dict[str, Any]] = None,
                 fallback_action: Optional[Dict[str, Any]] = None):
        """
        Initialize a recovery action.
        
        Args:
            strategy: Recovery strategy to use
            params: Parameters for the strategy (e.g., retry count, wait time)
            fallback_action: Alternative action to perform for fallback strategy
        """
        self.strategy = strategy
        self.params = params or {}
        self.fallback_action = fallback_action
        
        # Set default parameters based on strategy
        if strategy == RecoveryStrategy.RETRY and 'max_retries' not in self.params:
            self.params['max_retries'] = 3
            
        if (strategy == RecoveryStrategy.WAIT_AND_RETRY and 
            'wait_time' not in self.params):
            self.params['wait_time'] = 2.0  # Default to 2 seconds

class ErrorRecoveryManager:
    """
    Manages error recovery for failed actions.
    """
    
    def __init__(self, window_manager: WindowManager, 
                 image_processor: ImageProcessor, debug_mode: bool = False):
        """
        Initialize the error recovery manager.
        
        Args:
            window_manager: WindowManager instance
            image_processor: ImageProcessor instance
            debug_mode: Whether to output debug information
        """
        self.window_manager = window_manager
        self.image_processor = image_processor
        self.debug_mode = debug_mode
        
        # Configure logging
        self.logger = logging.getLogger('error_recovery')
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
        
        self.logger.setLevel(logging.DEBUG if debug_mode else logging.INFO)
        
        # Initialize checkpoint system
        self.checkpoints = []
        self.recovery_history = []
    
    def create_checkpoint(self, action_index: int, 
                         window_id: Optional[int] = None,
                         screenshot: Any = None) -> Dict[str, Any]:
        """
        Create a checkpoint that can be used to resume from if a future action fails.
        
        Args:
            action_index: Current action index
            window_id: Window ID for the checkpoint
            screenshot: Optional screenshot at checkpoint time
            
        Returns:
            Checkpoint dictionary
        """
        checkpoint = {
            'action_index': action_index,
            'window_id': window_id,
            'timestamp': time.time(),
        }
        
        # Take a screenshot if one wasn't provided
        if screenshot is None and window_id is not None:
            try:
                screenshot = self.image_processor.capture_window_screenshot(window_id)
                # Convert numpy array to PIL Image if needed
                if hasattr(screenshot, 'shape') and not hasattr(screenshot, 'save'):
                    import numpy as np
                    from PIL import Image
                    if isinstance(screenshot, np.ndarray):
                        screenshot = Image.fromarray(screenshot)
                self.logger.debug(f"Created checkpoint screenshot at action index {action_index}")
            except Exception as e:
                self.logger.warning(f"Failed to capture checkpoint screenshot: {e}")
                screenshot = None
        
        if screenshot is not None:
            # Save the screenshot to a temporary file in the app directory
            app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            checkpoint_dir = os.path.join(app_dir, "config", "checkpoints")
            os.makedirs(checkpoint_dir, exist_ok=True)
            
            screenshot_path = os.path.join(
                checkpoint_dir, 
                f"checkpoint_{action_index}_{int(time.time())}.png"
            )
            
            try:
                screenshot.save(screenshot_path)
                checkpoint['screenshot_path'] = screenshot_path
                self.logger.debug(f"Saved checkpoint screenshot to {screenshot_path}")
            except Exception as e:
                self.logger.warning(f"Failed to save checkpoint screenshot: {e}")
        
        # Add to checkpoints list
        self.checkpoints.append(checkpoint)
        
        # Keep only the last 5 checkpoints to avoid using too much disk space
        if len(self.checkpoints) > 5:
            old_checkpoint = self.checkpoints.pop(0)
            if 'screenshot_path' in old_checkpoint:
                try:
                    if os.path.exists(old_checkpoint['screenshot_path']):
                        os.remove(old_checkpoint['screenshot_path'])
                        self.logger.debug(f"Removed old checkpoint screenshot {old_checkpoint['screenshot_path']}")
                except Exception as e:
                    self.logger.warning(f"Failed to remove old checkpoint screenshot: {e}")
        
        return checkpoint
    
    def get_latest_checkpoint(self) -> Optional[Dict[str, Any]]:
        """
        Get the most recent checkpoint.
        
        Returns:
            Latest checkpoint or None if no checkpoints
        """
        if not self.checkpoints:
            return None
        return self.checkpoints[-1]
    
    def get_checkpoint_before_action(self, action_index: int) -> Optional[Dict[str, Any]]:
        """
        Get the most recent checkpoint before the specified action index.
        
        Args:
            action_index: Action index to find checkpoint before
            
        Returns:
            Checkpoint before specified action or None if no valid checkpoint
        """
        valid_checkpoints = [cp for cp in self.checkpoints if cp['action_index'] < action_index]
        if not valid_checkpoints:
            return None
        return valid_checkpoints[-1]
    
    def apply_recovery_strategy(self, failed_action: Dict[str, Any], 
                               recovery: RecoveryAction,
                               action_index: int,
                               window_id: Optional[int] = None) -> Tuple[bool, Optional[Dict[str, Any]], int]:
        """
        Apply a recovery strategy after an action failure.
        
        Args:
            failed_action: The action that failed
            recovery: Recovery action to apply
            action_index: Index of the failed action
            window_id: Window ID for the action
            
        Returns:
            Tuple of (success, next_action, next_action_index)
            - success: Whether recovery was successful
            - next_action: The next action to perform (may be the original or a fallback)
            - next_action_index: The index of the next action to perform
        """
        strategy = recovery.strategy
        params = recovery.params
        
        self.logger.info(f"Applying recovery strategy: {strategy.value} for action at index {action_index}")
        
        # Record recovery attempt
        self.recovery_history.append({
            'timestamp': time.time(),
            'action_index': action_index,
            'action_type': failed_action.get('type', 'unknown'),
            'strategy': strategy.value,
            'params': params
        })
        
        # Apply the strategy
        if strategy == RecoveryStrategy.RETRY:
            max_retries = params.get('max_retries', 3)
            self.logger.info(f"Will retry up to {max_retries} times")
            return True, failed_action, action_index
            
        elif strategy == RecoveryStrategy.WAIT_AND_RETRY:
            wait_time = params.get('wait_time', 2.0)
            self.logger.info(f"Waiting {wait_time} seconds before retry")
            time.sleep(wait_time)
            return True, failed_action, action_index
            
        elif strategy == RecoveryStrategy.FALLBACK:
            if recovery.fallback_action:
                self.logger.info(f"Using fallback action: {recovery.fallback_action.get('type', 'unknown')}")
                return True, recovery.fallback_action, action_index
            else:
                self.logger.warning("No fallback action specified")
                return False, None, action_index
            
        elif strategy == RecoveryStrategy.CHECKPOINT:
            # Find the most recent checkpoint before the failed action
            checkpoint = self.get_checkpoint_before_action(action_index)
            if checkpoint:
                self.logger.info(f"Returning to checkpoint at action index {checkpoint['action_index']}")
                return True, None, checkpoint['action_index']
            else:
                self.logger.warning("No valid checkpoint found")
                return False, None, action_index
            
        elif strategy == RecoveryStrategy.SKIP:
            self.logger.info(f"Skipping failed action at index {action_index}")
            return True, None, action_index + 1
            
        elif strategy == RecoveryStrategy.ABORT:
            self.logger.info("Aborting automation sequence")
            return False, None, -1
        
        return False, None, action_index
    
    def get_recovery_for_action(self, action: Dict[str, Any]) -> RecoveryAction:
        """
        Get the appropriate recovery strategy for an action.
        
        Args:
            action: Action to get recovery for
            
        Returns:
            Recovery action
        """
        # Check if action has explicit recovery instructions
        if 'on_failure' in action:
            on_failure = action['on_failure']
            
            # Parse the specified strategy
            try:
                strategy = RecoveryStrategy(on_failure.get('strategy', 'retry'))
                params = on_failure.get('params', {})
                fallback = on_failure.get('fallback_action')
                
                return RecoveryAction(strategy, params, fallback)
            except (ValueError, KeyError):
                self.logger.warning(f"Invalid recovery strategy in action, using default")
        
        # Default recovery strategies based on action type
        action_type = action.get('type', 'unknown')
        
        if action_type == 'click_text':
            # For text clicking, retry a few times with increasing delays
            return RecoveryAction(
                RecoveryStrategy.WAIT_AND_RETRY,
                {'max_retries': 3, 'wait_time': 2.0}
            )
            
        elif action_type == 'click_template':
            # For template matching, retry with wait
            return RecoveryAction(
                RecoveryStrategy.WAIT_AND_RETRY,
                {'max_retries': 3, 'wait_time': 1.5}
            )
            
        elif action_type == 'click_position':
            # For fixed position clicks, simple retry
            return RecoveryAction(
                RecoveryStrategy.RETRY,
                {'max_retries': 2}
            )
            
        elif action_type == 'type_text':
            # For typing, simple retry
            return RecoveryAction(
                RecoveryStrategy.RETRY,
                {'max_retries': 2}
            )
            
        else:
            # Default strategy for other action types
            return RecoveryAction(
                RecoveryStrategy.RETRY,
                {'max_retries': 1}
            )
    
    def analyze_failure_pattern(self) -> Dict[str, Any]:
        """
        Analyze failure patterns to provide insights.
        
        Returns:
            Analysis of failure patterns
        """
        if not self.recovery_history:
            return {'patterns': [], 'recommendations': []}
        
        # Count failures by action type and strategy
        action_failures = {}
        strategy_usage = {}
        
        for recovery in self.recovery_history:
            action_type = recovery['action_type']
            strategy = recovery['strategy']
            
            if action_type not in action_failures:
                action_failures[action_type] = 0
            action_failures[action_type] += 1
            
            if strategy not in strategy_usage:
                strategy_usage[strategy] = 0
            strategy_usage[strategy] += 1
        
        # Identify patterns
        patterns = []
        recommendations = []
        
        # Check for frequently failing actions
        for action_type, count in action_failures.items():
            if count >= 3:
                patterns.append(f"Action type '{action_type}' failed {count} times")
                
                if action_type == 'click_text':
                    recommendations.append(
                        "Text recognition failures are common. Consider using template matching instead."
                    )
                elif action_type == 'click_template':
                    recommendations.append(
                        "Template matching failures may indicate UI changes. Consider updating templates."
                    )
                elif action_type == 'click_position':
                    recommendations.append(
                        "Position-based clicking is fragile. Consider using text or template matching."
                    )
        
        # Check for recovery strategy effectiveness
        if RecoveryStrategy.RETRY.value in strategy_usage and strategy_usage[RecoveryStrategy.RETRY.value] >= 5:
            patterns.append(f"Simple retry used {strategy_usage[RecoveryStrategy.RETRY.value]} times")
            recommendations.append(
                "Simple retries are being used frequently. Consider adding wait times between retries."
            )
        
        if RecoveryStrategy.CHECKPOINT.value in strategy_usage and strategy_usage[RecoveryStrategy.CHECKPOINT.value] >= 3:
            patterns.append(f"Checkpoint recovery used {strategy_usage[RecoveryStrategy.CHECKPOINT.value]} times")
            recommendations.append(
                "Frequent checkpoint usage suggests unstable UI elements. Consider more robust detection methods."
            )
        
        return {
            'patterns': patterns,
            'recommendations': recommendations,
            'action_failures': action_failures,
            'strategy_usage': strategy_usage
        }
    
    def cleanup(self) -> None:
        """Clean up resources used by the error recovery manager."""
        # Remove checkpoint screenshots
        for checkpoint in self.checkpoints:
            if 'screenshot_path' in checkpoint:
                try:
                    if os.path.exists(checkpoint['screenshot_path']):
                        os.remove(checkpoint['screenshot_path'])
                        self.logger.debug(f"Removed checkpoint screenshot {checkpoint['screenshot_path']}")
                except Exception as e:
                    self.logger.warning(f"Failed to remove checkpoint screenshot: {e}")
