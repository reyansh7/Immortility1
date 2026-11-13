"""Read-only P0 inventory. Does not read user memories/jobs, pair accounts or run agent tools."""

import argparse
import json
import os
import sys
from importlib.metadata import version
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services/broker/src"))


def audit(openmausbot: Path | None) -> dict:
    from immortility_broker.config import Settings
    from immortility_broker.hermes import isolated_config, runtime_check
    settings = Settings(
        _env_file=None,
        openrouter_api_key="",
        gemini_api_key="",
        groq_api_key="",
        nvidia_api_key="",
    )
    hermes = runtime_check(settings)
    source = settings.hermes_source
    present = {
        "tui_gateway": "tui_gateway/entry.py",
        "acp": "acp_adapter",
        "http_api": "gateway/platforms/api_server.py",
        "memory_providers": "agent/memory_manager.py",
        "scheduler": "cron/scheduler.py",
        "skills": "tools/skills_tool.py",
        "delegation": "tools/delegate_tool.py",
        "mcp": "tools/mcp_tool.py",
        "computer_use": "tools/computer_use_tool.py",
    }
    capabilities = {name: (source / path).exists() for name, path in present.items()}
    restrictions = {}
    if hermes["status"] == "available":
        config = isolated_config(source, "http://127.0.0.1:1", "audit-only-not-a-credential")
        restrictions = {
            "memory_enabled": config["memory"]["enabled"],
            "mcp_servers": len(config["mcp_servers"]),
            "plugins": len(config["plugins"]),
            "hooks": len(config["hooks"]),
            "disabled_toolsets": len(config["agent"]["disabled_toolsets"]),
            "lazy_installs": config["security"]["allow_lazy_installs"],
        }
    local = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData/Local"))
    install = openmausbot or local / "Programs/OpenMausBot"
    desktop = install / "OpenMausBot.exe"
    mcp = install / "resources/server/mcp-server.js"
    metadata = install / "resources/package.json"
    omb = {
        "installed_executable": desktop.is_file(),
        "packaged_mcp": mcp.is_file(),
        "status": "BLOCKED: not installed"
        if not desktop.is_file()
        else "IMPLEMENTED: installation present; unverified",
        "enabled_in_immortility": False,
        "version": None,
        "pairing_performed": False,
    }
    if metadata.is_file():
        omb["version"] = json.loads(metadata.read_text()).get("version")
    packages = {
        name: version(name)
        for name in [
            "fastapi",
            "pydantic",
            "httpx",
            "faster-whisper",
            "piper-tts",
            "sounddevice",
            "av",
        ]
    }
    qwen = ROOT / ".venv-tts/pyvenv.cfg"
    return {
        "schema_version": "1.0",
        "hermes": hermes,
        "hermes_source_capabilities_present": capabilities,
        "hermes_session_restrictions": restrictions,
        "openmausbot": omb,
        "broker_packages": packages,
        "qwen_environment_present": qwen.is_file(),
        "owners": {
            "intelligence": "Hermes",
            "permissions_and_task_lifecycle": "Immortility broker",
            "conversation_history": "Existing broker SQLite store",
            "long_term_memory": "Not enabled; existing external stores untouched",
            "scheduler": "Not enabled by Immortility; external schedules untouched",
            "active_computer_controller": "None enabled",
            "specialist_teams": "OpenMausBot candidate; not adopted",
        },
        "new_integrations_activated": [],
        "private_content_read": False,
        "note": "Source capability presence is not proof that its privileged execution passes broker policy. No native tools are enabled by this audit.",
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--openmausbot-root", type=Path)
    args = parser.parse_args()
    result = audit(args.openmausbot_root)
    path = ROOT / "data/audits/runtime.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
