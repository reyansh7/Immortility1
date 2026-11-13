import json
import re
import sqlite3
from pathlib import Path
from typing import Any

from .contracts import BrokerError, TERMINAL, TaskRequest, now, uid, validate


class Store:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        if self.db.execute("PRAGMA user_version").fetchone()[0] > 1:
            self.db.close()
            raise BrokerError(
                "database_version", "Database was created by a newer version; refusing downgrade."
            )
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA foreign_keys=ON")
        self.db.execute("PRAGMA busy_timeout=5000")
        with self.db:
            self.db.executescript("""
                CREATE TABLE IF NOT EXISTS sessions(id TEXT PRIMARY KEY, created TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS tasks(
                    id TEXT PRIMARY KEY, session_id TEXT NOT NULL REFERENCES sessions(id),
                    request_id TEXT UNIQUE NOT NULL, request TEXT NOT NULL, body TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS events(
                    task_id TEXT NOT NULL REFERENCES tasks(id), sequence INTEGER NOT NULL,
                    body TEXT NOT NULL, PRIMARY KEY(task_id, sequence));
                PRAGMA user_version=1;
            """)
        self.fts = False
        try:
            self.db.execute(
                "CREATE VIRTUAL TABLE IF NOT EXISTS memory_fts USING fts5("
                "session_id UNINDEXED, task_id UNINDEXED, body)"
            )
            self.fts = True
        except sqlite3.OperationalError:
            self.fts = False
        # Never replay inference or side effects on restart.
        for row in self.db.execute("SELECT body FROM tasks").fetchall():
            task = json.loads(row["body"])
            if task["status"] not in TERMINAL:
                self.state(
                    task["task_id"],
                    "disconnected",
                    error={
                        "code": "broker_restarted",
                        "message": "Interrupted by broker restart; send again.",
                    },
                )

    def sessions(self) -> list[dict[str, Any]]:
        return [
            dict(row) for row in self.db.execute("SELECT * FROM sessions ORDER BY created DESC")
        ]

    def session(self) -> dict[str, Any]:
        value = {"id": uid(), "created": now()}
        with self.db:
            self.db.execute("INSERT INTO sessions VALUES(:id,:created)", value)
        return value

    def tasks(self, session_id: str) -> list[dict[str, Any]]:
        return [
            json.loads(row[0])
            for row in self.db.execute(
                "SELECT body FROM tasks WHERE session_id=? ORDER BY rowid", (session_id,)
            )
        ]

    def get(self, task_id: str) -> dict[str, Any]:
        row = self.db.execute("SELECT body FROM tasks WHERE id=?", (task_id,)).fetchone()
        if not row:
            raise BrokerError("not_found", "Task not found.", 404)
        return dict(json.loads(row[0]))

    def create(self, request: TaskRequest) -> tuple[dict[str, Any], bool]:
        encoded = request.model_dump_json()
        row = self.db.execute(
            "SELECT request, body FROM tasks WHERE request_id=?", (request.request_id,)
        ).fetchone()
        if row:
            if TaskRequest.model_validate_json(row[0]).model_dump() != request.model_dump():
                raise BrokerError(
                    "idempotency_conflict", "Request ID already has different content."
                )
            return json.loads(row[1]), False
        if not self.db.execute(
            "SELECT 1 FROM sessions WHERE id=?", (request.session_id,)
        ).fetchone():
            raise BrokerError("not_found", "Session not found.", 404)
        task: dict[str, Any] = {
            "schema_version": "1.0",
            "task_id": uid(),
            "session_id": request.session_id,
            "request_id": request.request_id,
            "created_at": now(),
            "status": "created",
            "workspace_id": None,
            "privacy_class": request.privacy_class,
            "input": {
                "type": "text",
                "content": request.content,
                "source": request.source,
                "response_length": request.response_length,
            },
            "capabilities": ["chat.respond"],
            "budget": {"max_paid_usd": 0, "timeout_ms": 90000, "max_tokens": 2048},
        }
        validate("task", task)
        with self.db:
            self.db.execute(
                "INSERT INTO tasks VALUES(?,?,?,?,?)",
                (
                    task["task_id"],
                    request.session_id,
                    request.request_id,
                    encoded,
                    json.dumps(task),
                ),
            )
            self._event(task["task_id"], "task.state", {"status": "created"})
        return task, True

    def _event(self, task_id: str, kind: str, data: dict[str, Any]) -> dict[str, Any]:
        sequence = self.db.execute(
            "SELECT COALESCE(MAX(sequence),0)+1 FROM events WHERE task_id=?", (task_id,)
        ).fetchone()[0]
        event = {
            "schema_version": "1.0",
            "event_id": uid(),
            "task_id": task_id,
            "sequence": sequence,
            "timestamp": now(),
            "type": kind,
            "actor": "immortility-broker",
            "data": data,
            "correlation_id": self.get(task_id)["request_id"],
        }
        validate("event", event)
        self.db.execute("INSERT INTO events VALUES(?,?,?)", (task_id, sequence, json.dumps(event)))
        return event

    def event(self, task_id: str, kind: str, data: dict[str, Any]) -> dict[str, Any]:
        with self.db:
            return self._event(task_id, kind, data)

    def state(self, task_id: str, status: str, **updates: Any) -> None:
        task = self.get(task_id)
        allowed = {
            "created": {"queued", "blocked", "cancelled", "disconnected"},
            "queued": {"running", "cancelled", "disconnected", "failed"},
            "running": {
                "verifying",
                "awaiting_approval",
                "failed",
                "cancelled",
                "blocked",
                "rate_limited",
                "disconnected",
            },
            "awaiting_approval": {"running", "cancelled", "blocked", "failed", "disconnected"},
            "verifying": {"succeeded", "failed", "cancelled", "disconnected"},
        }
        if status not in allowed.get(task["status"], set()):
            raise BrokerError("invalid_transition", "Invalid task transition.")
        task.update(status=status, **updates)
        validate("task", task)
        with self.db:
            self.db.execute("UPDATE tasks SET body=? WHERE id=?", (json.dumps(task), task_id))
            self._event(task_id, "task.state", {"status": status})
            if task.get("error"):
                self._event(task_id, "task.error", task["error"])

    def events(self, task_id: str, after: int = 0) -> list[dict[str, Any]]:
        self.get(task_id)
        return [
            json.loads(row[0])
            for row in self.db.execute(
                "SELECT body FROM events WHERE task_id=? AND sequence>? ORDER BY sequence LIMIT 256",
                (task_id, after),
            )
        ]

    def remember(self, session_id: str, task_id: str, text: str) -> None:
        if not self.fts:
            return
        body = " ".join(text.split())[:2000]
        if not body:
            return
        with self.db:
            self.db.execute("DELETE FROM memory_fts WHERE task_id=?", (task_id,))
            self.db.execute(
                "INSERT INTO memory_fts(session_id, task_id, body) VALUES(?,?,?)",
                (session_id, task_id, body),
            )

    def recall(self, session_id: str, query: str, limit: int = 5) -> list[dict[str, str]]:
        if not self.fts:
            return []
        tokens = re.findall(r"[A-Za-z0-9]{3,}", query)[:8]
        if not tokens:
            return []
        try:
            rows = self.db.execute(
                "SELECT task_id, body FROM memory_fts WHERE memory_fts MATCH ? "
                "AND session_id=? LIMIT ?",
                (" OR ".join(tokens), session_id, limit),
            ).fetchall()
        except sqlite3.OperationalError:
            return []
        return [{"task_id": str(row["task_id"]), "body": str(row["body"])} for row in rows]

    def forget(self, session_id: str, task_id: str) -> int:
        if not self.fts:
            return 0
        with self.db:
            cursor = self.db.execute(
                "DELETE FROM memory_fts WHERE session_id=? AND task_id=?",
                (session_id, task_id),
            )
        return int(cursor.rowcount)

    def history(self, session_id: str) -> list[dict[str, str]]:
        history = []
        for task in self.tasks(session_id):
            if task["status"] == "succeeded":
                history.extend(
                    [
                        {"role": "user", "content": task["input"]["content"]},
                        {"role": "assistant", "content": task["result"]["text"]},
                    ]
                )
        return history[-20:]
