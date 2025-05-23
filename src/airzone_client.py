#!/usr/bin/env python3
import requests
import json
import logging
import os
from typing import Dict, Any, List, Optional, Union

# Try to import the cache, but don't fail if it doesn't exist
try:
    from .airzone_cache import AirzoneCache
    CACHE_AVAILABLE = True
except ImportError:
    CACHE_AVAILABLE = False

class AirzoneClient:
    """Client for interacting with Airzone HVAC systems."""
    
    def __init__(self, host: str = "192.168.1.100", port: int = 3000, use_cache: bool = True, cache_max_age: int = 300):
        """Initialize Airzone client.
        
        Args:
            host: Airzone host IP address
            port: Airzone API port
            use_cache: Whether to use caching (defaults to True)
            cache_max_age: Maximum age of cached data in seconds (defaults to 5 minutes)
        """
        self.host = host
        self.port = port
        self.base_url = f"http://{host}:{port}/api/v1"
        self.logger = logging.getLogger("airzone_client")
        
        # Initialize cache if available and enabled
        self.use_cache = use_cache and CACHE_AVAILABLE
        if self.use_cache:
            self.cache = AirzoneCache(max_age=cache_max_age)
            self.logger.info("Cache initialized")
        else:
            self.cache = None
            if use_cache and not CACHE_AVAILABLE:
                self.logger.warning("Cache requested but airzone_cache module not available")
    
    def _generate_cache_key(self, endpoint: str, data: Optional[Dict] = None) -> str:
        """Generate a cache key for a given API call.
        
        Args:
            endpoint: API endpoint
            data: Request data
            
        Returns:
            Cache key
        """
        if endpoint == "version":
            return "version"
        elif endpoint == "webserver":
            return "webserver"
        elif endpoint == "hvac":
            if data is None:
                return "hvac"
            
            if "systemID" in data and "zoneID" in data:
                if data["systemID"] == 127:
                    return "systems"
                elif data["systemID"] == 0 and data["zoneID"] == 0:
                    return "zones"
                else:
                    return f"zone_{data['systemID']}_{data['zoneID']}"
            elif "systemID" in data:
                if data["systemID"] == 127:
                    return "systems"
                else:
                    return f"system_{data['systemID']}"
        
        # For non-cacheable endpoints or complex data
        return None
    
    def _make_api_call(self, endpoint: str, data: Optional[Dict] = None, force_refresh: bool = False) -> Dict:
        """Make an API call to the Airzone system.
        
        Args:
            endpoint: API endpoint (without leading slash)
            data: Optional request data
            force_refresh: Force refresh from API even if cached data is available
            
        Returns:
            API response as dictionary
            
        Raises:
            Exception: If the API call fails
        """
        # Check cache first if available and not forcing refresh
        if self.use_cache and not force_refresh:
            cache_key = self._generate_cache_key(endpoint, data)
            if cache_key:
                cached_data = self.cache.get(cache_key)
                if cached_data:
                    self.logger.debug(f"Using cached data for {endpoint} with key {cache_key}")
                    return cached_data
        
        try:
            url = f"{self.base_url}/{endpoint}"
            headers = {"Content-Type": "application/json"}
            
            self.logger.debug(f"Making API call to {url} with data: {data}")
            
            if data:
                response = requests.post(url, headers=headers, data=json.dumps(data))
            else:
                response = requests.post(url, headers=headers)
            
            if response.status_code == 200:
                response_data = response.json()
                
                # Cache the response if caching is enabled
                if self.use_cache:
                    cache_key = self._generate_cache_key(endpoint, data)
                    if cache_key:
                        self.cache.set(cache_key, response_data)
                
                return response_data
            else:
                error_msg = f"Error: Status code {response.status_code}"
                self.logger.error(error_msg)
                raise Exception(error_msg)
                
        except Exception as e:
            self.logger.error(f"API call failed: {str(e)}")
            raise
    
    def get_version(self, force_refresh: bool = False) -> Dict:
        """Get the Airzone API version.
        
        Args:
            force_refresh: Force refresh from API even if cached data is available
            
        Returns:
            Version information
        """
        return self._make_api_call("version", force_refresh=force_refresh)
    
    def get_webserver_info(self, force_refresh: bool = False) -> Dict:
        """Get webserver information.
        
        Args:
            force_refresh: Force refresh from API even if cached data is available
            
        Returns:
            Webserver information including firmware version
        """
        webserver_info = self._make_api_call("webserver", force_refresh=force_refresh)
        
        # Enhance cache with connection information for recovery purposes
        if webserver_info and isinstance(webserver_info, dict):
            # Add IP and port to the response before caching
            webserver_info["ip_address"] = self.host
            webserver_info["port"] = self.port
            
            # Store in cache directly to ensure these fields are saved
            if self.use_cache:
                self.cache.set("webserver", webserver_info)
                
        return webserver_info
    
    def get_all_systems(self, force_refresh: bool = False) -> Dict:
        """Get information about all systems.
        
        Args:
            force_refresh: Force refresh from API even if cached data is available
            
        Returns:
            Information about all systems
        """
        return self._make_api_call("hvac", {"systemID": 127}, force_refresh=force_refresh)
    
    def get_all_zones(self, force_refresh: bool = False) -> Dict:
        """Get information about all zones in all systems.
        
        Args:
            force_refresh: Force refresh from API even if cached data is available
            
        Returns:
            Information about all zones
        """
        return self._make_api_call("hvac", {"systemID": 0, "zoneID": 0}, force_refresh=force_refresh)
    
    def get_system(self, system_id: int, force_refresh: bool = False) -> Dict:
        """Get information about a specific system.
        
        Args:
            system_id: System ID
            force_refresh: Force refresh from API even if cached data is available
            
        Returns:
            System information
        """
        return self._make_api_call("hvac", {"systemID": system_id}, force_refresh=force_refresh)
    
    def get_zone(self, system_id: int, zone_id: int, force_refresh: bool = False) -> Dict:
        """Get information about a specific zone.
        
        Args:
            system_id: System ID
            zone_id: Zone ID
            force_refresh: Force refresh from API even if cached data is available
            
        Returns:
            Zone information
        """
        return self._make_api_call("hvac", {"systemID": system_id, "zoneID": zone_id}, force_refresh=force_refresh)
    
    def set_zone_parameters(self, system_id: int, zone_id: int, parameters: Dict[str, Any]) -> Dict:
        """Set parameters for a specific zone.
        
        Args:
            system_id: System ID
            zone_id: Zone ID
            parameters: Parameters to set (e.g., {"on": 1, "setpoint": 22})
            
        Returns:
            API response
            
        Example:
            >>> client.set_zone_parameters(1, 1, {"on": 1, "setpoint": 22})
        """
        data = {"systemID": system_id, "zoneID": zone_id, **parameters}
        response = self._make_api_call("hvac", data)
        
        # Invalidate cache for this zone after changing parameters
        if self.use_cache:
            self.cache.invalidate(f"zone_{system_id}_{zone_id}")
            # Also invalidate system and all zones caches as they might contain this zone's data
            self.cache.invalidate(f"system_{system_id}")
            self.cache.invalidate("systems")
            self.cache.invalidate("zones")
        
        return response
        
    def invalidate_cache(self, key: Optional[str] = None):
        """Invalidate cache.
        
        Args:
            key: Specific cache key to invalidate, or None to invalidate all
            
        Returns:
            True if successful, False otherwise
        """
        if not self.use_cache:
            return False
            
        if key:
            return self.cache.invalidate(key)
        else:
            return self.cache.invalidate_all()


