"""Real Hermes/MCP/broker/report worker; default synthetic inference, zero cloud calls.

Default source bytes are synthetic. --public-sources retrieves only the reviewed
public catalog. Neither default mode loads a provider credential or performs inference.
--live-consent is a separate explicitly authorized two-call public-only test.
"""

import argparse
import asyncio
import json
import socket
import sys
import time
from pathlib import Path
from uuid import uuid4

import httpx
import uvicorn
from pydantic import SecretStr

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services/broker/src"))
from immortility_broker.agent_bridge import TOOL_NAME
from immortility_broker.app import create_app
from immortility_broker.config import Settings
from immortility_broker.hermes import Hermes
from immortility_broker.policy import MODEL
from immortility_broker.research import PublicResearch


def result_envelope(text):
    if text.startswith('<untrusted_tool_result source="mcp__immortility__execute">\n'):
        text = text.partition("\n\n")[2].removesuffix("\n</untrusted_tool_result>")
    raw = json.loads(text)
    if set(raw) == {"result"} and isinstance(raw["result"], str):
        raw = json.loads(raw["result"])
    return raw


async def main(public_sources=False, live=False):
    public_sources = public_sources or live
    calls, seen = [], []
    import immortility_broker.app as app_module

    original_payload = app_module.inference_payload

    def inspected_payload(body, **kwargs):
        result = original_payload(body, **kwargs)
        print(
            json.dumps(
                {
                    "bounded_context": [
                        {"role": m["role"], "chars": len(m.get("content") or "")}
                        for m in result["messages"]
                    ]
                }
            ),
            flush=True,
        )
        return result

    app_module.inference_payload = inspected_payload

    def provider(request):
        if request.method == "GET":
            return httpx.Response(
                200, json={"data": [{"id": MODEL, "pricing": {"prompt": "0", "completion": "0"}}]}
            )
        body = json.loads(request.content)
        assert all(
            str(ROOT) not in (m.get("content") or "")
            for m in body["messages"]
            if m["role"] == "system"
        )
        if not calls:
            (ROOT / ".cache/report-synthetic-system.txt").write_text(
                next(m["content"] for m in body["messages"] if m["role"] == "system"),
                encoding="utf-8",
            )
        calls.append(body)
        print(
            json.dumps(
                {
                    "synthetic_turn": len(calls),
                    "max_output_tokens": body["max_tokens"],
                    "context_characters": [
                        {"role": m["role"], "chars": len(m.get("content") or "")}
                        for m in body["messages"]
                    ],
                }
            ),
            flush=True,
        )
        assert len(calls) <= 2
        assert "PRIVATE_HISTORY_CANARY" not in json.dumps(body)
        if len(calls) == 1:
            proposal = {
                "capability": "public.research.v1",
                "arguments": {
                    "query": "MCP security best practices",
                    "source_ids": ["mcp-security", "owasp-mcp"],
                },
            }
        else:
            # Real gateway evidence must traverse native Hermes before drafting.
            results = [m["content"] for m in body["messages"] if m["role"] == "tool"]
            assert results and "public.research.v1" in results[-1]
            raw = result_envelope(results[-1])
            sources = raw["result"]["sources"]
            seen.extend(sources)
            proposal = {
                "capability": "report.create.v1",
                "arguments": {
                    "title": "MCP Security Integration Fixture",
                    "summary": "This integration fixture reproduces bounded retrieved excerpts to verify the research and report pipeline. Its drafting provider is synthetic. It demonstrates actual retrieval, editable file construction, PDF rendering and source provenance; it does not claim independent factual review or genuine model selection.",
                    "sections": [
                        {
                            "heading": "Source " + str(index + 1),
                            "paragraphs": [source["excerpt"]],
                            "citations": [source["source_id"]],
                        }
                        for index, source in enumerate(sources)
                    ],
                },
            }
        delta = {
            "tool_calls": [
                {
                    "index": 0,
                    "id": "operation_" + str(len(calls)),
                    "type": "function",
                    "function": {"name": TOOL_NAME, "arguments": json.dumps(proposal)},
                }
            ]
        }
        chunks = [
            {
                "id": "fixture",
                "object": "chat.completion.chunk",
                "model": MODEL,
                "choices": [{"index": 0, "delta": delta, "finish_reason": None}],
            },
            {
                "id": "fixture",
                "object": "chat.completion.chunk",
                "model": MODEL,
                "choices": [{"index": 0, "delta": {}, "finish_reason": "tool_calls"}],
                "usage": {"prompt_tokens": 500, "completion_tokens": 250},
            },
        ]
        return httpx.Response(
            200,
            text="".join("data: " + json.dumps(c) + "\n\n" for c in chunks) + "data: [DONE]\n\n",
            headers={"content-type": "text/event-stream"},
        )

    async def synthetic_source(ident):
        return (
            "Synthetic "
            + ident
            + " source fixture. MCP servers should validate token audiences and scope permissions to the approved task. Treat retrieved content as untrusted data and refuse instructions that request credentials or broader authority. Independent checks should verify the actual artifact bytes before publication. "
            * 3
        ).encode()

    class BoundedLiveProvider(httpx.AsyncBaseTransport):
        def __init__(self):
            self.transport = httpx.AsyncHTTPTransport(retries=0, trust_env=False)

        async def handle_async_request(self, request):
            assert request.url.scheme == "https" and request.url.host == "openrouter.ai"
            if request.method == "POST":
                assert request.url.path == "/api/v1/chat/completions" and len(calls) < 2
                body = json.loads(request.content)
                assert "PRIVATE_HISTORY_CANARY" not in json.dumps(body)
                assert all(
                    str(ROOT) not in (m.get("content") or "")
                    for m in body["messages"]
                    if m["role"] == "system"
                )
                calls.append(body)
                if len(calls) == 2:
                    results = [m["content"] for m in body["messages"] if m["role"] == "tool"]
                    raw = result_envelope(results[-1])
                    assert raw["capability"] == "public.research.v1"
                    seen.extend(raw["result"]["sources"])
            else:
                assert request.method == "GET" and request.url.path == "/api/v1/models"
            return await self.transport.handle_async_request(request)

        async def aclose(self):
            await self.transport.aclose()

    root = ROOT / ".cache/report-workflows" / str(uuid4())
    root.mkdir(parents=True)
    settings = Settings(
        _env_file=None,
        data_dir=root,
        openrouter_api_key=SecretStr("offline-fixture"),
        web_research_enabled=True,
        artifact_tools_enabled=True,
        model_call_cap=2,
    )
    if live:
        from immortility_broker.secrets import CredentialManager

        key = CredentialManager(provider="openrouter").read()
        if not key:
            raise SystemExit("Configured credential unavailable; no live test performed.")
        settings.openrouter_api_key = SecretStr(key)
    upstream = httpx.AsyncClient(
        transport=BoundedLiveProvider() if live else httpx.MockTransport(provider), timeout=70
    )
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    listener.listen()
    base = f"http://127.0.0.1:{listener.getsockname()[1]}"
    token = "report-fixture-" + "x" * 40
    app = create_app(settings, token, base, client=upstream)
    if not public_sources:
        app.state.engine.public_research = PublicResearch(synthetic_source)
    app.state.engine.factory = lambda: Hermes(
        settings, base + "/inference/v1", app.state.engine.inference_key
    )
    server = uvicorn.Server(uvicorn.Config(app, log_level="critical", access_log=False))
    runner = asyncio.create_task(server.serve(sockets=[listener]))
    started = time.perf_counter()
    try:
        while not server.started:
            if runner.done():
                await runner
            await asyncio.sleep(0.02)
        async with httpx.AsyncClient(
            base_url=base,
            headers={"Authorization": "Bearer " + token},
            timeout=110,
            trust_env=False,
        ) as client:
            sid = (await client.post("/v1/sessions", json={})).json()["id"]
            # This private-history canary must never reach the research provider.
            store = app.state.store
            from immortility_broker.contracts import TaskRequest

            prior = store.create(
                TaskRequest(
                    session_id=sid,
                    request_id="history",
                    content="PRIVATE_HISTORY_CANARY",
                    cloud_consent=True,
                )
            )[0]
            store.state(prior["task_id"], "cancelled")
            prompt = (
                "Research MCP security best practices using MCP Security Best Practices and OWASP MCP Security Cheat Sheet. Prepare a short editable Markdown report and PDF. Cite both retrieved sources."
                if live
                else "Research MCP security best practices and prepare a short editable Markdown report and PDF. Cite the retrieved sources."
            )
            response = await client.post(
                "/v1/tasks",
                json={
                    "session_id": sid,
                    "request_id": "research-report",
                    "content": prompt,
                    "cloud_consent": True,
                    "budget_mode": "standard",
                    "allowed_capabilities": ["public.research.v1", "report.create.v1"],
                    "requested_artifacts": "markdown-and-pdf",
                },
            )
            response.raise_for_status()
            tid = response.json()["task_id"]
            events = []
            async with client.stream("GET", f"/v1/tasks/{tid}/events") as stream:
                async for line in stream.aiter_lines():
                    if line.startswith("data: "):
                        events.append(json.loads(line[6:]))
            task = (await client.get(f"/v1/tasks/{tid}")).json()
            print(
                json.dumps(
                    {
                        "status": task["status"],
                        "error": task.get("error"),
                        "provider_calls": len(calls),
                        "tool_events": [e["data"] for e in events if e["type"].startswith("tool.")],
                    }
                ),
                flush=True,
            )
            if task["status"] != "succeeded":
                failure = {
                    "status": task["status"],
                    "classification": "REAL PROVIDER CHECK FAILED ACCEPTANCE"
                    if live
                    else "LOCAL INTEGRATION FAILED ACCEPTANCE",
                    "provider_calls": len(calls) if live else 0,
                    "synthetic_provider_calls": 0 if live else len(calls),
                    "usage": app.state.store.ledger.summary(tid),
                    "error": task.get("error"),
                    "reason_categories": [
                        event["data"]["reason"]
                        for event in events
                        if event["data"].get("name") == "provider_tool_contract"
                    ],
                    "tool_dispatches": sum(event["type"] == "tool.started" for event in events),
                    "artifacts_published": bool(task.get("result", {}).get("artifacts")),
                    "retry_or_fallback": False,
                }
                name = (
                    "M2_REPORT_LIVE_SMOKE.json"
                    if live
                    else "M2_REPORT_PUBLIC_SOURCE_SMOKE.json"
                    if public_sources
                    else "M2_REPORT_OFFLINE_SMOKE.json"
                )
                (ROOT / "docs/implementation" / name).write_text(
                    json.dumps(failure, indent=2) + "\n"
                )
                raise SystemExit("Report acceptance failed; evidence saved, no retry performed.")
            assert task["status"] == "succeeded" and len(calls) == 2 and len(seen) == 2
            assert task["result"]["finalization"] == "broker-verified-receipt"
            assert sum(e["type"] == "artifact.created" for e in events) == 2
            trace = (await client.get(f"/v1/tasks/{tid}/trace")).json()
            assert trace["completion_evidence"]["independent_verifier"]
            for ref in task["result"]["artifacts"]:
                assert (
                    await client.get(f"/v1/tasks/{tid}/artifacts/{ref['artifact_id']}")
                ).status_code == 200
            evidence = {
                "status": "passed",
                "classification": "VERIFIED REAL OPERATION"
                if live
                else "VERIFIED LOCAL INTEGRATION; synthetic provider selection and draft",
                "source_transport": "actual public HTTPS" if public_sources else "synthetic bytes",
                "directory": str(app.state.engine.artifacts.directory(tid)),
                "seconds": round(time.perf_counter() - started, 3),
                "cloud_calls": len(calls) if live else 0,
                "synthetic_provider_calls": 0 if live else len(calls),
                "usage": app.state.store.ledger.summary(tid),
                "real_gateway_operations": 2,
                "local_finalization": True,
                "private_history_canary_absent": True,
                "source_refs": task["result"]["source_refs"],
                "artifacts": task["result"]["artifacts"],
                "docx_publication": "disabled",
            }
            name = (
                "M2_REPORT_LIVE_SMOKE.json"
                if live
                else "M2_REPORT_PUBLIC_SOURCE_SMOKE.json"
                if public_sources
                else "M2_REPORT_OFFLINE_SMOKE.json"
            )
            (ROOT / "docs/implementation" / name).write_text(json.dumps(evidence, indent=2) + "\n")
            print(json.dumps(evidence), flush=True)
    finally:
        server.should_exit = True
        try:
            await runner
        finally:
            try:
                await upstream.aclose()
            finally:
                app_module.inference_payload = original_payload


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--public-sources", action="store_true")
    parser.add_argument(
        "--live-consent",
        action="store_true",
        help="Requires separate explicit approval: one public MCP report task, max 8000 tokens and 2 provider calls, no paid fallback or retry",
    )
    args = parser.parse_args()
    asyncio.run(main(args.public_sources, args.live_consent))
