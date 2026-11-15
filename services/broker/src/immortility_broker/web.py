"""Allowlisted public web lookup. Redirects are not followed.

DNS answers are checked before the request. A later DNS change for an
allowlisted host is still possible; private and local addresses are rejected
when they are visible at request time.
"""

import ipaddress
import socket
from urllib.parse import quote, urlsplit

import httpx

from .contracts import BrokerError
from .public_fetch import fetch_json, validate_url

ALLOWED_HOSTS = frozenset({"en.wikipedia.org"})
USER_AGENT = "Immortility/0.1 (local desktop research; research@localhost) python-httpx"


async def research_page_async(question: str) -> dict[str, str]:
    """Production path: bounded async I/O, pinned public connection, cancellable."""
    query = " ".join(question.split())[:120]
    if not query:
        raise BrokerError("invalid_request", "Research needs a question.", 400)
    rows = await fetch_json(
        "https://en.wikipedia.org/w/api.php?action=opensearch&limit=1&namespace=0&format=json&search="
        + quote(query)
    )
    if not isinstance(rows, list) or len(rows) < 4 or not rows[3]:
        return {"title": "", "url": "", "extract": ""}
    if any(
        not isinstance(rows[index], list) or not rows[index] or not isinstance(rows[index][0], str)
        for index in (1, 3)
    ):
        raise BrokerError("source_unavailable", "Malformed public search.", 503)
    title, url = rows[1][0][:300], rows[3][0][:2000]
    validate_url(url)
    summary = await fetch_json(
        "https://en.wikipedia.org/api/rest_v1/page/summary/" + quote(title, safe="")
    )
    if not isinstance(summary, dict):
        raise BrokerError("source_unavailable", "Malformed public summary.", 503)
    extract = summary.get("extract", "")
    if not isinstance(extract, str):
        raise BrokerError("source_unavailable", "Malformed public summary.", 503)
    return {"title": title, "url": url, "extract": extract[:1500]}


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
