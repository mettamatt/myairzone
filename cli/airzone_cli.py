#!/usr/bin/env python3
import argparse
import sys
import os
import logging
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.airzone_client import AirzoneClient, AirzoneSystem, AirzoneZone
from src.airzone_backup import AirzoneBackup
from src.airzone_errors import print_error_details

from scripts.check_system import check_systems
from scripts.check_errors import check_system_errors

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger("airzone_cli")

# Default connection values
DEFAULT_HOST = "192.168.1.100"
DEFAULT_PORT = 3000

def list_systems(client, force_refresh=False, json_output=False):
    """List all systems and zones."""
    systems_data = client.get_all_systems(force_refresh=force_refresh)
    
    if "systems" not in systems_data:
        print("No systems found")
        return
    
    print("\n--- Available Systems ---")
    
    for system_data in systems_data["systems"]:
        system_id = system_data.get("systemID")
        if system_id is not None:
            system = AirzoneSystem(client, system_id, system_data)
            
            print(f"\nSystem {system_id}")
            print(f"  Manufacturer: {system.manufacturer}")
            print(f"  Firmware: {system.firmware}")
            
            if system.has_errors:
                print(f"  Errors: {system.errors}")
            
            # Load zones for this system
            system.load_zones(force_refresh=force_refresh)
            
            if not system.all_zones:
                print("  No zones found")
                continue
            
            for zone_id, zone in system.all_zones.items():
                print(f"  Zone {zone_id}: {zone.name}")
                print(f"    Mode: {zone.mode_name}")
                print(f"    Temperature: {zone.temperature}°C")
                print(f"    Setpoint: {zone.setpoint}°C")
                print(f"    Humidity: {zone.humidity}%")
                print(f"    State: {'On' if zone.is_on else 'Off'}")
                
                if zone.has_errors:
                    print(f"    Errors: {zone.errors}")

def get_zone_status(client, system_id, zone_id, json_output=False, force_refresh=False):
    """Get status of a specific zone."""
    try:
        # Get system
        system = AirzoneSystem(client, system_id)
        
        # Get zone
        zone = system.get_zone(zone_id, force_refresh=force_refresh)
        
        if zone is None:
            print(f"Zone {zone_id} not found in System {system_id}")
            return
        
        # Print zone status
        cache_status = "(cached)" if not force_refresh and client.use_cache else "(live)"
        print(f"\nZone status: {zone.name} (System {system_id}, Zone {zone_id}) {cache_status}")
        print(f"  Power: {'On' if zone.is_on else 'Off'}")
        print(f"  Temperature: {zone.temperature}°C")
        print(f"  Setpoint: {zone.setpoint}°C")
        print(f"  Mode: {zone.mode_name} ({zone.mode})")
        print(f"  Humidity: {zone.humidity}%")
        
        if zone.has_errors:
            print(f"  Errors: {zone.errors}")
            
    except Exception as e:
        print(f"Error getting zone status: {str(e)}")

def control_zone(client, system_id, zone_id, power=None, setpoint=None, mode=None):
    """Control a specific zone.
    
    Args:
        client: AirzoneClient instance
        system_id: System ID
        zone_id: Zone ID
        power: 'on' or 'off'
        setpoint: Temperature setpoint
        mode: Mode ID (1: stop, 2: cooling, 3: heating, 4: ventilation, 5: dehumidify)
    """
    try:
        # Get system
        system = AirzoneSystem(client, system_id)
        
        # Get zone
        zone = system.get_zone(zone_id)
        
        if zone is None:
            print(f"Zone {zone_id} not found in System {system_id}")
            return
        
        print(f"Controlling zone: {zone.name} (System {system_id}, Zone {zone_id})")
        print(f"Initial state: Temperature {zone.temperature}°C, Setpoint {zone.setpoint}°C, Mode {zone.mode_name}, Power {'On' if zone.is_on else 'Off'}")
        
        # Save initial values for change reporting
        initial_setpoint = zone.setpoint
        initial_mode = zone.mode
        initial_power = zone.is_on
        
        # Apply changes
        changes_applied = False
        
        if power is not None:
            if power.lower() == "on" and not zone.is_on:
                zone.turn_on()
                changes_applied = True
                print(f"Power: Off -> On")
            elif power.lower() == "off" and zone.is_on:
                zone.turn_off()
                changes_applied = True
                print(f"Power: On -> Off")
        
        if setpoint is not None and float(setpoint) != float(initial_setpoint):
            old_setpoint = initial_setpoint
            zone.setpoint = float(setpoint)
            changes_applied = True
            print(f"Setpoint: {old_setpoint}°C -> {setpoint}°C")
        
        if mode is not None and mode != initial_mode:
            mode_names = {
                1: "Stop",
                2: "Cooling", 
                3: "Heating",
                4: "Ventilation",
                5: "Dehumidify"
            }
            old_mode = initial_mode
            old_mode_name = mode_names.get(old_mode, f'Unknown ({old_mode})')
            zone.mode = mode
            changes_applied = True
            print(f"Mode: {old_mode_name} -> {mode_names.get(mode, f'Unknown ({mode})')}")
        
        if not changes_applied:
            print("No changes applied")
        else:
            # Refresh to get latest state
            zone.refresh()
            print(f"Final state: Temperature {zone.temperature}°C, Setpoint {zone.setpoint}°C, Mode {zone.mode_name}, Power {'On' if zone.is_on else 'Off'}")
            
    except Exception as e:
        print(f"Error controlling zone: {str(e)}")

