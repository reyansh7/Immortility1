"""Run-scoped authorization for the shared warm Hermes gateway (M2/P1).

The warm 0.23.2+ gateway authenticates to the broker with one long-lived key, so a key
alone cannot tell which Hermes run a request belongs to. Without more, a stale run (for
example one left over from a cancelled task) could reach the next task's inference grant.

Each broker turn therefore gets a fresh, unguessable binding. The broker passes it to
Hermes as the run's ephemeral ``instructions``; Hermes appends those to the system prompt
at API-call time on every model request of that run (``agent/turn_context.py``), so each
request that reaches ``/inference/v1/chat/completions`` carries the binding of the run that
produced it. The broker:

* refuses a warm-key request whose binding is missing or differs from the active task's
  current binding (``run_binding_mismatch``), and
* strips the marker before anything is forwarded to a provider or the simulated fixture,
  so it never leaves the PC and never reaches a model.

Tool execution over the warm key is additionally bound to proposals the broker itself
relayed and authorized in the current run (see ``app.agent_tool``).

The binding is a correlation capability, not a secret against Hermes: Hermes is a trusted,
broker-supervised child. Its purpose is to make cross-run reuse of a grant impossible.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import re
import secrets
from typing import Any

MARKER_PREFIX = "[immortility-run-binding:"
_MARKER = re.compile(r"\s*\[immortility-run-binding:([A-Za-z0-9_-]{16,64})\]\s*")


def new_secret() -> bytes:
    return secrets.token_bytes(32)


def new_binding() -> str:
    return secrets.token_urlsafe(18)


def task_binding(secret: bytes, task_id: str) -> str:
    """Stable for one task within one broker process, unguessable across tasks.

    Stability keeps Hermes' Idempotency-Key replay of the *same* task's run working (the
    run body must not change between retries); a different task always gets a different
    binding, and a broker restart (new secret) invalidates every earlier run's binding.
    """
    digest = hmac.new(secret, task_id.encode(), hashlib.sha256).digest()
    return base64.urlsafe_b64encode(digest[:18]).decode().rstrip("=")


def marker(binding: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9_-]{16,64}", binding):
        raise ValueError("invalid run binding")
    return f"{MARKER_PREFIX}{binding}]"


def _strip_text(text: str, found: set[str]) -> str:
    def take(match: re.Match[str]) -> str:
        found.add(match.group(1))
        return "\n\n" if match.start() and match.end() < len(text) else ""

    return _MARKER.sub(take, text)


def extract_and_strip(body: Any) -> set[str]:
    """Remove every binding marker from system/developer messages in place.

    Returns the set of bindings found. Markers in user, assistant or tool content are
    also removed (and reported), so model-visible text can never smuggle one through.
    """
    found: set[str] = set()
    if not isinstance(body, dict):
        return found
    messages = body.get("messages")
    if not isinstance(messages, list):
        return found
    for message in messages:
        if not isinstance(message, dict):
            continue
        content = message.get("content")
        if isinstance(content, str) and MARKER_PREFIX in content:
            message["content"] = _strip_text(content, found)
        elif isinstance(content, list):
            for part in content:
                if (
                    isinstance(part, dict)
                    and isinstance(part.get("text"), str)
                    and MARKER_PREFIX in part["text"]
                ):
                    part["text"] = _strip_text(part["text"], found)
    return found


def verdict(found: set[str], expected: str | None) -> str:
    """``ok`` only when exactly the active run's binding is present."""
    if expected is None:
        return "no_active_binding"
    if not found:
        return "missing"
    if found != {expected}:
        return "mismatch"
    return "ok"
