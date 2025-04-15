# XTest Window Autoclicker Project

## Task Overview
Create a window autoclicker that uses X11's XTest extension to send synthetic mouse events without taking over the physical cursor, allowing the user to continue working normally.

## Progress
[X] Create project structure in .dotfiles/.local/bin/xtest_autoclicker
[X] Create main Python script (xtest_autoclicker.py)
[X] Create README with instructions
[X] Create installation script (install.sh)
[X] Add scratchpad to track progress and lessons
[X] Create smart_autoclicker.py with element recognition capabilities
[X] Update script for compatibility with i3 window manager on Ubuntu

## Technical Approach
- Using X11's XTest extension for synthetic mouse events
- xdotool for window detection and management
- Python-Xlib for X11 interaction
- OCR (Tesseract) for text recognition in windows
- OpenCV for template matching to find UI elements
- Interactive setup wizard for ease of use
- Command-line arguments for customization

## Lessons
- The XTest extension allows sending synthetic mouse events without moving the physical cursor
- XTest is specific to X11 and won't work on Wayland
- Window activation may be needed for some applications to properly receive the clicks
- Python-Xlib provides direct access to XTest functionality
- Window positions need to be tracked relative to window coordinates
- Some applications may have security measures that prevent synthetic input
- Tiling window managers like i3 require special handling for window geometry
- Multiple window geometry detection methods are needed for reliable operation across different window managers
- Direct window ID selection is better than trying to click on windows in tiling managers
- Having a way to list all window IDs is crucial for finding the right window in complex setups
- When targeting UI elements based on text, add a significant vertical offset (30px) for buttons below text
- Use grid-based clicking patterns with increasing coverage to handle various button layouts
- Visual debug markers are essential for troubleshooting click targeting issues
- XTest ButtonPress/ButtonRelease events DO NOT support direct positioning! Must use MotionNotify first
- Always use a sequence of: MotionNotify → ButtonPress → ButtonRelease → MotionNotify (to restore position)
- Multi-strategy clicking (trying different offsets and positions) works better than a single click attempt

## Implementation Plan: Multiple Cursor Support & Modular Design

### 1. Multiple Cursor Approach Using xinput

Linux's xinput utility can be used to create and manage virtual input devices, allowing for:

- Creation of a secondary cursor that doesn't interfere with the main cursor
- Separation of automation actions from user inputs

#### Implementation Ideas:

```bash
# Create a virtual pointer device
VIRTUAL_DEVICE=$(xinput create-master "Virtual Pointer")

# Get the ID of the new pointer
POINTER_ID=$(xinput list | grep "Virtual Pointer" | grep -oP "id=\K\d+")

# Send events to the virtual pointer
xinput set-ptr-feedback $POINTER_ID 0 0 0
xinput --test-xi2 $POINTER_ID  # Monitor events

# Move the virtual pointer
# This would require writing to the virtual device using low-level X11 APIs
```

**Challenges:**
- Requires root permissions or special udev rules
- Need to map window coordinates correctly
- May require substantial reworking of the X11 interaction code

### 2. Modular Design Improvements

#### Proposed Module Structure:

1. **Core Modules**
   - `input_manager.py`: Handle all input operations (clicks, typing)
   - `window_manager.py`: Handle window detection and focusing
   - `image_processor.py`: Handle screenshot capture and image recognition
   - `action_controller.py`: Orchestrate the execution of automation sequences

2. **UI Layer**
   - `cli.py`: Command line interface
   - `config_manager.py`: Configuration loading/saving

3. **Test Structure**
   - Unit tests for each module
   - Integration tests for common workflows
   - Mock objects for X11 display to enable testing without actual GUI

## Implementation Tasks

[X] Research xinput approach in detail
   - [X] Test creating virtual input devices (implemented proof of concept in xinput_poc.py)
   - [X] Determine if permissions can be handled gracefully (requires root for creating virtual input devices)
   - [X] Experiment with sending events to specific windows (implemented in InputManager)

[X] Create modular structure
   - [X] Define clear interfaces between modules
   - [X] Create new modular framework in /modules directory
   - [X] Implement dependency injection via constructor parameters

[X] Set up testing framework
   - [X] Create mock objects for X11 interactions in tests/mock_display.py
   - [X] Write initial tests for each core module
      - [X] InputManager tests
      - [X] WindowManager tests
      - [X] ImageProcessor tests
      - [X] ActionController tests
   - [ ] Implement CI workflow for automated testing

## Remaining Tasks

[X] Implement advanced features
   - [X] Create config import/export functionality (implemented in ConfigManager)
   - [X] Add action recording capability (implemented in recorder.py)
   - [X] Add error recovery mechanisms (implemented in error_recovery.py)
   - [X] Made configuration portable (changed to <app_dir>/config instead of ~/.config)

