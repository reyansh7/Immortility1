"""Real Hermes + reviewed MCP bridge + broker gateway; only inference is fake.

This proves protocol integration, not genuine live model tool selection.
No provider credential, user history, microphone, capture or external network.
"""

import asyncio
import argparse
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
from immortility_broker.agent_bridge import TOOL_NAME
from immortility_broker.config import Settings
from immortility_broker.policy import MODEL


async def main(live=False):
    calls = []
    evidence_seen = False
    import immortility_broker.app as app_module
    original_payload = app_module.inference_payload
    def inspect_payload(body, **kwargs):
        result = original_payload(body, **kwargs)
        assert all(str(ROOT) not in m["content"] and "Workspace (snapshot" not in m["content"] for m in result["messages"] if m["role"] == "system")
        print("Context lengths:", [{"role": m["role"], "chars": len(m["content"])} for m in result["messages"]], flush=True)
        return result
    app_module.inference_payload = inspect_payload

    def provider(request):
        nonlocal evidence_seen
        if request.method == "GET":
            return httpx.Response(200, json={"data": [{"id": MODEL, "pricing": {"prompt": "0", "completion": "0"}}]})
        body = json.loads(request.content)
        calls.append(body)
        assert len(calls) <= 2 and len(body["tools"]) == 1
        assert body["tools"][0]["function"]["name"] == TOOL_NAME
        if len(calls) == 1:
            delta = {"tool_calls": [{"index": 0, "id": "clock_fixture", "type": "function", "function": {"name": TOOL_NAME, "arguments": json.dumps({"capability": "clock.now.v1", "arguments": {}})}}]}
            finish = "tool_calls"
        else:
            tool_messages = [m["content"] for m in body["messages"] if m["role"] == "tool"]
            evidence_seen = any("timestamp" in t and "clock.now.v1" in t for t in tool_messages)
            assert evidence_seen, "Actual broker result never reached Hermes/provider"
            delta = {"content": "OFFLINE PROVIDER: the broker clock result was received and checked."}
            finish = "stop"
        chunks = [{"id": "fixture", "object": "chat.completion.chunk", "model": MODEL, "choices": [{"index": 0, "delta": delta, "finish_reason": None}]}, {"id": "fixture", "object": "chat.completion.chunk", "model": MODEL, "choices": [{"index": 0, "delta": {}, "finish_reason": finish}], "usage": {"prompt_tokens": 300, "completion_tokens": 50}}]
        return httpx.Response(200, text="".join("data: " + json.dumps(c) + "\n\n" for c in chunks) + "data: [DONE]\n\n", headers={"content-type": "text/event-stream"})

    class BoundedLiveProvider(httpx.AsyncBaseTransport):
        def __init__(self):
            self.transport = httpx.AsyncHTTPTransport(retries=0, trust_env=False)

        async def handle_async_request(self, request):
            nonlocal evidence_seen
            assert request.url.scheme == "https" and request.url.host == "openrouter.ai"
            if request.method == "POST":
                assert request.url.path == "/api/v1/chat/completions" and len(calls) < 2
                body = json.loads(request.content)
                calls.append(body)
                if len(calls) == 2:
                    evidence_seen = any('62' in m.get("content", "") and "arithmetic.add.v1" in m.get("content", "") for m in body["messages"] if m.get("role") == "tool")
            else:
                assert request.method == "GET" and request.url.path == "/api/v1/models"
            return await self.transport.handle_async_request(request)

        async def aclose(self):
            await self.transport.aclose()

    with tempfile.TemporaryDirectory(prefix="agent-bridge-", dir=ROOT / ".cache") as folder:
        settings = Settings(_env_file=None, data_dir=Path(folder), openrouter_api_key=SecretStr("offline-fixture"), local_tools_enabled=not live, standard_mcp_enabled=live, model_call_cap=2)
        if live:
            from immortility_broker.secrets import CredentialManager
            key = CredentialManager(provider="openrouter").read()
            if not key:
                raise SystemExit("No configured key; no live test performed.")
            settings.openrouter_api_key = SecretStr(key)
        upstream = httpx.AsyncClient(transport=BoundedLiveProvider() if live else httpx.MockTransport(provider), timeout=70)
        listener = socket.socket()
        listener.bind(("127.0.0.1", 0))
        listener.listen()
        base = f"http://127.0.0.1:{listener.getsockname()[1]}"
        token = "fixture-only-" + "x" * 40
        app = create_app(settings, token, base, client=upstream)
        runtimes = []
        from immortility_broker.hermes import Hermes
        def factory():
            runtime = Hermes(settings, base + "/inference/v1", app.state.engine.inference_key)
            runtimes.append(runtime)
            return runtime
        app.state.engine.factory = factory
        server = uvicorn.Server(uvicorn.Config(app, log_level="critical", access_log=False))
        runner = asyncio.create_task(server.serve(sockets=[listener]))
        started = time.perf_counter()
        try:
            while not server.started:
                if runner.done():
                    await runner
                await asyncio.sleep(.02)
            async with httpx.AsyncClient(base_url=base, headers={"Authorization": "Bearer " + token}, timeout=110, trust_env=False) as client:
                sid = (await client.post("/v1/sessions", json={})).json()["id"]
                prompt = "A basket contains nineteen screws and forty-three bolts. Determine the total number of items and verify it with your approved arithmetic capability." if live else "Verify the current UTC time using the approved broker capability, then explain the result."
                response = await client.post("/v1/tasks", json={"session_id": sid, "request_id": "native-mcp-bridge", "content": prompt, "cloud_consent": True, "budget_mode": "standard", "allowed_capabilities": ["arithmetic.add.v1" if live else "clock.now.v1"]})
                response.raise_for_status()
                tid = response.json()["task_id"]
                events = []
                async with client.stream("GET", f"/v1/tasks/{tid}/events") as stream:
                    async for line in stream.aiter_lines():
                        if line.startswith("data: "):
                            events.append(json.loads(line[6:]))
                task = (await client.get(f"/v1/tasks/{tid}")).json()
                print("Synthetic native inventory:", [sorted(r.tool_inventory) for r in runtimes])
                print(json.dumps({"status": task["status"], "error": task.get("error"), "provider_calls": len(calls), "tool_events": [e["data"] for e in events if e["type"].startswith("tool.")]}), flush=True)
                assert task["status"] == "succeeded" and evidence_seen
                assert sum(e["type"] == "tool.completed" for e in events) == 1
                report = {"status": "passed", "classification": "VERIFIED REAL OPERATION" if live else "VERIFIED LOCAL INTEGRATION; provider tool selection MOCK-TESTED ONLY", "runtime": "real pinned Hermes native loop + SDK MCP bridge + authoritative broker gateway", "provider_requests": len(calls), "real_tool_dispatches": 1, "actual_result_reached_provider": evidence_seen, "cloud_calls": len(calls) if live else 0, "seconds": round(time.perf_counter()-started, 3), "usage": app.state.store.ledger.summary(tid)}
                (ROOT / ("docs/implementation/M2A_LIVE_BRIDGE_SMOKE.json" if live else "docs/implementation/M2A_NATIVE_BRIDGE_SMOKE.json")).write_text(json.dumps(report, indent=2)+"\n")
                print(json.dumps(report))
        finally:
            server.should_exit = True
            await runner
            await upstream.aclose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live-consent", action="store_true", help="Only after specific user authorization for this public arithmetic prompt; max 2 calls/8000 tokens")
    asyncio.run(main(parser.parse_args().live_consent))
