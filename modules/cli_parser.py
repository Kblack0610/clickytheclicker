#!/usr/bin/env python3
"""
Command Line Interface Parser Module

This module provides functionality for parsing command line arguments for the autoclicker.
It defines and processes all available command line options.
"""

import argparse
from typing import Any, Dict

def parse_args() -> Dict[str, Any]:
    """
    Parse command line arguments for the XTest Autoclicker.
    
    Returns:
        Dict[str, Any]: Dictionary containing parsed arguments.
    """
    parser = argparse.ArgumentParser(
        description="XTest Window Autoclicker - Click within a specific window without moving your cursor"
    )
    
    # Window selection options
    window_group = parser.add_argument_group("Window Selection")
    window_group.add_argument("--window-name", help="Select window by name instead of clicking")
    window_group.add_argument("--window-id", type=lambda x: int(x, 0), help="Use specific window ID (hex or decimal)")
    window_group.add_argument("--list-windows", action="store_true", help="List all available windows and exit")
    window_group.add_argument("--i3", action="store_true", help="Use i3 window manager mode for geometry handling")
    
    # Click behavior options
    click_group = parser.add_argument_group("Click Behavior")
    click_group.add_argument("--interval", type=float, default=1.0, help="Seconds between clicks (default: 1.0)")
    click_group.add_argument("--jitter", type=int, default=0, help="Random jitter in pixels (default: 0)")
    click_group.add_argument("--clicks", type=int, help="Stop after N clicks (default: unlimited)")
    click_group.add_argument("--button", type=int, default=1, 
                           help="Mouse button to click (1=left, 2=middle, 3=right, default: 1)")
    
    # Click positions
    position_group = parser.add_argument_group("Click Positions")
    position_group.add_argument("--position", type=lambda s: [int(x) for x in s.split(',')], action="append",
                              help="Add click position as x,y (relative to window, can be used multiple times)")
    position_group.add_argument("--random", action="store_true", 
                              help="Click at random positions within the window")
    position_group.add_argument("--grid", type=lambda s: [int(x) for x in s.split(',')], 
                              help="Create a grid of positions with columns,rows")
    position_group.add_argument("--center", action="store_true", help="Click at the center of the window")
    
    # Other options
    parser.add_argument("--debug", action="store_true", help="Enable debug output")
    parser.add_argument("--dry-run", action="store_true", help="Don't actually click, just show what would happen")
    parser.add_argument("--no-activate", action="store_true", help="Don't activate window before clicking")
    parser.add_argument("--version", action="store_true", help="Show version and exit")
    
    # Special actions
    parser.add_argument("--test-click", action="store_true", help="Send a single test click and exit")
    
    args = parser.parse_args()
    return vars(args)
