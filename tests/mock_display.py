#!/usr/bin/env python3
"""
Mock X11 Display for Testing

Provides mock objects for X11 display and windows to allow testing without
an actual X server connection.
"""

class MockGeometry:
    """Mock for X11 window geometry."""
    
    def __init__(self, x=0, y=0, width=800, height=600):
        self.x = x
        self.y = y
        self.width = width
        self.height = height

class MockAttributes:
    """Mock for X11 window attributes."""
    
    def __init__(self, map_state=1):  # 1 = IsViewable
        self.map_state = map_state

class MockWindow:
    """Mock for X11 window."""
    
    def __init__(self, window_id, name="Test Window", x=0, y=0, width=800, height=600, viewable=True):
        """
        Initialize a mock window.
        
        Args:
            window_id: Window ID
            name: Window name
            x: X position
            y: Y position
            width: Window width
            height: Window height
            viewable: Whether the window is viewable
        """
        self.id = window_id
        self._name = name
        self._x = x
        self._y = y
        self._width = width
        self._height = height
        self._map_state = 1 if viewable else 0  # 1 = IsViewable
        self._parent = None
        self._children = []
    
    def get_geometry(self):
        """Get window geometry."""
        return MockGeometry(self._x, self._y, self._width, self._height)
    
    def get_attributes(self):
        """Get window attributes."""
        return MockAttributes(self._map_state)
    
    def get_wm_name(self):
        """Get window name."""
        return self._name
    
    def set_parent(self, parent):
        """Set window parent."""
        self._parent = parent
    
    def add_child(self, child):
        """Add a child window."""
        self._children.append(child)
        child.set_parent(self)
    
    def query_tree(self):
        """Get window tree."""
        return MockTree(self._parent, self._children)
    
    def set_input_focus(self, revert_to, time):
        """Set input focus."""
        # Mock implementation - just return True
        return True

class MockTree:
    """Mock for X11 window tree query result."""
    
    def __init__(self, parent=None, children=None):
        """
        Initialize a mock tree.
        
        Args:
            parent: Parent window
            children: List of child windows
        """
        self.parent = parent
        self.children = children or []

class MockRoot:
    """Mock for X11 root window."""
    
    def __init__(self, width=1920, height=1080):
        """
        Initialize a mock root window.
        
        Args:
            width: Screen width
            height: Screen height
        """
        self.id = 0
        self._width = width
        self._height = height
        self._children = []
    
    def query_tree(self):
        """Get window tree."""
        return MockTree(None, self._children)
    
    def add_child(self, child):
        """Add a child window."""
        self._children.append(child)
        child.set_parent(self)
    
    def warp_pointer(self, x, y):
        """Mock warp pointer."""
        return True
    
    def screen(self):
        """Get screen."""
        return self

class MockScreen:
    """Mock for X11 screen."""
    
    def __init__(self, width=1920, height=1080):
        """
        Initialize a mock screen.
        
        Args:
            width: Screen width
            height: Screen height
        """
        self._width = width
        self._height = height
        self.root = MockRoot(width, height)
    
    def root(self):
        """Get root window."""
        return self.root

class MockDisplay:
    """Mock for X11 display."""
    
    def __init__(self, screens=None):
        """
        Initialize a mock display.
        
        Args:
            screens: List of screens
        """
        self._screens = screens or [MockScreen()]
        self._windows = {}
        self._closed = False
    
    def screen(self, screen_num=0):
        """Get screen."""
        return self._screens[screen_num]
    
    def create_resource_object(self, resource_type, resource_id):
        """Create resource object (e.g. window)."""
        if resource_type == 'window':
            if resource_id in self._windows:
                return self._windows[resource_id]
            else:
                # Create a new window with this ID
                window = MockWindow(resource_id)
                self._windows[resource_id] = window
                return window
        return None
    
    def add_window(self, window):
        """Add a window to the display."""
        self._windows[window.id] = window
    
    def sync(self):
        """Synchronize with the X server."""
        # Mock implementation - just return
        pass
    
    def close(self):
        """Close the display connection."""
        self._closed = True
    
    def is_closed(self):
        """Check if the display is closed."""
        return self._closed

# Constants that would normally be provided by Xlib
class X:
    """Mock for X11 constants."""
    ButtonPress = 4
    ButtonRelease = 5
    KeyPress = 2
    KeyRelease = 3
    RevertToParent = 1
    CurrentTime = 0
    IsViewable = 1

class XK:
    """Mock for X11 keysym handling."""
    
    @staticmethod
    def string_to_keysym(s):
        """Convert string to keysym."""
        # Mock implementation - just return the character's ascii value
        if len(s) == 1:
            return ord(s)
        return 0

class xtest:
    """Mock for Xlib.ext.xtest module."""
    
    @staticmethod
    def fake_input(display, event_type, detail, root_x=0, root_y=0, delay=0):
        """Fake input event."""
        # Mock implementation - just return True
        return True


# Factory function to create a mock setup with windows
def create_mock_display_with_windows():
    """
    Create a mock display with some test windows.
    
    Returns:
        MockDisplay: A mock display with some windows
    """
    display = MockDisplay()
    root = display.screen().root
    
    # Create some test windows
    windows = [
        MockWindow(1, "Terminal", 0, 0, 800, 600),
        MockWindow(2, "Browser", 800, 0, 800, 600),
        MockWindow(3, "Code Editor", 0, 600, 800, 600),
        MockWindow(4, "File Manager", 800, 600, 800, 600)
    ]
    
    # Add windows to display and root
    for window in windows:
        display.add_window(window)
        root.add_child(window)
    
    return display
