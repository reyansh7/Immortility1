"""Keyless warm MCP experiment; production reuse remains disabled.

Real canonical Hermes, reviewed MCP bridge and broker gateway. Only inference
is synthetic. Four sequential scratch profiles test task-token/history isolation,
permission denial, in-flight tool cancellation and subsequent recovery.
"""

import asyncio
from dataclasses import replace
import hashlib
import hmac
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services/broker/src"))

from fastapi import Request
from fastapi.responses import StreamingResponse
import httpx
from pydantic import SecretStr
import uvicorn

from immortility_broker.agent_bridge import TOOL_NAME
from immortility_broker.app import create_app
from immortility_broker.config import Settings
from immortility_broker.contracts import TaskRequest
from immortility_broker.evidence import implementation_provenance, write_engineering_evidence
from immortility_broker.hermes import Hermes, isolated_config, runtime_check
from immortility_broker.process_owner import spawn_owned


async def session(runtime, profile, history, *, before_complete=None):
    start = time.perf_counter()
    create = await runtime.send(
        "session.create",
        {
            "source": "tui",
            "profile": profile,
            "model": "synthetic-local-fixture",
            "provider": "custom",
            "messages": [{"role": "user", "content": history}],
        },
    )
    sid, ready, sent, complete = None, False, False, False
    result = {"profile": profile}
    controller = None
    try:
        async for frame in runtime.frames():
            if frame.get("error") or ("method" in frame and "id" in frame):
                raise RuntimeError("Unexpected gateway response or permission request")
            if frame.get("id") == create:
                sid = frame["result"]["session_id"]
                runtime.session_id = sid
            event = frame.get("params", {}) if frame.get("method") == "event" else {}
            kind, payload = event.get("type"), event.get("payload", {})
            if kind == "session.info" and not payload.get("lazy"):
                tools = payload.get("tools") or []
                if isinstance(tools, dict):
                    tools = [tool for group in tools.values() for tool in group]
                inventory = {tool if isinstance(tool, str) else tool.get("name") for tool in tools}
                if inventory != {TOOL_NAME}:
                    raise RuntimeError("Unexpected MCP/native tool inventory")
                ready = True
            if (
                kind in {"tool.start", "tool.generating"}
                and payload.get("name", payload.get("tool_name")) != TOOL_NAME
            ):
                raise RuntimeError("Unexpected tool identity")
            if kind in {"approval", "error"}:
                raise RuntimeError("Unexpected gateway event")
            if ready and sid and not sent:
                result["ready_seconds"] = round(time.perf_counter() - start, 4)
                await runtime.send(
                    "prompt.submit",
                    {
                        "session_id": sid,
                        "text": "Use the approved broker clock and acknowledge the result.",
                    },
                )
                sent = True
                if before_complete:
                    controller = asyncio.create_task(before_complete(sid))
            if kind == "message.complete":
                result["completion_status"] = payload.get("status")
                if not before_complete and payload.get("status") in {"error", "interrupted"}:
                    raise RuntimeError("Synthetic tool session failed")
                complete = True
                break
        if not complete:
            raise RuntimeError("Missing completion")
        if controller:
            await controller
        close = await runtime.send("session.close", {"session_id": sid})
        async for frame in runtime.frames():
            if frame.get("id") == close:
                if frame.get("error") or frame.get("result", {}).get("closed") is not True:
                    raise RuntimeError("Close not acknowledged")
                break
        runtime.session_id = None
        result["total_with_close_seconds"] = round(time.perf_counter() - start, 4)
        return result
    finally:
        if controller and not controller.done():
            controller.cancel()
            try:
                await controller
            except asyncio.CancelledError:
                pass