class AirzoneSystem:
    """Class representing an Airzone system."""
    
    def __init__(self, client: AirzoneClient, system_id: int, data: Dict = None):
        """Initialize Airzone system.
        
        Args:
            client: AirzoneClient instance
            system_id: System ID
            data: Optional system data
        """
        self.client = client
        self.system_id = system_id
        self._data = data or {}
        self.zones = {}
    
    def refresh(self, force_refresh: bool = False) -> None:
        """Refresh system data.
        
        Args:
            force_refresh: Force refresh from API even if cached data is available
        """
        system_data = self.client.get_system(self.system_id, force_refresh=force_refresh)
        if isinstance(system_data, dict) and "data" in system_data:
            self._data = system_data.get("data", {})
        else:
            self._data = system_data
    
    def load_zones(self, force_refresh: bool = False) -> None:
        """Load all zones for this system.
        
        Args:
            force_refresh: Force refresh from API even if cached data is available
        """
        all_zones_data = self.client.get_all_zones(force_refresh=force_refresh)
        
        if isinstance(all_zones_data, dict) and "systems" in all_zones_data:
            for system in all_zones_data["systems"]:
                if isinstance(system, dict) and "data" in system:
                    system_zones = system.get("data", [])
                    for zone_data in system_zones:
                        if zone_data.get("systemID") == self.system_id:
                            zone_id = zone_data.get("id") or zone_data.get("zoneID")
                            if zone_id is not None:
                                self.zones[zone_id] = AirzoneZone(self.client, self.system_id, zone_id, zone_data)
    
    @property
    def name(self) -> str:
        """Get system name."""
        # Look for a system name in the data if available, otherwise use ID
        system_name = self._data.get("name", None)
        if system_name:
            return system_name
        
        # If we have zones, use the first zone's name as a prefix
        if self.zones and len(self.zones) > 0:
            first_zone = next(iter(self.zones.values()))
            return f"System {self.system_id} ({first_zone.name})"
        
        # Default to system ID
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
    def all_zones(self) -> Dict[int, "AirzoneZone"]:
        """Get all zones for this system."""
        if not self.zones:
            self.load_zones()
        return self.zones
    
    def get_zone(self, zone_id: int, force_refresh: bool = False) -> "AirzoneZone":
        """Get a specific zone.
        
        Args:
            zone_id: Zone ID
            force_refresh: Force refresh from API even if cached data is available
            
        Returns:
            AirzoneZone instance
        """
        if zone_id not in self.zones or force_refresh:
            # Try to get just this zone first
            try:
                zone_data = self.client.get_zone(self.system_id, zone_id, force_refresh=force_refresh)
                if isinstance(zone_data, dict) and "data" in zone_data:
                    self.zones[zone_id] = AirzoneZone(self.client, self.system_id, zone_id, zone_data["data"])
            except Exception:
                # If that fails, load all zones
                self.load_zones(force_refresh=force_refresh)
                
        return self.zones.get(zone_id)


