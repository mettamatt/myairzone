# Airzone HVAC Backup & Control System

A streamlined Python toolkit for backing up, monitoring, and controlling Airzone HVAC systems. This project focuses on system discovery, validation, error reporting, and backup/restore functionality.

## Features

- 💾 **Backup & Restore:** Create full system configuration backups and validate them
- 📊 **System Discovery:** Automatically detect all Airzone systems and zones
- 🚨 **Error Monitoring:** Check for and report system errors with detailed diagnostics
- 🌡 **System Validation:** Verify systems against expected configuration
- 🚀 **Caching System:** Reduce API calls with intelligent local caching
- 🧪 **Robust Testing:** Comprehensive unit tests following best practices
- ⚡ **Zone Control:** Control individual zones (power, temperature, mode)

## Project Structure

The project is organized with a clean, modular structure:

```
myairzone/
├── src/                     # Core source code (modular design)
│   ├── client.py            # API client for HTTP requests
│   ├── system.py            # AirzoneSystem class
│   ├── zone.py              # AirzoneZone class
│   ├── iaq_sensor.py        # AirzoneIAQSensor class
│   ├── models.py            # Shared constants and data structures
│   ├── airzone_cache.py     # Caching system
│   ├── airzone_backup.py    # Backup/restore functionality
│   ├── airzone_errors.py    # Error handling
│   └── __init__.py          # Package initialization
├── cli/                     # Command-line interface
│   ├── airzone_cli.py       # Streamlined CLI with subcommands
│   └── utils.py             # CLI utilities and decorators
├── scripts/                 # Utility scripts
│   ├── check_errors.py      # Error checking
│   ├── check_system.py      # System validation
│   └── setup_tests.sh       # Test setup
├── tests/                   # Test suite
├── logs/                    # Log files
├── backups/                 # Backup files
└── airzone_cli.py           # Main entry point
```

## Requirements

- **Python 3.7+** (tested with Python 3.8-3.13)
- **Virtual environment** (recommended)
- **Network access** to your Airzone device
- **Dependencies** (installed automatically):
  - `requests>=2.28.0` - HTTP client for API communication
  - `pytest>=7.4.0` - Testing framework (development)
  - `pytest-cov>=4.1.0` - Coverage reporting (development)
  - `responses>=0.23.0` - HTTP mocking for tests (development)

## Installation

### Option 1: Standard Installation

1. Clone this repository and create a virtual environment:

   ```bash
   git clone https://github.com/yourusername/myairzone.git
   cd myairzone
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

2. Install required packages:

   ```bash
   pip install -r requirements.txt
   ```

3. Configure your Airzone device:
   ```bash
   cp .env.example .env
   # Edit .env with your device's IP address
   ```

### Option 2: Development Installation

For developers who want to make changes to the code:

```bash
# Clone and navigate to the project
git clone https://github.com/mettamatt/myairzone.git
cd myairzone

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install in development mode
pip install -e .

# Configure your device
cp .env.example .env
# Edit .env with your device's IP address
```

## Quick Start

After installation, you can immediately start using the CLI:

```bash
# Activate virtual environment
source .venv/bin/activate

# Check if your Airzone device is accessible
python airzone_cli.py --help

# List all systems and zones
python airzone_cli.py list

# Get status of a specific zone
python airzone_cli.py status --system 1 --zone 1

# Create a backup of your current configuration
python airzone_cli.py backup create
```

## Usage (Unified CLI)

The project features a unified command-line interface for all functions. There are multiple ways to run it:

### Method 1: Main Entry Point (Recommended)

```bash
python airzone_cli.py [options] COMMAND
```

### Method 2: Direct CLI Script

```bash
python cli/airzone_cli.py [options] COMMAND
```

### Method 3: After Development Installation

```bash
airzone [options] COMMAND
```

**Note:** Make sure your virtual environment is activated before running any commands:

```bash
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### Core Commands

1. **List all systems and zones:**

   ```bash
   python airzone_cli.py list
   ```

2. **Get status of a specific zone:**

   ```bash
   # Get human-readable status
   python airzone_cli.py status --system 1 --zone 1

   # Get JSON output for scripting
   python airzone_cli.py status --system 1 --zone 1 --json
   ```

3. **Control a zone:**

   ```bash
   # Turn on a zone and set temperature
   python airzone_cli.py control --system 1 --zone 1 --power on --setpoint 22.5

   # Change mode to cooling
   python airzone_cli.py control --system 1 --zone 1 --mode 2

   # Turn off a zone
   python airzone_cli.py control --system 1 --zone 1 --power off

   # Multiple changes at once
   python airzone_cli.py control --system 1 --zone 1 --power on --setpoint 23 --mode 3
   ```

   **Available modes:**

   - `1`: Stop
   - `2`: Cooling
   - `3`: Heating
   - `4`: Ventilation
   - `5`: Dehumidify

