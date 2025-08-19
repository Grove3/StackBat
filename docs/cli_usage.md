# CLI Usage Guide

## Installation

```bash
pip install yamble
```

## Basic Commands

### List Available Templates
```bash
yamble list-templates
```

### Interactive Mode
```bash
yamble interactive
```

### Generate Compose File
```bash
yamble generate \
  -T flight:flight_core.yml.j2 \
  -T hatp:hatp_services.yml.j2 \
  -V flight_version=v2.1 \
  -V hatp_version=latest \
  -o my-compose.yml
```

### Validate Templates
```bash
yamble validate -T flight_core.yml.j2 -V flight_version=v2.1
```

### Configuration Management
```bash
# List saved configurations
yamble list-configs

# Use saved configuration
yamble use-config production-config

# Delete configuration
yamble delete-config old-config
```

### Create Sample Templates
```bash
yamble create-samples --force
```

## Advanced Usage

### Custom Templates Directory
```bash
yamble --templates-dir /path/to/templates list-templates
```

### Custom Configuration File
```bash
yamble --config-file /path/to/config.json interactive
```

### Verbose Output
```bash
yamble --verbose generate -T flight:flight_core.yml.j2
```
