#!/usr/bin/env python3
"""
Unit tests for the ClickPositionManager module
"""

import os
import sys
import pytest
from unittest.mock import MagicMock, patch

# Add parent directory to path for importing modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from modules.click_position_manager import ClickPositionManager

class TestClickPositionManager:
    """Unit tests for the ClickPositionManager class."""
    
    def test_init(self):
        """Test ClickPositionManager initialization."""
        manager = ClickPositionManager()
        assert manager is not None
        assert manager.click_positions == []
        assert manager.jitter == 0
        assert manager.debug_mode is False
        
        manager_debug = ClickPositionManager(debug_mode=True)
        assert manager_debug.debug_mode is True
    
    def test_add_click_position(self):
        """Test adding a click position."""
        manager = ClickPositionManager()
        
        # Test
        manager.add_click_position(100, 200)
        
        # Assert
        assert len(manager.click_positions) == 1
        assert manager.click_positions[0] == (100, 200)
        
        # Add another position
        manager.add_click_position(300, 400)
        assert len(manager.click_positions) == 2
        assert manager.click_positions[1] == (300, 400)
    
    @patch('modules.click_position_manager.subprocess.run')
    @patch('modules.click_position_manager.input')
    def test_capture_click_position(self, mock_input, mock_run):
        """Test capturing a mouse position."""
        # Setup
        mock_input.return_value = ""  # Simulate pressing Enter
        
        mock_result = MagicMock()
        mock_result.stdout = "X=150\nY=250\n"
        mock_run.return_value = mock_result
        
        manager = ClickPositionManager()
        window_geometry = (50, 50, 800, 600)
        
        # Test
        result = manager.capture_click_position(window_geometry)
        
        # Assert
        assert result is True
        assert len(manager.click_positions) == 1
        assert manager.click_positions[0] == (100, 200)  # 150-50, 250-50
        
        # Test with no window geometry
        manager.click_positions = []
        result = manager.capture_click_position(None)
        assert result is False
        assert len(manager.click_positions) == 0
        
        # Test with incomplete mouse data
        mock_result.stdout = "X=150\n"  # Missing Y
        result = manager.capture_click_position(window_geometry)
        assert result is False
        
        # Test with subprocess error
        mock_run.side_effect = Exception("Test error")
        result = manager.capture_click_position(window_geometry)
        assert result is False
    
    def test_set_jitter(self):
        """Test setting jitter amount."""
        manager = ClickPositionManager()
        
        # Test
        manager.set_jitter(10)
        
        # Assert
        assert manager.jitter == 10
        
        # Test disabling jitter
        manager.set_jitter(0)
        assert manager.jitter == 0
    
    def test_get_click_positions(self):
        """Test getting the list of click positions."""
        manager = ClickPositionManager()
        
        # Add some positions
        manager.add_click_position(100, 200)
        manager.add_click_position(300, 400)
        
        # Test
        positions = manager.get_click_positions()
        
        # Assert
        assert positions == [(100, 200), (300, 400)]
        
        # Verify it's a copy by modifying the returned list
        positions.append((500, 600))
        assert len(manager.click_positions) == 2  # Original list unchanged
    
    def test_clear_click_positions(self):
        """Test clearing all click positions."""
        manager = ClickPositionManager()
        
        # Add some positions
        manager.add_click_position(100, 200)
        manager.add_click_position(300, 400)
        assert len(manager.click_positions) == 2
        
        # Test
        manager.clear_click_positions()
        
        # Assert
        assert len(manager.click_positions) == 0
    
    def test_get_jittered_position(self):
        """Test applying jitter to a position."""
        manager = ClickPositionManager()
        
        # Test with jitter disabled
        position = manager.get_jittered_position(100, 200)
        assert position == (100, 200)
        
        # Test with jitter enabled
        manager.set_jitter(10)
        position = manager.get_jittered_position(100, 200)
        
        # Position should be within jitter range
        assert 90 <= position[0] <= 110
        assert 190 <= position[1] <= 210
        
        # Test with different base position
        position = manager.get_jittered_position(300, 400)
        assert 290 <= position[0] <= 310
        assert 390 <= position[1] <= 410
