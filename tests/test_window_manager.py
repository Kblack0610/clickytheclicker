#!/usr/bin/env python3
"""
Tests for the WindowManager module
"""

import os
import sys
import pytest
from unittest.mock import MagicMock, patch

# Add parent directory to path for importing modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.window_manager import WindowManager

class TestWindowManager:
    """Tests for the WindowManager class."""
    
    @patch('modules.window_manager.Xlib.display.Display')
    def test_init(self, mock_display_class):
        """Test WindowManager initialization."""
        # Setup
        mock_display = mock_display_class.return_value
        
        # Test
        window_manager = WindowManager(debug_mode=True)
        
        # Assert
        assert window_manager.display is not None
        assert window_manager.debug_mode == True
        assert window_manager.is_i3 == False
    
    @patch('modules.window_manager.subprocess.check_output')
    def test_list_windows(self, mock_check_output):
        """Test listing windows."""
        # Setup
        mock_check_output.return_value = "123\n456\n789\n"
        
        window_manager = WindowManager(debug_mode=True)
        
        # Mock get_window_info to return test data
        window_manager.get_window_by_id = MagicMock(side_effect=[
            {"id": 123, "name": "Terminal", "width": 800, "height": 600},
            {"id": 456, "name": "Browser", "width": 1024, "height": 768},
            {"id": 789, "name": "Editor", "width": 1200, "height": 800}
        ])
        
        # Test
        windows = window_manager.list_windows()
        
        # Assert
        assert len(windows) == 3
        assert windows[0]["id"] == 123
        assert windows[0]["name"] == "Terminal"
        assert windows[1]["id"] == 456
        assert windows[1]["name"] == "Browser"
        assert windows[2]["id"] == 789
        assert windows[2]["name"] == "Editor"
        
        # Test with i3 mode
        window_manager.is_i3 = True
        mock_check_output.return_value = """
        {
            "id": 123,
            "name": "Terminal",
            "rect": {"width": 800, "height": 600, "x": 0, "y": 0}
        }
        {
            "id": 456,
            "name": "Browser",
            "rect": {"width": 1024, "height": 768, "x": 100, "y": 100}
        }
        """
        
        # We need to handle i3 output differently
        window_manager.get_window_by_id = MagicMock(side_effect=[
            {"id": 123, "name": "Terminal", "width": 800, "height": 600, "x": 0, "y": 0},
            {"id": 456, "name": "Browser", "width": 1024, "height": 768, "x": 100, "y": 100}
        ])
        
        # Test with i3 mode
        windows = window_manager.list_windows()
        
        # Assert
        assert len(windows) == 2
        assert windows[0]["id"] == 123
        assert windows[0]["name"] == "Terminal"
        assert windows[1]["id"] == 456
        assert windows[1]["name"] == "Browser"
    
    @patch('modules.window_manager.Xlib.display.Display')
    def test_get_window_by_id(self, mock_display_class):
        """Test getting window by ID."""
        # Setup
        mock_display = mock_display_class.return_value
        mock_window = MagicMock()
        mock_window.get_wm_name.return_value = "Test Window"
        mock_geometry = MagicMock()
        mock_geometry.width = 800
        mock_geometry.height = 600
        mock_geometry.x = 100
        mock_geometry.y = 200
        mock_window.get_geometry.return_value = mock_geometry
        
        # Make create_resource_object return our mock window
        mock_display.create_resource_object.return_value = mock_window
        
        window_manager = WindowManager(debug_mode=True)
        window_manager.display = mock_display
        
        # Test
        window = window_manager.get_window_by_id(123)
        
        # Assert
        assert window is not None
        assert window["id"] == 123
        assert window["name"] == "Test Window"
        assert window["width"] == 800
        assert window["height"] == 600
        assert window["x"] == 100
        assert window["y"] == 200
        
        # Test error case
        mock_display.create_resource_object.side_effect = Exception("Test error")
        
        window = window_manager.get_window_by_id(456)
        
        # Assert
        assert window is None
    
    @patch('modules.window_manager.Xlib.display.Display')
    def test_focus_window(self, mock_display_class):
        """Test focusing a window."""
        # Setup
        mock_display = mock_display_class.return_value
        mock_window = MagicMock()
        
        # Make create_resource_object return our mock window
        mock_display.create_resource_object.return_value = mock_window
        
        window_manager = WindowManager(debug_mode=True)
        window_manager.display = mock_display
        
        # Test
        result = window_manager.focus_window(123)
        
        # Assert
        assert result is True
        mock_window.set_input_focus.assert_called_once()
        
        # Test error case
        mock_display.create_resource_object.side_effect = Exception("Test error")
        
        result = window_manager.focus_window(456)
        
        # Assert
        assert result is False
    
    @patch('modules.window_manager.Xlib.display.Display')
    def test_cleanup(self, mock_display_class):
        """Test cleanup method."""
        # Setup
        mock_display = mock_display_class.return_value
        window_manager = WindowManager(debug_mode=True)
        window_manager.display = mock_display
        
        # Test
        window_manager.cleanup()
        
        # Assert
        mock_display.close.assert_called_once()