async def main():
    scratch = tempfile.TemporaryDirectory(prefix="immortility-warm-mcp-")
    home = Path(scratch.name)
    settings = Settings(
        _env_file=None,
        data_dir=home / "broker",
        local_tools_enabled=True,
        openrouter_api_key=SecretStr(""),
        groq_api_key=SecretStr(""),
        gemini_api_key=SecretStr(""),
        nvidia_api_key=SecretStr(""),
        infernal_voice_enabled=False,
        reference_voice_enabled=False,
    )
    if runtime_check(settings)["status"] != "available":
        scratch.cleanup()
        raise RuntimeError("Reviewed installed Hermes is required; no download is permitted")

    def forbidden(_):
        raise RuntimeError("This probe forbids all external requests")

    upstream = httpx.AsyncClient(transport=httpx.MockTransport(forbidden), trust_env=False)
    app = create_app(settings, secrets.token_urlsafe(32), client=upstream)
    engine, store = app.state.engine, app.state.store
    tokens, histories, tasks = {}, {}, {}
    requests, phases, denials, failures = [], [], [], []
    mcp_requests = []
    original_clock = engine.gateway.registrations["clock.now.v1"]
    entered, stopped = asyncio.Event(), asyncio.Event()

    @app.middleware("http")
    async def scoped_diagnostics(request: Request, call_next):
        if request.url.path == "/inference/v1/capabilities/call":
            supplied = request.headers.get("authorization", "")
            origin_profile = next(
                (
                    name
                    for name, key in tokens.items()
                    if hmac.compare_digest(supplied, "Bearer " + key)
                ),
                "unknown",
            )
            row = {
                "expected_profile": next(
                    (name for name, tid in tasks.items() if tid == engine.active), None
                ),
                "credential_profile": origin_profile,
                "credential_matches_active": hmac.compare_digest(
                    supplied, "Bearer " + engine.inference_key
                ),
                "client_category": "mcp-bridge"
                if request.headers.get("user-agent", "").startswith("Python-urllib/")
                else "probe-client",
            }
            response = await call_next(request)
            row["status"] = response.status_code
            mcp_requests.append(row)
            return response
        return await call_next(request)

    @app.post("/inference/probe/{profile}/v1/chat/completions")
    async def provider(profile: str, request: Request):
        body = await request.json()
        if (
            profile not in tokens
            or request.headers.get("authorization") != "Bearer " + tokens[profile]
        ):
            raise RuntimeError("Wrong profile credential")
        messages = json.dumps(body.get("messages", []))
        if histories[profile] not in messages or any(
            text in messages for name, text in histories.items() if name != profile
        ):
            raise RuntimeError("Profile history crossed")
        tool_results = [m for m in body["messages"] if m["role"] == "tool"]
        requests.append(
            {
                "profile": profile,
                "credential_matches": True,
                "history_isolated": True,
                "tool_result_received": bool(tool_results),
            }
        )
        if tool_results:
            if (
                "clock.now.v1" not in tool_results[-1]["content"]
                or "timestamp" not in tool_results[-1]["content"]
            ):
                # End synthetic drafting cleanly; independent Store receipt and
                # scoped HTTP diagnostics still fail the isolation acceptance.
                return StreamingResponse(
                    iter(
                        [
                            "data: "
                            + json.dumps(
                                {
                                    "choices": [
                                        {
                                            "index": 0,
                                            "delta": {
                                                "content": "SYNTHETIC: broker tool result was denied; no action verified."
                                            },
                                            "finish_reason": "stop",
                                        }
                                    ]
                                }
                            )
                            + "\n\n",
                            "data: [DONE]\n\n",
                        ]
                    ),
                    media_type="text/event-stream",
                )
            delta, finish = {"content": "SYNTHETIC: actual broker clock result received."}, "stop"
        else:
            delta = {
                "tool_calls": [
                    {
                        "index": 0,
                        "id": profile + ":clock",
                        "type": "function",
                        "function": {
                            "name": TOOL_NAME,
                            "arguments": json.dumps(
                                {"capability": "clock.now.v1", "arguments": {}}
                            ),
                        },
                    }
                ]
            }
            finish = "tool_calls"
        chunks = [
            {"choices": [{"index": 0, "delta": delta, "finish_reason": None}]},
            {
                "choices": [{"index": 0, "delta": {}, "finish_reason": finish}],
                "usage": {"prompt_tokens": 100, "completion_tokens": 50},
            },
        ]
        return StreamingResponse(
            iter([*("data: " + json.dumps(c) + "\n\n" for c in chunks), "data: [DONE]\n\n"]),
            media_type="text/event-stream",
        )

    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    listener.listen(128)
    base = "http://127.0.0.1:" + str(listener.getsockname()[1])
    server = uvicorn.Server(uvicorn.Config(app, log_level="critical", access_log=False))
    serve = asyncio.create_task(server.serve(sockets=[listener]))
    while not server.started:
        if serve.done():
            await serve
        await asyncio.sleep(0.02)
    runtime = Hermes(settings, base + "/blocked/v1", "launch-sentinel")
    config = isolated_config(settings.hermes_source, base + "/blocked/v1", "launch-sentinel")
    config["model"]["default"] = "synthetic-local-fixture"
    (home / "config.yaml").write_text(json.dumps(config), encoding="utf-8")
    env = {
        k: v
        for k, v in os.environ.items()
        if k.upper() in {"SYSTEMROOT", "WINDIR", "PATH", "TEMP", "TMP", "COMSPEC", "PATHEXT"}
    }
    env.update(
        HERMES_HOME=str(home),
        HERMES_IGNORE_RULES="1",
        HERMES_TUI_SOURCE="tui",
        HERMES_TUI_TOOLSETS="immortility",
        USERPROFILE=str(home),
        LOCALAPPDATA=str(home / "AppData/Local"),
        APPDATA=str(home / "AppData/Roaming"),
        OPENAI_BASE_URL=base + "/blocked/v1",
        OPENAI_API_KEY="launch-sentinel",
        PYTHONUTF8="1",
        PYTHONUNBUFFERED="1",
        PYTHONPATH=str(settings.hermes_source),
    )
    cleaned, idle_stats = False, {}
    try:
        runtime.process, runtime.owner = await spawn_owned(
            str(settings.hermes_source / "venv/Scripts/python.exe"),
            "-m",
            "tui_gateway.entry",
            cwd=home,
            env=env,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
            limit=2 * 1024 * 1024,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        async with asyncio.timeout(150), httpx.AsyncClient(trust_env=False, timeout=10) as client:
            for name in ["first", "second", "cancel", "recovery"]:
                task, _ = store.create(
                    TaskRequest(
                        session_id=store.session()["id"],
                        request_id=name,
                        content="Synthetic local MCP isolation test",
                        cloud_consent=True,
                        allowed_capabilities=["clock.now.v1"],
                    )
                )
                tid = task["task_id"]
                tasks[name] = tid
                store.state(tid, "queued")
                store.state(tid, "running")
                engine.open_grant(tid, "standard", 90)
                tokens[name], histories[name] = (
                    engine.inference_key,
                    "SYNTHETIC_HISTORY_" + name.upper(),
                )
                profile = home / "profiles" / name
                profile.mkdir(parents=True)
                cfg = isolated_config(
                    settings.hermes_source,
                    base + "/inference/probe/" + name + "/v1",
                    tokens[name],
                    broker_schemas=engine.gateway.discover(("clock.now.v1",)),
                )
                cfg["model"]["default"] = "synthetic-local-fixture"
                cfg["mcp_servers"]["immortility"]["env"]["IMMORTILITY_BROKER_URL"] = base
                (profile / "config.yaml").write_text(json.dumps(cfg), encoding="utf-8")
                headers = {"Authorization": "Bearer " + tokens[name]}
                denied = await client.post(
                    base + "/inference/v1/capabilities/call",
                    headers=headers,
                    json={"capability": "arithmetic.add.v1", "arguments": {"a": 1, "b": 2}},
                )
                if denied.status_code != 403:
                    raise RuntimeError("Unapproved capability was not denied")
                denials.append({"profile": name, "outside_scope": denied.status_code})
                for old_name, old_token in tokens.items():
                    if old_name == name:
                        continue
                    stale = await client.post(
                        base + "/inference/v1/capabilities/call",
                        headers={"Authorization": "Bearer " + old_token},
                        json={"capability": "clock.now.v1", "arguments": {}},
                    )
                    if stale.status_code != 401:
                        raise RuntimeError("Stale task credential was admitted")
                    denials.append({"profile": name, "revoked_profile": old_name, "status": 401})

                async def slow(_):
                    entered.set()
                    try:
                        await asyncio.sleep(60)
                    finally:
                        stopped.set()

                async def cancel_tool(sid):
                    await asyncio.wait_for(entered.wait(), 15)
                    await engine.cancel(tid)
                    await runtime.send("session.interrupt", {"session_id": sid})
                    if not stopped.is_set() or engine.gateway.pending or engine.gateway.grants:
                        raise RuntimeError("In-flight tool cleanup failed")

                if name == "cancel":
                    engine.gateway.registrations["clock.now.v1"] = replace(
                        original_clock, execute=slow
                    )
                phase = await session(
                    runtime,
                    name,
                    histories[name],
                    before_complete=cancel_tool if name == "cancel" else None,
                )
                phase["broker_task_status"] = store.get(tid)["status"]
                phases.append(phase)
                if name != "cancel":
                    tool_ok = [
                        e
                        for e in store.events(tid)
                        if e["type"] == "tool.completed" and e["data"].get("status") == "ok"
                    ]
                    if len(tool_ok) != 1:
                        raise RuntimeError("Actual broker tool receipt count mismatch")
                    store.state(tid, "verifying")
                    store.state(
                        tid,
                        "succeeded",
                        result={
                            "text": "Synthetic warm probe verified an actual broker clock read.",
                            "provider": "local",
                            "model": "probe",
                        },
                    )
                await engine.gateway.revoke(tid)
                engine.inference_allowed = False
                engine.inference_key = ""
                engine.active = None
                engine.gateway.registrations["clock.now.v1"] = original_clock
            if runtime.owner:
                before_idle = runtime.owner.statistics()
                await asyncio.sleep(2)
                idle_stats = {
                    "before": before_idle,
                    "after": runtime.owner.statistics(),
                    "observation_seconds": 2,
                    "memory_definition": "Windows job accounting/peak private commit, not physical RAM",
                }
    except Exception as error:
        failures.append(type(error).__name__)
        if isinstance(error, RuntimeError):
            # All RuntimeError messages raised above are fixed fixture labels;
            # arbitrary upstream exception bodies are never recorded.
            labels = {
                "Unexpected gateway response or permission request",
                "Unexpected MCP/native tool inventory",
                "Unexpected tool identity",
                "Unexpected gateway event",
                "Synthetic tool session failed",
                "Missing completion",
                "Close not acknowledged",
                "Unapproved capability was not denied",
                "Stale task credential was admitted",
                "In-flight tool cleanup failed",
                "Actual broker tool receipt count mismatch",
            }
            if str(error) in labels:
                failures.append(str(error))
    finally:
        for tid in tasks.values():
            await engine.gateway.revoke(tid)
        engine.inference_allowed = False
        process = runtime.process
        await runtime.stop()
        cleaned = (
            process is not None
            and process.returncode is not None
            and not engine.gateway.pending
            and not engine.gateway.grants
        )
        server.should_exit = True
        await serve
        listener.close()
        await upstream.aclose()
        store.db.close()
        scratch.cleanup()
    evidence = {
        "status": "passed" if len(phases) == 4 and not failures and cleaned else "failed",
        "probe_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "implementation": implementation_provenance(),
        "scope": "Real canonical Hermes/MCP/broker; synthetic local provider; no production warm reuse",
        "phases": phases,
        "provider_fixture_requests": requests,
        "mcp_request_diagnostics": mcp_requests,
        "permission_denials": denials,
        "failures": failures,
        "cleanup_confirmed": cleaned,
        "idle_job_observation": idle_stats,
        "tool_cancelled": stopped.is_set(),
        "cloud_calls": 0,
        "production_reuse_enabled": False,
        "limitations": [
            "Sequential profiles only",
            "No production credentials",
            "No native UI or actual model intelligence",
            "No crash/restart qualification or long idle soak",
        ],
    }
    output = write_engineering_evidence(evidence, "hermes-mcp-reuse-probe")
    print(
        json.dumps(
            {
                "status": evidence["status"],
                "evidence_path": str(output),
                "phases": phases,
                "failures": failures,
                "cleanup": cleaned,
            }
        ),
        flush=True,
    )
    if evidence["status"] != "passed":
        raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(main())
