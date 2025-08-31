# CLI Usage Guide

## Installation

```bash
pip install yamble
```

Shell completion is automatically installed on first run. To manually install:
```bash
yamble install-completion
source ~/.bashrc
```

## Global Options

```bash
yamble --help                              # Show help
yamble --templates-dir /path/to/templates  # Custom templates directory
yamble --config-file /path/to/config.yml   # Custom configuration file
yamble --verbose                           # Enable verbose logging
yamble --quiet                             # Suppress non-error output
```

## Core Commands

### Interactive Mode (Recommended for Beginners)
```bash
yamble interactive
yamble interactive --output my-compose.yml
yamble interactive --merge-strategy merge_deep
```

Interactive mode guides you through:
1. Template selection by category
2. Variable input with validation
3. Option to save configuration for reuse

### List Available Resources

```bash
# List all templates organized by category
yamble list-templates

# List saved configurations
yamble list-configs
```

### Generate Compose Files

```bash
# Basic generation with single template
yamble generate -T plex.yml.j2 -o compose.yml

# Multiple templates with variables
yamble generate \
  -T plex.yml.j2 \
  -T bitwarden.yml.j2 \
  -V plex_version=v2.1 \
  -V bitwarden_version=latest \
  -V environment=production \
  -o production-compose.yml

# With custom merge strategy
yamble generate \
  -T template1.yml.j2 \
  -T template2.yml.j2 \
  --merge-strategy merge_deep \
  -o merged-compose.yml
```

### Configuration Management

```bash
# Use a saved configuration
yamble use-config production-setup
yamble use-config staging-config --output staging-compose.yml

# Override variables in saved config
yamble use-config production-setup \
  -V environment=testing \

# Delete configurations
yamble delete-config old-config
yamble delete-config  # Shows available configs if none specified
```

### Launch Mode (Generate + Run)

```bash
# Generate and run Docker Compose
yamble launch production-config

# Run in daemon mode
yamble launch production-config -d

# Override variables when launching
yamble launch production-config \
  -V environment=staging \
  -V debug_mode=true \
  -d
```

### Template Validation

```bash
# Validate single template
yamble validate -T plex.yml.j2

# Validate with variables
yamble validate \
  -T plex.yml.j2 \
  -V plex_version=v2.1 \
  -V port=8080

# Validate multiple templates
yamble validate \
  -T plex.yml.j2 \
  -T bitwarden.yml.j2 \
  -V plex_version=v2.1
```

### Setup and Sample Creation

```bash
# Create sample templates and configuration
yamble create-samples

# Force overwrite existing samples
yamble create-samples --force
```

## Variable Formats

Variables are specified using `-V key=value` format:

```bash
# String variables
-V service_name=plex
-V environment=production

# Port lists (comma-separated)
-V ports=8080:8080,9090:9090,3000:3000

# Version tags
-V plex_version=v2.1.0
-V bitwarden_version=latest

# Boolean-like values
-V debug_mode=true
-V ssl_enabled=false
```

## Merge Strategies

When combining multiple templates that have conflicting keys:

```bash
# Overwrite (default) - later templates override earlier ones
yamble generate -T base.yml.j2 -T override.yml.j2 --merge-strategy overwrite

# Skip - keep first occurrence, skip conflicts
yamble generate -T base.yml.j2 -T override.yml.j2 --merge-strategy skip

# Deep merge - intelligently merge nested objects
yamble generate -T base.yml.j2 -T override.yml.j2 --merge-strategy merge_deep

# Error on conflicts - fail if any conflicts exist
yamble generate -T base.yml.j2 -T override.yml.j2 --merge-strategy error
```

## Multi-Environment Management
Yamble supports two approaches for managing multiple environments: manual variable overrides and automated profile-based deployment.

### Manual Environment Management
Override variables for different environments using the -V flag:

```bash
# Development
yamble use-config base-config \
  -V environment=dev \
  -V debug_mode=true \
  -o dev-compose.yml

# Staging
yamble use-config base-config \
  -V environment=staging \
  -o staging-compose.yml

# Production
yamble use-config base-config \
  -V environment=production \
  -V ssl_enabled=true \
  -o production-compose.yml
```

