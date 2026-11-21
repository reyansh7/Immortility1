import json
import re
import sqlite3
import os
import tempfile
import sys
from pathlib import Path
from typing import Any, BinaryIO

from .contracts import BrokerError, TERMINAL, TaskRequest, now, uid, validate
from .ledger import Ledger
from .workflows import WorkflowJournal, WorkflowRequest, workflow_identity
from .windows_observer import ObservationBegin


class OwnedConnection(sqlite3.Connection):
    owner: BinaryIO | None = None

    def close(self) -> None:
        try:
            super().close()
        finally:
            if self.owner is not None:
                self.owner.close()
                self.owner = None


def _own_data(path: Path) -> BinaryIO:
    handle = path.with_name(path.name + ".owner.lock").open("a+b")
    try:
        if os.fstat(handle.fileno()).st_size == 0:
            handle.write(b"\0")
            handle.flush()
        handle.seek(0)
        if sys.platform == "win32":
            import msvcrt

            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl

            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        return handle
    except OSError:
        handle.close()
        raise BrokerError(
            "broker_already_running", "Another broker owns this task database.", 409
        ) from None


class Store:
    def __init__(self, path: Path, *, recover_workflows: bool = False):
        self.data_root = path.parent
        path.parent.mkdir(parents=True, exist_ok=True)
        owner = _own_data(path)
        try:
            self.db = sqlite3.connect(path, check_same_thread=False, factory=OwnedConnection)
            self.db.owner = owner
        except BaseException:
            owner.close()
            raise
        self.db.row_factory = sqlite3.Row
        version = self.db.execute("PRAGMA user_version").fetchone()[0]
        if version > 4:
            self.db.close()
            raise BrokerError(
                "database_version", "Database was created by a newer version; refusing downgrade."
            )
        if version in {1, 2, 3}:
            # Consistent SQLite backup includes WAL data. Never overwrite a prior
            # backup or copy an open database using filesystem reads.
            fd, name = tempfile.mkstemp(
                prefix=path.name + (".pre-m0-" if version == 1 else f".pre-v{version}-"),
                suffix=".sqlite",
                dir=path.parent,
            )
            os.close(fd)
            try:
                with sqlite3.connect(name) as backup:
                    self.db.backup(backup)
            except BaseException:
                Path(name).unlink(missing_ok=True)
                self.db.close()
                raise
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
                CREATE TABLE IF NOT EXISTS workflows(
                    task_id TEXT PRIMARY KEY REFERENCES tasks(id), status TEXT NOT NULL,
                    body TEXT NOT NULL, digest TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS workflow_steps(
                    task_id TEXT NOT NULL REFERENCES workflows(task_id), step_id TEXT NOT NULL,
                    status TEXT NOT NULL, attempts INTEGER NOT NULL, result TEXT,
                    digest TEXT, error_code TEXT, PRIMARY KEY(task_id,step_id));
                CREATE TABLE IF NOT EXISTS model_preferences(id INTEGER PRIMARY KEY CHECK(id=1), body TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS provider_health(route_id TEXT PRIMARY KEY, failures INTEGER NOT NULL, cooldown REAL NOT NULL, auth_blocked INTEGER NOT NULL);
                CREATE TABLE IF NOT EXISTS route_observations(task_id TEXT PRIMARY KEY REFERENCES tasks(id), route_id TEXT NOT NULL, task_class TEXT NOT NULL, protocol_success INTEGER NOT NULL, verified_success INTEGER, latency_ms REAL NOT NULL, tokens INTEGER NOT NULL);
                CREATE INDEX IF NOT EXISTS route_benchmark ON route_observations(route_id,task_class) WHERE verified_success IS NOT NULL;
                CREATE TABLE IF NOT EXISTS inference_routes(attempt_id TEXT PRIMARY KEY REFERENCES usage_attempts(id), provider TEXT NOT NULL, model TEXT NOT NULL, account_scope TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS confirmed_facts(
                    id TEXT PRIMARY KEY,
                    scope TEXT NOT NULL CHECK(scope IN ('user','project')),
                    project_id TEXT NOT NULL DEFAULT '',
                    kind TEXT NOT NULL CHECK(kind IN ('preference','decision','outcome')),
                    trust TEXT NOT NULL CHECK(trust='user-confirmed'),
                    body TEXT NOT NULL,
                    body_key TEXT NOT NULL,
                    status TEXT NOT NULL CHECK(status IN ('active','superseded','revoked')),
                    supersedes TEXT,
                    created TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS confirmed_facts_lookup
                    ON confirmed_facts(status, scope, project_id, kind, body_key);
                PRAGMA user_version=4;
            """)
        self.fts = False
        self.ledger = Ledger(self.db)
        try:
            self.db.execute(
                "CREATE VIRTUAL TABLE IF NOT EXISTS memory_fts USING fts5("
                "session_id UNINDEXED, task_id UNINDEXED, body)"
            )
            self.fts = True
        except sqlite3.OperationalError:
            self.fts = False
        self.fact_fts = False
        try:
            self.db.execute(
                "CREATE VIRTUAL TABLE IF NOT EXISTS fact_fts USING fts5(fact_id UNINDEXED, body)"
            )
            self.fact_fts = True
        except sqlite3.OperationalError:
            self.fact_fts = False
        # Only explicitly authorized local read workflows may recover; no cloud,
        # conversation, approval, write or other side effect is replayed.
        journal = WorkflowJournal(self)
        for row in self.db.execute("SELECT body FROM tasks").fetchall():
            task = json.loads(row["body"])
            if task["status"] not in TERMINAL:
                if recover_workflows and journal.exists(task["task_id"]):
                    try:
                        spec, body = journal.load(task["task_id"])
                        import time

                        if (
                            spec.resume_on_restart
                            and body["expires_at"] > time.time()
                            and task["status"] in {"created", "queued", "running", "verifying"}
                        ):
                            if task["status"] != "queued":
                                self.state(task["task_id"], "queued")
                            journal.status(task["task_id"], "queued")
                            continue
                    except BrokerError:
                        pass
                self.state(
                    task["task_id"],
                    "disconnected",
                    error={
                        "code": "broker_restarted",
                        "message": "Interrupted by broker restart; send again.",
                    },
                )
                if journal.exists(task["task_id"]):
                    journal.status(task["task_id"], "disconnected")

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

    def budget(self, task_id: str, tokens: int, calls: int, timeout_s: int) -> None:
        task = self.get(task_id)
        task["budget"] = {
            "max_paid_usd": 0,
            "max_tokens": tokens,
            "max_calls": calls,
            "timeout_ms": timeout_s * 1000,
        }
        validate("task", task)
        with self.db:
            self.db.execute("UPDATE tasks SET body=? WHERE id=?", (json.dumps(task), task_id))

    def artifact_checkpoint(self, task_id: str, result: dict[str, Any]) -> None:
        task = self.get(task_id)
        if task["status"] != "running":
            raise BrokerError("tool_denied", "Artifact task is no longer running.", 403)
        task["result"] = result
        validate("task", task)
        with self.db:
            self.db.execute("UPDATE tasks SET body=? WHERE id=?", (json.dumps(task), task_id))

    def create(
        self, request: TaskRequest, *, model_selection: dict[str, Any] | None = None
    ) -> tuple[dict[str, Any], bool]:
        encoded = request.model_dump_json()
        row = self.db.execute(
            "SELECT request, body FROM tasks WHERE request_id=?", (request.request_id,)
        ).fetchone()
        if row:
            try:
                same = TaskRequest.model_validate_json(row[0]).model_dump() == request.model_dump()
            except ValueError:
                same = False
            if not same:
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
                "budget_mode": request.budget_mode,
                "allowed_capabilities": request.allowed_capabilities,
                "requested_artifacts": request.requested_artifacts,
                "model_selection": model_selection or {"mode": "auto_cloud", "route_id": None},
                **({"origin": "screen"} if request.origin == "screen" else {}),
            },
            "capabilities": ["chat.respond", *request.allowed_capabilities],
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

    def create_workflow(
        self, request: WorkflowRequest, manifests: dict[str, str]
    ) -> tuple[dict[str, Any], bool]:
        identity = workflow_identity(request.session_id, request.request_id)
        row = self.db.execute(
            "SELECT request,body FROM tasks WHERE request_id=?", (identity,)
        ).fetchone()
        if row:
            try:
                same = (
                    WorkflowRequest.model_validate_json(row["request"]).model_dump()
                    == request.model_dump()
                )
            except ValueError:
                same = False
            if not same:
                raise BrokerError(
                    "idempotency_conflict",
                    "Workflow request ID already has different content.",
                    409,
                )
            return dict(json.loads(row["body"])), False
        if not self.db.execute(
            "SELECT 1 FROM sessions WHERE id=?", (request.session_id,)
        ).fetchone():
            raise BrokerError("not_found", "Session not found.", 404)
        task: dict[str, Any] = {
            "schema_version": "1.0",
            "task_id": uid(),
            "session_id": request.session_id,
            "request_id": identity,
            "created_at": now(),
            "status": "created",
            "workspace_id": None,
            "privacy_class": "personal",
            "recall_excluded": True,
            "input": {
                "type": "local_workflow",
                "source": "text",
                "content": request.label,
                "no_cloud": True,
                "execution": "background",
            },
            "capabilities": list(manifests),
            "budget": {
                "max_paid_usd": 0,
                "max_tokens": 0,
                "max_calls": 0,
                "timeout_ms": request.deadline_seconds * 1000,
            },
        }
        validate("task", task)
        with self.db:
            self.db.execute(
                "INSERT INTO tasks VALUES(?,?,?,?,?)",
                (
                    task["task_id"],
                    request.session_id,
                    identity,
                    request.model_dump_json(),
                    json.dumps(task),
                ),
            )
            WorkflowJournal(self).insert(task["task_id"], request, manifests)
            self._event(task["task_id"], "task.state", {"status": "created"})
        return task, True

    def create_observation(self, request: ObservationBegin) -> dict[str, Any]:
        """Single-use native permission task; never invent cloud consent or retain UI text."""
        if not self.db.execute(
            "SELECT 1 FROM sessions WHERE id=?", (request.session_id,)
        ).fetchone():
            raise BrokerError("not_found", "Session not found.", 404)
        identity = "observation-" + request.request_id
        if self.db.execute("SELECT 1 FROM tasks WHERE request_id=?", (identity,)).fetchone():
            raise BrokerError(
                "idempotency_conflict", "Observation request was already submitted.", 409
            )
        task: dict[str, Any] = {
            "schema_version": "1.0",
            "task_id": uid(),
            "session_id": request.session_id,
            "request_id": identity,
            "created_at": now(),
            "status": "created",
            "workspace_id": None,
            "privacy_class": "personal",
            "recall_excluded": True,
            "input": {
                "type": "window_observation",
                "content": "Inspect one authorized window locally",
                "no_cloud": True,
                "source": "native",
            },
            "capabilities": ["window.inspect.v1"],
            "budget": {"max_paid_usd": 0, "max_tokens": 0, "max_calls": 0, "timeout_ms": 60000},
        }
        validate("task", task)
        with self.db:
            self.db.execute(
                "INSERT INTO tasks VALUES(?,?,?,?,?)",
                (
                    task["task_id"],
                    request.session_id,
                    identity,
                    request.model_dump_json(),
                    json.dumps(task),
                ),
            )
            self._event(task["task_id"], "task.state", {"status": "created"})
        return task

    def create_repair(self, session_id: str, request_id: str, summary: str) -> dict[str, Any]:
        if not self.db.execute("SELECT 1 FROM sessions WHERE id=?", (session_id,)).fetchone():
            raise BrokerError("not_found", "Session not found.", 404)
        identity = "repair-" + request_id
        if self.db.execute("SELECT 1 FROM tasks WHERE request_id=?", (identity,)).fetchone():
            raise BrokerError("idempotency_conflict", "Repair request was already submitted.", 409)
        task: dict[str, Any] = {
            "schema_version": "1.0",
            "task_id": uid(),
            "session_id": session_id,
            "request_id": identity,
            "created_at": now(),
            "status": "created",
            "workspace_id": None,
            "privacy_class": "personal",
            "input": {
                "type": "local_repair",
                "content": summary[:500],
                "no_cloud": True,
                "source": "text",
            },
            "capabilities": ["project.repair.v1"],
            "budget": {"max_paid_usd": 0, "max_tokens": 0, "max_calls": 0, "timeout_ms": 60000},
        }
        validate("task", task)
        with self.db:
            self.db.execute(
                "INSERT INTO tasks VALUES(?,?,?,?,?)",
                (
                    task["task_id"],
                    session_id,
                    identity,
                    json.dumps({"request_id": identity}),
                    json.dumps(task),
                ),
            )
            self._event(task["task_id"], "task.state", {"status": "created"})
        return task

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
            "queued": {"running", "cancelled", "disconnected", "failed", "stopping"},
            "running": {
                "queued",
                "verifying",
                "awaiting_approval",
                "failed",
                "cancelled",
                "blocked",
                "rate_limited",
                "disconnected",
                "stopping",
            },
            "awaiting_approval": {
                "running",
                "cancelled",
                "blocked",
                "failed",
                "disconnected",
                "stopping",
            },
            "verifying": {"queued", "succeeded", "failed", "cancelled", "disconnected", "stopping"},
            # A stop was requested. Only a confirmed executor exit may record `cancelled`.
            "stopping": {"cancelled", "disconnected", "failed"},
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
        task = self.get(task_id)
        if task["session_id"] != session_id or task.get("recall_excluded"):
            return
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
        task = self.get(task_id)
        if task["session_id"] != session_id:
            raise BrokerError("not_found", "Task not found in this session.", 404)
        # Exclude ALL future automatic recall, while retaining visible task evidence.
        # This is not secure deletion of history/WAL/backups.
        task["recall_excluded"] = True
        validate("task", task)
        with self.db:
            self.db.execute("UPDATE tasks SET body=? WHERE id=?", (json.dumps(task), task_id))
            if not self.fts:
                return 0
            cursor = self.db.execute(
                "DELETE FROM memory_fts WHERE session_id=? AND task_id=?",
                (session_id, task_id),
            )
        return int(cursor.rowcount)

    def confirm_fact(self, scope: str, project_id: str, kind: str, text: str) -> dict[str, str]:
        if not self.fact_fts:
            raise BrokerError("tool_denied", "Local fact search is unavailable.", 503)
        body = " ".join(text.split())[:500]
        key = body.casefold()
        if (
            not body
            or scope not in {"user", "project"}
            or kind
            not in {
                "preference",
                "decision",
                "outcome",
            }
        ):
            raise BrokerError(
                "invalid_request", "Confirmed memory needs a short factual statement.", 400
            )
        if scope == "user" and project_id:
            raise BrokerError("invalid_request", "User memory has no project scope.", 400)
        if scope == "project" and len(project_id) != 64:
            raise BrokerError("invalid_request", "Project memory requires its project scope.", 400)
        existing = self.db.execute(
            "SELECT id,body FROM confirmed_facts WHERE status='active' AND scope=? "
            "AND project_id=? AND kind=? AND body_key=?",
            (scope, project_id, kind, key),
        ).fetchone()
        if existing:
            return self._fact_row(str(existing["id"]))
        fact_id = uid()
        with self.db:
            self.db.execute(
                "INSERT INTO confirmed_facts VALUES(?,?,?,?,?,?,?,?,?,?)",
                (
                    fact_id,
                    scope,
                    project_id,
                    kind,
                    "user-confirmed",
                    body,
                    key,
                    "active",
                    None,
                    now(),
                ),
            )
            self.db.execute(
                "INSERT INTO fact_fts(fact_id, body) VALUES(?,?)",
                (fact_id, body),
            )
        return self._fact_row(fact_id)

    def correct_fact(self, fact_id: str, text: str) -> dict[str, str]:
        current = self._active_fact(fact_id)
        body = " ".join(text.split())[:500]
        if not body:
            raise BrokerError("invalid_request", "A correction needs replacement text.", 400)
        if body.casefold() == current["body_key"]:
            return self._fact_row(fact_id)
        replacement = self.confirm_fact(
            current["scope"], current["project_id"], current["kind"], body
        )
        if replacement["id"] == fact_id:
            return replacement
        with self.db:
            self.db.execute(
                "UPDATE confirmed_facts SET status='superseded' WHERE id=? AND status='active'",
                (fact_id,),
            )
            self.db.execute("DELETE FROM fact_fts WHERE fact_id=?", (fact_id,))
            self.db.execute(
                "UPDATE confirmed_facts SET supersedes=? WHERE id=? AND supersedes IS NULL",
                (fact_id, replacement["id"]),
            )
        return self._fact_row(replacement["id"])

    def revoke_fact(self, fact_id: str) -> dict[str, str]:
        self._active_fact(fact_id)
        with self.db:
            self.db.execute(
                "UPDATE confirmed_facts SET status='revoked' WHERE id=? AND status='active'",
                (fact_id,),
            )
            self.db.execute("DELETE FROM fact_fts WHERE fact_id=?", (fact_id,))
        row = self._fact_row(fact_id)
        return row

    def recall_facts(self, query: str, project_id: str, limit: int = 5) -> list[dict[str, str]]:
        if not self.fact_fts:
            return []
        tokens = re.findall(r"[A-Za-z0-9]{3,}", query)[:8]
        if not tokens:
            return []
        try:
            rows = self.db.execute(
                "SELECT fact_id FROM fact_fts WHERE fact_fts MATCH ? LIMIT 16",
                (" OR ".join(f'"{token}"' for token in tokens),),
            ).fetchall()
        except sqlite3.OperationalError:
            return []
        chosen: list[dict[str, str]] = []
        used = 0
        for row in rows:
            fact = self._fact_row(str(row["fact_id"]))
            if fact["status"] != "active" or fact["trust"] != "user-confirmed":
                continue
            if fact["scope"] == "project" and fact["project_id"] != project_id:
                continue
            if fact["scope"] not in {"user", "project"}:
                continue
            if used + len(fact["body"]) > 800 or len(chosen) >= limit:
                break
            chosen.append(fact)
            used += len(fact["body"])
        return chosen

    def _active_fact(self, fact_id: str) -> dict[str, str]:
        fact = self._fact_row(fact_id)
        if fact["status"] != "active":
            raise BrokerError("not_found", "That confirmed memory is no longer active.", 404)
        return fact

    def _fact_row(self, fact_id: str) -> dict[str, str]:
        row = self.db.execute(
            "SELECT id,scope,project_id,kind,trust,body,body_key,status,supersedes,created "
            "FROM confirmed_facts WHERE id=?",
            (fact_id,),
        ).fetchone()
        if row is None:
            raise BrokerError("not_found", "Confirmed memory was not found.", 404)
        return {key: "" if row[key] is None else str(row[key]) for key in row.keys()}

    def history(self, session_id: str) -> list[dict[str, str]]:
        history = []
        for task in self.tasks(session_id):
            if (
                task["status"] == "succeeded"
                and not task.get("recall_excluded")
                # Explain-this screen text stays in its own local turn: later (possibly
                # cloud) turns never receive it as history.
                and task["input"].get("origin") != "screen"
            ):
                history.extend(
                    [
                        {"role": "user", "content": task["input"]["content"]},
                        {"role": "assistant", "content": task["result"]["text"]},
                    ]
                )
        return history[-20:]
