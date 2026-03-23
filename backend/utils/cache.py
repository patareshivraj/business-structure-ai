# backend/utils/cache.py - Async cache with Redis support and fallback

import os
import json
from typing import Optional, Any
import asyncio
import logging
from threading import Lock
from collections import defaultdict

logger = logging.getLogger(__name__)

# Try to import Redis, fall back to in-memory if not available
try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("Redis not available, using in-memory cache")


# Configuration
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", None)
REDIS_PREFIX = os.getenv("REDIS_PREFIX", "bsi:")
CACHE_TTL = int(os.getenv("CACHE_TTL", "3600"))  # Default 1 hour

# In-memory fallback cache with thread safety
MEMORY_CACHE = {}
_CACHE_LOCK = Lock()  # Thread lock for memory cache operations


class RedisCache:
    """Async Redis cache wrapper with fallback to in-memory"""
    
    def __init__(self):
        self._client = None
        self._connected = False
    
    async def connect(self):
        """Connect to Redis"""
        if not REDIS_AVAILABLE:
            return False
        
        try:
            self._client = redis.Redis(
                host=REDIS_HOST,
                port=REDIS_PORT,
                db=REDIS_DB,
                password=REDIS_PASSWORD,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5
            )
            # Test connection
            await self._client.ping()
            self._connected = True
            logger.info(f"Connected to Redis at {REDIS_HOST}:{REDIS_PORT}")
            return True
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}. Using in-memory cache.")
            self._connected = False
            return False
    
    async def disconnect(self):
        """Disconnect from Redis"""
        if self._client:
            await self._client.close()
            self._connected = False
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        # Use Redis if connected
        if self._connected and self._client:
            try:
                value = await self._client.get(f"{REDIS_PREFIX}{key}")
                if value:
                    return json.loads(value)
            except Exception as e:
                logger.warning(f"Redis get failed: {e}")
        
        # Fallback to memory
        return MEMORY_CACHE.get(key)
    
    async def set(self, key: str, value: Any, ttl: int = CACHE_TTL) -> None:
        """Set value in cache"""
        # Use Redis if connected
        if self._connected and self._client:
            try:
                serialized = json.dumps(value)
                await self._client.setex(
                    f"{REDIS_PREFIX}{key}",
                    ttl,
                    serialized
                )
                return
            except Exception as e:
                logger.warning(f"Redis set failed: {e}")
        
        # Fallback to memory
        MEMORY_CACHE[key] = value
    
    async def delete(self, key: str) -> None:
        """Delete key from cache"""
        if self._connected and self._client:
            try:
                await self._client.delete(f"{REDIS_PREFIX}{key}")
            except Exception as e:
                logger.warning(f"Redis delete failed: {e}")
        
        MEMORY_CACHE.pop(key, None)
    
    async def clear(self, pattern: str = None) -> None:
        """Clear cache"""
        if self._connected and self._client:
            try:
                if pattern:
                    keys = await self._client.keys(f"{REDIS_PREFIX}{pattern}")
                    if keys:
                        await self._client.delete(*keys)
                else:
                    # Clear all with our prefix
                    keys = await self._client.keys(f"{REDIS_PREFIX}*")
                    if keys:
                        await self._client.delete(*keys)
            except Exception as e:
                logger.warning(f"Redis clear failed: {e}")
        
        if pattern:
            for key in list(MEMORY_CACHE.keys()):
                if pattern in key:
                    del MEMORY_CACHE[key]
        else:
            MEMORY_CACHE.clear()


# Global cache instance
_cache = RedisCache()


# -----------------------------
# Synchronous functions (backward compatibility)
# -----------------------------

def get_cache(key: str) -> Optional[Any]:
    """Synchronous cache get - for backward compatibility"""
    with _CACHE_LOCK:
        try:
            return MEMORY_CACHE.get(key)
        except Exception:
            return None


def set_cache(key: str, value: Any) -> None:
    """Synchronous cache set - for backward compatibility"""
    with _CACHE_LOCK:
        try:
            MEMORY_CACHE[key] = value
        except Exception:
            pass


def clear_cache(key: Optional[str] = None) -> None:
    """Clear specific key or entire cache"""
    with _CACHE_LOCK:
        if key is None:
            MEMORY_CACHE.clear()
        else:
            MEMORY_CACHE.pop(key, None)


# -----------------------------
# Async functions
# -----------------------------

async def get_cache_async(key: str) -> Optional[Any]:
    """Async cache get - for use with async endpoints"""
    return await _cache.get(key)


async def set_cache_async(key: str, value: Any, ttl: int = CACHE_TTL) -> None:
    """Async cache set - for use with async endpoints"""
    await _cache.set(key, value, ttl)


async def clear_cache_async(key: Optional[str] = None) -> None:
    """Async cache clear - for use with async endpoints"""
    await _cache.clear(key)


async def init_cache() -> bool:
    """Initialize Redis connection"""
    return await _cache.connect()


async def close_cache() -> None:
    """Close Redis connection"""
    await _cache.disconnect()


def is_redis_available() -> bool:
    """Check if Redis is available"""
    return REDIS_AVAILABLE and _cache._connected
