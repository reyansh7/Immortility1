"""Cancellable, JSON-only HTTPS fetch; connect to a validated IP with original TLS SNI."""

import asyncio
import ipaddress
import json
import socket
from typing import Any
from urllib.parse import urlsplit

import httpcore

from .contracts import BrokerError

ALLOWED_HOSTS = frozenset({"en.wikipedia.org"})
MAX_BYTES = 256000


def validate_url(url: str, *, allowed_hosts: frozenset[str] = ALLOWED_HOSTS) -> str:
    try:
        parsed = urlsplit(url)
        if (
            parsed.scheme != "https"
            or parsed.hostname not in allowed_hosts
            or parsed.port not in {None, 443}
            or parsed.username
            or parsed.password
            or parsed.fragment
        ):
            raise ValueError
        return str(parsed.hostname)
    except ValueError:
        raise BrokerError("tool_denied", "Public URL is outside the approved scope.", 403) from None


class PublicBackend(httpcore.AsyncNetworkBackend):
    def __init__(self, allowed_hosts: frozenset[str] = ALLOWED_HOSTS) -> None:
        self.backend = httpcore.AnyIOBackend()
        self.allowed_hosts = allowed_hosts

    async def connect_tcp(
        self,
        host: str,
        port: int,
        timeout: float | None = None,
        local_address: str | None = None,
        socket_options: Any = None,
    ) -> httpcore.AsyncNetworkStream:
        if host not in self.allowed_hosts or port != 443 or local_address is not None:
            raise BrokerError("tool_denied", "Connection is outside public scope.", 403)
        records = await asyncio.get_running_loop().getaddrinfo(host, port, type=socket.SOCK_STREAM)
        addresses = sorted({str(record[4][0]) for record in records})
        if not addresses or any(
            not ipaddress.ip_address(address).is_global for address in addresses
        ):
            raise BrokerError("tool_denied", "Private or mixed DNS answers are denied.", 403)
        # No second hostname resolution between validation and connect. HTTPCore
        # still uses the original origin hostname for TLS verification and SNI.
        return await self.backend.connect_tcp(
            addresses[0], port, timeout=timeout, socket_options=socket_options
        )


async def fetch_json(
    url: str,
    pool: httpcore.AsyncConnectionPool | None = None,
    *,
    hosts: frozenset[str] = ALLOWED_HOSTS,
    statuses: tuple[int, ...] = (200,),
    types: tuple[bytes, ...] = (b"application/json",),
    user_agent: str = "Immortility/0.1 public lookup",
) -> Any:
    validate_url(url, allowed_hosts=hosts)
    if pool is None:
        async with httpcore.AsyncConnectionPool(
            network_backend=PublicBackend(hosts), max_connections=1, retries=0
        ) as owned:
            return await fetch_json(
                url, owned, hosts=hosts, statuses=statuses, types=types, user_agent=user_agent
            )
    try:
        async with asyncio.timeout(8):
            async with pool.stream(
                "GET",
                url,
                headers={
                    "User-Agent": user_agent,
                    "Accept": "application/json",
                    "Accept-Encoding": "identity",
                },
                extensions={"timeout": {"connect": 3, "read": 5, "write": 3, "pool": 3}},
            ) as response:
                headers = {k.lower(): v.lower() for k, v in response.headers}
                if response.status not in statuses:
                    raise BrokerError(
                        "source_unavailable",
                        "The public source refused or redirected the request.",
                        503,
                    )
                if headers.get(b"content-encoding", b"identity") != b"identity":
                    raise BrokerError(
                        "source_unavailable",
                        "Compressed response was not requested and is refused.",
                        503,
                    )
                if not headers.get(b"content-type", b"").startswith(types):
                    raise BrokerError("source_unavailable", "Expected a JSON public source.", 503)
                body = bytearray()
                async for chunk in response.aiter_stream():
                    if len(body) + len(chunk) > MAX_BYTES:
                        raise BrokerError(
                            "output_limit", "Public source exceeds its byte limit.", 413
                        )
                    body.extend(chunk)
                return json.loads(body)
    except (
        TimeoutError,
        httpcore.NetworkError,
        httpcore.TimeoutException,
        httpcore.ProtocolError,
        ValueError,
        socket.gaierror,
    ):
        raise BrokerError(
            "source_unavailable", "The public source could not be read safely.", 503
        ) from None
