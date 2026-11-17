"""Retrieval over local notes and succeeded tasks. This is the broker store, not a second engine."""

import re
from pathlib import Path
from typing import Any

from .contracts import BrokerError

_SECRET = re.compile(
    r"(?i)(?:bearer\s+[A-Za-z0-9._-]{8,})"
    r"|(?:\b(?:sk|ghp|github_pat|nvapi|AIza)[-_][A-Za-z0-9_-]{8,})"
    r"|(?:\b(?:api[_-]?key|token|password|secret)\b\s*[:=]\s*\S+)"
)


def words(text: str) -> set[str]:
    found: set[str] = set()
    token: list[str] = []
    for char in text.lower():
        if char.isalnum():
            token.append(char)
            continue
        if len(token) >= 4:
            found.add("".join(token))
        token.clear()
    if len(token) >= 4:
        found.add("".join(token))
    return found


def retrieve(text: str, query: str, limit: int = 1200) -> str:
    paragraphs = [part.strip() for part in text.splitlines() if part.strip()]
    if not paragraphs:
        return ""
    query_words = words(query)
    if not query_words:
        return paragraphs[0][:limit]
    chosen: list[str] = []
    used = 0
    ranked = sorted(
        paragraphs,
        key=lambda part: len(words(part) & query_words),
        reverse=True,
    )
    for part in ranked:
        if not (words(part) & query_words) or used >= limit:
            continue
        piece = part[: limit - used]
        chosen.append(piece)
        used += len(piece) + 1
    if not chosen:
        return paragraphs[0][:limit]
    return "\n".join(chosen)


def trim_history(history: list[dict[str, str]], max_chars: int = 6000) -> list[dict[str, str]]:
    kept: list[dict[str, str]] = []
    used = 0
    for message in reversed(history):
        content = message.get("content", "")
        role = message.get("role", "")
        if role not in {"user", "assistant"} or not isinstance(content, str):
            continue
        if used and used + len(content) > max_chars:
            break
        if len(content) > max_chars:
            content = content[-max_chars:]
        kept.append({"role": role, "content": content})
        used += len(content)
        if used >= max_chars:
            break
    kept.reverse()
    return kept


def current_project_id(enabled: bool, root: Path | None) -> str:
    if not enabled or root is None:
        return ""
    try:
        from .project_inspection import identity

        return identity(root)
    except (OSError, BrokerError):
        return ""


def redact(text: str) -> str:
    """Remove credential-shaped text before anything is stored or recalled."""
    return _SECRET.sub("[redacted]", text)


def experience_record(
    *,
    request: str,
    provider: str,
    model: str,
    tools: list[str],
    outcome: str,
) -> str:
    """Compact receipt. Model prose is not stored as a verified fact."""
    category = " ".join(re.findall(r"[A-Za-z0-9]{3,}", redact(request))[:8])
    tool_list = ",".join(
        tool for tool in tools if isinstance(tool, str) and re.fullmatch(r"[a-z0-9._]{3,64}", tool)
    )
    if not re.fullmatch(r"[A-Za-z0-9._-]{1,32}", provider):
        provider = "unknown"
    if not re.fullmatch(r"[A-Za-z0-9._:/-]{1,80}", model):
        model = "unknown"
    if outcome not in {"ok", "failed"}:
        outcome = "unknown"
    return (
        f"verified experience category {category} provider {provider} model {model} "
        f"tool {tool_list or 'none'} outcome {outcome}"
    )[:500]


def format_facts(facts: list[dict[str, str]], limit: int = 400) -> str:
    lines: list[str] = []
    used = 0
    for fact in facts:
        if fact.get("trust") != "user-confirmed" or fact.get("status") != "active":
            continue
        line = f"[{fact.get('scope', '')}|{fact.get('kind', '')}] {fact.get('body', '')}"
        if used + len(line) > limit:
            break
        lines.append(line)
        used += len(line) + 1
    return "\n".join(lines)


def prior_task_notes(tasks: list[dict[str, Any]], query: str, skip: str, limit: int = 600) -> str:
    query_words = words(query)
    scored: list[tuple[int, str, str]] = []
    for task in tasks:
        if (
            task.get("task_id") == skip
            or task.get("status") != "succeeded"
            or task.get("recall_excluded")
        ):
            continue
        request = str(task.get("input", {}).get("content", ""))
        overlap = len(words(request) & query_words)
        if query_words and overlap == 0:
            continue
        answer = " ".join(str(task.get("result", {}).get("text", "")).split())
        scored.append((overlap, request[:180], answer[:180]))
    scored.sort(key=lambda item: item[0], reverse=True)
    lines = [f"Q: {request} A: {answer}" for _, request, answer in scored[:3]]
    return "\n".join(lines)[:limit]
