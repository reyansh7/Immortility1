from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[4]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT / ".env", extra="ignore")
    allow_paid_inference: Literal[False] = False
    monthly_paid_budget_usd: Literal[0] = 0
    # Deployment policy may lower a route's call budget, never increase it.
    model_call_cap: int = Field(default=6, ge=1, le=6)
    # Optional fallback only; a stored key never opts the user in.
    openrouter_fallback_enabled: bool = False
    openrouter_api_key: SecretStr = SecretStr("")
    gemini_api_key: SecretStr = SecretStr("")
    groq_api_key: SecretStr = SecretStr("")
    nvidia_api_key: SecretStr = SecretStr("")
    hermes_source: Path = Path.home() / "AppData/Local/hermes/hermes-agent"
    # Off until the 0.23.2 gateway passes the live tool-selection gate.
    hermes_0232_gateway: bool = False
    # Which reviewed gateway pin to run. Only the canary flag file may select a candidate pin,
    # and only inside a canary-* data directory (see hermes_gateway.GATEWAY_PINS).
    hermes_gateway_version: str = "0.23.2"
    # Environment cannot enable this. Only the canary file, applied after load, may.
    simulated_inference: bool = False
    # A reviewed, tested release. Never silently follow upstream main.
    hermes_revision: str = "04b88a4c"
    data_dir: Path = ROOT / "data/dev"
    credential_source: str = "local environment"
    # Off until the isolated runtime's security and native verification gates are resolved.
    experimental_qwen_tts: Literal[False] = False
    infernal_voice_enabled: bool = False
    reference_voice_enabled: bool = False
    # Specialists stay off until the user turns them on. Side-effect tools stay disabled.
    delegation_enabled: bool = False
    local_tools_enabled: bool = False
    # Read-only profile scan and File Explorer reveal. Deletion stays off.
    laptop_tools_enabled: bool = False
    workspace_tools_enabled: bool = False
    project_read_enabled: bool = False
    workspace_root: Path | None = None
    # Public web research is off until the user enables the allowlisted fetcher.
    web_research_enabled: bool = False
    # Local arithmetic MCP server is off until the user enables it.
    mcp_enabled: bool = False
    # Separate standard SDK gate; never inferred from the legacy demo checkbox.
    standard_mcp_enabled: bool = False
    artifact_tools_enabled: bool = False
    # Experimental provider schema export; native MCP identity/grants are unchanged.
    typed_tool_schemas_enabled: bool = False
    # Gateway path only: one locally answered warm-up run after readiness (K7).
    gateway_warmup_enabled: bool = True
    # No autorun/service install. Only explicit, local read workflows may recover.
    durable_workflows_enabled: bool = False
    local_only_mode: bool = False
    # Cannot be turned on by environment. No verified Windows isolation boundary.
    code_execution_enabled: Literal[False] = False
    origins: tuple[str, ...] = (
        "http://localhost:1420",
        "http://127.0.0.1:1420",
        "http://tauri.localhost",
        "https://tauri.localhost",
        "tauri://localhost",
    )

    @field_validator("allow_paid_inference", mode="before")
    @classmethod
    def parse_free_lock(cls, value: object) -> object:
        return False if isinstance(value, str) and value.lower() == "false" else value

    @field_validator("code_execution_enabled", "experimental_qwen_tts", mode="before")
    @classmethod
    def execution_stays_off(cls, value: object) -> object:
        del value
        return False

    @field_validator("simulated_inference", mode="before")
    @classmethod
    def simulated_stays_off(cls, value: object) -> object:
        del value
        return False

    @field_validator("monthly_paid_budget_usd", mode="before")
    @classmethod
    def parse_zero_budget(cls, value: object) -> object:
        return 0 if value == "0" else value

    def load_credentials(self) -> None:
        from .secrets import CredentialError, CredentialManager

        loaded = False
        for provider, field in (
            ("openrouter", "openrouter_api_key"),
            ("gemini", "gemini_api_key"),
            ("groq", "groq_api_key"),
            ("nvidia", "nvidia_api_key"),
        ):
            try:
                value = CredentialManager(provider=provider).read()
            except CredentialError:
                value = None
            if value:
                setattr(self, field, SecretStr(value))
                loaded = True
        if loaded:
            self.credential_source = "Windows Credential Manager"
