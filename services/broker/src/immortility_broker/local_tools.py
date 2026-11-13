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


def call_local_tool(name: str, enabled: bool) -> dict[str, str]:
    if not enabled or name not in AUTHORIZED:
        raise BrokerError("tool_denied", "That tool is not authorized.", 403)
    if name == "clock":
        return {"name": "clock", "result": datetime.now(timezone.utc).isoformat()}
    raise BrokerError("tool_denied", "That tool is not authorized.", 403)
