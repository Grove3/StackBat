"""
CLI interface for Compose Manager
"""

import os
import sys
import click
from pathlib import Path
from typing import Dict, List, Tuple, Any

from ..cli.click_logger import ClickLogger, verbose_option, quiet_option
from ..core.manager import YambleManager
from ..core.templates import create_sample_config, create_sample_templates


def check_first_run():
    """Check if this is first run and install completion"""
    # Skip if completion is already working

    config_dir = os.path.expanduser("~/.config/yamble/")
    first_run_marker = os.path.join(config_dir, "completion_installed")

    if not os.path.exists(first_run_marker):
        try:
            from ..completion.completion_installer import (
                install_completion_files,
                reload_shell,
            )

            result = install_completion_files()

            os.makedirs(config_dir, exist_ok=True)
            with open(first_run_marker, "w") as f:
                f.write("completion_installed")

            if result == "reload_shell":
                reload_shell()

            if result == "manual":
                click.echo(
                    click.style(
                        "🛑 Shell completion failed, follow readme instructions for manual installation!",
                        fg="red",
                    )
                )
            else:
                click.echo(
                    click.style(
                        "✓ Shell completion installed, however, completion may not be fully enabled. Please",
                        fg="green",
                    )
                )
                click.echo(
                    click.style("Run: source ~/.bashrc to reload you shell", fg="green")
                )

        except Exception:
            pass


@click.group(invoke_without_command=True)
# @click.option("--verbose", "-v", is_flag=True, help="Enable verbose logging")
@click.option(
    "--templates-dir",
    "-t",
    type=click.Path(exists=False, file_okay=False, dir_okay=True, path_type=Path),
    default=Path("templates"),
    help="Directory containing template files",
)
@click.option(
    "--config-file",
    "-c",
    type=click.Path(dir_okay=False, path_type=Path),
    default=Path("dcm_configurations.yml"),
    help="Configuration file for saved configurations",
)
@verbose_option()
@quiet_option()
@click.pass_context
def cli(
    ctx, templates_dir: Path, config_file: Path, verbose: bool, quiet: bool
) -> None:
    """Compose Template Manager CLI"""
    check_first_run()

    # Store common options in context
    ctx.ensure_object(dict)
    ctx.obj["templates_dir"] = templates_dir
    ctx.obj["config_file"] = config_file
    ctx.obj["verbose"] = verbose
    ctx.obj["quiet"] = quiet
    ctx.obj["manager"] = YambleManager(
        templates_dir=str(templates_dir), config_file=str(config_file)
    )
    ctx.obj["click_logger"] = ClickLogger(verbose, quiet)

    # If no command is specified, show help
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


@cli.command()
def install_completion():
    """Manually install shell completion"""
    from ..completion.completion_installer import install_completion_files

    install_completion_files()
    click.echo("✓ Shell completion installed!")


@cli.command()
@click.pass_context
def list_templates(ctx) -> None:
    """List all available templates organized by category"""
    manager: YambleManager = ctx.obj["manager"]
    templates = manager.get_category_templates()
    click_logger: ClickLogger = ctx.obj["click_logger"]

    all_templates = {}
    for category, category_templates in templates.items():
        display_name = manager.get_category_display_name(category)
        all_templates[display_name] = {}
        if category_templates:
            for template_name in category_templates:
                all_templates[display_name][template_name] = (
                    manager.parse_template_services(template_name)
                )

    click_logger.log_templates(all_templates)


@cli.command()
@click.option("--output", "-o", default="compose.yml", help="Output file path")
@click.pass_context
def interactive(ctx, output: str) -> None:
    """Interactive template selection and compose file generation"""
    manager: YambleManager = ctx.obj["manager"]
    click_logger: ClickLogger = ctx.obj["click_logger"]

    try:
        templates_list = interactive_template_selection(manager)

        # Generate compose file
        if not templates_list:
            click_logger.error("No templates selected!")
            sys.exit(1)

        # templates_list = []
        # for value in templates.values():
        #     templates_list.extend(value)

        parse_variables = get_template_variables_interactive(manager, templates_list)

        # Validate request
        click_logger.debug("Validating templates and variables")
        validation_result = manager.validate_templates(
            templates=templates_list, parsed_variables=parse_variables
        )

        if not validation_result.success:
            click_logger.log_validation_errors(
                validation_result,
                templates=manager.get_all_templates(),
                show_available=True,
            )
            sys.exit(1)

        # Validation success message
        if validation_result.success:
            click_logger.success("All templates valid!")

        result = manager.generate_compose_file(templates_list, output, parse_variables)

        # Log result
        click_logger.log_generation_result(result)

        if result.success:
            if click.confirm("Save this configuration for future use?"):
                save_name = click.prompt("Configuration name")
                manager.save_configuration(save_name, templates_list, parse_variables)
                click.echo(
                    click.style(f"✓ Saved configuration: {save_name}", fg="green")
                )
            sys.exit(0)
        else:
            click.echo(click.style("✗ Failed to generate compose file!", fg="red"))
            sys.exit(1)

    except Exception as e:
        if type(e).__name__ == "Abort":
            click_logger.error("Cancelled by the user")
        else:
            click_logger.error(f"Unexpected error: {e}")
        sys.exit(1)


