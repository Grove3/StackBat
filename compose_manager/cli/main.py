"""
CLI interface for Compose Manager
"""

import sys
import click
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import logging

from ..core.manager import ComposeManager
from ..core.templates import create_sample_templates

logger = logging.getLogger(__name__)


def setup_logging(verbose: bool = False) -> None:
    """Setup logging configuration"""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


@click.group(invoke_without_command=True)
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging')
@click.option('--templates-dir', '-t',
              type=click.Path(exists=False, file_okay=False, dir_okay=True, path_type=Path),
              default=Path('templates'),
              help='Directory containing template files')
@click.option('--config-file', '-c',
              type=click.Path(dir_okay=False, path_type=Path),
              default=Path('dcm_configurations.json'),
              help='Configuration file for saved configurations')
@click.pass_context
def cli(ctx, verbose: bool, templates_dir: Path, config_file: Path) -> None:
    """Compose Template Manager CLI"""
    setup_logging(verbose)

    # Store common options in context
    ctx.ensure_object(dict)
    ctx.obj['verbose'] = verbose
    ctx.obj['templates_dir'] = templates_dir
    ctx.obj['config_file'] = config_file
    ctx.obj['manager'] = ComposeManager(
        templates_dir=str(templates_dir),
        config_file=str(config_file)
    )

    # If no command is specified, show help
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


@cli.command()
@click.pass_context
def list_templates(ctx) -> None:
    """List all available templates organized by category"""
    manager: ComposeManager = ctx.obj['manager']
    templates = manager.get_all_templates()

    click.echo("\n" + "="*60)
    click.echo(click.style("Available Templates", bold=True, fg='blue'))
    click.echo("="*60)

    for category, category_templates in templates.items():
        display_name = manager.categories.get(category, category)
        click.echo(f"\n{click.style(display_name, bold=True, fg='green')}:")

        if category_templates:
            for template in category_templates:
                services = manager.parse_template_services(template)
                click.echo(f"  • {click.style(template, fg='cyan')}")
                if services:
                    services_str = ', '.join(services)
                    click.echo(f"    Services: {click.style(services_str, fg='yellow')}")
        else:
            click.echo(f"    {click.style('(No templates found)', fg='red')}")


@cli.command()
@click.option('--output', '-o', default='compose.yml',
              help='Output file path')
@click.option('--var', '-V', 'variables', multiple=True,
              help='Template variables in key=value format')
@click.option('--config', '-C', 'config_name',
              help='Use saved configuration')
@click.pass_context
def interactive(ctx, output: str, variables: Tuple[str], config_name: Optional[str]) -> None:
    """Interactive template selection and compose file generation"""
    manager: ComposeManager = ctx.obj['manager']

    # Load configuration if specified
    if config_name:
        config = manager.load_configuration(config_name)
        if not config:
            click.echo(click.style(f"Configuration '{config_name}' not found", fg='red'))
            sys.exit(1)

        selected_templates = config.get('selected_templates', {})
        template_vars = config.get('variables', {})
        click.echo(click.style(f"Loaded configuration: {config_name}", fg='green'))
    else:
        selected_templates = interactive_template_selection(manager)
        template_vars = {}

    # Parse additional variables from command line
    for var in variables:
        if '=' in var:
            key, value = var.split('=', 1)
            template_vars[key] = value
        else:
            click.echo(click.style(f"Invalid variable format: {var} (use key=value)", fg='red'))
            sys.exit(1)

    # Get additional variables interactively if none provided
    if not template_vars and not config_name:
        template_vars = get_template_variables_interactive()

    # Generate compose file
    if not selected_templates:
        click.echo(click.style("No templates selected!", fg='red'))
        sys.exit(1)

    success = manager.generate_compose_file(selected_templates, output, template_vars)

    if success:
        total_services = sum(len(manager.parse_template_services(t))
                           for templates in selected_templates.values()
                           for t in templates)
        click.echo(click.style(f"✓ Successfully generated {output}", fg='green'))
        click.echo(f"  Services included: {total_services}")

        # Ask to save configuration
        if not config_name and click.confirm("Save this configuration for future use?"):
            save_name = click.prompt("Configuration name")
            manager.save_configuration(save_name, selected_templates, template_vars)
            click.echo(click.style(f"✓ Saved configuration: {save_name}", fg='green'))
    else:
        click.echo(click.style("✗ Failed to generate compose file!", fg='red'))
        sys.exit(1)


@cli.command()
@click.option('--template', '-T', 'templates', multiple=True, required=True,
              help='Templates to use (format: category:template.yml)')
@click.option('--output', '-o', default='compose.yml',
              help='Output file path')
