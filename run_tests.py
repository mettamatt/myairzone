#!/usr/bin/env python3
"""
Simple test runner for AirZone project.

This script runs pytest with appropriate options for running the test suite.
"""

import pytest
import sys
import os
import argparse

def main():
    """Run the tests."""
    parser = argparse.ArgumentParser(description="Run tests for AirZone project")
    parser.add_argument("--cov", action="store_true", help="Generate coverage report")
    parser.add_argument("--html", action="store_true", help="Generate HTML coverage report")
    parser.add_argument("--xml", action="store_true", help="Generate XML coverage report")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("path", nargs="?", default="tests/", help="Test path to run (default: tests/)")
    
    args = parser.parse_args()
    
    # Ensure we're in the project root
    project_root = os.path.dirname(os.path.abspath(__file__))
    os.chdir(project_root)
    
    # Build pytest arguments
    pytest_args = []
    
    # Always show test progress
    pytest_args.append("-v")
    
    # Add extra verbosity if requested
    if args.verbose:
        pytest_args.append("-vv")
    
    # Add coverage if requested
    if args.cov:
        pytest_args.append("--cov=.")
        pytest_args.append("--cov-report=term")
        
        if args.html:
            pytest_args.append("--cov-report=html")
        
        if args.xml:
            pytest_args.append("--cov-report=xml")
    
    # Add test path
    pytest_args.append(args.path)
    
    # Print the command being run
    print(f"Running: pytest {' '.join(pytest_args)}\n")
    
    # Run pytest with the assembled arguments
    return pytest.main(pytest_args)

if __name__ == "__main__":
    sys.exit(main())