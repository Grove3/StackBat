"""
Yamble GUI - Main Application
"""

import sys
import logging
import argparse
from pathlib import Path
from nicegui import ui, app

from yamble.core.manager import YambleManager, setup_logging
from yamble.gui.dialogs import AboutDialog, SettingsDialog, ErrorDialog

logger = logging.getLogger(__name__)


class YambleGUI:
    """Main GUI Application Class"""

    def __init__(self, templates_dir: str = "", config_file: str = ""):
        self.templates_dir = templates_dir
        self.config_file = config_file

        # Setup static files
        self._setup_static_files()

        # Initialize manager
        try:
            self.manager = YambleManager(templates_dir, config_file)
        except Exception as e:
            logger.error(f"Failed to initialize YambleManager: {e}")
            sys.exit(1)

        # Dialogs (will be initialized in build())
        self.about_dialog = None
        self.settings_dialog = None
        self.config_dialog = None

    def _setup_static_files(self):
        """Setup static file serving"""
        static_dir = Path(__file__).parent / 'static'
        (static_dir / 'css').mkdir(parents=True, exist_ok=True)
        (static_dir / 'js').mkdir(parents=True, exist_ok=True)
        (static_dir / 'images').mkdir(parents=True, exist_ok=True)

        if static_dir.exists():
            app.add_static_files('/static', static_dir)
            logger.info(f"Static files served from: {static_dir}")

    def build(self):
        """Build the UI - called at module level"""
        self._apply_theme()
        self._create_header()
        self._create_main_content()
        self._create_footer()

        # Initialize dialogs
        self.about_dialog = AboutDialog(self)
        self.settings_dialog = SettingsDialog(self)

    def _apply_theme(self):
        """Apply custom theme and styling"""
        # Green theme instead of blue
        ui.colors(primary='#2E7D32', secondary='#66BB6A', accent='#4CAF50')
        ui.add_head_html('<link rel="stylesheet" href="/static/css/styles.css">')
        ui.add_head_html('<link rel="icon" href="data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><text y=%22.9em%22 font-size=%2290%22>⚙️</text></svg>">')

        # Load theme management script
        ui.add_head_html('<script src="/static/js/theme.js"></script>')

    def _create_header(self):
        """Create the top navigation header"""
        with ui.header().classes('items-center yamble-header'):
            with ui.row().classes('w-full items-center justify-between'):
                with ui.row().classes('items-center gap-2'):
                    ui.icon('widgets', size='lg').classes('text-white')
                    ui.label('Yamble').classes('text-h5 text-white font-bold')
                    ui.label('Docker Compose Template Manager').classes('text-white opacity-80 text-sm ml-4')

                with ui.row().classes('items-center gap-2'):
                    ui.button('Settings', on_click=self._show_settings, icon='settings').props('flat color=white')
                    ui.button('About', on_click=self._show_about, icon='info').props('flat color=white')

    def _create_main_content(self):
        """Create the main home page content"""
        with ui.column().classes('w-full items-center justify-center gap-8 mt-16'):
            ui.icon('widgets', size='xl').classes('text-primary')
            ui.label('Welcome to Yamble').classes('text-h3 text-center')
            ui.label('Docker Compose Template Manager').classes('text-subtitle1 text-grey-7 text-center')

    def _create_footer(self):
        """Create the bottom footer"""
        with ui.footer().classes('bg-grey-9'):
            with ui.row().classes('w-full items-center justify-center'):
                ui.label('Yamble © 2025').classes('text-white text-xs')

    def _show_about(self):
        """Show the About dialog"""
        if self.about_dialog:
            self.about_dialog.show()

    def _show_settings(self):
        """Show the Settings dialog"""
        if self.settings_dialog:
            self.settings_dialog.show()

# ============================================================================
# Module-level setup (runs when imported)
# ============================================================================

# Parse command line arguments
parser = argparse.ArgumentParser(description='Yamble GUI - Docker Compose Template Manager')
parser.add_argument('--templates-dir', help='Directory containing template files')
parser.add_argument('--config-file', help='Configuration file path')
parser.add_argument('--host', default='localhost', help='Host to run on')
parser.add_argument('--port', type=int, default=8080, help='Port to run on')
parser.add_argument('--reload', action='store_true', help='Enable auto-reload for development')
parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose logging')
parser.add_argument('--native', action='store_true', help='Run in native window mode')
args = parser.parse_args()

# Setup logging
setup_logging(args.verbose)

# Create and build the GUI
gui = YambleGUI(args.templates_dir, args.config_file)
gui.build()


# ============================================================================
# Run the application
# ============================================================================

if __name__ in {"__main__", "__mp_main__"}:
    if args.native:
        ui.run(
            native=True,
            window_size=(1400, 900),
            fullscreen=False,
            title='Yamble - Docker Compose Template Manager',
            favicon='⚙️'
        )
    else:
        ui.run(
            host=args.host,
            port=args.port,
            reload=args.reload,
            show=True,
            title='Yamble - Docker Compose Template Manager',
            favicon='⚙️'
        )
