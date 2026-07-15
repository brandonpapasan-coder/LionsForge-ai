import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import Lock
from time import perf_counter
from typing import TypedDict
from uuid import UUID, uuid4

from fastapi import FastAPI, Request, Response

logger = logging.getLogger("lionsforge.request")


class RequestMetricsSnapshot(TypedDict):
    request_count: int
    error_count: int
    average_duration_ms: float
    status_codes: dict[int, int]


@dataclass(frozen=True)
class ErrorEvent:
    request_id: str
    method: str
    path: str
    exception_type: str
    occurred_at: datetime


class ErrorMetricsSnapshot(TypedDict):
    total_count: int
    by_exception_type: dict[str, int]
    last_event: ErrorEvent | None


@dataclass
class RequestMetricsRegistry:
    request_count: int = 0
    error_count: int = 0
    total_duration_ms: float = 0.0
    status_codes: dict[int, int] = field(default_factory=dict)
    _lock: Lock = field(default_factory=Lock, repr=False)

    def record(self, status_code: int, duration_ms: float) -> None:
        with self._lock:
            self.request_count += 1
            if status_code >= 500:
                self.error_count += 1
            self.total_duration_ms += duration_ms
            self.status_codes[status_code] = self.status_codes.get(status_code, 0) + 1

    def snapshot(self) -> RequestMetricsSnapshot:
        with self._lock:
            average_duration_ms = self.total_duration_ms / self.request_count if self.request_count else 0.0
            return {
                "request_count": self.request_count,
                "error_count": self.error_count,
                "average_duration_ms": round(average_duration_ms, 2),
                "status_codes": dict(sorted(self.status_codes.items())),
            }

    def reset(self) -> None:
        with self._lock:
            self.request_count = 0
            self.error_count = 0
            self.total_duration_ms = 0.0
            self.status_codes.clear()


@dataclass
class ErrorEventRegistry:
    total_count: int = 0
    by_exception_type: dict[str, int] = field(default_factory=dict)
    last_event: ErrorEvent | None = None
    _lock: Lock = field(default_factory=Lock, repr=False)

    def record(self, request_id: str, method: str, path: str, exception: Exception) -> None:
        event = ErrorEvent(
            request_id=request_id,
            method=method,
            path=path,
            exception_type=exception.__class__.__name__,
            occurred_at=datetime.now(timezone.utc),
        )
        with self._lock:
            self.total_count += 1
            self.by_exception_type[event.exception_type] = self.by_exception_type.get(event.exception_type, 0) + 1
            self.last_event = event

    def snapshot(self) -> ErrorMetricsSnapshot:
        with self._lock:
            return {
                "total_count": self.total_count,
                "by_exception_type": dict(sorted(self.by_exception_type.items())),
                "last_event": self.last_event,
            }

    def reset(self) -> None:
        with self._lock:
            self.total_count = 0
            self.by_exception_type.clear()
            self.last_event = None


request_metrics_registry = RequestMetricsRegistry()
error_event_registry = ErrorEventRegistry()


def _request_id(value: str | None) -> str:
    if value:
        try:
            return str(UUID(value))
        except ValueError:
            pass
    return str(uuid4())


def configure_request_observability(app: FastAPI) -> None:
    @app.middleware("http")
    async def request_observability(request: Request, call_next) -> Response:
        request_id = _request_id(request.headers.get("x-request-id"))
        started_at = perf_counter()
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception as exc:
            duration_ms = round((perf_counter() - started_at) * 1000, 2)
            request_metrics_registry.record(status_code, duration_ms)
            error_event_registry.record(request_id, request.method, request.url.path, exc)
            logger.exception(json.dumps({
                "event": "http_request_error",
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": status_code,
                "duration_ms": duration_ms,
                "exception_type": exc.__class__.__name__,
            }))
            raise
        duration_ms = round((perf_counter() - started_at) * 1000, 2)
        request_metrics_registry.record(status_code, duration_ms)
        response.headers["x-request-id"] = request_id
        logger.info(json.dumps({
            "event": "http_request",
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status_code": status_code,
            "duration_ms": duration_ms,
        }))
        return response
