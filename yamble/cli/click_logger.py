"""
Click logging utilities for Compose generation results
"""

import sys
import click
from typing import List, Dict, Any
from ..core.manager import ValidationResult, ConfigType
from ..core.compose_generator import GenerationResult


class ClickLogger:
    """Click-based logger for Compose generation results"""

    def __init__(self, verbose: bool = False, quiet: bool = False):
        """
        Initialize the click logger

        Args:
            verbose: Show detailed information including warnings
            quiet: Only show errors and critical information
        """
        if verbose and quiet:
            click.echo(click.style("Cannot use both verbose and quiet options", fg="red"))
            sys.exit(1)

        self.verbose = verbose
        self.quiet = quiet

    def info(self, message: str, icon: str = "ℹ️"):
        """Log info message"""
        if not self.quiet:
            click.echo(f"{icon} {message}")

    def success(self, message: str, icon: str = "✅"):
        """Log success message"""
        if not self.quiet:
            click.echo(click.style(f"{icon} {message}", fg='green', bold=True))

    def warning(self, message: str, icon: str = "⚠️"):
        """Log warning message"""
        if not self.quiet:
            click.echo(click.style(f"{icon} {message}", fg='yellow'))

    def error(self, message: str, icon: str = "❌"):
        """Log error message"""
        click.echo(click.style(f"{icon} {message}", fg='red', bold=True))

    def debug(self, message: str, icon: str = "🔍"):
        """Log debug message (only in verbose mode)"""
        if self.verbose:
            click.echo(click.style(f"{icon} {message}", fg='blue'))

    def log_generation_start(self, templates: List[str], variables: Dict[str, Any], output_file: str):
        """Log the start of generation process"""
        if not self.quiet:
            click.echo(
                click.style("🚀 Starting Compose generation...", fg='blue', bold=True)
            )
            if self.verbose:
                click.echo(f"   Templates: {len(templates)}")
                for template in templates:
                    click.echo(f"      {template}")
                if variables:
                    self.log_parsed_variables(variables)
                click.echo(f"   Output: {output_file}")

    def log_generation_result(self, result: GenerationResult):
        """
        Log the complete generation result with appropriate formatting

        Args:
            result: GenerationResult from the generation process
        """
        if result.success:
            self._log_success(result)
        else:
            self._log_failure(result)

        # Always show errors
        if result.errors:
            self._log_errors(result.errors)

        # Show warnings if verbose or if there are errors
        if result.warnings and (self.verbose or result.errors):
            self._log_warnings(result.warnings)

        # Show detailed summary if verbose
        if self.verbose and result.success:
            self._log_detailed_summary(result)

    def log_templates(self, all_templates: Dict[str, Dict[str, Any]]):
        click.echo("\n" + "=" * 60)
        click.echo(click.style("Available Templates", bold=True, fg="blue"))
        click.echo("=" * 60)

        for display_name, template_names in all_templates.items():
            click.echo(f"\n{click.style(display_name, bold=True, fg='green')}:")
            for template_name, services in template_names.items():
                click.echo(f"  • {click.style(template_name, fg='cyan')}")
                if services:
                    services_str = ", ".join(services)
                    click.echo(
                        f"    Services: {click.style(services_str, fg='yellow')}"
                    )
                else:
                    click.echo(f"    {click.style('(No templates found)', fg='red')}")

        click.echo("=" * 60)

        # Add summary in verbose mode
        if self.verbose:
            total_templates = sum(len(templates) for templates in all_templates.values())
            total_categories = len([cat for cat, templates in all_templates.items() if templates])

            click.echo(f"\n{click.style('Summary:', fg='blue', bold=True)}")
            click.echo(f"   Categories: {total_categories}")
            click.echo(f"   Templates: {total_templates}")

    def log_configs(self, configs: ConfigType):
        if not configs:
            click.echo("No saved configurations found")
            return

        click.echo("\n" + "=" * 60)
        click.echo(click.style("Saved Configurations", bold=True, fg="blue"))
        click.echo("=" * 60)

        for config_name, config in configs.items():
            click.echo(f"\n{click.style(config_name, bold=True, fg='blue')}")

            if config:
                selected = config.get("selected_templates", {})
                if selected:
                    click.echo(click.style("  Templates:", fg='yellow'))
                    for template in selected:
                        click.echo(f"    {template}")

                # Show variables
                variables = config.get("variables", {})
                if variables:
                    variables = config.get("variables", {})
                    if variables:
                        click.echo(click.style("  Variables:", fg='yellow'))
                        self._print_variables(variables, indent=4)

        click.echo("=" * 60)

    def log_validation_errors(self, validation_result: ValidationResult, templates=[], show_available: bool = False):
        """Log validation errors with optional template listing"""
        if validation_result.missing_templates:
            for template in validation_result.missing_templates:
                self.error(f"Template not found: {template}")

        if validation_result.variable_errors:
            self.error("The following variables input have errors, please check and try again:")
            for error in validation_result.variable_errors:
                click.echo(f"   {error}")

        if validation_result.template_errors:
            for error in validation_result.template_errors:
                self.error(error)

        # Show available templates if requested and verbose
        if show_available and self.verbose and validation_result.missing_templates:
            self.debug("Available templates:")
            for template_file in templates:
                click.echo(f"   {template_file}")

    def log_parsed_variables(self, variables: Dict[str, Dict[str, Any]]):
        """Log parsed variables in verbose mode"""
        if self.verbose and variables:
            click.echo("   Variables:")
            for template, var in variables.items():
                click.echo(f"      {template}:")
                for key, value in var.items():
                    if isinstance(value, list):
                        click.echo(f"         {key}: [{', '.join(value)}]")
                    else:
                        click.echo(f"         {key}: {value}")

    def _log_success(self, result: GenerationResult):
        """Log successful generation"""
        if not self.quiet:
            # Main success message
            click.echo(
                click.style("✅ Compose file generated successfully!",
                          fg='green', bold=True)
            )

            # Basic stats
            stats_parts = []
            if result.services_count:
                stats_parts.append(f"{result.services_count} service{'s' if result.services_count != 1 else ''}")
            if result.networks_count:
                stats_parts.append(f"{result.networks_count} network{'s' if result.networks_count != 1 else ''}")
            if result.volumes_count:
                stats_parts.append(f"{result.volumes_count} volume{'s' if result.volumes_count != 1 else ''}")

            if stats_parts:
                click.echo(f"   Generated: {', '.join(stats_parts)}")

            if result.output_file:
                click.echo(f"   File: {click.style(str(result.output_file), fg='cyan')}")

    def _log_failure(self, result: GenerationResult):
        """Log failed generation"""
        click.echo(
            click.style("❌ Compose generation failed!",
                      fg='red', bold=True)
        )

        # Show template processing summary
        if result.processed_templates or result.skipped_templates:
            if result.processed_templates:
                click.echo(
                    f"   Processed: {len(result.processed_templates)} template{'s' if len(result.processed_templates) != 1 else ''}"
                )
            if result.skipped_templates:
                click.echo(
                    click.style(f"   Skipped: {len(result.skipped_templates)} template{'s' if len(result.skipped_templates) != 1 else ''}",
                              fg='yellow')
                )

    def _log_errors(self, errors: List[str]):
        """Log errors with formatting"""
        click.echo()
        click.echo(click.style("🔥 Errors:", fg='red', bold=True))
        for i, error in enumerate(errors, 1):
            # Add some smart formatting for common error types
            if "not found" in error.lower():
                icon = "📁"
            elif "yaml" in error.lower() or "parse" in error.lower():
                icon = "📄"
            elif "conflict" in error.lower() or "duplicate" in error.lower():
                icon = "⚔️"
            elif "validation" in error.lower() or "invalid" in error.lower():
                icon = "🔍"
            else:
                icon = "⚠️"

            click.echo(f"   {icon} {error}")

    def _log_warnings(self, warnings: List[str]):
        """Log warnings with formatting"""
        click.echo()
        click.echo(click.style("⚠️  Warnings:", fg='yellow', bold=True))
        for warning in warnings:
            # Add icons for different warning types
            if "overwriting" in warning.lower() or "overwrite" in warning.lower():
                icon = "🔄"
            elif "skipping" in warning.lower() or "skip" in warning.lower():
                icon = "⏭️"
            elif "merge" in warning.lower():
                icon = "🔀"
            else:
                icon = "⚠️"

            click.echo(f"   {icon} {warning}")

    def _log_detailed_summary(self, result: GenerationResult):
        """Log detailed summary for verbose mode"""
        if not result.success:
            return

        click.echo()
        click.echo(click.style("📊 Generation Summary:", fg='blue', bold=True))

        # Template processing
        if result.processed_templates:
            click.echo("   ✅ Successfully processed templates:")
            for template in result.processed_templates:
                click.echo(f"      • {template}")

        if result.skipped_templates:
            click.echo("   ⏭️  Skipped templates:")
            for template in result.skipped_templates:
                click.echo(f"      • {template}")

        # Resource counts
        if result.services_count or result.networks_count or result.volumes_count:
            click.echo("   📦 Resources created:")
            if result.services_count:
                click.echo(f"      Services: {result.services_count}")
            if result.networks_count:
                click.echo(f"      Networks: {result.networks_count}")
            if result.volumes_count:
                click.echo(f"      Volumes: {result.volumes_count}")

    def _print_variables(self, variables: dict, indent: int = 2) -> None:
        pad = " " * indent
        for key, value in variables.items():
            if isinstance(value, dict):
                click.echo(f"{pad}{key}:")
                self._print_variables(value, indent + 2)
            else:
                click.echo(f"{pad}{key}: {value}")

    def log_template_validation(self, template: str, is_valid: bool, error_msg: str = ""):
        """Log template validation results"""
        if is_valid:
            if self.verbose:
                click.echo(f"   ✅ {template} - Valid")
        else:
            click.echo(
                click.style(f"   ❌ {template} - Invalid: {error_msg}", fg='red')
            )

    def log_progress(self, current: int, total: int, template_name: str = ""):
        """Log processing progress"""
        if not self.quiet and self.verbose:
            percentage = (current / total) * 100 if total > 0 else 0
            template_info = f" ({template_name})" if template_name else ""
            click.echo(f"   Processing... {current}/{total} ({percentage:.1f}%){template_info}")


