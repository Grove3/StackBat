"""
Template management utilities
"""

from pathlib import Path
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)


def create_sample_config(config_file: Path, force: bool = False) -> bool:
    sample_config = """
categories:
  password:
    display_name: Password
    templates:
      - bitwarden.yml.j2
      - traefik.yml.j2
  media:
    display_name: Media
    templates:
      - pia_vpn.yml.j2
      - plex.yml.j2
      - sabnzbd.yml.j2

configurations:
  demo:
    templates: &demo_templates
      - "traefik.yml.j2"
      - "bitwarden.yml.j2"
      - "pia_vpn.yml.j2"
      - "photoprism.yml.j2"
      - "traefik.yml.j2"
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
      pia_vpn.yml.j2:
        local_ip: "192.168.0.3"
        dns_ip: "192.168.0.3"
        ports:
          - "1234:1234"
          - "5678:5678"
      photoprism.yml.j2:
        password: "super_secret"
      defaults:
        restart: "always"
        docker_volume_dir: "your/docker/volumes"
        domain: "example.com"
    profiles:
      number: 3
      variables:
        tag: [local, dev, prod]
        cf_dns_api_token: [1234, 5678, 3456]

  demo_2:
    templates: &demo2_templates
      - "plex.yml.j2"
      - "traefik.yml.j2"
      - "sabnzbd.yml.j2"
      - "joplin.yml.j2"
      - "traefik.yml.j2"
    variables: &demo2_variables
      traefik.yml.j2:
        tag: "2.11"
        restart: "unless-stopped"
        cf_api_email: "demo@example.com"
        cf_dns_api_token: "demo-token-1234"
        traefik_network: "frontend"
      plex.yml.j2:
        tag: "latest"
        traefik_label: "plex"
        advertise_ip: "http://192.168.1.50:32400/"
      sabnzbd.yml.j2:
        tag: "stable"
        api_key: "sab-api-key-9876"
        host_port: "8080:8080"
      joplin.yml.j2:
        tag: "latest"
        password: "notes_secret"
      defaults:
        restart: "always"
        docker_volume_dir: "/srv/docker/volumes"
        domain: "demo2.example.com"

  demo_3:
    templates:
      - *demo_templates
      - *demo2_templates
    variables:
      <<: [*demo_variables, *demo2_variables]
"""

    return write(sample_config, config_file)


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
        "bitwarden.yml.j2": """
services:
  bitwarden:
    image: vaultwarden/server:{{ tag | default('latest') }}
    container_name: {{ name | default('bitwarden')}}
    restart: {{ restart | default('unless-stopped')}}
    security_opt:
      - no-new-privileges:true
    networks:
      - proxy
    volumes:
      - {{ docker_volume_dir }}/bitwarden:/data/
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.{{ traefik_label }}.entrypoints=http"
      - "traefik.http.routers.{{ traefik_label }}.rule=Host(`{{ traefik_label }}.{{ domain }}`)"
      - "traefik.http.middlewares.{{ traefik_label }}-https-redirect.redirectscheme.scheme=https"
      - "traefik.http.routers.{{ traefik_label }}.middlewares={{ traefik_label }}-https-redirect"
      - "traefik.http.routers.{{ traefik_label }}-secure.entrypoints=https"
      - "traefik.http.routers.{{ traefik_label }}-secure.rule=Host(`{{ traefik_label }}.{{ domain }}`)"
      - "traefik.http.routers.{{ traefik_label }}-secure.tls=true"
      - "traefik.docker.network=proxy"

networks:
  proxy:
    external: true
""",
        "traefik.yml.j2": """
services:
  traefik:
    image: traefik:{{ tag | default('latest') }}
    container_name: traefik
    restart: {{ restart | default('unless-stopped') }}
    security_opt:
      - no-new-privileges:true
    networks:
      - {{ traefik_network | default('proxy') }}
    ports:
      - "{{ http_port | default('80') }}:80"
      - "{{ https_port | default('443') }}:443"
      - "{{ traefik_api_port | default('9000') }}:8080"
    command:
      - --api.debug={{ api_debug | default('true') }}
      - --log.level={{ log_level | default('DEBUG') }}
    environment:
      - CF_API_EMAIL={{ cf_api_email }}
      - CF_DNS_API_TOKEN={{ cf_dns_api_token }}
    volumes:
      - {{ docker_sock_path | default('/var/run/docker.sock') }}:/var/run/docker.sock:ro
      - {{ docker_volume_dir }}/traefik/traefik.yml:/traefik.yml:ro
      - {{ docker_volume_dir }}/traefik/acme.json:/acme.json
      - {{ docker_volume_dir }}/traefik/config.yml:/config.yml:ro
    labels:
      - "traefik.enable=true"

      # HTTP router
      - "traefik.http.routers.traefik.entrypoints=http"
      - "traefik.http.routers.traefik.rule=Host(`traefik.{{ domain }}`)"
      - "traefik.http.middlewares.traefik-https-redirect.redirectscheme.scheme=https"
      - "traefik.http.middlewares.sslheader.headers.customrequestheaders.X-Forwarded-Proto=https"
      - "traefik.http.routers.traefik.middlewares=traefik-https-redirect"

      # HTTPS router
      - "traefik.http.routers.traefik-secure.entrypoints=https"
      - "traefik.http.routers.traefik-secure.rule=Host(`traefik.{{ domain }}`)"
      - "traefik.http.routers.traefik-secure.tls=true"
      - "traefik.http.routers.traefik-secure.tls.certresolver={{ cert_resolver | default('cloudflare') }}"
      - "traefik.http.routers.traefik-secure.tls.domains[0].main={{ domain }}"
      - "traefik.http.routers.traefik-secure.tls.domains[0].sans=*.{{ domain | default('*.example.com') }}"
      - "traefik.http.routers.traefik-secure.service=api@internal"

networks:
  proxy:
    external: true
""",
        "pia_vpn.yml.j2": """
services:
  pia-vpn:
    image: {{ image | default('grove/pia-openvpn:v1') }}
    container_name: {{ name | default('pia-vpn') }}
    restart: {{ restart | default('unless-stopped')}}
    networks:
      - pia
    environment:
      REGION: "AU Sydney"
      LOCALNET: {{ local_ip }}
    cap_add:
      - NET_ADMIN
    dns:
      - "{{ dns_ip | default('8.8.8.8')}}"
    volumes:
      - {{ docker_volume_dir }}/torrents/pia-vpn:/config
    command: ["--auth-user-pass", "/config/auth.conf"]
    ports:
      {% for port in ports %}
      - {{ port }}
      {% endfor %}
      # ports of other containers that use the vpn (to access them locally)

networks:
  pia:
    external: true
""",
        "photoprism.yml.j2": """
services:
  photoprism:
    image: photoprism/photoprism:{{ tag | default('latest')}}
    container_name: {{ name | default('photoprism') }}
    restart: {{ restart | default('unless-stopped')}}
    user: {{ user | default('1000') }}:{{ group | default('1000')}}
    networks:
      - proxy
      - photos
    environment:
      PHOTOPRISM_ADMIN_PASSWORD: {{ password }}
      PHOTOPRISM_SITE_URL: photoprism.{{ domain }}
      HOME: "/photoprism"
    working_dir: "/photoprism"
    volumes:
      - "{{ docker_volume_dir }}/pictures:/photoprism/originals"
      - "{{ docker_volume_dir }}/pictures/import:/photoprism/import"
      - "{{ docker_volume_dir }}/photoprism:/photoprism/storage"
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.photos.entrypoints=http"
      - "traefik.http.routers.photos.rule=Host(`photoprism.{{ domain }}`)"
      - "traefik.http.middlewares.photos-https-redirect.redirectscheme.scheme=https"
      - "traefik.http.routers.photos.middlewares=photos-https-redirect"
      - "traefik.http.routers.photos-secure.entrypoints=https"
      - "traefik.http.routers.photos-secure.rule=Host(`photoprism.{{ domain }}`)"
      - "traefik.http.routers.photos-secure.tls=true"
      - "traefik.docker.network=proxy"
    depends_on:
      - photosdb

  photosdb:
    image: mariadb:{{ tag | default('latest')}}
    container_name: {{ name | default('photoprism-db') }}
    restart: {{ restart | default('unless-stopped')}}
    networks:
      - photos
    volumes:
      - {{ docker_volume_dir }}/photoprism/db:/var/lib/mysql # Important, don't remove
    environment:
      MYSQL_ROOT_PASSWORD: {{ password }}
      MYSQL_DATABASE: {{ db_name | default('photoprism') }}
      MYSQL_USER: {{ db_user | default('photoprism')}}
      MYSQL_PASSWORD: {{ password }}

networks:
  proxy:
    external: true

  photos:
    external: true
""",
        "plex.yml.j2": """
services:
  plex:
    image: plexinc/pms-docker:{{ tag | default('latest') }}
    container_name: {{ name | default('plex') }}
    restart: {{ restart | default('unless-stopped') }}
    security_opt:
      - no-new-privileges:true
    networks:
      - proxy
    environment:
      - ADVERTISE_IP={{ advertise_ip | default('') }}
    volumes:
      - {{ docker_volume_dir }}/plex:/config
      - /mnt/media:/data
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.{{ traefik_label }}.entrypoints=http"
      - "traefik.http.routers.{{ traefik_label }}.rule=Host(`{{ traefik_label }}.{{ domain }}`)"
      - "traefik.http.middlewares.{{ traefik_label }}-https-redirect.redirectscheme.scheme=https"
      - "traefik.http.routers.{{ traefik_label }}.middlewares={{ traefik_label }}-https-redirect"
      - "traefik.http.routers.{{ traefik_label }}-secure.entrypoints=https"
      - "traefik.http.routers.{{ traefik_label }}-secure.rule=Host(`{{ traefik_label }}.{{ domain }}`)"
      - "traefik.http.routers.{{ traefik_label }}-secure.tls=true"
      - "traefik.docker.network=proxy"

networks:
  proxy:
    external: true
""",
        "sabnzbd.yml.j2": """
services:
  sabnzbd:
    image: linuxserver/sabnzbd:{{ tag | default('stable') }}
    container_name: {{ name | default('sabnzbd') }}
    restart: {{ restart | default('unless-stopped') }}
    security_opt:
      - no-new-privileges:true
    networks:
      - proxy
    environment:
      - API_KEY={{ api_key }}
    ports:
      - "{{ host_port }}"
    volumes:
      - {{ docker_volume_dir }}/sabnzbd:/config
      - /mnt/downloads:/downloads
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.{{ traefik_label | default('sabnzbd') }}.entrypoints=http"
      - "traefik.http.routers.{{ traefik_label | default('sabnzbd') }}.rule=Host(`{{ traefik_label | default('sabnzbd') }}.{{ domain }}`)"
      - "traefik.http.middlewares.{{ traefik_label | default('sabnzbd') }}-https-redirect.redirectscheme.scheme=https"
      - "traefik.http.routers.{{ traefik_label | default('sabnzbd') }}.middlewares={{ traefik_label | default('sabnzbd') }}-https-redirect"
      - "traefik.http.routers.{{ traefik_label | default('sabnzbd') }}-secure.entrypoints=https"
      - "traefik.http.routers.{{ traefik_label | default('sabnzbd') }}-secure.rule=Host(`{{ traefik_label | default('sabnzbd') }}.{{ domain }}`)"
      - "traefik.http.routers.{{ traefik_label | default('sabnzbd') }}-secure.tls=true"
      - "traefik.docker.network=proxy"

networks:
  proxy:
    external: true
""",
        "joplin.yml.j2": """
services:
  joplin:
    image: joplin/server:{{ tag | default('latest') }}
    container_name: {{ name | default('joplin') }}
    restart: {{ restart | default('unless-stopped') }}
    security_opt:
      - no-new-privileges:true
    networks:
      - proxy
    environment:
      - APP_BASE_URL=https://{{ traefik_label | default('joplin') }}.{{ domain }}
      - APP_PORT=22300
      - POSTGRES_PASSWORD={{ password }}
    volumes:
      - {{ docker_volume_dir }}/joplin:/var/lib/joplin
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.{{ traefik_label | default('joplin') }}.entrypoints=http"
      - "traefik.http.routers.{{ traefik_label | default('joplin') }}.rule=Host(`{{ traefik_label | default('joplin') }}.{{ domain }}`)"
      - "traefik.http.middlewares.{{ traefik_label | default('joplin') }}-https-redirect.redirectscheme.scheme=https"
      - "traefik.http.routers.{{ traefik_label | default('joplin') }}.middlewares={{ traefik_label | default('joplin') }}-https-redirect"
      - "traefik.http.routers.{{ traefik_label | default('joplin') }}-secure.entrypoints=https"
      - "traefik.http.routers.{{ traefik_label | default('joplin') }}-secure.rule=Host(`{{ traefik_label | default('joplin') }}.{{ domain }}`)"
      - "traefik.http.routers.{{ traefik_label | default('joplin') }}-secure.tls=true"
      - "traefik.docker.network=proxy"

networks:
  proxy:
    external: true
"""
    }

    templates_dir.mkdir(exist_ok=True)
    created_count = 0

    for filename, content in sample_templates.items():
        template_path = templates_dir / filename

        if template_path.exists() and not force:
            logger.info(f"Template {filename} already exists, skipping")
            continue

        if (write(content, template_path)):
          created_count += 1

    return created_count


def write(content: str, template_path: Path) -> bool:
    try:
        with open(template_path, "w") as f:
            f.write(content)
        logger.info(f"Created sample file: {template_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to create file {template_path}: {e}")
        return False


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
        if any(func in var_name for func in ["range", "loop", "if", "else", "endif"]):
            continue

        variables[var_name] = default_value

    # Find {% if variable %} patterns
    if_pattern = r'\{\%\s*if\s+([^%\s]+)(?:\s*==\s*[\'"]([^\'"]*)[\'"]\s*)?\s*\%\}'
    if_matches = re.findall(if_pattern, content)

    for match in if_matches:
        var_name = match[0].strip()
        # Skip complex conditions
        if not any(op in var_name for op in ["and", "or", "not", "(", ")"]):
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
        from jinja2 import Environment

        # Create a basic Jinja2 environment
        env = Environment()

        # Try to parse the template
        template = env.from_string(content)

        # Try to render with empty context to check for basic syntax errors
        template.render()

        return True, "Template syntax is valid"

    except Exception as e:
        return False, f"Template syntax error: {str(e)}"
