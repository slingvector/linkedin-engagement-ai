import time
from typing import Callable, Dict, Optional
from fastapi import Request, Response, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
import redis
import structlog

from app.config import get_settings, get_yaml_config

logger = structlog.get_logger()

class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Redis-backed rate limiting middleware.
    Enforces the limits defined in config.yaml.
    """
    def __init__(self, app):
        super().__init__(app)
        settings = get_settings()
        self.redis = redis.from_url(settings.redis_url)
        self.config = get_yaml_config().get("rate_limits", {})
        
        # Mapping of path prefixes to their relevant limit keys in config.yaml
        self.route_map = {
            "/api/v1/posts/generate": "post_generation",
            "/api/v1/creators/comments/generate": "comment_generation",
            "/api/v2/posts/": "post_generation",  # Catch-all for V2 post actions
        }

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # 1. Identify if this route needs rate limiting
        limit_key = self._get_limit_key(request.url.path)
        if not limit_key:
            return await call_next(request)

        # 2. Identify the user (or IP as fallback)
        # We look for the user ID in the request scope if get_current_user has run,
        # but since middleware runs before dependencies, we might need to check the token manually
        # OR we limit by IP for now as a simple implementation.
        # In a real app, we'd extract the user_id from the JWT.
        client_id = self._get_client_id(request)
        
        # 3. Check Minute Limit
        minute_limit = self.config.get(limit_key, {}).get("max_per_minute", 10)
        if not self._check_limit(f"rate_limit:{limit_key}:min:{client_id}", minute_limit, 60):
            logger.warning("rate_limit_exceeded_minute", client_id=client_id, route=request.url.path)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded (minute). Please slow down."
            )

        # 4. Check Day Limit (Simplified - ignoring free/pro tier for now)
        day_limit = self.config.get(limit_key, {}).get("max_per_day_pro", 50)
        if not self._check_limit(f"rate_limit:{limit_key}:day:{client_id}", day_limit, 86400):
            logger.warning("rate_limit_exceeded_day", client_id=client_id, route=request.url.path)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Daily quota exceeded for this action."
            )

        return await call_next(request)

    def _get_limit_key(self, path: str) -> Optional[str]:
        for prefix, key in self.route_map.items():
            if path.startswith(prefix):
                return key
        return None

    def _get_client_id(self, request: Request) -> str:
        # Fallback to IP address
        return request.client.host if request.client else "unknown"

    def _check_limit(self, key: str, limit: int, window: int) -> bool:
        """
        Generic window-based rate limiter using Redis.
        Returns True if allowed, False if blocked.
        """
        try:
            current = self.redis.get(key)
            if current is not None and int(current) >= limit:
                return False
            
            # Use a pipeline to ensure atomic increment and expire
            pipe = self.redis.pipeline()
            pipe.incr(key)
            if current is None:
                pipe.expire(key, window)
            pipe.execute()
            return True
        except Exception as e:
            logger.error("redis_rate_limit_error", error=str(e))
            return True  # Fail open to avoid blocking users if Redis is down
