"""Allowlisted public web lookup. Redirects are not followed.

DNS answers are checked before the request. A later DNS change for an
allowlisted host is still possible; private and local addresses are rejected
when they are visible at request time.
"""

import asyncio
import html
import ipaddress
import re
import socket
from typing import Any
from urllib.parse import quote, urlsplit

import httpx

from .contracts import BrokerError
from .public_fetch import fetch_json, validate_url

ALLOWED_HOSTS = frozenset({"en.wikipedia.org"})
USER_AGENT = "Immortility/0.1 (local desktop research; research@localhost) python-httpx"


SEARCH_HOSTS = frozenset({"en.wikipedia.org", "api.duckduckgo.com"})
_FILLER = re.compile(
    r"^(?:please\s+)?(?:(?:can|could) you\s+)?(?:search (?:the web|online|the internet|wikipedia) "
    r"(?:for|about)|web search(?: for)?|look up|find (?:information|info) (?:on|about)|"
    r"research|what does (?:the web|the internet|wikipedia) say about)\s+",
    re.I,
)
_WEB_INTENT = re.compile(
    r"\b(?:search (?:the web|online|the internet|wikipedia)|web search|look (?:it )?up|"
    r"on (?:the web|wikipedia)|search for .{3,80} online)\b",
    re.I,
)
# Wikimedia's robot policy (https://w.wiki/4wJS) refuses API clients whose User-Agent has no
# real contact (measured: 403). The owner sets one in web-contact.json; it is never invented.
# Without it Wikipedia is skipped and only DuckDuckGo Instant Answers are queried.
CONTACT = {"value": ""}
_CONTACT = re.compile(
    r"(?:mailto:)?[^\s@<>()]{1,64}@[A-Za-z0-9.-]{1,120}\.[A-Za-z]{2,24}|https://[^\s<>()]{4,200}"
)


def configure_contact(value: str) -> bool:
    value = value.strip()
    if not _CONTACT.fullmatch(value):
        CONTACT["value"] = ""
        return False
    CONTACT["value"] = value
    return True


def _wiki_agent() -> str:
    return f"Immortility/0.1 (personal desktop assistant; {CONTACT['value']}) httpcore"


_OOB = ("[OUT-OF-BAND USER MESSAGE", "[/OUT-OF-BAND USER MESSAGE]")


def web_lookup_requested(content: str) -> bool:
    return bool(_WEB_INTENT.search(content))


def search_query(question: str) -> str:
    """The only text that leaves the PC: the user's question, trimmed, max 120 chars.

    Credential-shaped text is never sent (the lookup is skipped instead)."""
    from .memory import redact

    query = " ".join(question.split())
    query = _FILLER.sub("", query).strip(" ?.!")[:120]
    if not query:
        raise BrokerError("invalid_request", "Research needs a question.", 400)
    if redact(query) != query:
        raise BrokerError("private_query", "The question looks like it contains a secret.", 403)
    return query


def _clean(text: str, limit: int) -> str:
    text = html.unescape(re.sub(r"<[^>]*>", "", text))
    text = " ".join(text.split())
    for marker in _OOB:
        text = text.replace(marker, "[UNTRUSTED SOURCE MARKER")
    return text[:limit]


async def _wikipedia(query: str) -> list[dict[str, str]]:
    if not CONTACT["value"]:
        return []  # no contact configured: respect the robot policy and skip Wikipedia
    found = await fetch_json(
        "https://en.wikipedia.org/w/rest.php/v1/search/page?limit=3&q=" + quote(query),
        hosts=SEARCH_HOSTS,
        user_agent=_wiki_agent(),
    )
    pages = found.get("pages") if isinstance(found, dict) else None
    if not isinstance(pages, list):
        raise BrokerError("source_unavailable", "Malformed public search.", 503)
    sources = []
    for page in pages[:3]:
        if not isinstance(page, dict) or not isinstance(page.get("key"), str):
            continue
        title = _clean(str(page.get("title", "")), 120)
        url = "https://en.wikipedia.org/wiki/" + quote(page["key"], safe="_()',")
        validate_url(url, allowed_hosts=SEARCH_HOSTS)
        snippet = " — ".join(
            part
            for part in (
                _clean(str(page.get("description") or ""), 160),
                _clean(str(page.get("excerpt") or ""), 340),
            )
            if part
        )
        sources.append({"source": "wikipedia", "title": title, "url": url, "snippet": snippet})
    if sources:
        summary = await fetch_json(
            "https://en.wikipedia.org/api/rest_v1/page/summary/"
            + quote(sources[0]["title"], safe=""),
            hosts=SEARCH_HOSTS,
            user_agent=_wiki_agent(),
        )
        if isinstance(summary, dict) and isinstance(summary.get("extract"), str):
            sources[0]["snippet"] = _clean(summary["extract"], 900)
    return sources


