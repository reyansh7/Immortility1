"""Native scratch-window UIA evaluation, no user app capture or input action.

The optional hold leaves only our own fixture visible for independent inspection.
All children are task-owned and reaped. This does not enable a product capability.
"""

import argparse
import asyncio
import hashlib
import json
import os
import runpy
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services/broker/src"))
from immortility_broker.process_owner import reap, spawn_owned


async def inspect(request, folder):
    env = {
        k: v
        for k, v in os.environ.items()
        if k.upper() in {"SYSTEMROOT", "WINDIR", "PATH", "TEMP", "TMP"}
    }
    env.update(USERPROFILE=str(folder), APPDATA=str(folder), LOCALAPPDATA=str(folder))
    worker, owner = await spawn_owned(
        str(ROOT / ".venv-observer/Scripts/python.exe"),
        "-I",
        str(ROOT / "integrations/windows-observer/inspect_window.py"),
        env=env,
        cwd=folder,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.DEVNULL,
        limit=65536,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        job_memory_limit=256 * 1024**2,
    )
    try:
        worker.stdin.write((json.dumps(request) + "\n").encode())
        await worker.stdin.drain()
        worker.stdin.close()
        line = await asyncio.wait_for(worker.stdout.readline(), 10)
        if len(line) > 64000:
            raise AssertionError("Observer exceeded output limit")
        response = json.loads(line)
        await asyncio.wait_for(worker.wait(), 3)
        return response, owner.peak_committed_bytes()
    finally:
        await reap(worker, owner)


async def main(hold_seconds, wide=False):
    runpy.run_path(str(ROOT / "scripts/verify-observer-runtime.py"))["verify"]()
    started = time.perf_counter()
    with tempfile.TemporaryDirectory(prefix="observer-test-", dir=ROOT / ".cache") as folder:
        env = {
            k: v
            for k, v in os.environ.items()
            if k.upper() in {"SYSTEMROOT", "WINDIR", "PATH", "TEMP", "TMP"}
        }
        env.update(USERPROFILE=folder, APPDATA=folder, LOCALAPPDATA=folder)
        fixture, owner = await spawn_owned(
            sys.executable,
            "-I",
            str(ROOT / "integrations/windows-observer/scratch_window.py"),
            *(["--wide"] if wide else []),
            env=env,
            cwd=folder,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        try:
            target = json.loads(await asyncio.wait_for(fixture.stdout.readline(), 5))
            print("Owned synthetic window:", target["title"], flush=True)
            request = {
                "operation": "inspect",
                "task_id": str(uuid.uuid4()),
                "session_id": str(uuid.uuid4()),
                "lease_id": target["nonce"],
                "hwnd": target["hwnd"],
                "pid": target["pid"],
                "created": target["created"],
                "title_sha256": hashlib.sha256(target["title"].encode()).hexdigest(),
                "expires_at": time.time() + 20,
                "indicator_hwnd": target["hwnd"],
                "indicator_pid": target["pid"],
                "indicator_created": target["created"],
                "consent": True,
                "no_cloud": True,
            }
            first = time.perf_counter()
            observation, peak_commit = await inspect(request, folder)
            elapsed = (time.perf_counter() - first) * 1000
            assert "error" not in observation, observation.get("error")
            assert any("return a - b" in node["text"] for node in observation["nodes"]), (
                "Expected synthetic code was not retrieved"
            )
            assert any(node["protected"] for node in observation["nodes"]), (
                "Protected control was not classified"
            )
            assert "IMMORTILITY_SYNTHETIC_PASSWORD_CANARY" not in json.dumps(observation), (
                "Synthetic protected value leaked"
            )
            assert len(observation["nodes"]) <= 64
            if wide:
                assert observation["truncated"], "Wide tree must report truncation"
            denied = []
            for change, expected in [
                ({"consent": False}, "tool_denied"),
                ({"no_cloud": False}, "tool_denied"),
                ({"task_id": "invalid"}, "invalid_request"),
                ({"hwnd": True}, "invalid_request"),
                ({"title_sha256": "g" * 64}, "invalid_request"),
                ({"unexpected_key": "deny"}, "tool_denied"),
                ({"expires_at": float("inf")}, "grant_expired"),
                ({"expires_at": time.time() + 3600}, "grant_expired"),
                ({"operation": "click"}, "tool_denied"),
                ({"pid": target["pid"] + 1}, "stale_window"),
                ({"created": target["created"] + 1}, "stale_process"),
                ({"expires_at": time.time() - 1}, "grant_expired"),
                ({"lease_id": uuid.uuid4().hex}, "indicator_unavailable"),
            ]:
                result, _ = await inspect(
                    request | {"expires_at": time.time() + 20} | change, folder
                )
                assert result == {"error": expected}, "Unexpected denial classification"
                denied.append(expected)
            result = {
                "status": "passed",
                "mode": "real native Win32 scratch fixture + pywinauto UIA on Windows; no user app observed",
                "pywinauto": "0.6.9",
                "nodes": len(observation["nodes"]),
                "protected_nodes": sum(node["protected"] for node in observation["nodes"]),
                "synthetic_code_retrieved": True,
                "password_canary_absent": True,
                "negative_cases": denied,
                "screenshot_count": observation["screenshots"],
                "input_actions": observation["input_actions"],
                "cloud_calls": 0,
                "native_dpi": observation["dpi"],
                "job_peak_commit_bytes": peak_commit,
                "job_commit_limit_bytes": 256 * 1024**2,
                "cold_observe_ms_n1": round(elapsed, 2),
                "total_seconds": round(time.perf_counter() - started, 3),
                "product_registered": False,
                "general_app_corpus_verified": False,
                "wide_tree": wide,
                "truncated": observation["truncated"],
            }
            name = "WINDOWS_OBSERVER_WIDE_SMOKE.json" if wide else "WINDOWS_OBSERVER_SMOKE.json"
            (ROOT / "docs/implementation" / name).write_text(json.dumps(result, indent=2) + "\n")
            print(json.dumps(result), flush=True)
            if hold_seconds:
                print("Holding only the synthetic fixture for independent inspection.", flush=True)
                await asyncio.sleep(hold_seconds)
        finally:
            await reap(fixture, owner)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--hold-seconds", type=int, default=0, choices=range(0, 61))
    parser.add_argument("--wide", action="store_true")
    args = parser.parse_args()
    asyncio.run(main(args.hold_seconds, args.wide))
