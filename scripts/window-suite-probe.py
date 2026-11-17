"""Read-only correlation for the packaged-window suite.

Given a unique token typed into the window, find the task it created in the canary
database and print one JSON record that ties together: the window's request id, the
task, the Hermes run ids, each tool call with its authorization decision and receipt,
approval requests and decisions, and the final state. The database is opened with
``mode=ro``; this script never writes.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path


def probe(db: Path, token: str) -> dict[str, object]:
    uri = f"file:{db.as_posix()}?mode=ro"
    with sqlite3.connect(uri, uri=True, timeout=5) as conn:
        rows = conn.execute(
            "SELECT id, request_id, request, body FROM tasks WHERE request LIKE ? ORDER BY rowid",
            (f"%{token}%",),
        ).fetchall()
        if not rows:
            return {"token": token, "found": False}
        task_id, request_id, _request, body = rows[-1]
        task = json.loads(body)
        events = [
            json.loads(item[0])
            for item in conn.execute(
                "SELECT body FROM events WHERE task_id=? ORDER BY sequence", (task_id,)
            )
        ]
    text = ""
    states: list[str] = []
    runs: list[str] = []
    calls: dict[str, dict[str, object]] = {}
    approvals: list[dict[str, object]] = []
    notices: list[str] = []
    for event in events:
        kind = event.get("type")
        data = event.get("data") or {}
        if kind == "message.delta" and isinstance(data.get("text"), str):
            text += data["text"]
        elif kind == "task.state":
            states.append(str(data.get("status")))
        elif kind == "approval.requested":
            approvals.append(
                {
                    "request_id": data.get("request_id"),
                    "tool_call_id": data.get("tool_call_id"),
                    "capability": data.get("capability"),
                }
            )
        elif kind == "approval.resolved":
            approvals.append({"resolved": data.get("decision"), "request_id": data.get("request_id")})
        elif kind == "audit.notice":
            name = str(data.get("name"))
            notices.append(name)
            if name == "hermes.run.started" and data.get("run_id"):
                runs.append(str(data["run_id"]))
            if name == "tool.authorization":
                key = str(data.get("tool_call_id") or f"anon-{len(calls)}")
                calls.setdefault(key, {})["authorization"] = data.get("decision")
                calls[key]["capability"] = data.get("capability")
                if data.get("reason"):
                    calls[key]["reason"] = data.get("reason")
        if kind in {"tool.started", "tool.completed"} and data.get("tool_call_id"):
            entry = calls.setdefault(str(data["tool_call_id"]), {})
            entry[kind.split(".")[1]] = data.get("status", True)
            if data.get("receipt"):
                entry["receipt"] = data["receipt"]
    error = task.get("error") or {}
    return {
        "token": token,
        "found": True,
        "request_id": request_id,
        "task_id": task_id,
        "session_id": task.get("session_id"),
        "status": task.get("status"),
        "states": states,
        "hermes_run_ids": runs,
        "tool_calls": calls,
        "approvals": approvals,
        "notices": sorted(set(notices)),
        "error_code": error.get("code"),
        "final_text": text,
        "events": len(events),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", required=True, type=Path)
    parser.add_argument("--token", required=True)
    args = parser.parse_args()
    if not args.db.exists():
        print(json.dumps({"token": args.token, "found": False, "error": "no database"}))
        return 0
    print(json.dumps(probe(args.db, args.token)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
