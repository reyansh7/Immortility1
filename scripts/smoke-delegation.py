"""One real delegated turn through the broker and Hermes.

Research and coding run together, then review, then the parent combines them.
Uses the verified free OpenRouter route. Prints status and roles only.
"""

import asyncio
import json
import socket
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "services/broker/src"))

import httpx
import uvicorn

from immortility_broker.app import create_app
from immortility_broker.config import Settings


async def main() -> None:
    settings = Settings()
    settings.load_credentials()
    settings.delegation_enabled = True
    token = "delegate-smoke-" + "x" * 32
    with tempfile.TemporaryDirectory() as directory:
        settings.data_dir = Path(directory)
        listener = socket.socket()
        listener.bind(("127.0.0.1", 0))
        listener.listen()
        base = f"http://127.0.0.1:{listener.getsockname()[1]}"
        app = create_app(settings, token, base)
        server = uvicorn.Server(uvicorn.Config(app, log_level="critical", access_log=False))
        runner = asyncio.create_task(server.serve(sockets=[listener]))
        try:
            while not server.started:
                if runner.done():
                    await runner
                await asyncio.sleep(0.02)
            async with httpx.AsyncClient(
                base_url=base,
                headers={"Authorization": f"Bearer {token}"},
                trust_env=False,
                timeout=280,
            ) as client:
                health = (await client.get("/health/ready")).json()
                print("Hermes:", health.get("hermes"), flush=True)
                print("Delegation:", health.get("delegation_enabled"), flush=True)
                session = (await client.post("/v1/sessions")).json()["id"]
                created = await client.post(
                    "/v1/tasks",
                    json={
                        "session_id": session,
                        "request_id": "delegate-live",
                        "content": (
                            "In one sentence: what is two plus two, "
                            "and name the Python function that returns the length of a string."
                        ),
                        "cloud_consent": True,
                        "response_length": "brief",
                    },
                )
                created.raise_for_status()
                task_id = created.json()["task_id"]
                async with client.stream("GET", f"/v1/tasks/{task_id}/events") as events:
                    async for line in events.aiter_lines():
                        if not line.startswith("data: "):
                            continue
                        event = json.loads(line[6:])
                        if event["type"] in {
                            "agent.started",
                            "agent.completed",
                            "audit.notice",
                            "task.error",
                        }:
                            print(event["type"], event.get("data"), flush=True)
                result = (await client.get(f"/v1/tasks/{task_id}")).json()
                trace = (await client.get(f"/v1/tasks/{task_id}/trace")).json()
                text = (result.get("result") or {}).get("text") or ""
                print("STATUS", result["status"], flush=True)
                print("CALLS", app.state.engine.calls, flush=True)
                print(
                    "DELEGATIONS",
                    [(item["role"], item["status"]) for item in trace.get("delegations", [])],
                    flush=True,
                )
                print("TOOLS", trace.get("tools"), flush=True)
                print("ANSWER", " ".join(text.split())[:400], flush=True)
                if result.get("error"):
                    print("ERROR", result["error"].get("code"), result["error"].get("message"), flush=True)
                if result["status"] != "succeeded":
                    raise SystemExit(1)
        finally:
            server.should_exit = True
            await runner


if __name__ == "__main__":
    asyncio.run(main())