@click.option('--var', '-V', 'variables', multiple=True,
              help='Template variables in key=value format')
@click.option('--validate', is_flag=True,
              help='Validate templates before generation')
@click.pass_context
def generate(ctx, templates: Tuple[str], output: str, variables: Tuple[str], validate: bool) -> None:
    """Generate compose file from specified templates"""
    manager: ComposeManager = ctx.obj['manager']

    # Parse template specifications
    selected_templates = {}
    for template_spec in templates:
        if ':' not in template_spec:
            click.echo(click.style(f"Invalid template specification: {template_spec}", fg='red'))
            click.echo("Use format: category:template_file.yml")
            sys.exit(1)

        category, template_file = template_spec.split(':', 1)
        if category not in selected_templates:
            selected_templates[category] = []
        selected_templates[category].append(template_file)

    # Parse variables
    template_vars = {}
    for var in variables:
        if '=' not in var:
            click.echo(click.style(f"Invalid variable format: {var} (use key=value)", fg='red'))
            sys.exit(1)

        key, value = var.split('=', 1)
        template_vars[key] = value

    # Validate templates if requested
    if validate:
        click.echo("Validating templates...")
        all_valid = True
        for category, template_files in selected_templates.items():
            for template_file in template_files:
                is_valid, error_msg = manager.validate_template(template_file, template_vars)
                if is_valid:
                    click.echo(f"  ✓ {template_file}")
                else:
                    click.echo(f"  ✗ {template_file}: {error_msg}")
                    all_valid = False

        if not all_valid:
            click.echo(click.style("Template validation failed!", fg='red'))
            sys.exit(1)
        click.echo(click.style("All templates valid!", fg='green'))

    # Generate compose file
    success = manager.generate_compose_file(selected_templates, output, template_vars)

    if success:
        total_services = sum(len(manager.parse_template_services(t))
                           for template_files in selected_templates.values()
                           for t in template_files)
        click.echo(click.style(f"✓ Successfully generated {output}", fg='green'))
        click.echo(f"  Services included: {total_services}")
    else:
        click.echo(click.style("✗ Failed to generate compose file!", fg='red'))
        sys.exit(1)


@cli.command()
@click.pass_context
def list_configs(ctx) -> None:
    """List saved configurations"""
    manager: ComposeManager = ctx.obj['manager']
    configs = manager.list_configurations()

    if not configs:
        click.echo("No saved configurations found")
        return

    click.echo("\n" + "="*40)
    click.echo(click.style("Saved Configurations", bold=True, fg='blue'))
    click.echo("="*40)

    for config_name in configs:
        config = manager.load_configuration(config_name)
        click.echo(f"\n{click.style(config_name, bold=True, fg='cyan')}")

        if config:
            # Show selected templates
            selected = config.get('selected_templates', {})
            if selected:
                click.echo("  Templates:")
                for category, templates in selected.items():
                    display_name = manager.categories.get(category, category)
                    click.echo(f"    {display_name}: {', '.join(templates)}")

            # Show variables
            variables = config.get('variables', {})
            if variables:
                click.echo("  Variables:")
                for key, value in variables.items():
                    click.echo(f"    {key} = {value}")


@cli.command()
@click.argument('config_name')
@click.option('--output', '-o', default='compose.yml',
              help='Output file path')
@click.pass_context
def use_config(ctx, config_name: str, output: str) -> None:
    """Generate compose file using a saved configuration"""
    manager: ComposeManager = ctx.obj['manager']

    config = manager.load_configuration(config_name)
    if not config:
        click.echo(click.style(f"Configuration '{config_name}' not found", fg='red'))
        sys.exit(1)

    selected_templates = config.get('selected_templates', {})
    variables = config.get('variables', {})

    if not selected_templates:
        click.echo(click.style("Configuration has no templates selected", fg='red'))
        sys.exit(1)

    success = manager.generate_compose_file(selected_templates, output, variables)

    if success:
        click.echo(click.style(f"✓ Successfully generated {output} using config '{config_name}'", fg='green'))
    else:
        click.echo(click.style("✗ Failed to generate compose file!", fg='red'))
        sys.exit(1)


@cli.command()
@click.argument('config_name')
@click.pass_context
def delete_config(ctx, config_name: str) -> None:
    """Delete a saved configuration"""
    manager: ComposeManager = ctx.obj['manager']

    if not manager.load_configuration(config_name):
        click.echo(click.style(f"Configuration '{config_name}' not found", fg='red'))
        sys.exit(1)

    if click.confirm(f"Delete configuration '{config_name}'?"):
        if manager.delete_configuration(config_name):
            click.echo(click.style(f"✓ Deleted configuration: {config_name}", fg='green'))
        else:
            click.echo(click.style("✗ Failed to delete configuration", fg='red'))


