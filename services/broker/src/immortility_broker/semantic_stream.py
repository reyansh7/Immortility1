"""Bounded tool-mode state; transport envelopes and private reasoning are discarded."""

import io
from typing import Any

from .agent_bridge import accepted_tool_prefix, validate_stream
from .contracts import BrokerError


class SemanticToolStream:
    def __init__(self) -> None:
        self.content = io.StringIO()
        self.calls: dict[int, dict[str, Any]] = {}
        self.finish_reason: str | None = None
        self.events = 0
        self.semantic_bytes = 0
        self.argument_bytes = 0
        self.reasoning_events_discarded = 0
        self.metadata: dict[str, Any] = {}

    def _count(self, size: int) -> None:
        self.semantic_bytes += size
        if self.semantic_bytes > 128000:
            self.limit()

    @staticmethod
    def limit() -> None:
        raise BrokerError(
            "provider_stream_failed",
            "Provider semantic output exceeds its bound.",
            503,
            diagnostic="bridge_output_limit",
        )

    def add(self, chunk: Any) -> None:
        self.events += 1
        if self.events > 32768:
            self.limit()
        try:
            if (
                not isinstance(chunk, dict)
                or not isinstance(chunk.get("choices"), list)
                or len(chunk["choices"]) > 1
            ):
                raise ValueError
            for key in ("id", "model", "object"):
                value = chunk.get(key)
                if (
                    key not in self.metadata
                    and isinstance(value, str)
                    and len(value.encode()) <= 256
                    and all(32 <= ord(c) < 127 for c in value)
                ):
                    self.metadata[key] = value
            if type(chunk.get("created")) is int and 0 <= chunk["created"] < 2**63:
                self.metadata.setdefault("created", chunk["created"])
            for choice in chunk["choices"]:
                if (
                    not isinstance(choice, dict)
                    or type(choice.get("index", 0)) is not int
                    or choice.get("index", 0) != 0
                ):
                    raise ValueError
                delta = choice.get("delta")
                if (
                    not isinstance(delta, dict)
                    or delta.get("function_call") is not None
                    or delta.get("role") not in {None, "assistant"}
                ):
                    raise ValueError
                if any(
                    delta.get(key) is not None
                    for key in ("reasoning", "reasoning_content", "reasoning_details")
                ):
                    self.reasoning_events_discarded += 1
                text = delta.get("content")
                if text is not None:
                    if not isinstance(text, str) or self.finish_reason is not None and text:
                        raise ValueError
                    self._count(len(text.encode()))
                    self.content.write(text)
                fragments = delta.get("tool_calls")
                if fragments is None:
                    fragments = []
                if not isinstance(fragments, list):
                    raise ValueError
                for fragment in fragments:
                    if not isinstance(fragment, dict):
                        raise ValueError
                    index = fragment.get("index")
                    if (
                        type(index) is not int
                        or not 0 <= index < 4
                        or self.finish_reason is not None
                    ):
                        raise ValueError
                    call = self.calls.setdefault(
                        index,
                        {"id": "", "type": "function", "function": {"name": "", "arguments": ""}},
                    )
                    if fragment.get("type") not in {None, "function"}:
                        raise ValueError
                    ident = fragment.get("id")
                    if ident is not None:
                        if (
                            not isinstance(ident, str)
                            or len(ident.encode()) > 128
                            or call["id"]
                            and ident != call["id"]
                        ):
                            raise ValueError
                        call["id"] = ident
                    function = fragment.get("function", {})
                    if not isinstance(function, dict):
                        raise ValueError
                    name = function.get("name")
                    if name is not None:
                        if not isinstance(name, str):
                            raise ValueError
                        current = call["function"]["name"]
                        candidate = current if name == current else current + name
                        if not accepted_tool_prefix(candidate):
                            raise BrokerError(
                                "tool_denied",
                                "Provider requested an unapproved broker operation.",
                                403,
                                diagnostic="tool_name",
                            )
                        call["function"]["name"] = candidate
                    arguments = function.get("arguments")
                    if arguments is not None:
                        if not isinstance(arguments, str):
                            raise ValueError
                        size = len(arguments.encode())
                        self._count(size)
                        self.argument_bytes += size
                        call["function"]["arguments"] += arguments
                        if len(call["function"]["arguments"].encode()) > 16000:
                            self.limit()
                finish = choice.get("finish_reason")
                if finish is not None:
                    if self.finish_reason is not None or finish not in {"stop", "tool_calls"}:
                        raise ValueError
                    self.finish_reason = finish
        except (ValueError, TypeError, AttributeError, RecursionError):
            raise BrokerError(
                "tool_denied", "Malformed provider tool stream.", 403, diagnostic="stream_shape"
            ) from None

    def normalized(self, names: list[str], usage: dict[str, Any] | None) -> list[dict[str, Any]]:
        delta: dict[str, Any] = {}
        if self.calls:
            delta["tool_calls"] = [
                {"index": index, **call} for index, call in sorted(self.calls.items())
            ]
        chunks: list[dict[str, Any]] = [
            {
                "choices": [
                    {"index": 0, "delta": {"role": "assistant", "content": self.content.getvalue()}}
                ]
            },
            {"choices": [{"index": 0, "delta": delta, "finish_reason": self.finish_reason}]},
        ]
        if usage is not None:
            chunks.append(
                {
                    "choices": [],
                    "usage": {
                        key: usage[key]
                        for key in ("prompt_tokens", "completion_tokens", "total_tokens")
                        if type(usage.get(key)) is int
                    },
                }
            )
        # Reuse the exact reviewed proposal parser and capability scope checks.
        return validate_stream([{**self.metadata, **chunk} for chunk in chunks], names)
