"""
Redis cache service with graceful degradation.

This service provides caching functionality using Redis for frequently accessed data.
It implements a cache-aside pattern with graceful degradation - if Redis is unavailable,
the application continues to work by falling back to direct database queries.

Features:
- orjson for fast JSON serialization (3-10x faster than stdlib json)
- Graceful degradation (cache failures don't break the application)
- Key prefixing for organization
- Pattern-based cache invalidation
- Async operations with redis-py

Source: https://redis-py.readthedocs.io/en/stable/examples/asyncio_examples.html
"""

from collections.abc import Awaitable, Callable
from typing import Any

import orjson
import redis.asyncio as redis
from redis.asyncio.connection import ConnectionPool

from app.config import get_settings
from app.utils.logging import get_logger

logger = get_logger(__name__)


class CacheService:
    """
    Redis cache service with graceful degradation.

    This class provides async caching operations with automatic fallback
    when Redis is unavailable. All cache failures are logged but don't
    raise exceptions to ensure application stability.

    Usage:
        cache = CacheService(pool)

        # Simple get/set
        await cache.set("key", {"data": "value"}, ttl=300)
        value = await cache.get("key")

        # Get or compute pattern
        result = await cache.get_or_compute(
            key="expensive:query",
            compute_func=lambda: expensive_db_query(),
            ttl=600
        )
    """

    def __init__(self, pool: ConnectionPool | None = None) -> None:
        """
        Initialize the cache service.

        Args:
            pool: Redis connection pool. If None, caching is disabled.
        """
        self._pool = pool
        self._enabled = pool is not None

    @property
    def enabled(self) -> bool:
        """Check if caching is enabled."""
        return self._enabled

    async def _get_client(self) -> redis.Redis | None:
        """Get a Redis client from the pool."""
        if not self._enabled or self._pool is None:
            return None
        return redis.Redis(connection_pool=self._pool)

    async def ping(self) -> bool:
        """
        Check if Redis is reachable.

        Returns:
            True if Redis responds to ping, False otherwise.
        """
        if not self._enabled:
            return False
        try:
            client = await self._get_client()
            if client:
                return await client.ping()
        except Exception as e:
            logger.warning(f"Redis ping failed: {e}")
        return False

    async def get(self, key: str) -> Any | None:
        """
        Get a value from the cache.

        Args:
            key: The cache key.

        Returns:
            The cached value deserialized from JSON, or None if not found or error.
        """
        if not self._enabled:
            return None
        try:
            client = await self._get_client()
            if client:
                data = await client.get(key)
                if data:
                    return orjson.loads(data)
        except Exception as e:
            logger.warning(f"Cache get failed for key '{key}': {e}")
        return None

    async def set(self, key: str, value: Any, ttl: int | None = None) -> bool:
        """
        Set a value in the cache.

        Args:
            key: The cache key.
            value: The value to cache (must be JSON serializable).
            ttl: Time to live in seconds. Uses default TTL if not specified.

        Returns:
            True if the value was cached successfully, False otherwise.
        """
        if not self._enabled:
            return False

        settings = get_settings()
        ttl = ttl or settings.cache_default_ttl

        try:
            client = await self._get_client()
            if client:
                data = orjson.dumps(value)
                await client.setex(key, ttl, data)
                return True
        except Exception as e:
            logger.warning(f"Cache set failed for key '{key}': {e}")
        return False

    async def delete(self, key: str) -> bool:
        """
        Delete a key from the cache.

        Args:
            key: The cache key to delete.

        Returns:
            True if the key was deleted, False otherwise.
        """
        if not self._enabled:
            return False
        try:
            client = await self._get_client()
            if client:
                await client.delete(key)
                return True
        except Exception as e:
            logger.warning(f"Cache delete failed for key '{key}': {e}")
        return False

    async def delete_pattern(self, pattern: str) -> int:
        """
        Delete all keys matching a pattern.

        Uses Redis SCAN for safe iteration over large keyspaces.

        Args:
            pattern: The pattern to match (e.g., "cache:analytics:*").

        Returns:
            Number of keys deleted, or 0 on error.
        """
        if not self._enabled:
            return 0
        try:
            client = await self._get_client()
            if client:
                deleted = 0
                async for key in client.scan_iter(match=pattern):
                    await client.delete(key)
                    deleted += 1
                if deleted > 0:
                    logger.debug(f"Cache invalidation: deleted {deleted} keys matching '{pattern}'")
                return deleted
        except Exception as e:
            logger.warning(f"Cache delete_pattern failed for '{pattern}': {e}")
        return 0

    async def get_or_compute(
        self,
        key: str,
        compute_func: Callable[[], Awaitable[Any]],
        ttl: int | None = None,
    ) -> Any:
        """
        Get a value from cache, or compute and cache it if not found.

        This implements the cache-aside pattern:
        1. Try to get the value from cache
        2. If cache miss, compute the value
        3. Store the computed value in cache
        4. Return the value

        The compute function is always called on cache miss, even if caching
        is disabled or fails. This ensures the application works without Redis.

        Args:
            key: The cache key.
            compute_func: Async function to compute the value on cache miss.
            ttl: Time to live in seconds.

        Returns:
            The cached or computed value.
        """
        # Try cache first
        cached = await self.get(key)
        if cached is not None:
            logger.debug(f"Cache hit for '{key}'")
            return cached

        # Cache miss - compute the value
        logger.debug(f"Cache miss for '{key}', computing...")
        value = await compute_func()

        # Store in cache (fire and forget - don't block on cache set)
        await self.set(key, value, ttl)

        return value


# Global cache service instance (initialized in main.py lifespan)
_cache_service: CacheService | None = None


def get_cache_service() -> CacheService:
    """
    Get the global cache service instance.

    Returns:
        The cache service, or a disabled instance if not initialized.
    """
    global _cache_service
    if _cache_service is None:
        # Return a disabled cache service if not initialized
        return CacheService(pool=None)
    return _cache_service


def set_cache_service(service: CacheService) -> None:
    """
    Set the global cache service instance.

    Called during application startup to initialize the cache.

    Args:
        service: The cache service instance.
    """
    global _cache_service
    _cache_service = service


async def create_redis_pool() -> ConnectionPool | None:
    """
    Create a Redis connection pool.

    Returns:
        ConnectionPool if successful, None if Redis is disabled or unavailable.
    """
    settings = get_settings()

    if not settings.redis_enabled:
        logger.info("Redis caching is disabled by configuration")
        return None

    try:
        pool = ConnectionPool.from_url(
            settings.redis_url,
            max_connections=settings.redis_max_connections,
            socket_timeout=settings.redis_socket_timeout,
            socket_connect_timeout=settings.redis_socket_timeout,
            decode_responses=False,  # We handle encoding with orjson
        )

        # Test the connection
        client = redis.Redis(connection_pool=pool)
        await client.ping()
        logger.info(f"Redis connection pool created (max_connections={settings.redis_max_connections})")
        return pool

    except Exception as e:
        logger.warning(f"Failed to create Redis pool, caching disabled: {e}")
        return None


async def close_redis_pool(pool: ConnectionPool | None) -> None:
    """
    Close the Redis connection pool.

    Args:
        pool: The connection pool to close.
    """
    if pool:
        try:
            await pool.disconnect()
            logger.info("Redis connection pool closed")
        except Exception as e:
            logger.warning(f"Error closing Redis pool: {e}")
