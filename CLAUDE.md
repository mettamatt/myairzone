# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# AirZone HVAC Control System Guide

## Environment
- Python virtual environment location: `/Users/mettamatt/Sites/myairzone/.venv/`
- Activate: `source /Users/mettamatt/Sites/myairzone/.venv/bin/activate`

## Development Commands
- Install dependencies: `pip install -r requirements.txt`
- Install in development mode: `pip install -e .`
- Run tests: `python run_tests.py`
- Run tests with coverage: `python run_tests.py --cov`
- Run tests with HTML coverage: `python run_tests.py --cov --html`
- Run specific test file: `python run_tests.py tests/test_specific.py`

## Application Commands (Unified CLI)
- List all systems and zones: `python airzone_cli.py list`
- Get zone status: `python airzone_cli.py status --system [ID] --zone [ID]`
- Control zone: `python airzone_cli.py control --system [ID] --zone [ID] --power on --setpoint 22`
- Check system errors: `python airzone_cli.py errors`
- Create backup: `python airzone_cli.py backup create`
- List backups: `python airzone_cli.py backup list`
- Validate backup: `python airzone_cli.py backup validate [file]`
- List IAQ sensors: `python airzone_cli.py iaq list`
- Get IAQ sensor status: `python airzone_cli.py iaq status --system [ID] --sensor [ID]`
- Control IAQ sensor: `python airzone_cli.py iaq control --system [ID] --sensor [ID] --ventilation [0|1|2]`
  (Note: IAQ functionality is zone-based; sensor ID = zone ID)

## Architecture Overview (Streamlined)
The codebase has been refactored for better maintainability and reduced duplication:

### Core Modules (src/)
- **client.py**: Core API client (AirzoneClient) - handles HTTP requests and caching
- **system.py**: AirzoneSystem class - manages HVAC systems
- **zone.py**: AirzoneZone class - controls individual zones
- **iaq_sensor.py**: AirzoneIAQSensor class - manages air quality sensors
- **models.py**: Shared constants, enums, and data structures
- **airzone_cache.py**: Smart caching system to reduce API calls
- **airzone_backup.py**: Backup/restore functionality
- **airzone_errors.py**: Centralized error handling and definitions

### CLI (cli/)
- **airzone_cli.py**: Streamlined CLI with command subparsers
- **utils.py**: Reusable utilities (decorators, formatters, helpers)

### Main Entry Point
- **airzone_cli.py**: Wrapper that imports from cli/airzone_cli.py

### Documentation (docs/)
- **airzonelapi_openapi.yaml**: Official Airzone Local API OpenAPI specification

## System Information
- Airzone device located at: `192.168.1.100:3000`
- Device Alias: TestDevice
- MAC Address: 00:11:22:33:44:55
- 4 systems with zones: Salón, Oficina, D. Invitado, D.Carmen, D Principal, D. Max, D Annelise, Distribuido
- **mDNS Support**: Devices can be accessed via .local hostnames (e.g., AZW5GRA052.local)

## API Structure
The API supports both POST (with JSON body) and GET (with query parameters) for data retrieval:
- Version: `POST /api/v1/version` or `GET /api/v1/version`
- Systems: `POST /api/v1/hvac` with `{"systemID": 127}` or `GET /api/v1/hvac?systemid=127`
- Zones: `POST /api/v1/hvac` with `{"systemID": 0, "zoneID": 0}` or `GET /api/v1/hvac?systemid=0&zoneid=0`
- Control: `PUT /api/v1/hvac` with control parameters
- IAQ: `POST /api/v1/iaq` for sensor data or `GET /api/v1/iaq?systemid=1&iaqsensorid=1`
- Integration: `POST /api/v1/integration` for driver info, `PUT /api/v1/integration` to set driver

**IMPORTANT**: The complete Airzone Local API specification is available at `docs/airzonelapi_openapi.yaml` and should be used as the authoritative reference for all API endpoints, parameters, and response formats.

## Key Design Patterns
1. **Modular Structure**: Each entity (Client, System, Zone, IAQSensor) has its own module
2. **Decorator Pattern**: `@handle_cli_errors` for consistent error handling
3. **Factory Functions**: `create_client()` for standardized object creation
4. **Data-Driven Constants**: Modes, error codes, and properties defined in models.py
5. **Caching Strategy**: Automatic caching with invalidation on updates

## Code Optimization Results
- Original monolithic client: 1,158 lines → 5 modules totaling ~837 lines (28% reduction)
- CLI optimization: 745 lines → 486 lines (35% reduction)
- Better organization, maintainability, and extensibility

## Common Operations

### Working with Zones
```python
from src import AirzoneClient, AirzoneSystem

client = AirzoneClient(host="192.168.1.100")
system = AirzoneSystem(client, system_id=1)
zone = system.get_zone(zone_id=1)

# Control zone
zone.on = True
zone.setpoint = 22.5
zone.mode = 2  # Cooling
```

### Error Handling
All commands use the `@handle_cli_errors` decorator for consistent error handling.
Errors are logged and displayed with user-friendly messages.

## Testing Approach
- pytest with responses library for API mocking
- Focus on behavior over implementation
- Test files in tests/ directory
- Run with: `python run_tests.py`
