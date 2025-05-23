# Airzone HVAC Backup & Control System

A streamlined Python toolkit for backing up, monitoring, and controlling Airzone HVAC systems.

## Quick Usage

Activate your virtual environment first:
```bash
source .venv/bin/activate
```

**list** - Lists all systems and zones (no additional options)
```bash
python airzone_cli.py list
```

**status** - Gets status of a specific zone
- Requires: --system [ID] and --zone [ID]  
- Optional: --json for JSON output
```bash
python airzone_cli.py status --system 1 --zone 1
python airzone_cli.py status --system 1 --zone 1 --json
```

**control** - Controls a specific zone
- Requires: --system [ID] and --zone [ID]
- Optional: --power {on,off}, --setpoint [temp], --mode {1-5}
- Modes: 1=stop, 2=cooling, 3=heating, 4=ventilation, 5=dehumidify
```bash
python airzone_cli.py control --system 1 --zone 1 --power on --setpoint 22
python airzone_cli.py control --system 1 --zone 1 --mode 2
```

**errors** - Checks for errors in all systems (no additional options)
```bash
python airzone_cli.py errors
```

**check** - Checks systems against expected configuration
- Optional: --json for JSON output
```bash
python airzone_cli.py check
python airzone_cli.py check --json
```

**backup** - Backup operations with subcommands:
- create - Create a new backup
- list - List available backups  
- validate - Validate a backup file
- restore - Restore from a backup
```bash
python airzone_cli.py backup create
python airzone_cli.py backup list
python airzone_cli.py backup validate [file]
python airzone_cli.py backup restore [file]
```

**iaq** - Indoor Air Quality sensor operations:
- list - List all IAQ sensors
- status - Get IAQ sensor status (requires --system [ID] --sensor [ID])
- control - Control IAQ sensor (requires --system [ID] --sensor [ID] --ventilation [0|1|2])
```bash
python airzone_cli.py iaq list
python airzone_cli.py iaq status --system 1 --sensor 1
python airzone_cli.py iaq control --system 1 --sensor 1 --ventilation 2
```

## Features

- 💾 **Backup & Restore:** Create full system configuration backups and validate them
- 📊 **System Discovery:** Automatically detect all Airzone systems and zones
- 🚨 **Error Monitoring:** Check for and report system errors with detailed diagnostics
- 🌡 **System Validation:** Verify systems against expected configuration
- 🚀 **Caching System:** Reduce API calls with intelligent local caching
- 🧪 **Robust Testing:** Comprehensive unit tests following best practices
- ⚡ **Zone Control:** Control individual zones (power, temperature, mode)


## Installation

1. Clone and setup:
   ```bash
   git clone https://github.com/yourusername/myairzone.git
   cd myairzone
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. Test connection:
   ```bash
   python airzone_cli.py list
   ```

## Global Options

```bash
--host IP        # Specify Airzone host IP (default: 192.168.1.100)
--port PORT      # Specify API port (default: 3000)
--no-cache       # Disable caching
--force-refresh  # Force refresh from API
```

## Testing

```bash
python run_tests.py
```

## Troubleshooting

**Connection issues:** Check if your Airzone device is accessible:
```bash
ping YOUR_AIRZONE_IP
python airzone_cli.py --host YOUR_AIRZONE_IP list
```

**Module errors:** Make sure virtual environment is activated and dependencies installed:
```bash
source .venv/bin/activate
pip install -r requirements.txt
```
