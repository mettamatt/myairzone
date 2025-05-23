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

The project is organized with a clean directory structure:

```
myairzone/
├── src/                     # Core source code
│   ├── airzone_client.py    # Main API client
│   ├── airzone_cache.py     # Caching system
│   ├── airzone_backup.py    # Backup/restore functionality
│   ├── airzone_errors.py    # Error handling
│   └── __init__.py          # Package initialization
├── cli/                     # Command-line interface
│   └── airzone_cli.py       # Unified CLI
├── scripts/                 # Utility scripts
│   ├── check_errors.py      # Error checking
│   ├── check_system.py      # System validation
│   └── setup_tests.sh       # Test setup
├── tests/                   # Test suite
├── logs/                    # Log files
├── backups/                 # Backup files
└── airzone_cli.py           # Main entry point
```

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

### Option 2: Development Installation
```bash
pip install -e .
```

## Usage (Unified CLI)

The project features a unified command-line interface for all functions:

```bash
python airzone_cli.py [options] COMMAND
```

### Core Commands

1. **List all systems and zones:**
   ```bash
   python airzone_cli.py list
   ```

2. **Get status of a specific zone:**
   ```bash
   python airzone_cli.py status --system 1 --zone 1
   ```

3. **Control a zone:**
   ```bash
   python airzone_cli.py control --system 1 --zone 1 --power on --setpoint 22.5
   ```

4. **Check for system errors:**
   python airzone_cli.py errors
   ```

4. **Validate system configuration:**
   ```bash
   python airzone_cli.py check
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
./setup_tests.sh
```

### Testing Philosophy

1. **Focus on critical paths** - Test what matters most to users
2. **Optimize for maintenance** - Choose patterns that minimize test updates when implementation changes
3. **Strategic coverage** - Aim for high value coverage, not high percentage coverage

## System Details

### Device Information
- Alias: TestDevice
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
from airzone_client import AirzoneClient
from airzone_backup import AirzoneBackup

# Create client
client = AirzoneClient(host="192.168.1.100", port=3000)

# Create backup manager
backup_mgr = AirzoneBackup(client)

# Create a backup
backup_file = backup_mgr.create_backup()
print(f"Backup created: {backup_file}")

# Get system information
systems_data = client.get_all_systems()
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Based on reverse-engineering of the Airzone local API
- Created for system backup, validation and error monitoring purposes