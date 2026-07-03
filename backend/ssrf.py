"""
SSRF Protection — prevents Server-Side Request Forgery attacks.
Validates URLs against private/internal IP ranges before fetching.
"""
import socket
import ipaddress
import logging
from urllib.parse import urlparse, urljoin

logger = logging.getLogger("fake_news_api")

# HTTP status codes that indicate a redirect (validated per-hop by safe_get).
_REDIRECT_STATUS = {301, 302, 303, 307, 308}

# IP ranges that must NEVER be fetched by the server
_BLOCKED_NETWORKS = [
    ipaddress.ip_network("0.0.0.0/8"),         # "This" network
    ipaddress.ip_network("10.0.0.0/8"),         # Private Class A
    ipaddress.ip_network("100.64.0.0/10"),      # Carrier-grade NAT
    ipaddress.ip_network("127.0.0.0/8"),        # Loopback
    ipaddress.ip_network("169.254.0.0/16"),     # Link-local (AWS/GCP metadata!)
    ipaddress.ip_network("172.16.0.0/12"),      # Private Class B
    ipaddress.ip_network("192.0.0.0/24"),       # IETF Protocol Assignments
    ipaddress.ip_network("192.168.0.0/16"),     # Private Class C
    ipaddress.ip_network("198.18.0.0/15"),      # Benchmarking
    ipaddress.ip_network("224.0.0.0/4"),        # Multicast
    ipaddress.ip_network("240.0.0.0/4"),        # Reserved
    ipaddress.ip_network("255.255.255.255/32"), # Broadcast
    # IPv6
    ipaddress.ip_network("::1/128"),            # Loopback
    ipaddress.ip_network("fc00::/7"),           # Unique local
    ipaddress.ip_network("fe80::/10"),          # Link-local
    ipaddress.ip_network("ff00::/8"),           # Multicast
]


def validate_url(url: str) -> str:
    """Validate a URL is safe to fetch (not targeting internal/private IPs).

    Args:
        url: The URL to validate.

    Returns:
        The validated URL string.

    Raises:
        ValueError: If the URL targets a private/internal IP or is malformed.
    """
    parsed = urlparse(url)

    # Must be http or https
    if parsed.scheme not in ("http", "https"):
        raise ValueError("Only http:// and https:// URLs are allowed")

    hostname = parsed.hostname
    if not hostname:
        raise ValueError("URL must have a valid hostname")

    # Block obviously dangerous hostnames
    dangerous = {"localhost", "metadata.google.internal", "instance-data"}
    if hostname.lower() in dangerous:
        raise ValueError(f"Blocked hostname: {hostname}")

    # Resolve DNS and check all IPs
    try:
        addr_infos = socket.getaddrinfo(hostname, parsed.port or 443, proto=socket.IPPROTO_TCP)
    except socket.gaierror:
        raise ValueError(f"Cannot resolve hostname: {hostname}")

    for family, _, _, _, sockaddr in addr_infos:
        ip = ipaddress.ip_address(sockaddr[0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
            raise ValueError(f"URL resolves to blocked IP range: {ip}")
        for net in _BLOCKED_NETWORKS:
            if ip in net:
                raise ValueError(f"URL resolves to blocked IP range: {ip}")

    return url


async def safe_get(client, url: str, headers: dict | None = None, max_redirects: int = 5):
    """SSRF-safe HTTP GET that validates the target on every redirect hop.

    Auto-following redirects (httpx `follow_redirects=True`) is an SSRF bypass:
    a public URL can 30x-redirect to an internal address (e.g. the cloud metadata
    endpoint) which never gets re-validated. This helper disables automatic
    redirects and re-runs `validate_url` against each `Location` before fetching it.

    Note: this closes the redirect bypass. A determined attacker controlling DNS
    could still perform a rebinding (TOCTOU) attack between validation and connect;
    fully closing that requires pinning the resolved IP into the socket, which is
    incompatible with TLS SNI for the https news sources this app fetches.

    Args:
        client: an ``httpx.AsyncClient``.
        url: the initial URL (validated before the first request).
        headers: optional request headers.
        max_redirects: maximum number of redirect hops to follow.

    Returns:
        The final ``httpx.Response``.

    Raises:
        ValueError: if the initial URL or any redirect target is blocked, or if
            the redirect limit is exceeded.
    """
    current = validate_url(url)
    for _ in range(max_redirects + 1):
        resp = await client.get(current, headers=headers, follow_redirects=False)
        if resp.status_code in _REDIRECT_STATUS and "location" in resp.headers:
            location = urljoin(current, resp.headers["location"])
            current = validate_url(location)  # raises ValueError if blocked
            continue
        return resp
    raise ValueError("Too many redirects")
