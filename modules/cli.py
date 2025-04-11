#!/usr/bin/env python3
"""
Command Line Interface Module

Handles command-line arguments and user interaction for the autoclicker.
"""

import os
import sys
import argparse
import json
from typing import List, Dict, Any, Optional

from .input_manager import InputManager
from .window_manager import WindowManager
from .image_processor import ImageProcessor
from .action_controller import ActionController
from .config_manager import ConfigManager

class CLI:
    """
    Command-line interface for the autoclicker.
    """
    
    def __init__(self):
        """Initialize the CLI."""
        self.parser = self._create_parser()
        self.config_manager = ConfigManager()
    
    def _create_parser(self) -> argparse.ArgumentParser:
        """
        Create the argument parser.
        
        Returns:
            Configured argument parser
        """
        parser = argparse.ArgumentParser(
            description="Clicky the Clicker - An X11 autoclicker that clicks within specific application windows",
            formatter_class=argparse.ArgumentDefaultsHelpFormatter
        )
        
        # General options
        parser.add_argument('--debug', action='store_true', help="Enable debug output")
        parser.add_argument('--version', action='store_true', help="Show version information")
        
        # Window selection
        window_group = parser.add_argument_group('Window Selection')
        window_group.add_argument('--window-id', type=int, help="X11 window ID to click within")
        window_group.add_argument('--window-name', type=str, help="Name of window to click within (partial match)")
        window_group.add_argument('--list-windows', action='store_true', help="List all window IDs and names")
        window_group.add_argument('--i3', action='store_true', help="Use i3 window manager compatible mode")
        
        # Action configuration
        action_group = parser.add_argument_group('Action Configuration')
        action_group.add_argument('--config', type=str, help="Path to configuration file")
        action_group.add_argument('--list-configs', action='store_true', help="List available configurations")
        action_group.add_argument('--save-config', type=str, help="Save current sequence to a configuration file")
        
        # Execution control
        exec_group = parser.add_argument_group('Execution Control')
        exec_group.add_argument('--interval', type=float, default=0.1, help="Interval between actions in seconds")
        exec_group.add_argument('--loop', action='store_true', help="Loop the action sequence indefinitely")
        exec_group.add_argument('--continuous', action='store_true', help="Continuous mode: retry on failure")
        exec_group.add_argument('--max-cycles', type=int, default=0, help="Maximum number of cycles (0 = unlimited)")
        exec_group.add_argument('--virtual-pointer', action='store_true', help="Use virtual pointer (requires root)")
        
        # Testing and debugging
        test_group = parser.add_argument_group('Testing and Debugging')
        test_group.add_argument('--test-click', action='store_true', help="Test click in the center of the window")
        test_group.add_argument('--test-ocr', action='store_true', help="Test OCR capabilities")
        test_group.add_argument('--test-template', type=str, help="Test template matching with the given image")
        
        return parser
    
    def parse_args(self, args: Optional[List[str]] = None) -> argparse.Namespace:
        """
        Parse command-line arguments.
        
        Args:
            args: Command-line arguments (uses sys.argv if None)
            
        Returns:
            Parsed arguments
        """
        return self.parser.parse_args(args)
    
    def run(self, args: Optional[argparse.Namespace] = None) -> int:
        """
        Run the CLI with the given arguments.
        
        Args:
            args: Parsed arguments (parses from command line if None)
            
        Returns:
            Exit code
        """
        if args is None:
            args = self.parse_args()
        
        try:
            # Show version and exit
            if args.version:
                print("Clicky the Clicker v1.0.0")
                print("An X11 autoclicker that clicks within specific application windows")
                return 0
            
            # Initialize components with debug mode if specified
            window_manager = WindowManager(is_i3=args.i3, debug_mode=args.debug)
            input_manager = InputManager(use_virtual_pointer=args.virtual_pointer, debug_mode=args.debug)
            image_processor = ImageProcessor(debug_mode=args.debug)
            
            # List windows and exit
            if args.list_windows:
                windows = window_manager.list_windows()
                if not windows:
                    print("No windows found")
                    return 1
                
                print("Available windows:")
                for window in windows:
                    print(f"  ID: {window['id']}, Name: {window['name']}")
                return 0
            
            # List configurations and exit
            if args.list_configs:
                configs = self.config_manager.list_configs()
                if not configs:
                    print("No configurations found")
                    return 1
                
                print("Available configurations:")
                for config in configs:
                    print(f"  {config}")
                return 0
            
            # Create action controller
            action_controller = ActionController(
                input_manager=input_manager,
                window_manager=window_manager,
                image_processor=image_processor,
                debug_mode=args.debug
            )
            
            # Set execution parameters
            action_controller.loop_actions = args.loop
            action_controller.continuous_mode = args.continuous
            action_controller.click_interval = args.interval
            
            # Get window ID
            window_id = None
            if args.window_id:
                window_id = args.window_id
            elif args.window_name:
                windows = window_manager.list_windows()
                for window in windows:
                    if args.window_name.lower() in window['name'].lower():
                        window_id = window['id']
                        print(f"Using window: {window['name']} (ID: {window_id})")
                        break
                
                if window_id is None:
                    print(f"No window found matching name: {args.window_name}")
                    return 1
            
            # Test click in center of window
            if args.test_click and window_id:
                window = window_manager.get_window_by_id(window_id)
                if not window:
                    print(f"Window ID {window_id} not found")
                    return 1
                
                center_x = window['width'] // 2
                center_y = window['height'] // 2
                
                print(f"Testing click at center of window: ({center_x}, {center_y})")
                success = input_manager.click(center_x, center_y, window_id=window_id)
                
                if success:
                    print("Click successful")
                    return 0
                else:
                    print("Click failed")
                    return 1
            
            # Test OCR
            if args.test_ocr and window_id:
                print("Testing OCR capabilities...")
                screenshot = image_processor.capture_window_screenshot(window_id)
                if screenshot is None:
                    print("Failed to capture screenshot")
                    return 1
                
                print("Screenshot captured. Please enter text to find:")
                text = input("> ")
                
                result = image_processor.find_text_in_screenshot(text, screenshot)
                if result:
                    x, y, confidence = result
                    print(f"Found text at ({x}, {y}) with confidence {confidence:.2f}")
                    
                    if input("Click on this position? (y/n) ").lower() == 'y':
                        input_manager.click(x, y, window_id=window_id)
                else:
                    print(f"Text '{text}' not found")
                
                return 0
            
            # Test template matching
            if args.test_template and window_id:
                if not os.path.exists(args.test_template):
                    print(f"Template file not found: {args.test_template}")
                    return 1
                
                print(f"Testing template matching with {args.test_template}...")
                screenshot = image_processor.capture_window_screenshot(window_id)
                if screenshot is None:
                    print("Failed to capture screenshot")
                    return 1
                
                result = image_processor.find_template_in_screenshot(args.test_template, screenshot)
                if result:
                    x, y, confidence = result
                    print(f"Found template at ({x}, {y}) with confidence {confidence:.2f}")
                    
                    if input("Click on this position? (y/n) ").lower() == 'y':
                        input_manager.click(x, y, window_id=window_id)
                else:
                    print("Template not found")
                
                return 0
            
            # Load configuration
            if args.config:
                if not os.path.exists(args.config):
                    print(f"Configuration file not found: {args.config}")
                    return 1
                
                success = action_controller.load_actions(args.config)
                if not success:
                    print(f"Failed to load configuration: {args.config}")
                    return 1
                
                print(f"Loaded configuration from {args.config}")
            
            # Save configuration
            if args.save_config:
                if not action_controller.actions:
                    print("No actions to save")
                    return 1
                
                success = action_controller.save_actions(args.save_config)
                if not success:
                    print(f"Failed to save configuration: {args.save_config}")
                    return 1
                
                print(f"Saved configuration to {args.save_config}")
                return 0
            
            # Run automation if we have actions and a window
            if action_controller.actions and window_id:
                print(f"Running automation with {len(action_controller.actions)} actions")
                stats = action_controller.run_automation(window_id, args.max_cycles)
                return 0
            elif not action_controller.actions:
                print("No actions to perform. Load a configuration with --config or create actions interactively.")
                return 1
            elif not window_id:
                print("No window specified. Use --window-id or --window-name to specify a window.")
                return 1
            
            return 0
            
        except KeyboardInterrupt:
            print("\nOperation canceled by user")
            return 130
        except Exception as e:
            print(f"Error: {e}")
            if args.debug:
                import traceback
                traceback.print_exc()
            return 1
        finally:
            # Clean up resources
            pass
    
def main() -> int:
    """
    Main entry point for the CLI.
    
    Returns:
        Exit code
    """
    cli = CLI()
    return cli.run()

if __name__ == "__main__":
    sys.exit(main())
