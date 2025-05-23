#!/usr/bin/env python3
"""Streamlined Airzone CLI with reduced duplication."""

import argparse
import sys
import os
import json
import time
import logging
from datetime import datetime
from typing import Optional

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.client import AirzoneClient
from src.system import AirzoneSystem
from src.zone import AirzoneZone
from src.iaq_sensor import AirzoneIAQSensor
from src.airzone_backup import AirzoneBackup
from src.airzone_errors import print_error_details

from scripts.check_system import check_systems
from scripts.check_errors import check_system_errors

# Import our utilities
from .utils import handle_cli_errors, print_json_or_text, format_entity_info, create_client

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("airzone_cli")

# Load environment variables
def load_env_vars():
    """Load environment variables from .env file."""
    env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
    env_vars = {}
    
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key.strip()] = value.strip()
    
    return env_vars

# Load environment variables
env_vars = load_env_vars()

# Default connection values
DEFAULT_HOST = env_vars.get("AIRZONE_IP", "192.168.1.100")
DEFAULT_PORT = int(env_vars.get("AIRZONE_PORT", "3000"))


@handle_cli_errors
def list_systems(client: AirzoneClient, force_refresh: bool = False, json_output: bool = False):
    """List all systems and zones."""
    # Show connection status
    print(f"\n--- Connection Status ---")
    print(f"Host: {client.host}:{client.port}")
    
    # Test connectivity
    start_time = time.time()
    version_data = client.get_version()
    response_time = time.time() - start_time
    print(f"Status: Connected (response time: {response_time:.2f}s)")
    
    # Get webserver info
    webserver_info = client.get_webserver_info()
    if webserver_info:
        interface = webserver_info.get('interface', 'unknown')
        print(f"Interface: {interface}")
        
        if interface == 'wifi':
            wifi_rssi = webserver_info.get('wifi_rssi')
            wifi_quality = webserver_info.get('wifi_quality')
            wifi_channel = webserver_info.get('wifi_channel')
            
            if wifi_rssi is not None:
                wifi_info = f"{wifi_rssi} dBm"
                if wifi_quality and wifi_quality > 0:
                    wifi_info += f" ({wifi_quality}%)"
                if wifi_channel and wifi_channel > 0:
                    wifi_info += f" Ch{wifi_channel}"
                print(f"WiFi: {wifi_info}")
    
    if 'webserver' in version_data:
        print(f"Device: {version_data['webserver'].get('alias', 'Unknown')}")
    
    # Get all systems
    systems_data = client.get_all_systems(force_refresh=force_refresh)
    
    if json_output:
        print_json_or_text(systems_data, as_json=True)
        return
    
    if "systems" not in systems_data:
        print("No systems found")
        return
    
    print("\n--- Available Systems ---")
    
    for system_data in systems_data["systems"]:
        system_id = system_data.get("systemID")
        if system_id is None:
            continue
            
        system = AirzoneSystem(client, system_id, system_data)
        system.load_zones(force_refresh)
        
        print(f"\n{system.name}")
        print(f"  System ID: {system.system_id}")
        print(f"  Manufacturer: {system.manufacturer}")
        print(f"  Firmware: {system.firmware}")
        
        if system.has_errors:
            print(f"  Errors: {system.errors}")
            for error in system.errors:
                if isinstance(error, dict):
                    error_code = error.get("error", {}).get("code", "Unknown") if isinstance(error.get("error"), dict) else str(error.get("error", "Unknown"))
                else:
                    error_code = str(error)
                print(f"    Error Code: {error_code}")
        
        # Show zones
        for zone in system.all_zones.values():
            print(format_entity_info(zone, "Zone"))


@handle_cli_errors
def get_zone_status(client: AirzoneClient, system_id: int, zone_id: int, 
                   json_output: bool = False, force_refresh: bool = False):
    """Get status of a specific zone."""
    zone_data = client.get_zone(system_id, zone_id, force_refresh)
    
    if json_output:
        print_json_or_text(zone_data, as_json=True)
        return
    
    if "data" not in zone_data or not zone_data["data"]:
        print(f"Zone {zone_id} not found in system {system_id}")
        return
    
    zone = AirzoneZone(client, system_id, zone_id, zone_data["data"][0])
    print(format_entity_info(zone, "Zone"))
    
    if zone._data.get("errors"):
        print(f"  Errors: {zone._data['errors']}")


