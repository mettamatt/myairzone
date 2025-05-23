#!/usr/bin/env python3
import json
import os
import time
import shutil
import datetime
from typing import Dict, Any, Optional, List
import logging

logger = logging.getLogger("airzone_cache")

class AirzoneCache:
    """Cache for Airzone system and zone data to reduce API calls."""
    
    def __init__(self, cache_dir: str = None, max_age: int = 300):
        """Initialize the cache.
        
        Args:
            cache_dir: Directory to store cache files (defaults to ~/.airzone_cache)
            max_age: Maximum age of cache data in seconds (defaults to 5 minutes)
        """
        self.cache_dir = cache_dir or os.path.expanduser("~/.airzone_cache")
        self.max_age = max_age
        
        # Create cache directory if it doesn't exist
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)
            logger.info(f"Created cache directory: {self.cache_dir}")
    
    def _get_cache_path(self, key: str) -> str:
        """Get path to cache file for a given key.
        
        Args:
            key: Cache key
            
        Returns:
            Path to cache file
        """
        return os.path.join(self.cache_dir, f"{key}.json")
    
    def get(self, key: str) -> Optional[Dict[str, Any]]:
        """Get cached data for a given key.
        
        Args:
            key: Cache key
            
        Returns:
            Cached data or None if not found or expired
        """
        cache_path = self._get_cache_path(key)
        
        if not os.path.exists(cache_path):
            logger.debug(f"Cache miss: {key} (file not found)")
            return None
        
        # Check if cache is expired
        file_age = time.time() - os.path.getmtime(cache_path)
        if file_age > self.max_age:
            logger.debug(f"Cache expired: {key} (age: {file_age}s, max: {self.max_age}s)")
            return None
        
        try:
            with open(cache_path, "r") as f:
                data = json.load(f)
                logger.debug(f"Cache hit: {key}")
                return data
        except Exception as e:
            logger.error(f"Error reading cache: {str(e)}")
            return None
    
    def set(self, key: str, data: Dict[str, Any]) -> bool:
        """Set cached data for a given key.
        
        Args:
            key: Cache key
            data: Data to cache
            
        Returns:
            True if successful, False otherwise
        """
        cache_path = self._get_cache_path(key)
        
        try:
            with open(cache_path, "w") as f:
                json.dump(data, f, indent=2)
            logger.debug(f"Cache set: {key}")
            return True
        except Exception as e:
            logger.error(f"Error writing cache: {str(e)}")
            return False
    
    def invalidate(self, key: str) -> bool:
        """Invalidate cached data for a given key.
        
        Args:
            key: Cache key
            
        Returns:
            True if successful, False otherwise
        """
        cache_path = self._get_cache_path(key)
        
        if os.path.exists(cache_path):
            try:
                os.remove(cache_path)
                logger.debug(f"Cache invalidated: {key}")
                return True
            except Exception as e:
                logger.error(f"Error invalidating cache: {str(e)}")
                return False
        
        logger.debug(f"Cache already invalid: {key}")
        return True
    
    def invalidate_all(self) -> bool:
        """Invalidate all cached data.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            for filename in os.listdir(self.cache_dir):
                if filename.endswith(".json"):
                    os.remove(os.path.join(self.cache_dir, filename))
            logger.debug("All cache invalidated")
            return True
        except Exception as e:
            logger.error(f"Error invalidating all cache: {str(e)}")
            return False

# Examples of cache key formats:
# - version: "version"
# - webserver: "webserver"
# - all systems: "systems"
# - specific system: f"system_{system_id}"
# - all zones: "zones"
# - specific zone: f"zone_{system_id}_{zone_id}"