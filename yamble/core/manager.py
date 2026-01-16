"""
Core Compose Manager functionality
"""

import os
import yaml
import shlex
import logging
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Optional, TypedDict
from jinja2 import Environment, FileSystemLoader, meta, nodes

from yamble.core.compose_generator import ComposeGenerator, GenerationResult
from yamble.core.validator import Validator, ValidationResult


logger = logging.getLogger(__name__)


class ConfigVariables(TypedDict):
    templates: List[str]
    variables: Dict[str, Dict[str, Any]]


ConfigType = Dict[str, ConfigVariables]


class Category(TypedDict):
    display_name: str
    templates: list[str]


CategoryType = dict[str, Category]


class RootType(TypedDict):
    categories: CategoryType
    configurations: ConfigType


class ShellExecutionError(Exception):
    pass


ALLOWED_BINARIES = ["id", "whoami"]


def setup_logging(verbose: bool = False) -> None:
    """Setup logging configuration"""
    level = logging.DEBUG if verbose else logging.WARN
    logging.basicConfig(
        level=level, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    logger = logging.getLogger(__name__)
    logger.info("Logging is set to level: %s", logging.getLevelName(level))


class YambleManager:
    """Core class for managing Compose templates"""

    def __init__(
        self,
        templates_dir: Optional[str] = None,
        config_file: Optional[str] = None,
        allow_shell=False,
    ):
        """
        Initialize the Compose Manager

        Args:
            templates_dir: Directory containing Jinja2 templates
            config_file: Path to configuration file for saved configurations
            allow_shell: Allow shell command execution in templates
        """
        self.allow_shell = allow_shell

        # Initialize empty configurations (will be loaded by set_config_file)
        self.configurations: RootType = {"categories": {}, "configurations": {}}

        # Determine paths from various sources
        default_templates_dir = Path("templates")
        default_config_file = Path("dcm_configurations.yml")

        yamble_config_dir = Path.home() / ".config" / "yamble"
        templates_override_file = yamble_config_dir / "templates_location"
        config_override_file = yamble_config_dir / "configuration_location"

        templates_from_file = None
        config_from_file = None

        if templates_override_file.exists():
            try:
                with open(templates_override_file, "r") as f:
                    path = self._expand_path(f.read())
                    if path.is_dir():
                        templates_from_file = path
                    else:
                        logger.warning(
                            f"Templates path in {templates_override_file} is invalid: {path}"
                        )
            except Exception as e:
                logger.error(f"Error reading {templates_override_file}: {e}")

        if config_override_file.exists():
            try:
                with open(config_override_file, "r") as f:
                    path = self._expand_path(f.read())
                    if path.is_file():
                        config_from_file = path
                    else:
                        logger.warning(
                            f"Config path in {config_override_file} is invalid: {path}"
                        )
            except Exception as e:
                logger.error(f"Error reading {config_override_file}: {e}")

        # Determine final paths
        final_templates_dir = templates_dir or templates_from_file or default_templates_dir
        final_config_file = config_file or config_from_file or default_config_file

        self.sample_config_file = Path("sample_configurations.yml")

        # Use helper methods to initialize everything
        # Note: We need to set templates_dir first (without validation) so set_config_file works
        self.templates_dir = Path(final_templates_dir)
        self._initialize_jinja_env()

        # Initialize dependent components
        self.compose_generator = ComposeGenerator(self.jinja_env)
        self.validator = Validator(self.jinja_env, self.templates_dir)

        # Now set config file and load configurations
        self.config_file = Path(final_config_file)
        self.load_configurations()

    # ==================== Properties ====================

    @property
    def current_paths(self) -> dict[str, Path]:
        """
        Get the current templates directory and config file paths

        Returns:
            Dictionary with 'templates_dir' and 'config_file' paths
        """
        return {
            "templates_dir": self.templates_dir,
            "config_file": self.config_file,
        }

    @property
    def templates_directory(self) -> Path:
        """Get the current templates directory"""
        return self.templates_dir

    @property
    def configuration_file(self) -> Path:
        """Get the current configuration file path"""
        return self.config_file

    @property
    def all_templates(self) -> list[str]:
        """Get all available template files"""
        all_template_files = set(f.name for f in self.templates_dir.glob("*.yml.j2"))
        all_template_files.update(f.name for f in self.templates_dir.glob("*.yaml.j2"))
        return list(all_template_files)

    @property
    def category_templates(self) -> Dict[str, List[str]]:
        """
        Get all available templates organized by category

        Returns:
            Dictionary mapping category names to lists of template files
        """
        available_templates = self.all_templates.copy()
        categories = self.configurations.get("categories", {})
        category_templates = {}

        def pop_by_value(s: list, value):
            if value in s:
                s.remove(value)
                return value
            return None

        for key, value in categories.items():
            for template in value.get("templates", []):
                if template in available_templates:
                    if key in category_templates:
                        category_templates[key].append(
                            pop_by_value(available_templates, template)
                        )
                    else:
                        category_templates[key] = [
                            pop_by_value(available_templates, template)
                        ]
        if available_templates:
            category_templates["others"] = available_templates

        return category_templates

    @property
    def configuration_names(self) -> List[str]:
        """
        Get list of saved configuration names

        Returns:
            List of configuration names
        """
        return list(self.configurations["configurations"].keys())

    # ==================== Public Methods ====================

    def set_templates_dir(self, templates_dir: str | Path) -> bool:
        """
        Change the templates directory and reload the Jinja environment

        Args:
            templates_dir: New path to templates directory

        Returns:
            True if successful, False if directory doesn't exist
        """
        new_path = Path(templates_dir)

        if not new_path.exists() or not new_path.is_dir():
            logger.error(f"Templates directory does not exist: {new_path}")
            return False

        self.templates_dir = new_path

        # Reinitialize Jinja environment
        self._initialize_jinja_env()

        # Update dependent components
        self.compose_generator = ComposeGenerator(self.jinja_env)
        self.validator = Validator(self.jinja_env, self.templates_dir)

        logger.info(f"Templates directory changed to: {self.templates_dir}")
        return True

    def set_config_file(self, config_file: str | Path) -> bool:
        """
        Change the config file path and reload configurations

        Args:
            config_file: New path to config file

        Returns:
            True if successful, False otherwise
        """
        new_path = Path(config_file)

        # Config file doesn't need to exist yet (can be created on save)
        if new_path.exists() and not new_path.is_file():
            logger.error(f"Config path exists but is not a file: {new_path}")
            return False

        self.config_file = new_path

        # Reload configurations from new file
        self.configurations = {"categories": {}, "configurations": {}}
        self.load_configurations()

        logger.info(f"Config file changed to: {self.config_file}")
        return True

    def reload_templates_and_config(
        self,
        templates_dir: Optional[str | Path] = None,
        config_file: Optional[str | Path] = None
    ) -> tuple[bool, bool]:
        """
        Change both templates directory and config file, then reload

        Args:
            templates_dir: New path to templates directory (None to keep current)
            config_file: New path to config file (None to keep current)

        Returns:
            Tuple of (templates_success, config_success)
        """
        templates_success = True
        config_success = True

        if templates_dir is not None:
            templates_success = self.set_templates_dir(templates_dir)

        if config_file is not None:
            config_success = self.set_config_file(config_file)

        return templates_success, config_success

    def load_configurations(self) -> None:
        """Load saved configurations from YAML file"""
        if self.config_file.exists():
            try:
                with open(self.config_file, "r") as f:
                    self.configurations = yaml.safe_load(f)

                # Flatten lists
                configs = self.configurations.get("configurations", {})
                for key, value in configs.items():
                    flat_templates = []
                    for item in value.get("templates", []):
                        if isinstance(item, list):
                            flat_templates.extend(item)
                        else:
                            flat_templates.append(item)
                    value["templates"] = list(set(flat_templates))

                logger.info(f"Loaded {len(self.configurations)} configurations")
            except Exception as e:
                logger.error(f"Error loading configurations: {e}")
        else:
            logger.info(
                "No configuration file found, starting with empty configurations"
            )

    def save_configurations(self, configurations: RootType, location: Path) -> None:
        """Save configurations to YAML file"""
        try:
            with open(location, "w") as f:
                yaml.safe_dump(
                    self.configurations, f, indent=2, default_flow_style=False
                )
            logger.info(f"Saved {len(configurations)} configurations")
        except Exception as e:
            logger.error(f"Error saving configurations: {e}")

    def get_category_display_name(self, category):
        """Get the display name for a category"""
        categories = self.configurations.get("categories", {})
        if category in categories:
            return categories[category]["display_name"]

        return category

    def get_template_service_names(self, template_file: str) -> List[str]:
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
                    f"Could not render template {template_file}, fallback to basic text parsing. Error: {e}"
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

    def validate_templates(
        self,
        templates: List[str],
        parsed_variables: Dict[str, Dict[str, Any]],
        profiles={},
    ) -> ValidationResult:
        """
        Validate templates and variables for generation

        Args:
            templates: List of template filenames
            variables: List of variables in key=value format

        Returns:
            ValidationResult with all validation outcomes
        """
        return self.validator.validate_templates(templates, parsed_variables, profiles)

    def generate_compose_file(
        self,
        templates: List[str],
        output_file: str = "compose.yml",
        variables: Dict[int, Dict[str, Dict[str, Any]]] = {},
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

    def save_configuration(
        self,
        name: str,
        templates: List[str],
        variables: dict[str, dict[str, Any]],
    ) -> None:
        """
        Save a configuration for later use

        Args:
            name: Configuration name
            templates: Selected templates by category
            variables: Template variables
        """
        config: ConfigVariables = {
            "templates": templates.copy(),
            "variables": variables.copy(),
        }

        self.configurations["configurations"][name] = config
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
        if name in self.configurations["configurations"]:
            logger.info(f"Loaded configuration: {name}")
            return self.configurations["configurations"][name].copy()
        else:
            logger.warning(f"Configuration not found: {name}")
            return None

    def delete_configuration(self, name: str) -> bool:
        """
        Delete a saved configuration

        Args:
            name: Configuration name

        Returns:
            True if deleted, False if not found
        """
        if name in self.configurations["configurations"]:
            del self.configurations["configurations"][name]
            self.save_configurations(self.configurations, self.config_file)
            logger.info(f"Deleted configuration: {name}")
            return True
        else:
            logger.warning(f"Configuration not found for deletion: {name}")
            return False

    def get_jinja_template_vars(self, template_name: str) -> Dict[str, Any]:
        """
        Extract variables from a Jinja template

        Args:
            template_name: Name of the template file

        Returns:
            Dictionary with 'defaults' and 'required' variable lists
        """
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
                            defaults_map[var_name] = (
                                f"<dynamic:{type(default_val_node).__name__}>"
                            )
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

    # ==================== Private Methods ====================

    def _initialize_jinja_env(self) -> None:
        """Initialize or reinitialize the Jinja2 environment"""
        self.jinja_env = Environment(
            loader=FileSystemLoader(self.templates_dir),
            trim_blocks=True,
            lstrip_blocks=True,
        )

        # Inject environment variables as 'env'
        self.jinja_env.globals["env"] = os.environ

        # Inject getenv() helper
        self.jinja_env.globals["getenv"] = os.getenv

        # Inject safe shell execution helper
        self.jinja_env.globals["sh"] = self._safe_sh

    def _expand_path(self, path_str: str) -> Path:
        """Expand ~ and environment variables in a path string."""
        return Path(os.path.expandvars(os.path.expanduser(path_str.strip())))

    def _safe_sh(self, cmd):
        """Run shell commands only if explicitly allowed."""
        if not self.allow_shell:
            raise ShellExecutionError(f"Shell execution disabled. Cannot run: {cmd}")

        parts = shlex.split(cmd)
        if not parts:
            raise ShellExecutionError("Empty command")

        allowed_list = [*ALLOWED_BINARIES, *self.configurations.get("allowed_binaries", [])]

        binary = parts[0]
        if binary not in allowed_list:
            allowed = ", ".join(sorted(allowed_list))
            raise ShellExecutionError(f"Command '{binary}' not allowed. Allowed: {allowed}")

        try:
            return subprocess.check_output(parts, text=True).strip()
        except Exception as exc:
            raise ShellExecutionError(f"Error running '{cmd}': {exc}") from exc
