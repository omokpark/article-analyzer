import ipaddress
import socket
from urllib.parse import urlparse, urljoin

import requests
import trafilatura

_ALLOWED_SCHEMES = {"http", "https"}
_MAX_REDIRECTS = 5


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


def _safe_get(url: str, timeout: int = 15, headers: dict | None = None) -> str | None:
    """SSRF-safe HTTP GET.

    - allow_redirects=False로 리다이렉트를 직접 처리하여 각 단계의 URL을 검증
    - DNS rebinding: 각 요청 직전에 _is_safe_url()로 재검증해 TOCTOU 창을 최소화
    """
    current_url = url

    for _ in range(_MAX_REDIRECTS):
        # 매 리다이렉트 단계마다 재검증 (DNS rebinding 방어)
        if not _is_safe_url(current_url):
            return None

        try:
            response = requests.get(
                current_url,
                headers=headers or {},
                timeout=timeout,
                allow_redirects=False,
            )
        except requests.RequestException:
            return None

        if response.is_redirect or response.status_code in (301, 302, 303, 307, 308):
            location = response.headers.get("Location", "")
            if not location:
                return None
            # 상대 URL → 절대 URL 변환 후 SSRF 재검증
            next_url = urljoin(current_url, location)
            if not _is_safe_url(next_url):
                return None
            current_url = next_url
            continue

        if response.ok:
            return response.text
        return None

    return None  # 리다이렉트 횟수 초과


def _extract_with_trafilatura(url: str) -> dict | None:
    # trafilatura.fetch_url() 대신 _safe_get()으로 직접 fetch해
    # 리다이렉트 대상 URL까지 SSRF 검증 적용
    html = _safe_get(url)
    if html is None:
        return None

    body = trafilatura.extract(html)
    if body is None:
        return None

    meta = trafilatura.extract_metadata(html)
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
