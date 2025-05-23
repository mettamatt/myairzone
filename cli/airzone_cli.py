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

def list_systems(client, force_refresh=False, json_output=False):
    """List all systems and zones."""
    # Show connection status
    print(f"\n--- Connection Status ---")
    print(f"Host: {client.host}:{client.port}")
    
    try:
        # Test connectivity with version call
        import time
        start_time = time.time()
        version_data = client.get_version()
        response_time = time.time() - start_time
        print(f"Status: Connected (response time: {response_time:.2f}s)")
        
        # Get webserver info for WiFi details
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
    except Exception as e:
        print(f"Status: Connection failed - {str(e)}")
        return
    
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
            
            # Available modes
            modes = system_data.get("modes", [])
            if modes:
                mode_names = {1: "Stop", 2: "Cooling", 3: "Heating", 4: "Ventilation", 5: "Dehumidify"}
                available_modes = [mode_names.get(m, f"Mode {m}") for m in modes]
                print(f"  Available Modes: {', '.join(available_modes)}")
            
            # Fan speed - check both system and individual zones since it varies
            speed = system_data.get("speed", None)
            speeds = system_data.get("speeds", None)
            if speed is not None:
                print(f"  Fan Speed: {speed}")
            if speeds is not None:
                print(f"  Max Fan Speed: {speeds}")
            
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
                
                # Battery and signal info
                battery = zone._data.get("battery", None)
                if battery is not None:
                    print(f"    Battery: {battery}%")
                
                
                thermos_radio = zone._data.get("thermos_radio", None)
                if thermos_radio is not None:
                    radio_status = "Wireless" if thermos_radio == 1 else "Wired"
                    print(f"    Connection: {radio_status}")
                
                # Zone-specific fan speed
                zone_speed = zone._data.get("speed", None)
                zone_speeds = zone._data.get("speeds", None)
                speed_values = zone._data.get("speed_values", None)
                if zone_speed is not None:
                    speed_info = f"{zone_speed}"
                    if zone_speeds is not None:
                        speed_info += f"/{zone_speeds}"
                    if speed_values:
                        speed_info += f" (available: {speed_values})"
                    print(f"    Fan Speed: {speed_info}")
                
                # Demand status
                demands = []
                if zone._data.get("air_demand", 0) == 1:
                    demands.append("Air")
                if zone._data.get("cold_demand", 0) == 1:
                    demands.append("Cooling")
                if zone._data.get("heat_demand", 0) == 1:
                    demands.append("Heating")
                if zone._data.get("floor_demand", 0) == 1:
                    demands.append("Floor")
                if demands:
                    print(f"    Active Demands: {', '.join(demands)}")
                
                # Damper/slat positions
                slats_info = []
                slats_v = zone._data.get("slats_vertical", None)
                slats_h = zone._data.get("slats_horizontal", None)
                if slats_v is not None:
                    slats_info.append(f"V:{slats_v}")
                if slats_h is not None:
                    slats_info.append(f"H:{slats_h}")
                if slats_info:
                    print(f"    Dampers: {', '.join(slats_info)}")
                
                # Swing settings
                swing_info = []
                vswing = zone._data.get("slats_vswing", None)
                hswing = zone._data.get("slats_hswing", None)
                if vswing is not None:
                    swing_info.append(f"V:{'On' if vswing == 1 else 'Off'}")
                if hswing is not None:
                    swing_info.append(f"H:{'On' if hswing == 1 else 'Off'}")
                if swing_info:
                    print(f"    Swing: {', '.join(swing_info)}")
                
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