@handle_cli_errors
def control_zone(client: AirzoneClient, system_id: int, zone_id: int, **params):
    """Control a specific zone with various parameters.
    
    Args:
        client: AirzoneClient instance
        system_id: System ID
        zone_id: Zone ID
        **params: Control parameters (power, setpoint, mode, etc.)
    """
    # Get zone
    system = AirzoneSystem(client, system_id)
    zone = system.get_zone(zone_id)
    
    if zone is None:
        print(f"Zone {zone_id} not found in System {system_id}")
        return
    
    print(f"Controlling zone: {zone.name} (System {system_id}, Zone {zone_id})")
    print(f"Initial state: {zone.room_temp}°C, Setpoint {zone.setpoint}°C, "
          f"Mode {zone.mode_name}, Power {'On' if zone.is_on else 'Off'}")
    
    # Track changes
    changes = []
    
    # Power control
    if params.get('power'):
        power_on = params['power'].lower() == 'on'
        if power_on != zone.is_on:
            zone.on = power_on
            changes.append(f"Power: {'Off -> On' if power_on else 'On -> Off'}")
    
    # Temperature setpoint
    if params.get('setpoint') is not None:
        if params['setpoint'] != zone.setpoint:
            old_setpoint = zone.setpoint
            zone.setpoint = params['setpoint']
            changes.append(f"Setpoint: {old_setpoint}°C -> {params['setpoint']}°C")
    
    # Mode
    if params.get('mode') is not None:
        if params['mode'] != zone.mode:
            old_mode = zone.mode_name
            zone.mode = params['mode']
            changes.append(f"Mode: {old_mode} -> {zone.mode_name}")
    
    # Fan speed
    if params.get('fan_speed') is not None:
        if params['fan_speed'] != zone.fan_speed:
            old_speed = zone.fan_speed
            zone.fan_speed = params['fan_speed']
            changes.append(f"Fan Speed: {old_speed} -> {params['fan_speed']}")
    
    # Sleep timer
    if params.get('sleep') is not None:
        if params['sleep'] != zone.sleep_timer:
            old_sleep = zone.sleep_timer
            zone.sleep_timer = params['sleep']
            changes.append(f"Sleep Timer: {old_sleep} min -> {params['sleep']} min")
    
    # Report changes
    if changes:
        print("\nChanges applied:")
        for change in changes:
            print(f"  {change}")
        
        # Refresh and show final state
        zone.refresh(force_refresh=True)
        print(f"\nFinal state: {zone.room_temp}°C, Setpoint {zone.setpoint}°C, "
              f"Mode {zone.mode_name}, Power {'On' if zone.is_on else 'Off'}")
    else:
        print("\nNo changes applied")


@handle_cli_errors
def check_errors_command(client: AirzoneClient):
    """Check for system errors."""
    from scripts.check_errors import check_system_errors
    check_system_errors()


@handle_cli_errors
def check_system_command(client: AirzoneClient, json_output: bool = False):
    """Check system configuration."""
    check_systems(client, json_output)


@handle_cli_errors
def list_iaq_sensors(client: AirzoneClient, force_refresh: bool = False):
    """List all IAQ sensors (zones with air quality capability)."""
    zones_data = client.get_all_zones(force_refresh)
    
    if "systems" not in zones_data:
        print("No systems found")
        return
    
    iaq_zones = []
    for system in zones_data["systems"]:
        if "data" in system:
            for zone_data in system["data"]:
                # Check if this zone has air quality parameters
                if any(key.startswith("aq_") for key in zone_data.keys()):
                    system_id = zone_data.get("systemID")
                    zone_id = zone_data.get("zoneID")
                    if system_id is not None and zone_id is not None:
                        # Create IAQ sensor using zone data (sensor_id = zone_id)
                        sensor = AirzoneIAQSensor(client, system_id, zone_id, zone_data)
                        iaq_zones.append(sensor)
    
    if not iaq_zones:
        print("No IAQ sensors found")
        return
    
    print("\n--- IAQ Sensors ---")
    for sensor in iaq_zones:
        print(format_entity_info(sensor, "IAQ Sensor"))


