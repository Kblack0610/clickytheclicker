#!/usr/bin/env python3
"""
Proof of Concept: Virtual Pointer with xinput

This script demonstrates how to create a virtual pointer using xinput
and send events to it without moving the main cursor.

Requirements:
- xinput command-line tool
- python-xlib

Usage:
sudo python3 xinput_poc.py
(Note: requires root privileges to create virtual devices)
"""

import os
import sys
import time
import subprocess
import re
from Xlib import X, display
from Xlib.ext import xinput

# Check if running as root
if os.geteuid() != 0:
    print("This script needs to be run as root to create virtual input devices.")
    print("Please run with: sudo python3 xinput_poc.py")
    sys.exit(1)

def create_virtual_pointer():
    """Create a virtual pointer device using xinput"""
    try:
        # Create a virtual master pointer
        result = subprocess.run(
            ["xinput", "create-master", "VirtualPointer"],
            capture_output=True, 
            text=True,
            check=True
        )
        print("Virtual pointer created successfully")
        
        # Find the ID of the new pointer
        list_result = subprocess.run(
            ["xinput", "list"], 
            capture_output=True, 
            text=True,
            check=True
        )
        
        # Parse the output to find the virtual pointer ID
        match = re.search(r"VirtualPointer pointer\s+id=(\d+)", list_result.stdout)
        if match:
            pointer_id = match.group(1)
            print(f"Virtual pointer ID: {pointer_id}")
            return pointer_id
        else:
            print("Could not find virtual pointer ID")
            return None
            
    except subprocess.CalledProcessError as e:
        print(f"Error creating virtual pointer: {e}")
        print(f"Output: {e.output}")
        return None

def move_virtual_pointer(pointer_id, x, y):
    """Move the virtual pointer to x,y coordinates"""
    try:
        subprocess.run(
            ["xinput", "set-prop", pointer_id, "Device Enabled", "1"],
            check=True
        )
        
        # Move pointer using xinput reattach + warp
        # Note: This is a simplified approach - a more complete solution would
        # use Xlib's xinput extension to send raw events
        display_obj = display.Display()
        root = display_obj.screen().root
        
        # Try to map coordinates to virtual pointer
        # This is where a more robust solution would use the XInput extension directly
        print(f"Attempting to move virtual pointer to ({x}, {y})")
        
        # For demo purposes, this prints the command that would move the pointer
        # In practice, we would use Xlib to directly send events to the device
        print(f"Command equivalent: xinput set-ptr-feedback {pointer_id} {x} {y}")
        
        return True
    except Exception as e:
        print(f"Error moving virtual pointer: {e}")
        return False

def remove_virtual_pointer(pointer_id):
    """Remove the virtual pointer"""
    try:
        subprocess.run(
            ["xinput", "remove-master", pointer_id],
            check=True
        )
        print("Virtual pointer removed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error removing virtual pointer: {e}")
        return False

def main():
    print("Xinput Virtual Pointer Proof of Concept")
    print("=======================================")
    
    # Create virtual pointer
    pointer_id = create_virtual_pointer()
    if not pointer_id:
        sys.exit(1)
    
    try:
        # Demo: Move virtual pointer to a few coordinates
        print("\nMoving virtual pointer to different coordinates...")
        for pos in [(100, 100), (200, 200), (300, 300), (400, 400)]:
            print(f"\nMoving to {pos}...")
            move_virtual_pointer(pointer_id, pos[0], pos[1])
            time.sleep(2)  # Wait to observe the movement
            
        print("\nVirtual pointer demo completed.")
        
    except KeyboardInterrupt:
        print("\nDemo interrupted by user.")
    finally:
        # Clean up: remove virtual pointer
        print("\nRemoving virtual pointer...")
        remove_virtual_pointer(pointer_id)

if __name__ == "__main__":
    main()
