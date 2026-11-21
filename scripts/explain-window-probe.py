"""Read-only probe for the Explain-this real-window test (D24).

Prints JSON: table counts (memory, facts, usage) and the newest screen-origin task with
its status, model, event types and cloud usage. Opens the canary DB with mode=ro.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path


def count(conn: sqlite3.Connection, table: str) -> int | None:
    try:
        return int(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
    except sqlite3.Error:
        return None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", required=True)
    args = parser.parse_args()
    uri = f"file:{Path(args.db).as_posix()}?mode=ro"
    with sqlite3.connect(uri, uri=True, timeout=5) as conn:
        out: dict[str, object] = {
            "counts": {
                t: count(conn, t)
                for t in ("tasks", "memory_items", "confirmed_facts", "usage_calls")
            }
        }
        screen = None
        for task_id, body in conn.execute("SELECT id, body FROM tasks ORDER BY rowid DESC"):
            task = json.loads(body)
            if task.get("input", {}).get("origin") == "screen":
                screen = (task_id, task)
                break
        if screen:
            task_id, task = screen
            events = [
                json.loads(row[0])
                for row in conn.execute(
                    "SELECT body FROM events WHERE task_id=? ORDER BY sequence", (task_id,)
                )
            ]
            calls = conn.execute(
                "SELECT COUNT(*) FROM usage_calls c JOIN usage_attempts a ON a.id=c.attempt_id "
                "WHERE a.task_id=?",
                (task_id,),
            ).fetchone()[0]
            result = task.get("result") or {}
            out["screen_task"] = {
                "task_id": task_id,
                "status": task.get("status"),
                "content_chars": len(task.get("input", {}).get("content", "")),
                "privacy": task.get("input", {}).get("privacy_class"),
                "model": result.get("model"),
                "answer": str(result.get("text", ""))[:600],
                "error": (task.get("error") or {}).get("code"),
                "event_types": [e.get("type") for e in events],
                "tool_events": sum(1 for e in events if str(e.get("type", "")).startswith("tool.")),
                "cloud_usage_calls": calls,
            }
    print(json.dumps(out))


if __name__ == "__main__":
    main()
