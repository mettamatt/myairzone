#!/usr/bin/env python3
"""Airzone IAQ sensor class for managing air quality sensors."""

from typing import Dict, Optional, Union, TYPE_CHECKING
import logging

from .models import IAQ_VENTILATION_MODES, IAQ_QUALITY_INDEX

if TYPE_CHECKING:
    from .client import AirzoneClient


class AirzoneIAQSensor:
    """Class representing an Airzone Indoor Air Quality sensor."""
    
    def __init__(self, client: 'AirzoneClient', system_id: int, sensor_id: int, 
                 data: Optional[Dict] = None):
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
        self.logger = logging.getLogger(f"airzone_iaq_{system_id}_{sensor_id}")
    
    def refresh(self, force_refresh: bool = False) -> None:
        """Refresh sensor data (from zone data).
        
        Args:
            force_refresh: Force refresh from API
        """
        # Get zone data since IAQ is embedded in zones (sensor_id = zone_id)
        response = self.client.get_zone(self.system_id, self.sensor_id, force_refresh)
        if isinstance(response, dict) and "data" in response:
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
        """Get sensor name (zone name for IAQ)."""
        return self._data.get("name", f"Zone {self.sensor_id}")
    
    # Air quality measurements (zone-based parameters)
    @property
    def co2_level(self) -> float:
        """Get CO2 level in ppm (not available in zone-based IAQ)."""
        return self._data.get("co2_value", 0.0)
    
    @property
    def pm2_5_level(self) -> float:
        """Get PM2.5 level in μg/m³ (not available in zone-based IAQ)."""
        return self._data.get("pm2_5_value", 0.0)
    
    @property
    def pm10_level(self) -> float:
        """Get PM10 level in μg/m³ (not available in zone-based IAQ)."""
        return self._data.get("pm10_value", 0.0)
    
    @property
    def tvoc_level(self) -> float:
        """Get TVOC level in ppb (not available in zone-based IAQ)."""
        return self._data.get("tvoc_value", 0.0)
    
    @property
    def pressure(self) -> float:
        """Get atmospheric pressure in hPa (not available in zone-based IAQ)."""
        return self._data.get("pressure_value", 0.0)
    
    @property
    def iaq_index(self) -> int:
        """Get air quality index from zone aq_quality parameter."""
        return self._data.get("aq_quality", 0)
    
    @property
    def iaq_quality(self) -> str:
        """Get air quality as text."""
        quality_map = {0: "Good", 1: "Medium", 2: "Poor"}
        return quality_map.get(self.iaq_index, "Unknown")
    
    @property
    def iaq_score(self) -> int:
        """Get air quality score (derived from aq_quality)."""
        # Convert aq_quality to a score-like value
        quality = self._data.get("aq_quality", 0)
        score_map = {0: 90, 1: 60, 2: 30}  # Good=90, Medium=60, Poor=30
        return score_map.get(quality, 0)
    
    @property
    def low_threshold(self) -> int:
        """Get air quality low threshold."""
        return self._data.get("aq_thrlow", 0)
    
    @property
    def high_threshold(self) -> int:
        """Get air quality high threshold."""
        return self._data.get("aq_thrhigh", 0)

    # Ventilation control (zone-based air quality mode)
    @property
    def ventilation_mode(self) -> int:
        """Get air quality mode from zone aq_mode parameter."""
        return self._data.get("aq_mode", 0)
    
    @property
    def ventilation_mode_name(self) -> str:
        """Get air quality mode name."""
        mode_map = {0: "Off", 1: "On", 2: "Auto"}
        return mode_map.get(self.ventilation_mode, "Unknown")
    
    @ventilation_mode.setter
    def ventilation_mode(self, mode: int) -> None:
        """Set air quality mode.
        
        Args:
            mode: 0=Off, 1=On, 2=Auto
            
        Raises:
            ValueError: If mode is invalid
        """
        if mode not in [0, 1, 2]:
            raise ValueError(f"Invalid air quality mode: {mode}. Valid: 0=Off, 1=On, 2=Auto")
        
        # Use zone control to set aq_mode (sensor_id = zone_id)
        self.client.set_zone_parameters(self.system_id, self.sensor_id, {"aq_mode": mode})
        self._data["aq_mode"] = mode
    
    def set_ventilation_mode(self, mode: Union[int, str]) -> None:
        """Set ventilation mode by ID or name.
        
        Args:
            mode: Mode ID (0,1,2) or name ("off", "on", "auto")
        """
        if isinstance(mode, str):
            mode_map = {"off": 0, "on": 1, "auto": 2}
            mode = mode_map.get(mode.lower())
            if mode is None:
                raise ValueError("Mode must be 'off', 'on', or 'auto'")
        self.ventilation_mode = mode
    
    def __repr__(self) -> str:
        """String representation."""
        return f"<AirzoneIAQSensor {self.sensor_id}: {self.name}>"
