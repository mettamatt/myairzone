#!/usr/bin/env python3
"""
Setup script for Airzone HVAC Control System
"""

from setuptools import setup, find_packages

setup(
    name="myairzone",
    version="1.0.0",
    description="A streamlined Python toolkit for Airzone HVAC systems",
    packages=find_packages(),
    python_requires=">=3.7",
    install_requires=[
        "requests>=2.28.0",
        "pytest>=7.4.0",
        "pytest-cov>=4.1.0", 
        "responses>=0.23.0",
    ],
    entry_points={
        "console_scripts": [
            "airzone=cli.airzone_cli:main",
        ],
    },
    author="Matt",
    author_email="",
    url="",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
)
