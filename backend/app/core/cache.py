import time
from typing import Dict, Any, Optional
import redis
import json
from .config import settings
from .logging import get_logger

logger = get_logger(__name__)

class SimpleCache:
    """
    A simple in-memory cache with time-to-live (TTL) support.
    """
    _cache: Dict[str, Any] = {}
    _ttl: Dict[str, float] = {}

    def set(self, key: str, value: Any, ttl_seconds: int = 60):
        """
        Set a value in the cache with a specific TTL.
        """
        self._cache[key] = value
        self._ttl[key] = time.time() + ttl_seconds

    def get(self, key: str) -> Optional[Any]:
        """
        Get a value from the cache. Returns None if the key is not found or has expired.
        """
        if key in self._cache:
            if time.time() < self._ttl[key]:
                return self._cache[key]
            else:
                # Clean up expired key
                del self._cache[key]
                del self._ttl[key]
        return None

    def update_prices(self, prices: Dict[str, Any], ttl_seconds: int = 300):
        """
        A convenience method to update multiple price tickers in the cache.
        """
        for symbol, price_data in prices.items():
            # The key for a ticker will be `ticker_{symbol}`
            self.set(f"ticker_{symbol.upper()}", price_data, ttl_seconds)

# Global instance of the cache
price_cache = SimpleCache()

class Cache:
    def __init__(self, redis_url: str):
        try:
            self.redis = redis.from_url(redis_url, decode_responses=True)
            self.redis.ping()
            logger.info(f"Successfully connected to Redis cache at {redis_url}.")
        except redis.exceptions.ConnectionError as e:
            logger.error(f"Could not connect to Redis at {redis_url}: {e}", exc_info=True)
            self.redis = None

    def get(self, key: str) -> Optional[Any]:
        if not self.redis:
            return None
        try:
            cached_value = self.redis.get(key)
            if cached_value:
                return json.loads(cached_value)
        except Exception as e:
            logger.error(f"Error getting value from Redis cache for key '{key}': {e}", exc_info=True)
        return None

    def set(self, key: str, value: Any, ttl_seconds: int = 60):
        if not self.redis:
            return
        try:
            serialized_value = json.dumps(value)
            self.redis.setex(key, ttl_seconds, serialized_value)
        except Exception as e:
            logger.error(f"Error setting value in Redis cache for key '{key}': {e}", exc_info=True)

    def delete(self, key: str):
        if not self.redis:
            return
        try:
            self.redis.delete(key)
        except Exception as e:
            logger.error(f"Error deleting key from Redis cache: {e}", exc_info=True)

# Use the REDIS_URL from settings
cache_client = Cache(settings.REDIS_URL)

def get_cache_key_for_user_portfolio(user_id: int) -> str:
    """Generates a consistent cache key for a user's portfolio."""
    return f"portfolio:{user_id}" 