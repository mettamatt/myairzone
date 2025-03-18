# AirZone Project Guide

## Environment
- Python virtual environment location: `/Users/mettamatt/Sites/myairzone/.venv/`
- Activate: `source /Users/mettamatt/Sites/myairzone/.venv/bin/activate`

## Commands
- Run Python scripts: `python script_name.py`
- Install dependencies: `pip install -r requirements.txt` (if available)
- List all systems and zones: `python control_airzone.py list`
- Get specific zone status: `python control_airzone.py status --system [ID] --zone [ID]`
- Control a zone: `python control_airzone.py control --system [ID] --zone [ID] [options]`
- Monitor all systems: `python monitor_airzone.py`

## Project Structure
- `airzone_client.py`: Core client library for Airzone API communication
- `control_airzone.py`: Command-line tool for viewing and controlling zones
- `monitor_airzone.py`: Tool for monitoring systems and logging changes
- `test_airzone.py`: Simple test script for testing API endpoints

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

## Code Style
- Use Python 3.x conventions
- Prefer explicit error handling with try/except blocks
- Use descriptive variable names
- Document functions with docstrings
- Follow PEP 8 style guidelines

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