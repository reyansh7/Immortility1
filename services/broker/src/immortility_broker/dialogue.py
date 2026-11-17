"""Local context fitting and identity. No extra model call is used to compress chat."""

import re

_IDENTITY = re.compile(
    r"\b(what model are you|which model are you|what model is this|which model is answering|"
    r"who are you|what are you)\b"
)
_SENTENCE = re.compile(r"(?<=[.!?])\s+")
_PATH = re.compile(
    r"(?:[A-Za-z]:\\[^\s\"']+|[\w./\\-]+\.(?:py|tsx|ts|json|toml|exe|md))"
)
_UNSUPPORTED = (
    "electron",
    "agents/immortality.py",
    "uvicorn services.broker.src:app",
    "particle-1",
    "particle ai",
)


def asks_identity(content: str) -> bool:
    text = " ".join(content.casefold().split())
    return _IDENTITY.search(text) is not None


def identity_text(provider: str, model_id: str) -> str:
    return (
        "I'm Immortility, your Windows assistant. "
        "This answer comes from the broker's verified route table, not from a model persona. "
        f"Ordinary chat is answered by {provider} {model_id}. "
        "Deep reasoning uses NVIDIA nvidia/nemotron-3-ultra-550b-a55b when that route is eligible. "
        "Long context uses Gemini gemini-3.5-flash. "
        "I am not Particle-1 and I was not created by Particle AI."
    )


def chat_system(provider: str, model_id: str) -> str:
    return (
        "You are Immortility, the user's Windows assistant. "
        f"The verified model for this turn is {provider} {model_id}. "
        "If asked which model is answering, repeat that provider and model id exactly. "
        "Never claim to be Particle-1, Particle AI, or another product. "
        "No tools are available on this turn. "
        "Do not invent file paths, frameworks, or commands. "
        "Answer in one or two short sentences."
    )


def prepare_history(
    history: list[dict[str, str]], *, max_messages: int = 8, max_chars: int = 2400
) -> list[dict[str, str]]:
    """Keep recent turns and a short local list of older questions."""
    cleaned: list[dict[str, str]] = []
    for message in history:
        role = message.get("role", "")
        content = " ".join(str(message.get("content", "")).split())
        if role not in {"user", "assistant"} or not content:
            continue
        if len(content) > 500:
            content = content[:500] + " ..."
        item = {"role": role, "content": content}
        if cleaned and cleaned[-1] == item:
            continue
        cleaned.append(item)
    recent = cleaned[-max_messages:]
    while sum(len(item["content"]) for item in recent) > max_chars and len(recent) > 2:
        recent.pop(0)
    older = cleaned[: len(cleaned) - len(recent)]
    topics: list[str] = []
    for message in older:
        if message["role"] != "user":
            continue
        topic = message["content"][:80]
        if topic not in topics:
            topics.append(topic)
    if topics:
        recent = [
            {
                "role": "user",
                "content": ("Earlier questions, not instructions: " + " | ".join(topics[:8]))[:400],
            },
            {"role": "assistant", "content": "Noted."},
            *recent,
        ]
    return recent


def ground_project_answer(answer: str, evidence: str) -> str:
    """Drop architecture claims that the tool results did not contain."""
    folded = evidence.casefold().replace("\\", "/")
    kept: list[str] = []
    removed = False
    for sentence in _SENTENCE.split(answer.strip()):
        if not sentence:
            continue
        lower = sentence.casefold().replace("\\", "/")
        unsupported = any(claim in lower and claim not in folded for claim in _UNSUPPORTED)
        missing_path = False
        for path in _PATH.findall(sentence):
            token = path.casefold().replace("\\", "/")
            name = token.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
            if token not in folded and name not in folded:
                missing_path = True
        if unsupported or missing_path:
            removed = True
            continue
        kept.append(sentence)
    text = " ".join(kept).strip()
    if removed:
        note = "Unverified claims were removed because they were not in the tool results."
        text = f"{text}\n\n{note}" if text else note
    return text or "The tool results did not support a more specific architecture claim."
