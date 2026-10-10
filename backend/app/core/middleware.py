import time
import uuid

from starlette.datastructures import Headers
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.logging import get_logger, request_id_ctx_var

logger = get_logger("app.middleware")

HEALTH_CHECK_PATHS: frozenset[str] = frozenset(
    {
        "/api/v1/utils/health-check",
        "/api/v1/utils/health-check/",
    }
)


class RequestLoggingMiddleware:
    """ASGI middleware that injects a correlation ID (X-Request-ID),

    tracks latency, and logs HTTP requests.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = Headers(scope=scope)
        request_id = (
            headers.get("x-request-id")
            or headers.get("x-correlation-id")
            or uuid.uuid4().hex[:12]
        )
        token = request_id_ctx_var.set(request_id)

        start_time = time.perf_counter()
        status_code: int = 500

        async def send_wrapper(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message.get("status", 200)
                headers_list: list[tuple[bytes, bytes]] = list(
                    message.get("headers", [])
                )
                has_x_request_id = any(
                    h[0].lower() == b"x-request-id" for h in headers_list
                )
                if not has_x_request_id:
                    headers_list.append((b"x-request-id", request_id.encode("latin-1")))
                message["headers"] = headers_list
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        except Exception as exc:
            duration_ms = (time.perf_counter() - start_time) * 1000
            method = scope.get("method", "GET")
            path = scope.get("path", "")
            logger.exception(
                f"{method} {path} - 500 Internal Server Error ({duration_ms:.2f}ms) - Exception: {exc}"
            )
            raise
        finally:
            duration_ms = (time.perf_counter() - start_time) * 1000
            method = scope.get("method", "GET")
            path = scope.get("path", "")
            query_string = scope.get("query_string", b"").decode("latin-1")
            full_path = f"{path}?{query_string}" if query_string else path

            client = scope.get("client")
            client_ip = client[0] if client else "unknown"

            log_msg = f"{method} {full_path} - {status_code} ({duration_ms:.2f}ms) - client: {client_ip}"

            if path in HEALTH_CHECK_PATHS:
                logger.debug(log_msg)
            elif status_code >= 500:
                logger.error(log_msg)
            elif status_code >= 400:
                logger.warning(log_msg)
            else:
                logger.info(log_msg)

            request_id_ctx_var.reset(token)
