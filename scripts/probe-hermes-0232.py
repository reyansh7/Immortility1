"""One live Hermes 0.23.2 tool-selection probe. Does not print credentials."""

import json
import os
import socket
import threading
import time
import urllib.request
from pathlib import Path

import uvicorn

from immortility_broker.app import create_app
from immortility_broker.config import Settings
from immortility_broker.contracts import uid

SENTENCE = (
    "Check the current time, calculate 247 × 36, and inspect the current project status. "
    "Use your tools and report the verified results."
)


def main() -> None:
    local = Path(os.environ["LOCALAPPDATA"])
    data = local / "Immortility" / "hermes-0232" / "probe"
    data.mkdir(parents=True, exist_ok=True)
    root = Path(__file__).resolve().parents[1]
    (data / "local-tools.json").write_text(json.dumps({"enabled": True}) + "\n", encoding="utf-8")
    (data / "workspace.json").write_text(
        json.dumps(
            {
                "enabled": False,
                "root": str(root),
                "project_read_enabled": True,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    settings = Settings(
        _env_file=None,
        data_dir=data,
        hermes_0232_gateway=True,
        local_tools_enabled=True,
        project_read_enabled=True,
        workspace_root=root,
    )
    settings.load_credentials()
    token = os.urandom(32).hex()
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.bind(("127.0.0.1", 0))
    listener.listen(128)
    port = listener.getsockname()[1]
    url = f"http://127.0.0.1:{port}"
    app = create_app(settings, token, url)
    server = uvicorn.Server(uvicorn.Config(app, log_level="critical", access_log=False))
    thread = threading.Thread(target=lambda: __import__("asyncio").run(server.serve(sockets=[listener])), daemon=True)
    thread.start()
    deadline = time.monotonic() + 150
    while time.monotonic() < deadline:
        if server.started:
            break
        time.sleep(0.2)
    else:
        raise SystemExit("broker did not start")
    headers = {"Authorization": "Bearer " + token, "Content-Type": "application/json"}

    def call(method: str, path: str, body: dict | None = None) -> dict:
        request = urllib.request.Request(
            url + path,
            data=None if body is None else json.dumps(body).encode(),
            headers=headers,
            method=method,
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode())

    session = call("POST", "/v1/sessions")
    task = call(
        "POST",
        "/v1/tasks",
        {
            "schema_version": "1.0",
            "session_id": session["id"],
            "request_id": uid(),
            "content": SENTENCE,
            "privacy_class": "personal",
            "cloud_consent": True,
            "source": "text",
            "budget_mode": "fast",
            "allowed_capabilities": [
                "clock.now.v1",
                "arithmetic.multiply.v1",
                "project.outline.v1",
                "project.search.v1",
            ],
        },
    )
    task_id = task["task_id"]
    finished = task
    deadline = time.monotonic() + 180
    while finished.get("status") not in {
        "succeeded",
        "failed",
        "cancelled",
        "blocked",
        "rate_limited",
        "disconnected",
    }:
        if time.monotonic() > deadline:
            break
        time.sleep(1)
        finished = call("GET", "/v1/tasks/" + task_id)
    event_request = urllib.request.Request(
        url + "/v1/tasks/" + task_id + "/events",
        headers={"Authorization": "Bearer " + token},
        method="GET",
    )
    with urllib.request.urlopen(event_request, timeout=30) as response:
        raw_events = response.read().decode()
    tools = []
    notices = []
    for line in raw_events.splitlines():
        if not line.startswith("data:"):
            continue
        event = json.loads(line.split(":", 1)[1])
        kind = str(event.get("type", ""))
        if kind.startswith("tool."):
            tools.append({"type": kind, "data": event.get("data")})
        elif kind == "audit.notice":
            payload = event.get("data") if isinstance(event.get("data"), dict) else {}
            notices.append(
                {
                    "name": payload.get("name") or payload.get("code"),
                    "provider": payload.get("provider"),
                    "model": payload.get("model"),
                    "served_model": payload.get("served_model"),
                    "status": payload.get("status"),
                }
            )
    result = finished.get("result") if isinstance(finished.get("result"), dict) else {}
    error = finished.get("error") if isinstance(finished.get("error"), dict) else {}
    summary = {
        "status": finished.get("status"),
        "provider": result.get("provider"),
        "model": result.get("model"),
        "error_code": error.get("code"),
        "tools": tools,
        "notices": notices,
        "answer": result.get("text"),
    }
    summary["process_lifecycle"] = "task_recorded_before_shutdown"
    print(json.dumps(summary, indent=2), flush=True)
    server.should_exit = True
    thread.join(timeout=3)
    raise SystemExit(0 if finished.get("status") == "succeeded" else 1)


if __name__ == "__main__":
    main()
