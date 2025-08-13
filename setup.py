#!/usr/bin/env python3
"""
Setup configuration for Compose Manager
"""

from setuptools import setup, find_packages
import os

# Read the contents of README file
this_directory = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(this_directory, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

# Core requirements
install_requires = [
    'jinja2>=3.0.0',
    'pyyaml>=6.0',
    'click>=8.0.0',
]

# Optional dependencies
extras_require = {
    'gui': [
        'customtkinter>=5.2.2'
    ],  # tkinter is part of standard library
    'dev': [
        'pytest>=6.0.0',
        'pytest-cov>=2.0.0',
        'black>=22.0.0',
        'flake8>=3.9.0',
        'mypy>=0.800',
        'pre-commit>=2.0.0',
    ],
    'docs': [
        'sphinx>=4.0.0',
        'sphinx-rtd-theme>=0.5.0',
    ]
}

# All extras combined
extras_require['all'] = list(set(sum(extras_require.values(), [])))

setup(
    name='compose-manager',
    version='0.1.0',
    author='Stephen Grove',
    author_email='grove_3@hotmail.com',
    description='A CLI and GUI tool for managing Compose templates using Jinja2',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/yourusername/compose-manager',
    packages=find_packages(),
    include_package_data=True,
    install_requires=install_requires,
    extras_require=extras_require,
    python_requires='>=3.7',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: System :: Systems Administration',
        'Topic :: Utilities',
    ],
    entry_points={
        'console_scripts': [
            'compose-manager=compose_manager.cli.main:main',
            'dcm=compose_manager.cli.main:main',  # Short alias
        ],
        'gui_scripts': [
            'compose-manager-gui=compose_manager.gui.main:main [gui]',
        ],
    },
    keywords='docker docker-compose compose jinja2 templates cli gui',
    project_urls={
        'Bug Reports': 'https://github.com/yourusername/compose-manager/issues',
        'Source': 'https://github.com/yourusername/compose-manager',
        'Documentation': 'https://compose-manager.readthedocs.io/',
    },
)
