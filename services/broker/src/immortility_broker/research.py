"""Bounded public-source research. Fixed reviewed source IDs, no arbitrary URL or query egress."""

import asyncio
import hashlib
import re
import time
from collections import OrderedDict
from collections.abc import Awaitable, Callable
from typing import Any, Literal

import httpcore
from pydantic import Field

from .capabilities import StrictModel
from .contracts import BrokerError, now
from .public_fetch import PublicBackend, validate_url

SourceId = Literal["mcp-security", "mcp-authorization", "owasp-mcp"]
SOURCES = {
    "mcp-security": (
        "MCP Security Best Practices",
        "https://raw.githubusercontent.com/modelcontextprotocol/modelcontextprotocol/main/docs/docs/2026-07-28/tutorials/security/security_best_practices.mdx",
    ),
    "mcp-authorization": (
        "MCP Authorization 2026 07 28",
        "https://raw.githubusercontent.com/modelcontextprotocol/modelcontextprotocol/main/docs/specification/2026-07-28/basic/authorization/index.mdx",
    ),
    "owasp-mcp": (
        "OWASP MCP Security Cheat Sheet",
        "https://raw.githubusercontent.com/OWASP/CheatSheetSeries/master/cheatsheets/MCP_Security_Cheat_Sheet.md",
    ),
}
HOSTS = frozenset({"raw.githubusercontent.com"})


class ResearchInput(StrictModel):
    query: str = Field(min_length=3, max_length=200)
    source_ids: list[SourceId] = Field(default_factory=list, max_length=3)


class Evidence(StrictModel):
    source_id: SourceId
    title: str = Field(max_length=120)
    url: str = Field(max_length=300)
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    retrieved_at: str = Field(max_length=40)
    excerpt: str = Field(min_length=20, max_length=650)
    cache_hit: bool


class ResearchOutput(StrictModel):
    sources: list[Evidence] = Field(min_length=1, max_length=3)
    unavailable: list[SourceId] = Field(max_length=3)
    search_mode: Literal["reviewed-source-catalog"] = "reviewed-source-catalog"
    source_trust: Literal["untrusted-data"] = "untrusted-data"


def model_evidence(result: dict[str, Any]) -> dict[str, Any]:
    """Keep full provenance in the broker; send only evidence needed for drafting."""
    checked = ResearchOutput.model_validate(result)
    return {
        "sources": [
            {"source_id": source.source_id, "title": source.title, "excerpt": source.excerpt}
            for source in checked.sources
        ],
        "unavailable": checked.unavailable,
        "search_mode": checked.search_mode,
        "source_trust": checked.source_trust,
    }


async def fetch_source(source_id: str) -> bytes:
    url = SOURCES[source_id][1]
    validate_url(url, allowed_hosts=HOSTS)
    try:
        async with (
            asyncio.timeout(8),
            httpcore.AsyncConnectionPool(
                network_backend=PublicBackend(HOSTS), max_connections=1, retries=0
            ) as pool,
        ):
            async with pool.stream(
                "GET",
                url,
                headers={
                    "Accept": "text/plain",
                    "Accept-Encoding": "identity",
                    "User-Agent": "Immortility/0.1 reviewed public sources",
                },
                extensions={"timeout": {"connect": 3, "read": 5, "write": 3, "pool": 3}},
            ) as response:
                headers = {key.lower(): value.lower() for key, value in response.headers}
                if (
                    response.status != 200
                    or headers.get(b"content-encoding", b"identity") != b"identity"
                    or not headers.get(b"content-type", b"").startswith(b"text/plain")
                ):
                    raise BrokerError("source_unavailable", "Source response was refused.", 503)
                if int(headers.get(b"content-length", b"0")) > 256000:
                    raise BrokerError("source_limit", "Source exceeds the read limit.", 413)
                body = bytearray()
                async for chunk in response.aiter_stream():
                    if len(body) + len(chunk) > 256000:
                        raise BrokerError("source_limit", "Source exceeds the read limit.", 413)
                    body.extend(chunk)
                return bytes(body)
    except BrokerError:
        raise
    except (
        httpcore.NetworkError,
        httpcore.TimeoutException,
        httpcore.ProtocolError,
        TimeoutError,
        OSError,
        ValueError,
    ):
        raise BrokerError(
            "source_unavailable", "Public source could not be retrieved safely.", 503
        ) from None


