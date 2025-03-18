#!/usr/bin/env python3
import logging
import json
import os
from datetime import datetime
from typing import List, Dict, Any, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("airzone_errors.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("airzone_errors")

# Centralized error code definitions
ERROR_CODES = {
    "Error 9": "Gateway-System communication error. The system loses communication with the AC unit. "
               "The system will open all the zones and deactivate the control from the controllers, "
               "only allowing the operation of the unit from the controller of its manufacturer.",
    
    "Error 12": "Communication error between Airzone Cloud Webserver - system. "
              "The system loses communication with the Webserver. "
              "Check that the Webserver is correctly connected to the Control board's automation bus.",
    
    "IU error CONF": "Indoor Unit configuration error. There might be a mismatch in the configuration "
                   "between the Airzone system and the indoor unit."
}

# Centralized error solutions
ERROR_SOLUTIONS = {
    "Error 9": [
        "Check physical connections between the gateway and the AC unit",
        "Power cycle both the AC unit and the Airzone system",
        "Verify that the AC unit is functioning correctly"
    ],
    "Error 12": [
        "Check physical connections between the webserver and the control board",
        "Power cycle the webserver",
        "Verify network connectivity if using an IP connection"
    ],
    "IU error CONF": [
        "Check configuration settings in the AC unit",
        "Verify compatibility between the Airzone system and the AC unit",
        "Try resetting the AC unit and the Airzone system"
    ]
}

def get_error_description(error_code: str) -> str:
    """Get description for known error codes.
    
    Args:
        error_code: The error code string
        
    Returns:
        Error description or "Unknown error code"
    """
    return ERROR_CODES.get(error_code, "Unknown error code")

def get_error_solutions(error_code: str) -> List[str]:
    """Get solutions for known error codes.
    
    Args:
        error_code: The error code string
        
    Returns:
        List of solution steps
    """
    return ERROR_SOLUTIONS.get(error_code, [
        "Consult the Airzone documentation for specific error codes",
        "Contact Airzone technical support"
    ])

def save_error_log(error_details: List[Dict[str, Any]], custom_filename: Optional[str] = None) -> str:
    """Save error details to a log file.
    
    Args:
        error_details: List of error dictionaries
        custom_filename: Optional custom filename
        
    Returns:
        Path to the saved log file
    """
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = custom_filename or os.path.join(log_dir, f"airzone_errors_{timestamp}.json")
    
    with open(filename, "w") as f:
        json.dump(error_details, f, indent=2)
    
    logger.info(f"Error details saved to {filename}")
    return filename

def print_error_details(error_details: List[Dict[str, Any]]) -> None:
    """Print formatted error details.
    
    Args:
        error_details: List of error dictionaries
    """
    if not error_details:
        print("\n✅ No errors detected in any system or zone. All systems appear to be functioning normally.")
        return
        
    for error in error_details:
        error_code = error.get("error_code", "Unknown")
        system_id = error.get("system_id", "Unknown")
        zone_id = error.get("zone_id", None)
        zone_name = error.get("zone_name", None)
        
        if zone_id and zone_name:
            print(f"\n===== ZONE {zone_name} (System {system_id}, Zone {zone_id}) ERROR =====")
        else:
            print(f"\n===== SYSTEM {system_id} ERROR =====")
            
        print(f"Error: {error_code}")
        print(f"Description: {get_error_description(error_code)}")
        print("Solutions:")
        
        for i, solution in enumerate(get_error_solutions(error_code), 1):
            print(f"  {i}. {solution}")
    
    print("\n===== MANUAL INTERVENTION REQUIRED =====")
    print("Note: Remote restart is NOT possible via the API with this Airzone model (firmware 4.12)")
    print("To resolve errors, physical intervention is required:")
    print("  1. Power cycle the Airzone webserver hardware")
    print("  2. Check all physical connections between components")
    print("  3. Power cycle the affected AC units")
    print("  4. If errors persist, contact Airzone technical support")