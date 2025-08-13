"""
Completion Installer for Compose Manager
"""

# compose_manager/completion_installer.py
import os
from importlib import resources
import subprocess

import logging

logger = logging.getLogger(__name__)

def install_completion_files():
    """Install completion files using importlib.resources"""
    shell = os.environ.get('SHELL', '')
    home = os.path.expanduser('~')
    action_needed = None

    try:
        if 'bash' in shell or not shell:
            # Get completion content using importlib.resources
            try:
                # Python 3.9+ syntax
                completion_content = (resources.files('compose_manager') / 'completion' / 'bash' / 'compose-manager').read_text()
            except AttributeError:
                # Python 3.8 fallback
                with resources.path('compose_manager.completion.bash', 'compose-manager') as completion_file:
                    completion_content = completion_file.read_text()

            # Try system completion directories first (no restart needed)
            system_dirs = [
                '/etc/bash_completion.d/',
                '/usr/local/etc/bash_completion.d/',
                '/usr/share/bash-completion/completions/'
            ]

            # Try system directories first (work immediately)
            for sys_dir in system_dirs:
                if os.path.exists(sys_dir) and os.access(sys_dir, os.W_OK):
                    try:
                        with open(os.path.join(sys_dir, 'compose-manager'), 'w') as f:
                            f.write(completion_content)
                            logger.debug(f"Completion file installed to {sys_dir}")
                        return "immediate"
                    except:
                        continue

            # Fallback to user directories
            user_completion_dir = os.path.join(home, '.local/share/bash-completion/completions/')
            os.makedirs(user_completion_dir, exist_ok=True)

            with open(os.path.join(user_completion_dir, 'compose-manager'), 'w') as f:
                f.write(completion_content)
                logger.debug(f"Completion file installed to {user_completion_dir}")
            action_needed = "reload_shell"

        elif 'zsh' in shell:
            # Get zsh completion content
            try:
                completion_content = (resources.files('compose_manager') / 'completion' / 'zsh' / '_compose-manager').read_text()
            except AttributeError:
                with resources.path('compose_manager.completion.zsh', '_compose-manager') as completion_file:
                    completion_content = completion_file.read_text()

            # Install to user zsh completion directory
            user_zsh_dir = os.path.join(home, '.local/share/zsh/site-functions/')
            os.makedirs(user_zsh_dir, exist_ok=True)

            with open(os.path.join(user_zsh_dir, '_compose-manager'), 'w') as f:
                f.write(completion_content)
                logger.debug(f"Completion file installed to {user_zsh_dir}")
            action_needed = "reload_shell"

        return action_needed

    except Exception as e:
        # Fallback to bashrc method
        return install_to_bashrc()

def install_to_bashrc():
    """Fallback: install to bashrc if completion directories don't work"""
    home = os.path.expanduser('~')
    bashrc = os.path.join(home, '.bashrc')
    completion_line = 'eval "$(_COMPOSE_MANAGER_COMPLETE=bash_source compose-manager)"'

    try:
        # Check if already installed
        if os.path.exists(bashrc):
            with open(bashrc, 'r') as f:
                if '_COMPOSE_MANAGER_COMPLETE=' in f.read():
                    return "already_installed"

        # Add to bashrc
        with open(bashrc, 'a') as f:
            f.write(f'\n# compose-manager completion\n{completion_line}\n')
            logger.debug("Completion file installed to ~/.bashrc")
        return "reload_shell"

    except Exception:
        return "manual"

def reload_shell():
    """Try to reload the current shell completion"""
    try:
        # Try to reload bash completion
        subprocess.run(['bash', '-c', 'source ~/.bashrc'],
                      capture_output=True, timeout=2)
        return True
    except:
        return False