def control_zone(client, system_id, zone_id, power=None, setpoint=None, mode=None, 
                 sleep=None, fan_speed=None, slats_vertical=None, slats_horizontal=None,
                 vertical_swing=None, horizontal_swing=None):
    """Control a specific zone.
    
    Args:
        client: AirzoneClient instance
        system_id: System ID
        zone_id: Zone ID
        power: 'on' or 'off'
        setpoint: Temperature setpoint
        mode: Mode ID (1: stop, 2: cooling, 3: heating, 4: ventilation, 5: dehumidify)
        sleep: Sleep timer in minutes
        fan_speed: Fan speed value
        slats_vertical: Vertical slat position
        slats_horizontal: Horizontal slat position
        vertical_swing: 'on' or 'off' for vertical swing
        horizontal_swing: 'on' or 'off' for horizontal swing
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
        
        # Sleep timer
        if sleep is not None:
            old_sleep = zone.sleep_timer
            if sleep != old_sleep:
                zone.sleep_timer = sleep
                changes_applied = True
                if sleep == 0:
                    print(f"Sleep: {old_sleep}min -> Disabled")
                else:
                    print(f"Sleep: {old_sleep}min -> {sleep}min")
        
        # Fan speed
        if fan_speed is not None:
            old_speed = zone.fan_speed
            if fan_speed != old_speed:
                try:
                    zone.fan_speed = fan_speed
                    changes_applied = True
                    print(f"Fan Speed: {old_speed} -> {fan_speed}")
                except ValueError as e:
                    print(f"Fan Speed Error: {e}")
        
        # Slat positions
        if slats_vertical is not None:
            old_slats = zone.slats_vertical
            if slats_vertical != old_slats:
                zone.slats_vertical = slats_vertical
                changes_applied = True
                print(f"Vertical Slats: {old_slats} -> {slats_vertical}")
        
        if slats_horizontal is not None:
            old_slats = zone.slats_horizontal
            if slats_horizontal != old_slats:
                zone.slats_horizontal = slats_horizontal
                changes_applied = True
                print(f"Horizontal Slats: {old_slats} -> {slats_horizontal}")
        
        # Swing settings
        if vertical_swing is not None:
            old_swing = zone.vertical_swing
            new_swing = vertical_swing.lower() == "on"
            if new_swing != old_swing:
                zone.vertical_swing = new_swing
                changes_applied = True
                print(f"Vertical Swing: {'On' if old_swing else 'Off'} -> {'On' if new_swing else 'Off'}")
        
        if horizontal_swing is not None:
            old_swing = zone.horizontal_swing
            new_swing = horizontal_swing.lower() == "on"
            if new_swing != old_swing:
                zone.horizontal_swing = new_swing
                changes_applied = True
                print(f"Horizontal Swing: {'On' if old_swing else 'Off'} -> {'On' if new_swing else 'Off'}")
        
        if not changes_applied:
            print("No changes applied")
        else:
            # Refresh to get latest state
            zone.refresh()
            print(f"Final state: Temperature {zone.temperature}°C, Setpoint {zone.setpoint}°C, Mode {zone.mode_name}, Power {'On' if zone.is_on else 'Off'}")
            
    except Exception as e:
        print(f"Error controlling zone: {str(e)}")

def show_zone_validation(client, system_id, zone_id):
    """Show validation information for a specific zone.
    
    Args:
        client: AirzoneClient instance
        system_id: System ID
        zone_id: Zone ID
    """
    try:
        # Get system
        system = AirzoneSystem(client, system_id)
        
        # Get zone
        zone = system.get_zone(zone_id)
        
        if zone is None:
            print(f"Zone {zone_id} not found in System {system_id}")
            return
        
        print(f"\n=== Validation Info for {zone.name} (System {system_id}, Zone {zone_id}) ===")
        
        validation_info = zone.get_validation_info()
        
        # Mode validation
        modes = validation_info["modes"]
        if modes:
            mode_names = {1: "Stop", 2: "Cooling", 3: "Heating", 4: "Ventilation", 5: "Dehumidify"}
            mode_list = [f"{m}({mode_names.get(m, 'Unknown')})" for m in modes]
            print(f"Valid Modes: {', '.join(mode_list)}")
        else:
            print("Valid Modes: No restrictions")
        
        # Temperature validation
        temp_range = validation_info["temp_range"]
        if temp_range["min"] is not None and temp_range["max"] is not None:
            step_str = f", step: {temp_range['step']}°C" if temp_range.get("step") else ""
            print(f"Temperature Range: {temp_range['min']}-{temp_range['max']}°C{step_str}")
        
        # Mode-specific temperature ranges
        heat_range = validation_info["heat_range"]
        cool_range = validation_info["cool_range"]
        if heat_range["min"] is not None:
            print(f"Heating Mode Range: {heat_range['min']}-{heat_range['max']}°C")
        if cool_range["min"] is not None:
            print(f"Cooling Mode Range: {cool_range['min']}-{cool_range['max']}°C")
        
        # Fan speed validation
        speed_values = validation_info["speed_values"]
        max_speeds = validation_info["max_speeds"]
        if speed_values:
            print(f"Valid Fan Speeds: {speed_values}")
        elif max_speeds is not None:
            print(f"Fan Speed Range: 0-{max_speeds}")
        else:
            print("Fan Speed: Not supported or no restrictions")
        
        # Sleep timer
        print("Sleep Timer: 0-1440 minutes (0-24 hours)")
        
        # Additional info
        angle_values = validation_info["angle_values"]
        if angle_values["heat"]:
            print(f"Heat Angle Values: {angle_values['heat']}")
        if angle_values["cool"]:
            print(f"Cool Angle Values: {angle_values['cool']}")
            
    except Exception as e:
        print(f"Error getting validation info: {str(e)}")

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
    check_parser.add_argument("--summary", action="store_true", help="Show only summary information")
    check_parser.add_argument("--brief", action="store_true", help="Show brief status with errors highlighted")
    
    errors_parser = subparsers.add_parser("errors", help="Check for errors in all systems")
    
    # Validate command
    validate_parser = subparsers.add_parser("validate", help="Show validation info for a zone")
    validate_parser.add_argument("--system", type=int, required=True, help="System ID")
    validate_parser.add_argument("--zone", type=int, required=True, help="Zone ID")
    
    # Control command
    control_parser = subparsers.add_parser("control", help="Control a specific zone")
    control_parser.add_argument("--system", type=int, required=True, help="System ID")
    control_parser.add_argument("--zone", type=int, required=True, help="Zone ID")
    control_parser.add_argument("--power", choices=["on", "off"], help="Turn zone on or off")
    control_parser.add_argument("--setpoint", type=float, help="Set temperature setpoint")
    control_parser.add_argument("--mode", type=int, choices=[1, 2, 3, 4, 5], 
                                help="Set mode (1: stop, 2: cooling, 3: heating, 4: ventilation, 5: dehumidify)")
    control_parser.add_argument("--sleep", type=int, help="Set sleep timer in minutes (0 to disable)")
    control_parser.add_argument("--fan-speed", type=int, help="Set fan speed")
    control_parser.add_argument("--slats-vertical", type=int, help="Set vertical slat position")
    control_parser.add_argument("--slats-horizontal", type=int, help="Set horizontal slat position")
    control_parser.add_argument("--vertical-swing", choices=["on", "off"], help="Enable/disable vertical swing")
    control_parser.add_argument("--horizontal-swing", choices=["on", "off"], help="Enable/disable horizontal swing")
    
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
            if hasattr(args, 'summary') and args.summary:
                check_systems(client, force_refresh=args.force_refresh, json_output=args.json, summary_only=True)
            elif hasattr(args, 'brief') and args.brief:
                check_systems(client, force_refresh=args.force_refresh, json_output=args.json, brief_mode=True)
            else:
                check_systems(client, force_refresh=args.force_refresh, json_output=args.json)
            
        elif args.command == "errors":
            check_system_errors()
            
        elif args.command == "validate":
            show_zone_validation(client, args.system, args.zone)
            
        elif args.command == "control":
            control_zone(client, args.system, args.zone, args.power, args.setpoint, args.mode,
                        getattr(args, 'sleep', None), getattr(args, 'fan_speed', None),
                        getattr(args, 'slats_vertical', None), getattr(args, 'slats_horizontal', None),
                        getattr(args, 'vertical_swing', None), getattr(args, 'horizontal_swing', None))
            
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