#!/usr/bin/env python3
"""Yamble GUI Launcher - Simple passthrough to main module"""

import sys
import subprocess

def main():
    """Launch the GUI by running main module"""
    # Run as a module, not a script - this makes relative imports work
    cmd = [sys.executable, '-m', 'yamble.gui.main'] + sys.argv[1:]

    try:
        return subprocess.run(cmd).returncode
    except KeyboardInterrupt:
        print("\nShutting down Yamble GUI...")
        return 0

if __name__ == '__main__':
    sys.exit(main())