@handle_cli_errors
def get_iaq_sensor_status(client: AirzoneClient, system_id: int, sensor_id: int, 
                         force_refresh: bool = False):
    """Get status of a specific IAQ sensor (zone with air quality capability)."""
    # Get zone data (sensor_id maps to zone_id)
    zone_data = client.get_zone(system_id, sensor_id, force_refresh)
    
    if "data" not in zone_data or not zone_data["data"]:
        print(f"Zone {sensor_id} not found in system {system_id}")
        return
    
    zone_info = zone_data["data"][0]
    
    # Check if this zone has air quality parameters
    if not any(key.startswith("aq_") for key in zone_info.keys()):
        print(f"Zone {sensor_id} in system {system_id} does not have air quality capability")
        return
    
    sensor = AirzoneIAQSensor(client, system_id, sensor_id, zone_info)
    print(format_entity_info(sensor, "IAQ Sensor"))


@handle_cli_errors
def control_iaq_sensor(client: AirzoneClient, system_id: int, sensor_id: int, 
                      ventilation_mode: Optional[int] = None):
    """Control an IAQ sensor (zone air quality settings)."""
    # Get zone data first (sensor_id maps to zone_id)
    zone_data = client.get_zone(system_id, sensor_id, False)
    
    if "data" not in zone_data or not zone_data["data"]:
        print(f"Zone {sensor_id} not found in system {system_id}")
        return
    
    zone_info = zone_data["data"][0]
    
    # Check if this zone has air quality parameters
    if not any(key.startswith("aq_") for key in zone_info.keys()):
        print(f"Zone {sensor_id} in system {system_id} does not have air quality capability")
        return
    
    sensor = AirzoneIAQSensor(client, system_id, sensor_id, zone_info)
    
    print(f"Controlling IAQ sensor: {sensor.name}")
    print(f"Initial air quality mode: {sensor.ventilation_mode_name}")
    
    if ventilation_mode is not None:
        old_mode = sensor.ventilation_mode_name
        sensor.ventilation_mode = ventilation_mode
        print(f"Air quality mode changed: {old_mode} -> {sensor.ventilation_mode_name}")
    else:
        print("No changes specified")


# Backup commands
@handle_cli_errors
def backup_create(client: AirzoneClient):
    """Create a backup."""
    backup = AirzoneBackup(client)
    backup_file = backup.create_backup()
    print(f"Backup created: {backup_file}")


@handle_cli_errors
def backup_list(client: AirzoneClient):
    """List available backups."""
    backup = AirzoneBackup(client)
    backups = backup.list_backups()
    
    if not backups:
        print("No backups found")
        return
    
    print("\nAvailable backups:")
    for b in backups:
        print(f"  {b}")


@handle_cli_errors
def backup_validate(client: AirzoneClient, backup_file: str):
    """Validate a backup file."""
    backup = AirzoneBackup(client)
    is_valid, message = backup.validate_backup(backup_file)
    
    if is_valid:
        print(f"✓ Backup is valid: {message}")
    else:
        print(f"✗ Backup is invalid: {message}")


