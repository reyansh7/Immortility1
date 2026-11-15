"""Two public synthetic prompts, real Hermes, explicit opt-in live free route.

No existing history, project notes, audio, screenshots or files are sent. Keys
remain in memory. The broker and HTTP transport independently cap calls; no retry.
"""

import argparse
import asyncio
import json
import socket
import sys
import tempfile
import time
from pathlib import Path

import httpx
import uvicorn
from pydantic import SecretStr

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services/broker/src"))
from immortility_broker.app import create_app
from immortility_broker.config import Settings
from immortility_broker.policy import MODEL
from immortility_broker.secrets import CredentialManager


class BoundedProvider(httpx.AsyncBaseTransport):
    def __init__(self):
        self.transport = httpx.AsyncHTTPTransport(retries=0, trust_env=False)
        self.calls = 0

    async def handle_async_request(self, request):
        if request.url.scheme != "https" or request.url.host != "openrouter.ai":
            raise RuntimeError("Provider destination denied")
        if request.method == "POST":
            if request.url.path != "/api/v1/chat/completions" or self.calls >= 2:
                raise RuntimeError("Synthetic call ceiling exceeded")
            self.calls += 1
        elif request.method != "GET" or request.url.path != "/api/v1/models":
            raise RuntimeError("Provider operation denied")
        return await self.transport.handle_async_request(request)

    async def aclose(self):
        await self.transport.aclose()


async def main():
    key = CredentialManager(provider="openrouter").read()
    if not key:
        raise SystemExit("No configured OpenRouter credential; no live calls made.")
    provider = BoundedProvider()
    async with httpx.AsyncClient(transport=provider, timeout=70, trust_env=False) as upstream:
        with tempfile.TemporaryDirectory(prefix="chat-identity-", dir=ROOT / ".cache") as directory:
            settings = Settings(_env_file=None, data_dir=Path(directory), openrouter_api_key=SecretStr(key), model_call_cap=1)
            listener = socket.socket()
            listener.bind(("127.0.0.1", 0))
            listener.listen()
            base = f"http://127.0.0.1:{listener.getsockname()[1]}"
            token = "synthetic-chat-" + "x" * 40
            app = create_app(settings, token, base, client=upstream)
            server = uvicorn.Server(uvicorn.Config(app, log_level="critical", access_log=False))
            runner = asyncio.create_task(server.serve(sockets=[listener]))
            rows = []
            try:
                while not server.started:
                    if runner.done():
                        await runner
                    await asyncio.sleep(.02)
                async with httpx.AsyncClient(base_url=base, headers={"Authorization": "Bearer " + token}, timeout=110, trust_env=False) as client:
                    for index, prompt in enumerate(("Who are you?", "What can you actually do right now?")):
                        # Separate empty sessions avoid identity/capability priming.
                        sid = (await client.post("/v1/sessions", json={})).json()["id"]
                        started = time.perf_counter()
                        response = await client.post("/v1/tasks", json={"session_id": sid, "request_id": f"public-{index}", "content": prompt, "cloud_consent": True, "budget_mode": "fast", "response_length": "brief"})
                        response.raise_for_status()
                        task_id = response.json()["task_id"]
                        async with client.stream("GET", f"/v1/tasks/{task_id}/events") as events:
                            async for _ in events.aiter_lines():
                                pass
                        task = (await client.get(f"/v1/tasks/{task_id}")).json()
                        usage = app.state.store.ledger.summary(task_id)
                        assert usage["calls"] <= 1 and usage["charged_tokens"] <= 4000
                        text = task.get("result", {}).get("text", "")
                        assert key not in text
                        rows.append({"prompt": prompt, "status": task["status"], "response": text, "error": task.get("error"), "seconds": round(time.perf_counter()-started, 3), "usage": usage})
                        print(json.dumps({k: v for k, v in rows[-1].items() if k != "response"}), flush=True)
            finally:
                server.should_exit = True
                await runner
            report = {"scope": "two authorized public-only prompts; real Hermes and live free router; UI display is separate acceptance", "route": MODEL, "provider_calls": provider.calls, "call_cap_per_task": 1, "token_cap_per_task": 4000, "private_content_sent": False, "paid_fallback": False, "turns": rows}
            (ROOT / "docs/implementation/CHAT_IDENTITY_LIVE_SMOKE.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
            assert len(rows) == 2 and all(row["status"] == "succeeded" for row in rows)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live-consent", action="store_true")
    if not parser.parse_args().live_consent:
        parser.error("Task-scoped user authorization required; use --live-consent only after approval.")
    asyncio.run(main())