def main():
    """Main CLI function."""
    parser = argparse.ArgumentParser(description="Airzone HVAC Control System")
    parser.add_argument("--host", default=DEFAULT_HOST, help="Airzone device IP address")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="Airzone API port")
    parser.add_argument("--no-cache", action="store_true", help="Disable caching")
    parser.add_argument("--force-refresh", action="store_true", help="Force refresh from API")
    
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # System commands
    list_parser = subparsers.add_parser("list", help="List all systems and zones")
    
    status_parser = subparsers.add_parser("status", help="Get status of a specific zone")
    status_parser.add_argument("--system", type=int, required=True, help="System ID")
    status_parser.add_argument("--zone", type=int, required=True, help="Zone ID")
    status_parser.add_argument("--json", action="store_true", help="Output in JSON format")
    
    check_parser = subparsers.add_parser("check", help="Check systems against expected configuration")
    check_parser.add_argument("--json", action="store_true", help="Output in JSON format")
    
    errors_parser = subparsers.add_parser("errors", help="Check for errors in all systems")
    
    # Control command
    control_parser = subparsers.add_parser("control", help="Control a specific zone")
    control_parser.add_argument("--system", type=int, required=True, help="System ID")
    control_parser.add_argument("--zone", type=int, required=True, help="Zone ID")
    control_parser.add_argument("--power", choices=["on", "off"], help="Turn zone on or off")
    control_parser.add_argument("--setpoint", type=float, help="Set temperature setpoint")
    control_parser.add_argument("--mode", type=int, choices=[1, 2, 3, 4, 5], 
                                help="Set mode (1: stop, 2: cooling, 3: heating, 4: ventilation, 5: dehumidify)")
    
    # Backup commands
    backup_parser = subparsers.add_parser("backup", help="Backup operations")
    backup_subparsers = backup_parser.add_subparsers(dest="backup_command", help="Backup command")
    
    create_parser = backup_subparsers.add_parser("create", help="Create a new backup")
    create_parser.add_argument("--output", "-o", help="Output file path")
    
    list_backups_parser = backup_subparsers.add_parser("list", help="List available backups")
    
    validate_parser = backup_subparsers.add_parser("validate", help="Validate a backup file")
    validate_parser.add_argument("file", help="Backup file to validate")
    
    restore_parser = backup_subparsers.add_parser("restore", help="Restore from a backup")
    restore_parser.add_argument("file", help="Backup file to restore from")
    restore_parser.add_argument("--dry-run", "-d", action="store_true", help="Perform a dry run without applying changes")
    
    args = parser.parse_args()
    
    # Create client
    client = AirzoneClient(
        host=args.host, 
        port=args.port,
        use_cache=not args.no_cache
    )
    
    try:
        # Handle main commands
        if args.command == "list":
            list_systems(client, force_refresh=args.force_refresh)
            
        elif args.command == "status":
            get_zone_status(client, args.system, args.zone, args.json, force_refresh=args.force_refresh)
            
        elif args.command == "check":
            check_systems(client, force_refresh=args.force_refresh, json_output=args.json)
            
        elif args.command == "errors":
            check_system_errors()
            
        elif args.command == "control":
            control_zone(client, args.system, args.zone, args.power, args.setpoint, args.mode)
            
        # Handle backup commands
        elif args.command == "backup":
            backup_mgr = AirzoneBackup(client)
            
            if args.backup_command == "create":
                backup_file = backup_mgr.create_backup(args.output)
                print(f"Backup created: {backup_file}")
                
            elif args.backup_command == "list":
                backup_mgr.list_backups()
                
            elif args.backup_command == "validate":
                is_valid = backup_mgr.validate_backup(args.file)
                if is_valid:
                    print(f"✅ Backup file {args.file} is valid")
                else:
                    print(f"❌ Backup file {args.file} is NOT valid")
                    return 1
                    
            elif args.backup_command == "restore":
                success = backup_mgr.restore_from_backup(args.file, args.dry_run)
                if success:
                    if args.dry_run:
                        print("Dry run completed successfully - no changes applied")
                    else:
                        print("Restore completed successfully")
                else:
                    print("Restore failed")
                    return 1
                    
            else:
                backup_parser.print_help()
                
        else:
            parser.print_help()
            
    except Exception as e:
        print(f"Error: {str(e)}")
        logger.error(f"Error running command: {str(e)}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())