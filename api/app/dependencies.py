"""
FastAPI dependency injection utilities.

This module provides dependency functions for injecting services
into FastAPI route handlers.
"""

from app.services.cache_service import CacheService, get_cache_service


def get_cache() -> CacheService:
    """
    FastAPI dependency for getting the cache service.

    Usage:
        @router.get("/endpoint")
        async def handler(cache: CacheService = Depends(get_cache)):
            value = await cache.get("key")
            ...

    Returns:
        The global CacheService instance.
    """
    return get_cache_service()
