#!/usr/bin/env python3
"""Main Airzone API client for making HTTP requests."""

import requests
import json
import logging
import os
from typing import Dict, Any, List, Optional, Union
from dotenv import load_dotenv

from .models import CACHE_KEY_PATTERNS, API_ENDPOINTS

# Load environment variables from .env file
load_dotenv()

# Try to import the cache, but don't fail if it doesn't exist
try:
    from .airzone_cache import AirzoneCache
    CACHE_AVAILABLE = True
except ImportError:
    CACHE_AVAILABLE = False


class AirzoneClient:
    """Client for interacting with Airzone HVAC systems."""
    
    def __init__(self, host: str = None, port: int = None, use_cache: bool = True, cache_max_age: int = 300):
        """Initialize Airzone client.
        
        Args:
            host: Airzone host IP address (defaults to AIRZONE_IP from .env)
            port: Airzone API port (defaults to AIRZONE_PORT from .env)
            use_cache: Whether to use caching (defaults to True)
            cache_max_age: Maximum age of cached data in seconds (defaults to 5 minutes)
        """
        self.host = host or os.getenv("AIRZONE_IP", "192.168.1.100")
        self.port = port or int(os.getenv("AIRZONE_PORT", "3000"))
        self.base_url = f"http://{self.host}:{self.port}/api/v1"
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

    def _generate_cache_key(self, endpoint: str, data: Optional[Dict] = None) -> Optional[str]:
        """Generate a cache key for a given API call using pattern matching.
        
        Args:
            endpoint: API endpoint
            data: Request data
            
        Returns:
            Cache key or None if not cacheable
        """
        # Try exact pattern match first
        key = (endpoint, frozenset(data.items()) if data else None)
        if key in CACHE_KEY_PATTERNS:
            return CACHE_KEY_PATTERNS[key]
        
        # Handle dynamic patterns
        if endpoint == 'hvac' and data:
            if 'zoneID' in data and 'systemID' in data:
                if data['systemID'] == 127:
                    return 'systems'
                elif data['systemID'] == 0 and data['zoneID'] == 0:
                    return 'zones'
                else:
                    return f"zone_{data['systemID']}_{data['zoneID']}"
            elif 'systemID' in data:
                if data['systemID'] == 127:
                    return 'systems'
                else:
                    return f"system_{data['systemID']}"
        
        elif endpoint == 'iaq' and data:
            if 'iaqsensorid' in data and 'systemID' in data:
                if data['systemID'] == 127:
                    return 'iaq_sensors'
                else:
                    return f"iaq_sensor_{data['systemID']}_{data['iaqsensorid']}"
            elif 'systemID' in data:
                if data['systemID'] == 127:
                    return 'iaq_sensors'
                else:
                    return f"iaq_system_{data['systemID']}"
        
        elif endpoint in ['version', 'webserver']:
            return endpoint
            
        return None

    def _make_api_call(self, endpoint: str, data: Optional[Dict] = None, 
                      force_refresh: bool = False, method: str = "POST") -> Dict:
        """Make an API call to the Airzone system.
        
        Args:
            endpoint: API endpoint (without leading slash)
            data: Optional request data
            force_refresh: Force refresh from API even if cached data is available
            method: HTTP method (default POST)
            
        Returns:
            API response as dictionary
            
        Raises:
            Exception: If the API call fails
        """
        # Check cache first if available and not forcing refresh
        if self.use_cache and not force_refresh and method == "POST":
            cache_key = self._generate_cache_key(endpoint, data)
            if cache_key:
                cached_data = self.cache.get(cache_key)
                if cached_data:
                    self.logger.debug(f"Using cached data for {endpoint} with key {cache_key}")
                    return cached_data
        
        try:
            url = f"{self.base_url}/{endpoint}"
            headers = {"Content-Type": "application/json"}
            
            self.logger.debug(f"Making {method} API call to {url} with data: {data}")
            
            if method == "POST":
                response = requests.post(url, headers=headers, 
                                       data=json.dumps(data) if data else None)
            elif method == "PUT":
                response = requests.put(url, headers=headers,
                                      data=json.dumps(data) if data else None)
            else:
                response = requests.request(method, url, headers=headers,
                                          data=json.dumps(data) if data else None)
            
            if response.status_code == 200:
                response_data = response.json()
                
                # Cache the response if caching is enabled and it's a GET-like POST
                if self.use_cache and method == "POST":
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
    
    def clear_cache(self) -> None:
        """Clear all cached data."""
        if self.cache:
            self.cache.clear()
            self.logger.info("Cache cleared")
    
    def get_version(self, force_refresh: bool = False) -> Dict:
        """Get version information.
        
        Args:
            force_refresh: Force refresh from API
            
        Returns:
            Version information
        """
        return self._make_api_call("version", force_refresh=force_refresh)
    
    def get_webserver_info(self, force_refresh: bool = False) -> Dict:
        """Get webserver information.
        
        Args:
            force_refresh: Force refresh from API
            
        Returns:
            Webserver information including:
            - deviceID: Device unique identifier
            - ws_ID: Webserver ID
            - ws_alias: Webserver alias
            - ws_fw_version: Firmware version
            - interface_type: Interface type
            - interface_conn: Connection status
            - interface_ip: IP address
            - ws_type: Webserver type
            - ws_MAC: MAC address
            - ws_ssid: WiFi SSID
        """
        return self._make_api_call("webserver", force_refresh=force_refresh)

    def get_all_systems(self, force_refresh: bool = False) -> Dict:
        """Get information about all systems.
        
        Args:
            force_refresh: Force refresh from API
            
        Returns:
            Information about all systems
        """
        return self._make_api_call("hvac", {"systemID": 127}, force_refresh=force_refresh)
    
    def get_all_zones(self, force_refresh: bool = False) -> Dict:
        """Get information about all zones in all systems.
        
        Args:
            force_refresh: Force refresh from API
            
        Returns:
            Information about all zones
        """
        return self._make_api_call("hvac", {"systemID": 0, "zoneID": 0}, force_refresh=force_refresh)
    
    def get_system(self, system_id: int, force_refresh: bool = False) -> Dict:
        """Get information about a specific system.
        
        Args:
            system_id: System ID
            force_refresh: Force refresh from API
            
        Returns:
            System information
        """
        return self._make_api_call("hvac", {"systemID": system_id}, force_refresh=force_refresh)
    
    def get_zone(self, system_id: int, zone_id: int, force_refresh: bool = False) -> Dict:
        """Get information about a specific zone.
        
        Args:
            system_id: System ID
            zone_id: Zone ID
            force_refresh: Force refresh from API
            
        Returns:
            Zone information
        """
        return self._make_api_call("hvac", {"systemID": system_id, "zoneID": zone_id}, 
                                  force_refresh=force_refresh)

    def set_zone_parameters(self, system_id: int, zone_id: int, parameters: Dict[str, Any]) -> Dict:
        """Set parameters for a specific zone.
        
        Args:
            system_id: System ID
            zone_id: Zone ID
            parameters: Parameters to set (e.g., {"on": 1, "setpoint": 22})
            
        Returns:
            API response
        """
        data = {"systemID": system_id, "zoneID": zone_id, **parameters}
        response = self._make_api_call("hvac", data, method="PUT")
        
        # Invalidate cache for this zone after changing parameters
        if self.use_cache:
            self.cache.invalidate(f"zone_{system_id}_{zone_id}")
            self.cache.invalidate(f"system_{system_id}")
            self.cache.invalidate("systems")
            self.cache.invalidate("zones")
        
        return response
    
    def get_all_iaq_sensors(self, force_refresh: bool = False) -> Dict:
        """Get all IAQ sensors across all systems.
        
        Args:
            force_refresh: Force refresh from API
            
        Returns:
            All IAQ sensors data
        """
        return self._make_api_call("iaq", {"systemID": 1, "iaqsensorid": 0}, 
                                  force_refresh=force_refresh)
    
    def get_iaq_sensor(self, system_id: int, sensor_id: int, force_refresh: bool = False) -> Dict:
        """Get specific IAQ sensor data.
        
        Args:
            system_id: System ID
            sensor_id: IAQ sensor ID
            force_refresh: Force refresh from API
            
        Returns:
            IAQ sensor data
        """
        return self._make_api_call("iaq", {"systemID": system_id, "iaqsensorid": sensor_id}, 
                                  force_refresh=force_refresh)

    def set_iaq_parameters(self, system_id: int, sensor_id: int, parameters: Dict[str, Any]) -> Dict:
        """Set parameters for a specific IAQ sensor.
        
        Args:
            system_id: System ID
            sensor_id: IAQ sensor ID
            parameters: Parameters to set (e.g., {"iaq_mode_vent": 1})
            
        Returns:
            API response
        """
        data = {"systemID": system_id, "iaqsensorid": sensor_id, **parameters}
        response = self._make_api_call("iaq", data, method="PUT")
        
        # Invalidate cache for this IAQ sensor after changing parameters
        if self.use_cache:
            self.cache.invalidate(f"iaq_sensor_{system_id}_{sensor_id}")
            self.cache.invalidate(f"iaq_system_{system_id}")
            self.cache.invalidate("iaq_sensors")
        
        return response
    
    def get_demo_data(self) -> Dict:
        """Get demo zone data for validation reference.
        
        Returns:
            Demo zone data with all possible parameters
        """
        return self._make_api_call("demo")
    
    def invalidate_cache(self, key: Optional[str] = None) -> bool:
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