def excerpt(text: str, query: str) -> str:
    # No HTML, JS, MDX or fenced code is executed. Prefer relevant prose.
    plain = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
    plain = re.sub(r"<[^>]*>", "", plain)
    blocks = [re.sub(r"\s+", " ", part).strip() for part in plain.split("\n\n")]
    blocks = [
        part
        for part in blocks
        if 60 <= len(part) <= 2000 and not part.startswith(("---", "import ", "export "))
    ]
    terms = set(re.findall(r"[a-z]{3,}", query.lower())) - {
        "the",
        "and",
        "for",
        "report",
        "research",
    }
    ranked = sorted(
        enumerate(blocks),
        key=lambda item: (
            -sum(term in item[1].lower() for term in terms)
            - 3
            * sum(
                word in item[1].lower()
                for word in ("must", "validate", "least privilege", "scope", "token")
            ),
            item[0],
        ),
    )
    chosen = " ".join(block for _, block in ranked[:2])[:650]
    # Hermes' reserved OOB steering syntax must never originate in a source.
    chosen = chosen.replace("[OUT-OF-BAND USER MESSAGE", "[UNTRUSTED SOURCE MARKER").replace(
        "[/OUT-OF-BAND USER MESSAGE]", "[END UNTRUSTED MARKER]"
    )
    if len(chosen) < 20:
        raise BrokerError("source_unavailable", "Source contains no usable evidence.", 503)
    return chosen


class PublicResearch:
    def __init__(self, fetcher: Callable[[str], Awaitable[bytes]] = fetch_source):
        self.fetcher = fetcher
        self.cache: OrderedDict[str, tuple[float, bytes, str]] = OrderedDict()

    async def retrieve(self, arguments: dict[str, Any]) -> dict[str, Any]:
        request = ResearchInput.model_validate(arguments)
        if not request.source_ids and not re.search(
            r"\bmcp\b|model context protocol", request.query, re.I
        ):
            raise BrokerError(
                "source_scope", "Only the reviewed MCP security source catalog is available.", 403
            )
        selected = request.source_ids or (
            ["mcp-security", "owasp-mcp"]
            if "authoriz" not in request.query.lower()
            else ["mcp-security", "mcp-authorization", "owasp-mcp"]
        )
        selected = list(dict.fromkeys(selected))
        sources, unavailable = [], []
        for ident in selected:
            try:
                cached = self.cache.get(ident)
                hit = cached is not None and time.monotonic() - cached[0] < 900
                if not hit:
                    body = await self.fetcher(ident)
                    if len(body) > 256000:
                        raise BrokerError("source_limit", "Source exceeds limit.", 413)
                    cached = (time.monotonic(), body, now())
                    self.cache[ident] = cached
                    while len(self.cache) > 3:
                        self.cache.popitem(last=False)
                assert cached is not None
                _, body, fetched_at = cached
                sources.append(
                    Evidence(
                        source_id=ident,
                        title=SOURCES[ident][0],
                        url=SOURCES[ident][1],
                        sha256=hashlib.sha256(body).hexdigest(),
                        retrieved_at=fetched_at,
                        excerpt=excerpt(body.decode("utf-8", "strict"), request.query),
                        cache_hit=hit,
                    )
                )
            except (BrokerError, UnicodeError):
                unavailable.append(ident)
        if not sources:
            raise BrokerError("source_unavailable", "No reviewed public source was available.", 503)
        return ResearchOutput(sources=sources, unavailable=unavailable).model_dump(mode="json")
