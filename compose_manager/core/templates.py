"""
Template management utilities
"""

from pathlib import Path
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)


def create_sample_templates(templates_dir: Path, force: bool = False) -> int:
    """
    Create sample template files for demonstration

    Args:
        templates_dir: Directory to create templates in
        force: Overwrite existing templates if True

    Returns:
        Number of templates created
    """
    sample_templates = {
        'flight_core.yml.j2': '''# Flight Core Services Template
version: '3.8'

services:
  flight_controller:
    image: flight/controller:{{ flight_version | default('latest') }}
    container_name: flight_controller_{{ instance_id | default('1') }}
    ports:
      - "{{ flight_controller_port | default('8080') }}:8080"
    environment:
      - FLIGHT_MODE={{ flight_mode | default('auto') }}
      - LOG_LEVEL={{ log_level | default('INFO') }}
      - INSTANCE_ID={{ instance_id | default('1') }}
    volumes:
      - flight_logs:/var/log/flight
      - flight_config:/etc/flight
    networks:
      - flight_network
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  flight_telemetry:
    image: flight/telemetry:{{ flight_version | default('latest') }}
    container_name: flight_telemetry_{{ instance_id | default('1') }}
    ports:
      - "{{ flight_telemetry_port | default('8081') }}:8081"
    environment:
      - TELEMETRY_RATE={{ telemetry_rate | default('10') }}
      - DATA_FORMAT={{ data_format | default('json') }}
    depends_on:
      - flight_controller
    volumes:
      - flight_data:/var/data/telemetry
    networks:
      - flight_network
    restart: unless-stopped

{% if include_flight_recorder | default('false') == 'true' %}
  flight_recorder:
    image: flight/recorder:{{ flight_version | default('latest') }}
    container_name: flight_recorder_{{ instance_id | default('1') }}
    environment:
      - RECORD_FORMAT={{ record_format | default('parquet') }}
      - COMPRESSION={{ compression | default('gzip') }}
    volumes:
      - flight_recordings:/var/recordings
    networks:
      - flight_network
    depends_on:
      - flight_telemetry
    restart: unless-stopped
{% endif %}

networks:
  flight_network:
    driver: bridge
    ipam:
      config:
        - subnet: {{ flight_subnet | default('172.20.0.0/16') }}

volumes:
  flight_logs:
    driver: local
  flight_config:
    driver: local
  flight_data:
    driver: local
{% if include_flight_recorder | default('false') == 'true' %}
  flight_recordings:
    driver: local
{% endif %}
''',

        'flight_simulation.yml.j2': '''# Flight Simulation Services Template
version: '3.8'

services:
  flight_simulator:
    image: flight/simulator:{{ flight_version | default('latest') }}
    container_name: flight_simulator_{{ instance_id | default('1') }}
    ports:
      - "{{ simulator_port | default('9000') }}:9000"
      - "{{ simulator_ui_port | default('9001') }}:9001"
    environment:
      - SIM_MODE={{ sim_mode | default('realistic') }}
      - PHYSICS_ENGINE={{ physics_engine | default('bullet') }}
      - WEATHER_ENABLED={{ weather_enabled | default('true') }}
      - TIME_SCALE={{ time_scale | default('1.0') }}
    volumes:
      - sim_scenarios:/var/scenarios
      - sim_results:/var/results
    networks:
      - flight_network
    restart: unless-stopped
    {% if gpu_enabled | default('false') == 'true' %}
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
    {% endif %}

  scenario_manager:
    image: flight/scenario-manager:{{ flight_version | default('latest') }}
    container_name: scenario_manager_{{ instance_id | default('1') }}
    ports:
      - "{{ scenario_port | default('9002') }}:9002"
    environment:
      - SCENARIO_PATH=/var/scenarios
      - AUTO_LOAD={{ auto_load_scenarios | default('true') }}
    volumes:
      - sim_scenarios:/var/scenarios:ro
    networks:
      - flight_network
    depends_on:
      - flight_simulator
    restart: unless-stopped

networks:
  flight_network:
    external: true

volumes:
  sim_scenarios:
    driver: local
  sim_results:
    driver: local
''',

        'hatp_services.yml.j2': '''# HATP (High Availability Transport Protocol) Services Template
version: '3.8'

services:
  hatp_processor:
    image: hatp/processor:{{ hatp_version | default('latest') }}
    container_name: hatp_processor_{{ instance_id | default('1') }}
    ports:
      - "{{ hatp_processor_port | default('9090') }}:9090"
    environment:
      - HATP_CONFIG={{ hatp_config | default('/config/default.yml') }}
      - PROCESSING_THREADS={{ processing_threads | default('4') }}
      - BUFFER_SIZE={{ buffer_size | default('1024') }}
      - LOG_LEVEL={{ log_level | default('INFO') }}
    volumes:
      - hatp_data:/data
      - hatp_config:/config
      - hatp_logs:/var/log/hatp
    networks:
      - hatp_network
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "hatp-health-check"]
      interval: 30s
      timeout: 10s
      retries: 3

  hatp_gateway:
    image: hatp/gateway:{{ hatp_version | default('latest') }}
    container_name: hatp_gateway_{{ instance_id | default('1') }}
    ports:
      - "{{ hatp_gateway_port | default('9091') }}:9091"
      - "{{ hatp_gateway_admin_port | default('9092') }}:9092"
    environment:
      - GATEWAY_MODE={{ gateway_mode | default('cluster') }}
      - MAX_CONNECTIONS={{ max_connections | default('1000') }}
      - TIMEOUT={{ connection_timeout | default('30') }}
    depends_on:
      - hatp_processor
    volumes:
      - hatp_gateway_config:/etc/gateway
    networks:
      - hatp_network
    restart: unless-stopped

{% if include_hatp_monitor | default('true') == 'true' %}
  hatp_monitor:
    image: hatp/monitor:{{ hatp_version | default('latest') }}
    container_name: hatp_monitor_{{ instance_id | default('1') }}
    ports:
      - "{{ hatp_monitor_port | default('9093') }}:9093"
    environment:
      - MONITOR_INTERVAL={{ monitor_interval | default('5') }}
      - ALERT_THRESHOLD={{ alert_threshold | default('80') }}
      - METRICS_RETENTION={{ metrics_retention | default('7d') }}
    depends_on:
      - hatp_processor
      - hatp_gateway
    volumes:
      - hatp_metrics:/var/metrics
    networks:
      - hatp_network
    restart: unless-stopped
{% endif %}

{% if enable_hatp_cluster | default('false') == 'true' %}
  hatp_cluster_coordinator:
    image: hatp/cluster-coordinator:{{ hatp_version | default('latest') }}
    container_name: hatp_coordinator_{{ instance_id | default('1') }}
    ports:
      - "{{ coordinator_port | default('9094') }}:9094"
    environment:
      - CLUSTER_SIZE={{ cluster_size | default('3') }}
      - ELECTION_TIMEOUT={{ election_timeout | default('5000') }}
      - HEARTBEAT_INTERVAL={{ heartbeat_interval | default('1000') }}
    networks:
      - hatp_network
    restart: unless-stopped
{% endif %}

networks:
  hatp_network:
    driver: bridge
    attachable: true
    ipam:
      config:
        - subnet: {{ hatp_subnet | default('172.21.0.0/16') }}

volumes:
  hatp_data:
    driver: local
  hatp_config:
    driver: local
  hatp_logs:
    driver: local
  hatp_gateway_config:
    driver: local
{% if include_hatp_monitor | default('true') == 'true' %}
  hatp_metrics:
    driver: local
{% endif %}
''',

        'hatpy_services.yml.j2': ''' # HATPY template
services:
  hatp_processor:
    image: hatpy/processor:{{ hatpy_version | default('latest') }}
    container_name: hatp_processor_{{ instance_id | default('1') }}
    ports:
      - "{{ hatp_processor_port | default('9090') }}:9090"
    environment:
      - HATP_CONFIG={{ hatp_config | default('/config/default.yml') }}
      - PROCESSING_THREADS={{ processing_threads | default('4') }}
      - BUFFER_SIZE={{ buffer_size | default('1024') }}
      - LOG_LEVEL={{ log_level | default('INFO') }}
    volumes:
      - hatp_data:/data
      - hatp_config:/config
      - hatp_logs:/var/log/hatp
    networks:
      - hatp_network
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "hatp-health-check"]
      interval: 30s
      timeout: 10s
      retries: 3

''',

        'mission_system_core.yml.j2': '''# Mission System Core Template
version: '3.8'

services:
  mission_planner:
    image: mission/planner:{{ mission_version | default('latest') }}
    container_name: mission_planner_{{ instance_id | default('1') }}
    ports:
      - "{{ mission_planner_port | default('7070') }}:7070"
    environment:
      - MISSION_MODE={{ mission_mode | default('planning') }}
      - PLANNING_ALGORITHM={{ planning_algorithm | default('astar') }}
      - MAX_WAYPOINTS={{ max_waypoints | default('1000') }}
      - SAFETY_MARGIN={{ safety_margin | default('10.0') }}
    volumes:
      - mission_plans:/var/plans
      - mission_maps:/var/maps
      - mission_config:/etc/mission
    networks:
      - mission_network
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:7070/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  mission_executor:
    image: mission/executor:{{ mission_version | default('latest') }}
    container_name: mission_executor_{{ instance_id | default('1') }}
    ports:
      - "{{ mission_executor_port | default('7071') }}:7071"
    environment:
      - EXECUTION_MODE={{ execution_mode | default('automatic') }}
      - CHECKPOINT_INTERVAL={{ checkpoint_interval | default('30') }}
      - RECOVERY_STRATEGY={{ recovery_strategy | default('rollback') }}
    depends_on:
      - mission_planner
    volumes:
      - mission_plans:/var/plans:ro
      - mission_state:/var/state
      - mission_logs:/var/log/mission
    networks:
      - mission_network
    restart: unless-stopped

  mission_monitor:
    image: mission/monitor:{{ mission_version | default('latest') }}
    container_name: mission_monitor_{{ instance_id | default('1') }}
    ports:
      - "{{ mission_monitor_port | default('7072') }}:7072"
    environment:
      - MONITOR_FREQUENCY={{ monitor_frequency | default('1') }}
      - ALERT_ENABLED={{ alert_enabled | default('true') }}
      - DASHBOARD_ENABLED={{ dashboard_enabled | default('true') }}
    depends_on:
      - mission_planner
      - mission_executor
    volumes:
      - mission_state:/var/state:ro
      - mission_logs:/var/log/mission:ro
    networks:
      - mission_network
    restart: unless-stopped

{% if include_mission_database | default('true') == 'true' %}
  mission_database:
    image: {{ database_image | default('postgres:13') }}
    container_name: mission_db_{{ instance_id | default('1') }}
    ports:
      - "{{ database_port | default('5432') }}:5432"
    environment:
      - POSTGRES_DB={{ database_name | default('mission_db') }}
      - POSTGRES_USER={{ database_user | default('mission_user') }}
      - POSTGRES_PASSWORD={{ database_password | default('mission_pass') }}
    volumes:
      - mission_db_data:/var/lib/postgresql/data
    networks:
      - mission_network
    restart: unless-stopped
{% endif %}

networks:
  mission_network:
    driver: bridge
    ipam:
      config:
        - subnet: {{ mission_subnet | default('172.22.0.0/16') }}

volumes:
  mission_plans:
    driver: local
  mission_maps:
    driver: local
  mission_config:
    driver: local
  mission_state:
    driver: local
  mission_logs:
    driver: local
{% if include_mission_database | default('true') == 'true' %}
  mission_db_data:
    driver: local
{% endif %}
''',

        'mission_autonomy_ai.yml.j2': '''# Mission Autonomy AI Template
version: '3.8'

services:
  autonomy_engine:
    image: autonomy/engine:{{ autonomy_version | default('latest') }}
    container_name: autonomy_engine_{{ instance_id | default('1') }}
    ports:
      - "{{ autonomy_engine_port | default('6060') }}:6060"
    environment:
      - AI_MODE={{ ai_mode | default('learning') }}
      - MODEL_PATH={{ model_path | default('/models/default') }}
      - INFERENCE_BATCH_SIZE={{ inference_batch_size | default('32') }}
      - LEARNING_RATE={{ learning_rate | default('0.001') }}
      - GPU_ENABLED={{ gpu_enabled | default('false') }}
    volumes:
      - autonomy_models:/models
      - autonomy_data:/data
      - autonomy_logs:/var/log/autonomy
    networks:
      - autonomy_network
    restart: unless-stopped
    {% if gpu_enabled | default('false') == 'true' %}
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: {{ gpu_count | default('1') }}
              capabilities: [gpu]
    {% endif %}
    healthcheck:
      test: ["CMD", "python", "-c", "import requests; requests.get('http://localhost:6060/health')"]
      interval: 30s
      timeout: 10s
      retries: 3

  autonomy_trainer:
    image: autonomy/trainer:{{ autonomy_version | default('latest') }}
    container_name: autonomy_trainer_{{ instance_id | default('1') }}
    ports:
      - "{{ autonomy_trainer_port | default('6061') }}:6061"
    environment:
      - TRAINING_MODE={{ training_mode | default('supervised') }}
      - EPOCHS={{ training_epochs | default('100') }}
      - VALIDATION_SPLIT={{ validation_split | default('0.2') }}
      - CHECKPOINT_FREQUENCY={{ checkpoint_frequency | default('10') }}
    depends_on:
      - autonomy_engine
    volumes:
      - autonomy_models:/models
      - autonomy_training_data:/training_data
      - autonomy_checkpoints:/checkpoints
    networks:
      - autonomy_network
    restart: unless-stopped
    {% if gpu_enabled | default('false') == 'true' %}
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: {{ gpu_count | default('1') }}
              capabilities: [gpu]
    {% endif %}

  autonomy_inference:
    image: autonomy/inference:{{ autonomy_version | default('latest') }}
    container_name: autonomy_inference_{{ instance_id | default('1') }}
    ports:
      - "{{ autonomy_inference_port | default('6062') }}:6062"
    environment:
      - MODEL_VERSION={{ model_version | default('latest') }}
      - INFERENCE_TIMEOUT={{ inference_timeout | default('5000') }}
      - BATCH_PROCESSING={{ batch_processing | default('true') }}
    depends_on:
      - autonomy_engine
    volumes:
      - autonomy_models:/models:ro
      - autonomy_inference_cache:/cache
    networks:
      - autonomy_network
    restart: unless-stopped
    {% if gpu_enabled | default('false') == 'true' %}
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
    {% endif %}

{% if include_model_registry | default('true') == 'true' %}
  model_registry:
    image: autonomy/model-registry:{{ autonomy_version | default('latest') }}
    container_name: model_registry_{{ instance_id | default('1') }}
    ports:
      - "{{ model_registry_port | default('6063') }}:6063"
    environment:
      - STORAGE_BACKEND={{ model_storage_backend | default('local') }}
      - VERSIONING_ENABLED={{ model_versioning | default('true') }}
      - METADATA_DB={{ model_metadata_db | default('sqlite') }}
    volumes:
      - autonomy_models:/models
      - model_registry_db:/var/db
    networks:
      - autonomy_network
    restart: unless-stopped
{% endif %}

{% if include_data_pipeline | default('false') == 'true' %}
  data_pipeline:
    image: autonomy/data-pipeline:{{ autonomy_version | default('latest') }}
    container_name: data_pipeline_{{ instance_id | default('1') }}
    ports:
      - "{{ data_pipeline_port | default('6064') }}:6064"
    environment:
      - PIPELINE_CONFIG={{ pipeline_config | default('/config/pipeline.yml') }}
      - DATA_FORMAT={{ data_format | default('parquet') }}
      - PROCESSING_WORKERS={{ processing_workers | default('4') }}
    volumes:
      - autonomy_data:/data
      - autonomy_training_data:/training_data
      - pipeline_config:/config
    networks:
      - autonomy_network
    restart: unless-stopped
{% endif %}

networks:
  autonomy_network:
    driver: bridge
    ipam:
      config:
        - subnet: {{ autonomy_subnet | default('172.23.0.0/16') }}

volumes:
  autonomy_models:
    driver: local
  autonomy_data:
    driver: local
  autonomy_logs:
    driver: local
  autonomy_training_data:
    driver: local
  autonomy_checkpoints:
    driver: local
  autonomy_inference_cache:
    driver: local
{% if include_model_registry | default('true') == 'true' %}
  model_registry_db:
    driver: local
{% endif %}
{% if include_data_pipeline | default('false') == 'true' %}
  pipeline_config:
    driver: local
{% endif %}
'''
    }

    templates_dir.mkdir(exist_ok=True)
    created_count = 0

    for filename, content in sample_templates.items():
        template_path = templates_dir / filename

        if template_path.exists() and not force:
            logger.info(f"Template {filename} already exists, skipping")
            continue

        try:
            with open(template_path, 'w') as f:
                f.write(content)
            logger.info(f"Created sample template: {filename}")
            created_count += 1
        except Exception as e:
            logger.error(f"Failed to create template {filename}: {e}")

    return created_count


