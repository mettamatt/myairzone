#!/usr/bin/env python3
"""Airzone zone class for managing individual HVAC zones."""

from typing import Dict, List, Optional, Union, TYPE_CHECKING
import logging

from .models import MODES, MODE_IDS

if TYPE_CHECKING:
    from .client import AirzoneClient


class AirzoneZone:
    """Class representing an Airzone zone."""
    
    def __init__(self, client: 'AirzoneClient', system_id: int, zone_id: int, 
                 data: Optional[Dict] = None):
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
        self.logger = logging.getLogger(f"airzone_zone_{system_id}_{zone_id}")
    
    def refresh(self, force_refresh: bool = False) -> None:
        """Refresh zone data.
        
        Args:
            force_refresh: Force refresh from API
        """
        response = self.client.get_zone(self.system_id, self.zone_id, force_refresh=force_refresh)
        if isinstance(response, dict) and "data" in response:
            # API returns data as a list with one zone
            zone_list = response["data"]
            if isinstance(zone_list, list) and len(zone_list) > 0:
                self._data = zone_list[0]
            else:
                self._data = zone_list
        else:
            self._data = response
    
    # Basic properties
    @property
    def name(self) -> str:
        """Get zone name."""
        return self._data.get("name", f"Zone {self.zone_id}")
    
    @property
    def is_on(self) -> bool:
        """Check if zone is on."""
        return self._data.get("on", 0) == 1
    
    @property
    def on(self) -> bool:
        """Alias for is_on."""
        return self.is_on
    
    @on.setter
    def on(self, value: bool) -> None:
        """Set zone on/off state."""
        self.client.set_zone_parameters(self.system_id, self.zone_id, {"on": 1 if value else 0})
        self._data["on"] = 1 if value else 0
    
    def turn_on(self) -> None:
        """Turn zone on."""
        self.on = True
    
    def turn_off(self) -> None:
        """Turn zone off."""
        self.on = False
    
    # Temperature properties
    @property
    def room_temp(self) -> float:
        """Get current room temperature."""
        return self._data.get("roomTemp", 0.0)
    
    @property
    def setpoint(self) -> float:
        """Get current setpoint temperature."""
        return self._data.get("setpoint", 0.0)
    
    @setpoint.setter
    def setpoint(self, value: float) -> None:
        """Set target temperature."""
        self.client.set_zone_parameters(self.system_id, self.zone_id, {"setpoint": value})
        self._data["setpoint"] = value

    # Mode properties
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
        return MODES.get(self.mode, "Unknown")
    
    @mode.setter
    def mode(self, value: int) -> None:
        """Set mode.
        
        Args:
            value: Mode ID (1: stop, 2: cooling, 3: heating, 4: ventilation, 5: dehumidify)
            
        Raises:
            ValueError: If mode is not supported
        """
        if not self.validate_mode(value):
            available_modes = self._data.get("modes", [])
            available_names = [f"{m}({MODES.get(m, 'Unknown')})" for m in available_modes]
            raise ValueError(f"Mode {value} not supported. Available: {available_names}")
            
        self.client.set_zone_parameters(self.system_id, self.zone_id, {"mode": value})
        self._data["mode"] = value
    
    # Environmental properties
    @property
    def humidity(self) -> int:
        """Get current humidity percentage."""
        return self._data.get("humidity", 0)
    
    # Fan properties
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
        """Set fan speed."""
        if not self.validate_fan_speed(speed):
            raise ValueError(f"Invalid fan speed: {speed}")
        self.client.set_zone_parameters(self.system_id, self.zone_id, {"speed": speed})
        self._data["speed"] = speed
    
    # Sleep timer
    @property
    def sleep_timer(self) -> int:
        """Get sleep timer in minutes."""
        return self._data.get("sleep", 0)
    
    # Error handling
    @property
    def errors(self) -> List[Dict]:
        """Get zone errors."""
        return self._data.get("errors", [])
    
    @property
    def has_errors(self) -> bool:
        """Check if zone has errors."""
        return len(self.errors) > 0
    
    @sleep_timer.setter
    def sleep_timer(self, minutes: int) -> None:
        """Set sleep timer (0-1440 minutes)."""
        if not 0 <= minutes <= 1440:
            raise ValueError(f"Sleep timer must be 0-1440 minutes")
        self.client.set_zone_parameters(self.system_id, self.zone_id, {"sleep": minutes})
        self._data["sleep"] = minutes
    
    # Validation methods
    def validate_mode(self, mode: int) -> bool:
        """Validate if mode is supported."""
        available_modes = self._data.get("modes", [])
        return not available_modes or mode in available_modes
    
    def validate_fan_speed(self, speed: int) -> bool:
        """Validate fan speed."""
        available_speeds = self.available_fan_speeds
        if available_speeds:
            return speed in available_speeds
        max_speeds = self._data.get("speeds")
        if max_speeds is not None:
            return 0 <= speed <= max_speeds
        return True
    
    def validate_temperature(self, temp: float) -> bool:
        """Validate temperature setpoint."""
        min_temp = self._data.get("minTemp", 15)
        max_temp = self._data.get("maxTemp", 30)
        return min_temp <= temp <= max_temp
    
    def __repr__(self) -> str:
        """String representation."""
        return f"<AirzoneZone {self.zone_id}: {self.name}>"
