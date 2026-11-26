"""Isolated Hermes 0.23.2 desktop-path canary. The model is the local fixture.

This does not read or write the user's Immortality state database, and it does
not call Groq, Gemini, or NVIDIA.
"""

import json
import os
import socket
import subprocess
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

import uvicorn

from immortility_broker.app import create_app
from immortility_broker.config import Settings
from immortility_broker.contracts import uid
from immortility_broker.providers import quota_evidence

ROOT = Path(__file__).resolve().parents[1]


def percentile(values: list[float], fraction: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, round((len(ordered) - 1) * fraction)))
    return round(ordered[index], 3)


def main() -> int:
    local = Path(os.environ["LOCALAPPDATA"])
    data = local / "Immortility" / "canary-0232-m15"
    data.mkdir(parents=True, exist_ok=True)
    (data / "hermes-gateway.json").write_text('{"enabled": true}\n', encoding="utf-8")
    (data / "simulated-inference.json").write_text(
        '{"enabled": true, "category": "simulated_model"}\n', encoding="utf-8"
    )
    (data / "local-tools.json").write_text('{"enabled": true}\n', encoding="utf-8")
    (data / "workspace.json").write_text(
        json.dumps({"enabled": False, "root": str(ROOT), "project_read_enabled": True}) + "\n",
        encoding="utf-8",
    )
    try:
        urllib.request.urlopen("http://127.0.0.1:8642/health", timeout=2)
    except OSError:
        pass
    else:
        print(json.dumps({"blocked": "port 8642 is already in use"}))
        return 2
    settings = Settings(
        _env_file=None,
        data_dir=data,
        local_tools_enabled=True,
        project_read_enabled=True,
        workspace_root=ROOT,
    )
    token = os.urandom(32).hex()
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.bind(("127.0.0.1", 0))
    listener.listen(128)
    url = f"http://127.0.0.1:{listener.getsockname()[1]}"
    app = create_app(settings, token, url)
    server = uvicorn.Server(uvicorn.Config(app, log_level="critical", access_log=False))
    started = time.perf_counter()
    thread = threading.Thread(
        target=lambda: __import__("asyncio").run(server.serve(sockets=[listener])),
        daemon=True,
    )
    thread.start()
    deadline = time.monotonic() + 150
    while time.monotonic() < deadline and not server.started:
        time.sleep(0.1)
    cold_ms = round((time.perf_counter() - started) * 1000, 1)
    headers = {"Authorization": "Bearer " + token, "Content-Type": "application/json"}

    def call(method: str, path: str, body: dict | None = None, timeout: float = 60) -> dict:
        request = urllib.request.Request(
            url + path,
            data=None if body is None else json.dumps(body).encode(),
            headers=headers,
            method=method,
        )
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode())

    def task(
        content: str, capabilities: list[str], session_id: str, budget: str = "fast"
    ) -> dict:
        created = call(
            "POST",
            "/v1/tasks",
            {
                "schema_version": "1.0",
                "session_id": session_id,
                "request_id": uid(),
                "content": content,
                "cloud_consent": True,
                "budget_mode": budget,
                "allowed_capabilities": capabilities,
            },
        )
        task_id = created["task_id"]
        found = {}
        limit = time.monotonic() + 90
        while time.monotonic() < limit:
            found = call("GET", f"/v1/tasks/{task_id}")
            if found["status"] in {"succeeded", "failed", "blocked", "cancelled"}:
                break
            time.sleep(0.2)
        events = []
        try:
            request = urllib.request.Request(
                url + f"/v1/tasks/{task_id}/events", headers=headers
            )
            with urllib.request.urlopen(request, timeout=20) as response:
                for line in response.read().decode().splitlines():
                    if line.startswith("data: "):
                        events.append(json.loads(line[6:]))
        except (OSError, urllib.error.URLError, json.JSONDecodeError):
            events = []
        return {"task": found, "events": events}

    health = []
    for _ in range(10):
        sample = time.perf_counter()
        call("GET", "/health/live")
        health.append((time.perf_counter() - sample) * 1000)
    session = call("POST", "/v1/sessions")["id"]
    cases = [
        ("chat", "SIM:chat hello", [], "fast"),
        ("clock", "SIM:clock", ["clock.now.v1"], "fast"),
        ("steps", "SIM:steps", ["clock.now.v1", "arithmetic.multiply.v1"], "standard"),
        ("duplicate", "SIM:dup", [], "fast"),
        ("inject", "SIM:inject", ["clock.now.v1"], "fast"),
        ("bad-args", "SIM:bad", ["arithmetic.multiply.v1"], "fast"),
        ("shell", "SIM:shell", ["clock.now.v1"], "fast"),
        ("browser", "SIM:browser", ["clock.now.v1"], "fast"),
        ("computer", "SIM:computer", ["clock.now.v1"], "fast"),
        ("yolo", "SIM:yolo", ["clock.now.v1"], "fast"),
        ("mcp", "SIM:mcp", ["clock.now.v1"], "fast"),
        ("unknown", "SIM:unknown", ["clock.now.v1"], "fast"),
        ("path", "SIM:path", ["project.read.v1"], "fast"),
        ("malformed", "SIM:malformed", [], "fast"),
    ]
    results = []
    for name, content, capabilities, budget in cases:
        outcome = task(content, capabilities, session, budget)
        body = outcome["task"]
        result = body.get("result") or {}
        tool_names = [
            event.get("data", {}).get("name")
            for event in outcome["events"]
            if event.get("type") == "tool.completed"
        ]
        results.append(
            {
                "name": name,
                "status": body.get("status"),
                "provider": result.get("provider"),
                "model": result.get("model"),
                "inference_category": result.get("inference_category"),
                "billing_status": result.get("billing_status"),
                "text": (result.get("text") or "")[:180],
                "tools": tool_names,
                "error": (body.get("error") or {}).get("code"),
            }
        )
    slow = call(
        "POST",
        "/v1/tasks",
        {
            "schema_version": "1.0",
            "session_id": session,
            "request_id": uid(),
            "content": "SIM:slow",
            "cloud_consent": True,
            "allowed_capabilities": [],
        },
    )
    cancel_started = time.perf_counter()
    call("POST", f"/v1/tasks/{slow['task_id']}/cancel")
    cancelled = {}
    while time.perf_counter() - cancel_started < 20:
        cancelled = call("GET", f"/v1/tasks/{slow['task_id']}")
        if cancelled["status"] in {"cancelled", "failed", "succeeded", "blocked"}:
            break
        time.sleep(0.1)
    cancel_ms = round((time.perf_counter() - cancel_started) * 1000, 1)
    gateway = []
    for path in ("/health", "/v1/capabilities", "/v1/runs"):
        request = urllib.request.Request("http://127.0.0.1:8642" + path, method="GET" if path != "/v1/runs" else "POST")
        if path == "/v1/runs":
            request.data = b"{}"
            request.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(request, timeout=5) as response:
                gateway.append({"path": path, "status": response.status})
        except urllib.error.HTTPError as error:
            gateway.append({"path": path, "status": error.code})
        except OSError:
            gateway.append({"path": path, "status": None})
    bad = urllib.request.Request(
        "http://127.0.0.1:8642/v1/runs",
        data=b"{}",
        headers={"Authorization": "Bearer not-the-key", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(bad, timeout=5) as response:
            gateway.append({"path": "/v1/runs", "auth": "invalid", "status": response.status})
    except urllib.error.HTTPError as error:
        gateway.append({"path": "/v1/runs", "auth": "invalid", "status": error.code})
    memory = subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-Command",
            "Get-Process python -ErrorAction SilentlyContinue | "
            "Select-Object Id,WorkingSet64,CPU | ConvertTo-Json -Compress",
        ],
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    server.should_exit = True
    thread.join(timeout=25)
    time.sleep(1)
    try:
        urllib.request.urlopen("http://127.0.0.1:8642/health", timeout=2)
        port_open = True
    except OSError:
        port_open = False
    allowed = {"chat", "clock", "steps", "duplicate", "inject"}
    denied = {"bad-args", "shell", "browser", "computer", "yolo", "mcp", "unknown", "path", "malformed"}
    ok = (
        cold_ms > 0
        and all(item["status"] == "succeeded" and item["provider"] == "simulated" for item in results if item["name"] in allowed)
        and all(
            item["status"] in {"blocked", "failed", "cancelled"}
            for item in results
            if item["name"] in denied
        )
        and cancelled.get("status") == "cancelled"
        and all(item["status"] in {401, 403} for item in gateway if item["path"] != "/health")
        and not port_open
    )
    print(
        json.dumps(
            {
                "cold_start_ms": cold_ms,
                "health_p50_ms": percentile(health, 0.5),
                "health_p95_ms": percentile(health, 0.95),
                "cancel_ms": cancel_ms,
                "cancel_status": cancelled.get("status"),
                "cases": results,
                "gateway": gateway,
                "port_open_after_stop": port_open,
                "process_sample": memory.stdout.strip()[:500],
                "quota": quota_evidence(),
                "passed": ok,
            },
            indent=2,
        ),
        flush=True,
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
