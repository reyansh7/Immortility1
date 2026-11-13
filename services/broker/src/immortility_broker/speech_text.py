"""User-facing assistant text to speech segments.

Code fences and Markdown markers are removed so they are not narrated.
This module never sees tool payloads, credentials, or hidden reasoning.
"""

import re

_FENCE = re.compile(r"```.*?```", re.DOTALL)
_LINK = re.compile(r"\[([^\]]+)\]\([^)]+\)")
_MARK = re.compile(r"[#>*_~]+")
_SPACE = re.compile(r"\s+")
_END = re.compile(r"[.!?]$")


def for_speech(text: str) -> str:
    cleaned = _FENCE.sub(" ", text)
    cleaned = _LINK.sub(r"\1", cleaned)
    cleaned = cleaned.replace("`", "")
    cleaned = _MARK.sub("", cleaned)
    return _SPACE.sub(" ", cleaned).strip()[:4000]


def ready_sentences(text: str, spoken: int, final: bool) -> tuple[list[str], int]:
    """Return sentences that are safe to synthesize, plus the new spoken count."""
    clean = for_speech(text)
    if not clean:
        return [], spoken
    parts = [part.strip() for part in re.split(r"(?<=[.!?])\s+", clean) if part.strip()]
    if not final and not _END.search(clean):
        parts = parts[:-1]
    fresh = parts[spoken:]
    return fresh, spoken + len(fresh)