4. **Check for system errors:**

   ```bash
   python airzone_cli.py errors
   ```

5. **Validate system configuration:**

   ```bash
   python airzone_cli.py check

   # Get JSON output
   python airzone_cli.py check --json
   ```

### Backup & Restore

The backup system provides comprehensive tools for configuration management:

```bash
# Create a new backup
python airzone_cli.py backup create

# List available backups
python airzone_cli.py backup list

# Validate a backup file
python airzone_cli.py backup validate backups/airzone_backup_20250317_123045.json

# Preview a restore operation (dry run)
python airzone_cli.py backup restore backups/airzone_backup_20250317_123045.json --dry-run
```

### Utility Scripts

You can also run utility scripts directly:

```bash
# Check for system errors
python scripts/check_errors.py

# Validate system configuration
python scripts/check_system.py

# Run with different host
AIRZONE_IP=YOUR_AIRZONE_IP python scripts/check_errors.py
```

### Global Options

The following options can be used with any command:

```bash
--host IP        # Specify Airzone host IP (default: 192.168.1.100)
--port PORT      # Specify API port (default: 3000)
--no-cache       # Disable caching
--force-refresh  # Force refresh from API
```

## Testing

The project includes a comprehensive test suite with both unittest and pytest frameworks:

```bash
# Run all tests with our simplified test runner
python run_tests.py

# Generate coverage report
python run_tests.py --cov

# Generate HTML coverage report
python run_tests.py --cov --html

# Run tests on a specific path
python run_tests.py tests/test_implementation_resilient.py

# Legacy test script (includes additional setup)
./scripts/setup_tests.sh
```

### Testing Philosophy

1. **Focus on critical paths** - Test what matters most to users
2. **Optimize for maintenance** - Choose patterns that minimize test updates when implementation changes
3. **Strategic coverage** - Aim for high value coverage, not high percentage coverage

## System Details

### Device Information

- Alias: YOUR_DEVICE_ALIAS
- MAC Address: 00:11:22:33:44:55
- IP Address: 192.168.1.100
- Port: 3000

### System Overview

1. **System 1**

   - Zone: Salón

2. **System 2**

   - Zones: Oficina, D. Invitado, D.Carmen
   - Known Issue: "IU error CONF" - Indoor Unit configuration error

3. **System 3**

   - Zone: D Principal
   - Known Issue: "Error 9" - Gateway-System communication error

4. **System 4**
   - Zones: D. Max, D Annelise, Distribuido

## Error Information

The system identifies and reports these known error types:

- **Error 9**: Gateway-System communication error. The system loses communication with the AC unit.
- **Error 12**: Communication error between Airzone Cloud Webserver - system.
- **IU error CONF**: Indoor Unit configuration error.

Note: Remote restart is NOT possible via the API with this Airzone model (firmware 4.12).
For persistent issues, a physical restart of the Airzone hardware is required.

## API Client Usage

For custom applications, you can use the client library directly:

```python
from src.client import AirzoneClient
from src.system import AirzoneSystem
from src.zone import AirzoneZone
from src.airzone_backup import AirzoneBackup

# Create client
client = AirzoneClient(host="192.168.1.100", port=3000)

# Create backup manager
backup_mgr = AirzoneBackup(client)

# Create a backup
backup_file = backup_mgr.create_backup()
print(f"Backup created: {backup_file}")

# Get system information
systems_data = client.get_all_systems()

# Control a zone
system = AirzoneSystem(client, system_id=1)
zone = system.get_zone(zone_id=1)
zone.setpoint = 22.5  # Set temperature
zone.turn_on()        # Turn on the zone
```

## Troubleshooting

### Common Issues

1. **ModuleNotFoundError: No module named 'requests'**

   ```bash
   # Make sure virtual environment is activated
   source .venv/bin/activate

   # Install dependencies
   pip install -r requirements.txt
   ```

2. **ImportError: No module named 'src'**

   ```bash
   # Make sure you're in the project root directory
   cd /path/to/myairzone

   # Run from the project root
   python airzone_cli.py --help
   ```

3. **Connection refused or timeout**

   ```bash
   # Check if Airzone device is accessible
   ping YOUR_AIRZONE_IP

   # Use different host/port
   python airzone_cli.py --host YOUR_AIRZONE_IP --port 3000 list
   ```

4. **Permission denied on scripts**
   ```bash
   # Make scripts executable
   chmod +x scripts/setup_tests.sh
   ```

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Based on reverse-engineering of the Airzone local API
- Created for system backup, validation and error monitoring purposes
