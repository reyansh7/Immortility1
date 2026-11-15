"""Real published local runtime, client detach/reattach, SDK work and safe shutdown.

No GUI/model/account/service install. --hold-seconds leaves this owned scratch
runtime available for a separate native dashboard acceptance run, then shuts down.
Never prints its private bearer credential; publication mode must not print one.
"""

import argparse
import asyncio
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services/broker/src"))
from immortility_broker.attachment import FILENAME, read
from immortility_broker.process_owner import reap, spawn_owned


def client_for(record):
    return httpx.AsyncClient(
        base_url=record.url,
        headers={"Authorization": "Bearer " + record.token},
        trust_env=False,
        timeout=120,
    )


async def main(hold_seconds):
    started = time.perf_counter()
    with tempfile.TemporaryDirectory(prefix="attachment-smoke-", dir=ROOT / ".cache") as directory:
        folder = Path(directory)
        env = {
            key: value
            for key, value in os.environ.items()
            if key.upper() in {"SYSTEMROOT", "WINDIR", "PATH", "TEMP", "TMP"}
        }
        env.update(
            PYTHONPATH=str(ROOT / "services/broker/src"),
            PYTHONUTF8="1",
            PYTHONUNBUFFERED="1",
            USERPROFILE=directory,
            APPDATA=directory,
            LOCALAPPDATA=directory,
        )
        process, owner = await spawn_owned(
            sys.executable,
            "-m",
            "immortility_broker",
            "--headless",
            "--local-workflows",
            "--standard-mcp",
            "--data-dir",
            directory,
            "--publish-attachment",
            env=env,
            cwd=ROOT,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        try:
            line = await asyncio.wait_for(process.stdout.readline(), 15)
            handshake = json.loads(line)
            assert set(handshake) == {"status", "instance_id"}, (
                "Publication exposed unexpected handshake fields"
            )
            assert handshake["status"] == "background-ready"
            record = read(folder)
            assert record.token.encode() not in line
            assert record.instance_id == handshake["instance_id"]
            process.stdin.close()
            async with client_for(record) as first:
                ready = (await first.get("/health/ready")).json()
                assert ready["runtime_mode"] == "local-background"
                assert not ready["ready"] and not ready["capture_enabled"]
                assert (await first.post("/v1/tasks", json={})).status_code == 403
                session = (await first.post("/v1/sessions", json={})).json()["id"]
                task = (
                    await first.post(
                        "/v1/workflows",
                        json={
                            "session_id": session,
                            "request_id": "native-attachment-demo",
                            "label": "Synthetic background SDK verification",
                            "steps": [
                                {
                                    "id": f"step{i}",
                                    "capability": "arithmetic.add.v1",
                                    "arguments": {"a": i, "b": 1},
                                    "depends_on": [f"step{i - 1}"] if i else [],
                                }
                                for i in range(8)
                            ],
                            "local_read_consent": True,
                            "no_cloud": True,
                            "deadline_seconds": 120,
                            "max_retries": 0,
                            "resume_on_restart": False,
                        },
                    )
                ).json()
                task_id = task["task_id"]
                async with first.stream("GET", f"/v1/tasks/{task_id}/events") as events:
                    async for item in events.aiter_lines():
                        if item.startswith("data: "):
                            event = json.loads(item[6:])
                            if event["type"] == "tool.started":
                                cursor = event["sequence"]
                                break
                    else:
                        raise AssertionError("No real SDK dispatch started")
            # Client closed while work is active. Reattach using protected discovery.
            assert process.returncode is None
            resumed = read(folder)
            assert resumed.instance_id == record.instance_id
            async with client_for(resumed) as second:
                active = (await second.get(f"/v1/tasks/{task_id}")).json()
                assert active["status"] not in {"failed", "cancelled", "disconnected"}
                replay = []
                async with second.stream(
                    "GET", f"/v1/tasks/{task_id}/events?after={cursor}"
                ) as events:
                    async for item in events.aiter_lines():
                        if item.startswith("data: "):
                            event = json.loads(item[6:])
                            assert event["task_id"] == task_id and event["sequence"] > cursor
                            cursor = event["sequence"]
                            replay.append(event)
                final = (await second.get(f"/v1/tasks/{task_id}")).json()
                assert final["status"] == "succeeded", final.get("error")
                workflow = (await second.get(f"/v1/workflows/{task_id}")).json()
                assert len(workflow["steps"]) == 8
                assert all(step["status"] == "completed" for step in workflow["steps"])
                usage = (await second.get(f"/v1/tasks/{task_id}/usage")).json()["summary"]
                assert usage["calls"] == usage["charged_tokens"] == 0
                if hold_seconds:
                    print("BACKGROUND_ACCEPTANCE_DATA_ROOT " + directory, flush=True)
                    print(
                        "Owned scratch runtime ready for separate dashboard test; no keys/models loaded.",
                        flush=True,
                    )
                    await asyncio.sleep(hold_seconds)
                assert (await second.post("/v1/runtime/shutdown", json={})).json() == {
                    "shutdown_requested": True
                }
            await asyncio.wait_for(process.wait(), 8)
            assert process.returncode == 0
            assert not (folder / FILENAME).exists()
            evidence = {
                "status": "passed",
                "runtime": "real local-only Uvicorn broker + isolated official MCP SDK",
                "dpapi_discovery": True,
                "stdout_credential_absent": True,
                "control_pipe_eof_survived": True,
                "client_detached_after_real_dispatch": True,
                "reattached_same_instance": True,
                "replayed_events": len(replay),
                "completed_sdk_steps": 8,
                "cloud_calls": 0,
                "cloud_tokens": 0,
                "forbidden_inference_denied": True,
                "graceful_shutdown": True,
                "publication_removed": True,
                "seconds_including_optional_hold": round(time.perf_counter() - started, 3),
                "native_dashboard": "separate acceptance",
            }
            (ROOT / "docs/implementation/BACKGROUND_ATTACHMENT_SMOKE.json").write_text(
                json.dumps(evidence, indent=2) + "\n"
            )
            print(json.dumps(evidence), flush=True)
        finally:
            await reap(process, owner)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--hold-seconds", type=int, default=0, choices=range(0, 301))
    args = parser.parse_args()
    asyncio.run(main(args.hold_seconds))
