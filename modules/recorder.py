#!/usr/bin/env python3
"""
Recorder Module

Records user actions for later replay in automation sequences.
Captures mouse clicks and keyboard input within a specified window.
"""

import os
import time
import json
import threading
from typing import List, Dict, Tuple, Optional, Any, Callable
from datetime import datetime

from Xlib import X
from Xlib.display import Display
from Xlib.ext import record
from Xlib.protocol import rq

from .window_manager import WindowManager
from .image_processor import ImageProcessor

class ActionRecorder:
    """
    Records user actions for automation.
    """
    
    def __init__(self, window_manager: WindowManager, 
                 image_processor: ImageProcessor, debug_mode: bool = False):
        """
        Initialize the action recorder.
        
        Args:
            window_manager: WindowManager instance
            image_processor: ImageProcessor instance
            debug_mode: Whether to output debug information
        """
        self.window_manager = window_manager
        self.image_processor = image_processor
        self.debug_mode = debug_mode
        
        # X11 display for recording
        self.display = Display()
        self.record_display = Display()
        
        # Recording state
        self.is_recording = False
        self.record_thread = None
        self.start_time = 0
        self.actions = []
        self.target_window_id = None
        self.window_geometry = None
        self.last_action_time = 0
        self.record_keyboard = True
        self.record_mouse = True
        
        # Context for Xlib recording
        self.ctx = None
    
    def start_recording(self, window_id: int, record_keyboard: bool = True,
                      record_mouse: bool = True) -> bool:
        """
        Start recording user actions within a specific window.
        
        Args:
            window_id: ID of the window to record
            record_keyboard: Whether to record keyboard events
            record_mouse: Whether to record mouse events
            
        Returns:
            Whether recording started successfully
        """
        if self.is_recording:
            if self.debug_mode:
                print("Already recording")
            return False
        
        # Get window geometry to convert coordinates
        window = self.window_manager.get_window_by_id(window_id)
        if not window:
            if self.debug_mode:
                print(f"Window ID {window_id} not found")
            return False
        
        self.target_window_id = window_id
        self.window_geometry = window
        self.record_keyboard = record_keyboard
        self.record_mouse = record_mouse
        
        # Reset actions list and start time
        self.actions = []
        self.start_time = time.time()
        self.last_action_time = self.start_time
        
        # Create record context
        self.ctx = self.record_display.record_create_context(
            0,
            [record.AllClients],
            [{
                'core_requests': (0, 0),
                'core_replies': (0, 0),
                'ext_requests': (0, 0, 0, 0),
                'ext_replies': (0, 0, 0, 0),
                'delivered_events': (0, 0),
                'device_events': (X.ButtonPressMask | X.ButtonReleaseMask | 
                                X.KeyPressMask | X.KeyReleaseMask | 
                                X.MotionNotifyMask),
                'errors': (0, 0),
                'client_started': False,
                'client_died': False,
            }]
        )
        
        # Start recording thread
        self.is_recording = True
        self.record_thread = threading.Thread(target=self._record_thread)
        self.record_thread.daemon = True
        self.record_thread.start()
        
        if self.debug_mode:
            print(f"Started recording in window {window_id} ({window['name']})")
            if record_keyboard and record_mouse:
                print("Recording keyboard and mouse events")
            elif record_keyboard:
                print("Recording keyboard events only")
            elif record_mouse:
                print("Recording mouse events only")
        
        return True
    
    def stop_recording(self) -> List[Dict[str, Any]]:
        """
        Stop recording user actions.
        
        Returns:
            List of recorded actions
        """
        if not self.is_recording:
            if self.debug_mode:
                print("Not recording")
            return self.actions
        
        # Stop recording
        self.is_recording = False
        
        # Stop record context
        if self.ctx:
            self.record_display.record_free_context(self.ctx)
            self.ctx = None
        
        if self.record_thread:
            self.record_thread.join(timeout=1.0)
        
        # Calculate relative timing for all actions
        if self.actions:
            self._normalize_action_timing()
        
        if self.debug_mode:
            print(f"Stopped recording, captured {len(self.actions)} actions")
            for i, action in enumerate(self.actions):
                print(f"  {i+1}. {action['type']}")
        
        return self.actions
    
    def _record_thread(self) -> None:
        """Record thread function."""
        try:
            self.record_display.record_enable_context(self.ctx, self._process_event)
            # This is a blocking call that returns after record_disable_context()
        except Exception as e:
            if self.debug_mode:
                print(f"Recording error: {e}")
        finally:
            # Clean up
            if self.ctx:
                self.record_display.record_free_context(self.ctx)
                self.ctx = None
            
            if self.debug_mode:
                print("Recording thread ended")
    
    def _process_event(self, reply) -> None:
        """
        Process X11 events during recording.
        
        Args:
            reply: X11 event reply
        """
        if not self.is_recording:
            return
        
        if reply.category != record.FromServer:
            return
        
        if reply.client_swapped:
            # Not handling swapped clients
            return
        
        data = reply.data
        while len(data):
            event, data = rq.EventField(None).parse_binary_value(
                data, self.record_display.display, None, None)
            
            # Skip events for windows other than our target
            window_id = self._get_event_window_id(event)
            if window_id is None or window_id != self.target_window_id:
                continue
            
            current_time = time.time()
            
            if event.type == X.ButtonPress and self.record_mouse:
                # Mouse button press
                self._add_mouse_click_action(event, current_time)
            
            elif event.type == X.KeyPress and self.record_keyboard:
                # Keyboard key press
                self._add_keyboard_action(event, current_time)
    
    def _get_event_window_id(self, event) -> Optional[int]:
        """
        Get the window ID from an X11 event.
        
        Args:
            event: X11 event
            
        Returns:
            Window ID or None
        """
        if hasattr(event, 'event'):
            return event.event
        return None
    
    def _add_mouse_click_action(self, event, timestamp: float) -> None:
        """
        Add a mouse click action to the recording.
        
        Args:
            event: X11 event
            timestamp: Event timestamp
        """
        # Get relative coordinates within the window
        x_rel, y_rel = self._get_relative_coordinates(event.root_x, event.root_y)
        
        # Only record if coordinates are within window bounds
        if x_rel < 0 or y_rel < 0 or x_rel > self.window_geometry['width'] or y_rel > self.window_geometry['height']:
            return
        
        # Add action
        action = {
            'type': 'click_position',
            'x': x_rel,
            'y': y_rel,
            'button': event.detail,  # 1=left, 3=right, etc.
            'timestamp': timestamp
        }
        
        self.actions.append(action)
        self.last_action_time = timestamp
        
        if self.debug_mode:
            print(f"Recorded mouse click: button={event.detail}, pos=({x_rel}, {y_rel})")
            
            # Take a screenshot and check if there's text or an image at the clicked location
            try:
                screenshot = self.image_processor.capture_window_screenshot(self.target_window_id)
                if screenshot:
                    # Try to find text near the click
                    words = self.image_processor.get_text_in_region(
                        screenshot, 
                        x_rel - 50, y_rel - 50, 
                        100, 100
                    )
                    if words:
                        print(f"  Text detected near click: {', '.join(words)}")
                        
                        # If we find text, add a click_text action as an alternative
                        # This can make the automation more robust
                        for word in words:
                            if len(word) > 3:  # Only consider words with >3 chars
                                alt_action = {
                                    'type': 'click_text',
                                    'text': word,
                                    'button': event.detail,
                                    'timestamp': timestamp,
                                    'is_alternative': True
                                }
                                self.actions.append(alt_action)
                                print(f"  Added alternative text click action for: '{word}'")
                                break
            except Exception as e:
                if self.debug_mode:
                    print(f"Error analyzing click position: {e}")
    
    def _add_keyboard_action(self, event, timestamp: float) -> None:
        """
        Add a keyboard action to the recording.
        
        Args:
            event: X11 event
            timestamp: Event timestamp
        """
        # Convert keycode to character
        keycode = event.detail
        keysym = self.display.keycode_to_keysym(keycode, 0)
        
        # Skip modifiers
        if keysym in (0xffe1, 0xffe2, 0xffe3, 0xffe4, 0xffe5, 0xffe6, 0xffe7, 0xffe8, 0xffe9, 0xffea):
            return
        
        # Try to get character
        try:
            char = self.display.lookup_string(keysym)
            if not char:
                if self.debug_mode:
                    print(f"Unmappable key: {keysym}")
                return
        except:
            return
        
        # If this is the first keystroke or it's been a while since the last one,
        # start a new type_text action
        if not self.actions or self.actions[-1]['type'] != 'type_text' or \
           timestamp - self.last_action_time > 1.0:
            action = {
                'type': 'type_text',
                'text': char,
                'timestamp': timestamp
            }
            self.actions.append(action)
        else:
            # Append to existing type_text action
            self.actions[-1]['text'] += char
        
        self.last_action_time = timestamp
        
        if self.debug_mode:
            print(f"Recorded keystroke: '{char}'")
    
    def _get_relative_coordinates(self, root_x: int, root_y: int) -> Tuple[int, int]:
        """
        Convert root window coordinates to coordinates relative to the target window.
        
        Args:
            root_x: X coordinate relative to root window
            root_y: Y coordinate relative to root window
            
        Returns:
            Tuple of (x, y) coordinates relative to target window
        """
        # Translate global coordinates to window-relative
        x_rel = root_x - self.window_geometry['x']
        y_rel = root_y - self.window_geometry['y']
        
        return x_rel, y_rel
    
    def _normalize_action_timing(self) -> None:
        """
        Convert absolute timestamps to relative delays between actions.
        """
        prev_time = self.start_time
        
        for action in self.actions:
            if 'timestamp' in action:
                # Calculate delay since last action
                delay = action['timestamp'] - prev_time
                action['delay'] = max(0.1, round(delay, 2))  # Minimum delay of 0.1s, rounded to 2 decimal places
                prev_time = action['timestamp']
                
                # Remove original timestamp
                del action['timestamp']
    
    def save_recording(self, filepath: str) -> bool:
        """
        Save recorded actions to a file.
        
        Args:
            filepath: Path to save the file
            
        Returns:
            Whether saving was successful
        """
        # Add any missing delay values
        for action in self.actions:
            if 'delay' not in action:
                action['delay'] = 0.1  # Default delay
        
        # Remove any alternative actions
        actions = [a for a in self.actions if not a.get('is_alternative', False)]
        
        # Create config structure
        config = {
            'actions': actions,
            'loop_actions': False,
            'continuous_mode': False,
            'click_interval': 0.1,
            'metadata': {
                'created': datetime.now().isoformat(),
                'window_id': self.target_window_id,
                'window_name': self.window_geometry['name'] if self.window_geometry else "Unknown",
            }
        }
        
        try:
            # Create directory if it doesn't exist
            dir_path = os.path.dirname(filepath)
            if dir_path and not os.path.exists(dir_path):
                os.makedirs(dir_path, exist_ok=True)
            
            with open(filepath, 'w') as f:
                json.dump(config, f, indent=2)
            
            if self.debug_mode:
                print(f"Saved {len(actions)} actions to {filepath}")
            
            return True
        except Exception as e:
            if self.debug_mode:
                print(f"Error saving recording: {e}")
            return False
    
    def cleanup(self) -> None:
        """Clean up resources."""
        # Stop recording if active
        if self.is_recording:
            self.stop_recording()
        
        # Close displays
        if self.display:
            self.display.close()
        if self.record_display:
            self.record_display.close()

