# Simplified Testing Approach for AirZone

> **Note**: This document has been updated to reflect the new project structure with `src/`, `cli/`, and `scripts/` directories. The original `control_airzone.py` has been consolidated into `cli/airzone_cli.py`.

## Core Principles

1. Test behaviors, not implementations
2. Focus on critical paths that users care about
3. Write tests that remain valid when implementation details change

## Recommended Testing Tools

For simplicity, standardize on pytest and responses:

```bash
pip install pytest pytest-cov responses
```

## Testing Structure

### 1. Client Behaviors

Test the behaviors of the AirzoneClient:

```python
# test_client_behaviors.py
import pytest
import responses

@responses.activate
def test_client_gets_systems():
    """Test that client can retrieve systems."""
    # Mock external API
    responses.add(
        responses.POST, 
        "http://192.168.1.100:3000/api/v1/hvac",
        json={"systems": [{"systemID": 1}]}, 
        status=200
    )
    
    # Create client
    client = AirzoneClient()
    
    # Test behavior
    systems = client.get_all_systems()
    assert "systems" in systems
    assert len(systems["systems"]) == 1
```

### 2. CLI Workflows

Test complete CLI workflows:

```python
# test_cli_workflows.py
import pytest
import responses
from io import StringIO
from unittest.mock import patch

@responses.activate
def test_list_systems_workflow():
    """Test the workflow of listing systems."""
    # Mock external API
    responses.add(
        responses.POST, 
        "http://192.168.1.100:3000/api/v1/hvac",
        json={"systems": [{"systemID": 1, "name": "Test System"}]}, 
        status=200
    )
    
    # Capture stdout
    with patch('sys.stdout', new=StringIO()) as fake_out:
        # Run CLI command
        with patch('sys.argv', ['airzone_cli.py', 'list']):
            from cli.airzone_cli import main
            main()
        
        # Check output for expected content
        output = fake_out.getvalue()
        assert "Test System" in output
```

### 3. Cache Behaviors

Test cache behaviors:

```python
# test_cache_behaviors.py
import pytest
import tempfile

def test_cache_stores_and_retrieves():
    """Test that cache can store and retrieve data."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create cache
        cache = AirzoneCache(cache_dir=tmpdir)
        
        # Test behavior
        data = {"test": "data"}
        cache.set("test_key", data)
        result = cache.get("test_key")
        
        assert result == data
```

## Running Tests

Run tests with coverage:

```bash
pytest --cov=. tests/ -v
```

## Simplify Test Helpers

Create minimal useful test helpers:

```python
# conftest.py

import pytest
import tempfile

@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir

@pytest.fixture
def test_client():
    """Create a test client."""
    from src.airzone_client import AirzoneClient
    return AirzoneClient(use_cache=False)
```

## Conclusions

1. **Focus on behavior** - Test what the code does, not how it does it
2. **Simplify tooling** - Use one test framework and minimal helpers
3. **Mock external boundaries** - Use responses to mock HTTP calls
4. **Test critical workflows** - Prioritize testing user-facing functionality
5. **Avoid implementation coupling** - Don't test internal methods directly