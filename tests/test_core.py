"""
Tests for core functionality
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from yamble.core.manager import YambleManager
from yamble.core.templates import create_sample_templates


class TestYambleManager:

    def setup_method(self):
        """Setup test environment"""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.templates_dir = self.temp_dir / "templates"
        self.config_file = self.temp_dir / "test_config.json"

        self.manager = YambleManager(
            templates_dir=str(self.templates_dir),
            config_file=str(self.config_file)
        )

    def teardown_method(self):
        """Cleanup test environment"""
        shutil.rmtree(self.temp_dir)

    def test_manager_initialization(self):
        """Test manager initialization"""
        assert self.manager.templates_dir.exists()
        assert self.manager.categories
        assert len(self.manager.categories) == 4

    def test_create_sample_templates(self):
        """Test sample template creation"""
        count = create_sample_templates(self.templates_dir)
        assert count > 0

        # Check that templates were created
        templates = self.manager.get_all_templates()
        assert any(templates.values())

    def test_template_parsing(self):
        """Test template service parsing"""
        # Create sample templates first
        create_sample_templates(self.templates_dir)

        # Test parsing a template
        flight_templates = self.manager.get_template_files('flight')
        if flight_templates:
            services = self.manager.parse_template_services(flight_templates[0])
            assert isinstance(services, list)

    def test_configuration_management(self):
        """Test saving and loading configurations"""
        selected_templates = {
            'flight': ['flight_core.yml.j2']
        }
        variables = {
            'flight_version': 'v2.1',
            'flight_mode': 'auto'
        }

        # Save configuration
        self.manager.save_configuration('test_config', selected_templates, variables)

        # Load configuration
        loaded_config = self.manager.load_configuration('test_config')
        assert loaded_config is not None
        assert loaded_config['selected_templates'] == selected_templates
        assert loaded_config['variables'] == variables

    def test_compose_generation(self):
        """Test compose file generation"""
        # Create sample templates
        create_sample_templates(self.templates_dir)

        selected_templates = {
            'flight': ['flight_core.yml.j2']
        }
        variables = {
            'flight_version': 'v2.1',
            'flight_mode': 'auto'
        }

        output_file = self.temp_dir / "test-compose.yml"

        success = self.manager.generate_compose_file(
            selected_templates,
            str(output_file),
            variables
        )

        assert success
        assert output_file.exists()

        # Check content
        with open(output_file, 'r') as f:
            content = f.read()
            assert 'flight_controller' in content
            assert 'v2.1' in content


if __name__ == '__main__':
    pytest.main([__file__])
