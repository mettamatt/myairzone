#!/usr/bin/env python3
import json
import os
import time
import logging
from typing import Dict, Any, Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()
from datetime import datetime

from .client import AirzoneClient
from .system import AirzoneSystem
from .zone import AirzoneZone

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger("airzone_backup")

class AirzoneBackup:
    """Backup and restore functionality for Airzone systems."""
    
    def __init__(self, client: AirzoneClient):
        """Initialize the backup manager.
        
        Args:
            client: AirzoneClient instance
        """
        self.client = client
        self.backup_dir = "backups"
        
        # Ensure backup directory exists
        if not os.path.exists(self.backup_dir):
            os.makedirs(self.backup_dir)
            logger.info(f"Created backup directory: {self.backup_dir}")
    
    def create_backup(self, filename: Optional[str] = None) -> str:
        """Create a backup of all system configuration.
        
        Args:
            filename: Optional custom filename
            
        Returns:
            Path to the backup file
        """
        cache_data = {}
        
        logger.info("Creating backup of Airzone configuration...")
        
        # Get webserver info
        webserver_info = self.client.get_webserver_info()
        if webserver_info:
            cache_data["webserver"] = webserver_info
        
        # Get all systems
        systems_data = self.client.get_all_systems()
        if systems_data:
            cache_data["systems"] = systems_data
        
        # Get all zones
        zones_data = self.client.get_all_zones()
        if zones_data:
            cache_data["zones"] = zones_data
        
        # Add metadata
        cache_data["metadata"] = {
            "created": datetime.now().isoformat(),
            "host": self.client.host,
            "port": self.client.port,
            "version": self.client.get_version().get("version", "Unknown"),
            "backup_type": "full"
        }
        
        # Generate filename if not provided
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = os.path.join(self.backup_dir, f"airzone_backup_{timestamp}.json")
        
        # Save to file
        with open(filename, "w") as f:
            json.dump(cache_data, f, indent=2)
        
        logger.info(f"Backup saved to {filename}")
        return filename
    
    def validate_backup(self, backup_file: str) -> bool:
        """Validate a backup file.
        
        Args:
            backup_file: Path to backup file
            
        Returns:
            True if valid, False otherwise
        """
        try:
            with open(backup_file, "r") as f:
                backup_data = json.load(f)
            
            # Check required keys
            required_keys = ["webserver", "systems", "zones", "metadata"]
            for key in required_keys:
                if key not in backup_data:
                    logger.error(f"Backup validation failed: Missing {key} data")
                    return False
            
            # Check metadata
            if "host" not in backup_data["metadata"] or "port" not in backup_data["metadata"]:
                logger.error("Backup validation failed: Missing host/port in metadata")
                return False
            
            # Check for systems
            if "systems" not in backup_data["systems"]:
                logger.error("Backup validation failed: No systems found in backup")
                return False
            
            logger.info(f"Backup file {backup_file} is valid")
            return True
        except Exception as e:
            logger.error(f"Backup validation failed: {str(e)}")
            return False
    
    def restore_from_backup(self, backup_file: str, dry_run: bool = True) -> bool:
        """Restore from a backup file.
        
        Args:
            backup_file: Path to backup file
            dry_run: If True, just validate but don't apply changes
            
        Returns:
            True if successful, False otherwise
        """
        # First validate the backup
        if not self.validate_backup(backup_file):
            return False
        
        try:
            with open(backup_file, "r") as f:
                backup_data = json.load(f)
            
            logger.info(f"Restoring from backup: {backup_file}")
            
            # If dry run, just report what would be done
            if dry_run:
                webserver = backup_data["webserver"]
                systems = backup_data["systems"].get("systems", [])
                
                print("\n=== DRY RUN: RESTORE PREVIEW ===")
                print(f"Backup created: {backup_data['metadata']['created']}")
                print(f"Source: {backup_data['metadata']['host']}:{backup_data['metadata']['port']}")
                print(f"Target: {self.client.host}:{self.client.port}")
                print(f"Webserver: {webserver.get('alias', 'Unknown')} ({webserver.get('mac', 'Unknown')})")
                print(f"Firmware: {webserver.get('ws_firmware', 'Unknown')}")
                print(f"Systems: {len(systems)}")
                
                for system in systems:
                    system_id = system.get("systemID", "Unknown")
                    manufacturer = system.get("manufacturer", "Unknown")
                    firmware = system.get("system_firmware", "Unknown")
                    print(f"  System {system_id}: {manufacturer} (Firmware: {firmware})")
                
                print("\nNo changes applied (dry run)")
                return True
            
            # Implement partial restore for controllable parameters
            restored_count = 0
            failed_count = 0
            
            print("\n=== RESTORING CONTROLLABLE PARAMETERS ===")
            
            # Get current zone data to compare
            current_zones = self.client.get_all_zones()
            current_zone_map = {}
            
            # Handle different current zone structures
            if "data" in current_zones:
                for zone_data in current_zones["data"]:
                    system_id = zone_data.get("systemID")
                    zone_id = zone_data.get("zoneID")
                    if system_id is not None and zone_id is not None:
                        current_zone_map[f"{system_id}_{zone_id}"] = zone_data
            elif "systems" in current_zones:
                # Extract zones from all systems
                for system in current_zones["systems"]:
                    if "data" in system:
                        for zone_data in system["data"]:
                            system_id = zone_data.get("systemID")
                            zone_id = zone_data.get("zoneID")
                            if system_id is not None and zone_id is not None:
                                current_zone_map[f"{system_id}_{zone_id}"] = zone_data
            
            # Restore zones from backup
            backup_zones = []
            zones_data = backup_data.get("zones", {})
            
            # Handle different backup structures
            if "data" in zones_data:
                backup_zones = zones_data["data"]
            elif "systems" in zones_data:
                # Extract zones from all systems
                for system in zones_data["systems"]:
                    if "data" in system:
                        backup_zones.extend(system["data"])
            
            for backup_zone in backup_zones:
                system_id = backup_zone.get("systemID")
                zone_id = backup_zone.get("zoneID")
                zone_name = backup_zone.get("name", f"Zone {zone_id}")
                
                if system_id is None or zone_id is None:
                    continue
                    
                zone_key = f"{system_id}_{zone_id}"
                current_zone = current_zone_map.get(zone_key)
                
                if not current_zone:
                    print(f"  ⚠️  Zone {zone_name} (S{system_id}Z{zone_id}) not found in current system")
                    failed_count += 1
                    continue
                
                changes_made = []
                
                try:
                    # Restore power state
                    backup_on = backup_zone.get("on", 0)
                    current_on = current_zone.get("on", 0)
                    if backup_on != current_on:
                        self.client.set_zone_parameters(system_id, zone_id, {"on": backup_on})
                        changes_made.append(f"Power: {'On' if backup_on else 'Off'}")
                    
                    # Restore setpoint
                    backup_setpoint = backup_zone.get("setpoint")
                    current_setpoint = current_zone.get("setpoint")
                    if backup_setpoint is not None and current_setpoint is not None:
                        if abs(backup_setpoint - current_setpoint) > 0.1:  # Allow small float differences
                            self.client.set_zone_parameters(system_id, zone_id, {"setpoint": backup_setpoint})
                            changes_made.append(f"Setpoint: {backup_setpoint}°C")
                    
                    # Restore mode
                    backup_mode = backup_zone.get("mode")
                    current_mode = current_zone.get("mode")
                    if backup_mode is not None and backup_mode != current_mode:
                        self.client.set_zone_parameters(system_id, zone_id, {"mode": backup_mode})
                        mode_names = {1: "Stop", 2: "Cooling", 3: "Heating", 4: "Ventilation", 5: "Dehumidify"}
                        mode_name = mode_names.get(backup_mode, f"Mode {backup_mode}")
                        changes_made.append(f"Mode: {mode_name}")
                    
                    # Restore sleep timer
                    backup_sleep = backup_zone.get("sleep")
                    current_sleep = current_zone.get("sleep")
                    if backup_sleep is not None and current_sleep is not None and backup_sleep != current_sleep:
                        self.client.set_zone_parameters(system_id, zone_id, {"sleep": backup_sleep})
                        if backup_sleep == 0:
                            changes_made.append("Sleep: Disabled")
                        else:
                            changes_made.append(f"Sleep: {backup_sleep}min")
                    
                    # Restore fan speed (if supported)
                    backup_speed = backup_zone.get("speed")
                    current_speed = current_zone.get("speed")
                    if backup_speed is not None and current_speed is not None and backup_speed != current_speed:
                        # Check if zone supports fan speed control
                        if backup_zone.get("speed_values") or current_zone.get("speed_values"):
                            self.client.set_zone_parameters(system_id, zone_id, {"speed": backup_speed})
                            changes_made.append(f"Fan Speed: {backup_speed}")
                    
                    # Restore slat positions (if supported)
                    for slat_param in ["slats_vertical", "slats_horizontal"]:
                        backup_slat = backup_zone.get(slat_param)
                        current_slat = current_zone.get(slat_param)
                        if backup_slat is not None and current_slat is not None and backup_slat != current_slat:
                            self.client.set_zone_parameters(system_id, zone_id, {slat_param: backup_slat})
                            param_name = "V-Slats" if "vertical" in slat_param else "H-Slats"
                            changes_made.append(f"{param_name}: {backup_slat}")
                    
                    # Restore swing settings (if supported)
                    for swing_param in ["slats_vswing", "slats_hswing"]:
                        backup_swing = backup_zone.get(swing_param)
                        current_swing = current_zone.get(swing_param)
                        if backup_swing is not None and current_swing is not None and backup_swing != current_swing:
                            self.client.set_zone_parameters(system_id, zone_id, {swing_param: backup_swing})
                            swing_name = "V-Swing" if "vswing" in swing_param else "H-Swing"
                            swing_value = "On" if backup_swing == 1 else "Off"
                            changes_made.append(f"{swing_name}: {swing_value}")
                    
                    if changes_made:
                        print(f"  ✅ {zone_name} (S{system_id}Z{zone_id}): {', '.join(changes_made)}")
                        restored_count += 1
                    else:
                        print(f"  ➡️  {zone_name} (S{system_id}Z{zone_id}): No changes needed")
                        
                except Exception as e:
                    print(f"  ❌ {zone_name} (S{system_id}Z{zone_id}): Failed - {str(e)}")
                    failed_count += 1
            
            print(f"\n=== RESTORE SUMMARY ===")
            print(f"Zones restored: {restored_count}")
            print(f"Zones failed: {failed_count}")
            print(f"Total zones processed: {len(backup_zones)}")
            
            if failed_count == 0:
                print("✅ Restore completed successfully")
                return True
            else:
                print("⚠️  Restore completed with some failures")
                return restored_count > 0
            
        except Exception as e:
            logger.error(f"Restore failed: {str(e)}")
            return False
    
    def list_backups(self):
        """List all available backups."""
        if not os.path.exists(self.backup_dir):
            print("No backups directory found")
            return
        
        backups = [f for f in os.listdir(self.backup_dir) if f.endswith(".json")]
        
        if not backups:
            print("No backups found")
            return
        
        print(f"\n=== Available Backups ({len(backups)}) ===")
        
        for i, backup_file in enumerate(sorted(backups, reverse=True), 1):
            path = os.path.join(self.backup_dir, backup_file)
            file_time = datetime.fromtimestamp(os.path.getmtime(path))
            file_size = os.path.getsize(path) / 1024  # KB
            
            # Try to extract metadata
            try:
                with open(path, "r") as f:
                    backup_data = json.load(f)
                    metadata = backup_data.get("metadata", {})
                    host = metadata.get("host", "Unknown")
                    systems_count = len(backup_data.get("systems", {}).get("systems", []))
                    print(f"{i}. {backup_file}")
                    print(f"   Created: {file_time.strftime('%Y-%m-%d %H:%M:%S')}")
                    print(f"   Size: {file_size:.1f} KB")
                    print(f"   Host: {host}")
                    print(f"   Systems: {systems_count}")
                    print()
            except Exception:
                # If can't read metadata, just show basic info
                print(f"{i}. {backup_file}")
                print(f"   Created: {file_time.strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"   Size: {file_size:.1f} KB")
                print()

def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Backup and restore Airzone configurations")
    parser.add_argument("--host", default=os.getenv("AIRZONE_IP", "192.168.1.100"), help="Airzone device IP address")
    parser.add_argument("--port", type=int, default=int(os.getenv("AIRZONE_PORT", "3000")), help="Airzone API port")
    
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # Backup command
    backup_parser = subparsers.add_parser("backup", help="Create a new backup")
    backup_parser.add_argument("--output", "-o", help="Output file path")
    
    # List command
    subparsers.add_parser("list", help="List available backups")
    
    # Validate command
    validate_parser = subparsers.add_parser("validate", help="Validate a backup file")
    validate_parser.add_argument("file", help="Backup file to validate")
    
    # Restore command
    restore_parser = subparsers.add_parser("restore", help="Restore from a backup")
    restore_parser.add_argument("file", help="Backup file to restore from")
    restore_parser.add_argument("--dry-run", "-d", action="store_true", help="Perform a dry run without applying changes")
    
    args = parser.parse_args()
    
    # Create client
    client = AirzoneClient(host=args.host, port=args.port)
    
    # Create backup manager
    backup_mgr = AirzoneBackup(client)
    
    # Handle commands
    if args.command == "backup":
        backup_file = backup_mgr.create_backup(args.output)
        print(f"Backup created: {backup_file}")
        
    elif args.command == "list":
        backup_mgr.list_backups()
        
    elif args.command == "validate":
        is_valid = backup_mgr.validate_backup(args.file)
        if is_valid:
            print(f"✅ Backup file {args.file} is valid")
        else:
            print(f"❌ Backup file {args.file} is NOT valid")
            return 1
            
    elif args.command == "restore":
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
        parser.print_help()
        
    return 0

if __name__ == "__main__":
    exit(main())