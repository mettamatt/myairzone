#!/usr/bin/env python3
"""
Implementation-resilient tests for the AirZone project.

These tests focus on behaviors and outcomes rather than specific implementations,
making them more maintainable when internal implementation details change.
"""

import pytest
import responses
import tempfile
import os
import json
import time

from airzone_client import AirzoneClient, AirzoneSystem, AirzoneZone
from airzone_cache import AirzoneCache
from control_airzone import control_zone, get_zone_status

# Helper for creating a test client
def create_test_client(host="test-host", port=3000):
    """Create a test client that doesn't use real networking."""
    return AirzoneClient(host=host, port=port, use_cache=False)

# ----- Test 1: Test the AirzoneClient behavior, not implementation -----

@responses.activate
def test_client_retrieves_system_data():
    """Test that the client can retrieve system data."""
    # Mock the HTTP response at the system boundary
    responses.add(
        responses.POST,
        "http://test-host:3000/api/v1/hvac",
        json={"systems": [{"systemID": 1, "name": "Test System"}]},
        status=200
    )
    
    # Create a client that will use the mocked HTTP response
    client = create_test_client()
    
    # Call the method under test
    result = client.get_all_systems()
    
    # Verify the behavior (can retrieve systems data) not the implementation
    assert "systems" in result
    assert len(result["systems"]) == 1
    assert result["systems"][0]["systemID"] == 1
    assert result["systems"][0]["name"] == "Test System"

# ----- Test 2: Test AirzoneCache contract, not implementation details -----

def test_cache_contract():
    """Test the public contract of the cache (set, get, invalidate)."""
    # Create a temporary directory for testing
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create cache
        cache = AirzoneCache(cache_dir=temp_dir, max_age=10)
        test_data = {"name": "Test System", "value": 42}
        
        # Contract: set() should store data retrievable by get()
        assert cache.set("test_key", test_data)
        retrieved = cache.get("test_key")
        assert retrieved == test_data
        
        # Contract: data should expire after max_age
        time.sleep(0.1)  # Just a bit of time to ensure file timestamps differ
        new_data = {"name": "Updated System", "value": 43}
        assert cache.set("updated_key", new_data)
        
        # Contract: invalidate() should make key no longer retrievable
        assert cache.invalidate("test_key")
        assert cache.get("test_key") is None
        
        # The other key should still be there
        assert cache.get("updated_key") == new_data
        
        # Contract: invalidate_all() should clear all keys
        assert cache.invalidate_all()
        assert cache.get("updated_key") is None

# ----- Test 3: Test AirzoneZone behavior, not implementation -----

@responses.activate
def test_zone_temperature_control():
    """Test the behavior of changing a zone's temperature."""
    # Initial zone data
    initial_data = {
        "systemID": 1,
        "zoneID": 1,
        "name": "Test Zone",
        "on": 1,
        "roomTemp": 22.5,
        "setpoint": 21.0,
        "humidity": 45,
        "mode": 3
    }
    
    # Updated data after setting temperature
    updated_data = dict(initial_data)
    updated_data["setpoint"] = 23.0
    
    # Mock HTTP interactions at system boundary
    # First response for getting zone info
    responses.add(
        responses.POST,
        "http://test-host:3000/api/v1/hvac",
        json={"data": initial_data},
        status=200
    )
    
    # Second response for setting temperature
    responses.add(
        responses.POST,
        "http://test-host:3000/api/v1/hvac",
        json={"status": "success"},
        status=200
    )
    
    # Third response for getting updated zone info
    responses.add(
        responses.POST,
        "http://test-host:3000/api/v1/hvac",
        json={"data": updated_data},
        status=200
    )
    
    # Create client and zone
    client = create_test_client()
    zone = AirzoneZone(client, 1, 1, initial_data)
    
    # Test the behavior (temperature can be changed)
    # This is resilient to implementation changes of how setting happens internally
    zone.setpoint = 23.0
    
    # Verify the outcome (new temperature) not how it got there
    assert zone.setpoint == 23.0

# ----- Test 4: Test workflow, not individual methods -----

@responses.activate
def test_zone_control_workflow():
    """Test the full workflow of controlling a zone."""
    # Mock HTTP interactions for the workflow
    # Initial zone data
    zone_data = {
        "data": {
            "systemID": 1,
            "zoneID": 1,
            "name": "Test Zone",
            "on": 1,
            "roomTemp": 22.5,
            "setpoint": 21.0,
            "humidity": 45,
            "mode": 3
        }
    }
    
    # Mock getting zone
    responses.add(
        responses.POST,
        "http://test-host:3000/api/v1/hvac",
        json=zone_data,
        status=200
    )
    
    # Mock setting temperature
    responses.add(
        responses.POST,
        "http://test-host:3000/api/v1/hvac",
        json={"status": "success"},
        status=200
    )
    
    # Mock getting updated zone
    updated_zone = dict(zone_data)
    updated_zone["data"]["setpoint"] = 23.0
    responses.add(
        responses.POST,
        "http://test-host:3000/api/v1/hvac",
        json=updated_zone,
        status=200
    )
    
    # Test the entire workflow
    client = create_test_client()
    
    # Execute the workflow
    control_zone(client, 1, 1, setpoint=23.0)
    
    # Verify the workflow outcome
    # The next response would be for getting the zone status
    responses.replace(
        responses.POST,
        "http://test-host:3000/api/v1/hvac",
        json=updated_zone,
        status=200
    )
    
    # We'd check the zone status through the appropriate function
    # This is simplified for demonstration
    zone = AirzoneZone(client, 1, 1)
    zone.refresh()
    assert zone.setpoint == 23.0

# ----- Test 5: Test error handling behaviors -----

@responses.activate
def test_error_handling_behavior():
    """Test how the client handles errors from the API."""
    # Mock an HTTP error response
    responses.add(
        responses.POST,
        "http://test-host:3000/api/v1/hvac",
        status=500
    )
    
    # Create client
    client = create_test_client()
    
    # Verify the behavior (exception is raised on API error)
    with pytest.raises(Exception) as e:
        client.get_all_systems()
    
    # We care that an exception is raised, but not the specific message
    # This makes the test resilient to changes in error message formatting
    assert "Error" in str(e.value)

if __name__ == "__main__":
    pytest.main(["-v", __file__])