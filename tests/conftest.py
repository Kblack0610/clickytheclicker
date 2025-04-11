#!/usr/bin/env python3
"""
Pytest configuration for Clicky the Clicker tests
"""

import os
import sys
import pytest

# Add the parent directory to the path for importing modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.mock_display import create_mock_display_with_windows

@pytest.fixture
def mock_display():
    """
    Fixture to provide a mock X11 display for testing.
    """
    return create_mock_display_with_windows()
