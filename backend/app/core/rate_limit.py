from dataclasses import dataclass
from threading import Lock
from time import monotonic

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core.config import Settings


@dataclass
class RateLimitBucket:
    window_started_at: float
    request_count: int = 0


class RateLimiter:
    def __init__(self) -> None:
        self._buckets: dict[str, RateLimitBucket] = {}
        self._lock = Lock()

    def allow(
        self,
        key: str,
        limit: int,
        window_seconds: int,
    ) -> tuple[bool, int]:
        now = monotonic()
        with self._lock:
            bucket = self._buckets.get(key)
            if bucket is None or now - bucket.window_started_at >= window_seconds:
                bucket = RateLimitBucket(window_started_at=now)
                self._buckets[key] = bucket
            bucket.request_count += 1
            remaining = max(limit - bucket.request_count, 0)
            return bucket.request_count <= limit, remaining

    def reset(self) -> None:
        with self._lock:
            self._buckets.clear()


rate_limiter = RateLimiter()


def configure_rate_limiting(app: FastAPI, settings: Settings) -> None:
    exempt_paths = {"/health", "/ready", "/metrics"}

    @app.middleware("http")
    async def rate_limit_requests(request: Request, call_next):
        if not settings.rate_limit_enabled or request.url.path in exempt_paths:
            return await call_next(request)

        client_host = request.client.host if request.client else "unknown"
        key = f"{client_host}:{request.url.path}"
        allowed, remaining = rate_limiter.allow(
            key,
            settings.rate_limit_requests,
            settings.rate_limit_window_seconds,
        )
        if not allowed:
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded."},
                headers={
                    "Retry-After": str(settings.rate_limit_window_seconds),
                    "X-RateLimit-Limit": str(settings.rate_limit_requests),
                    "X-RateLimit-Remaining": "0",
                },
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(settings.rate_limit_requests)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        return response
