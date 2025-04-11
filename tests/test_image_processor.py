#!/usr/bin/env python3
"""
Tests for the ImageProcessor module
"""

import os
import sys
import pytest
import numpy as np
from unittest.mock import MagicMock, patch
from PIL import Image

# Add parent directory to path for importing modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.image_processor import ImageProcessor

class TestImageProcessor:
    """Tests for the ImageProcessor class."""
    
    def test_init(self):
        """Test ImageProcessor initialization."""
        # Test
        processor = ImageProcessor(debug_mode=True)
        
        # Assert
        assert processor.debug_mode == True
    
    @patch('modules.image_processor.ImageGrab.grab')
    def test_capture_screen_screenshot(self, mock_grab):
        """Test capturing screen screenshot."""
        # Setup
        mock_image = MagicMock(spec=Image.Image)
        mock_grab.return_value = mock_image
        
        processor = ImageProcessor(debug_mode=True)
        
        # Test
        screenshot = processor.capture_screen_screenshot()
        
        # Assert
        assert screenshot is not None
        mock_grab.assert_called_once()
    
    @patch('modules.image_processor.ImageGrab.grab')
    def test_capture_window_screenshot(self, mock_grab):
        """Test capturing window screenshot."""
        # Setup
        mock_image = MagicMock(spec=Image.Image)
        mock_grab.return_value = mock_image
        
        processor = ImageProcessor(debug_mode=True)
        
        # Create a mock get_window_by_id function
        def mock_get_window_by_id(window_id):
            return {
                "id": window_id,
                "x": 100,
                "y": 200,
                "width": 800,
                "height": 600
            }
        
        # Create a mock window manager
        mock_window_manager = MagicMock()
        mock_window_manager.get_window_by_id = mock_get_window_by_id
        processor.window_manager = mock_window_manager
        
        # Test with window_id
        screenshot = processor.capture_window_screenshot(123)
        
        # Assert
        assert screenshot is not None
        mock_grab.assert_called_once_with(bbox=(100, 200, 900, 800))
        
        # Test without window_id
        mock_grab.reset_mock()
        screenshot = processor.capture_window_screenshot(None)
        
        # Assert
        assert screenshot is not None
        mock_grab.assert_called_once() 
    
    @patch('modules.image_processor.pytesseract.image_to_data')
    def test_find_text_in_screenshot(self, mock_image_to_data):
        """Test finding text in screenshot."""
        # Setup
        # Mock pytesseract output
        mock_image_to_data.return_value = """level	page_num	block_num	par_num	line_num	word_num	left	top	width	height	conf	text
1	1	0	0	0	0	0	0	800	600	-1	
2	1	1	0	0	0	74	106	651	390	-1	
3	1	1	1	0	0	74	106	651	390	-1	
4	1	1	1	1	0	74	106	651	36	-1	
5	1	1	1	1	1	74	106	93	36	96.868256	test
5	1	1	1	1	2	171	106	149	36	96.868256	button"""
        
        processor = ImageProcessor(debug_mode=True)
        
        # Create a mock PIL image
        mock_image = MagicMock(spec=Image.Image)
        
        # Test finding text
        result = processor.find_text_in_screenshot("test", mock_image)
        
        # Assert
        assert result is not None
        assert len(result) == 3
        assert result[0] == 74 + 93//2  # x center
        assert result[1] == 106 + 36//2  # y center
        assert result[2] > 0.9  # confidence
        
        # Test text not found
        result = processor.find_text_in_screenshot("nonexistent", mock_image)
        
        # Assert
        assert result is None
    
    @patch('modules.image_processor.cv2.matchTemplate')
    @patch('modules.image_processor.cv2.minMaxLoc')
    @patch('modules.image_processor.cv2.imread')
    def test_find_template_in_screenshot(self, mock_imread, mock_minMaxLoc, mock_matchTemplate):
        """Test finding template in screenshot."""
        # Setup
        # Mock template image
        mock_template = np.zeros((50, 50, 3), dtype=np.uint8)
        mock_imread.return_value = mock_template
        
        # Mock match result
        mock_matchTemplate.return_value = np.zeros((50, 50), dtype=np.float32)
        
        # Mock minMaxLoc result (min_val, max_val, min_loc, max_loc)
        mock_minMaxLoc.return_value = (0.0, 0.8, (0, 0), (100, 150))
        
        processor = ImageProcessor(debug_mode=True)
        
        # Create a mock PIL image
        mock_image = MagicMock(spec=Image.Image)
        mock_image.size = (800, 600)
        
        # Convert PIL image to numpy array for mock
        processor._pil_to_cv = MagicMock(return_value=np.zeros((600, 800, 3), dtype=np.uint8))
        
        # Test finding template (with confidence above threshold)
        result = processor.find_template_in_screenshot("template.png", mock_image, threshold=0.7)
        
        # Assert
        assert result is not None
        assert len(result) == 3
        assert result[0] == 125  # x center (100 + 50/2)
        assert result[1] == 175  # y center (150 + 50/2)
        assert result[2] == 0.8  # confidence
        
        # Test finding template (with confidence below threshold)
        mock_minMaxLoc.return_value = (0.0, 0.6, (0, 0), (100, 150))
        
        result = processor.find_template_in_screenshot("template.png", mock_image, threshold=0.7)
        
        # Assert
        assert result is None
    
    def test_text_matches(self):
        """Test text matching functionality."""
        processor = ImageProcessor(debug_mode=True)
        
        # Test exact match
        assert processor._text_matches("test", "test") is True
        
        # Test case insensitive match
        assert processor._text_matches("Test", "test") is True
        
        # Test substring match
        assert processor._text_matches("testbutton", "test") is True
        
        # Test non-match
        assert processor._text_matches("button", "test") is False
    
    def test_cleanup(self):
        """Test cleanup method."""
        processor = ImageProcessor(debug_mode=True)
        
        # There's not much to test here since cleanup is a no-op for ImageProcessor
        processor.cleanup()
        # Just make sure it doesn't raise an exception
