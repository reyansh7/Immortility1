"""MANUAL native consent + real broker/gateway/UIA test, restricted to our fixture.

The human must select the printed synthetic window and click Allow themselves.
No UI automation, auto-approval, real user-window reads, models or accounts.
Closing/Cancel is a valid refusal, not a passing positive test.
"""

import asyncio
import json
import os
import subprocess
import sys
import tempfile
import time
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services/broker/src"))

from fastapi.testclient import TestClient
import immortility_broker.app as broker
from immortility_broker.config import Settings
from immortility_broker.contracts import BrokerError
from immortility_broker.process_owner import reap, spawn_owned
from immortility_broker.windows_observer import reviewed_observer


async def main():
    await asyncio.to_thread(reviewed_observer)
    with tempfile.TemporaryDirectory(prefix="native-consent-", dir=ROOT / ".cache") as directory:
        folder = Path(directory)
        env = {
            key: value
            for key, value in os.environ.items()
            if key.upper() in {"SYSTEMROOT", "WINDIR", "PATH", "TEMP", "TMP"}
        }
        env.update(USERPROFILE=directory, APPDATA=directory, LOCALAPPDATA=directory)
        fixture, owner = await spawn_owned(
            sys.executable,
            "-I",
            str(ROOT / "integrations/windows-observer/scratch_window.py"),
            env=env,
            cwd=folder,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        original = broker.select_window
        try:
            target = json.loads(await asyncio.wait_for(fixture.stdout.readline(), 5))

            @asynccontextmanager
            async def fixture_only(lease):
                async with original(lease) as picker:
                    if any(
                        getattr(picker.selection, key) != target[key]
                        for key in ("hwnd", "pid", "created")
                    ):
                        raise BrokerError(
                            "tool_denied",
                            "This acceptance run permits its synthetic fixture only.",
                            403,
                        )
                    yield picker

            broker.select_window = fixture_only
            settings = Settings(
                _env_file=None,
                data_dir=folder / "broker",
                hermes_source=folder / "absent-hermes",
                openrouter_api_key="",
                gemini_api_key="",
                groq_api_key="",
                nvidia_api_key="",
                reference_voice_enabled=False,
                infernal_voice_enabled=False,
                delegation_enabled=False,
                workspace_tools_enabled=False,
                web_research_enabled=False,
                mcp_enabled=False,
                standard_mcp_enabled=False,
                durable_workflows_enabled=False,
            )

            def no_model(*args):
                raise AssertionError("Native read must not start a model")

            app = broker.create_app(settings, "native-acceptance-" + "x" * 40, factory=no_model)
            headers = {"Authorization": "Bearer " + "native-acceptance-" + "x" * 40}
            print(
                "MANUAL CHECK: select ONLY this synthetic window in the native picker:", flush=True
            )
            print(target["title"], flush=True)
            print(
                "Click Allow one local read yourself. Cancel/closing refuses; nothing is auto-approved.",
                flush=True,
            )
            started = time.perf_counter()
            with TestClient(app) as client:
                session = client.post("/v1/sessions", headers=headers).json()["id"]
                task = client.post(
                    "/v1/observations",
                    headers=headers,
                    json={
                        "session_id": session,
                        "request_id": str(uuid4()),
                    },
                ).json()
                result = client.get(f"/v1/observations/{task['task_id']}", headers=headers).json()
                assert result["task"]["status"] == "succeeded", result["task"].get(
                    "error", result["task"]["status"]
                )
                snapshot = result["snapshot"]
                assert snapshot["hwnd"] == target["hwnd"] and snapshot["pid"] == target["pid"]
                assert any("return a - b" in node["text"] for node in snapshot["nodes"])
                assert "IMMORTILITY_SYNTHETIC_PASSWORD_CANARY" not in json.dumps(snapshot)
                assert snapshot["screenshots"] == snapshot["input_actions"] == 0
                assert (
                    client.get(f"/v1/observations/{task['task_id']}", headers=headers).status_code
                    == 404
                )
                usage = app.state.store.ledger.summary(task["task_id"])
                assert usage["calls"] == usage["charged_tokens"] == 0
                assert "return a - b" not in json.dumps(app.state.store.events(task["task_id"]))
            evidence = {
                "status": "passed",
                "consent": "human native selection and Allow click; no automation",
                "runtime": "real native picker + broker + gateway + UIA worker",
                "scope": "synthetic fixture only, enforced by extra acceptance filter",
                "nodes": len(snapshot["nodes"]),
                "code_retrieved": True,
                "password_canary_absent": True,
                "single_use_delivery": True,
                "cloud_calls": 0,
                "screenshots": 0,
                "desktop_input_actions": 0,
                "elapsed_seconds_including_human": round(time.perf_counter() - started, 3),
                "general_app_corpus": "unverified",
                "dashboard_render": "separate acceptance",
            }
            (ROOT / "docs/implementation/NATIVE_WINDOW_CONSENT_SMOKE.json").write_text(
                json.dumps(evidence, indent=2) + "\n"
            )
            print(json.dumps(evidence), flush=True)
        finally:
            broker.select_window = original
            await reap(fixture, owner)


if __name__ == "__main__":
    asyncio.run(main())