@cli.command()
@click.option(
    "--template",
    "-T",
    "templates",
    multiple=True,
    required=True,
    help="Templates to use (format: -T template.yml -T template2.yml)",
)
@click.option("--output", "-o", default="compose.yml", help="Output file path")
@click.option(
    "--var",
    "-V",
    "variables",
    multiple=True,
    help="Template variables in key=value format",
)
@click.option(
    "--merge-strategy",
    type=click.Choice(["overwrite", "skip", "merge_deep", "error"]),
    default="overwrite",
    help="Strategy for handling conflicts",
)
@click.pass_context
def generate(
    ctx,
    templates: List[str],
    output: str,
    variables: Tuple[str],
    merge_strategy: str,
) -> None:
    """Generate compose file from specified templates"""
    # Initialize the click logger
    manager: YambleManager = ctx.obj["manager"]
    click_logger: ClickLogger = ctx.obj["click_logger"]

    try:
        success, parsed_variables = parse_variables(list(variables))
        if not success:
            click_logger.error("Unable to pass variables!")
            sys.exit(1)

        # Start generation
        click_logger.log_generation_start(list(templates), parsed_variables, output)

        # Validate request
        click_logger.debug("Validating templates and variables")
        validation_result = manager.validate_templates(
            templates=list(templates), parsed_variables=parsed_variables
        )

        if not validation_result.success:
            click_logger.log_validation_errors(
                validation_result,
                templates=manager.get_all_templates(),
                show_available=True,
            )
            sys.exit(1)

        # Validation success message
        if validation_result.success:
            click_logger.success("All templates valid!")

        # Generate
        click_logger.debug("Generating compose file...")
        result = manager.generate_compose_file(
            templates, output, parsed_variables, merge_strategy
        )

        # Log result
        click_logger.log_generation_result(result)

        sys.exit(0 if result.success else 1)

    except Exception as e:
        if type(e).__name__ == "Abort":
            click_logger.error("Cancelled by the user")
        else:
            click_logger.error(f"Unexpected error: {e}")
        sys.exit(1)


@cli.command()
@click.pass_context
def list_configs(ctx) -> None:
    """List saved configurations"""
    manager: YambleManager = ctx.obj["manager"]
    click_logger: ClickLogger = ctx.obj["click_logger"]
    configs = manager.list_configurations()

    all_configs = {}
    for config_name in configs:
        all_configs[config_name] = manager.load_configuration(config_name)

    click_logger.log_configs(all_configs)


@cli.command()
@click.argument("config_name")
@click.option("--output", "-o", default="compose.yml", help="Output file path")
@click.option(
    "--merge-strategy",
    type=click.Choice(["overwrite", "skip", "merge_deep", "error"]),
    default="overwrite",
    help="Strategy for handling conflicts",
)
@click.pass_context
def use_config(ctx, config_name: str, output: str, merge_strategy: str) -> None:
    """Generate compose file using a saved configuration"""
    manager: YambleManager = ctx.obj["manager"]
    click_logger: ClickLogger = ctx.obj["click_logger"]

    try:
        config = manager.load_configuration(config_name)
        if not config:
            click_logger.error(f"Configuration '{config_name}' not found")
            sys.exit(1)

        selected_templates = config.get("selected_templates", {})
        parsed_variables = config.get("variables", {})

        if not selected_templates:
            click_logger.error("Configuration has no templates selected")
            sys.exit(1)

        # Start generation
        click_logger.log_generation_start(list(selected_templates), parsed_variables, output)

        # Validate request
        click_logger.debug("Validating templates and variables")
        validation_result = manager.validate_templates(
            templates=list(selected_templates), parsed_variables=parsed_variables
        )

        if not validation_result.success:
            click_logger.log_validation_errors(
                validation_result,
                templates=manager.get_all_templates(),
                show_available=True,
            )
            sys.exit(1)

        # Validation success message
        if validation_result.success:
            click_logger.success("All templates valid!")

        # Generate
        click_logger.debug("Generating compose file...")
        result = manager.generate_compose_file(
            selected_templates, output, parsed_variables, merge_strategy
        )

        # Log result
        click_logger.log_generation_result(result)

        sys.exit(0 if result.success else 1)

    except Exception as e:
        if type(e).__name__ == "Abort":
            click_logger.error("Cancelled by the user")
        else:
            click_logger.error(f"Unexpected error: {e}")
        sys.exit(1)