### Profile-Based Multi-Environment Deployment
Profiles enable you to define a single configuration that automatically generates multiple environment-specific compose files. Define the number of profiles and specify which variables change across environments:
```yml
configurations:
  multi_env_app:
    selected_templates:
      - "traefik.yml.j2"
      - "web_app.yml.j2"
    variables:
      traefik.yml.j2:
        restart: "unless-stopped"
        traefik_network: "proxy"
      web_app.yml.j2:
        database_host: "db.internal"
      defaults:
        restart: "always"
        domain: "example.com"
      profiles:
        number: 3
        variables:
          cf_dns_api_token:
            - "dev-token-1234"
            - "staging-token-5678"
            - "prod-token-3456"
          tag:
            - "dev"
            - "staging"
            - "prod"
          ssl_enabled:
            - false
            - true
            - true
```

When you use a configuration with profiles, Yamble generates separate compose files for each environment:

```bash
yamble use-config multi_env_app
```

This generates:

* `compose_1.yml` (dev environment: dev tag, 1 replica, SSL disabled)
* `compose_2.yml` (staging environment: staging tag, 2 replicas, SSL enabled)
* `compose_3.yml` (prod environment: prod tag, 5 replicas, SSL enabled)

### Profile Variable Mapping
Each profile gets its variables by index position:

* **Profile 1** (index 0): `tag: "dev"`, `cf_dns_api_token: "dev-token-1234"`, `ssl_enabled: false`
* **Profile 2** (index 1): `tag: "staging"`, `cf_dns_api_token: "staging-token-5678"`, `ssl_enabled: true`
* **Profile 3** (index 2): `tag: "prod"`, `cf_dns_api_token: "prod-token-3456"`, `ssl_enabled: true`

Variables not listed in the profile's variables section remain the same across all profiles.

### Complex Profile Example

```yml
configurations:
  microservices_stack:
    selected_templates:
      - "api_gateway.yml.j2"
      - "user_service.yml.j2"
      - "payment_service.yml.j2"
    variables:
      defaults:
        restart: "always"
        network: "microservices"
      profiles:
        number: 4  # dev, test, staging, prod
        variables:
          environment_name:
            - "development"
            - "testing"
            - "staging"
            - "production"
          tag:
            - "dev"
            - "test"
            - "staging"
            - "v2.1.0"
          database_url:
            - "postgres://dev-db:5432/app"
            - "postgres://test-db:5432/app"
            - "postgres://staging-db:5432/app"
            - "postgres://prod-db:5432/app"
          log_level:
            - "DEBUG"
            - "INFO"
            - "WARN"
            - "ERROR"
```
This configuration generates four complete deployment environments with different database connections, scaling, and logging configurations, perfect for CI/CD pipelines or rapid environment provisioning.

## Troubleshooting

### Common Issues

```bash
# Template not found
yamble list-templates  # Check available templates

# Configuration not found
yamble list-configs   # Check saved configurations

# Variable validation errors
yamble validate -T template.yml.j2 -V key=value  # Test variables

# Shell completion not working
yamble install-completion
source ~/.bashrc

# Verbose output for debugging
yamble --verbose generate -T template.yml.j2
```

### File Locations

- Default templates directory: `./templates/`
- Default config file: `./dcm_configurations.yml`
- Completion marker: `~/.config/yamble/completion_installed`

### Exit Codes

- `0`: Success
- `1`: General error (validation failed, file not found, etc.)
- `130`: User cancelled (Ctrl+C)

## Tips and Best Practices

1. **Start with Interactive Mode**: Use `yamble interactive` to understand the workflow
2. **Save Configurations**: Save commonly used template combinations for quick reuse
3. **Validate First**: Use `yamble validate` to catch issues before generation
4. **Use Verbose Mode**: Add `--verbose` when troubleshooting
5. **Organize Templates**: Use the category system to organize templates logically
6. **Version Control**: Keep your templates directory under version control