"""
Airzone HVAC Control System

A streamlined Python toolkit for backing up, monitoring, and controlling Airzone HVAC systems.
"""

from .client import AirzoneClient
from .system import AirzoneSystem
from .zone import AirzoneZone
from .iaq_sensor import AirzoneIAQSensor
from .airzone_backup import AirzoneBackup
from .airzone_cache import AirzoneCache
from .airzone_errors import get_error_description, get_error_solutions, save_error_log, print_error_details

__version__ = "1.0.0"
__all__ = [
    "AirzoneClient",
    "AirzoneSystem", 
    "AirzoneZone",
    "AirzoneIAQSensor",
    "AirzoneBackup",
    "AirzoneCache",
    "get_error_description",
    "get_error_solutions",
    "save_error_log",
    "print_error_details",
]
