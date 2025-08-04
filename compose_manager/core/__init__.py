"""
Core functionality for Compose Template Manager
"""

from .manager import ComposeManager
from .templates import create_sample_templates

__all__ = ["ComposeManager", "create_sample_templates"]