class AirzoneZone:
    """Class representing an Airzone zone."""
    
    def __init__(self, client: AirzoneClient, system_id: int, zone_id: int, data: Dict = None):
        """Initialize Airzone zone.
        
        Args:
            client: AirzoneClient instance
            system_id: System ID
            zone_id: Zone ID
            data: Optional zone data
        """
        self.client = client
        self.system_id = system_id
        self.zone_id = zone_id
        self._data = data or {}
    
    def refresh(self, force_refresh: bool = False) -> None:
        """Refresh zone data.
        
        Args:
            force_refresh: Force refresh from API even if cached data is available
        """
        response = self.client.get_zone(self.system_id, self.zone_id, force_refresh=force_refresh)
        if isinstance(response, dict) and "data" in response:
            self._data = response["data"]
        else:
            self._data = response
    
    @property
    def name(self) -> str:
        """Get zone name."""
        return self._data.get("name", f"Zone {self.zone_id}")
    
    @property
    def is_on(self) -> bool:
        """Check if zone is on."""
        return self._data.get("on", 0) == 1
    
    def turn_on(self) -> None:
        """Turn zone on."""
        self.client.set_zone_parameters(self.system_id, self.zone_id, {"on": 1})
        self.refresh(force_refresh=True)
    
    def turn_off(self) -> None:
        """Turn zone off."""
        self.client.set_zone_parameters(self.system_id, self.zone_id, {"on": 0})
        self.refresh(force_refresh=True)
    
    @property
    def temperature(self) -> float:
        """Get current temperature."""
        return self._data.get("roomTemp", 0.0)
    
    @property
    def setpoint(self) -> float:
        """Get current setpoint."""
        return self._data.get("setpoint", 0.0)
    
    @setpoint.setter
    def setpoint(self, value: float) -> None:
        """Set temperature setpoint.
        
        Args:
            value: Temperature setpoint
        """
        self.client.set_zone_parameters(self.system_id, self.zone_id, {"setpoint": value})
        self.refresh(force_refresh=True)
        # Update the internal data directly as well to ensure it's available immediately
        self._data["setpoint"] = value
    
    @property
    def mode(self) -> int:
        """Get current mode.
        
        Returns:
            Mode ID (1: stop, 2: cooling, 3: heating, 4: ventilation, 5: dehumidify)
        """
        return self._data.get("mode", 0)
    
    @property
    def mode_name(self) -> str:
        """Get current mode name."""
        modes = {
            1: "Stop",
            2: "Cooling",
            3: "Heating",
            4: "Ventilation",
            5: "Dehumidify"
        }
        return modes.get(self.mode, "Unknown")
    
    @mode.setter
    def mode(self, value: int) -> None:
        """Set mode.
        
        Args:
            value: Mode ID (1: stop, 2: cooling, 3: heating, 4: ventilation, 5: dehumidify)
        """
        self.client.set_zone_parameters(self.system_id, self.zone_id, {"mode": value})
        self.refresh(force_refresh=True)
    
    @property
    def humidity(self) -> int:
        """Get current humidity percentage."""
        return self._data.get("humidity", 0)
    
    @property
    def errors(self) -> List[Dict]:
        """Get zone errors."""
        return self._data.get("errors", [])
    
    @property
    def has_errors(self) -> bool:
        """Check if zone has errors."""
        return len(self.errors) > 0
    
    def __str__(self) -> str:
        return f"{self.name} (System {self.system_id}, Zone {self.zone_id}): {self.temperature}°C / {self.setpoint}°C"


