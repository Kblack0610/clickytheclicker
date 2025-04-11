#!/usr/bin/env python3
"""
Clicky the Clicker - Main Entry Point

An X11 autoclicker that clicks within specific application windows with OCR and
template matching capabilities.

This is the main entry point for the modular implementation of the autoclicker.
"""

import sys
import os

# Add the parent directory to path to allow importing modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from modules.input_manager import InputManager
from modules.window_manager import WindowManager
from modules.image_processor import ImageProcessor
from modules.action_controller import ActionController
from modules.cli import CLI

def main():
    """Main entry point for Clicky the Clicker."""
    try:
        print("Clicky the Clicker - An X11 autoclicker for window automation")
        print("============================================================")
        
        # Use the CLI module to handle command-line arguments and execution
        cli = CLI()
        exit_code = cli.run()
        
        return exit_code
        
    except KeyboardInterrupt:
        print("\nClicky the Clicker was interrupted by the user.")
        return 130
    except Exception as e:
        print(f"Error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
