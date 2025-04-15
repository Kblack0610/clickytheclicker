#!/usr/bin/env python3
"""
Unit tests for the WindowSelector module
"""

import os
import sys
import pytest
from unittest.mock import MagicMock, patch

# Add parent directory to path for importing modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from modules.window_selector import WindowSelector

class TestWindowSelector:
    """Unit tests for the WindowSelector class."""
    
    def test_init(self):
        """Test WindowSelector initialization."""
        selector = WindowSelector()
        assert selector is not None
        assert selector.selected_window is None
        assert selector.window_geometry is None
        assert selector.debug_mode is False
        
        selector_debug = WindowSelector(debug_mode=True)
        assert selector_debug.debug_mode is True
    
    @patch('modules.window_selector.subprocess.run')
    def test_select_window_by_click(self, mock_run):
        """Test selecting a window by clicking on it."""
        # Setup
        mock_result = MagicMock()
        mock_result.stdout = "WINDOW=0x12345678\nX=100\nY=200\n"
        mock_run.return_value = mock_result
        
        selector = WindowSelector()
        
        # Mock get_window_name and get_window_geometry
        selector.get_window_name = MagicMock(return_value="Test Window")
        selector.get_window_geometry = MagicMock(return_value=(10, 20, 800, 600))
        
        # Test
        result = selector.select_window_by_click()
        
        # Assert
        assert result is True
        assert selector.selected_window == 0x12345678
        assert selector.window_geometry == (10, 20, 800, 600)
        selector.get_window_name.assert_called_once_with(0x12345678)
        selector.get_window_geometry.assert_called_once_with(0x12345678)
        
        # Test failure case
        mock_run.side_effect = Exception("Test error")
        result = selector.select_window_by_click()
        assert result is False
    
    @patch('modules.window_selector.subprocess.run')
    def test_select_window_by_name(self, mock_run):
        """Test selecting a window by name."""
        # Setup
        mock_result = MagicMock()
        mock_result.stdout = "12345678\n"
        mock_run.return_value = mock_result
        
        selector = WindowSelector()
        
        # Mock get_window_name and get_window_geometry
        selector.get_window_geometry = MagicMock(return_value=(10, 20, 800, 600))
        
        # Test
        result = selector.select_window_by_name("Test Window")
        
        # Assert
        assert result is True
        assert selector.selected_window == 12345678
        selector.get_window_geometry.assert_called_once_with(12345678)
        
        # Test failure case - no window found
        mock_result.stdout = ""
        result = selector.select_window_by_name("Nonexistent Window")
        assert result is False
        
        # Test failure case - exception
        mock_run.side_effect = Exception("Test error")
        result = selector.select_window_by_name("Test Window")
        assert result is False
    
    @patch('modules.window_selector.subprocess.run')
    def test_get_window_name(self, mock_run):
        """Test getting a window name by ID."""
        # Setup
        mock_result = MagicMock()
        mock_result.stdout = "Test Window\n"
        mock_run.return_value = mock_result
        
        selector = WindowSelector()
        
        # Test
        name = selector.get_window_name(12345678)
        
        # Assert
        assert name == "Test Window"
        mock_run.assert_called_once()
        
        # Test failure case
        mock_run.side_effect = Exception("Test error")
        name = selector.get_window_name(12345678)
        assert name == "Unknown"
    
    @patch('modules.window_selector.subprocess.run')
    def test_get_window_geometry(self, mock_run):
        """Test getting window geometry."""
        # Setup
        mock_result = MagicMock()
        mock_result.stdout = "X=10\nY=20\nWIDTH=800\nHEIGHT=600\n"
        mock_run.return_value = mock_result
        
        selector = WindowSelector()
        
        # Test
        geometry = selector.get_window_geometry(12345678)
        
        # Assert
        assert geometry == (10, 20, 800, 600)
        mock_run.assert_called_once()
        
        # Test incomplete data
        mock_result.stdout = "X=10\nY=20\nWIDTH=800\n"  # Missing HEIGHT
        geometry = selector.get_window_geometry(12345678)
        assert geometry is None
        
        # Test failure case
        mock_run.side_effect = Exception("Test error")
        geometry = selector.get_window_geometry(12345678)
        assert geometry is None
    
    def test_get_selected_window_info(self):
        """Test getting information about the selected window."""
        # Setup
        selector = WindowSelector()
        selector.selected_window = 12345678
        selector.window_geometry = (10, 20, 800, 600)
        selector.get_window_name = MagicMock(return_value="Test Window")
        
        # Test
        info = selector.get_selected_window_info()
        
        # Assert
        assert info is not None
        assert info['id'] == 12345678
        assert info['name'] == "Test Window"
        assert info['geometry']['x'] == 10
        assert info['geometry']['y'] == 20
        assert info['geometry']['width'] == 800
        assert info['geometry']['height'] == 600
        
        # Test with no window selected
        selector.selected_window = None
        info = selector.get_selected_window_info()
        assert info is None
        
        # Test with no geometry
        selector.selected_window = 12345678
        selector.window_geometry = None
        info = selector.get_selected_window_info()
        assert info is None
