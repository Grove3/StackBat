# Yamble - Compose Template Manager

A powerful CLI and GUI tool for managing Docker Compose templates using Jinja2 templating. Organize your containerized applications by categories and generate customized Compose files with dynamic configuration.

## Features

- **Template Categories**: Organize templates by functional areas
- **Jinja2 Templating**: Dynamic template rendering with variables and conditionals
- **CLI Interface**: Scriptable command-line interface with shell completion
- **GUI Interface**: User-friendly graphical interface with live preview
- **Configuration Management**: Save and reuse template configurations
- **Template Validation**: Validate template syntax and structure
- **Interactive Mode**: Step-by-step template selection and variable input
- **Launch Mode**: Generate and immediately run Docker Compose
- **Shell Completion**: Auto-completion for commands and options

## Installation

### Basic Installation (CLI only)
```bash
pip install yamble
```

### Full Installation (CLI + GUI)
```bash
pip install yamble[gui]
```

### Development Installation
```bash
git clone git@bitbucket.org:grove_3/yamble.git
cd yamble
python3 -m venv venv
source venv/bin/activate
pip install -e .[dev,gui]
```

## Quick Start

for more in-depth documentation refer to the following:
* [cli usage](docs/cli_usage.md)
* [gui usage](docs/gui_usage.md)

### Create Sample Templates
```bash
yamble create-samples
# This will create templates folder with sample templates and sample_configurations.yml file
# To try the samples, rename sample_configuration.yml to dcm_configurations.yml
mv sample_configurations.yml dcm_configurations.yml
```

### CLI Usage
```bash
# List available templates
yamble list-templates

# Interactive mode (recommended for first-time users)
yamble interactive

# Direct generation
yamble generate -T plex.yml.j2 -T bitwarden.yml.j2 -V tag=latest -o my-compose.yml

# Use saved configuration
yamble use-config my-config

# Generate and launch immediately
yamble launch my-config -d

# Validate templates before generation
yamble validate -T plex.yml.j2 -V tag=latest
```

### GUI Usage
```bash
yamble-gui
```

## Shell Completion

Yamble automatically installs shell completion on first run. If you need to manually install it:

```bash
yamble install-completion
source ~/.bashrc  # or restart your shell
```

## Template Categories
Template categories enable you to organize and group related templates for better discoverability and cleaner CLI output. When templates are organized by categories like "Media", or "Password", the list-templates command presents them in logical groups with clear headings, making it easier to find and select the right templates for your use case.

```yml
categories:
  media:
    display_name: Media
    templates:
    - pia_vpn.yml.j2
    - plex.yml.j2
    - sabnzbd.yml.j2
  password:
    display_name: Password
    templates:
    - bitwarden.yml.j2
    - traefik.yml.j2
```

`yamble -v list-templates`

```bash
============================================================
Available Templates
============================================================

Media:
  • pia_vpn.yml.j2
    Services: pia-vpn
  • plex.yml.j2
    Services: plex
  • sabnzbd.yml.j2
    Services: sabnzbd

Password:
  • bitwarden.yml.j2
    Services: bitwarden
  • traefik.yml.j2
    Services: traefik

others:
  • photoprism.yml.j2
    Services: photoprism, photosdb
  • joplin.yml.j2
    Services: joplin
============================================================

Summary:
   Categories: 3
   Templates: 7
```

## Template Variables

Templates support Jinja2 variables with defaults:

```yaml
services:
  flight_controller:
    image: flight/controller:{{ flight_version | default('latest') }}
    ports:
      - "{{ flight_controller_port | default('8080') }}:8080"
    environment:
      - FLIGHT_MODE={{ flight_mode | default('auto') }}
```

Variables can be provided via:
- Command line: `-V key=value`
- Interactive prompts
- Saved configurations

## Configuration Management

Yamble's configuration system leverages the full power of YAML to provide flexible, reusable, and maintainable template configurations. Configurations are stored in YAML format and support advanced YAML features like anchors, aliases, and merging to eliminate duplication and enable sophisticated configuration composition.

### Basic Configuration Structure
Configurations are saved in YAML format and include:

* **Templates:** List of template files to use
* **Template variables:** Variable values for each template
* **Default variables:** Global defaults applied to all templates
* **Profiles:** Multi-environment variable sets

### YAML Anchors and Aliases
Use YAML anchors (&) and aliases (*) to define reusable configuration blocks and eliminate duplication:

