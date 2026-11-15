"""Count actual ASGI bytes, including chunked bodies, before JSON parsing."""

import asyncio

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send


class BodyLimitMiddleware:
    def __init__(self, app: ASGIApp, maximum: int = 512000):
        self.app, self.maximum = app, maximum

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        chunks = []
        size = 0
        try:
            async with asyncio.timeout(8):
                while True:
                    message = await receive()
                    if message["type"] == "http.disconnect":
                        return
                    body = message.get("body", b"")
                    size += len(body)
                    if size > self.maximum:
                        await JSONResponse(
                            {"error": {"code": "too_large", "message": "Request too large."}}, 413
                        )(scope, receive, send)
                        return
                    chunks.append(body)
                    if not message.get("more_body", False):
                        break
        except TimeoutError:
            await JSONResponse(
                {"error": {"code": "body_timeout", "message": "Request body timed out."}}, 408
            )(scope, receive, send)
            return
        pending = True

        async def replay() -> Message:
            nonlocal pending
            if pending:
                pending = False
                return {"type": "http.request", "body": b"".join(chunks), "more_body": False}
            return await receive()

        await self.app(scope, replay, send)
