#!/usr/bin/env python3
"""
Main entry point for Airzone CLI.
This script provides backwards compatibility by importing and running the CLI from the new location.
"""

import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(__file__))

# Import and run the CLI
from cli.airzone_cli import main

if __name__ == "__main__":
    sys.exit(main())
