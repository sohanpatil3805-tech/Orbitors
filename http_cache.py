"""
OrbitGuard AI — Disk-cached HTTP downloads
Keeps public data sources polite: one download per TTL, and the last good copy
is reused when a source is unreachable or refuses a request.
"""

import time
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

import requests

from config import CACHE_DIR

HTTP_CACHE_DIR = CACHE_DIR / "http"
USER_AGENT = "OrbitGuardAI/1.0 (research dashboard)"

# A host that just refused or timed out a connection is not retried for this long, so an
# outage costs one connection timeout per refresh instead of one per file (~10 files from
# CelesTrak per refresh, ~20 s each when the host is unreachable).
UNREACHABLE_RETRY_SECONDS = 300
_unreachable_until: dict[str, float] = {}


def host_unreachable(url: str) -> bool:
    """True if `url`'s host failed to connect within the last UNREACHABLE_RETRY_SECONDS."""
    return _unreachable_until.get(urlparse(url).netloc, 0.0) > time.time()


def mark_unreachable(url: str, error: Exception) -> None:
    """Remember a connection-level failure. HTTP errors (e.g. a 403) mean the host is reachable."""
    if isinstance(error, requests.ConnectionError):   # includes connect timeouts and DNS failures
        _unreachable_until[urlparse(url).netloc] = time.time() + UNREACHABLE_RETRY_SECONDS


def cached_text(url: str, name: str, ttl_seconds: int, force: bool = False,
                session: Optional[requests.Session] = None, timeout: int = 60) -> Optional[str]:
    """
    Return the body of `url`, downloading at most once per `ttl_seconds`.
    Falls back to the cached copy (however old) if the download fails.
    Returns None only when there is neither a download nor a cached copy.
    """
    HTTP_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = HTTP_CACHE_DIR / name

    if not force and path.exists() and time.time() - path.stat().st_mtime < ttl_seconds:
        return path.read_text(encoding="utf-8")

    if host_unreachable(url):
        print(f"[HTTP] {name}: {urlparse(url).netloc} was unreachable moments ago; "
              + ("using cached copy" if path.exists() else "no cached copy"))
        return path.read_text(encoding="utf-8") if path.exists() else None

    try:
        getter = session or requests
        resp = getter.get(url, timeout=timeout, headers={"User-Agent": USER_AGENT})
        resp.raise_for_status()
        text = resp.text
        if not text.strip() or text.lstrip().startswith("<!DOCTYPE"):
            raise ValueError("empty or HTML response")
        path.write_text(text, encoding="utf-8")
        return text
    except Exception as e:
        mark_unreachable(url, e)
        print(f"[HTTP] {name}: download failed ({e}); using cached copy" if path.exists()
              else f"[HTTP] {name}: download failed ({e}); no cached copy")
        return path.read_text(encoding="utf-8") if path.exists() else None


def cache_age_seconds(name: str) -> Optional[float]:
    """Age of a cached download, or None if it was never downloaded."""
    path = HTTP_CACHE_DIR / name
    return time.time() - path.stat().st_mtime if path.exists() else None
