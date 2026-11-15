"""Transactional per-attempt reservations. Unknown usage stays charged, never zero."""

import json
import sqlite3
import threading
from datetime import date, timedelta
from typing import Any

from .contracts import BrokerError, now, uid


class Ledger:
    def __init__(self, db: sqlite3.Connection):
        self.db = db
        self.lock = threading.RLock()
        with db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS usage_attempts(
                    id TEXT PRIMARY KEY, task_id TEXT NOT NULL, parent_id TEXT,
                    route TEXT NOT NULL, token_cap INTEGER NOT NULL, call_cap INTEGER NOT NULL);
                CREATE TABLE IF NOT EXISTS usage_calls(
                    id TEXT PRIMARY KEY, attempt_id TEXT NOT NULL REFERENCES usage_attempts(id),
                    created TEXT NOT NULL, input_reserved INTEGER NOT NULL,
                    output_reserved INTEGER NOT NULL, charged INTEGER NOT NULL,
                    status TEXT NOT NULL, reported TEXT);
                CREATE TABLE IF NOT EXISTS inference_routes(
                    attempt_id TEXT PRIMARY KEY REFERENCES usage_attempts(id), provider TEXT NOT NULL,
                    model TEXT NOT NULL, account_scope TEXT NOT NULL);
                CREATE INDEX IF NOT EXISTS usage_created ON usage_calls(created,attempt_id);
                CREATE INDEX IF NOT EXISTS inference_account ON inference_routes(provider,account_scope);
            """)

    def begin(self, task_id: str, token_cap: int, call_cap: int, route: str) -> str:
        attempt_id = uid()
        with self.lock, self.db:
            self.db.execute(
                "INSERT INTO usage_attempts VALUES(?,?,?,?,?,?)",
                (attempt_id, task_id, None, route, token_cap, call_cap),
            )
        return attempt_id

    def bind_route(
        self, attempt_id: str, provider: str, model: str, account_scope: str, route_id: str
    ) -> None:
        with self.lock, self.db:
            previous = self.db.execute(
                "SELECT provider,model,account_scope FROM inference_routes WHERE attempt_id=?",
                (attempt_id,),
            ).fetchone()
            if previous and tuple(previous) != (provider, model, account_scope):
                raise BrokerError(
                    "route_changed",
                    "An active task cannot silently switch provider or account.",
                    403,
                )
            self.db.execute(
                "INSERT OR IGNORE INTO inference_routes VALUES(?,?,?,?)",
                (attempt_id, provider, model, account_scope),
            )
            self.db.execute("UPDATE usage_attempts SET route=? WHERE id=?", (route_id, attempt_id))

    def reserve(self, attempt_id: str, input_tokens: int, output_tokens: int) -> str:
        if input_tokens < 0 or output_tokens <= 0:
            raise BrokerError("budget_exhausted", "Invalid token reservation.", 403)
        with self.lock, self.db:
            self.db.execute("BEGIN IMMEDIATE")
            attempt = self.db.execute(
                "SELECT * FROM usage_attempts WHERE id=?", (attempt_id,)
            ).fetchone()
            if attempt is None:
                raise BrokerError("inference_closed", "Unknown inference attempt.", 403)
            scope = self.db.execute(
                "SELECT provider,account_scope FROM inference_routes WHERE attempt_id=?",
                (attempt_id,),
            ).fetchone()
            if scope:
                # Application policy across tasks; not a claim of provider quota.
                # Unknown/sent reservations count, failed preflight does not.
                day = date.fromisoformat(now()[:10])
                requests, charged = self.db.execute(
                    "SELECT COUNT(*),COALESCE(SUM(c.charged),0) FROM usage_calls c JOIN inference_routes r ON r.attempt_id=c.attempt_id WHERE r.provider=? AND r.account_scope=? AND c.created>=? AND c.created<? AND c.status!='not_sent'",
                    (
                        scope["provider"],
                        scope["account_scope"],
                        day.isoformat(),
                        (day + timedelta(days=1)).isoformat(),
                    ),
                ).fetchone()
                if requests >= 50 or charged + input_tokens + output_tokens > 100000:
                    raise BrokerError(
                        "shared_budget_exhausted",
                        "The shared local daily request/token ceiling is exhausted. No fallback sent.",
                        403,
                    )
            if self.db.execute(
                "SELECT 1 FROM usage_calls c JOIN usage_attempts a ON a.id=c.attempt_id "
                "WHERE a.task_id=? AND c.status='overrun'",
                (attempt["task_id"],),
            ).fetchone():
                raise BrokerError(
                    "usage_overrun", "Task blocked after provider usage overrun.", 403
                )
            # Include every attempt/retry/review/child belonging to the same task.
            used, calls = self.db.execute(
                "SELECT COALESCE(SUM(c.charged),0),COUNT(*) FROM usage_calls c "
                "JOIN usage_attempts a ON a.id=c.attempt_id WHERE a.task_id=?",
                (attempt["task_id"],),
            ).fetchone()
            if (
                calls >= attempt["call_cap"]
                or used + input_tokens + output_tokens > attempt["token_cap"]
            ):
                raise BrokerError("budget_exhausted", "Task token or call budget exhausted.", 403)
            call_id = uid()
            self.db.execute(
                "INSERT INTO usage_calls VALUES(?,?,?,?,?,?,?,?)",
                (
                    call_id,
                    attempt_id,
                    now(),
                    input_tokens,
                    output_tokens,
                    input_tokens + output_tokens,
                    "reserved",
                    None,
                ),
            )
        return call_id

    def settle(self, call_id: str, usage: dict[str, Any] | None, *, sent: bool = True) -> None:
        with self.lock:
            self._settle(call_id, usage, sent=sent)

    def _settle(self, call_id: str, usage: dict[str, Any] | None, *, sent: bool) -> None:
        row = self.db.execute("SELECT * FROM usage_calls WHERE id=?", (call_id,)).fetchone()
        if row is None:
            raise BrokerError("inference_closed", "Unknown inference call.", 403)
        if row["status"] != "reserved":
            raise BrokerError("usage_conflict", "Usage call was already settled.", 409)
        clean: dict[str, Any] | None = None
        if usage is not None:
            prompt, completion = usage.get("prompt_tokens"), usage.get("completion_tokens")
            if (
                type(prompt) is not int
                or type(completion) is not int
                or prompt < 0
                or completion < 0
            ):
                usage = None
            else:
                clean = {"prompt_tokens": prompt, "completion_tokens": completion}
                for name in ("prompt_tokens_details", "completion_tokens_details"):
                    details = usage.get(name)
                    if isinstance(details, dict):
                        clean[name] = {
                            str(k): v for k, v in details.items() if type(v) is int and v >= 0
                        }
        charged = (
            0
            if not sent
            else row["charged"]
            if clean is None
            else clean["prompt_tokens"] + clean["completion_tokens"]
        )
        overrun = clean is not None and (
            clean["prompt_tokens"] > row["input_reserved"]
            or clean["completion_tokens"] > row["output_reserved"]
        )
        with self.db:
            self.db.execute(
                "UPDATE usage_calls SET status=?,reported=?,charged=? WHERE id=?",
                (
                    "overrun"
                    if overrun
                    else "not_sent"
                    if not sent
                    else "unknown"
                    if clean is None
                    else "reported",
                    json.dumps(clean) if clean is not None else None,
                    charged,
                    call_id,
                ),
            )
        if overrun:
            raise BrokerError(
                "usage_overrun",
                "Provider usage exceeded its reservation; further calls blocked.",
                403,
            )

    def summary(self, task_id: str) -> dict[str, Any]:
        rows = self.db.execute(
            "SELECT c.* FROM usage_calls c JOIN usage_attempts a ON a.id=c.attempt_id WHERE a.task_id=? ORDER BY c.rowid",
            (task_id,),
        ).fetchall()
        reported = [json.loads(r["reported"]) for r in rows if r["reported"] is not None]
        return {
            "calls": len(rows),
            "dispatch_attempts": sum(
                r["status"] in {"reported", "unknown", "overrun"} for r in rows
            ),
            "not_sent_calls": sum(r["status"] == "not_sent" for r in rows),
            "pending_reservations": sum(r["status"] == "reserved" for r in rows),
            "charged_tokens": sum(r["charged"] for r in rows),
            "unknown_calls": sum(r["status"] in {"unknown", "reserved"} for r in rows),
            "prompt_tokens": sum(r["prompt_tokens"] for r in reported) if reported else None,
            "completion_tokens": sum(r["completion_tokens"] for r in reported)
            if reported
            else None,
        }

    def owns_attempt(self, attempt_id: str, task_id: str) -> bool:
        return (
            self.db.execute(
                "SELECT 1 FROM usage_attempts WHERE id=? AND task_id=?", (attempt_id, task_id)
            ).fetchone()
            is not None
        )

    def details(self, task_id: str) -> dict[str, Any]:
        attempts = [
            dict(row)
            for row in self.db.execute(
                "SELECT * FROM usage_attempts WHERE task_id=? ORDER BY rowid", (task_id,)
            )
        ]
        calls = []
        for row in self.db.execute(
            "SELECT c.* FROM usage_calls c JOIN usage_attempts a ON a.id=c.attempt_id WHERE a.task_id=? ORDER BY c.rowid",
            (task_id,),
        ):
            item = dict(row)
            item["reported"] = json.loads(item["reported"]) if item["reported"] else None
            calls.append(item)
        routes = [
            dict(row)
            for row in self.db.execute(
                "SELECT r.attempt_id,r.provider,r.model FROM inference_routes r JOIN usage_attempts a ON a.id=r.attempt_id WHERE a.task_id=?",
                (task_id,),
            )
        ]
        return {
            "schema_version": "1.0",
            "summary": self.summary(task_id),
            "attempts": attempts,
            "calls": calls,
            "routes": routes,
        }


def input_upper_bound(messages: list[dict[str, str]]) -> int:
    # Free router can choose different tokenizers. UTF-8 byte count is deliberately
    # conservative for text BPE models; include envelope/role special-token allowance.
    return 64 + sum(len(m["content"].encode("utf-8")) + 32 for m in messages)
