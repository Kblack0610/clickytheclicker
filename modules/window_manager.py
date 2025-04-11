#!/usr/bin/env python3
"""
Window Manager Module

Handles window detection, focusing, and geometry calculations for the autoclicker.
Supports different window managers, including i3 and other tiling window managers.
"""

import os
import subprocess
import re
from typing import Dict, List, Tuple, Optional, Any
import Xlib
from Xlib import X, display

class WindowManager:
    """
    Manages window detection, coordinates, and focus.
    Supports different window managers and desktop environments.
    """
    
    def __init__(self, is_i3: bool = False, debug_mode: bool = False):
        """
        Initialize the window manager.
        
        Args:
            is_i3: Whether running on i3 window manager
            debug_mode: Whether to output debug information
        """
        self.debug_mode = debug_mode
        self.is_i3 = is_i3
        self.display = display.Display()
        self.root = self.display.screen().root
        
    def list_windows(self) -> List[Dict[str, Any]]:
        """
        List all visible windows with their properties.
        
        Returns:
            List of dictionaries containing window information
        """
        windows = []
        
        try:
            # Try xdotool first, which works in most environments
            if self._command_exists("xdotool"):
                if self.debug_mode:
                    print("Using xdotool to list windows")
                    
                output = subprocess.check_output(
                    ["xdotool", "search", "--onlyvisible", "--name", ""],
                    text=True
                )
                window_ids = output.strip().split('\n')
                
                for window_id in window_ids:
                    if not window_id:
                        continue
                        
                    try:
                        # Get window properties
                        name_output = subprocess.check_output(
                            ["xdotool", "getwindowname", window_id],
                            text=True
                        ).strip()
                        
                        # Get window geometry
                        geom_output = subprocess.check_output(
                            ["xdotool", "getwindowgeometry", window_id],
                            text=True
                        )
                        
                        # Parse geometry
                        position_match = re.search(r"Position: (\d+),(\d+)", geom_output)
                        size_match = re.search(r"Geometry: (\d+)x(\d+)", geom_output)
                        
                        if position_match and size_match:
                            x, y = map(int, position_match.groups())
                            width, height = map(int, size_match.groups())
                            
                            windows.append({
                                "id": window_id,
                                "name": name_output,
                                "x": x,
                                "y": y,
                                "width": width,
                                "height": height
                            })
                    except Exception as e:
                        if self.debug_mode:
                            print(f"Error getting window properties for {window_id}: {e}")
            else:
                # Fallback to Xlib
                if self.debug_mode:
                    print("Falling back to Xlib to list windows")
                windows = self._list_windows_xlib()
                
        except Exception as e:
            if self.debug_mode:
                print(f"Error listing windows: {e}")
        
        return windows
    
    def _list_windows_xlib(self) -> List[Dict[str, Any]]:
        """
        List windows using Xlib directly (fallback method).
        
        Returns:
            List of dictionaries containing window information
        """
        windows = []
        
        try:
            # Get all top-level windows
            window_ids = self.root.query_tree().children
            
            for window in window_ids:
                try:
                    # Check if window is mapped (visible)
                    attributes = window.get_attributes()
                    if attributes.map_state != X.IsViewable:
                        continue
                        
                    # Get window name
                    name = window.get_wm_name() or "Unnamed window"
                    
                    # Get geometry
                    geom = window.get_geometry()
                    
                    # Translate to absolute coordinates
                    abs_x, abs_y = self._get_absolute_coordinates(window, geom.x, geom.y)
                    
                    windows.append({
                        "id": window.id,
                        "name": name,
                        "x": abs_x,
                        "y": abs_y,
                        "width": geom.width,
                        "height": geom.height
                    })
                except Exception as e:
                    if self.debug_mode:
                        print(f"Error processing window {window.id}: {e}")
            
        except Exception as e:
            if self.debug_mode:
                print(f"Error in _list_windows_xlib: {e}")
                
        return windows
    
    def get_window_by_id(self, window_id: int) -> Optional[Dict[str, Any]]:
        """
        Get information about a specific window by ID.
        
        Args:
            window_id: X11 window ID
            
        Returns:
            Dictionary with window properties or None if not found
        """
        try:
            window = self.display.create_resource_object('window', window_id)
            
            # Get window attributes
            attributes = window.get_attributes()
            if attributes.map_state != X.IsViewable:
                if self.debug_mode:
                    print(f"Window {window_id} is not viewable")
                return None
            
            # Get window name
            name = window.get_wm_name() or "Unnamed window"
            
            # Get geometry
            geom = window.get_geometry()
            
            # Translate to absolute coordinates
            abs_x, abs_y = self._get_absolute_coordinates(window, geom.x, geom.y)
            
            return {
                "id": window_id,
                "name": name,
                "x": abs_x,
                "y": abs_y,
                "width": geom.width,
                "height": geom.height
            }
            
        except Exception as e:
            if self.debug_mode:
                print(f"Error getting window {window_id}: {e}")
            return None
    
    def _get_absolute_coordinates(self, window: Any, x: int, y: int) -> Tuple[int, int]:
        """
        Convert window-relative coordinates to absolute screen coordinates.
        
        Args:
            window: Xlib window object
            x: Window-relative X coordinate
            y: Window-relative Y coordinate
            
        Returns:
            Tuple of (absolute_x, absolute_y)
        """
        # Start with the window's coordinates
        abs_x, abs_y = x, y
        
        try:
            if self.is_i3:
                # For i3, we need to handle differently due to how it manages windows
                # Just get the geometry directly and don't try to traverse the tree
                geom = window.get_geometry()
                abs_x, abs_y = geom.x, geom.y
                
                # For i3, we might need to use xwininfo as a more reliable source
                try:
                    output = subprocess.check_output(
                        ["xwininfo", "-id", str(window.id)],
                        text=True
                    )
                    
                    # Parse xwininfo output
                    abs_x_match = re.search(r"Absolute upper-left X:\s+(\d+)", output)
                    abs_y_match = re.search(r"Absolute upper-left Y:\s+(\d+)", output)
                    
                    if abs_x_match and abs_y_match:
                        abs_x = int(abs_x_match.group(1))
                        abs_y = int(abs_y_match.group(1))
                except Exception as e:
                    if self.debug_mode:
                        print(f"Error getting i3 window coordinates with xwininfo: {e}")
            else:
                # For regular window managers, traverse the window tree to get absolute coordinates
                # Get window geometry
                geom = window.get_geometry()
                
                # Initialize absolute coordinates
                abs_x, abs_y = geom.x, geom.y
                
                # Traverse up the window tree until we reach the root
                parent = window.query_tree().parent
                while parent.id != self.root.id:
                    parent_geom = parent.get_geometry()
                    abs_x += parent_geom.x
                    abs_y += parent_geom.y
                    parent = parent.query_tree().parent
        except Exception as e:
            if self.debug_mode:
                print(f"Error calculating absolute coordinates: {e}")
        
        return abs_x, abs_y
    
    def focus_window(self, window_id: int) -> bool:
        """
        Focus a specific window.
        
        Args:
            window_id: X11 window ID
            
        Returns:
            Whether focusing was successful
        """
        try:
            window = self.display.create_resource_object('window', window_id)
            window.set_input_focus(X.RevertToParent, X.CurrentTime)
            self.display.sync()
            return True
        except Exception as e:
            if self.debug_mode:
                print(f"Error focusing window {window_id}: {e}")
            return False
    
    def get_window_screenshot(self, window_id: int) -> Optional[bytes]:
        """
        Take a screenshot of a specific window.
        
        Args:
            window_id: X11 window ID
            
        Returns:
            Raw image data or None if failed
        """
        try:
            # This is just a placeholder - in a real implementation, 
            # we would use a library like PIL or opencv to capture the window
            if self.debug_mode:
                print(f"Would take screenshot of window {window_id}")
            
            # Use xwd and convert to get a screenshot (requires imagemagick)
            # This is just an example - the full implementation would use PIL
            subprocess.run([
                "xwd", "-id", str(window_id), "-out", "/tmp/window_screenshot.xwd"
            ], check=True)
            
            subprocess.run([
                "convert", "/tmp/window_screenshot.xwd", "/tmp/window_screenshot.png"
            ], check=True)
            
            if os.path.exists("/tmp/window_screenshot.png"):
                return "/tmp/window_screenshot.png"
            
            return None
            
        except Exception as e:
            if self.debug_mode:
                print(f"Error taking window screenshot: {e}")
            return None
    
    def _command_exists(self, cmd: str) -> bool:
        """
        Check if a command exists on the system.
        
        Args:
            cmd: Command name to check
            
        Returns:
            True if command exists, False otherwise
        """
        return subprocess.call(
            ["which", cmd], 
            stdout=subprocess.DEVNULL, 
            stderr=subprocess.DEVNULL
        ) == 0
    
    def cleanup(self) -> None:
        """Clean up resources."""
        # Close the X display connection
        self.display.close()