async def _duckduckgo(query: str) -> list[dict[str, str]]:
    # DuckDuckGo Instant Answer API: free, no key, no tracking parameters sent.
    data = await fetch_json(
        "https://api.duckduckgo.com/?format=json&no_html=1&skip_disambig=1&no_redirect=1&t=immortility&q="
        + quote(query),
        hosts=SEARCH_HOSTS,
        statuses=(200, 202),
        types=(b"application/json", b"application/x-javascript"),
    )
    if not isinstance(data, dict):
        raise BrokerError("source_unavailable", "Malformed instant answer.", 503)
    sources = []
    answer = _clean(str(data.get("Answer") or ""), 300)
    if answer:
        sources.append(
            {
                "source": "duckduckgo",
                "title": "DuckDuckGo instant answer",
                "url": "https://duckduckgo.com/?q=" + quote(query),
                "snippet": answer,
            }
        )
    abstract = _clean(str(data.get("AbstractText") or ""), 700)
    url = str(data.get("AbstractURL") or "")
    if abstract and url.startswith("https://"):
        sources.append(
            {
                "source": "duckduckgo",
                "title": _clean(str(data.get("Heading") or "Summary"), 120)
                + " ("
                + _clean(str(data.get("AbstractSource") or "web"), 40)
                + ")",
                "url": url[:300],
                "snippet": abstract,
            }
        )
    return sources


async def research_page_async(question: str) -> dict[str, Any]:
    """Free public lookup: Wikipedia search + summary and the DuckDuckGo Instant Answer API,
    queried in parallel. Results are untrusted data; nothing is invented when both fail."""
    query = search_query(question)
    results = await asyncio.gather(_wikipedia(query), _duckduckgo(query), return_exceptions=True)
    for result in results:
        if isinstance(result, BaseException) and not isinstance(result, Exception):
            raise result  # cancellation and interpreter exits propagate
    if all(isinstance(result, Exception) for result in results):
        raise BrokerError("source_unavailable", "No free public source answered.", 503)
    sources: list[dict[str, str]] = []
    seen: set[str] = set()
    # An instant answer (DuckDuckGo) first, then Wikipedia pages, deduplicated by URL.
    ordered = [*(results[1] if isinstance(results[1], list) else [])]
    ordered += results[0] if isinstance(results[0], list) else []
    for source in ordered:
        key = source["url"].split("#")[0].lower()
        if key in seen or not source["snippet"]:
            continue
        seen.add(key)
        sources.append(source)
    sources = sources[:4]
    if not sources:
        return {"title": "", "url": "", "extract": "", "sources": [], "query": query}
    first = sources[0]
    return {
        "title": first["title"],
        "url": first["url"],
        "extract": first["snippet"],
        "sources": sources,
        "query": query,
    }


def guard_url(url: str) -> str:
    parsed = urlsplit(url)
    host = (parsed.hostname or "").lower()
    if parsed.scheme != "https" or host not in ALLOWED_HOSTS or parsed.username or parsed.password:
        raise BrokerError("tool_denied", "That web address is not allowed.", 403)
    if parsed.port not in {None, 443}:
        raise BrokerError("tool_denied", "That web address is not allowed.", 403)
    try:
        infos = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
    except socket.gaierror as error:
        raise BrokerError(
            "catalog_unavailable", "The public source could not be resolved."
        ) from error
    if not infos:
        raise BrokerError("catalog_unavailable", "The public source could not be resolved.")
    for info in infos:
        address = ipaddress.ip_address(info[4][0])
        if not address.is_global:
            raise BrokerError("tool_denied", "That address is not public.", 403)
    return url


def _get(client: httpx.Client, url: str) -> httpx.Response:
    guarded = guard_url(url)
    try:
        response = client.get(guarded, timeout=8, follow_redirects=False)
    except httpx.HTTPError as error:
        raise BrokerError("catalog_unavailable", "The public source did not respond.") from error
    if response.status_code == 403:
        raise BrokerError("tool_denied", "The public source refused the request.", 403)
    if response.status_code != 200:
        raise BrokerError("catalog_unavailable", "The public source did not respond.")
    return response


def research_page(question: str, client: httpx.Client | None = None) -> dict[str, str]:
    """Search English Wikipedia and return one summary. No result is invented."""
    query = " ".join(question.split())[:120]
    if not query:
        raise BrokerError("invalid_request", "Research needs a question.", 400)
    owns = client is None
    http = client or httpx.Client(
        trust_env=False,
        follow_redirects=False,
        headers={"User-Agent": USER_AGENT},
    )
    try:
        search_url = (
            "https://en.wikipedia.org/w/api.php?action=opensearch&limit=1&namespace=0"
            f"&format=json&search={quote(query)}"
        )
        rows = _get(http, search_url).json()
        if not isinstance(rows, list) or len(rows) < 4 or not rows[3]:
            return {"title": "", "url": "", "extract": ""}
        page_url = str(rows[3][0])
        guard_url(page_url)
        title = str(rows[1][0])
        summary_url = "https://en.wikipedia.org/api/rest_v1/page/summary/" + quote(title, safe="")
        summary = _get(http, summary_url).json()
        extract = str(summary.get("extract") or "")[:1500]
        return {"title": title, "url": page_url, "extract": extract}
    finally:
        if owns:
            http.close()
