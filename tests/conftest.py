"""
Test configuration file for pytest.

This file contains fixtures and configuration for the pytest test suite.
Focusing on behavior testing rather than implementation details.
"""

import pytest
import tempfile
import os
import json
from unittest.mock import MagicMock

# Sample test data
@pytest.fixture
def mock_system_data():
    """Sample system data for tests."""
    return {
        "systemID": 1,
        "manufacturer": "Test Manufacturer",
        "system_firmware": "1.0",
        "name": "Test System"
    }

@pytest.fixture
def mock_zone_data():
    """Sample zone data for tests."""
    return {
        "systemID": 1,
        "zoneID": 1,
        "id": 1,
        "name": "Test Zone",
        "on": 1,
        "roomTemp": 22.5,
        "setpoint": 23.0,
        "humidity": 45,
        "mode": 3
    }

@pytest.fixture
def mock_version_data():
    """Sample version data for tests."""
    return {"version": "1.0"}

@pytest.fixture
def mock_webserver_data():
    """Sample webserver data for tests."""
    return {
        "ws_firmware": "4.12",
        "mac": "00:11:22:33:44:55",
        "alias": "TestDevice"
    }

@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir

@pytest.fixture
def create_test_client():
    """Create a test client factory function."""
    def _create_client(host="test-host", port=3000, use_cache=False):
        import sys
        import os
        sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
        from src.client import AirzoneClient
        return AirzoneClient(host=host, port=port, use_cache=use_cache)
    return _create_client

@pytest.fixture
def mock_cli_environment():
    """Mock CLI environment to use test values instead of real .env config."""
    from unittest.mock import patch
    
    # Test configuration
    TEST_HOST = "192.168.1.100"
    TEST_PORT = 3000
    
    with patch('cli.airzone_cli.DEFAULT_HOST', TEST_HOST), \
         patch('cli.airzone_cli.DEFAULT_PORT', TEST_PORT):
        yield TEST_HOST, TEST_PORT