"""Hermes v0.21.1 stdio JSON-RPC adapter. No custom agent loop or internal AIAgent imports."""

import ast
import asyncio
import contextlib
import json
import os
import subprocess
import tempfile
import tomllib
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

from .config import Settings
from .contracts import BrokerError
from .policy import MODEL

REVIEWED_VERSION = "0.21.1"
REVIEWED_REVISION = "04b88a4c0a7fe05ebe3bf053a103a39fe6638f11"


def toolsets(source: Path) -> list[str]:
    tree = ast.parse((source / "toolsets.py").read_text(encoding="utf-8"))
    for node in tree.body:
        if (
            isinstance(node, ast.Assign)
            and any(isinstance(t, ast.Name) and t.id == "TOOLSETS" for t in node.targets)
            and isinstance(node.value, ast.Dict)
        ):
            names = [key.value for key in node.value.keys if isinstance(key, ast.Constant)]
            if names and all(isinstance(n, str) for n in names):
                return names
    raise BrokerError("hermes_incompatible", "Cannot verify Hermes toolset catalog.")


def runtime_check(settings: Settings) -> dict[str, str]:
    source = settings.hermes_source
    python = source / "venv/Scripts/python.exe"
    if not python.is_file() or not (source / "tui_gateway/entry.py").is_file():
        return {
            "status": "missing",
            "message": "Set HERMES_SOURCE to a reviewed Hermes source install.",
        }
    try:
        revision = subprocess.check_output(
            ["git", "-C", str(source), "rev-parse", "HEAD"],
            text=True,
            timeout=5,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            stderr=subprocess.DEVNULL,
        ).strip()
        if revision != REVIEWED_REVISION or settings.hermes_revision not in {
            REVIEWED_REVISION,
            REVIEWED_REVISION[:8],
        }:
            return {
                "status": "incompatible",
                "message": "Hermes revision differs from reviewed pin.",
            }
        version = tomllib.loads((source / "pyproject.toml").read_text(encoding="utf-8"))["project"][
            "version"
        ]
        if version != REVIEWED_VERSION:
            raise BrokerError(
                "hermes_incompatible", "Hermes package version differs from the reviewed release."
            )
        subprocess.run(
            ["git", "-C", str(source), "diff", "--quiet", "HEAD"],
            check=True,
            timeout=5,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        toolsets(source)
    except (OSError, subprocess.SubprocessError, BrokerError, ValueError, KeyError, SyntaxError):
        return {"status": "incompatible", "message": "Hermes compatibility check failed."}
    return {"status": "available", "version": version, "revision": revision}


ROLE_PROMPTS = {
    "research": "You are Immortility's research specialist. No tools, web, or files are available. Use only the prompt and say what is uncertain.",
    "coding": "You are Immortility's coding specialist. No terminal or filesystem is available. Propose the change in text. Do not claim files were edited or tests were run.",
    "review": "You are Immortility's review specialist. No tools are available. End with a line that is exactly VERDICT: pass or VERDICT: fail.",
}


def _failure_detail(params: dict[str, Any]) -> str:
    surface = params.get("error_surface")
    code = ""
    if isinstance(surface, dict) and isinstance(surface.get("code"), str):
        code = "".join(ch for ch in surface["code"] if ch.isalnum() or ch in "._-")[:40]
    raw = params.get("error") or params.get("failure_reason") or "error"
    if not isinstance(raw, str):
        raw = "error"
    text = " ".join(raw.split())[:160]
    lowered = text.lower()
    if any(mark in lowered for mark in ("sk-", "bearer ", "api_key", "api-key", "openrouter")):
        text = "provider error"
    return f"{code}: {text}" if code else text


def isolated_config(
    source: Path,
    base_url: str,
    token: str,
    response_length: str = "normal",
    role: str | None = None,
) -> dict[str, Any]:
    companion = (
        "You are Immortility, a concise, warm Windows companion. Be candid about uncertainty. Never claim you performed an action based only on model text. No tools are available in this session. "
        + {
                "brief": "Answer in one or two short conversational sentences unless safety or correctness requires more.",
                "normal": "Use short, clear paragraphs and enough detail to be useful.",
                "detailed": "Explain the reasoning and practical steps thoroughly, without filler.",
            }.get(response_length, "Use concise natural language.")
    )
    return {
        "model": {
            "provider": "custom",
            "default": MODEL,
            "base_url": base_url,
            "api_key": token,
            "api_mode": "chat_completions",
        },
        "agent": {
            "max_turns": 1 if role else 2,
            "disabled_toolsets": toolsets(source),
            "system_prompt": ROLE_PROMPTS.get(role or "", companion),
        },
        "platform_toolsets": {"cli": []},
        "mcp_servers": {},
        "plugins": {},
        "fallback_model": None,
        "fallback_models": [],
        "hooks": {},
        "security": {"allow_lazy_installs": False},
        "auxiliary": {"title_generation": {"enabled": False}},
        "compression": {"enabled": False},
        "memory": {"enabled": False},
        "display": {"streaming": True},
    }


class Hermes:
    def __init__(self, settings: Settings, base_url: str, token: str):
        self.settings, self.base_url, self.token = settings, base_url, token
        self.process: asyncio.subprocess.Process | None = None
        self.counter = 0
        self.session_id: str | None = None
        self.response_length = "normal"

    async def send(self, method: str, params: dict[str, Any]) -> int:
        assert self.process and self.process.stdin
        self.counter += 1
        self.process.stdin.write(
            (
                json.dumps(
                    {"jsonrpc": "2.0", "id": self.counter, "method": method, "params": params}
                )
                + "\n"
            ).encode()
        )
        await self.process.stdin.drain()
        return self.counter

    async def frames(self) -> AsyncIterator[dict[str, Any]]:
        assert self.process and self.process.stdout
        # Free-route first tokens often exceed 25s. The task budget still ends the turn.
        while line := await asyncio.wait_for(self.process.stdout.readline(), 70):
            try:
                frame = json.loads(line)
                if isinstance(frame, dict):
                    yield frame
            except ValueError:
                continue  # upstream occasionally writes non-protocol notices; never forward raw logs
        raise BrokerError("hermes_lost", "Hermes exited before completing the turn.", 503)

    async def run(
        self, content: str, history: list[dict[str, str]], role: str | None = None
    ) -> AsyncIterator[str]:
        # The broker verified this checkout before accepting the native handshake.
        # Do not spawn synchronous Git probes inside an active event loop on Windows.
        self.settings.data_dir.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="hermes-", dir=self.settings.data_dir) as home:
            source = self.settings.hermes_source
            config = isolated_config(
                source, self.base_url, self.token, self.response_length, role
            )
            Path(home, "config.yaml").write_text(json.dumps(config), encoding="utf-8")
            # Explicit environment allowlist. No inherited keys, auth pools, user profile config,
            # plugins, project rules, MCP, HTTP proxies, or paid fallback credentials.
            env = {
                k: v
                for k, v in os.environ.items()
                if k.upper()
                in {
                    "SYSTEMROOT",
                    "WINDIR",
                    "PATH",
                    "TEMP",
                    "TMP",
                    "COMSPEC",
                    "PATHEXT",
                }
            }
            env.update(
                HERMES_HOME=home,
                HERMES_IGNORE_RULES="1",
                HERMES_TUI_SOURCE="tui",
                HERMES_TUI_TOOLSETS="bot_room",
                USERPROFILE=home,
                LOCALAPPDATA=str(Path(home, "AppData/Local")),
                APPDATA=str(Path(home, "AppData/Roaming")),
                OPENAI_BASE_URL=self.base_url,
                OPENAI_API_KEY=self.token,
                PYTHONUTF8="1",
                PYTHONUNBUFFERED="1",
            )
            try:
                self.process = await asyncio.create_subprocess_exec(
                    str(source / "venv/Scripts/python.exe"),
                    "-m",
                    "tui_gateway.entry",
                    cwd=home,
                    env={**env, "PYTHONPATH": str(source)},
                    stdin=asyncio.subprocess.PIPE,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.DEVNULL,
                    limit=2 * 1024 * 1024,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )
                create_id = await self.send(
                    "session.create",
                    {
                        "source": "tui",
                        "messages": history,
                        "model": MODEL,
                        "provider": "custom",
                    },
                )
                sid = None
                submitted = False
                output = ""
                async for frame in self.frames():
                    if "method" in frame and "id" in frame:
                        # No approval, shell, secret, or other server request is accepted.
                        raise BrokerError(
                            "tool_denied", "Hermes requested a disabled capability.", 403
                        )
                    if frame.get("id") == create_id:
                        if frame.get("error"):
                            raise BrokerError("hermes_protocol", "Hermes refused session creation.")
                        sid = frame["result"]["session_id"]
                        self.session_id = sid
                    # Stdio event envelope in the reviewed release.
                    envelope = frame.get("params", {})
                    event = envelope.get("type") if frame.get("method") == "event" else None
                    params = envelope.get("payload", {})
                    if event == "session.info" and not params.get("lazy") and not submitted:
                        if params.get("tools"):
                            raise BrokerError(
                                "tools_enabled", "Hermes tool inventory is not empty; blocked.", 403
                            )
                        if not sid:
                            continue
                        submitted = True
                        await self.send("prompt.submit", {"session_id": sid, "text": content})
                    elif event in {"tool.start", "approval", "tool.generating"}:
                        raise BrokerError(
                            "tool_denied", "Unexpected tool attempt; Hermes stopped.", 403
                        )
                    elif event == "message.delta":
                        delta = params.get("text", "")
                        output += delta
                        if len(output) > 128000:
                            raise BrokerError(
                                "output_limit", "Response exceeded the local output limit."
                            )
                        yield delta
                    elif event == "message.complete":
                        if params.get("status") in {"error", "interrupted"}:
                            raise BrokerError(
                                "hermes_failed",
                                "Hermes could not complete the response: "
                                + _failure_detail(params),
                                503,
                            )
                        text = params.get("text", "")
                        if not output and text:
                            yield text
                        elif text and text != output:
                            raise BrokerError(
                                "stream_mismatch", "Hermes final response did not match its stream."
                            )
                        return
                    elif event == "error" or frame.get("error"):
                        raise BrokerError(
                            "hermes_failed", "Hermes reported a protocol or runtime error.", 503
                        )
            finally:
                await self.stop()

    async def stop(self) -> None:
        if self.process and self.process.returncode is None:
            with contextlib.suppress(OSError, ConnectionError):
                if self.session_id:
                    await self.send("session.interrupt", {"session_id": self.session_id})
                if self.process.stdin:
                    self.process.stdin.close()
            try:
                await asyncio.wait_for(self.process.wait(), 1.5)
            except TimeoutError:
                pass
        if self.process and self.process.returncode is None:
            if os.name == "nt":
                killer = await asyncio.create_subprocess_exec(
                    "taskkill.exe",
                    "/PID",
                    str(self.process.pid),
                    "/T",
                    "/F",
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.DEVNULL,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                )
                await asyncio.wait_for(killer.wait(), 5)
            else:
                self.process.kill()
            await asyncio.wait_for(self.process.wait(), 5)
        self.process = None
        self.session_id = None
