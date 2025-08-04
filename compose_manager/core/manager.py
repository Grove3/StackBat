"""
Core Compose Manager functionality
"""

import os
import json
import yaml
from pathlib import Path
from typing import Dict, List, Any, Optional
from jinja2 import Environment, FileSystemLoader, Template
import logging

logger = logging.getLogger(__name__)


class ComposeManager:
    """Core class for managing Compose templates"""

    def __init__(self, templates_dir: Optional[str] = None, config_file: Optional[str] = None):
        """
        Initialize the Compose Manager

        Args:
            templates_dir: Directory containing Jinja2 templates
            config_file: Path to configuration file for saved configurations
        """
        self.templates_dir = Path(templates_dir or "templates")
        self.config_file = Path(config_file or "dcm_configurations.json")

        # Ensure templates directory exists
        self.templates_dir.mkdir(exist_ok=True)

        # Setup Jinja2 environment
        self.jinja_env = Environment(
            loader=FileSystemLoader(self.templates_dir),
            trim_blocks=True,
            lstrip_blocks=True
        )

        # Template categories
        self.categories = {
            'flight': 'Flight Containers',
            'hatp': 'HATP Containers',
            'mission_system': 'Mission System Containers',
            'mission_autonomy': 'Mission Autonomy Containers'
        }

        self.configurations = {}
        self.load_configurations()

    def load_configurations(self) -> None:
        """Load saved configurations from file"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    self.configurations = json.load(f)
                logger.info(f"Loaded {len(self.configurations)} configurations")
            except Exception as e:
                logger.error(f"Error loading configurations: {e}")
                self.configurations = {}
        else:
            logger.info("No configuration file found, starting with empty configurations")

    def save_configurations(self) -> None:
        """Save configurations to file"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.configurations, f, indent=2)
            logger.info(f"Saved {len(self.configurations)} configurations")
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
        templates = {}
        for category in self.categories.keys():
            templates[category] = self.get_template_files(category)
        return templates

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

            with open(template_path, 'r') as f:
                content = f.read()

            # Try to render template with empty context to parse structure
            try:
                template = self.jinja_env.from_string(content)
                rendered = template.render()
                data = yaml.safe_load(rendered)

                if data and 'services' in data:
                    return list(data['services'].keys())
            except Exception as e:
                logger.debug(f"Could not render template {template_file} for parsing: {e}")

            # Fallback: basic text parsing
            services = []
            lines = content.split('\n')
            in_services = False

            for line in lines:
                stripped = line.strip()
                if stripped == 'services:':
                    in_services = True
                    continue
                elif in_services and stripped and not stripped.startswith(' ') and ':' in stripped:
                    if stripped.startswith('{%') or stripped.startswith('{{'):
                        # Skip Jinja2 control structures
                        continue
                    service_name = stripped.split(':')[0].strip()
                    if service_name != 'services':
                        services.append(service_name)
                elif in_services and stripped and not stripped.startswith(' ') and not stripped.startswith('#'):
                    # End of services section
                    break

            return services

        except Exception as e:
            logger.error(f"Error parsing template {template_file}: {e}")
            return []

    def validate_template(self, template_file: str, variables: Dict[str, Any] = None) -> tuple[bool, str]:
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

    def generate_compose_file(self,
                            selected_templates: Dict[str, List[str]],
                            output_file: str = "compose.yml",
                            variables: Dict[str, Any] = None) -> bool:
        """
        Generate final compose.yml from selected templates

        Args:
            selected_templates: Dictionary mapping categories to lists of template files
            output_file: Path to output compose file
            variables: Variables for template rendering

        Returns:
            True if generation successful, False otherwise
        """
        try:
            if variables is None:
                variables = {}

            logger.info(f"Generating compose file with {sum(len(templates) for templates in selected_templates.values())} templates")

            # Start with base compose structure
            compose_data = {
                'version': '3.8',
                'services': {},
                'networks': {},
                'volumes': {}
            }

            # Process each selected template
            for category, templates in selected_templates.items():
                logger.debug(f"Processing {len(templates)} templates for category: {category}")

                for template_file in templates:
                    try:
                        template_path = self.templates_dir / template_file
                        if not template_path.exists():
                            logger.warning(f"Template file not found: {template_file}")
                            continue

                        # Render template with Jinja2
                        template = self.jinja_env.get_template(template_file)
                        rendered_content = template.render(**variables)

                        # Parse rendered YAML
                        template_data = yaml.safe_load(rendered_content)
                        if not template_data:
                            logger.warning(f"Template {template_file} rendered to empty content")
                            continue

                        # Merge services
                        if 'services' in template_data:
                            for service_name, service_config in template_data['services'].items():
                                if service_name in compose_data['services']:
                                    logger.warning(f"Service '{service_name}' already exists, overwriting")
                                compose_data['services'][service_name] = service_config

                        # Merge networks
                        if 'networks' in template_data:
                            compose_data['networks'].update(template_data['networks'])

                        # Merge volumes
                        if 'volumes' in template_data:
                            compose_data['volumes'].update(template_data['volumes'])

                        # Handle other top-level keys
                        for key, value in template_data.items():
                            if key not in ['services', 'networks', 'volumes', 'version']:
                                if key in compose_data:
                                    if isinstance(compose_data[key], dict) and isinstance(value, dict):
                                        compose_data[key].update(value)
                                    else:
                                        compose_data[key] = value
                                else:
                                    compose_data[key] = value

                        logger.debug(f"Successfully processed template: {template_file}")

                    except yaml.YAMLError as e:
                        logger.error(f"Error parsing YAML from {template_file}: {e}")
                        continue
                    except Exception as e:
                        logger.error(f"Error processing template {template_file}: {e}")
                        continue

            # Clean up empty sections
            if not compose_data['networks']:
                del compose_data['networks']
            if not compose_data['volumes']:
                del compose_data['volumes']

            # Write final compose file
            output_path = Path(output_file)
            with open(output_path, 'w') as f:
                yaml.dump(compose_data, f, default_flow_style=False, indent=2, sort_keys=False)

            service_count = len(compose_data['services'])
            logger.info(f"Successfully generated {output_file} with {service_count} services")
            return True

        except Exception as e:
            logger.error(f"Error generating compose file: {e}")
            return False

    def save_configuration(self, name: str, selected_templates: Dict[str, List[str]],
                          variables: Dict[str, str]) -> None:
        """
        Save a configuration for later use

        Args:
            name: Configuration name
            selected_templates: Selected templates by category
            variables: Template variables
        """
        config = {
            'selected_templates': selected_templates.copy(),
            'variables': variables.copy()
        }

        self.configurations[name] = config
        self.save_configurations()
        logger.info(f"Saved configuration: {name}")

    def load_configuration(self, name: str) -> Optional[Dict[str, Any]]:
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
            self.save_configurations()
            logger.info(f"Deleted configuration: {name}")
            return True
        else:
            logger.warning(f"Configuration not found for deletion: {name}")
            return False
