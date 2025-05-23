#!/usr/bin/env python3
"""
Check all systems and zones to validate full configuration is detected.
Specifically designed for:
- TestDevice at 192.168.1.100
- Systems 1-4 with all their zones
"""

import logging
import argparse
import json
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.client import AirzoneClient
from src.system import AirzoneSystem
from src.zone import AirzoneZone

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger("airzone_check")

# Expected zones by system
EXPECTED_ZONES = {
    1: {"Salón"},
    2: {"Oficina", "D. Invitado", "D.Carmen"},
    3: {"D Principal"},
    4: {"D. Max", "D Annelise", "Distribuido"}
}

def check_systems(client, force_refresh=False, json_output=False, summary_only=False, brief_mode=False):
    """Check all systems and zones to ensure they match expected configuration.
    
    Args:
        client: AirzoneClient instance
        force_refresh: Force refresh from API even if cached data is available
        json_output: Whether to output results in JSON format
        summary_only: Show only the final summary
        brief_mode: Show brief status with error highlighting
    """
    systems_data = client.get_all_systems(force_refresh=force_refresh)
    
    if "systems" not in systems_data:
        print("No systems found!")
        return False
    
    results = {
        "device": {
            "ip": client.host,
            "port": client.port
        },
        "systems": {},
        "success": True
    }
    
    # Get webserver info to verify device
    webserver = client.get_webserver_info(force_refresh=force_refresh)
    if webserver:
        results["device"]["mac"] = webserver.get("mac", "Unknown")
        results["device"]["alias"] = webserver.get("alias", "Unknown")
        results["device"]["firmware"] = webserver.get("ws_firmware", "Unknown")
    
    all_systems_found = True
    
    for expected_system_id in EXPECTED_ZONES.keys():
        system_found = False
        
        # Find this system in the results
        for system_data in systems_data["systems"]:
            system_id = system_data.get("systemID")
            if system_id is not None and system_id == expected_system_id:
                system = AirzoneSystem(client, system_id, system_data)
                system_found = True
                
                # Load zones for this system
                system.load_zones(force_refresh=force_refresh)
                
                # Check for expected zones
                found_zones = {zone.name for zone_id, zone in system.all_zones.items()}
                expected_zones = EXPECTED_ZONES[system_id]
                missing_zones = expected_zones - found_zones
                
                system_info = {
                    "id": system_id,
                    "found": True,
                    "manufacturer": system.manufacturer,
                    "firmware": system.firmware,
                    "errors": system.errors,
                    "has_errors": system.has_errors,
                    "zones": {
                        "expected": list(expected_zones),
                        "found": list(found_zones),
                        "missing": list(missing_zones),
                        "complete": len(missing_zones) == 0
                    }
                }
                
                # Add details for each zone
                system_info["zone_details"] = {}
                for zone_id, zone in system.all_zones.items():
                    system_info["zone_details"][zone_id] = {
                        "name": zone.name,
                        "is_on": zone.is_on,
                        "temperature": zone.room_temp,
                        "setpoint": zone.setpoint,
                        "mode": zone.mode,
                        "mode_name": zone.mode_name,
                        "humidity": zone.humidity,
                        "errors": zone.errors
                    }
                
                results["systems"][system_id] = system_info
                
                # Print output if not JSON and not summary_only
                if not json_output and not summary_only and not brief_mode:
                    print(f"\nSystem {system_id} - Found: {system_found}")
                    print(f"  Manufacturer: {system.manufacturer}")
                    print(f"  Firmware: {system.firmware}")
                    
                    if system.has_errors:
                        print(f"  Errors: {system.errors}")
                        for error in system.errors:
                            error_code = error.get("code", "Unknown")
                            if error_code == 9:
                                print("    Error 9: Gateway-System communication error.")
                            elif error_code == 12:
                                print("    Error 12: Communication error between Webserver-system.")
                            elif isinstance(error_code, str) and "CONF" in error_code:
                                print("    IU error CONF: Indoor Unit configuration error.")
                    
                    print(f"  Zones:")
                    print(f"    Expected: {', '.join(expected_zones)}")
                    print(f"    Found: {', '.join(found_zones)}")
                    
                    if missing_zones:
                        print(f"    Missing: {', '.join(missing_zones)}")
                    else:
                        print(f"    All expected zones found!")
                    
                    for zone_id, zone in system.all_zones.items():
                        print(f"    Zone {zone_id}: {zone.name}")
                        print(f"      Mode: {zone.mode_name}")
                        print(f"      Temperature: {zone.room_temp}°C")
                        print(f"      Setpoint: {zone.setpoint}°C")
                        print(f"      Humidity: {zone.humidity}%")
                        print(f"      State: {'On' if zone.is_on else 'Off'}")
                        
                        if zone.has_errors:
                            print(f"      Errors: {zone.errors}")
                
                break
        
        if not system_found:
            all_systems_found = False
            results["systems"][expected_system_id] = {
                "id": expected_system_id,
                "found": False,
                "zones": {
                    "expected": list(EXPECTED_ZONES[expected_system_id]),
                    "found": [],
                    "missing": list(EXPECTED_ZONES[expected_system_id]),
                    "complete": False
                }
            }
            
            if not json_output and not summary_only and not brief_mode:
                print(f"\nSystem {expected_system_id} - Found: False")
                print(f"  Missing System!")
    
    # Add overall summary
    results["success"] = all_systems_found
    
    # Check for expected error conditions mentioned in context
    if 2 in results["systems"] and results["systems"][2]["found"]:
        # Check for "IU error CONF" in System 2
        has_expected_error = False
        for error in results["systems"][2].get("errors", []):
            if "CONF" in str(error.get("code", "")):
                has_expected_error = True
                break
        results["systems"][2]["has_expected_error"] = has_expected_error
    
    if 3 in results["systems"] and results["systems"][3]["found"]:
        # Check for "Error 9" in System 3
        has_expected_error = False
        for error in results["systems"][3].get("errors", []):
            if error.get("code") == 9:
                has_expected_error = True
                break
        results["systems"][3]["has_expected_error"] = has_expected_error
    
    # Print JSON output if requested
    if json_output:
        print(json.dumps(results, indent=2))
    elif brief_mode:
        # Brief mode: Show only critical status and errors
        print(f"Device: {results['device'].get('alias', 'Unknown')} - {client.host}:{client.port}")
        print(f"Status: {'✓ All systems operational' if all_systems_found else '✗ Some systems missing'}")
        
        # Show errors prominently
        error_count = 0
        for system_id, system_info in results["systems"].items():
            if system_info.get('found') and system_info.get('has_errors', False):
                error_count += len(system_info.get('errors', []))
                print(f"⚠️  System {system_id}: {len(system_info.get('errors', []))} error(s)")
                for error in system_info.get('errors', []):
                    error_code = error.get('code', 'Unknown')
                    if error_code == 9:
                        print(f"   🔴 Error 9: Gateway communication failure")
                    elif error_code == 12:
                        print(f"   🔴 Error 12: Webserver communication failure")
                    elif isinstance(error_code, str) and "CONF" in error_code:
                        print(f"   🔴 Config Error: Indoor unit mismatch")
        
        if error_count == 0:
            print("✓ No system errors detected")
    else:
        # Print summary (default or summary_only mode)
        print("\n--- Summary ---")
        print(f"Device: {results['device'].get('alias', 'Unknown')} ({results['device'].get('mac', 'Unknown')})")
        print(f"IP: {client.host}:{client.port}")
        print(f"Firmware: {results['device'].get('firmware', 'Unknown')}")
        print(f"All systems found: {all_systems_found}")
        
        for system_id, system_info in results["systems"].items():
            status_line = f"System {system_id}: {'✓' if system_info['found'] else '✗'} " + \
                         f"Zones: {'✓' if system_info.get('zones', {}).get('complete', False) else '✗'}"
            
            # Add error indicator
            if system_info.get('found') and system_info.get('has_errors', False):
                status_line += f" ⚠️  {len(system_info.get('errors', []))} error(s)"
            
            print(status_line)
    
    return all_systems_found

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Check Airzone HVAC systems configuration")
    parser.add_argument("--host", default="192.168.1.100", help="Airzone device IP address")
    parser.add_argument("--port", type=int, default=3000, help="Airzone API port")
    parser.add_argument("--force-refresh", action="store_true", help="Force refresh from API")
    parser.add_argument("--json", action="store_true", help="Output in JSON format")
    args = parser.parse_args()
    
    # Create client
    client = AirzoneClient(host=args.host, port=args.port)
    
    try:
        success = check_systems(client, force_refresh=args.force_refresh, json_output=args.json)
        return 0 if success else 1
    except Exception as e:
        print(f"Error checking systems: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())