def main():
    """Example usage of the Airzone client."""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Create client with caching enabled
    client = AirzoneClient(use_cache=True, cache_max_age=300)
    
    print("\nFirst run - should get data from API:")
    
    # Get basic information
    version = client.get_version()
    webserver = client.get_webserver_info()
    
    print(f"API Version: {version.get('version')}")
    print(f"Webserver Firmware: {webserver.get('ws_firmware')}")
    print(f"MAC Address: {webserver.get('mac')}")
    
    # Get all systems
    systems_data = client.get_all_systems()
    systems = []
    
    if "systems" in systems_data:
        for system_data in systems_data["systems"]:
            system_id = system_data.get("systemID")
            if system_id is not None:
                system = AirzoneSystem(client, system_id, system_data)
                systems.append(system)
                
                print(f"\nSystem {system_id}")
                print(f"  Manufacturer: {system.manufacturer}")
                print(f"  Firmware: {system.firmware}")
                
                if system.has_errors:
                    print(f"  Errors: {system.errors}")
                
                # Load zones for this system
                system.load_zones()
                
                for zone_id, zone in system.all_zones.items():
                    print(f"  Zone {zone_id}: {zone.name}")
                    print(f"    Mode: {zone.mode_name}")
                    print(f"    Temperature: {zone.temperature}°C")
                    print(f"    Setpoint: {zone.setpoint}°C")
                    print(f"    Humidity: {zone.humidity}%")
                    print(f"    State: {'On' if zone.is_on else 'Off'}")
                    
                    if zone.has_errors:
                        print(f"    Errors: {zone.errors}")
    
    print("\nSecond run - should use cached data:")
    
    # Get basic information again (should use cache)
    version = client.get_version()
    webserver = client.get_webserver_info()
    
    print(f"API Version: {version.get('version')} (from cache)")
    print(f"Webserver Firmware: {webserver.get('ws_firmware')} (from cache)")
    print(f"MAC Address: {webserver.get('mac')} (from cache)")
    
    # Get system info again (should use cache)
    for system in systems:
        print(f"\nSystem {system.system_id} (from cache)")
        print(f"  Manufacturer: {system.manufacturer}")
        print(f"  Firmware: {system.firmware}")
        
        if system.has_errors:
            print(f"  Errors: {system.errors}")
        
        # Zones should be already loaded and cached
        for zone_id, zone in system.all_zones.items():
            print(f"  Zone {zone_id}: {zone.name} (from cache)")
            print(f"    Mode: {zone.mode_name}")
            print(f"    Temperature: {zone.temperature}°C")
            print(f"    Setpoint: {zone.setpoint}°C")
            print(f"    Humidity: {zone.humidity}%")
            print(f"    State: {'On' if zone.is_on else 'Off'}")
            
            if zone.has_errors:
                print(f"    Errors: {zone.errors}")
    
    print("\nThird run - force refresh from API:")
    
    # Force refresh from API
    version = client.get_version(force_refresh=True)
    webserver = client.get_webserver_info(force_refresh=True)
    
    print(f"API Version: {version.get('version')} (refreshed)")
    print(f"Webserver Firmware: {webserver.get('ws_firmware')} (refreshed)")
    print(f"MAC Address: {webserver.get('mac')} (refreshed)")
    
    # Invalidate all cache and get fresh data
    client.invalidate_cache()
    print("\nCache invalidated, getting fresh data:")
    
    # Get all systems again (should query API)
    systems_data = client.get_all_systems()
    
    if "systems" in systems_data:
        for system_data in systems_data["systems"]:
            system_id = system_data.get("systemID")
            if system_id is not None:
                print(f"\nSystem {system_id} (refreshed)")
                system = AirzoneSystem(client, system_id, system_data)
                print(f"  Manufacturer: {system.manufacturer}")
                print(f"  Firmware: {system.firmware}")


if __name__ == "__main__":
    main()