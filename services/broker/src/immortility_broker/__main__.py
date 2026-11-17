"""Private stdout handshake to the native parent; stdin closure shuts down the broker."""

import asyncio
import argparse
import json
import secrets
import socket
import sys
import threading
import os
from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import SettingsConfigDict

import uvicorn

from .app import create_app
from .config import Settings
from .contracts import uid


class LocalHeadlessSettings(Settings):
    model_config = SettingsConfigDict(env_file=None, extra="ignore")


def main() -> None:
    parser = argparse.ArgumentParser(description="Immortility broker; no service is installed.")
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("--local-workflows", action="store_true")
    parser.add_argument("--standard-mcp", action="store_true")
    parser.add_argument("--data-dir", type=Path)
    parser.add_argument("--publish-attachment", action="store_true")
    args = parser.parse_args()
    settings: Settings
    if args.headless:
        if args.data_dir is None or not args.local_workflows:
            parser.error("Headless mode requires --data-dir and explicit --local-workflows.")
        if args.publish_attachment and os.name != "nt":
            parser.error("Attachment publication requires current-user Windows DPAPI.")
        settings = LocalHeadlessSettings(
            data_dir=args.data_dir.resolve(),
            hermes_source=args.data_dir.resolve() / "disabled-hermes",
            local_only_mode=True,
            durable_workflows_enabled=True,
            local_tools_enabled=True,
            standard_mcp_enabled=args.standard_mcp,
            openrouter_api_key=SecretStr(""),
            gemini_api_key=SecretStr(""),
            groq_api_key=SecretStr(""),
            nvidia_api_key=SecretStr(""),
            infernal_voice_enabled=False,
            reference_voice_enabled=False,
            workspace_tools_enabled=False,
            delegation_enabled=False,
            web_research_enabled=False,
        )
    else:
        if (
            args.local_workflows
            or args.standard_mcp
            or args.data_dir is not None
            or args.publish_attachment
        ):
            parser.error("These switches require explicit --headless mode.")
        settings = Settings()
        settings.load_credentials()
    token = secrets.token_urlsafe(32)
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.bind(("127.0.0.1", 0))
    listener.listen(128)
    port = listener.getsockname()[1]
    url = f"http://127.0.0.1:{port}"
    instance_id = uid()
    publication: tuple[Path, bytes] | None = None

    def cleanup_publication() -> None:
        nonlocal publication
        if publication:
            from .attachment import unpublish

            unpublish(*publication)
            publication = None

    def stop_runtime() -> None:
        server.should_exit = True

    app = create_app(
        settings,
        token,
        url,
        instance_id=instance_id,
        shutdown_hook=cleanup_publication if args.publish_attachment else None,
        stop_runtime=stop_runtime if args.headless else None,
    )
    if settings.data_dir.name.startswith("canary-"):
        (settings.data_dir / "startup-trace.json").write_text(
            json.dumps(
                {
                    "data_dir": str(settings.data_dir),
                    "hermes_0232_gateway": settings.hermes_0232_gateway,
                    "simulated_inference": settings.simulated_inference,
                }
            ),
            encoding="utf-8",
        )
    server = uvicorn.Server(uvicorn.Config(app, log_level="critical", access_log=False))

    def parent_watch() -> None:
        sys.stdin.buffer.read()
        server.should_exit = True

    if not args.headless:
        threading.Thread(target=parent_watch, daemon=True).start()

    async def run() -> None:
        nonlocal publication
        if not args.publish_attachment:
            print(json.dumps({"url": url, "token": token}), flush=True)
            await server.serve(sockets=[listener])
            return
        from .attachment import publish

        serving = asyncio.create_task(server.serve(sockets=[listener]))
        try:
            async with asyncio.timeout(10):
                while not server.started:
                    if serving.done():
                        await serving
                        raise RuntimeError("Background runtime did not become ready")
                    await asyncio.sleep(0.02)
            publication = await asyncio.to_thread(
                publish, settings.data_dir, url, token, instance_id
            )
            # Publication mode never prints the local bearer credential to logs/console.
            print(
                json.dumps({"status": "background-ready", "instance_id": instance_id}), flush=True
            )
            await serving
        finally:
            cleanup_publication()
            server.should_exit = True
            if not serving.done():
                await serving

    asyncio.run(run())


if __name__ == "__main__":
    main()
