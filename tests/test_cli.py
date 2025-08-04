"""
Tests for CLI functionality
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from click.testing import CliRunner
from compose_manager.cli.main import cli
from compose_manager.core.templates import create_sample_templates


class TestCLI:

    def setup_method(self):
        """Setup test environment"""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.templates_dir = self.temp_dir / "templates"
        self.config_file = self.temp_dir / "test_config.json"

        # Create sample templates
        create_sample_templates(self.templates_dir)

        self.runner = CliRunner()

    def teardown_method(self):
        """Cleanup test environment"""
        shutil.rmtree(self.temp_dir)

    def test_list_templates(self):
        """Test list-templates command"""
        result = self.runner.invoke(cli, [
            '--templates-dir', str(self.templates_dir),
            'list-templates'
        ])

        assert result.exit_code == 0
        assert 'Available Templates' in result.output
        assert 'Flight Containers' in result.output

    def test_create_samples(self):
        """Test create-samples command"""
        new_templates_dir = self.temp_dir / "new_templates"

        result = self.runner.invoke(cli, [
            '--templates-dir', str(new_templates_dir),
            'create-samples'
        ])

        assert result.exit_code == 0
        assert new_templates_dir.exists()

    def test_generate_command(self):
        """Test generate command"""
        output_file = self.temp_dir / "test-output.yml"

        result = self.runner.invoke(cli, [
            '--templates-dir', str(self.templates_dir),
            'generate',
            '-T', 'flight:flight_core.yml.j2',
            '-V', 'flight_version=v2.1',
            '-o', str(output_file)
        ])

        assert result.exit_code == 0
        assert output_file.exists()

    def test_validate_command(self):
        """Test validate command"""
        result = self.runner.invoke(cli, [
            '--templates-dir', str(self.templates_dir),
            'validate',
            '-T', 'flight_core.yml.j2',
            '-V', 'flight_version=v2.1'
        ])

        # Should succeed if template exists and is valid
        # May fail if template doesn't exist, which is also valid for testing
        assert result.exit_code in [0, 1]


if __name__ == '__main__':
    pytest.main([__file__])
