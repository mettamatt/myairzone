#!/usr/bin/env python3
"""Shared models and constants for Airzone system."""

from typing import Dict, Any, Optional, Tuple

# Operating modes for HVAC systems
MODES = {
    1: "Stop",
    2: "Cooling", 
    3: "Heating",
    4: "Ventilation",
    5: "Dehumidify"
}

# Reverse mapping for mode names to IDs
MODE_IDS = {v: k for k, v in MODES.items()}

# IAQ sensor ventilation modes
IAQ_VENTILATION_MODES = {
    0: "Off",
    1: "On",
    2: "Auto"
}

# Cache key patterns for different API endpoints
CACHE_KEY_PATTERNS = {
    ('version', None): 'version',
    ('webserver', None): 'webserver',
    ('hvac', frozenset([('systemID', 127)])): 'systems',
    ('hvac', frozenset([('systemID', 0), ('zoneID', 0)])): 'zones',
    ('iaq', frozenset([('systemID', 127)])): 'iaq_sensors',
}

# API endpoints
API_ENDPOINTS = {
    'version': 'version',
    'webserver': 'webserver', 
    'hvac': 'hvac',
    'iaq': 'iaq',
    'demo': 'demo'
}

# Zone property metadata for dynamic property creation
ZONE_PROPERTIES = {
    'on': {'type': bool, 'writable': True, 'api_name': 'on'},
    'setpoint': {'type': float, 'writable': True, 'api_name': 'setpoint'},
    'roomTemp': {'type': float, 'writable': False, 'api_name': 'roomTemp'},
    'mode': {'type': int, 'writable': True, 'api_name': 'mode'},
    'fanSpeed': {'type': int, 'writable': True, 'api_name': 'fanSpeed'},
    'humidity': {'type': float, 'writable': False, 'api_name': 'humidity'},
}

# IAQ sensor property metadata
IAQ_PROPERTIES = {
    'co2_value': {'type': float, 'writable': False, 'unit': 'ppm'},
    'pm2_5_value': {'type': float, 'writable': False, 'unit': 'μg/m³'},
    'pm10_value': {'type': float, 'writable': False, 'unit': 'μg/m³'},
    'tvoc_value': {'type': float, 'writable': False, 'unit': 'ppb'},
    'pressure_value': {'type': float, 'writable': False, 'unit': 'hPa'},
    'iaq_index': {'type': int, 'writable': False, 'unit': None},
    'iaq_score': {'type': int, 'writable': False, 'unit': None},
    'iaq_mode_vent': {'type': int, 'writable': True, 'unit': None},
}

# IAQ quality index meanings
IAQ_QUALITY_INDEX = {
    1: "Good",
    2: "Medium", 
    3: "Bad"
}
