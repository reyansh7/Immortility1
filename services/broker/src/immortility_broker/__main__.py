"""Private stdout handshake to the native parent; stdin closure shuts down the broker."""

import asyncio
import json
import secrets
import socket
import sys
import threading

import uvicorn

from .app import create_app
from .config import Settings


def main() -> None:
    settings = Settings()
    settings.load_credentials()
    token = secrets.token_urlsafe(32)
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.bind(("127.0.0.1", 0))
    listener.listen(128)
    port = listener.getsockname()[1]
    url = f"http://127.0.0.1:{port}"
    app = create_app(settings, token, url)
    server = uvicorn.Server(uvicorn.Config(app, log_level="critical", access_log=False))

    def parent_watch() -> None:
        sys.stdin.buffer.read()
        server.should_exit = True

    threading.Thread(target=parent_watch, daemon=True).start()
    print(json.dumps({"url": url, "token": token}), flush=True)
    asyncio.run(server.serve(sockets=[listener]))


if __name__ == "__main__":
    main()
