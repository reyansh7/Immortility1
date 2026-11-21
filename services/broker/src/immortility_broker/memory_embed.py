"""Local-only memory embeddings (M2/P3b, DECISIONS D23).

The embedder talks to Ollama on the loopback interface only. The address is fixed in code,
not configurable, so memory text can never be sent to another host: there is no setting,
flag field or environment variable that changes it. Any failure (Ollama not running, model
missing, slow, malformed reply) returns ``None`` and memory falls back to lexical search;
a short circuit breaker avoids paying the timeout on every turn while Ollama is down.

Model: ``nomic-embed-text`` (Apache-2.0, https://huggingface.co/nomic-ai/nomic-embed-text-v1.5,
served by Ollama, MIT). It expects task prefixes, applied here.
"""

from __future__ import annotations

import math
import re
import time
from array import array
from collections.abc import Callable
from typing import Any

import httpx

LOOPBACK = "http://127.0.0.1:11434"
MODEL_PATTERN = re.compile(r"[A-Za-z0-9._:-]{1,64}")
PREFIXES = {
    "nomic-embed-text": ("search_query: ", "search_document: "),
}
MAX_BATCH = 32
MAX_CHARS = 600
BREAKER_SECONDS = 60.0


def _prefixes(model: str) -> tuple[str, str]:
    return PREFIXES.get(model.split(":", 1)[0], ("", ""))


def pack(vector: list[float]) -> bytes:
    return array("f", vector).tobytes()


def unpack(blob: bytes) -> list[float]:
    values = array("f")
    values.frombytes(blob)
    return values.tolist()


def normalize(vector: list[float]) -> list[float]:
    norm = math.sqrt(sum(v * v for v in vector))
    return [v / norm for v in vector] if norm > 0 else vector


def dot(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


class LoopbackEmbedder:
    def __init__(
        self,
        model: str = "nomic-embed-text",
        *,
        timeout: float = 2.0,
        post: Callable[[str, dict[str, Any], float], Any] | None = None,
        clock: Callable[[], float] = time.monotonic,
    ):
        if not MODEL_PATTERN.fullmatch(model):
            raise ValueError("invalid embedding model id")
        self.model = model
        self.timeout = timeout
        self._post = post or self._http_post
        self._clock = clock
        self._down_until = 0.0
        self.dim: int | None = None
        self.calls = 0
        self.failures = 0
        self.last_ms = 0.0

    _client: httpx.Client | None = None

    @classmethod
    def _http_post(cls, url: str, body: dict[str, Any], timeout: float) -> Any:
        if not url.startswith(LOOPBACK + "/"):
            raise ValueError("embeddings are loopback-only")
        # One reused client: building a client per call costs ~200 ms on Windows (SSL
        # context), five times the embedding itself.
        if cls._client is None:
            cls._client = httpx.Client(trust_env=False, follow_redirects=False)
        response = cls._client.post(url, json=body, timeout=timeout)
        response.raise_for_status()
        return response.json()

    def available(self) -> bool:
        return self._clock() >= self._down_until

    def embed(self, texts: list[str], *, query: bool = False) -> list[list[float]] | None:
        if not texts or not self.available():
            return None
        prefix = _prefixes(self.model)[0 if query else 1]
        inputs = [prefix + " ".join(t.split())[:MAX_CHARS] for t in texts[:MAX_BATCH]]
        started = time.perf_counter()
        self.calls += 1
        try:
            data = self._post(
                LOOPBACK + "/api/embed",
                {"model": self.model, "input": inputs, "truncate": True, "keep_alive": "30m"},
                self.timeout,
            )
            vectors = data.get("embeddings") if isinstance(data, dict) else None
            if not isinstance(vectors, list) or len(vectors) != len(inputs):
                raise ValueError("malformed embedding reply")
            out = []
            for vector in vectors:
                if (
                    not isinstance(vector, list)
                    or not 8 <= len(vector) <= 4096
                    or not all(isinstance(v, (int, float)) and math.isfinite(v) for v in vector)
                ):
                    raise ValueError("malformed embedding vector")
                if self.dim is None:
                    self.dim = len(vector)
                if len(vector) != self.dim:
                    raise ValueError("embedding dimension changed")
                out.append(normalize([float(v) for v in vector]))
            return out
        except Exception:
            self.failures += 1
            self._down_until = self._clock() + BREAKER_SECONDS
            return None
        finally:
            self.last_ms = round((time.perf_counter() - started) * 1000, 1)

    def status(self) -> dict[str, Any]:
        return {
            "model": self.model,
            "endpoint": "loopback",
            "available": self.available(),
            "dim": self.dim,
            "calls": self.calls,
            "failures": self.failures,
            "last_ms": self.last_ms,
        }
