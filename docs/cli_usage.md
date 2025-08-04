# CLI Usage Guide

## Installation

```bash
pip install compose-manager
```

## Basic Commands

### List Available Templates
```bash
compose-manager list-templates
```

### Interactive Mode
```bash
compose-manager interactive
```

### Generate Compose File
```bash
compose-manager generate \
  -T flight:flight_core.yml.j2 \
  -T hatp:hatp_services.yml.j2 \
  -V flight_version=v2.1 \
  -V hatp_version=latest \
  -o my-compose.yml
```

### Validate Templates
```bash
compose-manager validate -T flight_core.yml.j2 -V flight_version=v2.1
```

### Configuration Management
```bash
# List saved configurations
compose-manager list-configs

# Use saved configuration
compose-manager use-config production-config

# Delete configuration
compose-manager delete-config old-config
```

### Create Sample Templates
```bash
compose-manager create-samples --force
```

## Advanced Usage

### Custom Templates Directory
```bash
compose-manager --templates-dir /path/to/templates list-templates
```

### Custom Configuration File
```bash
compose-manager --config-file /path/to/config.json interactive
```

### Verbose Output
```bash
compose-manager --verbose generate -T flight:flight_core.yml.j2
```
