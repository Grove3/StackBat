"""
Enhanced Compose file generation with improved robustness
"""

import re
import yaml
from pathlib import Path
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class MergeStrategy(Enum):
    """Strategies for handling conflicting keys during merge"""

    OVERWRITE = "overwrite"
    SKIP = "skip"
    MERGE_DEEP = "merge_deep"
    ERROR = "error"

    @classmethod
    def from_str(cls, name: str) -> "MergeStrategy":
        try:
            return cls(name)
        except ValueError:
            raise KeyError(f"Unknown merge strategy: {name}")


@dataclass
class GenerationResult:
    """Result of compose file generation"""

    success: bool
    output_file: Optional[Path] = None
    services_count: int = 0
    networks_count: int = 0
    volumes_count: int = 0
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    processed_templates: List[str] = field(default_factory=list)
    skipped_templates: List[str] = field(default_factory=list)


@dataclass
class ComposeStructure:
    """Structured representation of a Compose file"""

    services: Dict[str, Any] = field(default_factory=dict)
    networks: Dict[str, Any] = field(default_factory=dict)
    volumes: Dict[str, Any] = field(default_factory=dict)
    secrets: Dict[str, Any] = field(default_factory=dict)
    configs: Dict[str, Any] = field(default_factory=dict)
    extensions: Dict[str, Any] = field(default_factory=dict)  # x-* extensions
    version: Optional[str] = None


