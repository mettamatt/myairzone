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

## Architecture Overview
- **src/airzone_client.py**: Core API client with zone control classes (AirzoneClient, AirzoneSystem, AirzoneZone)
- **src/airzone_cache.py**: Smart caching system to reduce API calls
- **src/airzone_backup.py**: Backup/restore functionality for system configurations
- **src/airzone_errors.py**: Centralized error handling and definitions
- **cli/airzone_cli.py**: Unified command-line interface for all operations
- **airzone_cli.py**: Main entry point (wrapper around cli/airzone_cli.py)
- **run_tests.py**: Custom test runner with coverage support
- **setup.py**: Package configuration with console script entry point

## System Information
- Airzone device located at: `192.168.1.100:3000`
- Device Alias: TestDevice
- MAC Address: 00:11:22:33:44:55
- 4 systems with multiple zones including Salón, Oficina, D. Invitado, D.Carmen, etc.

## API Notes
- All API requests are POST requests with JSON payloads
- Main endpoints:
  - Version: `POST /api/v1/version`
  - Systems: `POST /api/v1/hvac` with `{"systemID": 127}`
  - Zones: `POST /api/v1/hvac` with `{"systemID": 0, "zoneID": 0}`
  - Specific System: `POST /api/v1/hvac` with `{"systemID": [ID]}`
  - Specific Zone: `POST /api/v1/hvac` with `{"systemID": [ID], "zoneID": [ID]}`
  - Webserver: `POST /api/v1/webserver`
  - Control: `POST /api/v1/hvac` with parameters like `{"systemID": [ID], "zoneID": [ID], "on": 1, "setpoint": 22}`

## Zone Control Options
- Power on/off: `"on": 1` or `"on": 0`
- Temperature: `"setpoint": 22`
- Mode: `"mode": [ID]` where ID is:
  1. Stop
  2. Cooling
  3. Heating
  4. Ventilation
  5. Dehumidify

## Code Architecture Patterns
- **Client-System-Zone hierarchy**: AirzoneClient → AirzoneSystem → AirzoneZone classes
- **Caching strategy**: Local file cache in logs/ directory with TTL and validation
- **Error handling**: Custom exception classes in airzone_errors.py with specific error codes
- **Backup format**: JSON-based configuration snapshots with validation
- **Testing approach**: pytest with responses library for API mocking, focus on resilient tests
- **CLI design**: Single entry point with subcommands for different operations

## Known Issues
- System 2 has an "IU error CONF" error - Indoor Unit configuration error
- System 3 has an "Error 9" error - Gateway-System communication error
- Altherma parameters endpoint returns a 500 error (not supported by this installation)

## Error Codes
- **Error 9**: Gateway-System communication error. The system loses communication with the AC unit. The system will open all the zones and deactivate the control from the controllers, only allowing the operation of the unit from the controller of its manufacturer.
- **Error 12**: Communication error between Airzone Cloud Webserver - system. The system loses communication with the Webserver. Check that the Webserver is correctly connected to the Control board's automation bus.
- **IU error CONF**: Indoor Unit configuration error. There might be a mismatch in the configuration between the Airzone system and the indoor unit.

## Troubleshooting Notes
- Remote restart is NOT possible via the API with this Airzone model (firmware 4.12)
- Attempted methods that do not work:
  - PUT request to '/integration' with {'reboot': True}
  - GET request to '/reboot'
  - PUT request to '/webserver' to update settings
  - Toggling zone states
  - Various session reset endpoints
- Physical intervention required to resolve errors:
  1. Power cycle the Airzone webserver hardware
  2. Check physical connections between components
  3. Power cycle the affected AC units