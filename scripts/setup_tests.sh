#!/bin/bash

# Exit on error
set -e

YELLOW='\033[1;33m'
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Help message
function show_help {
    echo -e "${YELLOW}AirZone Test Setup and Runner${NC}"
    echo ""
    echo "Usage: ./setup_tests.sh [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -h, --help                Show this help message"
    echo "  -i, --install             Install dependencies only"
    echo "  -c, --coverage            Generate coverage report"
    echo "  -s, --skip-install        Skip dependency installation"
    echo ""
    echo "Without options, this script will install dependencies and run all tests."
}

# Parse arguments
INSTALL_DEPS=true
GENERATE_COVERAGE=false
RUN_TESTS=true

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        -i|--install)
            RUN_TESTS=false
            ;;
        -c|--coverage)
            GENERATE_COVERAGE=true
            ;;
        -s|--skip-install)
            INSTALL_DEPS=false
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            show_help
            exit 1
            ;;
    esac
    shift
done

echo -e "${YELLOW}Setting up the test environment for AirZone project...${NC}"

# Activate virtual environment if it exists
if [ -d ".venv" ]; then
    echo "Activating virtual environment..."
    source .venv/bin/activate
fi

# Install or update dependencies
if [[ "$INSTALL_DEPS" == "true" ]]; then
    echo -e "${YELLOW}Installing dependencies...${NC}"
    pip install -r requirements.txt
fi

# Run tests
if [[ "$RUN_TESTS" == "true" ]]; then
    if [[ "$GENERATE_COVERAGE" == "true" ]]; then
        echo -e "${YELLOW}Running tests with coverage...${NC}"
        python run_tests.py --cov --html
        echo -e "${GREEN}Coverage report generated in 'htmlcov/' directory${NC}"
        echo -e "${GREEN}Open 'htmlcov/index.html' in your browser to view the report${NC}"
    else
        echo -e "${YELLOW}Running tests...${NC}"
        python run_tests.py
    fi
fi

echo -e "${GREEN}Done!${NC}"