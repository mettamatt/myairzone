#!/usr/bin/env python3
import json
import os
import time
import logging
from typing import Dict, Any, Optional
from datetime import datetime

from airzone_client import AirzoneClient

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
            
            # For actual restore, we would restore each zone's state
            # This is limited because Airzone doesn't provide a full restore API
            # We can only restore settings like on/off state, temperature, mode
            
            # TODO: Implement full restore logic here
            # For now, just log that this would require customized logic
            logger.warning("Full restore not implemented - would require device-specific logic")
            return False
            
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
    parser.add_argument("--host", default="192.168.1.100", help="Airzone device IP address")
    parser.add_argument("--port", type=int, default=3000, help="Airzone API port")
    
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