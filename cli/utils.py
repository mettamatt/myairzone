#!/usr/bin/env python3
"""Utilities for CLI commands to reduce code duplication."""

import json
import logging
from functools import wraps
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger("airzone_cli")


def handle_cli_errors(func: Callable) -> Callable:
    """Decorator to handle CLI command errors consistently.
    
    Args:
        func: Function to wrap
        
    Returns:
        Wrapped function with error handling
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            print(f"Error: {str(e)}")
            logger.exception(f"Command {func.__name__} failed")
            return 1
    return wrapper


def print_json_or_text(data: Any, as_json: bool = False) -> None:
    """Print data as JSON or formatted text.
    
    Args:
        data: Data to print
        as_json: Whether to print as JSON
    """
    if as_json:
        print(json.dumps(data, indent=2))
    else:
        print(data)


def format_entity_info(entity: Any, entity_type: str) -> str:
    """Format entity information for display.
    
    Args:
        entity: Entity object (zone, system, sensor)
        entity_type: Type of entity
        
    Returns:
        Formatted string
    """
    info = [f"\n{entity_type} {getattr(entity, 'id', 'Unknown')}: {entity.name}"]
    
    # Common attributes
    if hasattr(entity, 'on'):
        info.append(f"  Power: {'On' if entity.on else 'Off'}")
    
    if hasattr(entity, 'room_temp'):
        info.append(f"  Temperature: {entity.room_temp}°C")
    
    if hasattr(entity, 'setpoint'):
        info.append(f"  Setpoint: {entity.setpoint}°C")
    
    if hasattr(entity, 'mode_name'):
        info.append(f"  Mode: {entity.mode_name}")
    
    if hasattr(entity, 'humidity'):
        info.append(f"  Humidity: {entity.humidity}%")
    
    if hasattr(entity, 'fan_speed'):
        info.append(f"  Fan Speed: {entity.fan_speed}")
    
    # IAQ sensor specific
    if hasattr(entity, 'co2_level'):
        info.append(f"  CO2: {entity.co2_level} ppm")
    
    if hasattr(entity, 'iaq_quality'):
        info.append(f"  Air Quality: {entity.iaq_quality}")
    
    if hasattr(entity, 'ventilation_mode_name'):
        info.append(f"  Ventilation: {entity.ventilation_mode_name}")
    
    # Error information
    if hasattr(entity, 'errors') and entity.errors:
        info.append(f"  Errors: {entity.errors}")
    
    return '\n'.join(info)


def create_client(host: str, port: int, no_cache: bool = False) -> 'AirzoneClient':
    """Create an AirzoneClient instance with standard configuration.
    
    Args:
        host: Host IP address
        port: Port number
        no_cache: Whether to disable caching
        
    Returns:
        Configured AirzoneClient instance
    """
    from src.client import AirzoneClient
    return AirzoneClient(host=host, port=port, use_cache=not no_cache)