@cli.command()
@click.argument("config_name", required=False)
@click.pass_context
def delete_config(ctx, config_name: str) -> None:
    """Delete a saved configuration"""
    manager: YambleManager = ctx.obj["manager"]

    if not config_name:
        # List available configurations
        configs = manager.get_configuration_names()
        if configs:
            click.echo(click.style("Available configurations:", fg="yellow"))
            for config in configs:
                click.echo(f"  • {config}")
        else:
            click.echo(click.style("No configurations found", fg="yellow"))
        click.echo("\nUsage: delete-config <config_name>")
        sys.exit(1)

    if not manager.load_configuration(config_name):
        click.echo(click.style(f"Configuration '{config_name}' not found", fg="red"))
        # Show available configs here too
        configs = manager.get_configuration_names()
        if configs:
            click.echo(click.style("Available configurations:", fg="yellow"))
            for config in configs:
                click.echo(f"  • {config}")
        sys.exit(1)

    if click.confirm(f"Delete configuration '{config_name}'?"):
        if manager.delete_configuration(config_name):
            click.echo(
                click.style(f"✓ Deleted configuration: {config_name}", fg="green")
            )
        else:
            click.echo(click.style("✗ Failed to delete configuration", fg="red"))


@cli.command()
@click.option("--force", is_flag=True, help="Overwrite existing templates")
@click.pass_context
def create_samples(ctx, force: bool) -> None:
    """Create sample template files"""
    manager: YambleManager = ctx.obj["manager"]
    click_logger: ClickLogger = ctx.obj["click_logger"]
    templates_dir = ctx.obj["templates_dir"]
    config_dir = manager.sample_config_file

    created_count = create_sample_templates(templates_dir, force)

    if created_count > 0:
        click_logger.success(
            f"Created {created_count} sample templates in {templates_dir}"
        )
    else:
        click_logger.info(
            "No sample templates created (files may already exist, use --force to overwrite)"
        )

    if create_sample_config(config_dir, force):
        click_logger.success(f"Sample config file has been created at: {config_dir}")
    else:
        click_logger.error(f"Unable to write sample config at: {config_dir}")


@cli.command()
@click.option(
    "--template",
    "-T",
    "templates",
    multiple=True,
    required=True,
    help="Templates to validate",
)
@click.option(
    "--var",
    "-V",
    "variables",
    multiple=True,
    help="Template variables in key=value format",
)
@click.pass_context
def validate(ctx, templates: List[str], variables: Tuple[str]) -> None:
    """Validate templates and variables"""
    manager: YambleManager = ctx.obj["manager"]
    click_logger: ClickLogger = ctx.obj["click_logger"]

    try:
        click_logger.info(f"Validating {len(templates)} templates", "🔍")

        success, parsed_variables = parse_variables(list(variables))
        if not success:
            click_logger.error("Unable to pass variables!")
            sys.exit(1)

        # Validate
        validation_result = manager.validate_templates(
            templates=list(templates), parsed_variables=parsed_variables
        )

        # Log results
        if validation_result.success:
            click_logger.success(f"All {len(templates)} templates are valid!")
            click_logger.log_parsed_variables(validation_result.parsed_variables)
        else:
            click_logger.log_validation_errors(validation_result)

        sys.exit(0 if validation_result.success else 1)

    except Exception as e:
        click_logger.error(f"Validation failed: {str(e)}")
        sys.exit(1)


