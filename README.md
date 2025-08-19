# Compose Template Manager

A powerful CLI and GUI tool for managing Compose templates using Jinja2 templating. Organize your containerized applications by categories (Flight, HATP, Mission System, Mission Autonomy) and generate customized Compose files with dynamic configuration.

## Features

- **Template Categories**: Organize templates by functional areas
- **Jinja2 Templating**: Dynamic template rendering with variables and conditionals
- **CLI Interface**: Scriptable command-line interface for automation
- **GUI Interface**: User-friendly graphical interface with live preview
- **Configuration Management**: Save and reuse template configurations
- **Template Validation**: Validate template syntax and structure
- **Live Preview**: See generated compose files in real-time

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

### Create Sample Templates
```bash
yamble create-samples
```

### CLI Usage
```bash
# List available templates
yamble list-templates

# Interactive mode
yamble interactive

# Direct generation
yamble generate -T flight:flight_core.yml.j2 -V flight_version=v2.1 -o my-compose.yml

# Use saved configuration
yamble use-config my-config
```

### GUI Usage
```bash
yamble-gui
```

## Template Categories

- **Flight Containers**: Flight control, telemetry, simulation
- **HATP Containers**: High Availability Transport Protocol services
- **Mission System Containers**: Mission planning, execution, monitoring
- **Mission Autonomy Containers**: AI/ML services, model management

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

## Configuration

Configurations are saved in JSON format and include:
- Selected templates by category
- Template variable values
- Output file preferences

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

MIT License - see LICENSE file for details.
