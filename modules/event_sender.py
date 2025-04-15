#!/usr/bin/env python3
"""
Event Sender Module

This module provides functionality for sending synthetic mouse events to X11
using the XTest extension. It handles click events without moving the user's cursor.
"""

import time
from typing import Optional

try:
    from Xlib import display, X
    from Xlib.ext import xtest
except ImportError:
    raise ImportError("Required dependencies not found. Please install python-xlib package.")

class EventSender:
    """
    Class for sending synthetic mouse events to X11 windows.
    
    Uses the XTest extension to send click events without taking over
    the user's physical cursor.
    """
    
    def __init__(self, debug_mode: bool = False):
        """
        Initialize the EventSender.
        
        Args:
            debug_mode: Whether to enable debug output.
        """
        self.debug_mode = debug_mode
        self.display = display.Display()
        self.root = self.display.screen().root
        
    def send_click_event(self, x: int, y: int, button: int = 1) -> bool:
        """
        Send a synthetic click event using XTest at absolute coordinates.
        
        Args:
            x: Absolute X coordinate to click.
            y: Absolute Y coordinate to click.
            button: Mouse button to click (1=left, 2=middle, 3=right).
            
        Returns:
            bool: True if click was successfully sent, False otherwise.
        """
        try:
            # IMPORTANT: Do NOT use MotionNotify as it moves the actual cursor
            # Instead, pass coordinates directly to button events
            
            # Simulate mouse down and up (click)
            xtest.fake_input(self.display, X.ButtonPress, button, x=x, y=y)
            self.display.sync()
            time.sleep(0.1)  # Small delay between press and release
            xtest.fake_input(self.display, X.ButtonRelease, button, x=x, y=y)
            self.display.sync()
            
            if self.debug_mode:
                print(f"Click event sent at ({x}, {y}) with button {button}")
                
            return True
        except Exception as e:
            print(f"Error sending XTest click event: {e}")
            return False
    
    def click_at_window_position(
        self, 
        window_geometry: Optional[tuple], 
        rel_x: int, 
        rel_y: int, 
        button: int = 1
    ) -> bool:
        """
        Click at a position relative to window using XTest.
        
        Args:
            window_geometry: Tuple of (x, y, width, height) for the window.
            rel_x: X coordinate relative to window's top-left corner.
            rel_y: Y coordinate relative to window's top-left corner.
            button: Mouse button to click (1=left, 2=middle, 3=right).
            
        Returns:
            bool: True if click was successfully sent, False otherwise.
        """
        if not window_geometry:
            print("Cannot click: Window geometry is not available")
            return False
        
        window_x, window_y, _, _ = window_geometry
        target_x = window_x + rel_x
        target_y = window_y + rel_y
        
        if self.debug_mode:
            print(f"Clicking at window position: ({rel_x}, {rel_y}) => absolute ({target_x}, {target_y})")
        
        return self.send_click_event(target_x, target_y, button)
    
    def cleanup(self) -> None:
        """Clean up resources used by the EventSender."""
        if self.display:
            self.display.close()
            
    def __del__(self):
        """Destructor to ensure cleanup of resources."""
        self.cleanup()
