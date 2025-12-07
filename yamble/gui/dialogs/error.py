"""
Error Dialog for Yamble GUI
"""

from nicegui import ui
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from ..main import YambleGUI


class ErrorDialog:
    """Error dialog for displaying error messages"""

    def __init__(self, gui: 'YambleGUI'):
        """Initialize the Error dialog"""
        self.gui = gui
        self.dialog = None
        self.error_message = None
        self.error_details = None

    def show(self, message: str, details: Optional[str] = None, title: str = "Error"):
        """
        Show an error dialog

        Args:
            message: The main error message
            details: Optional detailed error information
            title: Dialog title (default: "Error")
        """
        self.error_message = message
        self.error_details = details
        self.title = title

        with ui.dialog() as self.dialog, ui.card().classes('min-w-96 max-w-2xl dialog-content'):
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
                ui.icon('error', size='md').classes('text-red')
                ui.label(self.title).classes('text-h6 font-bold text-red')
            ui.button(
                icon='close',
                on_click=self.dialog.close
            ).props('flat round dense')

    def _create_content(self):
        """Create the main content of the dialog"""
        with ui.column().classes('gap-3 w-full'):
            # Error message
            with ui.card().classes('w-full bg-red-50 border-l-4 border-red'):
                with ui.row().classes('items-start gap-2 p-2'):
                    ui.icon('warning', size='sm').classes('text-red mt-1')
                    ui.label(self.error_message).classes('text-sm flex-grow')

            # Details (if provided)
            if self.error_details:
                with ui.expansion('Error Details', icon='info').classes('w-full'):
                    with ui.card().classes('w-full bg-grey-100'):
                        ui.label(self.error_details).classes('text-xs font-mono text-grey-8 whitespace-pre-wrap p-2')

            # Helpful tips
            with ui.column().classes('gap-2 mt-2'):
                ui.label('What to do:').classes('font-bold text-sm')
                with ui.column().classes('gap-1 ml-4'):
                    ui.label('• Check the error message above for details').classes('text-xs text-grey-7')
                    ui.label('• Verify your configuration settings').classes('text-xs text-grey-7')
                    ui.label('• Check the application logs for more information').classes('text-xs text-grey-7')
                    ui.label('• Contact support if the problem persists').classes('text-xs text-grey-7')

    def _create_footer(self):
        """Create the dialog footer"""
        with ui.row().classes('w-full justify-between items-center'):
            ui.button(
                'Copy Error',
                icon='content_copy',
                on_click=self._copy_error
            ).props('flat size=sm')
            with ui.row().classes('gap-2'):
                ui.button(
                    'Report Issue',
                    icon='bug_report',
                    on_click=lambda: ui.notify('Issue reporting coming soon!')
                ).props('flat size=sm')
                ui.button(
                    'Close',
                    on_click=self.dialog.close
                ).props('color=primary size=sm')

    def _copy_error(self):
        """Copy error message to clipboard"""
        error_text = f"Error: {self.error_message}"
        if self.error_details:
            error_text += f"\n\nDetails:\n{self.error_details}"

        # Note: Actual clipboard functionality would need JavaScript integration
        ui.notify('Error copied to clipboard!', type='positive')