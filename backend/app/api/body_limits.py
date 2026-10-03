"""A bounded upload gate before framework parsing or application dispatch."""

import asyncio
import re

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

MAX_BODY_BYTES = 120_000
UPLOAD_SECONDS = 10.0


class _Rejected(Exception):
    def __init__(self, status: int, detail: str) -> None:
        self.status = status
        self.detail = detail


class RequestBodyLimitMiddleware:
    def __init__(
        self,
        app: ASGIApp,
        *,
        max_bytes: int = MAX_BODY_BYTES,
        timeout_seconds: float = UPLOAD_SECONDS,
    ) -> None:
        self.app = app
        self.max_bytes = max_bytes
        self.timeout_seconds = timeout_seconds

    def _declared_length(self, scope: Scope) -> int | None:
        headers: dict[bytes, list[bytes]] = {}
        for key, value in scope.get("headers", []):
            if key.lower() in {b"content-length", b"transfer-encoding", b"content-encoding"}:
                headers.setdefault(key.lower(), []).append(value.strip().lower())
        lengths = headers.get(b"content-length", [])
        transfer = headers.get(b"transfer-encoding", [])
        if len(lengths) > 1 or (lengths and transfer) or (transfer and transfer != [b"chunked"]):
            raise _Rejected(400, "Ambiguous or unsupported request framing.")
        encoding = headers.get(b"content-encoding", [])
        if encoding and encoding != [b"identity"]:
            raise _Rejected(
                415, "Compressed request bodies are not supported. Send uncompressed JSON."
            )
        if not lengths:
            return None
        if re.fullmatch(rb"[0-9]{1,20}", lengths[0]) is None:
            raise _Rejected(400, "Invalid request Content-Length.")
        length = int(lengths[0])
        if length > self.max_bytes:
            raise _Rejected(
                413,
                f"Request body exceeds the {self.max_bytes:,}-byte limit. Keep your input and reduce its size.",
            )
        return length

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        chunks: list[bytes] = []
        size = 0
        try:
            declared = self._declared_length(scope)
            expires_at = asyncio.get_running_loop().time() + self.timeout_seconds
            async with asyncio.timeout(self.timeout_seconds):
                while True:
                    # Yield even for immediately available empty frames so the deadline can fire.
                    await asyncio.sleep(0)
                    message = await receive()
                    if message["type"] == "http.disconnect":
                        return
                    if asyncio.get_running_loop().time() >= expires_at:
                        raise TimeoutError
                    if message["type"] != "http.request":
                        raise _Rejected(400, "Invalid request body event.")
                    chunk = message.get("body", b"")
                    size += len(chunk)
                    if size > self.max_bytes:
                        raise _Rejected(
                            413,
                            f"Request body exceeds the {self.max_bytes:,}-byte limit. Keep your input and reduce its size.",
                        )
                    if declared is not None and size > declared:
                        raise _Rejected(400, "Request body does not match Content-Length.")
                    if chunk:
                        chunks.append(chunk)
                    if not message.get("more_body", False):
                        break
            if declared is not None and size != declared:
                raise _Rejected(400, "Request body does not match Content-Length.")
        except (TimeoutError, _Rejected) as exc:
            status = exc.status if isinstance(exc, _Rejected) else 408
            detail = (
                exc.detail
                if isinstance(exc, _Rejected)
                else (
                    "Request upload timed out before processing. Keep your input and retry when the connection is stable."
                )
            )
            headers = {
                "Cache-Control": "no-store",
                "Referrer-Policy": "no-referrer",
                "X-Content-Type-Options": "nosniff",
            }
            if scope.get("http_version", "1.1").startswith("1."):
                headers["Connection"] = "close"
            await JSONResponse({"detail": detail}, status_code=status, headers=headers)(
                scope, receive, send
            )
            return

        buffered: bytes | None = b"".join(chunks)
        chunks.clear()

        async def admitted_receive() -> Message:
            nonlocal buffered
            if buffered is not None:
                body, buffered = buffered, None
                return {"type": "http.request", "body": body, "more_body": False}
            # Preserve downstream disconnect observation; do not manufacture one.
            return await receive()

        # The upload deadline ends before parsing, execution and response streaming.
        await self.app(scope, admitted_receive, send)