class ComposeGenerator:
    """
    Enhanced Compose file generator with robust error handling and validation
    """

    def __init__(
        self,
        jinja_env,
        merge_strategy: MergeStrategy = MergeStrategy.OVERWRITE,
        validate_services: bool = True,
        format_output: bool = True,
    ):
        """
        Initialize the generator

        Args:
            jinja_env: Jinja2 Environment for template rendering
            merge_strategy: How to handle conflicting keys during merge
            validate_services: Whether to validate service configurations
            format_output: Whether to format the output YAML
        """
        self.jinja_env = jinja_env
        self.merge_strategy = merge_strategy
        self.validate_services = validate_services
        self.format_output = format_output

        # Track processed items for conflict detection
        self._processed_services: Set[str] = set()
        self._processed_networks: Set[str] = set()
        self._processed_volumes: Set[str] = set()

    def generate_compose_file(
        self,
        templates: List[str],
        templates_dir: Path,
        output_file: str = "compose.yml",
        variables: Dict[int, Dict[str, Dict[str, Any]]] = {},
        merge_strategy: str = "overwrite",
    ) -> GenerationResult:
        """
        Generate Compose file from templates

        Args:
            templates: List of template file names
            templates_dir: Directory containing template files
            output_file: Output file path
            variables: Variables for template rendering
            merge_strategy: How to manage conflicting definitions

        Returns:
            GenerationResult with success status and details
        """
        variables = variables or {}
        result = GenerationResult(success=False)

        temp_merge_strategy = self.merge_strategy
        self.merge_strategy = MergeStrategy.from_str(merge_strategy)

        if not templates:
            result.errors.append("No templates provided")
            return result

        try:
            logger.info(f"Generating compose file from {len(templates)} templates")

            for i, value in enumerate(variables.values()):
                new_output_file = output_file
                if len(variables.values()) > 1:
                    array = new_output_file.split(".")
                    new_output_file = f"{array[0]}_{i + 1}.{array[1]}"

                # Initialize compose structure
                compose = ComposeStructure()

                # Reset tracking sets
                self._processed_services.clear()
                self._processed_networks.clear()
                self._processed_volumes.clear()

                # Process each template
                for template_file in templates:
                    template_vars = value.get(template_file, {})
                    template_result = self._process_template(
                        template_file, templates_dir, template_vars, compose
                    )

                    if template_result.success:
                        result.processed_templates.append(template_file)
                    else:
                        result.skipped_templates.append(template_file)
                        result.errors.extend(template_result.errors)
                        result.warnings.extend(template_result.warnings)

                # Validate final structure if enabled
                if self.validate_services:
                    validation_errors = self._validate_compose_structure(compose)
                    result.errors.extend(validation_errors)

                # Generate output if we have any services
                if not compose.services:
                    result.errors.append("No services found in processed templates")
                    return result

                # Write the compose file
                success = self._write_compose_file(compose, new_output_file)
                if success:
                    result.success = True
                    result.output_file = Path(new_output_file)
                    result.services_count = len(compose.services)
                    result.networks_count = len(compose.networks)
                    result.volumes_count = len(compose.volumes)
                    logger.info(
                        f"Successfully generated {new_output_file} with {result.services_count} services"
                    )
                else:
                    result.errors.append("Failed to write compose file")

        except Exception as e:
            logger.error(f"Unexpected error during compose generation: {e}")
            result.errors.append(f"Generation failed: {str(e)}")

        self.merge_strategy = temp_merge_strategy

        return result

    def _process_template(
        self,
        template_file: str,
        templates_dir: Path,
        variables: Dict[str, Any],
        compose: ComposeStructure,
    ) -> GenerationResult:
        """
        Process a single template file

        Args:
            template_file: Template file name
            templates_dir: Templates directory
            variables: Template variables
            compose: Compose structure to merge into

        Returns:
            GenerationResult for this template
        """
        result = GenerationResult(success=False)

        try:
            template_path = templates_dir / template_file
            if not template_path.exists():
                result.errors.append(f"Template file not found: {template_file}")
                return result

            logger.debug(f"Processing template: {template_file}")

            # Render template
            rendered_content = self._render_template(template_file, variables)
            if not rendered_content:
                result.errors.append(
                    f"Template {template_file} rendered to empty content"
                )
                return result

            # Parse YAML
            template_data = self._parse_yaml_content(rendered_content, template_file)
            if template_data is None:
                result.errors.append(f"Failed to parse YAML from {template_file}")
                return result

            template_data = self._clean_template_data(template_data)

            # Merge into main structure
            merge_result = self._merge_template_data(
                template_data, compose, template_file
            )
            result.errors.extend(merge_result.errors)
            result.warnings.extend(merge_result.warnings)

            if not merge_result.errors:
                result.success = True

        except Exception as e:
            logger.error(f"Error processing template {template_file}: {e}")
            result.errors.append(f"Template processing failed: {str(e)}")

        return result

    def _render_template(
        self, template_file: str, variables: Dict[str, Any]
    ) -> Optional[str]:
        """
        Render a Jinja2 template

        Args:
            template_file: Template file name
            variables: Template variables

        Returns:
            Rendered content or None if failed
        """
        try:
            template = self.jinja_env.get_template(template_file)
            return template.render(**variables)
        except Exception as e:
            logger.error(f"Error rendering template {template_file}: {e}")
            return None

    def _parse_yaml_content(
        self, content: str, template_file: str
    ) -> Optional[Dict[str, Any]]:
        """
        Parse YAML content with error handling

        Args:
            content: YAML content to parse
            template_file: Template file name for error reporting

        Returns:
            Parsed YAML data or None if failed
        """
        try:
            data = yaml.safe_load(content)
            if not isinstance(data, dict):
                logger.warning(
                    f"Template {template_file} did not produce a dictionary structure"
                )
                return None
            return data
        except yaml.YAMLError as e:
            logger.error(f"YAML parsing error in {template_file}: {e}")
            return None

    def _clean_template_data(self, template_data: Dict[str, Any]) -> Dict[str, Any]:
        def clean(d: Dict[str, Any]) -> Dict[str, Any]:
            cleaned = {}
            for k, v in d.items():
                if isinstance(v, dict):
                    nested = clean(v)  # recurse
                    if nested:  # only keep if not empty
                        cleaned[k] = nested
                elif isinstance(v, list):
                    nested_list = [item for item in v if item]  # remove falsy items
                    if nested_list:
                        cleaned[k] = nested_list
                elif v:  # keep if truthy
                    cleaned[k] = v
            return cleaned

        return clean(template_data)

    def _merge_template_data(
        self,
        template_data: Dict[str, Any],
        compose: ComposeStructure,
        template_file: str,
    ) -> GenerationResult:
        """
        Merge template data into the main compose structure

        Args:
            template_data: Parsed template data
            compose: Main compose structure
            template_file: Template file name for error reporting

        Returns:
            GenerationResult indicating success/failure and any issues
        """
        result = GenerationResult(success=True)

        try:
            # Merge services
            if "services" in template_data:
                self._merge_services(
                    template_data["services"], compose, template_file, result
                )

            # Merge networks
            if "networks" in template_data:
                self._merge_section(
                    template_data["networks"],
                    compose.networks,
                    self._processed_networks,
                    "networks",
                    template_file,
                    result,
                )

            # Merge volumes
            if "volumes" in template_data:
                self._merge_section(
                    template_data["volumes"],
                    compose.volumes,
                    self._processed_volumes,
                    "volumes",
                    template_file,
                    result,
                )

            # Merge other sections
            for section in ["secrets", "configs"]:
                if section in template_data:
                    target_dict = getattr(compose, section)
                    self._merge_dict_section(
                        template_data[section],
                        target_dict,
                        section,
                        template_file,
                        result,
                    )

            # Handle extensions (x-* keys)
            for key, value in template_data.items():
                if key.startswith("x-"):
                    compose.extensions[key] = value

            # Handle version (use first non-None version encountered)
            if "version" in template_data and compose.version is None:
                compose.version = template_data["version"]

        except Exception as e:
            logger.error(f"Error merging template data from {template_file}: {e}")
            result.errors.append(f"Merge failed: {str(e)}")
            result.success = False

        return result

    def _merge_services(
        self,
        services_data: Dict[str, Any],
        compose: ComposeStructure,
        template_file: str,
        result: GenerationResult,
    ):
        """Merge services with enhanced conflict handling"""
        for service_name, service_config in services_data.items():
            if service_name in self._processed_services:
                self._handle_conflict(
                    "service",
                    service_name,
                    template_file,
                    result,
                    lambda: self._merge_service_config(
                        compose.services[service_name], service_config
                    ),
                )
            else:
                # Validate service configuration
                if self.validate_services:
                    validation_errors = self._validate_service_config(
                        service_name, service_config
                    )
                    result.errors.extend(validation_errors)

                compose.services[service_name] = service_config
                self._processed_services.add(service_name)

    def _merge_section(
        self,
        section_data: Dict[str, Any],
        target_dict: Dict[str, Any],
        processed_set: Set[str],
        section_name: str,
        template_file: str,
        result: GenerationResult,
    ):
        """Generic section merger"""
        for item_name, item_config in section_data.items():
            if item_name in processed_set:
                self._handle_conflict(
                    section_name,
                    item_name,
                    template_file,
                    result,
                    lambda: target_dict.update({item_name: item_config}),
                )
            else:
                target_dict[item_name] = item_config
                processed_set.add(item_name)

    def _merge_dict_section(
        self,
        section_data: Dict[str, Any],
        target_dict: Dict[str, Any],
        section_name: str,
        template_file: str,
        result: GenerationResult,
    ):
        """Merge dictionary sections without conflict tracking"""
        for key, value in section_data.items():
            if key in target_dict:
                result.warnings.append(
                    f"Overwriting {section_name} '{key}' from template {template_file}"
                )
            target_dict[key] = value

    def _handle_conflict(
        self,
        item_type: str,
        item_name: str,
        template_file: str,
        result: GenerationResult,
        merge_action,
    ):
        """Handle conflicts based on merge strategy"""
        if self.merge_strategy == MergeStrategy.ERROR:
            result.errors.append(
                f"Conflict: {item_type} '{item_name}' already exists (from {template_file})"
            )
        elif self.merge_strategy == MergeStrategy.SKIP:
            result.warnings.append(
                f"Skipping duplicate {item_type} '{item_name}' from {template_file}"
            )
        elif self.merge_strategy == MergeStrategy.OVERWRITE:
            result.warnings.append(
                f"Overwriting {item_type} '{item_name}' from {template_file}"
            )
            merge_action()
        elif self.merge_strategy == MergeStrategy.MERGE_DEEP:
            try:
                merge_action()
                result.warnings.append(
                    f"Deep merged {item_type} '{item_name}' from {template_file}"
                )
            except Exception as e:
                result.errors.append(
                    f"Failed to deep merge {item_type} '{item_name}': {str(e)}"
                )

    def _merge_service_config(self, existing_config: Dict, new_config: Dict) -> Dict:
        """Deep merge service configurations"""
        merged = existing_config.copy()

        for key, value in new_config.items():
            if key in merged:
                if isinstance(merged[key], dict) and isinstance(value, dict):
                    merged[key] = {**merged[key], **value}
                elif isinstance(merged[key], list) and isinstance(value, list):
                    merged[key] = list(set(merged[key] + value))  # Unique merge
                else:
                    merged[key] = value  # Overwrite
            else:
                merged[key] = value

        return merged

    def _validate_service_config(
        self, service_name: str, config: Dict[str, Any]
    ) -> List[str]:
        """Validate a service configuration"""
        errors = []

        # Check required image or build
        if "image" not in config and "build" not in config:
            errors.append(
                f"Service '{service_name}' missing both 'image' and 'build' keys"
            )

        # Validate port formats
        if "ports" in config:
            for port in config["ports"]:
                if isinstance(port, str):
                    if not re.match(r"^\d+:\d+(/tcp|/udp)?$|^\d+$", port):
                        errors.append(
                            f"Service '{service_name}' has invalid port format: {port}"
                        )

        # Validate depends_on references
        if "depends_on" in config:
            depends_on = config["depends_on"]
            if isinstance(depends_on, list):
                for dep in depends_on:
                    if not isinstance(dep, str):
                        errors.append(
                            f"Service '{service_name}' has invalid depends_on format"
                        )

        return errors

    def _validate_compose_structure(self, compose: ComposeStructure) -> List[str]:
        """Validate the overall compose structure"""
        errors = []

        # Check for circular dependencies
        circular_deps = self._find_circular_dependencies(compose.services)
        if circular_deps:
            errors.append(f"Circular dependencies detected: {circular_deps}")

        # Validate network references
        for service_name, service_config in compose.services.items():
            if "networks" in service_config:
                networks = service_config["networks"]
                if isinstance(networks, list):
                    for network in networks:
                        if network not in compose.networks and network != "default":
                            errors.append(
                                f"Service '{service_name}' references undefined network '{network}'"
                            )

        return errors

    def _find_circular_dependencies(self, services: Dict[str, Any]) -> List[str]:
        """Find circular dependencies in services"""

        def has_cycle(graph, start, visited, rec_stack):
            visited[start] = True
            rec_stack[start] = True

            for neighbor in graph.get(start, []):
                if not visited.get(neighbor, False):
                    if has_cycle(graph, neighbor, visited, rec_stack):
                        return True
                elif rec_stack.get(neighbor, False):
                    return True

            rec_stack[start] = False
            return False

        # Build dependency graph
        graph = {}
        for service_name, config in services.items():
            depends_on = config.get("depends_on", [])
            if isinstance(depends_on, dict):
                depends_on = list(depends_on.keys())
            elif not isinstance(depends_on, list):
                depends_on = []
            graph[service_name] = depends_on

        visited = {}
        rec_stack = {}
        cycles = []

        for service in graph:
            if not visited.get(service, False):
                if has_cycle(graph, service, visited, rec_stack):
                    cycles.append(service)

        return cycles

    def _write_compose_file(self, compose: ComposeStructure, output_file: str) -> bool:
        """Write the compose structure to a file"""
        try:
            # Build final compose dictionary
            compose_dict = {}

            # Add version if present
            if compose.version:
                compose_dict["version"] = compose.version

            # Add extensions first
            compose_dict.update(compose.extensions)

            # Add main sections
            if compose.services:
                compose_dict["services"] = compose.services

            if compose.networks:
                compose_dict["networks"] = compose.networks

            if compose.volumes:
                compose_dict["volumes"] = compose.volumes

            if compose.secrets:
                compose_dict["secrets"] = compose.secrets

            if compose.configs:
                compose_dict["configs"] = compose.configs

            # Generate YAML
            yaml_content = self._format_yaml_output(compose_dict)

            # Write to file
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            with open(output_path, "w", encoding="utf-8") as f:
                f.write(yaml_content)

            return True

        except Exception as e:
            logger.error(f"Error writing compose file: {e}")
            return False

    def _format_yaml_output(self, compose_dict: Dict[str, Any]) -> str:
        """Format YAML output with proper spacing and structure"""
        yaml_content = yaml.dump(
            compose_dict,
            default_flow_style=False,
            indent=2,
            sort_keys=False,
            allow_unicode=True,
        )

        if not self.format_output:
            return yaml_content

        yaml_content = self._add_section_and_item_spacing(yaml_content)
        yaml_content = self._add_header(yaml_content)
        return yaml_content

    def _add_section_and_item_spacing(self, yaml_content: str) -> str:
        lines = yaml_content.split("\n")
        result_lines = []

        i = 0
        first_section = True
        first_item = True

        while i < len(lines):
            line = lines[i]

            if re.match(r"^[a-zA-Z0-9_-]+:", line):
                if not first_section:
                    line = "\n" + line
                    first_item = True
                else:
                    first_section = False

            elif re.match(r"^  [a-zA-Z0-9_-]+:", line):
                if not first_item:
                    line = "\n" + line
                else:
                    first_item = False

            result_lines.append(line)

            i += 1

        return "\n".join(result_lines)

    def _add_header(self, yaml_content: str) -> str:
        header = f"""# -------------------------------------------------------------------
#  AUTO-GENERATED FILE - DO NOT EDIT DIRECTLY
#
#  This docker compose configuration was generated by yamble.
#  Any manual changes may be overwritten the next time the file is generated.
#
#  Last generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
# -------------------------------------------------------------------
"""
        return header + "\n" + yaml_content
