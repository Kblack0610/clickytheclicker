#!/usr/bin/env python3
"""
Window Selector Module

This module provides functionality for selecting and managing X11 windows for the autoclicker.
It handles window selection by click, by name, and getting window geometry.
"""

import subprocess
import time
from typing import Tuple, Optional, Dict, Any

class WindowSelector:
    """
    Class for selecting and managing X11 windows.
    
    Provides methods to select windows by clicking on them or by name,
    and to retrieve window information like geometry and names.
    """
    
    def __init__(self, debug_mode: bool = False):
        """
        Initialize the WindowSelector.
        
        Args:
            debug_mode: Whether to enable debug output.
        """
        self.debug_mode = debug_mode
        self.selected_window = None
        self.window_geometry = None
    
    def select_window_by_click(self) -> bool:
        """
        Prompt user to click on a window to select it.
        
        Returns:
            bool: True if window was successfully selected, False otherwise.
        """
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
                        window_id = int(line.split("=")[1], 16)
                        break
                    except (ValueError, IndexError):
                        pass
            
            if window_id:
                self.selected_window = window_id
                window_name = self.get_window_name(window_id)
                print(f"Selected window: {window_name} (id: {window_id:x})")
                
                # Get window geometry
                self.window_geometry = self.get_window_geometry(window_id)
                if self.window_geometry:
                    x, y, width, height = self.window_geometry
                    print(f"Window geometry: x={x}, y={y}, width={width}, height={height}")
                    return True
        except subprocess.SubprocessError as e:
            print(f"Error running xdotool: {e}")
            
        print("Failed to select window. Please try again.")
        return False
        
    def select_window_by_name(self, window_name: str) -> bool:
        """
        Select a window by its name/title.
        
        Args:
            window_name: The name/title of the window to select.
            
        Returns:
            bool: True if window was successfully selected, False otherwise.
        """
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
    
    def get_window_name(self, window_id: int) -> str:
        """
        Get the window name from its ID.
        
        Args:
            window_id: The ID of the window.
            
        Returns:
            str: The name of the window or "Unknown" if could not be determined.
        """
        try:
            result = subprocess.run(["xdotool", "getwindowname", str(window_id)], 
                                  capture_output=True, text=True, check=True)
            return result.stdout.strip()
        except subprocess.SubprocessError:
            return "Unknown"
    
    def get_window_geometry(self, window_id: int) -> Optional[Tuple[int, int, int, int]]:
        """
        Get the geometry (position and size) of a window.
        
        Args:
            window_id: The ID of the window.
            
        Returns:
            Optional[Tuple[int, int, int, int]]: Tuple of (x, y, width, height) or None if failed.
        """
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
    
    def get_selected_window_info(self) -> Optional[Dict[str, Any]]:
        """
        Get information about the currently selected window.
        
        Returns:
            Optional[Dict[str, Any]]: Dictionary with window information or None if no window selected.
        """
        if not self.selected_window or not self.window_geometry:
            return None
            
        x, y, width, height = self.window_geometry
        return {
            'id': self.selected_window,
            'name': self.get_window_name(self.selected_window),
            'geometry': {
                'x': x,
                'y': y,
                'width': width,
                'height': height
            }
        }
