import requests
import trafilatura


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
    return _extract_with_trafilatura(url) or _extract_with_jina(url)
