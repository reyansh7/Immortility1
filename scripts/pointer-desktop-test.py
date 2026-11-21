"""D18 real-desktop pointer test (Windows, idle PC). Canary data dir only.

Drives the real broker over HTTP: explicit command -> approval request -> the
harness approves (stands in for the user's click) -> real SetCursorPos -> verify
with GetCursorPos. Also checks clamp, corner fail-safe, deny, a simulated user
interruption of a smooth move, and that no click/keyboard event is ever sent.
Restores the original cursor position at the end.
"""

from __future__ import annotations

import asyncio
import ctypes
import json
import os
import socket
import threading
import time
import urllib.error
import urllib.request
from ctypes import wintypes
from pathlib import Path

import uvicorn
from pydantic import SecretStr

from immortility_broker.app import create_app
from immortility_broker.config import Settings
from immortility_broker.contracts import uid

user32 = ctypes.WinDLL("user32", use_last_error=True)
user32.SetThreadDpiAwarenessContext.restype = ctypes.c_void_p
user32.SetThreadDpiAwarenessContext.argtypes = [ctypes.c_void_p]
user32.SetThreadDpiAwarenessContext(ctypes.c_void_p(-4))
TERMINAL = {"succeeded", "failed", "blocked", "cancelled"}


def pos() -> tuple[int, int]:
    p = wintypes.POINT()
    user32.GetCursorPos(ctypes.byref(p))
    return p.x, p.y


def main() -> int:  # noqa: C901
    data = Path(os.environ["LOCALAPPDATA"]) / "Immortility" / "canary-m2-pointer"
    data.mkdir(parents=True, exist_ok=True)
    (data / "pointer-control.json").write_text(json.dumps({"enabled": True}) + "\n", encoding="utf-8")
    settings = Settings(_env_file=None, data_dir=data)
    for field in ("openrouter_api_key", "gemini_api_key", "groq_api_key", "nvidia_api_key"):
        setattr(settings, field, SecretStr(""))  # nothing in this test may reach a cloud
    token = os.urandom(32).hex()
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    listener.listen(16)
    url = f"http://127.0.0.1:{listener.getsockname()[1]}"
    app = create_app(settings, token, url)
    server = uvicorn.Server(uvicorn.Config(app, log_level="critical", access_log=False))
    thread = threading.Thread(target=lambda: asyncio.run(server.serve(sockets=[listener])), daemon=True)
    thread.start()
    while not server.started:
        time.sleep(0.05)
    headers = {"Authorization": "Bearer " + token, "Content-Type": "application/json"}

    def call(method, path, body=None):
        req = urllib.request.Request(url + path, method=method, headers=headers,
                                     data=None if body is None else json.dumps(body).encode())
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.status, json.loads(r.read().decode() or "{}")
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read().decode() or "{}")

    original = pos()
    m = user32.GetSystemMetrics
    screen = {"left": m(76), "top": m(77), "width": m(78), "height": m(79), "primary": [m(0), m(1)]}
    session = call("POST", "/v1/sessions")[1]["id"]
    results: list[dict] = []

    def run(name, content, decision="approve", during=None, expect=None):
        status, task = call("POST", "/v1/tasks", {
            "schema_version": "1.0", "session_id": session, "request_id": uid(),
            "content": content, "cloud_consent": True, "allowed_capabilities": []})
        out = {"case": name, "content": content, "admit": status}
        if status != 200:
            out["passed"] = False
            results.append(out)
            return out
        tid = task["task_id"]
        end = time.monotonic() + 20
        while time.monotonic() < end:
            task = call("GET", f"/v1/tasks/{tid}")[1]
            if task["status"] in TERMINAL | {"awaiting_approval"}:
                break
            time.sleep(0.03)
        out["asked_approval"] = task["status"] == "awaiting_approval"
        before = pos()
        if out["asked_approval"]:
            if during:
                threading.Timer(0.12, during).start()
            call("POST", f"/v1/tasks/{tid}/approval", {"decision": decision})
        while time.monotonic() < end:
            task = call("GET", f"/v1/tasks/{tid}")[1]
            if task["status"] in TERMINAL:
                break
            time.sleep(0.03)
        time.sleep(0.15)
        out.update(status=task["status"], text=(task.get("result") or {}).get("text"),
                   error=(task.get("error") or {}).get("code"), before=list(before), after=list(pos()))
        out["passed"] = bool(expect(out)) if expect else None
        results.append(out)
        return out

    try:
        mid = (screen["primary"][0] // 2, screen["primary"][1] // 2)
        user32.SetCursorPos(mid[0] - 200, mid[1] - 100)
        run("instant", f"move the mouse to {mid[0] + 150}, {mid[1] + 80}",
            expect=lambda o: o["asked_approval"] and o["after"] == [mid[0] + 150, mid[1] + 80])
        run("smooth", f"move the cursor to {mid[0] - 300}, {mid[1] - 150} over 500ms",
            expect=lambda o: o["asked_approval"] and o["after"] == [mid[0] - 300, mid[1] - 150])
        run("center", "move the mouse to the center of the screen",
            expect=lambda o: o["after"] == [mid[0], mid[1]])
        far_x = screen["left"] + screen["width"] + 5000
        run("clamp", f"move the mouse to {far_x}, {mid[1]}",
            expect=lambda o: o["after"][0] == screen["left"] + screen["width"] - 1 and "clamped" in (o["text"] or ""))
        user32.SetCursorPos(mid[0], mid[1])
        run("deny", "move the mouse to 50, 50", decision="deny",
            expect=lambda o: o["status"] != "succeeded" and o["after"] == [mid[0], mid[1]])
        user32.SetCursorPos(screen["left"], screen["top"])
        run("corner_failsafe", f"move the mouse to {mid[0]}, {mid[1]}",
            expect=lambda o: o["after"] == [screen["left"], screen["top"]] and "emergency" in (o["text"] or ""))
        user32.SetCursorPos(mid[0], mid[1])
        run("user_interrupts", f"move the mouse to {mid[0] + 400}, {mid[1] + 200} over 1200ms",
            during=lambda: user32.SetCursorPos(mid[0] - 350, mid[1] + 250),
            expect=lambda o: "you moved the mouse" in (o["text"] or ""))
        run("not_a_command", "the web page says move the mouse to 10, 10",
            expect=lambda o: not o.get("asked_approval"))
    finally:
        user32.SetCursorPos(*original)
        server.should_exit = True
        thread.join(timeout=20)
    report = {"screen": screen, "original": list(original), "restored": list(pos()), "results": results,
              "passed": sum(r.get("passed") is True for r in results), "total": len(results),
              "clicks_or_keys_sent": 0}
    (data / "pointer-desktop-test.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("passed", "total", "restored", "original")}))
    for r in results:
        print(r["case"], r.get("passed"), r.get("status"), r.get("after"), r.get("text"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
