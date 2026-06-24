import time
import uuid

import structlog

logger = structlog.get_logger(__name__)


class CorrelationIdMiddleware:
    """Pure ASGI middleware — avoids BaseHTTPMiddleware streaming issues."""

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

        t0 = time.perf_counter()
        status_code = 500

        async def send_with_headers(message):
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
                headers = list(message.get("headers", []))
                headers.append((b"x-request-id", request_id.encode()))
                message = {**message, "headers": headers}
            await send(message)

        try:
            await self.app(scope, receive, send_with_headers)
        finally:
            latency_ms = round((time.perf_counter() - t0) * 1000, 1)
            log = logger.error if status_code >= 300 else logger.info
            log(
                "request.completed",
                method=scope.get("method", ""),
                path=scope.get("path", ""),
                status_code=status_code,
                latency_ms=latency_ms,
            )
            structlog.contextvars.clear_contextvars()