@cli.command()
@click.option('--force', is_flag=True, help='Overwrite existing templates')
@click.pass_context
def create_samples(ctx, force: bool) -> None:
    """Create sample template files"""
    templates_dir = ctx.obj['templates_dir']

    created_count = create_sample_templates(templates_dir, force)

    if created_count > 0:
        click.echo(click.style(f"✓ Created {created_count} sample templates in {templates_dir}", fg='green'))
    else:
        click.echo("No sample templates created (files may already exist, use --force to overwrite)")


@cli.command()
@click.option('--template', '-T', 'template_file', required=True,
              help='Template file to validate')
@click.option('--var', '-V', 'variables', multiple=True,
              help='Template variables in key=value format')
@click.pass_context
def validate(ctx, template_file: str, variables: Tuple[str]) -> None:
    """Validate a template file"""
    manager: ComposeManager = ctx.obj['manager']

    # Parse variables
    template_vars = {}
    for var in variables:
        if '=' not in var:
            click.echo(click.style(f"Invalid variable format: {var} (use key=value)", fg='red'))
            sys.exit(1)

        key, value = var.split('=', 1)
        template_vars[key] = value

    is_valid, error_msg = manager.validate_template(template_file, template_vars)

    if is_valid:
        click.echo(click.style(f"✓ Template {template_file} is valid", fg='green'))

        # Show services found
        services = manager.parse_template_services(template_file)
        if services:
            click.echo(f"  Services: {', '.join(services)}")
    else:
        click.echo(click.style(f"✗ Template {template_file} is invalid:", fg='red'))
        click.echo(f"  {error_msg}")
        sys.exit(1)


def interactive_template_selection(manager: ComposeManager) -> Dict[str, List[str]]:
    """Interactive template selection interface"""
    templates = manager.get_all_templates()
    selected = {}

    click.echo("\n" + "="*60)
    click.echo(click.style("Interactive Template Selection", bold=True, fg='blue'))
    click.echo("="*60)

    for category, category_templates in templates.items():
        if not category_templates:
            continue

        display_name = manager.categories.get(category, category)
        click.echo(f"\n{click.style(display_name, bold=True, fg='green')}:")

        for i, template in enumerate(category_templates, 1):
            services = manager.parse_template_services(template)
            click.echo(f"{i:2d}. {click.style(template, fg='cyan')}")
            if services:
                services_str = ', '.join(services)
                click.echo(f"     Services: {click.style(services_str, fg='yellow')}")

        while True:
            choice = click.prompt(
                f"\nSelect templates for {display_name} (comma-separated numbers, or 'skip')",
                default='skip',
                show_default=True
            ).strip()

            if choice.lower() == 'skip':
                break

            try:
                if choice:
                    indices = [int(x.strip()) - 1 for x in choice.split(',')]
                    category_selected = [category_templates[i] for i in indices
                                       if 0 <= i < len(category_templates)]
                    if category_selected:
                        selected[category] = category_selected
                        click.echo(f"Selected: {click.style(', '.join(category_selected), fg='green')}")
                break
            except (ValueError, IndexError):
                click.echo(click.style("Invalid selection. Please try again.", fg='red'))

    return selected


def get_template_variables_interactive() -> Dict[str, str]:
    """Get template variables through interactive prompts"""
    variables = {}

    click.echo("\n" + "="*50)
    click.echo(click.style("Template Variables", bold=True, fg='blue'))
    click.echo("="*50)
    click.echo("Enter values for template variables (press Enter to skip):")

    common_vars = [
        ('flight_version', 'Flight container version'),
        ('flight_mode', 'Flight mode (auto/manual)'),
        ('hatp_version', 'HATP container version'),
        ('hatp_config', 'HATP configuration file path'),
        ('mission_version', 'Mission system version'),
        ('mission_mode', 'Mission mode (planning/execution)'),
        ('autonomy_version', 'Autonomy system version'),
        ('ai_mode', 'AI mode (learning/inference)'),
        ('gpu_enabled', 'Enable GPU support (true/false)'),
    ]

    for var_name, description in common_vars:
        value = click.prompt(f"{var_name} ({description})", default='', show_default=False)
        if value.strip():
            variables[var_name] = value.strip()

    return variables


def main() -> None:
    """Main entry point for CLI"""
    try:
        cli()
    except KeyboardInterrupt:
        click.echo("\nOperation cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        if logger.isEnabledFor(logging.DEBUG):
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
