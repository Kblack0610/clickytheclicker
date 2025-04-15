#!/usr/bin/env python3
"""
XTest Window Autoclicker - A tool to click within a specific window without moving your cursor

This script uses the X11 XTest extension to send synthetic mouse events to a window
without taking over your physical mouse cursor, allowing you to continue working
while the autoclicker operates independently.
"""

import sys
import subprocess
from typing import Dict, Any

try:
    from Xlib import display, X
    from Xlib.ext import xtest
except ImportError:
    print("Required dependencies not found. Installing...")
    subprocess.call([sys.executable, "-m", "pip", "install", "python-xlib"])
    from Xlib import display, X
    from Xlib.ext import xtest

from modules.cli_parser import parse_args
from modules.window_selector import WindowSelector
from modules.click_position_manager import ClickPositionManager
from modules.event_sender import EventSender
from modules.autoclicker_controller import AutoclickerController

VERSION = "1.2.0"

def list_windows() -> None:
    """List all available windows and exit."""
    window_selector = WindowSelector(debug_mode=True)
    
    try:
        result = subprocess.run(["xdotool", "search", "--onlyvisible", "--name", ".*"], 
                              capture_output=True, text=True, check=True)
        
        if result.stdout.strip():
            window_ids = result.stdout.strip().split("\n")
            print(f"Found {len(window_ids)} windows:")
            
            for window_id_str in window_ids:
                try:
                    window_id = int(window_id_str)
                    window_name = window_selector.get_window_name(window_id)
                    geometry = window_selector.get_window_geometry(window_id)
                    
                    if geometry:
                        x, y, width, height = geometry
                        print(f"ID: 0x{window_id:08x} ({window_id}) - \"{window_name}\" ({width}x{height} at {x},{y})")
                    else:
                        print(f"ID: 0x{window_id:08x} ({window_id}) - \"{window_name}\" (geometry unavailable)")
                except (ValueError, TypeError):
                    continue
    except subprocess.SubprocessError as e:
        print(f"Error listing windows: {e}")
        sys.exit(1)

def main() -> int:
    """Main entry point for the XTest Autoclicker."""
    # Parse command line arguments
    args = parse_args()
    
    # Handle special commands
    if args.get('version'):
        print(f"XTest Window Autoclicker v{VERSION}")
        return 0
        
    if args.get('list_windows'):
        list_windows()
        return 0
    
    # Create controller
    controller = AutoclickerController(debug_mode=args.get('debug', False))
    
    # Set up from args
    if not controller.setup_from_args(args):
        print("Failed to set up autoclicker")
        return 1
    
    # Run test click if requested
    if args.get('test_click'):
        success = controller.run_test_click()
        return 0 if success else 1
    
    # Run autoclicker
    controller.run_autoclicker(dry_run=args.get('dry_run', False))
    return 0

if __name__ == "__main__":
    sys.exit(main())