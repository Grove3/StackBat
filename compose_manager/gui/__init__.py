"""
GUI interface for Compose Template Manager
"""

try:
    from .main import main, ComposeGUI
    __all__ = ["main", "ComposeGUI"]
except ImportError:
    # GUI not available
    __all__ = []
