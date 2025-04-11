#!/usr/bin/env python3
"""
Tests for the ActionController module
"""

import os
import sys
import json
import pytest
import tempfile
from unittest.mock import MagicMock, patch

# Add parent directory to path for importing modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.action_controller import ActionController

class TestActionController:
    """Tests for the ActionController class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Create mock dependencies
        self.mock_input_manager = MagicMock()
        self.mock_window_manager = MagicMock()
        self.mock_image_processor = MagicMock()
        
        # Create controller with mocks
        self.controller = ActionController(
            input_manager=self.mock_input_manager,
            window_manager=self.mock_window_manager,
            image_processor=self.mock_image_processor,
            debug_mode=True
        )
    
    def test_init(self):
        """Test ActionController initialization."""
        # Assert
        assert self.controller.input_manager == self.mock_input_manager
        assert self.controller.window_manager == self.mock_window_manager
        assert self.controller.image_processor == self.mock_image_processor
        assert self.controller.debug_mode == True
        assert self.controller.actions == []
        assert self.controller.is_running == False
        assert self.controller.loop_actions == False
        assert self.controller.continuous_mode == False
        assert self.controller.click_interval == 0.1
    
    def test_add_action(self):
        """Test adding an action."""
        # Setup
        action = {"type": "click_position", "x": 100, "y": 200}
        
        # Test
        self.controller.add_action(action)
        
        # Assert
        assert len(self.controller.actions) == 1
        assert self.controller.actions[0] == action
    
    def test_load_actions(self):
        """Test loading actions from a configuration file."""
        # Setup
        config = {
            "actions": [
                {"type": "click_position", "x": 100, "y": 200},
                {"type": "type_text", "text": "test"}
            ],
            "loop_actions": True,
            "continuous_mode": False,
            "click_interval": 0.5
        }
        
        # Create a temporary file
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp_file:
            json.dump(config, temp_file)
            config_path = temp_file.name
        
        try:
            # Test
            result = self.controller.load_actions(config_path)
            
            # Assert
            assert result == True
            assert len(self.controller.actions) == 2
            assert self.controller.actions[0]["type"] == "click_position"
            assert self.controller.actions[1]["type"] == "type_text"
            assert self.controller.loop_actions == True
            assert self.controller.continuous_mode == False
            assert self.controller.click_interval == 0.5
        finally:
            # Clean up
            os.unlink(config_path)
        
        # Test with invalid file
        result = self.controller.load_actions("nonexistent_file.json")
        assert result == False
    
    def test_save_actions(self):
        """Test saving actions to a configuration file."""
        # Setup
        self.controller.actions = [
            {"type": "click_position", "x": 100, "y": 200},
            {"type": "type_text", "text": "test"}
        ]
        self.controller.loop_actions = True
        self.controller.continuous_mode = False
        self.controller.click_interval = 0.5
        
        # Create a temporary file path
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            config_path = temp_file.name
        
        try:
            # Test
            result = self.controller.save_actions(config_path)
            
            # Assert
            assert result == True
            
            # Verify the saved file
            with open(config_path, 'r') as f:
                saved_config = json.load(f)
            
            assert len(saved_config["actions"]) == 2
            assert saved_config["actions"][0]["type"] == "click_position"
            assert saved_config["actions"][1]["type"] == "type_text"
            assert saved_config["loop_actions"] == True
            assert saved_config["continuous_mode"] == False
            assert saved_config["click_interval"] == 0.5
        finally:
            # Clean up
            os.unlink(config_path)
    
    @patch('modules.action_controller.time.sleep')
    def test_perform_action_click_position(self, mock_sleep):
        """Test performing click_position action."""
        # Setup
        action = {"type": "click_position", "x": 100, "y": 200, "button": 1}
        
        # Mock successful click
        self.mock_input_manager.click.return_value = True
        
        # Test
        success, desc = self.controller.perform_action(action, window_id=123)
        
        # Assert
        assert success == True
        self.mock_input_manager.click.assert_called_once_with(100, 200, 1, 123)
        
        # Test failure case
        self.mock_input_manager.click.reset_mock()
        self.mock_input_manager.click.return_value = False
        
        success, desc = self.controller.perform_action(action, window_id=123)
        
        # Assert
        assert success == False
        self.mock_input_manager.click.assert_called_once_with(100, 200, 1, 123)
    
    @patch('modules.action_controller.time.sleep')
    def test_perform_action_click_text(self, mock_sleep):
        """Test performing click_text action."""
        # Setup
        action = {"type": "click_text", "text": "test", "button": 1}
        
        # Mock successful screenshot and text finding
        mock_screenshot = MagicMock()
        self.mock_image_processor.capture_window_screenshot.return_value = mock_screenshot
        self.mock_image_processor.find_text_in_screenshot.return_value = (150, 250, 0.95)
        self.mock_input_manager.click.return_value = True
        
        # Test
        success, desc = self.controller.perform_action(action, window_id=123)
        
        # Assert
        assert success == True
        self.mock_image_processor.capture_window_screenshot.assert_called_once_with(123)
        self.mock_image_processor.find_text_in_screenshot.assert_called_once_with("test", mock_screenshot)
        self.mock_input_manager.click.assert_called_once_with(150, 250, 1, 123)
        
        # Test text not found
        self.mock_image_processor.capture_window_screenshot.reset_mock()
        self.mock_image_processor.find_text_in_screenshot.reset_mock()
        self.mock_input_manager.click.reset_mock()
        
        self.mock_image_processor.find_text_in_screenshot.return_value = None
        
        success, desc = self.controller.perform_action(action, window_id=123)
        
        # Assert
        assert success == False
        self.mock_image_processor.capture_window_screenshot.assert_called_once_with(123)
        self.mock_image_processor.find_text_in_screenshot.assert_called_once_with("test", mock_screenshot)
        self.mock_input_manager.click.assert_not_called()
    
    @patch('modules.action_controller.time.sleep')
    @patch('os.path.exists')
    def test_perform_action_click_template(self, mock_exists, mock_sleep):
        """Test performing click_template action."""
        # Setup
        action = {"type": "click_template", "template": "template.png", "button": 1, "threshold": 0.8}
        
        # Mock file exists
        mock_exists.return_value = True
        
        # Mock successful screenshot and template finding
        mock_screenshot = MagicMock()
        self.mock_image_processor.capture_window_screenshot.return_value = mock_screenshot
        self.mock_image_processor.find_template_in_screenshot.return_value = (150, 250, 0.95)
        self.mock_input_manager.click.return_value = True
        
        # Test
        success, desc = self.controller.perform_action(action, window_id=123)
        
        # Assert
        assert success == True
        self.mock_image_processor.capture_window_screenshot.assert_called_once_with(123)
        self.mock_image_processor.find_template_in_screenshot.assert_called_once_with(
            "template.png", mock_screenshot, threshold=0.8
        )
        self.mock_input_manager.click.assert_called_once_with(150, 250, 1, 123)
        
        # Test template not found
        self.mock_image_processor.capture_window_screenshot.reset_mock()
        self.mock_image_processor.find_template_in_screenshot.reset_mock()
        self.mock_input_manager.click.reset_mock()
        
        self.mock_image_processor.find_template_in_screenshot.return_value = None
        
        success, desc = self.controller.perform_action(action, window_id=123)
        
        # Assert
        assert success == False
        self.mock_image_processor.capture_window_screenshot.assert_called_once_with(123)
        self.mock_image_processor.find_template_in_screenshot.assert_called_once_with(
            "template.png", mock_screenshot, threshold=0.8
        )
        self.mock_input_manager.click.assert_not_called()
        
        # Test template file doesn't exist
        self.mock_image_processor.capture_window_screenshot.reset_mock()
        self.mock_image_processor.find_template_in_screenshot.reset_mock()
        
        mock_exists.return_value = False
        
        success, desc = self.controller.perform_action(action, window_id=123)
        
        # Assert
        assert success == False
        self.mock_image_processor.capture_window_screenshot.assert_not_called()
        self.mock_image_processor.find_template_in_screenshot.assert_not_called()
    
    @patch('modules.action_controller.time.sleep')
    def test_perform_action_type_text(self, mock_sleep):
        """Test performing type_text action."""
        # Setup
        action = {"type": "type_text", "text": "test"}
        
        # Mock successful typing
        self.mock_input_manager.type_text.return_value = True
        
        # Test
        success, desc = self.controller.perform_action(action, window_id=123)
        
        # Assert
        assert success == True
        self.mock_input_manager.type_text.assert_called_once_with("test", 123)
        
        # Test failure case
        self.mock_input_manager.type_text.reset_mock()
        self.mock_input_manager.type_text.return_value = False
        
        success, desc = self.controller.perform_action(action, window_id=123)
        
        # Assert
        assert success == False
        self.mock_input_manager.type_text.assert_called_once_with("test", 123)
    
    @patch('modules.action_controller.time.sleep')
    def test_perform_action_wait(self, mock_sleep):
        """Test performing wait action."""
        # Setup
        action = {"type": "wait", "duration": 2.5}
        
        # Test
        success, desc = self.controller.perform_action(action)
        
        # Assert
        assert success == True
        mock_sleep.assert_called_once_with(2.5)
    
    def test_get_action_description(self):
        """Test getting action descriptions."""
        # Setup various action types
        actions = [
            {"type": "click_text", "text": "test"},
            {"type": "click_template", "template": "/path/to/template.png"},
            {"type": "click_position", "x": 100, "y": 200},
            {"type": "type_text", "text": "test"},
            {"type": "wait", "duration": 2.5},
            {"type": "unknown"}
        ]
        
        # Test
        descriptions = [self.controller._get_action_description(action) for action in actions]
        
        # Assert
        assert descriptions[0] == "Click text: 'test'"
        assert descriptions[1] == "Click template: 'template.png'"
        assert descriptions[2] == "Click at position: (100, 200)"
        assert descriptions[3] == "Type text: 'test'"  # Debug mode is on
        assert descriptions[4] == "Wait (2.5 seconds)"
        assert descriptions[5] == "Unknown action: unknown"
        
        # Test with debug mode off
        self.controller.debug_mode = False
        assert self.controller._get_action_description(actions[3]) == "Type text (4 chars)"
    
    def test_cleanup(self):
        """Test cleanup method."""
        # Test
        self.controller.cleanup()
        
        # Assert cleanup was called on all managers
        self.mock_input_manager.cleanup.assert_called_once()
        self.mock_window_manager.cleanup.assert_called_once()
        self.mock_image_processor.cleanup.assert_called_once()