class ActionAnalyzer:
    """
    Analyzes recorded actions to improve them.
    """
    
    def __init__(self, window_manager: WindowManager, 
                 image_processor: ImageProcessor, debug_mode: bool = False):
        """
        Initialize the action analyzer.
        
        Args:
            window_manager: WindowManager instance
            image_processor: ImageProcessor instance
            debug_mode: Whether to output debug information
        """
        self.window_manager = window_manager
        self.image_processor = image_processor
        self.debug_mode = debug_mode
    
    def optimize_action_sequence(self, actions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Optimize a sequence of actions for better reliability.
        
        Args:
            actions: List of actions to optimize
            
        Returns:
            Optimized list of actions
        """
        if not actions:
            return []
        
        optimized = []
        skip_next = False
        
        for i, action in enumerate(actions):
            # Skip if marked in previous iteration
            if skip_next:
                skip_next = False
                continue
            
            # Handle specific action types
            if action['type'] == 'click_position':
                # Check for a click followed by typing - this is likely a form field
                if i < len(actions) - 1 and actions[i+1]['type'] == 'type_text':
                    # Combine into a single action with an explicit click before typing
                    combined = action.copy()
                    combined['text'] = actions[i+1]['text']
                    combined['type'] = 'click_and_type'
                    
                    if 'delay' in actions[i+1]:
                        combined['delay'] = actions[i+1]['delay']
                    
                    optimized.append(combined)
                    skip_next = True
                else:
                    optimized.append(action)
            
            # Handle double-clicks
            elif action['type'] == 'click_position' and i < len(actions) - 1:
                next_action = actions[i+1]
                if (next_action['type'] == 'click_position' and 
                    abs(next_action['x'] - action['x']) < 5 and 
                    abs(next_action['y'] - action['y']) < 5 and
                    'delay' in next_action and next_action['delay'] < 0.3):
                    
                    # Looks like a double-click
                    double_click = action.copy()
                    double_click['is_double_click'] = True
                    
                    if 'delay' in next_action:
                        double_click['delay'] = next_action['delay']
                    
                    optimized.append(double_click)
                    skip_next = True
                else:
                    optimized.append(action)
            
            else:
                optimized.append(action)
            
            # Add a small wait after certain actions
            if action['type'] in ('click_text', 'click_template'):
                # Add a small wait to allow UI to update
                wait_action = {
                    'type': 'wait',
                    'duration': 0.5,
                    'delay': 0
                }
                optimized.append(wait_action)
        
        if self.debug_mode:
            print(f"Optimized {len(actions)} actions to {len(optimized)} actions")
        
        return optimized
