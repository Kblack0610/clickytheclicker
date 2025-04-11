#!/usr/bin/env python3
"""
Input Manager Module

Handles all input operations (mouse clicks, keyboard typing) for the autoclicker.
Supports both standard XTest-based input and virtual pointer input via xinput.
"""

import os
import time
import subprocess
from typing import Tuple, Optional, Dict, Any
import Xlib
from Xlib import X, XK, display
from Xlib.ext import xtest

class InputManager:
    """
    Manages input operations like mouse clicks and keyboard typing.
    Can work with either the standard cursor or a virtual cursor.
    """
    
    def __init__(self, use_virtual_pointer: bool = False, debug_mode: bool = False):
        """
        Initialize the input manager.
        
        Args:
            use_virtual_pointer: Whether to use a virtual pointer instead of moving the main cursor
            debug_mode: Whether to output debug information
        """
        self.debug_mode = debug_mode
        self.use_virtual_pointer = use_virtual_pointer
        self.display = display.Display()
        self.root = self.display.screen().root
        
        # Virtual pointer details if enabled
        self.virtual_pointer_id = None
        
        if use_virtual_pointer:
            if os.geteuid() != 0:
                print("Warning: Creating a virtual pointer requires root privileges.")
                print("Some functionality may be limited.")
            else:
                self._setup_virtual_pointer()
    
    def _setup_virtual_pointer(self) -> bool:
        """
        Set up a virtual pointer using xinput if possible.
        
        Returns:
            bool: Whether the virtual pointer was successfully created
        """
        try:
            # Check if xinput is available
            subprocess.run(["which", "xinput"], check=True, capture_output=True)
            
            # Create a virtual master pointer
            result = subprocess.run(
                ["xinput", "create-master", "ClickyPointer"],
                capture_output=True, 
                text=True,
                check=True
            )
            
            if self.debug_mode:
                print("Virtual pointer created successfully")
            
            # Find the ID of the new pointer
            list_result = subprocess.run(
                ["xinput", "list"], 
                capture_output=True, 
                text=True,
                check=True
            )
            
            # Parse the output to find the virtual pointer ID
            import re
            match = re.search(r"ClickyPointer pointer\s+id=(\d+)", list_result.stdout)
            if match:
                self.virtual_pointer_id = match.group(1)
                if self.debug_mode:
                    print(f"Virtual pointer ID: {self.virtual_pointer_id}")
                return True
            else:
                if self.debug_mode:
                    print("Could not find virtual pointer ID")
                return False
                
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            if self.debug_mode:
                print(f"Error setting up virtual pointer: {e}")
            return False
    
    def click(self, x: int, y: int, button: int = 1, window_id: Optional[int] = None) -> bool:
        """
        Perform a mouse click at the specified coordinates.
        
        Args:
            x: X coordinate relative to window
            y: Y coordinate relative to window
            button: Mouse button (1=left, 2=middle, 3=right)
            window_id: Optional window ID to click within
            
        Returns:
            bool: Whether the click was successful
        """
        try:
            if self.use_virtual_pointer and self.virtual_pointer_id:
                return self._click_virtual(x, y, button, window_id)
            else:
                return self._click_xtest(x, y, button, window_id)
        except Exception as e:
            if self.debug_mode:
                print(f"Click error: {e}")
            return False
    
    def _click_xtest(self, x: int, y: int, button: int = 1, window_id: Optional[int] = None) -> bool:
        """
        Perform a mouse click using XTest.
        
        Args:
            x: X coordinate relative to window
            y: Y coordinate relative to window
            button: Mouse button (1=left, 2=middle, 3=right)
            window_id: Optional window ID to click within
            
        Returns:
            bool: Whether the click was successful
        """
        try:
            # Get absolute coordinates if window_id is provided
            if window_id:
                window = self.display.create_resource_object('window', window_id)
                geom = window.get_geometry()
                x_abs, y_abs = x, y
                
                # Translate to absolute coordinates
                while True:
                    parent = window.query_tree().parent
                    pgeom = parent.get_geometry()
                    x_abs += geom.x
                    y_abs += geom.y
                    if parent == self.root:
                        break
                    window = parent
                    geom = pgeom
            else:
                # Use coordinates as given
                x_abs, y_abs = x, y
            
            if self.debug_mode:
                print(f"Targeting absolute position: ({x_abs}, {y_abs})")
            
            # IMPORTANT: Save the current mouse position
            pointer_data = self.root.query_pointer()
            old_x, old_y = pointer_data.root_x, pointer_data.root_y
            
            # FIXED IMPLEMENTATION: 
            # The previous implementation was incorrect as XTest fake_input doesn't support 
            # passing x,y coordinates directly to click events
            
            # 1. Move the synthetic pointer using XTest (this doesn't move the real cursor)
            xtest.fake_input(self.display, X.MotionNotify, 0, x=x_abs, y=y_abs)
            self.display.sync()
            
            # 2. Send button events at the current synthetic position
            xtest.fake_input(self.display, X.ButtonPress, button)
            self.display.sync()
            time.sleep(0.1)  # Small delay between press and release
            xtest.fake_input(self.display, X.ButtonRelease, button)
            self.display.sync()
            
            # 3. Move the synthetic pointer back to original position
            # This ensures we don't leave the synthetic cursor somewhere unexpected
            xtest.fake_input(self.display, X.MotionNotify, 0, x=old_x, y=old_y)
            self.display.sync()
            
            if self.debug_mode:
                print(f"Click executed at ({x_abs}, {y_abs}), then restored to ({old_x}, {old_y})")
            
            return True
            
        except Exception as e:
            if self.debug_mode:
                print(f"XTest click error: {e}")
            return False
    
    def _click_virtual(self, x: int, y: int, button: int = 1, window_id: Optional[int] = None) -> bool:
        """
        Perform a mouse click using the virtual pointer.
        
        Args:
            x: X coordinate relative to window
            y: Y coordinate relative to window
            button: Mouse button (1=left, 2=middle, 3=right)
            window_id: Optional window ID to click within
            
        Returns:
            bool: Whether the click was successful
        """
        # This is placeholder implementation - a full implementation would use
        # the XInput extension to directly create and send events to the virtual device
        if self.debug_mode:
            print(f"Virtual click at ({x}, {y}) with button {button} in window {window_id}")
        
        # For now, we'll just simulate it with xinput command
        try:
            # Get absolute coordinates if window_id is provided (similar to _click_xtest)
            if window_id:
                window = self.display.create_resource_object('window', window_id)
                geom = window.get_geometry()
                x_abs, y_abs = x, y
                
                # Translate to absolute coordinates
                while True:
                    parent = window.query_tree().parent
                    pgeom = parent.get_geometry()
                    x_abs += geom.x
                    y_abs += geom.y
                    if parent == self.root:
                        break
                    window = parent
                    geom = pgeom
            else:
                # Use coordinates as given
                x_abs, y_abs = x, y
                
            # Here we'd use XInput to move the virtual pointer and generate click events
            # This is just a placeholder that prints what would happen
            if self.debug_mode:
                print(f"Would move virtual pointer {self.virtual_pointer_id} to ({x_abs}, {y_abs})")
                print(f"Would click button {button}")
                
            return True
            
        except Exception as e:
            if self.debug_mode:
                print(f"Virtual click error: {e}")
            return False
    
    def type_text(self, text: str, window_id: Optional[int] = None) -> bool:
        """
        Type text using XTest keyboard events.
        
        Args:
            text: Text to type
            window_id: Optional window ID to focus before typing
            
        Returns:
            bool: Whether the typing was successful
        """
        try:
            # Focus window if provided
            if window_id:
                window = self.display.create_resource_object('window', window_id)
                window.set_input_focus(X.RevertToParent, X.CurrentTime)
                self.display.sync()
            
            # Type each character
            for char in text:
                self._type_character(char)
                time.sleep(0.01)  # Small delay between characters
                
            return True
            
        except Exception as e:
            if self.debug_mode:
                print(f"Type text error: {e}")
            return False
    
    def _type_character(self, char: str) -> None:
        """
        Type a single character using XTest.
        
        Args:
            char: Character to type
        """
        # Get the keycode for the character
        keysym = XK.string_to_keysym(char)
        keycode = self.display.keysym_to_keycode(keysym)
        
        if keycode:
            # Press and release the key
            xtest.fake_input(self.display, X.KeyPress, keycode)
            self.display.sync()
            time.sleep(0.01)
            xtest.fake_input(self.display, X.KeyRelease, keycode)
            self.display.sync()
        else:
            if self.debug_mode:
                print(f"Could not find keycode for character: {char}")
    
    def cleanup(self) -> None:
        """Clean up resources, including removing any virtual pointer."""
        if self.use_virtual_pointer and self.virtual_pointer_id:
            try:
                subprocess.run(
                    ["xinput", "remove-master", self.virtual_pointer_id],
                    check=True
                )
                if self.debug_mode:
                    print("Virtual pointer removed successfully")
            except subprocess.CalledProcessError as e:
                if self.debug_mode:
                    print(f"Error removing virtual pointer: {e}")
        
        # Close the display connection
        self.display.close()
