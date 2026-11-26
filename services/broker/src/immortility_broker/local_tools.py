"""One local read-only tool. Terminal, files, browser, and MCP stay unauthorized."""

import json
from datetime import datetime, timezone
from typing import Any

from .contracts import BrokerError

AUTHORIZED = frozenset({"clock"})


def apply_local_tools_file(settings: Any) -> None:
    path = settings.data_dir / "local-tools.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeError):
        return
    if isinstance(data, dict) and isinstance(data.get("enabled"), bool):
        settings.local_tools_enabled = data["enabled"]


def save_local_tools_file(settings: Any, enabled: bool) -> None:
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    (settings.data_dir / "local-tools.json").write_text(
        json.dumps({"enabled": enabled}) + "\n", encoding="utf-8"
    )
    settings.local_tools_enabled = enabled


def _zone_label(moment: datetime) -> str:
    """'IST, UTC+05:30'. Windows names zones in words ('India Standard Time') → initials."""
    name = moment.tzname() or ""
    if " " in name:
        name = "".join(word[0] for word in name.split() if word[:1].isalpha()).upper()
    offset = moment.strftime("%z")
    offset = f"UTC{offset[:3]}:{offset[3:]}" if offset else "UTC"
    return f"{name}, {offset}" if name and not name.startswith(("UTC", "+", "-")) else offset


def clock_reading(now: datetime | None = None) -> dict[str, str]:
    """K23: the clock answers in the PC's local time with an explicit offset, plus a ready
    display string, so a small model never has to convert from UTC itself."""
    moment = (now or datetime.now(timezone.utc)).astimezone()
    hour = moment.strftime("%I").lstrip("0") or "12"
    display = (
        f"{hour}:{moment.strftime('%M %p')} on {moment.strftime('%A')} "
        f"{moment.day} {moment.strftime('%B %Y')} ({_zone_label(moment)})"
    )
    return {
        "timestamp": moment.isoformat(timespec="seconds"),
        "utc": moment.astimezone(timezone.utc).isoformat(timespec="seconds"),
        "local": display,
    }


def call_local_tool(name: str, enabled: bool) -> dict[str, str]:
    if not enabled or name not in AUTHORIZED:
        raise BrokerError("tool_denied", "That tool is not authorized.", 403)
    if name == "clock":
        return {"name": "clock", "result": datetime.now(timezone.utc).isoformat()}
    raise BrokerError("tool_denied", "That tool is not authorized.", 403)