# Click command decorators and utilities
def verbose_option():
    """Click option for verbose output"""
    return click.option(
        '--verbose', '-v',
        is_flag=True,
        help='Show detailed output including warnings and progress'
    )

def quiet_option():
    """Click option for quiet output"""
    return click.option(
        '--quiet', '-q',
        is_flag=True,
        help='Only show errors and critical information'
    )

def output_option():
    """Click option for output file"""
    return click.option(
        '--output', '-o',
        default='compose.yml',
        help='Output file path (default: compose.yml)'
    )

# Utility function for on the fly results logging
def log_compose_generation(result: GenerationResult, verbose: bool = False, quiet: bool = False):
    """
    Standalone function to log generation results

    Args:
        result: GenerationResult from compose generation
        verbose: Show detailed output
        quiet: Only show critical information
    """
    logger = ClickLogger(verbose=verbose, quiet=quiet)
    logger.log_generation_result(result)


# Progress bar integration for multiple template processing
def log_with_progress_bar(templates: List[str], process_func, **kwargs):
    """
    Process templates with a click progress bar

    Args:
        templates: List of template names
        process_func: Function to process each template
        **kwargs: Additional arguments for process_func
    """
    results = []

    with click.progressbar(
        templates,
        label='Processing templates',
        item_show_func=lambda x: x if x else ''
    ) as template_bar:
        for template in template_bar:
            try:
                result = process_func(template, **kwargs)
                results.append(result)
            except Exception as e:
                click.echo(f"\nError processing {template}: {e}", err=True)
                results.append(None)

    return results
