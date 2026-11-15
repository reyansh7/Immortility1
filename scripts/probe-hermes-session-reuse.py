"""Keyless canonical-gateway isolation probe. Never enables production warm reuse.

Two sequential named scratch profiles, empty tool inventories, local synthetic
provider only. No user profile, broker database, provider account or model install.
"""

import asyncio
import argparse
import hashlib
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

from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
import uvicorn

from immortility_broker.config import Settings
from immortility_broker.evidence import implementation_provenance, write_engineering_evidence
from immortility_broker.hermes import Hermes, isolated_config, runtime_check
from immortility_broker.process_owner import spawn_owned


async def main(fault_after_first_close=False):
    settings = Settings(_env_file=None)
    if runtime_check(settings)["status"] != "available":
        raise RuntimeError("Reviewed installed Hermes is required; nothing is downloaded.")
    app = FastAPI()
    tokens = {name: secrets.token_urlsafe(32) for name in ("first", "second")}
    canaries = {name: "SYNTHETIC_" + name.upper() + "_HISTORY_CANARY" for name in tokens}
    calls, phases = [], []
    errors = []

    @app.post("/{profile}/v1/chat/completions")
    async def synthetic_provider(profile: str, request: Request):
        body = await request.json()
        auth_ok = (
            profile in tokens
            and request.headers.get("authorization") == "Bearer " + tokens[profile]
        )
        encoded = json.dumps(body.get("messages", []))
        other = "second" if profile == "first" else "first"
        own_history = canaries.get(profile, "MISSING") in encoded
        crossed_history = canaries[other] in encoded
        calls.append(
            {
                "profile": profile,
                "credential_matches": auth_ok,
                "own_history": own_history,
                "crossed_history": crossed_history,
                "tools_present": bool(body.get("tools")),
            }
        )
        if not auth_ok or not own_history or crossed_history or body.get("tools"):
            errors.append("profile_isolation_failed")
        chunks = [
            {
                "choices": [
                    {
                        "index": 0,
                        "delta": {"content": "Synthetic local profile response."},
                        "finish_reason": None,
                    }
                ]
            },
            {
                "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 20, "completion_tokens": 10},
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
    cleaned = False
    elapsed = None
    cleanup_seconds = None
    try:
        with tempfile.TemporaryDirectory(prefix="immortility-warm-probe-") as folder:
            home = Path(folder)

            def config(profile, token):
                result = isolated_config(
                    settings.hermes_source, base + "/" + profile + "/v1", token
                )
                result["model"]["default"] = "synthetic-local-fixture"
                return result

            (home / "config.yaml").write_text(
                json.dumps(config("blocked", "launch-sentinel")), encoding="utf-8"
            )
            for name in tokens:
                profile_home = home / "profiles" / name
                profile_home.mkdir(parents=True)
                (profile_home / "config.yaml").write_text(
                    json.dumps(config(name, tokens[name])), encoding="utf-8"
                )
            env = {
                k: v
                for k, v in os.environ.items()
                if k.upper()
                in {"SYSTEMROOT", "WINDIR", "PATH", "TEMP", "TMP", "COMSPEC", "PATHEXT"}
            }
            env.update(
                HERMES_HOME=folder,
                HERMES_IGNORE_RULES="1",
                HERMES_TUI_SOURCE="tui",
                HERMES_TUI_TOOLSETS="bot_room",
                USERPROFILE=folder,
                LOCALAPPDATA=str(home / "AppData/Local"),
                APPDATA=str(home / "AppData/Roaming"),
                OPENAI_BASE_URL=base + "/blocked/v1",
                OPENAI_API_KEY="launch-sentinel",
                PYTHONUTF8="1",
                PYTHONUNBUFFERED="1",
                PYTHONPATH=str(settings.hermes_source),
            )
            started = time.perf_counter()
            runtime.process, runtime.owner = await spawn_owned(
                str(settings.hermes_source / "venv/Scripts/python.exe"),
                "-m",
                "tui_gateway.entry",
                cwd=folder,
                env=env,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL,
                limit=2 * 1024 * 1024,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            with_process = runtime.process
            try:
                async with asyncio.timeout(100):
                    for name in tokens:
                        phase = time.perf_counter()
                        create = await runtime.send(
                            "session.create",
                            {
                                "source": "tui",
                                "profile": name,
                                "model": "synthetic-local-fixture",
                                "provider": "custom",
                                "messages": [{"role": "user", "content": canaries[name]}],
                            },
                        )
                        sid, ready, submitted, complete = None, False, False, False
                        timings = {"profile": name}
                        async for frame in runtime.frames():
                            if frame.get("error") or ("method" in frame and "id" in frame):
                                raise RuntimeError(
                                    "Unexpected canonical gateway response or permission request."
                                )
                            if frame.get("id") == create:
                                sid = frame["result"]["session_id"]
                                runtime.session_id = sid
                            event = (
                                frame.get("params", {}) if frame.get("method") == "event" else {}
                            )
                            kind, payload = event.get("type"), event.get("payload", {})
                            if kind == "session.info" and not payload.get("lazy"):
                                inventory = payload.get("tools") or []
                                if isinstance(inventory, dict):
                                    inventory = [
                                        tool for group in inventory.values() for tool in group
                                    ]
                                if inventory:
                                    raise RuntimeError("Probe refuses any enabled tool.")
                                ready = True
                            if kind in {"tool.start", "approval", "tool.generating", "error"}:
                                raise RuntimeError("Probe encountered a forbidden gateway event.")
                            if ready and sid and not submitted:
                                timings["ready_seconds"] = round(time.perf_counter() - phase, 4)
                                await runtime.send(
                                    "prompt.submit",
                                    {
                                        "session_id": sid,
                                        "text": "Reply briefly using only this synthetic session.",
                                    },
                                )
                                submitted = True
                            if kind == "message.complete":
                                if payload.get("status") in {"error", "interrupted"}:
                                    raise RuntimeError("Synthetic session failed.")
                                complete = True
                                break
                        if not complete:
                            raise RuntimeError("Session did not complete.")
                        close = await runtime.send("session.close", {"session_id": sid})
                        async for frame in runtime.frames():
                            if frame.get("id") == close:
                                if (
                                    frame.get("error")
                                    or frame.get("result", {}).get("closed") is not True
                                ):
                                    raise RuntimeError("Session close was not acknowledged.")
                                break
                        runtime.session_id = None
                        timings["total_with_close_seconds"] = round(time.perf_counter() - phase, 4)
                        phases.append(timings)
                        if fault_after_first_close:
                            raise RuntimeError("Synthetic post-close cleanup fault")
                if len(calls) != 2 or errors or with_process.returncode is not None:
                    raise RuntimeError("Sequential profile isolation did not pass.")
            finally:
                cleanup = time.perf_counter()
                await runtime.stop()
                cleanup_seconds = round(time.perf_counter() - cleanup, 4)
                cleaned = with_process.returncode is not None
            elapsed = round(time.perf_counter() - started, 4)
    except Exception as error:
        errors.append(type(error).__name__)
    finally:
        server.should_exit = True
        await serve
        listener.close()
    evidence = {
        "probe_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "synthetic_fault_requested": fault_after_first_close,
        "status": "passed" if cleaned and len(phases) == 2 and not errors else "failed",
        "scope": "Canonical Hermes gateway with two sequential named scratch profiles and synthetic local text responses only",
        "implementation": implementation_provenance(),
        "phases": phases,
        "calls": calls,
        "errors": errors,
        "cleanup_confirmed": cleaned,
        "cloud_calls": 0,
        "tool_calls": 0,
        "production_reuse_enabled": False,
        "sample_count": len(phases),
        "percentiles": "not supported by two samples",
        "limitations": [
            "No MCP/tool profile isolation proof",
            "No cancellation/crash/concurrent-session acceptance",
            "No production credential or user context",
            "No idle RAM or sustained throughput acceptance",
        ],
    }
    if elapsed is not None:
        evidence.update(elapsed_seconds=elapsed, cleanup_seconds=cleanup_seconds)
    output = write_engineering_evidence(evidence, "hermes-session-reuse-probe")
    print(
        json.dumps(
            {
                "status": evidence["status"],
                "evidence_path": str(output),
                "phases": phases,
                "cloud_calls": 0,
                "errors": errors,
            }
        ),
        flush=True,
    )
    if evidence["status"] != "passed":
        raise SystemExit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--fault-after-first-close",
        action="store_true",
        help="Negative cleanup acceptance: intentionally exits 1 after the first session closes.",
    )
    asyncio.run(main(parser.parse_args().fault_after_first_close))
