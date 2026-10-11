"""
OrbitGuard AI — Space-Track.org client (optional)

With a free Space-Track account the dashboard gets:
  * the full public catalogue (~30k on-orbit objects, including all debris),
    instead of CelesTrak's active + selected debris groups;
  * official public conjunction messages (class cdm_public) with the 18th Space
    Defense Squadron's own collision probability, shown next to ours.

Credentials are read from the environment or a git-ignored `.env` file:
    SPACETRACK_USER=you@example.com
    SPACETRACK_PASSWORD=your-password
Without them every function returns None and the app falls back to CelesTrak.
"""

import json
import os
from typing import Optional

import requests

from config import PROJECT_ROOT, SPACETRACK_BASE_URL, SPACETRACK_CACHE_TTL_SECONDS
from http_cache import cached_text, cache_age_seconds, USER_AGENT

GP_QUERY = "/basicspacedata/query/class/gp/decay_date/null-val/epoch/%3Enow-30/orderby/norad_cat_id/format/json"
CDM_QUERY = "/basicspacedata/query/class/cdm_public/TCA/%3Enow/orderby/TCA%20asc/format/json"


def _read_dotenv() -> dict:
    path = PROJECT_ROOT / ".env"
    values = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                values[key.strip()] = val.strip().strip('"').strip("'")
    return values


def credentials() -> Optional[tuple[str, str]]:
    env = _read_dotenv()
    user = os.environ.get("SPACETRACK_USER") or env.get("SPACETRACK_USER")
    password = os.environ.get("SPACETRACK_PASSWORD") or env.get("SPACETRACK_PASSWORD")
    return (user, password) if user and password else None


def is_configured() -> bool:
    return credentials() is not None


def _session() -> Optional[requests.Session]:
    creds = credentials()
    if creds is None:
        return None
    s = requests.Session()
    s.headers["User-Agent"] = USER_AGENT
    try:
        resp = s.post(f"{SPACETRACK_BASE_URL}/ajaxauth/login",
                      data={"identity": creds[0], "password": creds[1]}, timeout=30)
        resp.raise_for_status()
        if "Failed" in resp.text:
            print("[Space-Track] Login failed — check SPACETRACK_USER / SPACETRACK_PASSWORD")
            return None
        return s
    except requests.RequestException as e:
        print(f"[Space-Track] Login error: {e}")
        return None


def _query(path: str, name: str, force: bool = False) -> Optional[list[dict]]:
    if not is_configured():
        return None
    # Only log in when the cache actually needs a download
    age = cache_age_seconds(name)
    fresh = age is not None and age < SPACETRACK_CACHE_TTL_SECONDS
    session = None if (fresh and not force) else _session()
    if session is None and age is None:
        return None
    text = cached_text(f"{SPACETRACK_BASE_URL}{path}", name, SPACETRACK_CACHE_TTL_SECONDS,
                       force=force and session is not None, session=session, timeout=180)
    if text is None:
        return None
    try:
        data = json.loads(text)
        return data if isinstance(data, list) else None
    except json.JSONDecodeError:
        return None


def fetch_gp_catalog(force: bool = False) -> Optional[list[dict]]:
    """Latest GP (OMM) element set for every on-orbit object, or None."""
    return _query(GP_QUERY, "spacetrack_gp.json", force)


def fetch_public_cdms(force: bool = False) -> Optional[list[dict]]:
    """
    Upcoming public conjunction messages, or None. Each has TCA, MIN_RNG (metres),
    PC, SAT_1_ID / SAT_2_ID, SAT_1_NAME / SAT_2_NAME, object types and RCS sizes.
    """
    return _query(CDM_QUERY, "spacetrack_cdm_public.json", force)
