"""
Yamble GUI Package

Run with: python -m yamble.gui.main [options]
Or use: yamble-gui [options]
"""

__version__ = '0.1.0'
__author__ = 'Stephen Grove'
__email__ = "grove_3@hotmail.com"

try:
    import nicegui
    GUI_AVAILABLE = True
except ImportError:
    GUI_AVAILABLE = False

def check_gui_availability():
    """Check if GUI dependencies are available"""
    if not GUI_AVAILABLE:
        raise ImportError(
            "GUI dependencies not available. Install with: pip install yamble[gui]"
        )
    return True

__all__ = ['check_gui_availability', 'GUI_AVAILABLE']
