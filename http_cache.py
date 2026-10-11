"""
OrbitGuard AI — Disk-cached HTTP downloads
Keeps public data sources polite: one download per TTL, and the last good copy
is reused when a source is unreachable or refuses a request.
"""

import time
from pathlib import Path
from typing import Optional

import requests

from config import CACHE_DIR

HTTP_CACHE_DIR = CACHE_DIR / "http"
USER_AGENT = "OrbitGuardAI/1.0 (research dashboard)"


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
        print(f"[HTTP] {name}: download failed ({e}); using cached copy" if path.exists()
              else f"[HTTP] {name}: download failed ({e}); no cached copy")
        return path.read_text(encoding="utf-8") if path.exists() else None


def cache_age_seconds(name: str) -> Optional[float]:
    """Age of a cached download, or None if it was never downloaded."""
    path = HTTP_CACHE_DIR / name
    return time.time() - path.stat().st_mtime if path.exists() else None
