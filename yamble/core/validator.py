from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
import yaml
from pathlib import Path
from jinja2 import Environment


@dataclass
class ValidationResult:
    """Result of template and variable validation"""

    success: bool = False
    templates: List[str] = field(default_factory=list)
    missing_templates: List[str] = field(default_factory=list)
    variable_errors: List[str] = field(default_factory=list)
    template_errors: List[str] = field(default_factory=list)
    # Final merged variables per profile and template
    parsed_variables: Dict[int, Dict[str, Dict[str, Any]]] = field(default_factory=dict)


class Validator:
    def __init__(self, jinja_env: Environment, templates_dir: Path):
        self.jinja_env = jinja_env
        self.templates_dir = templates_dir

    # ----------------------------
    # Public entrypoints
    # ----------------------------
    def validate_templates(
        self,
        templates: List[str],
        variables: Dict[str, Dict[str, Any]],
        profiles: Optional[Dict[str, Any]] = None,
    ) -> ValidationResult:
        """Validate multiple templates against optional profiles + variables."""
        result = ValidationResult(success=True)

        num_profiles = self._resolve_num_profiles(profiles, result)
        if result.variable_errors:
            result.success = False
            return result

        # Track template existence first
        for template_file in templates:
            template_path = self.templates_dir / template_file
            if template_path.exists():
                result.templates.append(template_file)
            else:
                result.missing_templates.append(template_file)

        # Validate templates across all profiles (or just once if no profiles)
        for i in range(num_profiles):
            result.parsed_variables[i] = {}
            for template_file in templates:
                merged_vars = self._merge_variables(
                    variables, profiles, i, template_file
                )
                result.parsed_variables[i][template_file] = merged_vars

                # Only render if template actually exists
                if template_file in result.templates:
                    ok, msg = self._render_and_check(template_file, merged_vars)
                    if not ok:
                        result.template_errors.append(
                            f"Profile {i}, Template '{template_file}': {msg}"
                        )

        result.success = (
            not result.variable_errors
            and not result.template_errors
            and not result.missing_templates
        )
        return result

    def validate_template(
        self,
        template_file: str,
        variables: Dict[str, Dict[str, Any]],
        profiles: Optional[Dict[str, Any]] = None,
    ) -> ValidationResult:
        """Validate a single template against all profiles, or once if no profiles."""
        result = ValidationResult(success=True)

        num_profiles = self._resolve_num_profiles(profiles, result)
        if result.variable_errors:
            result.success = False
            return result

        template_path = self.templates_dir / template_file
        if template_path.exists():
            result.templates.append(template_file)
        else:
            result.missing_templates.append(template_file)

        for i in range(num_profiles):
            merged_vars = self._merge_variables(variables, profiles, i, template_file)
            if i not in result.parsed_variables:
                result.parsed_variables[i] = {}
            result.parsed_variables[i][template_file] = merged_vars

            if template_file in result.templates:
                ok, msg = self._render_and_check(template_file, merged_vars)
                if not ok:
                    result.template_errors.append(
                        f"Profile {i}, Template '{template_file}': {msg}"
                    )

        result.success = (
            not result.variable_errors
            and not result.template_errors
            and not result.missing_templates
        )
        return result

    # ----------------------------
    # Helpers
    # ----------------------------
    def _resolve_num_profiles(
        self, profiles: Optional[Dict[str, Any]], result: ValidationResult
    ) -> int:
        """Determine how many profiles to iterate over. Infer if number is missing."""
        if not profiles:
            return 1

        variables = profiles.get("variables", {})
        num = profiles.get("number")

        if num is None and variables:
            # Infer from first variable list
            first_key, first_values = next(iter(variables.items()))
            if isinstance(first_values, list):
                num = len(first_values)
            else:
                result.variable_errors.append(
                    f"Cannot infer number of profiles: '{first_key}' is not a list."
                )
                return 1

        if num is None:
            result.variable_errors.append(
                "Missing 'profiles.number' and no variables to infer from."
            )
            return 1

        # Validate consistency of variable lengths
        for var_name, values in variables.items():
            if not isinstance(values, list):
                result.variable_errors.append(f"Variable '{var_name}' must be a list.")
            elif len(values) != num:
                result.variable_errors.append(
                    f"Variable '{var_name}' has {len(values)} values, expected {num}."
                )

        return num if not result.variable_errors else 1

    def _merge_variables(
        self,
        variables: Dict[str, Dict[str, Any]],
        profiles: Optional[Dict[str, Any]],
        profile_index: int,
        template_file: str,
    ) -> Dict[str, Any]:
        """Apply precedence: defaults < template_vars < profile_vars[index] (if given) < terminal (if given)."""

        # Start with defaults and template-level vars
        merged = {
            **variables.get("defaults", {}),
            **variables.get(template_file, {}),
        }

        # Overlay profile variables if profiles are defined
        if profiles:
            for var_name, values in profiles.get("variables", {}).items():
                if isinstance(values, list) and profile_index < len(values):
                    merged[var_name] = values[profile_index]

        # Finally overlay terminal variables (ultimate override)
        merged.update(variables.get("terminal", {}))

        return merged

    def _render_and_check(
        self, template_file: str, variables: Dict[str, Any]
    ) -> tuple[bool, str]:
        """Render template and check YAML validity."""
        try:
            template = self.jinja_env.get_template(template_file)
            rendered = template.render(**variables)
            yaml.safe_load(rendered)
            return True, "ok"
        except Exception as e:
            return False, str(e)
