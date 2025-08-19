"""
Core Compose Manager functionality
"""

import yaml
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from jinja2 import Environment, FileSystemLoader, meta, nodes
from dataclasses import dataclass, field

from ..core.compose_generator import ComposeGenerator, GenerationResult
from ..core.templates import (
    ConfigType,
    ConfigVariables
)

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of template and variable validation"""

    success: bool = False
    missing_templates: List[str] = field(default_factory=list)
    variable_errors: List[str] = field(default_factory=list)
    template_errors: List[str] = field(default_factory=list)
    parsed_variables: Dict[str, Dict[str, Any]] = field(default_factory=dict)


class ComposeManager:
    """Core class for managing Compose templates"""

    def __init__(
        self, templates_dir: Optional[str] = None, config_file: Optional[str] = None
    ):
        """
        Initialize the Compose Manager

        Args:
            templates_dir: Directory containing Jinja2 templates
            config_file: Path to configuration file for saved configurations
        """
        self.templates_dir = Path(templates_dir or "templates")
        self.config_file = Path(config_file or "dcm_configurations.yml")
        self.sample_config_file = Path("sample_configuration.yml")

        # Ensure templates directory exists
        self.templates_dir.mkdir(exist_ok=True)

        # Setup Jinja2 environment
        self.jinja_env = Environment(
            loader=FileSystemLoader(self.templates_dir),
            trim_blocks=True,
            lstrip_blocks=True,
        )

        # Template categories
        self.categories = {
            # 'flight': 'Flight Containers',
            # 'hatp': 'HATP Containers',
            # 'mission_system': 'Mission System Containers',
            # 'mission_autonomy': 'Mission Autonomy Containers'
        }

        self.compose_generator = ComposeGenerator(
            self.jinja_env,
        )

        self.configurations: ConfigType = {}
        self.load_configurations()

    def load_configurations(self) -> None:
        """Load saved configurations from YAML file"""
        if self.config_file.exists():
            try:
                with open(self.config_file, "r") as f:
                    self.configurations = yaml.safe_load(f)

                logger.info(f"Loaded {len(self.configurations)} configurations")
            except Exception as e:
                logger.error(f"Error loading configurations: {e}")
                self.configurations = {}
        else:
            logger.info(
                "No configuration file found, starting with empty configurations"
            )

    def save_configurations(self, configurations: ConfigType, location: Path) -> None:
        """Save configurations to YAML file"""
        try:
            with open(location, "w") as f:
                yaml.safe_dump(
                    self.configurations, f, indent=2, default_flow_style=False
                )
            logger.info(f"Saved {len(configurations)} configurations")
        except Exception as e:
            logger.error(f"Error saving configurations: {e}")

    def get_template_files(self, category: str) -> List[str]:
        """
        Get available template files for a category

        Args:
            category: Template category name

        Returns:
            List of template filenames for the category
        """
        patterns = [f"{category}*.yml.j2", f"{category}*.yaml.j2"]
        template_files = []

        for pattern in patterns:
            template_files.extend(self.templates_dir.glob(pattern))

        return [f.name for f in template_files]

    def get_all_templates(self) -> Dict[str, List[str]]:
        """
        Get all available templates organized by category

        Returns:
            Dictionary mapping category names to lists of template files
        """
        all_keys = []

        for item in self.configurations.values():
            selected = item.get("selected_templates", {})
            all_keys.extend(selected.keys())

        # Remove duplicates
        categories = list(set(all_keys))

        templates = {
            category: temps
            for category in categories
            if (temps := self.get_template_files(category))
        }

        # Handle miscellaneous category
        all_template_files = self.get_templates_simple()

        categorized_files = set()
        for file_list in templates.values():
            categorized_files.update(file_list)

        uncategorized_files = list(all_template_files - categorized_files)
        if uncategorized_files:
            templates["others"] = uncategorized_files

        return templates

    def get_templates_simple(self) -> set[str]:
        all_template_files = set(f.name for f in self.templates_dir.glob("*.yml.j2"))
        all_template_files.update(f.name for f in self.templates_dir.glob("*.yaml.j2"))
        return all_template_files

    def parse_template_services(self, template_file: str) -> List[str]:
        """
        Parse a template file to extract service names

        Args:
            template_file: Name of template file to parse

        Returns:
            List of service names found in the template
        """
        try:
            template_path = self.templates_dir / template_file
            if not template_path.exists():
                logger.warning(f"Template file not found: {template_file}")
                return []

            with open(template_path, "r") as f:
                content = f.read()

            # Try to render template with empty context to parse structure
            try:
                template = self.jinja_env.from_string(content)
                rendered = template.render()
                data = yaml.safe_load(rendered)

                if data and "services" in data:
                    return list(data["services"].keys())
            except Exception as e:
                logger.debug(
                    f"Could not render template {template_file} for parsing: {e}"
                )

            # Fallback: basic text parsing
            services = []
            lines = content.split("\n")
            in_services = False

            for line in lines:
                # Skip Jinja control structures
                if line.strip().startswith("{%") or line.strip().startswith("{{"):
                    continue

                if not in_services:
                    if line.strip() == "services:":
                        in_services = True
                    continue

                # Stop collecting if we reach a line that is not indented or starts a new top-level section
                if in_services:
                    if line.startswith(" ") or line.startswith("\t"):
                        # Count indentation
                        indent_level = len(line) - len(line.lstrip())
                        if indent_level == 2 and ":" in line:
                            key = line.strip().split(":")[0]
                            services.append(key)
                    else:
                        # We've reached a new section or end of 'services'
                        break

            return services

        except Exception as e:
            logger.error(f"Error parsing template {template_file}: {e}")
            return []

    def validate_template(
        self, template_file: str, variables: Dict[str, Any] = {}
    ) -> tuple[bool, str]:
        """
        Validate a template file

        Args:
            template_file: Name of template file to validate
            variables: Variables to use for template rendering

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            template_path = self.templates_dir / template_file
            if not template_path.exists():
                return False, f"Template file not found: {template_file}"

            # Try to load and render template
            template = self.jinja_env.get_template(template_file)
            rendered_content = template.render(**(variables or {}))

            # Try to parse as YAML
            yaml.safe_load(rendered_content)

            return True, "Template is valid"

        except Exception as e:
            return False, f"Template validation failed: {str(e)}"

    def validate_templates(
        self, templates: List[str], parsed_variables: Dict[str, Dict[str, Any]]
    ) -> ValidationResult:
        """
        Validate templates and variables for generation

        Args:
            templates: List of template filenames
            variables: List of variables in key=value format

        Returns:
            ValidationResult with all validation outcomes
        """
        result = ValidationResult(success=True)

        # Get available templates
        templates_dict = self.get_all_templates()
        all_templates = [
            item for sublist in templates_dict.values() for item in sublist
        ]

        # Check template availability
        for template_file in templates:
            if template_file not in all_templates:
                result.missing_templates.append(template_file)

        # Validate template content
        self._validate_template_content(templates, parsed_variables, result)

        # Set overall success
        result.success = (
            not result.missing_templates
            and not result.variable_errors
            and not result.template_errors
        )

        return result

    def _validate_template_content(
        self,
        templates: List[str],
        variables: Dict[str, Dict[str, Any]],
        result: ValidationResult,
    ) -> None:
        """Validate template content"""
        for template_file in templates:
            template_vars = {
                **variables.get(template_file, {}),
                **variables.get("defaults", {}),
            }
            is_valid, error_msg = self.validate_template(template_file, template_vars)
            if not is_valid:
                result.template_errors.append(
                    f"Template '{template_file}': {error_msg}"
                )

    def generate_compose_file(
        self,
        templates: List[str],
        output_file: str = "compose.yml",
        variables: Dict[str, Dict[str, Any]] = {},
        merge_strategy: str = "overwrite",
    ) -> GenerationResult:
        """
        Generate final compose.yml from selected templates

        Args:
            templates: List of template files
            output_file: Path to output compose file
            variables: Variables for template rendering
            merge_strategy: How to manage conflicting definitions

        Returns:
            True if generation successful, False otherwise
        """
        return self.compose_generator.generate_compose_file(
            templates, self.templates_dir, output_file, variables, merge_strategy
        )

    def get_configuration_names(self) -> List[str]:
        return list(self.configurations.keys())

    def save_configuration(
        self,
        name: str,
        selected_templates: dict[str, dict[str, Any]],
        variables: dict[str, dict[str, Any]],
    ) -> None:
        """
        Save a configuration for later use

        Args:
            name: Configuration name
            selected_templates: Selected templates by category
            variables: Template variables
        """
        config: ConfigVariables = {
            "selected_templates": selected_templates.copy(),
            "variables": variables.copy(),
        }

        self.configurations[name] = config
        self.save_configurations(self.configurations, self.config_file)
        logger.info(f"Saved configuration: {name}")

    def load_configuration(self, name: str) -> ConfigVariables | None:
        """
        Load a saved configuration

        Args:
            name: Configuration name

        Returns:
            Configuration dictionary or None if not found
        """
        if name in self.configurations:
            logger.info(f"Loaded configuration: {name}")
            return self.configurations[name].copy()
        else:
            logger.warning(f"Configuration not found: {name}")
            return None

    def list_configurations(self) -> List[str]:
        """
        Get list of saved configuration names

        Returns:
            List of configuration names
        """
        return list(self.configurations.keys())

    def delete_configuration(self, name: str) -> bool:
        """
        Delete a saved configuration

        Args:
            name: Configuration name

        Returns:
            True if deleted, False if not found
        """
        if name in self.configurations:
            del self.configurations[name]
            self.save_configurations(self.configurations, self.config_file)
            logger.info(f"Deleted configuration: {name}")
            return True
        else:
            logger.warning(f"Configuration not found for deletion: {name}")
            return False

    def get_jinja_template_vars(self, template_name: str) -> Dict[str, Any]:
        # Load template source
        source, _, _ = self.jinja_env.loader.get_source(self.jinja_env, template_name)

        parsed_content = self.jinja_env.parse(source)

        defaults_map = {}

        def walk(node):
            if isinstance(node, nodes.Filter) and node.name == "default":
                # The thing being filtered should be a Name node
                if isinstance(node.node, nodes.Name):
                    var_name = node.node.name
                    if node.args:  # Default filter has an argument
                        default_val_node = node.args[0]
                        if isinstance(default_val_node, nodes.Const):
                            defaults_map[var_name] = default_val_node.value
                        else:
                            defaults_map[var_name] = f"<dynamic:{type(default_val_node).__name__}>"
            # Recursively walk child nodes
            for field_name in node.fields:
                child = getattr(node, field_name)
                if isinstance(child, list):
                    for item in child:
                        if isinstance(item, nodes.Node):
                            walk(item)
                elif isinstance(child, nodes.Node):
                    walk(child)

        walk(parsed_content)

        all_vars = meta.find_undeclared_variables(parsed_content)
        required = [var for var in all_vars if var not in defaults_map.keys()]

        final_map = {"defaults": defaults_map, "required": required}
        return final_map
