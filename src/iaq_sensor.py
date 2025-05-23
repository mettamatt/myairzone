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
        """Refresh sensor data.
        
        Args:
            force_refresh: Force refresh from API
        """
        response = self.client.get_iaq_sensor(self.system_id, self.sensor_id, force_refresh)
        if isinstance(response, dict) and "data" in response:
            sensor_list = response["data"]
            if isinstance(sensor_list, list) and len(sensor_list) > 0:
                self._data = sensor_list[0]
            else:
                self._data = sensor_list
        else:
            self._data = response
    
    # Basic properties
    @property
    def name(self) -> str:
        """Get sensor name."""
        return self._data.get("name", f"IAQ Sensor {self.sensor_id}")
    
    # Air quality measurements (read-only)
    @property
    def co2_level(self) -> float:
        """Get CO2 level in ppm."""
        return self._data.get("co2_value", 0.0)
    
    @property
    def pm2_5_level(self) -> float:
        """Get PM2.5 level in μg/m³."""
        return self._data.get("pm2_5_value", 0.0)
    
    @property
    def pm10_level(self) -> float:
        """Get PM10 level in μg/m³."""
        return self._data.get("pm10_value", 0.0)
    
    @property
    def tvoc_level(self) -> float:
        """Get TVOC level in ppb."""
        return self._data.get("tvoc_value", 0.0)
    
    @property
    def pressure(self) -> float:
        """Get atmospheric pressure in hPa."""
        return self._data.get("pressure_value", 0.0)
    
    @property
    def iaq_index(self) -> int:
        """Get air quality index (1=Good, 2=Medium, 3=Bad)."""
        return self._data.get("iaq_index", 0)
    
    @property
    def iaq_quality(self) -> str:
        """Get air quality as text."""
        return IAQ_QUALITY_INDEX.get(self.iaq_index, "Unknown")
    
    @property
    def iaq_score(self) -> int:
        """Get air quality score (0-100)."""
        return self._data.get("iaq_score", 0)

    # Ventilation control
    @property
    def ventilation_mode(self) -> int:
        """Get ventilation mode (0=Off, 1=On, 2=Auto)."""
        return self._data.get("iaq_mode_vent", 0)
    
    @property
    def ventilation_mode_name(self) -> str:
        """Get ventilation mode name."""
        return IAQ_VENTILATION_MODES.get(self.ventilation_mode, "Unknown")
    
    @ventilation_mode.setter
    def ventilation_mode(self, mode: int) -> None:
        """Set ventilation mode.
        
        Args:
            mode: 0=Off, 1=On, 2=Auto
            
        Raises:
            ValueError: If mode is invalid
        """
        if mode not in IAQ_VENTILATION_MODES:
            raise ValueError(f"Invalid ventilation mode: {mode}. Valid: 0=Off, 1=On, 2=Auto")
        
        self.client.set_iaq_parameters(self.system_id, self.sensor_id, {"iaq_mode_vent": mode})
        self._data["iaq_mode_vent"] = mode
    
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
