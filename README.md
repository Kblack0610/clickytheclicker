# Clicky the Clicker

An X11 autoclicker that clicks within specific application windows **without moving your physical mouse cursor**, allowing you to continue working normally while the autoclicker operates independently. This project now features a modular architecture with support for virtual pointers, OCR text recognition, and template matching.

## Features

- Sends synthetic mouse events that don't affect your physical cursor
- Select a specific window for automation
- Define multiple click positions within the window
- Set custom click intervals
- Add random jitter for more natural behavior
- Limit the total number of clicks
- Option to enable/disable window activation
- **New Features:**
  - Modular architecture for better maintainability and testing
  - Virtual pointer support (with root privileges) for complete separation from user input
  - OCR text recognition to find and click on text elements
  - Template matching to find and click on graphical elements
  - Action sequences with support for clicks, typing, and waiting
  - Configuration saving and loading

## How It Works

This tool uses the X11 XTest extension to send synthetic mouse events directly to X11 windows. Unlike traditional autoclickers that take over your physical mouse, this tool:

1. Uses XTest to send "virtual" mouse events to the target window
2. Leaves your physical mouse cursor free for you to use normally
3. Works even when the target window isn't in focus (in most cases)

## Requirements

- Linux with X11 (not Wayland)
- Python 3.6+
- xdotool (for window selection and geometry)
- Python-xlib (for XTest events)
- Optional: Tesseract OCR (for text recognition)
- Optional: OpenCV and NumPy (for template matching)

## Installation

1. Install system dependencies:
```bash
sudo apt-get install xdotool tesseract-ocr
```

2. Install Python dependencies:
```bash
pip install -r requirements.txt
```

3. Make the script executable:
```bash
chmod +x clicky.py
```

4. Optional: For virtual pointer support (requires root):
```bash
sudo apt-get install xinput
```

## Usage

### Basic Usage

Run the main script:
```bash
./clicky.py
```

### List Available Windows

```bash
./clicky.py --list-windows
```

This will show all available windows with their IDs and names.

### Running Automation

```bash
./clicky.py --window-id <ID> --config <config_file.json>
```

or

```bash
./clicky.py --window-name "Firefox" --config <config_file.json>
```

### Command Line Options

```bash
./clicky.py --window-id <ID> --interval 0.5 --loop --max-cycles 10
```

Options:
- `--window-id`: ID of the window to automate
- `--window-name`: Name of the window to automate (partial match)
- `--interval`: Time between actions in seconds (default: 0.1)
- `--loop`: Loop the action sequence indefinitely
- `--continuous`: Continuous mode - retry on failures
- `--max-cycles`: Maximum number of cycles before stopping (default: unlimited)
- `--debug`: Enable debug output
- `--config`: Path to a configuration file with actions
- `--save-config`: Save current sequence to a configuration file
- `--virtual-pointer`: Use virtual pointer (requires root)

### Testing Features

```bash
./clicky.py --window-id <ID> --test-click
```

Clicks in the center of the specified window.

```bash
./clicky.py --window-id <ID> --test-ocr
```

Tests OCR functionality by allowing you to find text in the window.

```bash
./clicky.py --window-id <ID> --test-template <image.png>
```

Tests template matching with the specified image.

### During Operation

- Press Ctrl+C to stop the autoclicker

## Troubleshooting

Common issues:

1. **Clicks not registering**: Some applications may require window activation. If clicks aren't registering, try running without the `--no-activate` option.

2. **Window selection issues**: If selecting a window by clicking doesn't work, try using the `--window-name` option instead.

3. **XTest not working**: If you're using Wayland instead of X11, this tool won't work as XTest is an X11 extension. Check your display server with `echo $XDG_SESSION_TYPE`.

4. **Permission errors**: If you see X11 permission errors, try running `xhost +local:` to temporarily allow local connections to X server.

## Technical Details

The XTest extension provides a way to generate input events without actually moving the input devices. This allows programs to:

- Generate synthetic mouse and keyboard events
- Perform automated testing of GUI applications 
- Create automation tools that don't disturb the user

This is much different from PyAutoGUI or similar libraries that move the physical cursor.