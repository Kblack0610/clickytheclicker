#!/usr/bin/env python3
"""
Autoclicker Controller Module

This module provides the main controller for the autoclicker application.
It coordinates the window selection, click position management, and event sending.
"""

import random
import time
from typing import List, Tuple, Optional, Dict, Any

from modules.window_selector import WindowSelector
from modules.click_position_manager import ClickPositionManager
from modules.event_sender import EventSender

class AutoclickerController:
    """
    Main controller for the XTest Autoclicker application.
    
    Coordinates between WindowSelector, ClickPositionManager, and EventSender
    to provide a complete autoclicking experience.
    """
    
    def __init__(self, debug_mode: bool = False):
        """
        Initialize the AutoclickerController.
        
        Args:
            debug_mode: Whether to enable debug output.
        """
        self.debug_mode = debug_mode
        self.window_selector = WindowSelector(debug_mode)
        self.click_position_manager = ClickPositionManager(debug_mode)
        self.event_sender = EventSender(debug_mode)
        
        self.is_running = False
        self.click_interval = 1.0  # Default: 1 second between clicks
        self.click_count = 0
        self.max_clicks = None  # Default: No limit
        self.i3_mode = False
        self.button = 1  # Default: left button
        
    def setup_from_args(self, args: Dict[str, Any]) -> bool:
        """
        Set up the autoclicker from command line arguments.
        
        Args:
            args: Dictionary of command line arguments.
            
        Returns:
            bool: True if setup was successful, False otherwise.
        """
        # Set basic parameters
        self.debug_mode = args.get('debug', False)
        self.click_interval = args.get('interval', 1.0)
        self.click_position_manager.set_jitter(args.get('jitter', 0))
        self.max_clicks = args.get('clicks')
        self.i3_mode = args.get('i3', False)
        self.button = args.get('button', 1)
        
        # Select window
        window_selected = False
        if args.get('window_id'):
            self.window_selector.selected_window = args['window_id']
            self.window_selector.window_geometry = self.window_selector.get_window_geometry(args['window_id'])
            if self.window_selector.window_geometry:
                window_selected = True
                print(f"Using window ID: {args['window_id']:x}")
        elif args.get('window_name'):
            window_selected = self.window_selector.select_window_by_name(args['window_name'])
        else:
            window_selected = self.window_selector.select_window_by_click()
        
        if not window_selected:
            print("Failed to select a window")
            return False
            
        # Set up click positions
        if args.get('position'):
            for pos in args['position']:
                if len(pos) == 2:
                    self.click_position_manager.add_click_position(pos[0], pos[1])
        
        if args.get('center'):
            if self.window_selector.window_geometry:
                _, _, width, height = self.window_selector.window_geometry
                self.click_position_manager.add_click_position(width // 2, height // 2)
        
        if args.get('grid'):
            if len(args['grid']) == 2 and self.window_selector.window_geometry:
                cols, rows = args['grid']
                _, _, width, height = self.window_selector.window_geometry
                
                for row in range(rows):
                    for col in range(cols):
                        x = (col + 0.5) * (width / cols)
                        y = (row + 0.5) * (height / rows)
                        self.click_position_manager.add_click_position(int(x), int(y))
        
        # If no positions specified, prompt user to add one
        if not self.click_position_manager.get_click_positions() and not args.get('random'):
            if not self.click_position_manager.capture_click_position(self.window_selector.window_geometry):
                print("No click positions defined")
                return False
        
        return True
        
    def run_autoclicker(self, dry_run: bool = False) -> None:
        """
        Run the autoclicker main loop.
        
        Args:
            dry_run: If True, don't actually send clicks, just simulate.
        """
        if not self.window_selector.selected_window or not self.window_selector.window_geometry:
            print("Cannot run: No window selected")
            return
            
        click_positions = self.click_position_manager.get_click_positions()
        if not click_positions and not self.click_position_manager.jitter and self.debug_mode:
            print("Warning: No click positions defined, will use center of window")
            _, _, width, height = self.window_selector.window_geometry
            click_positions = [(width // 2, height // 2)]
            
        self.is_running = True
        self.click_count = 0
        
        print("Starting autoclicker...")
        print("Press Ctrl+C to stop")
        
        try:
            while self.is_running:
                # Check if we've reached max clicks
                if self.max_clicks is not None and self.click_count >= self.max_clicks:
                    print(f"Reached maximum of {self.max_clicks} clicks")
                    self.is_running = False
                    break
                
                # Make sure window still exists and update geometry
                if not dry_run:
                    self.window_selector.window_geometry = self.window_selector.get_window_geometry(
                        self.window_selector.selected_window
                    )
                    if not self.window_selector.window_geometry:
                        print("Window no longer exists. Stopping.")
                        self.is_running = False
                        break
                
                # Determine click position
                if click_positions:
                    # Use next position in the list
                    pos_idx = self.click_count % len(click_positions)
                    rel_x, rel_y = click_positions[pos_idx]
                else:
                    # Use random position within window
                    _, _, width, height = self.window_selector.window_geometry
                    rel_x = random.randint(10, width - 10)
                    rel_y = random.randint(10, height - 10)
                
                # Apply jitter if enabled
                rel_x, rel_y = self.click_position_manager.get_jittered_position(rel_x, rel_y)
                
                # Send click event
                if not dry_run:
                    success = self.event_sender.click_at_window_position(
                        self.window_selector.window_geometry, 
                        rel_x, 
                        rel_y,
                        self.button
                    )
                    if success:
                        self.click_count += 1
                        print(f"Click {self.click_count} at position ({rel_x}, {rel_y})")
                    else:
                        print("Failed to send click event")
                else:
                    # Dry run mode - just print what would happen
                    self.click_count += 1
                    print(f"[DRY RUN] Click {self.click_count} at position ({rel_x}, {rel_y})")
                
                # Wait for next click
                time.sleep(self.click_interval)
                
        except KeyboardInterrupt:
            print("\nStopping autoclicker")
            self.is_running = False
        finally:
            self.cleanup()
    
    def run_test_click(self) -> bool:
        """
        Send a single test click and exit.
        
        Returns:
            bool: True if test click was successful, False otherwise.
        """
        if not self.window_selector.selected_window or not self.window_selector.window_geometry:
            print("Cannot run test: No window selected")
            return False
            
        _, _, width, height = self.window_selector.window_geometry
        test_x = width // 2
        test_y = height // 2
        
        print(f"Sending test click at center of window ({test_x}, {test_y})")
        success = self.event_sender.click_at_window_position(
            self.window_selector.window_geometry, 
            test_x, 
            test_y,
            self.button
        )
        
        if success:
            print("Test click sent successfully")
        else:
            print("Failed to send test click")
            
        return success
    
    def cleanup(self) -> None:
        """Clean up resources used by the controller."""
        if self.event_sender:
            self.event_sender.cleanup()