```yml
configurations:
  demo:
    templates: &demo_templates
      - "traefik.yml.j2"
      - "bitwarden.yml.j2"
      - "pia_vpn.yml.j2"
      - "photoprism.yml.j2"
    variables: &demo_variables
      traefik.yml.j2:
        tag: "latest"
        restart: "unless-stopped"
        cf_api_email: "user@example.com"
        cf_dns_api_token: "your-token-here"
        traefik_network: "proxy"
      bitwarden.yml.j2:
        tag: "local"
        traefik_label: "bitwarden"
      defaults:
        restart: "always"
        docker_volume_dir: "your/docker/volumes"
        domain: "example.com"

  demo_2:
    templates: &demo2_templates
      - "plex.yml.j2"
      - "sabnzbd.yml.j2"
      - "joplin.yml.j2"
    variables: &demo2_variables
      plex.yml.j2:
        tag: "latest"
        traefik_label: "plex"
        advertise_ip: "http://192.168.1.50:32400/"
      defaults:
        restart: "always"
        docker_volume_dir: "/srv/docker/volumes"
        domain: "demo2.example.com"
```
### Configuration Composition

Combine multiple configurations using YAML merge keys (<<) and list concatenation to create composite configurations:

```yml
  # Composite configuration combining demo and demo_2
  demo_3:
    templates:
      - *demo_templates
      - *demo2_templates
    variables:
      <<: [*demo_variables, *demo2_variables]
```

This creates a new configuration (demo_3) that:

Combines templates from both demo and demo_2 configurations
Merges variables from both configurations, with later values overriding earlier ones
Inherits all settings from the referenced configurations

### Profile Support

Profiles enable multi-environment deployments with different variable sets:

```yml
configurations:
  multi_env:
    templates:
      - "app.yml.j2"
    variables:
      app.yml.j2:
        base_config: "shared"
      defaults:
        restart: "always"
      profiles:
        number: 3
        variables:
          tag: [dev, staging, prod]
          cf_dns_api_token: [dev-token, staging-token, prod-token]
```
### Configuration Commands

```bash
# List all saved configurations with details
yamble list-configs

# Use a configuration
yamble use-config demo_3

# Override specific variables in a configuration
yamble use-config demo_3 \
  -V domain=prod.example.com \
  -V tag=v2.1.0

# Generate using configuration with custom output
yamble use-config demo_3 --output production-compose.yml

# Delete configurations
yamble delete-config demo_3
```

### Best Practices

1. **Use Anchors for Reusability:** Define common configuration blocks as anchors to avoid repetition
2. **Organize by Environment:** Create base configurations and extend them for different environments
3. **Leverage Composition:** Combine configurations to build complex deployments from modular pieces
4. **Profile Multi-Environment:** Use profiles for configurations that need to deploy across multiple environments
5. **Meaningful Names:** Use descriptive configuration names that indicate their purpose (e.g., production-web-stack, dev-minimal)

This approach allows you to build sophisticated, maintainable configuration hierarchies while keeping individual configurations clean and focused.

## Advanced Features

### Merge Strategies
When combining multiple templates, you can specify how conflicts are handled:
- `overwrite` (default): Later templates override earlier ones
- `skip`: Skip conflicting keys
- `merge_deep`: Deep merge objects and arrays
- `error`: Fail on conflicts

### Custom Directories
```bash
# Use custom templates directory
yamble --templates-dir /path/to/templates list-templates

# Use custom config file
yamble --config-file /path/to/config.yml interactive
```

### Verbose Output
```bash
# Enable verbose logging
yamble -v generate -T template.yml.j2

# Quiet mode (errors only)
yamble -q use-config prod
```

## Command Reference

| Command | Description |
|---------|-------------|
| `interactive` | Step-by-step template selection and generation |
| `generate` | Generate compose file from specified templates |
| `launch` | Generate and run Docker Compose |
| `list-templates` | Show all available templates by category |
| `list-configs` | Show all saved configurations |
| `use-config` | Generate using a saved configuration |
| `delete-config` | Delete a saved configuration |
| `validate` | Validate templates and variables |
| `create-samples` | Create example templates and configuration |
| `install-completion` | Manually install shell completion |

## Examples

### Basic Generation
```bash
yamble generate \
  -T plex.yml.j2 \
  -T bitwarden.yml.j2 \
  -V tag=v2.1 \
  -V domain=example.com \
  -o production-compose.yml
```

### Interactive Configuration
```bash
yamble interactive --output staging-compose.yml
# Follow prompts to select templates and set variables
# Option to save configuration for reuse
```

### Launch with Custom Settings
```bash
yamble launch production-config \
  -V environment=staging \
  -d
```

## Contributing

1. Create a feature branch
2. Make your changes
3. Add tests
4. Submit a pull request

## License

MIT License - see LICENSE file for details.
