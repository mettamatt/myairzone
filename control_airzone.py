#!/usr/bin/env python3
import argparse
import logging
import sys
import json
import os
import time

from airzone_client import AirzoneClient, AirzoneSystem, AirzoneZone

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger("airzone_control")

# Default values
DEFAULT_HOST = "192.168.1.100"
DEFAULT_PORT = 3000
DEFAULT_CACHE_DIR = os.path.expanduser("~/.airzone_cache")
DEFAULT_CACHE_MAX_AGE = 300  # 5 minutes


def list_systems(client: AirzoneClient, force_refresh: bool = False):
    """List all available systems and zones.
    
    Args:
        client: AirzoneClient instance
        force_refresh: Force refresh from API even if cached data is available
    """
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
                # Add specific error descriptions
                for error in system.errors:
                    error_code = error.get("code", "Unknown")
                    if error_code == 9:
                        print("    Error 9: Gateway-System communication error. The system loses communication with the AC unit.")
                    elif error_code == 12:
                        print("    Error 12: Communication error between Airzone Cloud Webserver - system.")
                    elif isinstance(error_code, str) and "CONF" in error_code:
                        print("    IU error CONF: Indoor Unit configuration error.")
            
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


def control_zone(client: AirzoneClient, system_id: int, zone_id: int, 
                power: str = None, setpoint: float = None, mode: int = None):
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


def get_zone_status(client: AirzoneClient, system_id: int, zone_id: int, 
                   json_output: bool = False, force_refresh: bool = False):
    """Get detailed status of a specific zone.
    
    Args:
        client: AirzoneClient instance
        system_id: System ID
        zone_id: Zone ID
        json_output: Whether to output in JSON format
        force_refresh: Force refresh from API even if cached data is available
    """
    try:
        # Get system
        system = AirzoneSystem(client, system_id)
        
        # Get zone
        zone = system.get_zone(zone_id, force_refresh=force_refresh)
        
        if zone is None:
            print(f"Zone {zone_id} not found in System {system_id}")
            return
        
        # Refresh to get latest data if needed
        if force_refresh:
            zone.refresh(force_refresh=True)
        
        if json_output:
            status = {
                "name": zone.name,
                "system_id": zone.system_id,
                "zone_id": zone.zone_id,
                "is_on": zone.is_on,
                "temperature": zone.temperature,
                "setpoint": zone.setpoint,
                "mode": zone.mode,
                "mode_name": zone.mode_name,
                "humidity": zone.humidity,
                "errors": zone.errors,
                "cached": not force_refresh and client.use_cache,
                "timestamp": int(time.time())
            }
            print(json.dumps(status, indent=2))
        else:
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


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Control Airzone HVAC systems")
    parser.add_argument("--host", default=DEFAULT_HOST, help="Airzone device IP address")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="Airzone API port")
    parser.add_argument("--no-cache", action="store_true", help="Disable caching")
    parser.add_argument("--force-refresh", action="store_true", help="Force refresh from API")
    parser.add_argument("--cache-dir", default=DEFAULT_CACHE_DIR, help="Cache directory")
    parser.add_argument("--cache-max-age", type=int, default=DEFAULT_CACHE_MAX_AGE, help="Maximum age of cached data in seconds")
    
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # List command
    list_parser = subparsers.add_parser("list", help="List all systems and zones")
    
    # Control command
    control_parser = subparsers.add_parser("control", help="Control a specific zone")
    control_parser.add_argument("--system", type=int, required=True, help="System ID")
    control_parser.add_argument("--zone", type=int, required=True, help="Zone ID")
    control_parser.add_argument("--power", choices=["on", "off"], help="Turn zone on or off")
    control_parser.add_argument("--setpoint", type=float, help="Set temperature setpoint")
    control_parser.add_argument("--mode", type=int, choices=[1, 2, 3, 4, 5], 
                                help="Set mode (1: stop, 2: cooling, 3: heating, 4: ventilation, 5: dehumidify)")
    
    # Status command
    status_parser = subparsers.add_parser("status", help="Get status of a specific zone")
    status_parser.add_argument("--system", type=int, required=True, help="System ID")
    status_parser.add_argument("--zone", type=int, required=True, help="Zone ID")
    status_parser.add_argument("--json", action="store_true", help="Output in JSON format")
    
    # Cache command
    cache_parser = subparsers.add_parser("cache", help="Manage cache")
    cache_parser.add_argument("--clear", action="store_true", help="Clear all cache")
    cache_parser.add_argument("--info", action="store_true", help="Show cache information")
    cache_parser.add_argument("--export", action="store_true", help="Export cached configuration to a backup file")
    cache_parser.add_argument("--export-path", help="Path to export configuration file (default: './airzone_config_backup.json')")
    
    args = parser.parse_args()
    
    # Create client
    client = AirzoneClient(
        host=args.host, 
        port=args.port,
        use_cache=not args.no_cache,
        cache_max_age=args.cache_max_age
    )
    
    try:
        # Handle commands
        if args.command == "list":
            try:
                list_systems(client, force_refresh=args.force_refresh)
            except Exception as e:
                print(f"Error listing systems: {str(e)}")
                return 1
        elif args.command == "control":
            control_zone(client, args.system, args.zone, args.power, args.setpoint, args.mode)
        elif args.command == "status":
            get_zone_status(client, args.system, args.zone, args.json, force_refresh=args.force_refresh)
        elif args.command == "cache":
            if args.clear:
                success = client.invalidate_cache()
                if success:
                    print("Cache cleared successfully")
                else:
                    print("Failed to clear cache")
            elif args.info:
                if client.use_cache:
                    cache_dir = client.cache.cache_dir
                    max_age = client.cache.max_age
                    
                    print(f"Cache directory: {cache_dir}")
                    print(f"Cache max age: {max_age} seconds")
                    
                    # Count cache files
                    if os.path.exists(cache_dir):
                        cache_files = [f for f in os.listdir(cache_dir) if f.endswith(".json")]
                        print(f"Cached items: {len(cache_files)}")
                        
                        if cache_files:
                            print("\nCached items:")
                            for cache_file in sorted(cache_files):
                                path = os.path.join(cache_dir, cache_file)
                                file_age = time.time() - os.path.getmtime(path)
                                file_size = os.path.getsize(path)
                                print(f"  {cache_file[:-5]}: {file_age:.1f}s old, {file_size} bytes")
                else:
                    print("Cache is disabled")
            elif args.export:
                if not client.use_cache:
                    print("Cache is disabled")
                    return 1
                
                # Get all cached data
                cache_data = {}
                
                # Get webserver info
                webserver_info = client.get_webserver_info()
                if webserver_info:
                    cache_data["webserver"] = webserver_info
                
                # Get all systems
                systems_data = client.get_all_systems()
                if systems_data:
                    cache_data["systems"] = systems_data
                
                # Get all zones
                zones_data = client.get_all_zones()
                if zones_data:
                    cache_data["zones"] = zones_data
                
                # Add metadata
                cache_data["metadata"] = {
                    "created": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "host": client.host,
                    "port": client.port
                }
                
                # Save to file
                export_path = args.export_path or "airzone_config_backup.json"
                try:
                    with open(export_path, "w") as f:
                        json.dump(cache_data, f, indent=2)
                    print(f"Configuration exported to {export_path}")
                except Exception as e:
                    print(f"Error exporting configuration: {e}")
                    return 1
            else:
                cache_parser.print_help()
        else:
            parser.print_help()
    except Exception as e:
        print(f"Error: {str(e)}")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())