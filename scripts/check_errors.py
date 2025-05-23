#!/usr/bin/env python3

import logging
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.airzone_client import AirzoneClient, AirzoneSystem
from src.airzone_errors import get_error_description, save_error_log, print_error_details
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger("airzone_error_check")

def check_system_errors():
    """Check all systems for errors and provide diagnostic information."""
    # Get connection details from environment variables or use defaults
    host = os.getenv("AIRZONE_IP", "192.168.1.100")
    port = int(os.getenv("AIRZONE_PORT", "3000"))
    
    print(f"Connecting to Airzone system at {host}:{port}...")
    
    # Create client
    client = AirzoneClient(host, port)
    
    try:
        # Get webserver info
        webserver_info = client.get_webserver_info()
        print("\n===== WEBSERVER INFORMATION =====")
        print(f"MAC Address: {webserver_info.get('mac', 'Unknown')}")
        print(f"Firmware: {webserver_info.get('ws_firmware', 'Unknown')}")
        print(f"Interface: {webserver_info.get('interface', 'Unknown')}")
    except Exception as e:
        logger.error(f"Error getting webserver info: {e}")
    
    # Get all systems
    systems_data = client.get_all_systems()
    error_log = []
    
    if "systems" not in systems_data:
        print("Failed to retrieve system data.")
        return
    
    # Check each system for errors
    for system_data in systems_data["systems"]:
        system_id = system_data.get("systemID")
        if system_id is not None:
            system = AirzoneSystem(client, system_id, system_data)
            
            # Check system errors
            if system.has_errors:
                for error in system.errors:
                    if isinstance(error, dict) and "system" in error:
                        error_code = error["system"]
                        error_log.append({
                            "timestamp": os.getenv("CHECK_TIME") or "Current run",
                            "type": "system",
                            "system_id": system_id,
                            "error_code": error_code,
                            "manufacturer": system.manufacturer,
                            "firmware": system.firmware
                        })
                        
                        logger.warning(f"System {system_id} has error: {error_code}")
            
            # Load zones for this system and check for errors
            system.load_zones()
            
            for zone_id, zone in system.all_zones.items():
                if zone.has_errors:
                    for error in zone.errors:
                        if isinstance(error, dict) and "system" in error:
                            error_code = error["system"]
                            error_log.append({
                                "timestamp": os.getenv("CHECK_TIME") or "Current run",
                                "type": "zone",
                                "system_id": system_id,
                                "zone_id": zone_id,
                                "zone_name": zone.name,
                                "error_code": error_code,
                                "temperature": zone.temperature,
                                "setpoint": zone.setpoint,
                                "is_on": zone.is_on
                            })
                            
                            logger.warning(f"Zone {zone.name} (System {system_id}, Zone {zone_id}) has error: {error_code}")
    
    # Save and print error information
    if error_log:
        save_error_log(error_log)
        print_error_details(error_log)
    else:
        print("\n✅ No errors detected in any system or zone. All systems appear to be functioning normally.")

if __name__ == "__main__":
    check_system_errors()