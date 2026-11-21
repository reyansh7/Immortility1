"""Fail-closed reading of config/permissions.default.yaml. Unknown actions are denied."""

from pathlib import Path

from .config import ROOT

_HARD_DENY = ("shell", "computer", "browser", "yolo", "mcp.install")
_ACTIONS = {
    "arithmetic.add.v1": "local_arithmetic",
    "arithmetic.multiply.v1": "local_arithmetic",
    "clock.now.v1": "local_clock",
    "public.research.v1": "browse_public_web",
    "report.create.v1": "write_approved_workspace",
    "project.outline.v1": "read_permitted_files",
    "project.search.v1": "read_permitted_files",
    "project.read.v1": "read_permitted_files",
    "laptop.storage.v1": "read_permitted_files",
    "laptop.resources.v1": "local_resources",
    "desktop.reveal.v1": "reveal_authorized_path",
    "pointer.move.v1": "move_pointer",
}


def _items(value: str) -> frozenset[str]:
    text = value.strip()
    if not (text.startswith("[") and text.endswith("]")):
        raise ValueError("policy list")
    return frozenset(part.strip() for part in text[1:-1].split(",") if part.strip())


def load_policy(path: Path | None = None) -> dict[str, object]:
    source = path or (ROOT / "config" / "permissions.default.yaml")
    default = ""
    profiles: dict[str, dict[str, frozenset[str]]] = {}
    approval: frozenset[str] = frozenset()
    section = ""
    profile = ""
    for raw in source.read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        if line.startswith("  ") and not line.startswith("    ") and line.strip().endswith(":"):
            profile = line.strip()[:-1]
            profiles[profile] = {"allow": frozenset(), "require_approval": frozenset()}
            section = "profile"
            continue
        if line.startswith("global:"):
            section = "global"
            profile = ""
            continue
        if line.startswith("default:"):
            default = line.split(":", 1)[1].strip()
            continue
        if ":" not in line:
            raise ValueError("policy line")
        key, value = (part.strip() for part in line.split(":", 1))
        if section == "profile" and key in {"allow", "require_approval"}:
            profiles[profile][key] = _items(value)
        elif section == "global" and key == "deny_without_fresh_approval":
            approval = _items(value)
    if default != "deny" or not profiles:
        raise ValueError("policy must default to deny")
    return {"default": default, "profiles": profiles, "approval": approval}


def decide(policy: dict[str, object], profile: str, action: str) -> str:
    if policy.get("default") != "deny" or not action:
        return "deny"
    approval = policy.get("approval")
    if isinstance(approval, frozenset) and action in approval:
        return "approval"
    profiles = policy.get("profiles")
    if not isinstance(profiles, dict):
        return "deny"
    rules = profiles.get(profile)
    if not isinstance(rules, dict):
        return "deny"
    if action in rules.get("allow", frozenset()):
        return "allow"
    if action in rules.get("require_approval", frozenset()):
        return "approval"
    return "deny"


def govern(capability: str, profile: str, policy: dict[str, object] | None = None) -> str:
    folded = capability.casefold()
    if any(token in folded for token in _HARD_DENY):
        return "deny"
    action = _ACTIONS.get(capability)
    if action is None:
        return "deny"
    try:
        loaded = policy if policy is not None else load_policy()
    except (OSError, ValueError):
        return "deny"
    return decide(loaded, profile, action)
