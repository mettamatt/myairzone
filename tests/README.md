# AirZone Testing Strategy

## Running the Tests

To run all tests:

```bash
python run_tests.py
```

To run tests with coverage reporting:

```bash
python run_tests.py --cov
```

To run tests with HTML coverage report:

```bash
python run_tests.py --cov --html
```

## Current Test Status

The test suite includes a mix of unit tests and integration tests:

- Implementation-resilient tests (`test_implementation_resilient.py`): 5 tests, all passing
- CLI behavior tests (`test_cli_behavior.py`): 5 tests, 3 passing, 2 skipped

The skipped tests need further development to handle mocking of the AirzoneZone properties and system error simulation. These will be implemented in a future update.

## Core Testing Philosophy

1. **Focus on critical paths** - Test what matters most to users
2. **Optimize for maintenance** - Choose patterns that minimize test updates when implementation changes
3. **Strategic coverage** - Aim for high value coverage, not high percentage coverage

## Implementation-Resilient Testing Patterns

### 1. Test Behaviors, Not Implementations

Good:
```python
# Testing that a zone can be turned on (a behavior)
def test_zone_can_be_turned_on():
    client = create_test_client()
    zone = get_test_zone(client, 1, 1)
    
    # Starting state
    zone.turn_off()
    assert not zone.is_on
    
    # Action
    zone.turn_on()
    
    # Verification
    assert zone.is_on
```

Avoid:
```python
# Testing implementation details
def test_zone_turn_on_calls_set_parameters_with_correct_arguments():
    # Too coupled to implementation details
    mock_client = Mock()
    zone = AirzoneZone(mock_client, 1, 1, {"on": 0})
    
    zone.turn_on()
    
    mock_client.set_zone_parameters.assert_called_once_with(1, 1, {"on": 1})
```

### 2. Use Higher-Level Assertions

Good:
```python
# Testing the ability to control a zone (outcome focused)
def test_zone_control_changes_temperature():
    # Setup system with test client
    client = create_test_client()
    
    # Execute control operation
    result = control_zone(client, 1, 1, setpoint=23.5)
    
    # Verify the outcome matters (not implementation details)
    assert result.success
    assert result.new_setpoint == 23.5
```

### 3. Mock at System Boundaries

Good:
```python
# Mocking the HTTP layer, not implementation details
@responses.activate
def test_client_gets_system_information():
    # Mock HTTP response at system boundary
    responses.add(
        responses.POST, 
        "http://test-host:3000/api/v1/hvac",
        json={"systems": [{"systemID": 1, "name": "Test System"}]}, 
        status=200
    )
    
    # Test client with real HTTP library but mocked responses
    client = AirzoneClient(host="test-host", port=3000)
    systems = client.get_all_systems()
    
    assert len(systems["systems"]) == 1
    assert systems["systems"][0]["name"] == "Test System"
```

### 4. Test Contract, Not Implementation

Good:
```python
# Test the contract (public API) of the cache
def test_cache_contract():
    cache = AirzoneCache(cache_dir=temp_dir)
    test_data = {"key": "value"}
    
    # Contract: cache.set() stores data that cache.get() can retrieve
    assert cache.set("test_key", test_data)
    assert cache.get("test_key") == test_data
    
    # Contract: cache.invalidate() makes data not retrievable
    assert cache.invalidate("test_key")
    assert cache.get("test_key") is None
```

### 5. Use Functional Tests for Workflows

Good:
```python
# Test a full workflow rather than individual methods
def test_control_workflow():
    # Setup
    client = create_test_client()
    
    # Initial state check
    systems = list_systems(client)
    assert systems[0].zones[1].is_on
    
    # Change state
    control_zone(client, 1, 1, power="off")
    
    # Verify changed state
    systems = list_systems(client)
    assert not systems[0].zones[1].is_on
```

## Test Organization

1. **Unit Tests**: Focus on core components in isolation
2. **Integration Tests**: Test how components work together
3. **Functional Tests**: Test complete workflows from user perspective

## Prioritizing Tests

For maximum value with minimum maintenance:

1. Test error handling and recovery extensively
2. Test cache behavior (expiry, invalidation, retrieval)
3. Test critical workflows for controlling zones and systems
4. Test parameter validation and boundary conditions

Always focus on testing the *WHAT*, not the *HOW*.