@handle_cli_errors
def backup_restore(client: AirzoneClient, backup_file: str, dry_run: bool = False):
    """Restore from a backup."""
    backup = AirzoneBackup(client)
    
    if dry_run:
        print("DRY RUN - No changes will be applied")
    
    changes = backup.restore_backup(backup_file, dry_run=dry_run)
    
    if changes:
        print(f"\n{'Would apply' if dry_run else 'Applied'} {len(changes)} changes")
    else:
        print("No changes needed")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Airzone HVAC Control CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    # Global options
    parser.add_argument("--host", default=DEFAULT_HOST, 
                       help=f"Airzone host IP (default: {DEFAULT_HOST})")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT,
                       help=f"Airzone port (default: {DEFAULT_PORT})")
    parser.add_argument("--no-cache", action="store_true",
                       help="Disable caching")
    parser.add_argument("--force-refresh", action="store_true",
                       help="Force refresh from API")
    
    # Subcommands
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # List command
    list_parser = subparsers.add_parser("list", help="List all systems and zones")
    list_parser.add_argument("--json", action="store_true", help="Output as JSON")
    
    # Status command
    status_parser = subparsers.add_parser("status", help="Get zone status")
    status_parser.add_argument("--system", type=int, required=True, help="System ID")
    status_parser.add_argument("--zone", type=int, required=True, help="Zone ID")
    status_parser.add_argument("--json", action="store_true", help="Output as JSON")
    
    # Control command
    control_parser = subparsers.add_parser("control", help="Control a zone")
    control_parser.add_argument("--system", type=int, required=True, help="System ID")
    control_parser.add_argument("--zone", type=int, required=True, help="Zone ID")
    control_parser.add_argument("--power", choices=["on", "off"], help="Power on/off")
    control_parser.add_argument("--setpoint", type=float, help="Temperature setpoint")
    control_parser.add_argument("--mode", type=int, choices=[1,2,3,4,5],
                               help="Mode (1=Stop, 2=Cool, 3=Heat, 4=Vent, 5=Dehumidify)")
    control_parser.add_argument("--fan-speed", type=int, help="Fan speed")
    control_parser.add_argument("--sleep", type=int, help="Sleep timer (minutes)")
    
    # Error check command
    subparsers.add_parser("errors", help="Check for system errors")
    
    # System check command
    check_parser = subparsers.add_parser("check", help="Check system configuration")
    check_parser.add_argument("--json", action="store_true", help="Output as JSON")
    
    # IAQ commands
    iaq_parser = subparsers.add_parser("iaq", help="IAQ sensor commands")
    iaq_subparsers = iaq_parser.add_subparsers(dest="iaq_command", help="IAQ command")
    
    iaq_list = iaq_subparsers.add_parser("list", help="List all IAQ sensors")
    
    iaq_status = iaq_subparsers.add_parser("status", help="Get IAQ sensor status")
    iaq_status.add_argument("--system", type=int, required=True, help="System ID")
    iaq_status.add_argument("--sensor", type=int, required=True, help="Sensor ID")
    
    iaq_control = iaq_subparsers.add_parser("control", help="Control IAQ sensor")
    iaq_control.add_argument("--system", type=int, required=True, help="System ID")
    iaq_control.add_argument("--sensor", type=int, required=True, help="Sensor ID")
    iaq_control.add_argument("--ventilation", type=int, choices=[0,1,2],
                            help="Ventilation mode (0=Off, 1=On, 2=Auto)")
    
    # Backup commands
    backup_parser = subparsers.add_parser("backup", help="Backup commands")
    backup_subparsers = backup_parser.add_subparsers(dest="backup_command")
    
    backup_subparsers.add_parser("create", help="Create a new backup")
    backup_subparsers.add_parser("list", help="List available backups")
    
    validate_parser = backup_subparsers.add_parser("validate", help="Validate backup")
    validate_parser.add_argument("file", help="Backup file to validate")
    
    restore_parser = backup_subparsers.add_parser("restore", help="Restore backup")
    restore_parser.add_argument("file", help="Backup file to restore")
    restore_parser.add_argument("--dry-run", action="store_true", 
                               help="Preview changes without applying")
    
    # Parse arguments
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 0
    
    # Create client
    client = create_client(args.host, args.port, args.no_cache)
    
    # Command dispatch
    if args.command == "list":
        list_systems(client, args.force_refresh, args.json)
    
    elif args.command == "status":
        get_zone_status(client, args.system, args.zone, args.json, args.force_refresh)
    
    elif args.command == "control":
        params = {}
        if args.power:
            params['power'] = args.power
        if args.setpoint is not None:
            params['setpoint'] = args.setpoint
        if args.mode is not None:
            params['mode'] = args.mode
        if args.fan_speed is not None:
            params['fan_speed'] = args.fan_speed
        if args.sleep is not None:
            params['sleep'] = args.sleep
        
        control_zone(client, args.system, args.zone, **params)
    
    elif args.command == "errors":
        check_errors_command(client)
    
    elif args.command == "check":
        check_system_command(client, args.json)
    
    elif args.command == "iaq":
        if args.iaq_command == "list":
            list_iaq_sensors(client, args.force_refresh)
        elif args.iaq_command == "status":
            get_iaq_sensor_status(client, args.system, args.sensor, args.force_refresh)
        elif args.iaq_command == "control":
            control_iaq_sensor(client, args.system, args.sensor, args.ventilation)
    
    elif args.command == "backup":
        if args.backup_command == "create":
            backup_create(client)
        elif args.backup_command == "list":
            backup_list(client)
        elif args.backup_command == "validate":
            backup_validate(client, args.file)
        elif args.backup_command == "restore":
            backup_restore(client, args.file, args.dry_run)
        else:
            backup_parser.print_help()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
