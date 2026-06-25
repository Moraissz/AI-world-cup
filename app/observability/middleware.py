import json
import time
import uuid

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = structlog.get_logger(__name__)

_MAX_BODY_BYTES = 2048


def _parse_body(raw: bytes) -> "dict | list | str | None":
    if not raw:
        return None
    try:
        parsed = json.loads(raw)
        text = json.dumps(parsed, ensure_ascii=False)
        if len(text) > _MAX_BODY_BYTES:
            return text[:_MAX_BODY_BYTES] + "...[truncated]"
        return parsed
    except (json.JSONDecodeError, UnicodeDecodeError):
        decoded = raw.decode("utf-8", errors="replace")
        if len(decoded) > _MAX_BODY_BYTES:
            return decoded[:_MAX_BODY_BYTES] + "...[truncated]"
        return decoded


async def _capture_response_body(response: Response) -> "tuple[bytes, Response]":
    body = b""
    async for chunk in response.body_iterator:
        body += chunk
    rebuilt = Response(
        content=body,
        status_code=response.status_code,
        headers=dict(response.headers),
        media_type=response.media_type,
    )
    return body, rebuilt


class CorrelationIdMiddleware:
    """Pure ASGI middleware — sets request_id/chat_id context vars and injects x-request-id response header."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        raw_headers = dict(scope.get("headers", []))
        request_id = raw_headers.get(b"x-request-id", b"").decode() or str(uuid.uuid4())
        chat_id = raw_headers.get(b"x-chat-id", b"").decode() or None

        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id, chat_id=chat_id)

        async def send_with_headers(message):
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers.append((b"x-request-id", request_id.encode()))
                message = {**message, "headers": headers}
            await send(message)

        try:
            await self.app(scope, receive, send_with_headers)
        finally:
            structlog.contextvars.clear_contextvars()


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        t0 = time.perf_counter()

        req_body = None
        if "application/json" in request.headers.get("content-type", ""):
            req_body = _parse_body(await request.body())

        response = await call_next(request)
        latency_ms = round((time.perf_counter() - t0) * 1000, 1)

        resp_raw, response = await _capture_response_body(response)
        resp_body = _parse_body(resp_raw)

        extra = {}
        if req_body is not None:
            extra["request_body"] = req_body
        if resp_body is not None:
            extra["response_body"] = resp_body

        qs = request.url.query
        path = f"{request.url.path}?{qs}" if qs else request.url.path

        log = logger.error if response.status_code >= 400 else logger.info
        log(
            "request.completed",
            method=request.method,
            path=path,
            status_code=response.status_code,
            latency_ms=latency_ms,
            **extra,
        )

        return response
