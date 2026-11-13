"""Deterministic execution routing. No extra model call is spent on classification."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Plan:
    mode: str
    roles: tuple[str, ...]
    call_limit: int
    timeout_s: int


_FAST = Plan("fast", (), 2, 90)
_CODE = ("bug", "traceback", "pytest", "refactor", "patch", "repository", "repo")
_RESEARCH = ("compare", "sources", "cite", "documentation", "research")
_REVIEW = ("review", "verify")
_WORKFLOW = ("then run", "after approval", "apply the change", "apply the patch")


def _has(text: str, needles: tuple[str, ...]) -> bool:
    return any(needle in text for needle in needles)


def wants_edit(content: str) -> bool:
    text = content.lower()
    return _has(text, _CODE) or "fix the " in text or "apply the " in text


def classify(content: str) -> Plan:
    """Pick the smallest mode that can answer the request."""
    text = " ".join(content.lower().split())
    code = wants_edit(content)
    research = _has(text, _RESEARCH)
    review = _has(text, _REVIEW)
    workflow = _has(text, _WORKFLOW)
    if not code and not research and not review and not workflow:
        return _FAST
    roles: list[str] = []
    if research:
        roles.append("research")
    if code:
        roles.append("coding")
    if review or (code and research) or workflow:
        roles.append("review")
    if workflow or (code and research):
        return Plan("workflow" if workflow else "deep", tuple(roles), 16, 300)
    if review and code:
        return Plan("deep", tuple(roles), 12, 240)
    return Plan("standard", tuple(roles), 6, 150)