def get_template_variables_from_content(content: str) -> Dict[str, Optional[str]]:
    """
    Extract Jinja2 variables from template content

    Args:
        content: Template content to analyze

    Returns:
        Dictionary mapping variable names to their default values (if any)
    """
    import re

    variables = {}

    # Find {{ variable }} patterns
    var_pattern = r'\{\{\s*([^}|]+)(?:\s*\|\s*default\([\'"]([^\'"]*)[\'"]\))?\s*\}\}'
    matches = re.findall(var_pattern, content)

    for match in matches:
        var_name = match[0].strip()
        default_value = match[1] if match[1] else None

        # Skip Jinja2 functions and complex expressions
        if any(func in var_name for func in ['range', 'loop', 'if', 'else', 'endif']):
            continue

        variables[var_name] = default_value

    # Find {% if variable %} patterns
    if_pattern = r'\{\%\s*if\s+([^%\s]+)(?:\s*==\s*[\'"]([^\'"]*)[\'"]\s*)?\s*\%\}'
    if_matches = re.findall(if_pattern, content)

    for match in if_matches:
        var_name = match[0].strip()
        # Skip complex conditions
        if not any(op in var_name for op in ['and', 'or', 'not', '(', ')']):
            if var_name not in variables:
                variables[var_name] = None

    return variables


