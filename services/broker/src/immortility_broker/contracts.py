import json
from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from jsonschema import Draft202012Validator, FormatChecker
from pydantic import BaseModel, ConfigDict, Field, field_validator

from .config import ROOT

TERMINAL = {"succeeded", "failed", "cancelled", "blocked", "rate_limited", "disconnected"}


def uid() -> str:
    return str(uuid4())


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


VALIDATORS = {
    path.name.removesuffix(".schema.json"): Draft202012Validator(
        json.loads(path.read_text()), format_checker=FormatChecker()
    )
    for path in (ROOT / "packages/contracts/schemas").glob("*.json")
}


def validate(name: str, value: dict[str, Any]) -> None:
    VALIDATORS[name].validate(value)


class TaskRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    schema_version: Literal["1.0"] = "1.0"
    session_id: str = Field(min_length=1, max_length=64)
    request_id: str = Field(min_length=1, max_length=64)
    content: str = Field(min_length=1, max_length=16000)
    privacy_class: Literal["public", "personal"] = "personal"
    cloud_consent: Literal[True]
    source: Literal["text", "voice"] = "text"
    response_length: Literal["brief", "normal", "detailed"] = "normal"

    @field_validator("cloud_consent", mode="before")
    @classmethod
    def explicit_cloud_consent(cls, value: object) -> object:
        if value is not True:
            raise ValueError("Explicit cloud consent is required.")
        return value


class BrokerError(Exception):
    def __init__(self, code: str, message: str, status: int = 409):
        self.code, self.message, self.status = code, message, status
        super().__init__(code)
