# GUI Usage Guide

## Installation

```bash
pip install yamble[gui]
```

## Launching the GUI

```bash
yamble-gui
```

## Interface Overview

### Template Selection Panel (Left)
- **Category Tabs**: Flight, HATP, Mission System, Mission Autonomy
- **Template Checkboxes**: Select individual templates
- **Service Information**: Shows services defined in each template
- **Selection Summary**: Overview of selected templates and services

### Configuration Panel (Right)
- **Variable Configuration**: Set Jinja2 template variables
- **Output File Selection**: Choose where to save the compose file
- **Action Buttons**: Generate, validate, save/load configurations
- **Live Preview**: Real-time preview of generated compose file

## Workflow

1. **Select Templates**: Check desired templates from category tabs
2. **Configure Variables**: Set values for template variables
3. **Preview**: Review the generated compose file in real-time
4. **Generate**: Create the final compose.yml file
5. **Save Configuration**: Save template selections and variables for reuse

## Features

### Template Management
- Browse templates by category
- View services defined in each template
- Validate template syntax and variables

### Configuration Management
- Save current template selections and variables
- Load previously saved configurations
- Delete unused configurations

### Live Preview
- Real-time preview of generated compose file
- Basic YAML syntax highlighting
- Updates automatically when selections change

### Validation
- Validate selected templates before generation
- Check template syntax and variable usage
- Display validation results in detailed dialog

## Menu Options

### File Menu
- **New Configuration**: Clear current selections
- **Save Configuration**: Save current state
- **Load Configuration**: Load saved configuration
- **Exit**: Close application

### Templates Menu
- **Refresh Templates**: Reload templates from disk
- **Create Sample Templates**: Generate example templates
- **Validate Selected**: Check selected templates

### Help Menu
- **About**: Application information
