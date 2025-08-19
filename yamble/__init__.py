"""
Compose Template Manager

A CLI and GUI tool for managing Compose templates using Jinja2.
"""

__version__ = "0.1.0"
__author__ = "Stephen Grove"
__email__ = "grove_3@hotmail.com"

from .core.manager import YambleManager

__all__ = ["YambleManager"]
