"""
GUI interface for Compose Manager using CustomTkinter
"""

import sys
import os
import tempfile
from pathlib import Path
from typing import Dict, List, Optional
import logging

try:
    import customtkinter as ctk
    from tkinter import filedialog, messagebox, simpledialog
    import tkinter as tk
    GUI_AVAILABLE = True
except ImportError:
    GUI_AVAILABLE = False

from ..core.manager import ComposeManager
from ..core.templates import create_sample_templates

logger = logging.getLogger(__name__)

# Set appearance mode and color theme
ctk.set_appearance_mode("Dark")  # Modes: "System" (standard), "Dark", "Light"
ctk.set_default_color_theme("green")  # Themes: "blue" (standard), "green", "dark-blue"


class DockerComposeGUI:
    """GUI frontend for Compose Manager using CustomTkinter"""

    def __init__(self, templates_dir: Optional[str] = None, config_file: Optional[str] = None):
        if not GUI_AVAILABLE:
            raise ImportError("GUI not available. CustomTkinter is required for GUI mode.")

        self.manager = ComposeManager(
            templates_dir=templates_dir,
            config_file=config_file
        )

        # Create sample templates if templates directory is empty
        templates = self.manager.get_all_templates()
        if not any(templates.values()):
            create_sample_templates(self.manager.templates_dir)

        self.root = ctk.CTk()
        self.root.title("Compose Template Manager")
        self.root.geometry("1400x900")
        self.root.minsize(1000, 700)

        # Configure grid weights
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)

        self.selected_templates = {}
        self.template_vars = {}
        self.config_entries = {}

        self.setup_gui()

    def setup_gui(self) -> None:
        """Setup the main GUI interface"""
        # Create main menu
        self.setup_menu()

        # Create main frame
        main_frame = ctk.CTkFrame(self.root)
        main_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        main_frame.grid_rowconfigure(0, weight=1)
        main_frame.grid_columnconfigure(0, weight=1)
        main_frame.grid_columnconfigure(1, weight=1)

        # Left panel - Template selection
        left_frame = ctk.CTkFrame(main_frame)
        left_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 5), pady=0)

        # Right panel - Configuration and output
        right_frame = ctk.CTkFrame(main_frame)
        right_frame.grid(row=0, column=1, sticky="nsew", padx=(5, 0), pady=0)

        self.setup_left_panel(left_frame)
        self.setup_right_panel(right_frame)

        # Status bar
        self.setup_status_bar()

    def setup_menu(self) -> None:
        """Setup application menu bar using buttons"""
        menu_frame = ctk.CTkFrame(self.root, height=40)
        menu_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 10))
        menu_frame.grid_columnconfigure(6, weight=1)  # Spacer

        # File operations
        ctk.CTkButton(menu_frame, text="New Config", width=100,
                     command=self.new_configuration).grid(row=0, column=0, padx=5, pady=5)
        ctk.CTkButton(menu_frame, text="Save Config", width=100,
                     command=self.save_config).grid(row=0, column=1, padx=5, pady=5)
        ctk.CTkButton(menu_frame, text="Load Config", width=100,
                     command=self.load_config).grid(row=0, column=2, padx=5, pady=5)

        # Template operations
        ctk.CTkButton(menu_frame, text="Refresh", width=80,
                     command=self.refresh_templates).grid(row=0, column=3, padx=5, pady=5)
        ctk.CTkButton(menu_frame, text="Validate", width=80,
                     command=self.validate_templates).grid(row=0, column=4, padx=5, pady=5)
        ctk.CTkButton(menu_frame, text="Samples", width=80,
                     command=self.create_samples).grid(row=0, column=5, padx=5, pady=5)

        # About button
        ctk.CTkButton(menu_frame, text="About", width=80,
                     command=self.show_about).grid(row=0, column=7, padx=5, pady=5)

    def setup_left_panel(self, parent) -> None:
        """Setup template selection panel"""
        parent.grid_rowconfigure(1, weight=1)
        parent.grid_columnconfigure(0, weight=1)

        # Title
        title_frame = ctk.CTkFrame(parent, height=50)
        title_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        title_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(title_frame, text="Template Selection",
                    font=ctk.CTkFont(size=18, weight="bold")).grid(row=0, column=0, padx=10, pady=10)

        # Create tabview for categories
        self.template_tabview = ctk.CTkTabview(parent)
        self.template_tabview.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))

        self.template_frames = {}
        self.template_vars = {}

        self.populate_template_tabs()

        # Selection summary
        summary_frame = ctk.CTkFrame(parent, height=150)
        summary_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=(0, 10))
        summary_frame.grid_rowconfigure(1, weight=1)
        summary_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(summary_frame, text="Selection Summary",
                    font=ctk.CTkFont(size=14, weight="bold")).grid(row=0, column=0, padx=10, pady=(10, 5))

        self.selection_text = ctk.CTkTextbox(summary_frame, height=100)
        self.selection_text.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))

    def populate_template_tabs(self) -> None:
        """Populate template selection tabs"""
        # Clear existing tabs
        for tab_name in list(self.template_tabview._tab_dict.keys()):
            self.template_tabview.delete(tab_name)

        self.template_frames.clear()
        self.template_vars.clear()

        # Create tab for each category
        for category, display_name in self.manager.categories.items():
            tab = self.template_tabview.add(display_name)
            self.template_frames[category] = tab
            self.template_vars[category] = {}

            # Create scrollable frame
            scrollable_frame = ctk.CTkScrollableFrame(tab)
            scrollable_frame.pack(fill="both", expand=True, padx=10, pady=10)

            # Get templates for this category
            templates = self.manager.get_template_files(category)

            if templates:
                for template in templates:
                    # Create frame for each template
                    template_frame = ctk.CTkFrame(scrollable_frame)
                    template_frame.pack(fill="x", padx=5, pady=5)

                    var = tk.BooleanVar()
                    self.template_vars[category][template] = var

                    # Create checkbox for template
                    cb = ctk.CTkCheckBox(template_frame, text=template, variable=var,
                                       command=self.update_selection)
                    cb.pack(anchor='w', padx=10, pady=5)

                    # Show services in this template
                    services = self.manager.parse_template_services(template)
                    if services:
                        services_text = f"Services: {', '.join(services)}"
                        ctk.CTkLabel(template_frame, text=services_text,
                                   text_color="gray", font=ctk.CTkFont(size=11)).pack(anchor='w', padx=30, pady=2)
            else:
                ctk.CTkLabel(scrollable_frame, text=f"No {category} templates found",
                           text_color="red").pack(padx=10, pady=10)

    def setup_right_panel(self, parent) -> None:
        """Setup configuration and output panel"""
        parent.grid_rowconfigure(2, weight=1)
        parent.grid_columnconfigure(0, weight=1)

        # Configuration section
        config_frame = ctk.CTkFrame(parent, height=300)
        config_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        config_frame.grid_rowconfigure(1, weight=1)
        config_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(config_frame, text="Configuration Variables",
                    font=ctk.CTkFont(size=14, weight="bold")).grid(row=0, column=0, padx=10, pady=(10, 5))

        # Scrollable frame for variables
        self.config_scrollable = ctk.CTkScrollableFrame(config_frame, height=200)
        self.config_scrollable.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))

        self.setup_config_vars()

        # Output file selection
        output_frame = ctk.CTkFrame(parent, height=120)
        output_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 10))
        output_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(output_frame, text="Output Configuration",
                    font=ctk.CTkFont(size=14, weight="bold")).grid(row=0, column=0, columnspan=3, padx=10, pady=(10, 5))

        ctk.CTkLabel(output_frame, text="Output File:").grid(row=1, column=0, padx=10, pady=5, sticky="w")

        self.output_var = tk.StringVar(value="compose.yml")
        self.output_entry = ctk.CTkEntry(output_frame, textvariable=self.output_var)
        self.output_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew")

        ctk.CTkButton(output_frame, text="Browse", width=80,
                     command=self.browse_output).grid(row=1, column=2, padx=10, pady=5)

        # Action buttons
        ctk.CTkButton(output_frame, text="Generate Compose File", width=180,
                     command=self.generate_compose).grid(row=2, column=0, padx=10, pady=10)
        ctk.CTkButton(output_frame, text="Validate Templates", width=150,
                     command=self.validate_templates).grid(row=2, column=1, padx=5, pady=10, sticky="w")

        # Preview area
        preview_frame = ctk.CTkFrame(parent)
        preview_frame.grid(row=2, column=0, sticky="nsew", padx=10, pady=(0, 10))
        preview_frame.grid_rowconfigure(1, weight=1)
        preview_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(preview_frame, text="Generated Compose Preview",
                    font=ctk.CTkFont(size=14, weight="bold")).grid(row=0, column=0, padx=10, pady=(10, 5))

        self.preview_text = ctk.CTkTextbox(preview_frame, font=ctk.CTkFont(family="Consolas", size=12))
        self.preview_text.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))

    def setup_config_vars(self) -> None:
        """Setup configuration variables section"""
        # Clear existing entries
        for widget in self.config_scrollable.winfo_children():
            widget.destroy()
        self.config_entries.clear()

        # Common variables with descriptions
        common_vars = [
            ('flight_version', 'Flight container version (e.g., v2.1, latest)'),
            ('flight_mode', 'Flight mode (auto, manual, simulation)'),
            ('hatp_version', 'HATP container version'),
            ('hatp_config', 'HATP configuration file path'),
            ('mission_version', 'Mission system version'),
            ('mission_mode', 'Mission mode (planning, execution, monitoring)'),
            ('autonomy_version', 'Autonomy system version'),
            ('ai_mode', 'AI mode (learning, inference, training)'),
            ('gpu_enabled', 'Enable GPU support (true/false)'),
        ]

        self.config_scrollable.grid_columnconfigure(1, weight=1)

        for row, (var_name, description) in enumerate(common_vars):
            # Variable name label
            ctk.CTkLabel(self.config_scrollable, text=f"{var_name}:",
                        font=ctk.CTkFont(weight="bold")).grid(row=row, column=0, sticky='w', padx=5, pady=2)

            # Entry field
            entry = ctk.CTkEntry(self.config_scrollable, width=200)
            entry.grid(row=row, column=1, sticky='ew', padx=5, pady=2)
            entry.bind('<KeyRelease>', lambda e: self.update_preview())
            self.config_entries[var_name] = entry

            # Description label
            ctk.CTkLabel(self.config_scrollable, text=description,
                        text_color="gray", font=ctk.CTkFont(size=11)).grid(row=row, column=2, sticky='w', padx=5, pady=2)

    def setup_status_bar(self) -> None:
        """Setup status bar at bottom of window"""
        self.status_frame = ctk.CTkFrame(self.root, height=40)
        self.status_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=(0, 10))
        self.status_frame.grid_columnconfigure(0, weight=1)

        self.status_var = tk.StringVar()
        self.status_var.set("Ready")
        self.status_label = ctk.CTkLabel(self.status_frame, textvariable=self.status_var)
        self.status_label.grid(row=0, column=0, padx=10, pady=10, sticky="w")

        # Progress bar (initially hidden)
        self.progress = ctk.CTkProgressBar(self.status_frame, width=200)

    def update_selection(self) -> None:
        """Update selected templates and refresh displays"""
        self.selected_templates.clear()

        for category, templates in self.template_vars.items():
            selected = []
            for template, var in templates.items():
                if var.get():
                    selected.append(template)
            if selected:
                self.selected_templates[category] = selected

        self.update_selection_summary()
        self.update_preview()

    def update_selection_summary(self) -> None:
        """Update the selection summary display"""
        self.selection_text.delete("1.0", "end")

        if not self.selected_templates:
            self.selection_text.insert("1.0", "No templates selected")
            return

        total_services = 0
        summary_text = ""

        for category, templates in self.selected_templates.items():
            display_name = self.manager.categories.get(category, category)
            summary_text += f"{display_name}:\n"

            for template in templates:
                services = self.manager.parse_template_services(template)
                service_count = len(services)
                total_services += service_count

                summary_text += f"  • {template} ({service_count} services)\n"
                if services:
                    summary_text += f"    Services: {', '.join(services)}\n"

            summary_text += "\n"

        summary_text += f"Total services: {total_services}"
        self.selection_text.insert("1.0", summary_text)

    def update_preview(self) -> None:
        """Update the preview of generated compose file"""
        if not self.selected_templates:
            self.preview_text.delete("1.0", "end")
            self.preview_text.insert("1.0", "# No templates selected\n# Select templates to see preview")
            return

        try:
            # Get configuration variables
            variables = self.get_template_variables()

            # Generate preview (in memory)
            with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as tmp:
                tmp_path = tmp.name

            success = self.manager.generate_compose_file(self.selected_templates, tmp_path, variables)

            if success:
                with open(tmp_path, 'r') as f:
                    content = f.read()

                self.preview_text.delete("1.0", "end")
                self.preview_text.insert("1.0", content)

                # Clean up temp file
                os.unlink(tmp_path)
            else:
                self.preview_text.delete("1.0", "end")
                self.preview_text.insert("1.0", "# Error generating preview\n# Check template files and variables")

        except Exception as e:
            self.preview_text.delete("1.0", "end")
            self.preview_text.insert("1.0", f"# Preview Error: {str(e)}")
            logger.error(f"Preview update error: {e}")

    def get_template_variables(self) -> Dict[str, str]:
        """Get template variables from GUI inputs"""
        variables = {}
        for var_name, entry in self.config_entries.items():
            value = entry.get().strip()
            if value:
                variables[var_name] = value
        return variables

    def generate_compose(self) -> None:
        """Generate the final compose.yml file"""
        if not self.selected_templates:
            messagebox.showwarning("Warning", "No templates selected!")
            return

        output_file = self.output_var.get()
        if not output_file:
            output_file = "compose.yml"

        variables = self.get_template_variables()

        self.status_var.set("Generating compose file...")
        self.progress.grid(row=0, column=1, padx=10, pady=10, sticky="e")
        self.progress.set(0.5)
        self.root.update()

        try:
            success = self.manager.generate_compose_file(self.selected_templates, output_file, variables)

            self.progress.set(1.0)
            self.root.update()

            if success:
                total_services = sum(len(self.manager.parse_template_services(t))
                                   for templates in self.selected_templates.values()
                                   for t in templates)

                self.status_var.set(f"Successfully generated {output_file}")
                messagebox.showinfo("Success",
                                  f"Generated {output_file} successfully!\n"
                                  f"Total services: {total_services}")
            else:
                self.status_var.set("Failed to generate compose file")
                messagebox.showerror("Error", "Failed to generate compose file!")

        finally:
            self.progress.grid_remove()
            self.root.after(3000, lambda: self.status_var.set("Ready"))

    def validate_templates(self) -> None:
        """Validate selected templates"""
        if not self.selected_templates:
            messagebox.showwarning("Warning", "No templates selected!")
            return

        variables = self.get_template_variables()
        validation_results = []
        all_valid = True

        self.status_var.set("Validating templates...")
        self.root.update()

        for category, templates in self.selected_templates.items():
            for template in templates:
                is_valid, error_msg = self.manager.validate_template(template, variables)
                validation_results.append((template, is_valid, error_msg))
                if not is_valid:
                    all_valid = False

        # Show validation results
        result_window = ctk.CTkToplevel(self.root)
        result_window.title("Template Validation Results")
        result_window.geometry("700x500")
        result_window.transient(self.root)

        # Results text area
        results_text = ctk.CTkTextbox(result_window, font=ctk.CTkFont(family="Consolas", size=12))
        results_text.pack(fill='both', expand=True, padx=20, pady=20)

        results_content = "Template Validation Results\n"
        results_content += "=" * 50 + "\n\n"

        for template, is_valid, error_msg in validation_results:
            status = "✓ VALID" if is_valid else "✗ INVALID"
            results_content += f"{status}: {template}\n"
            if not is_valid:
                results_content += f"  Error: {error_msg}\n"
            results_content += "\n"

        summary = "All templates are valid!" if all_valid else "Some templates have validation errors!"
        results_content += f"\nSummary: {summary}"

        results_text.insert("1.0", results_content)

        # Close button
        ctk.CTkButton(result_window, text="Close",
                     command=result_window.destroy).pack(pady=20)

        self.status_var.set("Validation complete")
        self.root.after(3000, lambda: self.status_var.set("Ready"))

    def browse_output(self) -> None:
        """Browse for output file location"""
        filename = filedialog.asksaveasfilename(
            defaultextension=".yml",
            filetypes=[("YAML files", "*.yml"), ("YAML files", "*.yaml"), ("All files", "*.*")],
            title="Save Compose file as..."
        )
        if filename:
            self.output_var.set(filename)

    def new_configuration(self) -> None:
        """Clear current configuration"""
        # Clear template selections
        for category, templates in self.template_vars.items():
            for var in templates.values():
                var.set(False)

        # Clear variables
        for entry in self.config_entries.values():
            entry.delete(0, "end")

        # Reset output file
        self.output_var.set("compose.yml")

        self.update_selection()
        self.status_var.set("New configuration created")

    def save_config(self) -> None:
        """Save current configuration"""
        if not self.selected_templates:
            messagebox.showwarning("Warning", "No templates selected to save!")
            return

        config_name = simpledialog.askstring("Save Configuration",
                                           "Enter configuration name:",
                                           parent=self.root)
        if not config_name:
            return

        variables = self.get_template_variables()

        try:
            self.manager.save_configuration(config_name, self.selected_templates, variables)
            self.status_var.set(f"Configuration '{config_name}' saved")
            messagebox.showinfo("Success", f"Configuration '{config_name}' saved successfully!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save configuration: {str(e)}")

    def load_config(self) -> None:
        """Load a saved configuration"""
        configs = self.manager.list_configurations()
        if not configs:
            messagebox.showinfo("Info", "No saved configurations found!")
            return

        # Create selection dialog
        dialog = ctk.CTkToplevel(self.root)
        dialog.title("Load Configuration")
        dialog.geometry("500x400")
        dialog.transient(self.root)
        dialog.grab_set()

        # Center the dialog
        dialog.geometry("+%d+%d" % (self.root.winfo_rootx() + 50, self.root.winfo_rooty() + 50))

        dialog.grid_rowconfigure(1, weight=1)
        dialog.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(dialog, text="Select configuration to load:",
                    font=ctk.CTkFont(size=14, weight="bold")).grid(row=0, column=0, pady=20)

        # Scrollable frame with configurations
        scrollable_frame = ctk.CTkScrollableFrame(dialog, height=200)
        scrollable_frame.grid(row=1, column=0, sticky="nsew", padx=20, pady=10)

        # Radio buttons for configurations
        selected_config = tk.StringVar()
        config_buttons = []

        for config_name in configs:
            rb = ctk.CTkRadioButton(scrollable_frame, text=config_name,
                                   variable=selected_config, value=config_name)
            rb.pack(anchor="w", padx=10, pady=5)
            config_buttons.append(rb)

        # Details area
        details_text = ctk.CTkTextbox(dialog, height=120, font=ctk.CTkFont(family="Consolas", size=11))
        details_text.grid(row=2, column=0, sticky="ew", padx=20, pady=10)

        def on_config_select():
            config_name = selected_config.get()
            if config_name:
                config = self.manager.load_configuration(config_name)

                details_text.delete("1.0", "end")
                if config:
                    details_content = f"Configuration: {config_name}\n\n"

                    # Show selected templates
                    selected = config.get('selected_templates', {})
                    if selected:
                        details_content += "Templates:\n"
                        for category, templates in selected.items():
                            display_name = self.manager.categories.get(category, category)
                            details_content += f"  {display_name}: {', '.join(templates)}\n"

                    # Show variables
                    variables = config.get('variables', {})
                    if variables:
                        details_content += f"\nVariables ({len(variables)}):\n"
                        for key, value in list(variables.items())[:5]:  # Show first 5
                            details_content += f"  {key} = {value}\n"
                        if len(variables) > 5:
                            details_content += f"  ... and {len(variables) - 5} more\n"

                    details_text.insert("1.0", details_content)

        # Bind selection event
        for rb in config_buttons:
            rb.configure(command=on_config_select)

        def load_selected():
            config_name = selected_config.get()
            if not config_name:
                messagebox.showwarning("Warning", "Please select a configuration!")
                return

            config = self.manager.load_configuration(config_name)

            if not config:
                messagebox.showerror("Error", f"Could not load configuration '{config_name}'")
                return

            # Clear current selection
            for category, templates in self.template_vars.items():
                for var in templates.values():
                    var.set(False)

            # Load template selection
            if 'selected_templates' in config:
                for category, templates in config['selected_templates'].items():
                    if category in self.template_vars:
                        for template in templates:
                            if template in self.template_vars[category]:
                                self.template_vars[category][template].set(True)

            # Load variables
            if 'variables' in config:
                for var_name, value in config['variables'].items():
                    if var_name in self.config_entries:
                        self.config_entries[var_name].delete(0, "end")
                        self.config_entries[var_name].insert(0, value)

            self.update_selection()
            dialog.destroy()
            self.status_var.set(f"Loaded configuration: {config_name}")
            messagebox.showinfo("Success", f"Configuration '{config_name}' loaded successfully!")

        def delete_selected():
            config_name = selected_config.get()
            if not config_name:
                messagebox.showwarning("Warning", "Please select a configuration!")
                return

            if messagebox.askyesno("Confirm Delete", f"Delete configuration '{config_name}'?"):
                if self.manager.delete_configuration(config_name):
                    # Remove from dialog
                    for rb in config_buttons:
                        if rb.cget("value") == config_name:
                            rb.destroy()
                            config_buttons.remove(rb)
                            break
                    details_text.delete("1.0", "end")
                    selected_config.set("")
                    messagebox.showinfo("Success", f"Configuration '{config_name}' deleted!")
                else:
                    messagebox.showerror("Error", "Failed to delete configuration!")

        # Buttons
        button_frame = ctk.CTkFrame(dialog)
        button_frame.grid(row=3, column=0, sticky="ew", padx=20, pady=20)

        ctk.CTkButton(button_frame, text="Load", command=load_selected).pack(side='left', padx=5)
        ctk.CTkButton(button_frame, text="Delete", command=delete_selected).pack(side='left', padx=5)
        ctk.CTkButton(button_frame, text="Cancel", command=dialog.destroy).pack(side='right', padx=5)

    def refresh_templates(self) -> None:
        """Refresh template list"""
        self.populate_template_tabs()
        self.update_selection()
        self.status_var.set("Templates refreshed")
        self.root.after(2000, lambda: self.status_var.set("Ready"))

    def create_samples(self) -> None:
        """Create sample template files"""
        if messagebox.askyesno("Create Samples",
                              "Create sample template files?\n"
                              "This will create example templates in the templates directory."):
            try:
                created_count = create_sample_templates(self.manager.templates_dir, force=False)
                if created_count > 0:
                    self.refresh_templates()
                    self.status_var.set(f"Created {created_count} sample templates")
                    messagebox.showinfo("Success",
                                      f"Created {created_count} sample templates!\n"
                                      "Templates have been refreshed.")
                else:
                    messagebox.showinfo("Info",
                                      "No sample templates created.\n"
                                      "Templates may already exist.")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to create sample templates: {str(e)}")

    def show_about(self) -> None:
        """Show about dialog"""
        about_window = ctk.CTkToplevel(self.root)
        about_window.title("About")
        about_window.geometry("400x300")
        about_window.transient(self.root)
        about_window.grab_set()

        # Center the dialog
        about_window.geometry("+%d+%d" % (self.root.winfo_rootx() + 100, self.root.winfo_rooty() + 100))

        about_text = """Compose Template Manager

A CLI and GUI tool for managing Compose templates using Jinja2.

Features:
• Template-based Compose generation
• Multiple container categories (Flight, HATP, Mission System, Mission Autonomy)
• Jinja2 templating with variables
• Configuration save/load
• Template validation
• Live preview

Version: 0.1.0"""

        ctk.CTkLabel(about_window, text=about_text, justify="left",
                    font=ctk.CTkFont(size=12)).pack(padx=20, pady=20)

        ctk.CTkButton(about_window, text="Close",
                     command=about_window.destroy).pack(pady=20)

    def run(self) -> None:
        """Start the GUI application"""
        try:
            # Handle window closing
            self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

            # Start the main loop
            self.root.mainloop()
        except KeyboardInterrupt:
            logger.info("GUI application interrupted by user")
        except Exception as e:
            logger.error(f"GUI application error: {e}")
            messagebox.showerror("Error", f"Application error: {str(e)}")

    def on_closing(self) -> None:
        """Handle application closing"""
        if messagebox.askokcancel("Quit", "Do you want to quit?"):
            self.root.destroy()


def main(templates_dir: Optional[str] = None, config_file: Optional[str] = None) -> None:
    """Main entry point for GUI"""
    if not GUI_AVAILABLE:
        print("Error: GUI not available. CustomTkinter is required for GUI mode.")
        print("Please install CustomTkinter: pip install customtkinter")
        sys.exit(1)

    try:
        # Setup logging for GUI
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )

        app = DockerComposeGUI(templates_dir=templates_dir, config_file=config_file)
        app.run()

    except Exception as e:
        logger.error(f"Failed to start GUI application: {e}")
        if GUI_AVAILABLE:
            try:
                root = ctk.CTk()
                root.withdraw()  # Hide main window
                messagebox.showerror("Error", f"Failed to start application:\n{str(e)}")
                root.destroy()
            except:
                pass
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
