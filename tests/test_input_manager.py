#!/usr/bin/env python3
"""
Tests for the InputManager module
"""

import os
import sys
import pytest
from unittest.mock import MagicMock, patch

# Add parent directory to path for importing modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.input_manager import InputManager
from tests.mock_display import X, XK, xtest

class TestInputManager:
    """Tests for the InputManager class."""
    
    @patch('modules.input_manager.Xlib.display.Display')
    def test_init(self, mock_display_class):
        """Test InputManager initialization."""
        # Setup
        mock_display = mock_display_class.return_value
        
        # Test
        input_manager = InputManager(debug_mode=True)
        
        # Assert
        assert input_manager.display is not None
        assert input_manager.debug_mode == True
        assert input_manager.use_virtual_pointer == False
    
    @patch('modules.input_manager.Xlib.display.Display')
    @patch('modules.input_manager.Xlib.ext.xtest.fake_input')
    def test_click(self, mock_fake_input, mock_display_class):
        """Test click functionality."""
        # Setup
        mock_display = mock_display_class.return_value
        mock_root = MagicMock()
        mock_screen = MagicMock()
        mock_screen.root = mock_root
        mock_display.screen.return_value = mock_screen
        
        input_manager = InputManager(debug_mode=True)
        input_manager.display = mock_display
        
        # Test clicking with default button
        success = input_manager.click(100, 200)
        
        # Assert
        assert success == True
        # Verify button press and release were called
        assert mock_fake_input.call_count == 2
        # First call should be button press
        mock_fake_input.assert_any_call(mock_display, X.ButtonPress, 1, root_x=100, root_y=200)
        # Second call should be button release
        mock_fake_input.assert_any_call(mock_display, X.ButtonRelease, 1, root_x=100, root_y=200)
        
        # Reset mock and test with different button
        mock_fake_input.reset_mock()
        
        # Test clicking with right button
        success = input_manager.click(300, 400, button=3)
        
        # Assert
        assert success == True
        # Verify button press and release were called with button 3
        assert mock_fake_input.call_count == 2
        mock_fake_input.assert_any_call(mock_display, X.ButtonPress, 3, root_x=300, root_y=400)
        mock_fake_input.assert_any_call(mock_display, X.ButtonRelease, 3, root_x=300, root_y=400)
    
    @patch('modules.input_manager.Xlib.display.Display')
    @patch('modules.input_manager.Xlib.ext.xtest.fake_input')
    def test_type_text(self, mock_fake_input, mock_display_class):
        """Test typing text functionality."""
        # Setup
        mock_display = mock_display_class.return_value
        input_manager = InputManager(debug_mode=True)
        input_manager.display = mock_display
        
        # Mock string_to_keysym to return the char code
        input_manager._string_to_keysym = lambda c: ord(c)
        
        # Test
        success = input_manager.type_text("test")
        
        # Assert
        assert success == True
        # Each character should have 2 calls (press and release)
        assert mock_fake_input.call_count == 8
        
        # Verify each key press and release
        expected_keycodes = [ord(c) for c in "test"]
        for keycode in expected_keycodes:
            mock_fake_input.assert_any_call(mock_display, X.KeyPress, keycode)
            mock_fake_input.assert_any_call(mock_display, X.KeyRelease, keycode)
    
    @patch('modules.input_manager.Xlib.display.Display')
    @patch('subprocess.run')
    def test_create_virtual_pointer(self, mock_run, mock_display_class):
        """Test virtual pointer creation."""
        # Setup
        mock_display = mock_display_class.return_value
        
        # Mock successful command execution
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = "Virtual core pointer id=2"
        mock_run.return_value = mock_process
        
        input_manager = InputManager(use_virtual_pointer=True, debug_mode=True)
        
        # Test
        result = input_manager._create_virtual_pointer()
        
        # Assert
        assert result is True
        mock_run.assert_called_once()
        
        # Test error case
        mock_run.reset_mock()
        mock_process.returncode = 1
        mock_run.return_value = mock_process
        
        result = input_manager._create_virtual_pointer()
        
        # Assert
        assert result is False
        mock_run.assert_called_once()
    
    @patch('modules.input_manager.Xlib.display.Display')
    def test_cleanup(self, mock_display_class):
        """Test cleanup method."""
        # Setup
        mock_display = mock_display_class.return_value
        input_manager = InputManager(debug_mode=True)
        input_manager.display = mock_display
        
        # Set virtual pointer to simulate cleanup 
        input_manager.virtual_pointer_id = 12
        
        # Mock remove virtual pointer method
        input_manager._remove_virtual_pointer = MagicMock(return_value=True)
        
        # Test
        input_manager.cleanup()
        
        # Assert
        mock_display.close.assert_called_once()
        if input_manager.virtual_pointer_id:
            input_manager._remove_virtual_pointer.assert_called_once()
