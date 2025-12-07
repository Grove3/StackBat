"""
About Dialog for Yamble GUI
"""

from nicegui import ui
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from yamble.gui.main import YambleGUI


class AboutDialog:
    """About dialog showing application information"""

    def __init__(self, gui: 'YambleGUI'):
        """Initialize the About dialog"""
        self.gui = gui
        self.dialog = None

    def show(self):
        """Show the About dialog"""
        with ui.dialog() as self.dialog, ui.card().classes('min-w-96 dialog-content'):
            with ui.column().classes('gap-4 w-full'):
                # Header
                self._create_header()

                ui.separator()

                # Content
                self._create_content()

                # Footer
                ui.separator()
                self._create_footer()

        self.dialog.open()

    def _create_header(self):
        """Create the dialog header"""
        with ui.row().classes('items-center justify-between w-full'):
            with ui.row().classes('items-center gap-2'):
                ui.icon('widgets', size='md').classes('text-primary')
                ui.label('About Yamble').classes('text-h6 font-bold')
            ui.button(
                icon='close',
                on_click=self.dialog.close
            ).props('flat round dense')

    def _create_content(self):
        """Create the main content of the dialog"""
        with ui.column().classes('gap-3'):
            # Title and version
            self._create_title_section()

            ui.separator().classes('my-2')

            # Description
            self._create_description_section()

            ui.separator().classes('my-2')

            # Author info
            self._create_author_section()

            ui.separator().classes('my-2')

            # Features
            self._create_features_section()

    def _create_title_section(self):
        """Create the title and version section"""
        with ui.column().classes('gap-1'):
            ui.label('Yamble Docker Compose Template Manager').classes('font-bold text-lg')
            with ui.row().classes('items-center gap-2'):
                ui.badge('v0.1.0', color='primary')
                ui.badge('Beta', color='orange')

    def _create_description_section(self):
        """Create the description section"""
        with ui.column().classes('gap-2'):
            ui.label('Description:').classes('font-bold text-sm text-grey-8')
            ui.label(
                'A powerful and flexible template manager for Docker Compose configurations. '
                'Yamble allows you to create, manage, and deploy containerized applications '
                'using customizable templates with variable substitution.'
            ).classes('text-sm text-grey-7')

    def _create_author_section(self):
        """Create the author information section"""
        with ui.column().classes('gap-2'):
            ui.label('Author:').classes('font-bold text-sm text-grey-8')
            with ui.row().classes('items-center gap-2'):
                ui.icon('person', size='sm').classes('text-grey-6')
                ui.label('Stephen Grove').classes('text-sm')
            with ui.row().classes('items-center gap-2'):
                ui.icon('email', size='sm').classes('text-grey-6')
                ui.link(
                    'grove_3@hotmail.com',
                    'mailto:grove_3@hotmail.com'
                ).classes('text-sm')

    def _create_features_section(self):
        """Create the features list section"""
        features = [
            'Template-based Docker Compose management',
            'Variable substitution and validation',
            'Configuration presets',
            'Easy deployment workflow'
        ]

        with ui.column().classes('gap-2'):
            ui.label('Features:').classes('font-bold text-sm text-grey-8')
            with ui.column().classes('gap-1 ml-4'):
                for feature in features:
                    with ui.row().classes('items-start gap-2'):
                        ui.icon('check_circle', size='sm').classes('text-green')
                        ui.label(feature).classes('text-sm')

    def _create_footer(self):
        """Create the dialog footer"""
        with ui.row().classes('w-full justify-between items-center'):
            ui.label('© 2025 Yamble').classes('text-xs text-grey-6')
            with ui.row().classes('gap-2'):
                ui.button(
                    'Documentation',
                    icon='book',
                    on_click=lambda: ui.notify('Documentation coming soon!')
                ).props('flat size=sm')
                ui.button(
                    'Close',
                    on_click=self.dialog.close
                ).props('flat size=sm color=primary')