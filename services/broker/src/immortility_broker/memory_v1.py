"""Personal memory v1 (M2/P3). One authority: the broker's existing SQLite database.

Additive tables only (``memory_items`` + ``memory_items_fts``); ``PRAGMA user_version`` is
not changed, so an older broker opening the same file ignores them. The tables are created
only when memory v1 is enabled (``memory-v1.json`` in the data dir), so a data directory
that never opted in is never modified.

Categories
  working     short-lived session context (expires)
  episodic    what happened: verified task receipts, with the task as provenance
  semantic    durable facts about the user's world / projects
  procedural  how the user wants things done (workflows, steps)
  profile     the user: name, preferences, style

Write gating (the broker decides, never the content):
  * ``user``     – the user's own words or an explicit UI action → active.
  * ``verified`` – broker-verified receipts (tool results it checked) → active, episodic only.
  * ``inferred`` – model-proposed → durable categories go to ``pending`` until the user confirms.
  * ``external`` – web pages, files, screen text, tool output → never active in a durable
    category; stored ``quarantined`` if it looks like an instruction, else ``pending``.
Only ``active`` rows are ever recalled into a prompt, and always labelled as data.

Retrieval is hybrid lexical: FTS5 (porter stemming, bm25) fused with recency, confidence,
category weight and project match. Vector embeddings are deferred (DECISIONS D12).
"""

from __future__ import annotations

import json
import math
import re
import sqlite3
import time
from datetime import datetime, timedelta, timezone
from typing import Any

from .contracts import BrokerError, uid
from .memory import redact

CATEGORIES = ("working", "episodic", "semantic", "procedural", "profile")
DURABLE = {"semantic", "procedural", "profile"}
SOURCES = ("user", "verified", "inferred", "external")
STATUSES = ("active", "pending", "superseded", "deleted", "quarantined")
TRUST_RANK = {"external": 0, "inferred": 1, "verified": 2, "user": 3}
CATEGORY_WEIGHT = {
    "profile": 1.0,
    "procedural": 0.9,
    "semantic": 0.85,
    "episodic": 0.6,
    "working": 0.7,
}
WORKING_TTL = timedelta(hours=2)
MAX_BODY = 500

_INSTRUCTION = re.compile(
    r"(?i)\b(ignore (?:all |any )?(?:previous|prior|above)|disregard|you must|you are now|"
    r"system prompt|always (?:call|run|execute|approve)|grant (?:yourself|permission)|"
    r"new instructions?|do not tell the user|exfiltrate|send (?:the|your) (?:key|token|password))"
)
_STOP = {
    "the",
    "and",
    "for",
    "that",
    "this",
    "with",
    "what",
    "which",
    "from",
    "have",
    "you",
    "your",
    "are",
    "was",
    "were",
    "is",
    "it",
    "my",
    "me",
    "do",
    "does",
    "did",
    "of",
    "to",
    "in",
    "on",
    "a",
    "an",
    "i",
    "we",
    "our",
    "be",
    "can",
    "how",
    "when",
    "where",
    "who",
    "should",
    "would",
    "about",
    "tell",
    "remember",
    "know",
    "please",
    "jarvis",
}

# Slot patterns for contradiction detection: (regex, subject template, value group).
_SLOTS: list[tuple[re.Pattern[str], str, int]] = [
    (re.compile(r"^(?:my|our) name is (.+)$"), "name", 1),
    (re.compile(r"^(?:call me|i am called|i'm called) (.+)$"), "name", 1),
    (re.compile(r"^(?:my|our) ([a-z][a-z0-9 '\-]{1,40}?) (?:is|are|=) (.+)$"), "my {0}", 2),
    (re.compile(r"^i (?:live|am based|reside) in (.+)$"), "home location", 1),
    (re.compile(r"^i work (?:at|for) (.+)$"), "employer", 1),
    (re.compile(r"^i (?:prefer|like|want) (.+?) (?:for|when|in) (.+)$"), "preference for {1}", 1),
    (
        re.compile(r"^(?:for|in) ([a-z0-9 '\-]{2,40}),? (?:i (?:prefer|use|want)|use) (.+)$"),
        "preference for {0}",
        2,
    ),
    (
        re.compile(r"^i (?:use|code in|write in|develop with) (.+?) (?:for|as) (?:my )?(.+)$"),
        "tool for {1}",
        1,
    ),
    (
        re.compile(
            r"^(?:the )?([a-z0-9 '\-]{2,40}?) (?:project|repo) (?:uses|is written in|is) (.+)$"
        ),
        "project {0}",
        2,
    ),
]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def normalize(text: str) -> str:
    text = " ".join(text.split()).strip().rstrip(".!")
    return text