def validate_jinja_template(content: str) -> tuple[bool, str]:
    """
    Validate Jinja2 template syntax

    Args:
        content: Template content to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        from jinja2 import Environment, Template

        # Create a basic Jinja2 environment
        env = Environment()

        # Try to parse the template
        template = env.from_string(content)

        # Try to render with empty context to check for basic syntax errors
        template.render()

        return True, "Template syntax is valid"

    except Exception as e:
        return False, f"Template syntax error: {str(e)}"


def get_sample_variables() -> Dict[str, str]:
    """
    Get sample variable values for testing templates

    Returns:
        Dictionary of sample variable values
    """
    return {
        # Flight variables
        'flight_version': 'v2.1.0',
        'flight_mode': 'auto',
        'flight_controller_port': '8080',
        'flight_telemetry_port': '8081',
        'instance_id': '1',
        'log_level': 'INFO',
        'telemetry_rate': '10',
        'data_format': 'json',
        'include_flight_recorder': 'false',
        'flight_subnet': '172.20.0.0/16',

        # Simulation variables
        'simulator_port': '9000',
        'simulator_ui_port': '9001',
        'sim_mode': 'realistic',
        'physics_engine': 'bullet',
        'weather_enabled': 'true',
        'time_scale': '1.0',
        'scenario_port': '9002',
        'auto_load_scenarios': 'true',

        # HATP variables
        'hatp_version': 'v1.5.0',
        'hatp_config': '/config/production.yml',
        'hatp_processor_port': '9090',
        'hatp_gateway_port': '9091',
        'hatp_gateway_admin_port': '9092',
        'hatp_monitor_port': '9093',
        'processing_threads': '8',
        'buffer_size': '2048',
        'gateway_mode': 'cluster',
        'max_connections': '2000',
        'connection_timeout': '30',
        'include_hatp_monitor': 'true',
        'enable_hatp_cluster': 'false',
        'hatp_subnet': '172.21.0.0/16',

        # Mission System variables
        'mission_version': 'v3.0.0',
        'mission_mode': 'planning',
        'mission_planner_port': '7070',
        'mission_executor_port': '7071',
        'mission_monitor_port': '7072',
        'planning_algorithm': 'astar',
        'max_waypoints': '1000',
        'safety_margin': '10.0',
        'execution_mode': 'automatic',
        'checkpoint_interval': '30',
        'recovery_strategy': 'rollback',
        'monitor_frequency': '1',
        'alert_enabled': 'true',
        'dashboard_enabled': 'true',
        'include_mission_database': 'true',
        'database_image': 'postgres:13',
        'database_port': '5432',
        'database_name': 'mission_db',
        'database_user': 'mission_user',
        'database_password': 'mission_pass',
        'mission_subnet': '172.22.0.0/16',

        # Autonomy variables
        'autonomy_version': 'v2.0.0',
        'ai_mode': 'learning',
        'autonomy_engine_port': '6060',
        'autonomy_trainer_port': '6061',
        'autonomy_inference_port': '6062',
        'model_registry_port': '6063',
        'data_pipeline_port': '6064',
        'model_path': '/models/default',
        'inference_batch_size': '32',
        'learning_rate': '0.001',
        'gpu_enabled': 'true',
        'gpu_count': '1',
        'training_mode': 'supervised',
        'training_epochs': '100',
        'validation_split': '0.2',
        'checkpoint_frequency': '10',
        'model_version': 'latest',
        'inference_timeout': '5000',
        'batch_processing': 'true',
        'include_model_registry': 'true',
        'include_data_pipeline': 'false',
        'model_storage_backend': 'local',
        'model_versioning': 'true',
        'model_metadata_db': 'sqlite',
        'pipeline_config': '/config/pipeline.yml',
        'processing_workers': '4',
        'autonomy_subnet': '172.23.0.0/16',
    }
