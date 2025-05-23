#!/usr/bin/env python3
import requests
import json
import logging
import os
from typing import Dict, Any, List, Optional, Union
from dotenv import load_dotenv

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
        elif endpoint == "iaq":
            if data is None:
                return "iaq"
            
            if "systemID" in data and "iaqsensorid" in data:
                if data["systemID"] == 127:
                    return "iaq_sensors"
                else:
                    return f"iaq_sensor_{data['systemID']}_{data['iaqsensorid']}"
            elif "systemID" in data:
                if data["systemID"] == 127:
                    return "iaq_sensors"
                else:
                    return f"iaq_system_{data['systemID']}"
        
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
    
    def _make_put_request(self, endpoint: str, data: Dict) -> Dict:
        """Make a PUT request to the Airzone system for control operations.
        
        Args:
            endpoint: API endpoint (without leading slash)
            data: Request data (required for PUT requests)
            
        Returns:
            API response as dictionary
            
        Raises:
            Exception: If the API call fails
        """
        try:
            url = f"{self.base_url}/{endpoint}"
            headers = {"Content-Type": "application/json"}
            
            self.logger.debug(f"Making PUT request to {url} with data: {data}")
            
            response = requests.put(url, headers=headers, data=json.dumps(data))
            
            if response.status_code == 200:
                response_data = response.json()
                return response_data
            else:
                error_msg = f"PUT request failed: Status code {response.status_code}"
                if response.text:
                    error_msg += f", Response: {response.text}"
                self.logger.error(error_msg)
                raise Exception(error_msg)
                
        except Exception as e:
            self.logger.error(f"PUT request failed: {str(e)}")
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
    
    def get_demo_data(self) -> Dict:
        """Get demo zone data for validation reference.
        
        Returns:
            Demo zone data with all possible parameters and their valid ranges
        """
        return self._make_api_call("demo")
    
    def get_validation_reference(self) -> Dict[str, Any]:
        """Get validation reference data from demo endpoint.
        
        Returns:
            Dictionary with validation information for all possible parameters
        """
        try:
            demo_data = self.get_demo_data()
            if "data" in demo_data and len(demo_data["data"]) > 0:
                zone_data = demo_data["data"][0]
                return {
                    "modes": zone_data.get("modes", []),
                    "speed_values": zone_data.get("speed_values", []),
                    "max_speeds": zone_data.get("speeds"),
                    "temp_range": {
                        "min": zone_data.get("minTemp"),
                        "max": zone_data.get("maxTemp"),
                        "step": zone_data.get("temp_step")
                    },
                    "cool_range": {
                        "min": zone_data.get("coolmintemp"),
                        "max": zone_data.get("coolmaxtemp")
                    },
                    "heat_range": {
                        "min": zone_data.get("heatmintemp"),
                        "max": zone_data.get("heatmaxtemp")
                    },
                    "sleep_range": {
                        "min": 0,
                        "max": 1440,
                        "description": "0-24 hours in minutes"
                    },
                    "example_values": {
                        "slats_vertical": zone_data.get("slats_vertical"),
                        "slats_horizontal": zone_data.get("slats_horizontal"),
                        "speed": zone_data.get("speed"),
                        "mode": zone_data.get("mode"),
                        "setpoint": zone_data.get("setpoint")
                    }
                }
        except Exception as e:
            self.logger.warning(f"Could not get validation reference data: {e}")
            
        return {}
    
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
        response = self._make_put_request("hvac", data)
        
        # Invalidate cache for this zone after changing parameters
        if self.use_cache:
            self.cache.invalidate(f"zone_{system_id}_{zone_id}")
            # Also invalidate system and all zones caches as they might contain this zone's data
            self.cache.invalidate(f"system_{system_id}")
            self.cache.invalidate("systems")
            self.cache.invalidate("zones")
        
        return response
    
    def get_all_iaq_sensors(self, force_refresh: bool = False) -> Dict:
        """Get all IAQ sensors across all systems.
        
        Args:
            force_refresh: Force refresh from API even if cached data is available
            
        Returns:
            All IAQ sensors data
        """
        # Use iaqsensorid 0 to get all airqsensors from system 1
        return self._make_api_call("iaq", {"systemID": 1, "iaqsensorid": 0}, force_refresh=force_refresh)
    
    def get_iaq_sensor(self, system_id: int, sensor_id: int, force_refresh: bool = False) -> Dict:
        """Get specific IAQ sensor data.
        
        Args:
            system_id: System ID
            sensor_id: IAQ sensor ID
            force_refresh: Force refresh from API even if cached data is available
            
        Returns:
            IAQ sensor data
        """
        return self._make_api_call("iaq", {"systemID": system_id, "iaqsensorid": sensor_id}, force_refresh=force_refresh)
    
    def set_iaq_parameters(self, system_id: int, sensor_id: int, parameters: Dict[str, Any]) -> Dict:
        """Set parameters for a specific IAQ sensor.
        
        Args:
            system_id: System ID
            sensor_id: IAQ sensor ID
            parameters: Parameters to set (e.g., {"iaq_mode_vent": 1})
            
        Returns:
            API response
            
        Example:
            >>> client.set_iaq_parameters(1, 1, {"iaq_mode_vent": 1})
        """
        data = {"systemID": system_id, "iaqsensorid": sensor_id, **parameters}
        response = self._make_put_request("iaq", data)
        
        # Invalidate cache for this IAQ sensor after changing parameters
        if self.use_cache:
            self.cache.invalidate(f"iaq_sensor_{system_id}_{sensor_id}")
            # Also invalidate system and all sensors caches as they might contain this sensor's data
            self.cache.invalidate(f"iaq_system_{system_id}")
            self.cache.invalidate("iaq_sensors")
        
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
                    # API returns data as a list with one zone, so get the first item
                    zone_list = zone_data["data"]
                    if isinstance(zone_list, list) and len(zone_list) > 0:
                        self.zones[zone_id] = AirzoneZone(self.client, self.system_id, zone_id, zone_list[0])
                    else:
                        self.zones[zone_id] = AirzoneZone(self.client, self.system_id, zone_id, zone_list)
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
            # API returns data as a list with one zone, so get the first item
            zone_list = response["data"]
            if isinstance(zone_list, list) and len(zone_list) > 0:
                self._data = zone_list[0]
            else:
                self._data = zone_list
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
            
        Raises:
            ValueError: If setpoint is outside valid range
        """
        if not self.validate_setpoint(value):
            validation_info = self.get_validation_info()
            current_mode = self.mode
            if current_mode == 2:  # Cooling
                temp_range = validation_info["cool_range"]
            elif current_mode == 3:  # Heating
                temp_range = validation_info["heat_range"]
            else:
                temp_range = validation_info["temp_range"]
            
            range_str = f"{temp_range['min']}-{temp_range['max']}°C"
            step_str = f" (step: {temp_range.get('step')}°C)" if temp_range.get('step') else ""
            raise ValueError(f"Setpoint {value}°C is invalid. Valid range: {range_str}{step_str}")
            
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
            
        Raises:
            ValueError: If mode is not supported by this zone
        """
        if not self.validate_mode(value):
            available_modes = self._data.get("modes", [])
            mode_names = {1: "Stop", 2: "Cooling", 3: "Heating", 4: "Ventilation", 5: "Dehumidify"}
            available_names = [f"{m}({mode_names.get(m, 'Unknown')})" for m in available_modes]
            raise ValueError(f"Mode {value} not supported. Available modes: {available_names}")
            
        self.client.set_zone_parameters(self.system_id, self.zone_id, {"mode": value})
        self.refresh(force_refresh=True)
    
    @property
    def humidity(self) -> int:
        """Get current humidity percentage."""
        return self._data.get("humidity", 0)
    
    @property
    def sleep_timer(self) -> int:
        """Get current sleep timer in minutes."""
        return self._data.get("sleep", 0)
    
    @sleep_timer.setter
    def sleep_timer(self, minutes: int) -> None:
        """Set sleep timer in minutes.
        
        Args:
            minutes: Sleep timer in minutes (0 to disable)
            
        Raises:
            ValueError: If sleep timer value is invalid
        """
        if not self.validate_sleep_timer(minutes):
            raise ValueError(f"Sleep timer {minutes} minutes is invalid. Valid range: 0-1440 minutes (0-24 hours)")
        self.client.set_zone_parameters(self.system_id, self.zone_id, {"sleep": minutes})
        self.refresh(force_refresh=True)
        self._data["sleep"] = minutes
    
    @property
    def fan_speed(self) -> int:
        """Get current fan speed."""
        return self._data.get("speed", 0)
    
    @property
    def available_fan_speeds(self) -> List[int]:
        """Get list of available fan speeds."""
        return self._data.get("speed_values", [])
    
    @fan_speed.setter
    def fan_speed(self, speed: int) -> None:
        """Set fan speed.
        
        Args:
            speed: Fan speed value
            
        Raises:
            ValueError: If speed is not in available speeds
        """
        if not self.validate_fan_speed(speed):
            available_speeds = self.available_fan_speeds
            max_speeds = self._data.get("speeds")
            if available_speeds:
                raise ValueError(f"Fan speed {speed} not available. Available speeds: {available_speeds}")
            elif max_speeds is not None:
                raise ValueError(f"Fan speed {speed} invalid. Valid range: 0-{max_speeds}")
            else:
                raise ValueError(f"Fan speed {speed} invalid. No validation data available.")
        self.client.set_zone_parameters(self.system_id, self.zone_id, {"speed": speed})
        self.refresh(force_refresh=True)
        self._data["speed"] = speed
    
    @property
    def slats_vertical(self) -> Optional[int]:
        """Get vertical slat position."""
        return self._data.get("slats_vertical")
    
    @slats_vertical.setter
    def slats_vertical(self, position: int) -> None:
        """Set vertical slat position.
        
        Args:
            position: Slat position value
        """
        self.client.set_zone_parameters(self.system_id, self.zone_id, {"slats_vertical": position})
        self.refresh(force_refresh=True)
        self._data["slats_vertical"] = position
    
    @property
    def slats_horizontal(self) -> Optional[int]:
        """Get horizontal slat position."""
        return self._data.get("slats_horizontal")
    
    @slats_horizontal.setter
    def slats_horizontal(self, position: int) -> None:
        """Set horizontal slat position.
        
        Args:
            position: Slat position value
        """
        self.client.set_zone_parameters(self.system_id, self.zone_id, {"slats_horizontal": position})
        self.refresh(force_refresh=True)
        self._data["slats_horizontal"] = position
    
    @property
    def vertical_swing(self) -> bool:
        """Check if vertical swing is enabled."""
        return self._data.get("slats_vswing", 0) == 1
    
    @vertical_swing.setter
    def vertical_swing(self, enabled: bool) -> None:
        """Set vertical swing mode.
        
        Args:
            enabled: True to enable vertical swing, False to disable
        """
        value = 1 if enabled else 0
        self.client.set_zone_parameters(self.system_id, self.zone_id, {"slats_vswing": value})
        self.refresh(force_refresh=True)
        self._data["slats_vswing"] = value
    
    @property
    def horizontal_swing(self) -> bool:
        """Check if horizontal swing is enabled."""
        return self._data.get("slats_hswing", 0) == 1
    
    @horizontal_swing.setter
    def horizontal_swing(self, enabled: bool) -> None:
        """Set horizontal swing mode.
        
        Args:
            enabled: True to enable horizontal swing, False to disable
        """
        value = 1 if enabled else 0
        self.client.set_zone_parameters(self.system_id, self.zone_id, {"slats_hswing": value})
        self.refresh(force_refresh=True)
        self._data["slats_hswing"] = value
    
    # Validation methods
    def validate_mode(self, mode: int) -> bool:
        """Validate if mode is supported by this zone.
        
        Args:
            mode: Mode ID to validate
            
        Returns:
            True if mode is supported, False otherwise
        """
        available_modes = self._data.get("modes", [])
        return mode in available_modes if available_modes else True
    
    def validate_fan_speed(self, speed: int) -> bool:
        """Validate if fan speed is supported by this zone.
        
        Args:
            speed: Fan speed to validate
            
        Returns:
            True if speed is supported, False otherwise
        """
        available_speeds = self._data.get("speed_values", [])
        if available_speeds:
            return speed in available_speeds
        # If no speed_values, check against max speeds
        max_speeds = self._data.get("speeds")
        if max_speeds is not None:
            return 0 <= speed <= max_speeds
        return True  # No validation data available
    
    def validate_setpoint(self, setpoint: float, mode: Optional[int] = None) -> bool:
        """Validate if temperature setpoint is within allowed range.
        
        Args:
            setpoint: Temperature setpoint to validate
            mode: Optional mode to check mode-specific limits
            
        Returns:
            True if setpoint is valid, False otherwise
        """
        current_mode = mode or self.mode
        
        # Check mode-specific limits first
        if current_mode == 2:  # Cooling mode
            min_temp = self._data.get("coolmintemp")
            max_temp = self._data.get("coolmaxtemp")
        elif current_mode == 3:  # Heating mode
            min_temp = self._data.get("heatmintemp")
            max_temp = self._data.get("heatmaxtemp")
        else:
            # For other modes, use general limits
            min_temp = self._data.get("minTemp")
            max_temp = self._data.get("maxTemp")
        
        if min_temp is not None and setpoint < min_temp:
            return False
        if max_temp is not None and setpoint > max_temp:
            return False
            
        # Check temperature step if available
        temp_step = self._data.get("temp_step")
        if temp_step and temp_step > 0:
            # Check if setpoint aligns with temperature step
            min_temp_check = min_temp or 0
            return abs((setpoint - min_temp_check) % temp_step) < 0.01
            
        return True
    
    def validate_sleep_timer(self, minutes: int) -> bool:
        """Validate sleep timer value.
        
        Args:
            minutes: Sleep timer in minutes
            
        Returns:
            True if valid, False otherwise
        """
        # Basic validation - non-negative and reasonable upper limit
        return 0 <= minutes <= 1440  # 0 to 24 hours
    
    def get_validation_info(self) -> Dict[str, Any]:
        """Get validation information for this zone.
        
        Returns:
            Dictionary containing validation limits and available values
        """
        return {
            "modes": self._data.get("modes", []),
            "speed_values": self._data.get("speed_values", []),
            "max_speeds": self._data.get("speeds"),
            "temp_range": {
                "min": self._data.get("minTemp"),
                "max": self._data.get("maxTemp"),
                "step": self._data.get("temp_step")
            },
            "cool_range": {
                "min": self._data.get("coolmintemp"),
                "max": self._data.get("coolmaxtemp")
            },
            "heat_range": {
                "min": self._data.get("heatmintemp"),
                "max": self._data.get("heatmaxtemp")
            },
            "angle_values": {
                "heat": self._data.get("heat_angle_values", []),
                "cool": self._data.get("cold_angle_values", [])
            }
        }
    
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