def body_key(text: str) -> str:
    return re.sub(r"[^a-z0-9 ]+", "", normalize(text).casefold()).strip()


def tokens(text: str) -> set[str]:
    return {t for t in re.findall(r"[a-z0-9]+", text.casefold()) if len(t) > 2 and t not in _STOP}


def subject_of(text: str) -> tuple[str, str] | None:
    """(subject, value) for statements that occupy a single-valued slot, else None."""
    key = body_key(text)
    key = re.sub(r"^(?:actually|correction|no|update|remember that|remember|note that)\s+", "", key)
    for pattern, template, group in _SLOTS:
        match = pattern.match(key)
        if match:
            groups = [g.strip() for g in match.groups()]
            subject = template.format(*groups) if "{" in template else template
            return " ".join(subject.split()), groups[group - 1]
    return None


def looks_like_instruction(text: str) -> bool:
    return bool(_INSTRUCTION.search(text))


class MemoryStore:
    """Memory v1 over an existing broker SQLite connection."""

    def __init__(self, db: sqlite3.Connection):
        self.db = db
        with self.db:
            self.db.executescript(
                """
                CREATE TABLE IF NOT EXISTS memory_items(
                    id TEXT PRIMARY KEY,
                    category TEXT NOT NULL CHECK(category IN
                        ('working','episodic','semantic','procedural','profile')),
                    body TEXT NOT NULL,
                    body_key TEXT NOT NULL,
                    subject TEXT NOT NULL DEFAULT '',
                    project_id TEXT NOT NULL DEFAULT '',
                    session_id TEXT NOT NULL DEFAULT '',
                    source TEXT NOT NULL CHECK(source IN ('user','verified','inferred','external')),
                    provenance TEXT NOT NULL DEFAULT '{}',
                    confidence REAL NOT NULL CHECK(confidence >= 0 AND confidence <= 1),
                    status TEXT NOT NULL CHECK(status IN
                        ('active','pending','superseded','deleted','quarantined')),
                    supersedes TEXT,
                    superseded_by TEXT,
                    conflict_with TEXT,
                    created TEXT NOT NULL,
                    updated TEXT NOT NULL,
                    last_used TEXT,
                    use_count INTEGER NOT NULL DEFAULT 0,
                    expires TEXT
                );
                CREATE INDEX IF NOT EXISTS memory_items_lookup
                    ON memory_items(status, category, project_id, subject);
                CREATE INDEX IF NOT EXISTS memory_items_key ON memory_items(body_key);
                """
            )
        try:
            self.db.execute(
                "CREATE VIRTUAL TABLE IF NOT EXISTS memory_items_fts USING fts5("
                "memory_id UNINDEXED, body, tokenize='porter unicode61')"
            )
        except sqlite3.OperationalError as error:  # pragma: no cover - FTS5 ships with CPython
            raise BrokerError(
                "memory_unavailable", "Local full-text search is unavailable.", 503
            ) from error

    # ---------------------------------------------------------------- writes
    def write(
        self,
        text: str,
        *,
        category: str,
        source: str,
        project_id: str = "",
        session_id: str = "",
        provenance: dict[str, Any] | None = None,
        confidence: float | None = None,
    ) -> dict[str, Any]:
        """Gate, dedupe and store one memory. Returns the row plus ``action``."""
        if category not in CATEGORIES or source not in SOURCES:
            raise BrokerError("invalid_request", "Unknown memory category or source.", 400)
        if project_id and not re.fullmatch(r"[a-f0-9]{64}", project_id):
            raise BrokerError("invalid_request", "Invalid project scope.", 400)
        body = normalize(redact(text))[:MAX_BODY]
        if len(body) < 3:
            raise BrokerError("invalid_request", "Memory needs a short statement.", 400)
        if source == "verified" and category != "episodic":
            raise BrokerError("invalid_request", "Verified receipts are episodic memory.", 400)
        default_conf = {"user": 0.95, "verified": 0.9, "inferred": 0.5, "external": 0.3}[source]
        conf = max(0.0, min(1.0, default_conf if confidence is None else float(confidence)))
        if source != "user":
            conf = min(conf, default_conf)  # nobody but the user can claim user-level certainty
        status = "active"
        if source == "external":
            status = "quarantined" if looks_like_instruction(body) else "pending"
        elif source == "inferred" and category in DURABLE:
            status = "pending"
        elif looks_like_instruction(body) and source != "user":
            status = "quarantined"
        key = body_key(body)
        slot = subject_of(body) if category in DURABLE else None
        subject = slot[0] if slot else ""
        stamp = _now()
        expires = (
            (datetime.now(timezone.utc) + WORKING_TTL).isoformat(timespec="seconds")
            if category == "working"
            else None
        )
        prov = json.dumps(provenance or {}, separators=(",", ":"), sort_keys=True)[:2000]

        duplicate = self._duplicate(key, body, category, project_id)
        if duplicate is not None and status == "active":
            with self.db:
                self.db.execute(
                    "UPDATE memory_items SET updated=?, use_count=use_count+1, "
                    "confidence=MAX(confidence, ?) WHERE id=?",
                    (stamp, conf, duplicate["id"]),
                )
            return {**self.get(duplicate["id"]), "action": "duplicate"}

        conflict = self._active_subject(subject, category, project_id) if subject else None
        action = "created"
        supersedes = None
        conflict_with = None
        if conflict is not None and conflict["body_key"] != key:
            if status == "active" and TRUST_RANK[source] >= TRUST_RANK[conflict["source"]]:
                supersedes, action = conflict["id"], "superseded"
            else:
                # Lower-trust contradiction never overrides; it waits for the user.
                status = "pending" if status == "active" else status
                conflict_with, action = conflict["id"], "conflict"
        memory_id = uid()
        with self.db:
            self.db.execute(
                "INSERT INTO memory_items(id,category,body,body_key,subject,project_id,session_id,"
                "source,provenance,confidence,status,supersedes,superseded_by,conflict_with,"
                "created,updated,last_used,use_count,expires) "
                "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,NULL,?,?,?,NULL,0,?)",
                (
                    memory_id,
                    category,
                    body,
                    key,
                    subject,
                    project_id,
                    session_id,
                    source,
                    prov,
                    conf,
                    status,
                    supersedes,
                    conflict_with,
                    stamp,
                    stamp,
                    expires,
                ),
            )
            if status == "active":
                self._index(memory_id, body, subject, category)
            if supersedes:
                self._retire(supersedes, "superseded", memory_id)
        if status == "quarantined":
            action = "quarantined"
        elif status == "pending" and action == "created":
            action = "pending"
        return {**self.get(memory_id), "action": action}

    def confirm(self, memory_id: str) -> dict[str, Any]:
        """The user confirms a pending item: it becomes user-sourced and active."""
        item = self.get(memory_id)
        if item["status"] not in {"pending", "quarantined"}:
            raise BrokerError("invalid_request", "Only pending memory can be confirmed.", 400)
        provenance = {**item["provenance"], "confirmed_from": item["source"]}
        with self.db:
            self.db.execute("DELETE FROM memory_items WHERE id=?", (memory_id,))
        result = self.write(
            item["body"],
            category=item["category"],
            source="user",
            project_id=item["project_id"],
            session_id=item["session_id"],
            provenance=provenance,
        )
        return result

    def correct(self, memory_id: str, text: str) -> dict[str, Any]:
        item = self.get(memory_id)
        if item["status"] != "active":
            raise BrokerError("not_found", "That memory is no longer active.", 404)
        if body_key(text) == item["body_key"]:
            return {**item, "action": "unchanged"}
        replacement = self.write(
            text,
            category=item["category"],
            source="user",
            project_id=item["project_id"],
            session_id=item["session_id"],
            provenance={"corrects": memory_id, **item["provenance"]},
        )
        if replacement["id"] != memory_id and self.get(memory_id)["status"] == "active":
            with self.db:
                self._retire(memory_id, "superseded", replacement["id"])
                self.db.execute(
                    "UPDATE memory_items SET supersedes=? WHERE id=? AND supersedes IS NULL",
                    (memory_id, replacement["id"]),
                )
        return {**self.get(replacement["id"]), "action": "corrected"}

    def delete(self, memory_id: str) -> dict[str, Any]:
        """Remove the content (tombstone keeps only id, category and timestamps)."""
        item = self.get(memory_id)
        with self.db:
            self.db.execute("DELETE FROM memory_items_fts WHERE memory_id=?", (memory_id,))
            self.db.execute(
                "UPDATE memory_items SET status='deleted', body='', body_key='', subject='', "
                "provenance='{}', updated=? WHERE id=?",
                (_now(), memory_id),
            )
        # The caller also excludes the provenance task from legacy recall (task notes, FTS,
        # history) so the deleted content cannot come back through another path.
        return {
            "id": memory_id,
            "category": item["category"],
            "status": "deleted",
            "task_id": str(item["provenance"].get("task_id", "")),
            "session_id": item["session_id"],
        }

    def delete_by_task(self, task_id: str) -> list[str]:
        """Delete every active/pending item derived from one task (episodic receipts too)."""
        if not re.fullmatch(r"[A-Za-z0-9-]{8,64}", task_id):
            return []
        rows = self.db.execute(
            "SELECT id FROM memory_items WHERE status NOT IN ('deleted') AND provenance LIKE ?",
            (f'%"task_id":"{task_id}"%',),
        ).fetchall()
        return [self.delete(str(row["id"]))["id"] for row in rows]

    def forget_matching(self, text: str, project_id: str = "") -> list[dict[str, Any]]:
        """'Forget my X' → delete active items in that slot (or exact text)."""
        slot = subject_of(text)
        rows = []
        if slot:
            rows = self.db.execute(
                "SELECT id FROM memory_items WHERE status IN ('active','pending') AND subject=? "
                "AND project_id IN ('',?)",
                (slot[0], project_id),
            ).fetchall()
        if not rows:
            hits = self.search(text, project_id=project_id, limit=1, touch=False)
            rows = [{"id": hits[0]["id"]}] if hits and hits[0]["score"] > 0.5 else []
        return [self.delete(str(row["id"])) for row in rows]

    # ---------------------------------------------------------------- reads
    def get(self, memory_id: str) -> dict[str, Any]:
        row = self.db.execute("SELECT * FROM memory_items WHERE id=?", (memory_id,)).fetchone()
        if row is None:
            raise BrokerError("not_found", "Memory not found.", 404)
        item = dict(row)
        item["provenance"] = json.loads(item["provenance"] or "{}")
        return item

    def list(
        self, *, status: str | None = None, category: str | None = None, limit: int = 200
    ) -> list[dict[str, Any]]:
        sql, args = "SELECT * FROM memory_items WHERE 1=1", []
        if status:
            sql, args = sql + " AND status=?", [*args, status]
        if category:
            sql, args = sql + " AND category=?", [*args, category]
        rows = self.db.execute(sql + " ORDER BY updated DESC LIMIT ?", (*args, limit)).fetchall()
        return [{**dict(r), "provenance": json.loads(r["provenance"] or "{}")} for r in rows]

    def search(
        self,
        query: str,
        *,
        project_id: str = "",
        session_id: str = "",
        categories: tuple[str, ...] | None = None,
        limit: int = 5,
        touch: bool = True,
    ) -> list[dict[str, Any]]:
        terms = sorted(tokens(query))[:12]
        if not terms:
            return []
        match = " OR ".join(f'"{t}"' for t in terms)
        try:
            rows = self.db.execute(
                "SELECT m.*, bm25(memory_items_fts) AS rank FROM memory_items_fts f "
                "JOIN memory_items m ON m.id=f.memory_id WHERE memory_items_fts MATCH ? "
                "AND m.status='active' ORDER BY rank LIMIT 64",
                (match,),
            ).fetchall()
        except sqlite3.OperationalError:
            return []
        now = datetime.now(timezone.utc)
        query_tokens = set(terms)
        scored = []
        for row in rows:
            item = dict(row)
            if item["project_id"] and item["project_id"] != project_id:
                continue  # another project's memory never leaks into this one
            if item["category"] == "working" and (
                item["session_id"] != session_id
                or (item["expires"] and datetime.fromisoformat(item["expires"]) < now)
            ):
                continue
            if categories and item["category"] not in categories:
                continue
            lexical = 1.0 / (1.0 + math.exp(item["rank"] + 2.0))  # bm25 is negative-better
            overlap = len(tokens(item["body"]) & query_tokens) / max(1, len(query_tokens))
            age_days = max(
                0.0,
                (
                    now - datetime.fromisoformat(item["updated"].replace("Z", "+00:00"))
                ).total_seconds()
                / 86400,
            )
            recency = math.exp(-age_days / 90)
            score = (
                0.45 * lexical
                + 0.35 * overlap
                + 0.08 * recency
                + 0.07 * item["confidence"]
                + 0.05 * CATEGORY_WEIGHT[item["category"]]
            )
            if project_id and item["project_id"] == project_id:
                score += 0.05
            item["score"] = round(score, 4)
            item["provenance"] = json.loads(item.pop("provenance") or "{}")
            item.pop("rank", None)
            scored.append(item)
        scored.sort(key=lambda i: i["score"], reverse=True)
        chosen = scored[:limit]
        if touch and chosen:
            with self.db:
                self.db.executemany(
                    "UPDATE memory_items SET last_used=?, use_count=use_count+1 WHERE id=?",
                    [(_now(), item["id"]) for item in chosen],
                )
        return chosen

    def context_block(
        self, query: str, *, project_id: str = "", session_id: str = "", limit_chars: int = 900
    ) -> str:
        """Prompt block of recalled memory, always labelled as data."""
        lines, used = [], 0
        for item in self.search(query, project_id=project_id, session_id=session_id, limit=8):
            line = f"[{item['category']}|{item['source']}|{item['confidence']:.2f}] {item['body']}"
            if used + len(line) > limit_chars:
                break
            lines.append(line)
            used += len(line) + 1
        return "\n".join(lines)

    def stats(self) -> dict[str, Any]:
        rows = self.db.execute(
            "SELECT category, status, COUNT(*) AS n FROM memory_items GROUP BY category, status"
        ).fetchall()
        return {f"{r['category']}.{r['status']}": r["n"] for r in rows}

    # ---------------------------------------------------------------- user turns
    def capture_user_turn(
        self, text: str, *, project_id: str = "", session_id: str = "", task_id: str = ""
    ) -> list[dict[str, Any]]:
        """Remember what the user explicitly states about themselves; act on 'forget'."""
        clean = re.sub(
            r"^(?:actually|correction|update|oh and|also|btw|no)[,:]?\s+",
            "",
            normalize(text),
            flags=re.I,
        )
        lowered = clean.casefold()
        prov = {"task_id": task_id, "via": "chat"} if task_id else {"via": "chat"}
        forget = re.match(r"^(?:please )?forget (?:that |about )?(.+)$", lowered)
        if forget:
            return [
                {**gone, "action": "deleted"}
                for gone in self.forget_matching(forget.group(1), project_id)
            ]
        remember = re.match(
            r"^(?:please )?(?:remember|note|keep in mind)(?: that)?[,:]? (.+)$", clean, re.I
        )
        statement = remember.group(1) if remember else clean
        directive = re.match(
            r"^(?:always|never|from now on|whenever|before|after)\b", statement, re.I
        )
        if not remember and not directive and subject_of(statement) is None:
            return []
        if "?" in statement or len(statement) > 300:
            return []
        lowered_statement = statement.casefold()
        if re.match(
            r"^(?:always|never|when|whenever|from now on|before|after|first)\b", lowered_statement
        ):
            category = "procedural"
        elif re.match(
            r"^(?:my name|call me|i (?:prefer|like|want|live|work|am))", lowered_statement
        ):
            category = "profile"
        else:
            category = "semantic"
        scoped = (
            project_id
            if category in {"semantic", "procedural"}
            and re.search(r"\b(?:this|the) (?:project|repo)\b", lowered_statement)
            else ""
        )
        return [
            self.write(
                statement,
                category=category,
                source="user",
                project_id=scoped,
                session_id=session_id,
                provenance=prov,
            )
        ]

    # ---------------------------------------------------------------- helpers
    def _duplicate(
        self, key: str, body: str, category: str, project_id: str
    ) -> dict[str, Any] | None:
        row = self.db.execute(
            "SELECT * FROM memory_items WHERE status='active' AND body_key=? AND category=? "
            "AND project_id=?",
            (key, category, project_id),
        ).fetchone()
        if row is not None:
            return dict(row)
        mine = tokens(body)
        if len(mine) < 3:
            return None
        for row in self.db.execute(
            "SELECT * FROM memory_items WHERE status='active' AND category=? AND project_id=? "
            "ORDER BY updated DESC LIMIT 200",
            (category, project_id),
        ):
            theirs = tokens(row["body"])
            if theirs and len(mine & theirs) / len(mine | theirs) >= 0.85:
                if (
                    subject_of(body)
                    and subject_of(row["body"])
                    and subject_of(body)[1] != subject_of(row["body"])[1]
                ):
                    continue  # same words, different value: a contradiction, not a duplicate
                return dict(row)
        return None

    def _active_subject(
        self, subject: str, category: str, project_id: str
    ) -> dict[str, Any] | None:
        row = self.db.execute(
            "SELECT * FROM memory_items WHERE status='active' AND subject=? AND project_id=? "
            "AND category IN ('semantic','procedural','profile') ORDER BY updated DESC LIMIT 1",
            (subject, project_id),
        ).fetchone()
        return dict(row) if row is not None else None

    def _index(self, memory_id: str, body: str, subject: str, category: str) -> None:
        # The slot subject ("name", "preference for editors") is indexed with the body so a
        # question about the slot finds the statement even without shared words.
        self.db.execute(
            "INSERT INTO memory_items_fts(memory_id, body) VALUES(?,?)",
            (memory_id, " ".join(filter(None, [body, subject, category]))),
        )

    def _retire(self, memory_id: str, status: str, successor: str) -> None:
        self.db.execute("DELETE FROM memory_items_fts WHERE memory_id=?", (memory_id,))
        self.db.execute(
            "UPDATE memory_items SET status=?, superseded_by=?, updated=? WHERE id=?",
            (status, successor, _now(), memory_id),
        )

    def import_confirmed_facts(self) -> int:
        """One-time, idempotent import of legacy user-confirmed facts (same database)."""
        try:
            rows = self.db.execute(
                "SELECT id, scope, project_id, kind, body FROM confirmed_facts WHERE status='active'"
            ).fetchall()
        except sqlite3.OperationalError:
            return 0
        imported = 0
        for row in rows:
            seen = self.db.execute(
                "SELECT 1 FROM memory_items WHERE provenance LIKE ?",
                (f'%"legacy_fact":"{row["id"]}"%',),
            ).fetchone()
            if seen:
                continue
            category = "profile" if row["kind"] == "preference" else "semantic"
            self.write(
                row["body"],
                category=category,
                source="user",
                project_id=row["project_id"] if row["scope"] == "project" else "",
                provenance={"legacy_fact": row["id"]},
            )
            imported += 1
        return imported


def elapsed_ms(started: float) -> float:
    return round((time.perf_counter() - started) * 1000, 3)