[ ] Improve documentation
   - [ ] Create README.md with installation and usage instructions
   - [ ] Add docstrings to all public functions
   - [ ] Create user guide with examples

[ ] Run extensive testing
   - [ ] Test with real scenarios
   - [ ] Test virtual pointer mode (with sudo)
   - [ ] Fix any bugs discovered during testing

## Original Next Steps (for the user)
1. Make the scripts executable: 
   ```
   chmod +x xtest_autoclicker.py smart_autoclicker.py install.sh
   ```

2. For i3 window manager, first list all windows to find the ID of the target window:
   ```
   ./smart_autoclicker.py --list-windows
   ```

3. Then run the autoclicker with the specific window ID:
   ```
   ./smart_autoclicker.py --window-id <ID> --i3
   ```

4. Optional: Run a test click to verify functionality:
   ```
   ./smart_autoclicker.py --window-id <ID> --test-click
   ```

## Testing Notes
- Some applications may require window activation to receive clicks properly
- If clicks aren't registering, try running without the --no-activate flag
- Applications can behave differently with synthetic vs. real mouse events
- The --i3 flag helps with tiling window managers
- If window detection fails, use --window-id approach

## Implementation Lessons

- When handling screenshots from different libraries (OpenCV, PIL, etc.), check the format and convert as needed (numpy arrays need to be converted to PIL Images for saving)
- When changing configuration paths, ensure all code paths that access files are updated consistently
- Error recovery mechanisms should handle recoverable errors gracefully and provide informative messages
- When working with OCR for text recognition, be aware that font styles, colors, and sizes can affect recognition accuracy
- Some UI elements (especially with custom fonts or rendering) may require special handling beyond OCR
- For critical UI elements that need to be clicked reliably, implement fallback mechanisms using window geometry

## Recent Improvements (April 2025)

- [X] Fixed indentation error in error_recovery.py (screenshot conversion code)
- [X] Improved text matching algorithm with fuzzy matching and better normalization
- [X] Enhanced screenshot capture to return PIL Images consistently
- [X] Added fallback mechanism for common UI elements that OCR struggles with
- [X] Added verbose logging for debugging text recognition issues

## Next Steps

- [X] Fix indentation errors in image_processor.py
- [ ] Add more specific UI element handlers for different applications
- [ ] Create a debug mode to save screenshots with OCR results visualized
- [ ] Add support for image-based element detection as an alternative to text
- [ ] Improve error messages with suggestions for manual configuration

## Current Issues (April 11, 2025)

- Fixed an indentation error in the `find_text_in_screenshot` method of image_processor.py
- Need to ensure all code is properly indented for consistent execution

## Test Improvement Plan (April 12, 2025)

### Test Types to Implement

1. **Unit Testing**
   - Test individual classes and methods in isolation
   - Mock external dependencies (X11, subprocess)
   - Focus on individual component correctness

2. **Integration Testing**
   - Test interaction between components
   - Verify modules work together as expected
   - Test communication between window manager and input manager

3. **Acceptance Testing**
   - Validate the software meets user requirements
   - Test common user workflows end-to-end 
   - Create test scenarios for different window managers

4. **Regression Testing**
   - Ensure new changes don't break existing functionality
   - Maintain baseline tests that cover core functionality
   - Automate tests to catch regressions early

5. **End-to-End Testing**
   - Test the entire application workflow
   - Include installation, configuration, and usage
   - Test with real window interactions (with safeguards)

6. **Smoke Testing**
   - Quick tests to verify basic functionality
   - Check that main features work after changes
   - Fast, simple tests that run before more complex tests

### Modularization Plan

1. **Separate XTestAutoclicker into Components**
   - Create WindowSelector module for window handling
   - Create ClickPositionManager for position management
   - Create EventSender for X11 event interactions
   - Move CLI parsing to separate module

2. **Create Common Interfaces**
   - Define clear interfaces between components
   - Enable easier mocking for testing
   - Improve extensibility

### Testing Frameworks & Tools

- pytest for test execution
- unittest.mock for mocking dependencies
- pytest-cov for test coverage analysis
- pytest-xvfb for headless X11 testing (when applicable)
- tox for testing in multiple environments

### Implementation Steps

1. Refactor code into modules
2. Create test fixtures and mocks
3. Write unit tests for each module
4. Create integration tests for module interactions
5. Implement acceptance tests for user stories
6. Add regression tests for core functionality
7. Create end-to-end tests for complete workflows
8. Implement smoke tests for quick verification

## Next Steps for Testing

[ ] Create test fixtures and mocks
[ ] Implement unit tests for all modules
[ ] Set up testing framework with pytest
[ ] Add CI automation for testing
[ ] Create documentation about testing