class AirzoneIAQSensor:
    """Class representing an Airzone Indoor Air Quality sensor."""
    
    def __init__(self, client: AirzoneClient, system_id: int, sensor_id: int, data: Dict = None):
        """Initialize Airzone IAQ sensor.
        
        Args:
            client: AirzoneClient instance
            system_id: System ID
            sensor_id: IAQ sensor ID
            data: Optional sensor data
        """
        self.client = client
        self.system_id = system_id
        self.sensor_id = sensor_id
        self._data = data or {}
    
    def refresh(self, force_refresh: bool = False) -> None:
        """Refresh IAQ sensor data.
        
        Args:
            force_refresh: Force refresh from API even if cached data is available
        """
        response = self.client.get_iaq_sensor(self.system_id, self.sensor_id, force_refresh=force_refresh)
        if isinstance(response, dict) and "data" in response:
            # API returns data as a list with one sensor, so get the first item
            sensor_list = response["data"]
            if isinstance(sensor_list, list) and len(sensor_list) > 0:
                self._data = sensor_list[0]
            else:
                self._data = sensor_list
        else:
            self._data = response
    
    @property
    def name(self) -> str:
        """Get sensor name."""
        return self._data.get("name", f"IAQ Sensor {self.sensor_id}")
    
    @property
    def co2_level(self) -> int:
        """Get CO2 level in ppm."""
        return self._data.get("co2_value", 0)
    
    @property
    def pm25_level(self) -> int:
        """Get PM2.5 level in μg/m³."""
        return self._data.get("pm2_5_value", 0)
    
    @property
    def pm10_level(self) -> int:
        """Get PM10 level in μg/m³."""
        return self._data.get("pm10_value", 0)
    
    @property
    def tvoc_level(self) -> int:
        """Get Total Volatile Organic Compounds level in ppb."""
        return self._data.get("tvoc_value", 0)
    
    @property
    def pressure(self) -> float:
        """Get atmospheric pressure in hPa."""
        return self._data.get("pressure_value", 0.0)
    
    @property
    def iaq_index(self) -> int:
        """Get IAQ index (1-3, where 1=Good, 2=Medium, 3=Bad)."""
        return self._data.get("iaq_index", 0)
    
    @property
    def iaq_score(self) -> int:
        """Get IAQ score (0-100, where 100=Excellent, 0=Poor)."""
        return self._data.get("iaq_score", 0)
    
    @property
    def iaq_index_name(self) -> str:
        """Get human-readable IAQ index name."""
        index_names = {
            1: "Good",
            2: "Medium", 
            3: "Bad"
        }
        return index_names.get(self.iaq_index, "Unknown")
    
    @property
    def ventilation_mode(self) -> Optional[int]:
        """Get current ventilation mode."""
        return self._data.get("iaq_mode_vent")
    
    @ventilation_mode.setter
    def ventilation_mode(self, mode: int) -> None:
        """Set ventilation mode.
        
        Args:
            mode: Ventilation mode (0=Off, 1=On, 2=Auto)
            
        Raises:
            ValueError: If mode is invalid
        """
        if mode not in [0, 1, 2]:
            raise ValueError("Ventilation mode must be 0 (Off), 1 (On), or 2 (Auto)")
        
        self.client.set_iaq_parameters(self.system_id, self.sensor_id, {"iaq_mode_vent": mode})
        self.refresh(force_refresh=True)
    
    def set_ventilation_mode(self, mode: int) -> None:
        """Set ventilation mode.
        
        Args:
            mode: Ventilation mode (0=Off, 1=On, 2=Auto)
        """
        self.ventilation_mode = mode
    
    @property
    def air_quality_summary(self) -> Dict[str, Any]:
        """Get comprehensive air quality summary."""
        return {
            "overall_index": self.iaq_index,
            "overall_score": self.iaq_score,
            "quality_name": self.iaq_index_name,
            "measurements": {
                "co2_ppm": self.co2_level,
                "pm2_5_ugm3": self.pm25_level,
                "pm10_ugm3": self.pm10_level,
                "tvoc_ppb": self.tvoc_level,
                "pressure_hpa": self.pressure
            },
            "ventilation_mode": self.ventilation_mode
        }
    
    def __str__(self) -> str:
        """String representation of IAQ sensor."""
        return f"IAQ Sensor {self.sensor_id} (System {self.system_id}): {self.iaq_index_name} (Score: {self.iaq_score}/100)"


if __name__ == "__main__":
    main()