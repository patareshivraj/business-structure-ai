# backend/utils/rate_limiter.py - Rate limiting and API cost control

import os
import time
import logging
from typing import Dict, Optional
from dataclasses import dataclass, field
from threading import Lock
from collections import defaultdict


logger = logging.getLogger(__name__)


@dataclass
class RateLimitConfig:
    """Rate limit configuration"""
    max_requests_per_minute: int = 60
    max_requests_per_hour: int = 1000
    max_api_calls_per_request: int = 20  # Hard cap on external API calls
    enable_cost_tracking: bool = True


@dataclass
class RequestStats:
    """Request statistics for monitoring"""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    rate_limited_requests: int = 0
    api_calls_this_request: int = 0
    last_request_time: float = field(default_factory=time.time)
    

class RateLimiter:
    """
    Token bucket rate limiter with cost control.
    Prevents API abuse and runaway costs from external services.
    """
    
    _instance: Optional['RateLimiter'] = None
    _lock = Lock()
    
    def __new__(cls, *args, **kwargs):
        # Singleton pattern for application-wide rate limiting
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, config: Optional[RateLimitConfig] = None):
        if hasattr(self, '_initialized'):
            return
        
        self._initialized = True
        
        # Load configuration from environment or use defaults
        self.config = config or RateLimitConfig(
            max_requests_per_minute=int(os.getenv("RATE_LIMIT_PER_MINUTE", "60")),
            max_requests_per_hour=int(os.getenv("RATE_LIMIT_PER_HOUR", "1000")),
            max_api_calls_per_request=int(os.getenv("MAX_API_CALLS_PER_REQUEST", "20")),
            enable_cost_tracking=os.getenv("ENABLE_COST_TRACKING", "true").lower() == "true"
        )
        
        # Token bucket state
        self._tokens: Dict[str, float] = defaultdict(lambda: self.config.max_requests_per_minute)
        self._last_refill: Dict[str, float] = defaultdict(time.time)
        
        # Request tracking
        self._request_history: Dict[str, list] = defaultdict(list)
        self._stats = RequestStats()
        self._stats_lock = Lock()
        
        logger.info(f"Rate limiter initialized: {self.config.max_requests_per_minute} req/min, "
                   f"{self.config.max_api_calls_per_request} max API calls/request")
    
    def _refill_tokens(self, key: str = "default"):
        """Refill tokens based on time elapsed"""
        now = time.time()
        elapsed = now - self._last_refill[key]
        
        # Refill at tokens per second rate
        tokens_per_second = self.config.max_requests_per_minute / 60.0
        new_tokens = self._tokens[key] + (elapsed * tokens_per_second)
        
        # Cap at max
        self._tokens[key] = min(new_tokens, self.config.max_requests_per_minute)
        self._last_refill[key] = now
    
    def check_rate_limit(self, key: str = "default") -> bool:
        """
        Check if request is allowed under rate limit.
        
        Args:
            key: Identifier for rate limit bucket (e.g., IP, user ID)
            
        Returns:
            True if request allowed, False if rate limited
        """
        self._refill_tokens(key)
        
        if self._tokens[key] >= 1:
            self._tokens[key] -= 1
            return True
        return False
    
    def check_api_call_limit(self) -> bool:
        """
        Check if we can make another external API call.
        Hard cap to prevent runaway costs.
        
        Returns:
            True if API call allowed, False if at limit
        """
        if not self.config.enable_cost_tracking:
            return True
        
        with self._stats_lock:
            return self._stats.api_calls_this_request < self.config.max_api_calls_per_request
    
    def increment_api_calls(self):
        """Increment API call counter for current request"""
        if self.config.enable_cost_tracking:
            with self._stats_lock:
                self._stats.api_calls_this_request += 1
                
                # Log warning if approaching limit
                if self._stats.api_calls_this_request == self.config.max_api_calls_per_request - 5:
                    logger.warning(f"Approaching API call limit: {self.config.max_api_calls_per_request}")
    
    def record_request(self, success: bool = True):
        """Record request outcome for statistics"""
        with self._stats_lock:
            self._stats.total_requests += 1
            if success:
                self._stats.successful_requests += 1
            else:
                self._stats.failed_requests += 1
    
    def record_rate_limit_hit(self):
        """Record when rate limit was hit"""
        with self._stats_lock:
            self._stats.rate_limited_requests += 1
    
    def start_request_tracking(self):
        """Initialize tracking for a new request"""
        with self._stats_lock:
            self._stats.api_calls_this_request = 0
    
    def reset_request_counter(self):
        """Reset the request-level counter"""
        with self._stats_lock:
            self._stats.api_calls_this_request = 0
    
    def get_stats(self) -> Dict:
        """Get current rate limiter statistics"""
        with self._stats_lock:
            return {
                "total_requests": self._stats.total_requests,
                "successful_requests": self._stats.successful_requests,
                "failed_requests": self._stats.failed_requests,
                "rate_limited_requests": self._stats.rate_limited_requests,
                "api_calls_this_request": self._stats.api_calls_this_request,
                "tokens_available": dict(self._tokens)
            }
    
    def is_available(self) -> bool:
        """Check if system is available (not overwhelmed)"""
        with self._stats_lock:
            # Consider system overwhelmed if >50% of hourly limit used
            return self._stats.total_requests < (self.config.max_requests_per_hour * 0.5)


# Global rate limiter instance
_rate_limiter: Optional[RateLimiter] = None


def get_rate_limiter() -> RateLimiter:
    """Get the global rate limiter instance"""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
    return _rate_limiter


def check_rate_limit(key: str = "default") -> bool:
    """Convenience function for rate limit checking"""
    return get_rate_limiter().check_rate_limit(key)


def check_api_call_limit() -> bool:
    """Convenience function for API call limit checking"""
    return get_rate_limiter().check_api_call_limit()


def increment_api_calls():
    """Convenience function to increment API call counter"""
    get_rate_limiter().increment_api_calls()


def start_request_tracking():
    """Convenience function to reset counter for new request"""
    get_rate_limiter().start_request_tracking()


if __name__ == "__main__":
    # Test rate limiter
    limiter = RateLimiter()
    
    print("Testing rate limiter...")
    for i in range(65):
        allowed = limiter.check_rate_limit("test")
        print(f"Request {i+1}: {'✓' if allowed else '✗'}")
    
    print(f"\nStats: {limiter.get_stats()}")