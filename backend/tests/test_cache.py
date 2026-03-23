# backend/tests/test_cache.py - Cache tests including Redis

import pytest
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestInMemoryCache:
    """Test in-memory cache functionality"""
    
    def test_get_cache_empty(self):
        """Test getting from empty cache"""
        from utils.cache import get_cache, clear_cache
        
        clear_cache()
        result = get_cache("nonexistent")
        assert result is None
    
    def test_set_and_get_cache(self):
        """Test setting and getting cache"""
        from utils.cache import set_cache, get_cache, clear_cache
        
        clear_cache()
        
        test_data = {"key": "value", "nested": {"data": 123}}
        set_cache("test_key", test_data)
        
        result = get_cache("test_key")
        assert result == test_data
    
    def test_clear_single_key(self):
        """Test clearing single key"""
        from utils.cache import set_cache, get_cache, clear_cache
        
        clear_cache()
        
        set_cache("key1", "value1")
        set_cache("key2", "value2")
        
        clear_cache("key1")
        
        assert get_cache("key1") is None
        assert get_cache("key2") == "value2"
    
    def test_clear_all(self):
        """Test clearing entire cache"""
        from utils.cache import set_cache, get_cache, clear_cache
        
        clear_cache()
        
        set_cache("key1", "value1")
        set_cache("key2", "value2")
        
        clear_cache()
        
        assert get_cache("key1") is None
        assert get_cache("key2") is None


class TestAsyncCache:
    """Test async cache functionality"""
    
    @pytest.mark.asyncio
    async def test_async_get_empty(self):
        """Test async getting from empty cache"""
        from utils.cache import get_cache_async, clear_cache_async
        
        await clear_cache_async()
        result = await get_cache_async("nonexistent")
        assert result is None
    
    @pytest.mark.asyncio
    async def test_async_set_and_get(self):
        """Test async setting and getting"""
        from utils.cache import set_cache_async, get_cache_async, clear_cache_async
        
        await clear_cache_async()
        
        test_data = {"key": "value"}
        await set_cache_async("async_key", test_data)
        
        result = await get_cache_async("async_key")
        assert result == test_data
    
    @pytest.mark.asyncio
    async def test_async_clear(self):
        """Test async clearing"""
        from utils.cache import set_cache_async, get_cache_async, clear_cache_async
        
        await clear_cache_async()
        
        await set_cache_async("key1", "value1")
        await set_cache_async("key2", "value2")
        
        await clear_cache_async()
        
        assert await get_cache_async("key1") is None
        assert await get_cache_async("key2") is None


class TestCacheConfiguration:
    """Test cache configuration"""
    
    def test_redis_availability_check(self):
        """Test Redis availability check"""
        from utils.cache import is_redis_available, REDIS_AVAILABLE
        
        # Should return False if Redis not connected
        result = is_redis_available()
        assert isinstance(result, bool)
    
    def test_cache_ttl_default(self):
        """Test default cache TTL"""
        from utils.cache import CACHE_TTL
        
        assert CACHE_TTL == 3600  # Default 1 hour
    
    def test_redis_prefix(self):
        """Test Redis key prefix"""
        from utils.cache import REDIS_PREFIX
        
        assert REDIS_PREFIX == "bsi:"
