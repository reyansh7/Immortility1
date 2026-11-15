"""Retrieval over local notes and succeeded tasks. This is the broker store, not a second engine."""

from typing import Any


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
