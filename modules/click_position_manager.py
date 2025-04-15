#!/usr/bin/env python3
"""
Click Position Manager Module

This module provides functionality for managing click positions for the autoclicker.
It handles adding, capturing, and managing click positions relative to windows.
"""

import subprocess
import time
import random
from typing import List, Tuple, Optional

class ClickPositionManager:
    """
    Class for managing click positions within a window.
    
    Provides methods to add, capture, and manage click positions
    relative to a window's coordinates.
    """
    
    def __init__(self, debug_mode: bool = False):
        """
        Initialize the ClickPositionManager.
        
        Args:
            debug_mode: Whether to enable debug output.
        """
        self.debug_mode = debug_mode
        self.click_positions = []  # List of positions to click (x, y)
        self.jitter = 0  # Default: No jitter
    
    def add_click_position(self, relative_x: int, relative_y: int) -> None:
        """
        Add a position (relative to window) to click.
        
        Args:
            relative_x: X coordinate relative to window's top-left corner.
            relative_y: Y coordinate relative to window's top-left corner.
        """
        self.click_positions.append((relative_x, relative_y))
        print(f"Added click position: ({relative_x}, {relative_y})")
    
    def capture_click_position(self, window_geometry: Optional[Tuple[int, int, int, int]]) -> bool:
        """
        Capture the current mouse position to add as a click position.
        
        Args:
            window_geometry: Tuple of (x, y, width, height) for the window.
            
        Returns:
            bool: True if position was successfully captured, False otherwise.
        """
        if not window_geometry:
            print("No window selected. Please select a window first.")
            return False
        
        print("Move your mouse to the position you want to click and press Enter...")
        input()
        
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
                window_x, window_y, _, _ = window_geometry
                relative_x = mouse_x - window_x
                relative_y = mouse_y - window_y
                self.add_click_position(relative_x, relative_y)
                return True
            else:
                print("Could not get mouse position.")
        except subprocess.SubprocessError as e:
            print(f"Error getting mouse position: {e}")
            
        return False
    
    def set_jitter(self, jitter_pixels: int) -> None:
        """
        Set the jitter amount for click positions.
        
        Args:
            jitter_pixels: Number of pixels to randomly jitter in each direction.
        """
        self.jitter = jitter_pixels
        if self.jitter > 0:
            print(f"Jitter set to ±{self.jitter} pixels")
        else:
            print("Jitter disabled")
    
    def get_click_positions(self) -> List[Tuple[int, int]]:
        """
        Get the list of click positions.
        
        Returns:
            List[Tuple[int, int]]: List of (x, y) click positions.
        """
        return self.click_positions.copy()
    
    def clear_click_positions(self) -> None:
        """Clear all click positions."""
        self.click_positions = []
        print("All click positions cleared")
    
    def get_jittered_position(self, base_x: int, base_y: int) -> Tuple[int, int]:
        """
        Apply jitter to a base position if jitter is enabled.
        
        Args:
            base_x: Base X coordinate.
            base_y: Base Y coordinate.
            
        Returns:
            Tuple[int, int]: Position with jitter applied (if enabled).
        """
        if self.jitter <= 0:
            return (base_x, base_y)
            
        jitter_x = random.randint(-self.jitter, self.jitter)
        jitter_y = random.randint(-self.jitter, self.jitter)
        
        return (base_x + jitter_x, base_y + jitter_y)
