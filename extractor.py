import ipaddress
import socket
from urllib.parse import urlparse

import requests
import trafilatura

_ALLOWED_SCHEMES = {"http", "https"}


def _is_safe_url(url: str) -> bool:
    """내부 네트워크 주소 및 허용되지 않은 스킴 차단 (SSRF 방지)"""
    try:
        parsed = urlparse(url)
        if parsed.scheme not in _ALLOWED_SCHEMES:
            return False
        hostname = parsed.hostname
        if not hostname:
            return False
        # IP 주소 직접 입력 차단 (루프백, 사설망, 링크로컬 등)
        try:
            addr = ipaddress.ip_address(hostname)
            if addr.is_private or addr.is_loopback or addr.is_link_local or addr.is_reserved:
                return False
        except ValueError:
            pass  # hostname은 도메인명 — DNS 해석 후 재확인
        # 도메인을 IP로 해석해서 내부망 여부 확인
        try:
            resolved = socket.getaddrinfo(hostname, None)
            for *_, sockaddr in resolved:
                ip_str = sockaddr[0]
                addr = ipaddress.ip_address(ip_str)
                if addr.is_private or addr.is_loopback or addr.is_link_local or addr.is_reserved:
                    return False
        except socket.gaierror:
            return False
        return True
    except Exception:
        return False


def _extract_with_trafilatura(url: str) -> dict | None:
    downloaded = trafilatura.fetch_url(url)
    if downloaded is None:
        return None

    body = trafilatura.extract(downloaded)
    if body is None:
        return None

    meta = trafilatura.extract_metadata(downloaded)
    title = meta.title if meta and meta.title else ""

    return {"title": title, "body": body, "url": url}


def _extract_with_jina(url: str) -> dict | None:
    try:
        response = requests.get(
            f"https://r.jina.ai/{url}",
            headers={"Accept": "application/json"},
            timeout=15,
        )
        response.raise_for_status()
        data = response.json()
        body = data.get("data", {}).get("content", "").strip()
        title = data.get("data", {}).get("title", "").strip()
        if not body:
            return None
        return {"title": title, "body": body, "url": url}
    except Exception:
        return None


def extract_article(url: str) -> dict | None:
    if not _is_safe_url(url):
        return None
    return _extract_with_trafilatura(url) or _extract_with_jina(url)
