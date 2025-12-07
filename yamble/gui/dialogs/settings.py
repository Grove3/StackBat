"""
Settings Dialog for Yamble GUI
"""

from pathlib import Path
from nicegui import ui
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from yamble.gui.main import YambleGUI


class SettingsDialog:
    """Settings dialog for application configuration"""

    def __init__(self, gui: 'YambleGUI'):
        """Initialize the Settings dialog"""
        self.gui = gui
        self.manager = gui.manager
        self.dialog = None
        self.dark_mode_switch = None
        self.templates_input = None
        self.config_input = None

    def show(self):
        """Show the Settings dialog"""
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
                ui.icon('settings', size='md').classes('text-primary')
                ui.label('Settings').classes('text-h6 font-bold')
            ui.button(
                icon='close',
                on_click=self.dialog.close
            ).props('flat round dense')

    def _create_content(self):
        """Create the main content of the dialog"""
        with ui.column().classes('gap-4 w-full'):
            # Templates Directory
            with ui.column().classes('gap-2 w-full'):
                ui.label('Templates Directory').classes('font-bold text-sm')
                with ui.row().classes('gap-2 w-full'):
                    self.templates_input = ui.input(
                        placeholder='/path/to/templates',
                        value=str(self.manager.templates_directory) if self.manager.templates_directory else ''
                    ).classes('flex-grow').props('outlined dense')
                    ui.button(
                        icon='folder_open',
                        on_click=lambda: self._pick_folder(self.templates_input)
                    ).props('flat')

            # Configuration File
            with ui.column().classes('w-full gap-2'):
                ui.label('Configuration File').classes('font-bold text-sm')
                with ui.row().classes('w-full gap-2'):
                    self.config_input = ui.input(
                        placeholder='/path/to/config.yml',
                        value=str(self.manager.configuration_file) if self.manager.configuration_file else ''
                    ).classes('flex-grow').props('outlined dense')
                    ui.button(
                        icon='folder_open',
                        on_click=lambda: self._pick_file(self.config_input)
                    ).props('flat')

            ui.separator()

            # Theme Settings
            with ui.column().classes('gap-2'):
                ui.label('Appearance').classes('font-bold text-sm')
                self.dark_mode_switch = ui.switch(
                    'Dark Mode',
                    value=True,  # Default to dark
                    on_change=self._toggle_theme
                )

            ui.separator()

            # Placeholder for additional settings
            with ui.column().classes('gap-2'):
                ui.label('Advanced').classes('font-bold text-sm')
                ui.checkbox('Show validation warnings', value=True)
                ui.checkbox('Enable debug logging', value=False)

    def _pick_folder(self, target_input):
        """Show folder picker dialog"""
        self._show_path_picker(target_input, pick_folders=True)

    def _pick_file(self, target_input):
        """Show file picker dialog"""
        self._show_path_picker(target_input, pick_folders=False)

    def _show_path_picker(self, target_input, pick_folders: bool = False):
        """
        Show a path picker dialog

        Args:
            target_input: The input field to update with selected path
            pick_folders: True to pick folders, False to pick files
        """
        picker_type = "folder" if pick_folders else "file"

        with ui.dialog() as picker_dialog, ui.card().classes('min-w-[600px] dialog-content'):
            current_path = Path(target_input.value) if target_input.value else Path.home()

            # Start from parent if current path is a file
            if current_path.is_file():
                current_path = current_path.parent
            elif not current_path.exists():
                current_path = Path.home()

            selected_path = {'value': None}

            with ui.column().classes('w-full gap-2'):
                # Header
                with ui.row().classes('items-center justify-between w-full'):
                    ui.label(f'Select {picker_type}').classes('text-h6 font-bold')
                    ui.button(icon='close', on_click=picker_dialog.close).props('flat round dense')

                ui.separator()

                # Path display
                path_label = ui.label(str(current_path)).classes('text-sm text-gray-600')

                # File/folder list
                list_container = ui.column().classes('w-full gap-1 max-h-96 overflow-auto')

                def update_list(path: Path):
                    """Update the file/folder list"""
                    list_container.clear()
                    path_label.set_text(str(path))

                    with list_container:
                        # Parent directory option
                        if path.parent != path:
                            with ui.row().classes('w-full items-center gap-2 p-2 hover:bg-gray-100 dark:hover:bg-gray-800 cursor-pointer rounded').on('click', lambda: update_list(path.parent)):
                                ui.icon('arrow_upward', size='sm')
                                ui.label('..').classes('flex-grow')

                        try:
                            items = sorted(path.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))

                            for item in items:
                                if item.name.startswith('.'):
                                    continue

                                is_dir = item.is_dir()

                                # Skip files if we're picking folders
                                if pick_folders and not is_dir:
                                    continue

                                with ui.row().classes('w-full items-center gap-2 p-2 hover:bg-gray-100 dark:hover:bg-gray-800 cursor-pointer rounded'):
                                    if is_dir:
                                        ui.icon('folder', size='sm').classes('text-amber-500')
                                    else:
                                        ui.icon('description', size='sm').classes('text-blue-500')

                                    label = ui.label(item.name).classes('flex-grow')

                                    if is_dir:
                                        # Double click to enter folder
                                        label.on('click', lambda i=item: update_list(i))
                                    else:
                                        # Click to select file
                                        label.on('click', lambda i=item: select_item(i))

                                    # Select button for folders when picking folders
                                    if is_dir and pick_folders:
                                        ui.button(
                                            'Select',
                                            on_click=lambda i=item: select_item(i)
                                        ).props('size=sm flat color=primary')

                        except PermissionError:
                            ui.label('Permission denied').classes('text-red-500')

                def select_item(path: Path):
                    """Select the given path"""
                    selected_path['value'] = path
                    picker_dialog.close()

                # Initial list
                update_list(current_path)

                ui.separator()

                # Footer
                with ui.row().classes('w-full justify-between items-center'):
                    # Manual path input
                    manual_input = ui.input(
                        placeholder='Or enter path manually',
                        value=str(current_path)
                    ).classes('flex-grow').props('outlined dense')

                    with ui.row().classes('gap-2'):
                        ui.button('Cancel', on_click=picker_dialog.close).props('flat')
                        ui.button(
                            'Select Current' if pick_folders else 'OK',
                            on_click=lambda: select_item(Path(manual_input.value))
                        ).props('color=primary')

        picker_dialog.on('close', lambda: self._handle_picker_result(target_input, selected_path['value']))
        picker_dialog.open()

    def _handle_picker_result(self, target_input, selected_path: Optional[Path]):
        """Handle the result from the path picker"""
        if selected_path:
            target_input.set_value(str(selected_path))
            ui.notify(f'Selected: {selected_path.name}', type='positive')

    def _toggle_theme(self, e):
        """Toggle between dark and light mode"""
        ui.run_javascript('toggleTheme()')
        theme = 'dark' if e.value else 'light'
        ui.notify(f'Switched to {theme} mode', type='positive')

    def _create_footer(self):
        """Create the dialog footer"""
        with ui.row().classes('w-full justify-end gap-2'):
            ui.button('Cancel', on_click=self.dialog.close).props('flat')
            ui.button(
                'Save',
                on_click=self._save_settings
            ).props('color=primary')

    def _save_settings(self):
        """Save settings and reload manager configuration"""
        templates_path = self.templates_input.value.strip()
        config_path = self.config_input.value.strip()

        # Check if paths have changed
        current_templates = str(self.manager.templates_directory)
        current_config = str(self.manager.configuration_file)

        templates_changed = templates_path and templates_path != current_templates
        config_changed = config_path and config_path != current_config

        if not templates_changed and not config_changed:
            ui.notify('No changes to save', type='info')
            self.dialog.close()
            return

        # Reload templates and config
        templates_success, config_success = self.manager.reload_templates_and_config(
            templates_dir=templates_path if templates_changed else None,
            config_file=config_path if config_changed else None
        )

        # Handle results
        if templates_changed and not templates_success:
            ui.notify(
                f'Failed to load templates directory: {templates_path}',
                type='negative',
                position='top'
            )
            return

        if config_changed and not config_success:
            ui.notify(
                f'Failed to load configuration file: {config_path}',
                type='negative',
                position='top'
            )
            return

        # Success - notify and refresh GUI
        success_messages = []
        if templates_success and templates_changed:
            success_messages.append('templates directory')
        if config_success and config_changed:
            success_messages.append('configuration file')

        ui.notify(
            f'Successfully updated {" and ".join(success_messages)}!',
            type='positive',
            position='top'
        )

        # Refresh GUI to reflect new templates/configs
        if hasattr(self.gui, 'refresh_templates'):
            self.gui.refresh_templates()

        self.dialog.close()