def interactive_template_selection(manager: YambleManager) -> List[str]:
    """Interactive template selection interface"""
    templates = manager.get_category_templates()
    selected = set()
    click.echo("\n" + "=" * 60)
    click.echo(click.style("Interactive Template Selection", bold=True, fg="blue"))
    click.echo("=" * 60)

    for category, category_templates in templates.items():
        if not category_templates:
            continue

        display_name = manager.get_category_display_name(category)
        click.echo(f"\n{click.style(display_name, bold=True, fg='green')}:")

        for i, template in enumerate(category_templates, 1):
            services = manager.parse_template_services(template)
            click.echo(f"{i:2d}. {click.style(template, fg='cyan')}")
            if services:
                services_str = ", ".join(services)
                click.echo(f"     Services: {click.style(services_str, fg='yellow')}")

        while True:
            choice = click.prompt(
                f"\nSelect templates for {display_name} (comma-separated numbers, or 'skip')",
                default="skip",
                show_default=True,
            ).strip()

            if choice.lower() == "skip":
                break

            try:
                if choice:
                    indices = [int(x.strip()) - 1 for x in choice.split(",")]
                    category_selected = [
                        category_templates[i]
                        for i in indices
                        if 0 <= i < len(category_templates)
                    ]
                    if category_selected:
                        selected.update(category_selected)
                        click.echo(
                            f"Selected: {click.style(', '.join(category_selected), fg='green')}"
                        )
                break
            except (ValueError, IndexError):
                click.echo(
                    click.style("Invalid selection. Please try again.", fg="red")
                )

    return list(selected)


def get_template_variables_interactive(
    manager: YambleManager, templates: List[str]
) -> Dict[str, Dict[str, Any]]:
    """Get template variables through interactive prompts until they are all valid."""
    new_variables = {}

    click.echo("\n" + "=" * 60)
    click.echo(click.style("Template Variables", bold=True, fg="blue"))
    click.echo("=" * 60)

    for template in templates:
        variables = manager.get_jinja_template_vars(template)
        required_keys = set(variables["required"])
        allowed_keys = required_keys.union(variables["defaults"].keys())

        click.echo(click.style(f"Template: {template}", bold=True))
        click.echo(click.style("   Required:", fg="blue"))
        for value in variables["required"]:
            click.echo(f"      {value}")

        click.echo(click.style("   Defaults:", fg="blue"))
        for key, value in variables["defaults"].items():
            click.echo(f"      {key}: {value}")

        kv_pairs = {}
        missing_keys = required_keys.copy()

        # Keep asking until all required keys are filled and valid
        while missing_keys:
            click.echo(
                click.style(
                    f"\nEnter values for: {', '.join(sorted(missing_keys))} or change any default values",
                    fg="yellow",
                )
            )
            user_input = click.prompt("Format: key=value, key=value", type=str)

            invalid_keys = set()
            for pair in user_input.split(","):
                pair = pair.strip()
                if not pair:
                    continue
                if "=" not in pair:
                    click.echo(click.style(f"Invalid format: {pair}", fg="red"))
                    continue

                key, value = pair.split("=", 1)
                key = key.strip()
                value = value.strip()

                if key not in allowed_keys:
                    click.echo(click.style(f"Unrecognized key: {key}", fg="red"))
                    continue

                # Store value and mark as filled
                kv_pairs[key] = value
                if key in missing_keys:
                    missing_keys.remove(key)

            # If user typed invalid keys, ask again for them specifically
            if invalid_keys:
                missing_keys.update(invalid_keys)

        new_variables[template] = kv_pairs
        new_variables["defaults"] = variables["defaults"]

    return new_variables


def parse_variables(variables: List[str]) -> Tuple[bool, Dict[str, Any]]:
    """Parse variable strings into dictionary"""
    parsed_vars = {"defaults": {}}

    result = True
    for var in variables:
        if "=" not in var:
            click.echo(click.style(f"Invalid variable format: {var} (use key=value)"))
            result = False
            continue

        key, value = var.split("=", 1)
        if key == "ports":
            parsed_vars["defaults"][key] = value.split(",")
        else:
            parsed_vars["defaults"][key] = value

    return (result, parsed_vars)


def main() -> None:
    """Main entry point for CLI"""
    try:
        cli()
    except Exception as e:
        if type(e).__name__ == "Abort":
            click.echo(click.style("Cancelled by the user", fg='red', bold=True))
        else:
            click.echo(click.style(f"Unexpected error: {e}", fg='red', bold=True))
        sys.exit(1)


if __name__ == "__main__":
    main()
