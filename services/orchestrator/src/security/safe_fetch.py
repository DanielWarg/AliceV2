import ipaddress
from urllib.parse import urlparse

import httpx


def _is_private(host: str) -> bool:
    try:
        ip = ipaddress.ip_address(host)
        return ip.is_private or ip.is_loopback or ip.is_link_local
    except ValueError:
        return host in ("localhost",)
    except Exception:
        return True


def allowlisted(url: str, hosts: set[str]) -> bool:
    u = urlparse(url)
    if u.scheme not in ("http", "https"):
        return False
    host = (u.hostname or "").lower()
    if not host or _is_private(host):
        return False
    return host in hosts


async def safe_get(
    url: str, hosts: set[str], max_bytes: int = 5 * 1024 * 1024
) -> bytes:
    if not allowlisted(url, hosts):
        raise PermissionError("net_blocked")
    async with httpx.AsyncClient(follow_redirects=False, timeout=5.0) as cli:
        r = await cli.get(url)
        if r.is_redirect:
            raise PermissionError("redirect_blocked")
        if int(r.headers.get("content-length", "0") or 0) > max_bytes:
            raise PermissionError("size_limit")
        content = r.content
        if len(content) > max_bytes:
            raise PermissionError("size_limit")
        return content
