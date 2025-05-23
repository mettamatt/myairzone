#!/usr/bin/env python3
"""Airzone system class for managing HVAC systems."""

from typing import Dict, List, Optional, TYPE_CHECKING
import logging

if TYPE_CHECKING:
    from .client import AirzoneClient
    from .zone import AirzoneZone


class AirzoneSystem:
    """Class representing an Airzone system."""
    
    def __init__(self, client: 'AirzoneClient', system_id: int, data: Optional[Dict] = None):
        """Initialize Airzone system.
        
        Args:
            client: AirzoneClient instance
            system_id: System ID
            data: Optional system data
        """
        self.client = client
        self.system_id = system_id
        self._data = data or {}
        self.zones: Dict[int, 'AirzoneZone'] = {}
        self.logger = logging.getLogger(f"airzone_system_{system_id}")
    
    def refresh(self, force_refresh: bool = False) -> None:
        """Refresh system data.
        
        Args:
            force_refresh: Force refresh from API
        """
        system_data = self.client.get_system(self.system_id, force_refresh=force_refresh)
        if isinstance(system_data, dict) and "data" in system_data:
            self._data = system_data.get("data", {})
        else:
            self._data = system_data
    
    def load_zones(self, force_refresh: bool = False) -> None:
        """Load all zones for this system.
        
        Args:
            force_refresh: Force refresh from API
        """
        # Import here to avoid circular dependency
        from .zone import AirzoneZone
        
        all_zones_data = self.client.get_all_zones(force_refresh=force_refresh)
        
        if isinstance(all_zones_data, dict) and "systems" in all_zones_data:
            for system in all_zones_data["systems"]:
                if isinstance(system, dict) and "data" in system:
                    system_zones = system.get("data", [])
                    for zone_data in system_zones:
                        if zone_data.get("systemID") == self.system_id:
                            zone_id = zone_data.get("id") or zone_data.get("zoneID")
                            if zone_id is not None:
                                self.zones[zone_id] = AirzoneZone(
                                    self.client, self.system_id, zone_id, zone_data
                                )
    
    @property
    def name(self) -> str:
        """Get system name."""
        # Look for a system name in the data if available
        system_name = self._data.get("name", None)
        if system_name:
            return system_name
        
        # If we have zones, use the first zone's name as a prefix
        if self.zones:
            first_zone = next(iter(self.zones.values()))
            return f"System {self.system_id} ({first_zone.name})"
        
        return f"System {self.system_id}"
    
    @property
    def manufacturer(self) -> str:
        """Get system manufacturer."""
        return self._data.get("manufacturer", "Unknown")
    
    @property
    def firmware(self) -> str:
        """Get system firmware version."""
        return self._data.get("system_firmware", "Unknown")
    
    @property
    def errors(self) -> List[Dict]:
        """Get system errors."""
        return self._data.get("errors", [])
    
    @property
    def has_errors(self) -> bool:
        """Check if system has errors."""
        return len(self.errors) > 0

    @property
    def all_zones(self) -> Dict[int, 'AirzoneZone']:
        """Get all zones for this system."""
        if not self.zones:
            self.load_zones()
        return self.zones
    
    def get_zone(self, zone_id: int, force_refresh: bool = False) -> 'AirzoneZone':
        """Get a specific zone.
        
        Args:
            zone_id: Zone ID
            force_refresh: Force refresh from API
            
        Returns:
            AirzoneZone instance
        """
        # Import here to avoid circular dependency
        from .zone import AirzoneZone
        
        if zone_id not in self.zones or force_refresh:
            # Try to get just this zone first
            zone_data = self.client.get_zone(self.system_id, zone_id, force_refresh)
            if "data" in zone_data and zone_data["data"]:
                zone_info = zone_data["data"][0]
                self.zones[zone_id] = AirzoneZone(
                    self.client, self.system_id, zone_id, zone_info
                )
            else:
                # Fall back to loading all zones
                self.load_zones(force_refresh)
                
        return self.zones.get(zone_id)
    
    def __repr__(self) -> str:
        """String representation."""
        return f"<AirzoneSystem {self.system_id}: {self.name}>"
