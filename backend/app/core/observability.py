import json
import logging
from time import perf_counter
from uuid import UUID, uuid4

from fastapi import FastAPI, Request, Response

logger = logging.getLogger("lionsforge.request")


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
        except Exception:
            duration_ms = round((perf_counter() - started_at) * 1000, 2)
            logger.exception(
                json.dumps(
                    {
                        "event": "http_request",
                        "request_id": request_id,
                        "method": request.method,
                        "path": request.url.path,
                        "status_code": status_code,
                        "duration_ms": duration_ms,
                    }
                )
            )
            raise

        duration_ms = round((perf_counter() - started_at) * 1000, 2)
        response.headers["x-request-id"] = request_id
        logger.info(
            json.dumps(
                {
                    "event": "http_request",
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": status_code,
                    "duration_ms": duration_ms,
                }
            )
        )
        return response
