"""
GUI interface for Compose Manager
"""

import sys
import os
import tempfile
from pathlib import Path
from typing import Dict, List, Optional
import logging

try:
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox, scrolledtext, simpledialog
    GUI_AVAILABLE = True
except ImportError:
    GUI_AVAILABLE = False

from ..core.manager import ComposeManager
from ..core.templates import create_sample_templates

logger = logging.getLogger(__name__)


class ComposeGUI:
    """GUI frontend for Compose Manager"""

    def __init__(self, templates_dir: Optional[str] = None, config_file: Optional[str] = None):
        if not GUI_AVAILABLE:
            raise ImportError("GUI not available. tkinter is required for GUI mode.")

        self.manager = ComposeManager(
            templates_dir=templates_dir,
            config_file=config_file
        )

        # Create sample templates if templates directory is empty
        templates = self.manager.get_all_templates()
        if not any(templates.values()):
            create_sample_templates(self.manager.templates_dir)

        self.root = tk.Tk()
        self.root.title("Compose Template Manager")
        self.root.geometry("1200x800")
        self.root.minsize(800, 600)

        # Configure styles
        self.setup_styles()

        self.selected_templates = {}
        self.template_vars = {}
        self.config_entries = {}

        self.setup_gui()

    def setup_styles(self) -> None:
        """Setup GUI styles and themes"""
        style = ttk.Style()

        # Configure styles for better appearance
        style.configure('Title.TLabel', font=('Arial', 12, 'bold'))
        style.configure('Heading.TLabel', font=('Arial', 10, 'bold'))
        style.configure('Success.TLabel', foreground='green')
        style.configure('Error.TLabel', foreground='red')
        style.configure('Info.TLabel', foreground='blue')

    def setup_gui(self) -> None:
        """Setup the main GUI interface"""
        # Create main menu
        self.setup_menu()

        # Create main paned window
        main_paned = ttk.PanedWindow(self.root, orient='horizontal')
        main_paned.pack(fill='both', expand=True, padx=5, pady=5)

        # Left panel - Template selection
        left_frame = ttk.Frame(main_paned)
        main_paned.add(left_frame, weight=1)

        # Right panel - Configuration and output
        right_frame = ttk.Frame(main_paned)
        main_paned.add(right_frame, weight=1)

        self.setup_left_panel(left_frame)
        self.setup_right_panel(right_frame)

        # Status bar
        self.setup_status_bar()

    def setup_menu(self) -> None:
        """Setup application menu bar"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="New Configuration", command=self.new_configuration)
        file_menu.add_separator()
        file_menu.add_command(label="Save Configuration", command=self.save_config)
        file_menu.add_command(label="Load Configuration", command=self.load_config)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)

        # Templates menu
        templates_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Templates", menu=templates_menu)
        templates_menu.add_command(label="Refresh Templates", command=self.refresh_templates)
        templates_menu.add_command(label="Create Sample Templates", command=self.create_samples)
        templates_menu.add_separator()
        templates_menu.add_command(label="Validate Selected", command=self.validate_templates)

        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self.show_about)

    def setup_left_panel(self, parent) -> None:
        """Setup template selection panel"""
        # Title
        title_frame = ttk.Frame(parent)
        title_frame.pack(fill='x', padx=5, pady=5)

        ttk.Label(title_frame, text="Template Selection", style='Title.TLabel').pack(side='left')
        ttk.Button(title_frame, text="Refresh", command=self.refresh_templates).pack(side='right')

        # Create notebook for categories
        self.template_notebook = ttk.Notebook(parent)
        self.template_notebook.pack(fill='both', expand=True, padx=5, pady=5)

        self.template_frames = {}
        self.template_vars = {}

        self.populate_template_tabs()

        # Selection summary
        summary_frame = ttk.LabelFrame(parent, text="Selection Summary")
        summary_frame.pack(fill='x', padx=5, pady=5)

        self.selection_text = tk.Text(summary_frame, height=4, wrap=tk.WORD)
        summary_scrollbar = ttk.Scrollbar(summary_frame, orient="vertical", command=self.selection_text.yview)
        self.selection_text.configure(yscrollcommand=summary_scrollbar.set)

        self.selection_text.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        summary_scrollbar.pack(side="right", fill="y")

    def populate_template_tabs(self) -> None:
        """Populate template selection tabs"""
        # Clear existing tabs
        for tab in self.template_notebook.tabs():
            self.template_notebook.forget(tab)

        self.template_frames.clear()
        self.template_vars.clear()

        # Create tab for each category
        for category, display_name in self.manager.categories.items():
            frame = ttk.Frame(self.template_notebook)
            self.template_notebook.add(frame, text=display_name)
            self.template_frames[category] = frame
            self.template_vars[category] = {}

            # Create scrollable frame
            canvas = tk.Canvas(frame)
            scrollbar = ttk.Scrollbar(frame, orient="vertical", command=canvas.yview)
            scrollable_frame = ttk.Frame(canvas)

            scrollable_frame.bind(
                "<Configure>",
                lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
            )

            canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
            canvas.configure(yscrollcommand=scrollbar.set)

            canvas.pack(side="left", fill="both", expand=True)
            scrollbar.pack(side="right", fill="y")

            # Get templates for this category
            templates = self.manager.get_template_files(category)

            if templates:
                for template in templates:
                    var = tk.BooleanVar()
                    self.template_vars[category][template] = var

                    # Create checkbutton for template
                    cb = ttk.Checkbutton(scrollable_frame, text=template, variable=var,
                                       command=self.update_selection)
                    cb.pack(anchor='w', padx=10, pady=2)

                    # Show services in this template
                    services = self.manager.parse_template_services(template)
                    if services:
                        services_text = f"Services: {', '.join(services)}"
                        ttk.Label(scrollable_frame, text=services_text,
                                foreground='gray', font=('Arial', 8)).pack(anchor='w', padx=30)
            else:
                ttk.Label(scrollable_frame, text=f"No {category} templates found",
                         foreground='red').pack(padx=10, pady=10)

    def setup_right_panel(self, parent) -> None:
        """Setup configuration and output panel"""
        # Configuration section
        config_frame = ttk.LabelFrame(parent, text="Configuration Variables")
        config_frame.pack(fill='x', padx=5, pady=5)

        # Scrollable frame for variables
        canvas = tk.Canvas(config_frame, height=200)
        scrollbar = ttk.Scrollbar(config_frame, orient="vertical", command=canvas.yview)
        self.config_vars_frame = ttk.Frame(canvas)

        self.config_vars_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=self.config_vars_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.setup_config_vars()

        # Output file selection
        output_frame = ttk.LabelFrame(parent, text="Output Configuration")
        output_frame.pack(fill='x', padx=5, pady=5)

        file_frame = ttk.Frame(output_frame)
        file_frame.pack(fill='x', padx=5, pady=5)

        ttk.Label(file_frame, text="Output File:").pack(side='left')
        self.output_var = tk.StringVar(value="compose.yml")
        ttk.Entry(file_frame, textvariable=self.output_var, width=40).pack(side='left', padx=5, fill='x', expand=True)
        ttk.Button(file_frame, text="Browse", command=self.browse_output).pack(side='left')

        # Action buttons
        button_frame = ttk.Frame(output_frame)
        button_frame.pack(fill='x', padx=5, pady=10)

        ttk.Button(button_frame, text="Generate Compose File",
                  command=self.generate_compose).pack(side='left', padx=5)
        ttk.Button(button_frame, text="Validate Templates",
                  command=self.validate_templates).pack(side='left', padx=5)

        # Preview area
        preview_frame = ttk.LabelFrame(parent, text="Generated Compose Preview")
        preview_frame.pack(fill='both', expand=True, padx=5, pady=5)

        self.preview_text = scrolledtext.ScrolledText(preview_frame, height=15, wrap=tk.NONE)
        self.preview_text.pack(fill='both', expand=True, padx=5, pady=5)

        # Add syntax highlighting (basic)
        self.preview_text.tag_configure("yaml_key", foreground="blue")
        self.preview_text.tag_configure("yaml_value", foreground="green")

    def setup_config_vars(self) -> None:
        """Setup configuration variables section"""
        # Clear existing entries
        for widget in self.config_vars_frame.winfo_children():
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

        row = 0
        for var_name, description in common_vars:
            # Variable name label
            ttk.Label(self.config_vars_frame, text=f"{var_name}:",
                     font=('Arial', 9, 'bold')).grid(row=row, column=0, sticky='w', padx=5, pady=2)

            # Entry field
            entry = ttk.Entry(self.config_vars_frame, width=25)
            entry.grid(row=row, column=1, sticky='ew', padx=5, pady=2)
            entry.bind('<KeyRelease>', lambda e: self.update_preview())
            self.config_entries[var_name] = entry

            # Description label
            ttk.Label(self.config_vars_frame, text=description,
                     foreground='gray', font=('Arial', 8)).grid(row=row, column=2, sticky='w', padx=5, pady=2)

            row += 1

        self.config_vars_frame.columnconfigure(1, weight=1)

    def setup_status_bar(self) -> None:
        """Setup status bar at bottom of window"""
        self.status_frame = ttk.Frame(self.root)
        self.status_frame.pack(side='bottom', fill='x')

        self.status_var = tk.StringVar()
        self.status_var.set("Ready")
        ttk.Label(self.status_frame, textvariable=self.status_var).pack(side='left', padx=5, pady=2)

        # Progress bar (initially hidden)
        self.progress_var = tk.DoubleVar()
        self.progress = ttk.Progressbar(self.status_frame, variable=self.progress_var, length=200)

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
        self.selection_text.delete(1.0, tk.END)

        if not self.selected_templates:
            self.selection_text.insert(tk.END, "No templates selected")
            return

        total_services = 0
        for category, templates in self.selected_templates.items():
            display_name = self.manager.categories.get(category, category)
            self.selection_text.insert(tk.END, f"{display_name}:\n")

            for template in templates:
                services = self.manager.parse_template_services(template)
                service_count = len(services)
                total_services += service_count

                self.selection_text.insert(tk.END, f"  • {template} ({service_count} services)\n")
                if services:
                    self.selection_text.insert(tk.END, f"    Services: {', '.join(services)}\n")

            self.selection_text.insert(tk.END, "\n")

        self.selection_text.insert(tk.END, f"Total services: {total_services}")

    def update_preview(self) -> None:
        """Update the preview of generated compose file"""
        if not self.selected_templates:
            self.preview_text.delete(1.0, tk.END)
            self.preview_text.insert(tk.END, "# No templates selected\n# Select templates to see preview")
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

                self.preview_text.delete(1.0, tk.END)
                self.preview_text.insert(tk.END, content)

                # Basic YAML syntax highlighting
                self.highlight_yaml()

                # Clean up temp file
                os.unlink(tmp_path)
            else:
                self.preview_text.delete(1.0, tk.END)
                self.preview_text.insert(tk.END, "# Error generating preview\n# Check template files and variables")

        except Exception as e:
            self.preview_text.delete(1.0, tk.END)
            self.preview_text.insert(tk.END, f"# Preview Error: {str(e)}")
            logger.error(f"Preview update error: {e}")

    def highlight_yaml(self) -> None:
        """Basic YAML syntax highlighting"""
        content = self.preview_text.get(1.0, tk.END)
        lines = content.split('\n')

        for i, line in enumerate(lines, 1):
            line_start = f"{i}.0"
            if ':' in line and not line.strip().startswith('#'):
                colon_pos = line.find(':')
                key_end = f"{i}.{colon_pos}"
                self.preview_text.tag_add("yaml_key", line_start, key_end)

                if colon_pos + 1 < len(line):
                    value_start = f"{i}.{colon_pos + 1}"
                    line_end = f"{i}.end"
                    self.preview_text.tag_add("yaml_value", value_start, line_end)

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
        self.progress.pack(side='right', padx=5, pady=2)
        self.progress_var.set(50)
        self.root.update()

        try:
            success = self.manager.generate_compose_file(self.selected_templates, output_file, variables)

            self.progress_var.set(100)
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
            self.progress.pack_forget()
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
        result_window = tk.Toplevel(self.root)
        result_window.title("Template Validation Results")
        result_window.geometry("600x400")
        result_window.transient(self.root)

        # Results text area
        results_text = scrolledtext.ScrolledText(result_window, height=20, width=70)
        results_text.pack(fill='both', expand=True, padx=10, pady=10)

        results_text.insert(tk.END, "Template Validation Results\n")
        results_text.insert(tk.END, "=" * 50 + "\n\n")

        for template, is_valid, error_msg in validation_results:
            status = "✓ VALID" if is_valid else "✗ INVALID"
            results_text.insert(tk.END, f"{status}: {template}\n")
            if not is_valid:
                results_text.insert(tk.END, f"  Error: {error_msg}\n")
            results_text.insert(tk.END, "\n")

        summary = "All templates are valid!" if all_valid else "Some templates have validation errors!"
        results_text.insert(tk.END, f"\nSummary: {summary}")

        # Close button
        ttk.Button(result_window, text="Close",
                  command=result_window.destroy).pack(pady=10)

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
            entry.delete(0, tk.END)

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
        dialog = tk.Toplevel(self.root)
        dialog.title("Load Configuration")
        dialog.geometry("400x300")
        dialog.transient(self.root)
        dialog.grab_set()

        # Center the dialog
        dialog.geometry("+%d+%d" % (self.root.winfo_rootx() + 50, self.root.winfo_rooty() + 50))

        ttk.Label(dialog, text="Select configuration to load:",
                 style='Heading.TLabel').pack(pady=10)

        # Listbox with configurations
        listbox_frame = ttk.Frame(dialog)
        listbox_frame.pack(fill='both', expand=True, padx=10, pady=5)

        listbox = tk.Listbox(listbox_frame)
        scrollbar = ttk.Scrollbar(listbox_frame, orient="vertical", command=listbox.yview)
        listbox.configure(yscrollcommand=scrollbar.set)

        listbox.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        for config_name in configs:
            listbox.insert(tk.END, config_name)

        # Show config details when selected
        details_text = tk.Text(dialog, height=6, wrap=tk.WORD)
        details_text.pack(fill='x', padx=10, pady=5)

        def on_select(event):
            selection = listbox.curselection()
            if selection:
                config_name = listbox.get(selection[0])
                config = self.manager.load_configuration(config_name)

                details_text.delete(1.0, tk.END)
                if config:
                    details_text.insert(tk.END, f"Configuration: {config_name}\n\n")

                    # Show selected templates
                    selected = config.get('selected_templates', {})
                    if selected:
                        details_text.insert(tk.END, "Templates:\n")
                        for category, templates in selected.items():
                            display_name = self.manager.categories.get(category, category)
                            details_text.insert(tk.END, f"  {display_name}: {', '.join(templates)}\n")

                    # Show variables
                    variables = config.get('variables', {})
                    if variables:
                        details_text.insert(tk.END, f"\nVariables ({len(variables)}):\n")
                        for key, value in list(variables.items())[:5]:  # Show first 5
                            details_text.insert(tk.END, f"  {key} = {value}\n")
                        if len(variables) > 5:
                            details_text.insert(tk.END, f"  ... and {len(variables) - 5} more\n")

        listbox.bind('<<ListboxSelect>>', on_select)

        def load_selected():
            selection = listbox.curselection()
            if not selection:
                messagebox.showwarning("Warning", "Please select a configuration!")
                return

            config_name = listbox.get(selection[0])
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
                        self.config_entries[var_name].delete(0, tk.END)
                        self.config_entries[var_name].insert(0, value)

            self.update_selection()
            dialog.destroy()
            self.status_var.set(f"Loaded configuration: {config_name}")
            messagebox.showinfo("Success", f"Configuration '{config_name}' loaded successfully!")

        def delete_selected():
            selection = listbox.curselection()
            if not selection:
                messagebox.showwarning("Warning", "Please select a configuration!")
                return

            config_name = listbox.get(selection[0])
            if messagebox.askyesno("Confirm Delete", f"Delete configuration '{config_name}'?"):
                if self.manager.delete_configuration(config_name):
                    listbox.delete(selection[0])
                    details_text.delete(1.0, tk.END)
                    messagebox.showinfo("Success", f"Configuration '{config_name}' deleted!")
                else:
                    messagebox.showerror("Error", "Failed to delete configuration!")

        # Buttons
        button_frame = ttk.Frame(dialog)
        button_frame.pack(fill='x', padx=10, pady=10)

        ttk.Button(button_frame, text="Load", command=load_selected).pack(side='left', padx=5)
        ttk.Button(button_frame, text="Delete", command=delete_selected).pack(side='left', padx=5)
        ttk.Button(button_frame, text="Cancel", command=dialog.destroy).pack(side='right', padx=5)

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
        about_text = """Compose Template Manager

A CLI and GUI tool for managing Compose templates using Jinja2.

Features:
• Template-based Compose generation
• Multiple container categories (Flight, HATP, Mission System, Mission Autonomy)
• Jinja2 templating with variables
• Configuration save/load
• Template validation
• Live preview

Version: 0.1.0
"""
        messagebox.showinfo("About", about_text)

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
        print("Error: GUI not available. tkinter is required for GUI mode.")
        print("Please install tkinter or use the CLI interface.")
        sys.exit(1)

    try:
        # Setup logging for GUI
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )

        app = ComposeGUI(templates_dir=templates_dir, config_file=config_file)
        app.run()

    except Exception as e:
        logger.error(f"Failed to start GUI application: {e}")
        if GUI_AVAILABLE:
            try:
                root = tk.Tk()
                root.withdraw()  # Hide main window
                messagebox.showerror("Error", f"Failed to start application:\n{str(e)}")
                root.destroy()
            except:
                pass
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
