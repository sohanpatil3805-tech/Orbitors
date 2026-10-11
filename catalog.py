"""
OrbitGuard AI — Object Catalogue
Builds one table of trackable objects from the best available source:

  1. Space-Track GP catalogue (full public catalogue) when credentials are set;
  2. otherwise CelesTrak active satellites + debris groups + stations.

Each object is joined with CelesTrak SATCAT metadata (type, owner, operational
status, radar cross-section) and gets an SGP4 propagator.
"""

import io
from dataclasses import dataclass, field
from datetime import datetime, timezone

import numpy as np
import pandas as pd
from sgp4 import omm
from sgp4.api import Satrec

import spacetrack_client
from celestrak_fetcher import CelesTrakFetcher
from config import CELESTRAK_GROUPS, IMPORTANT_SATELLITES, SATCAT_URL, SATCAT_CACHE_TTL_SECONDS, DEFAULT_OBJECT_RADIUS_M
from http_cache import cached_text

MU_EARTH = 398600.4418  # km^3/s^2
EARTH_RADIUS_KM = 6378.137

TYPE_NAMES = {"PAY": "PAYLOAD", "R/B": "ROCKET BODY", "DEB": "DEBRIS", "UNK": "UNKNOWN"}
# SATCAT operational status codes that mean "working spacecraft" (could manoeuvre)
OPERATIONAL_CODES = {"+", "P", "B", "S", "X"}
# Physical size overrides for large structures where radar cross-section understates size (m)
RADIUS_OVERRIDES_M = {25544: 55.0, 48274: 25.0, 20580: 7.0}

DEBRIS_GROUPS = [g for g in CELESTRAK_GROUPS if g.endswith("-debris")]


@dataclass
class Catalog:
    objects: pd.DataFrame                 # one row per object, indexed by NORAD_CAT_ID
    satrecs: dict = field(repr=False)     # NORAD_CAT_ID -> sgp4 Satrec
    source: str = ""
    built_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def watchlist_ids(self, extra: list[int] | None = None) -> list[int]:
        ids = list(IMPORTANT_SATELLITES) + list(extra or [])
        return [i for i in dict.fromkeys(ids) if i in self.satrecs]


def load_satcat(force: bool = False) -> pd.DataFrame:
    text = cached_text(SATCAT_URL, "satcat.csv", SATCAT_CACHE_TTL_SECONDS, force=force, timeout=120)
    if text is None:
        return pd.DataFrame()
    df = pd.read_csv(io.StringIO(text), low_memory=False)
    df = df[df["DECAY_DATE"].isna()]
    return df.set_index("NORAD_CAT_ID")


def _gp_records(force: bool = False) -> tuple[list[dict], str]:
    gp = spacetrack_client.fetch_gp_catalog(force=force)
    if gp:
        return gp, "Space-Track (full catalogue)"

    fetcher = CelesTrakFetcher()
    records: dict[int, dict] = {}
    for group in ["active", "stations", *DEBRIS_GROUPS]:
        for rec in fetcher.fetch_group(group):
            nid = int(rec["NORAD_CAT_ID"])
            if nid not in records or rec.get("EPOCH", "") > records[nid].get("EPOCH", ""):
                records[nid] = rec
    return list(records.values()), "CelesTrak (active + debris groups)"


def _radius_m(row) -> float:
    nid = row.name
    if nid in RADIUS_OVERRIDES_M:
        return RADIUS_OVERRIDES_M[nid]
    default = DEFAULT_OBJECT_RADIUS_M.get(row.get("OBJECT_TYPE", "UNKNOWN"), 1.0)
    rcs = row.get("RCS")
    if pd.notna(rcs) and rcs > 0:
        radius = float(np.clip(np.sqrt(rcs / np.pi), 0.1, 20.0))
        # Radar cross-section understates spacecraft with solar arrays and booms
        return max(radius, default) if row.get("OBJECT_TYPE") in ("PAYLOAD", "ROCKET BODY") else radius
    return default


def build_catalog(force: bool = False, max_epoch_age_days: float = 30.0) -> Catalog:
    records, source = _gp_records(force)
    satcat = load_satcat(force)
    now = datetime.now(timezone.utc)

    rows, satrecs = [], {}
    for rec in records:
        try:
            sat = Satrec()
            omm.initialize(sat, rec)
        except Exception:
            continue
        nid = int(rec["NORAD_CAT_ID"])
        epoch = pd.Timestamp(rec["EPOCH"]).tz_localize("UTC") if pd.Timestamp(rec["EPOCH"]).tzinfo is None \
            else pd.Timestamp(rec["EPOCH"])
        age_days = (now - epoch.to_pydatetime()).total_seconds() / 86400.0
        if age_days > max_epoch_age_days:
            continue
        n = float(rec["MEAN_MOTION"]) * 2 * np.pi / 86400.0
        ecc = float(rec["ECCENTRICITY"])
        sma = (MU_EARTH / n ** 2) ** (1 / 3)
        satrecs[nid] = sat
        rows.append({
            "NORAD_CAT_ID": nid,
            "OBJECT_NAME": rec.get("OBJECT_NAME", str(nid)),
            "EPOCH": epoch,
            "EPOCH_AGE_DAYS": age_days,
            "SMA_KM": sma,
            "ECCENTRICITY": ecc,
            "INCLINATION": float(rec["INCLINATION"]),
            "PERIGEE_KM": sma * (1 - ecc) - EARTH_RADIUS_KM,
            "APOGEE_KM": sma * (1 + ecc) - EARTH_RADIUS_KM,
            "PERIOD_MIN": 1440.0 / float(rec["MEAN_MOTION"]),
            "BSTAR": float(rec.get("BSTAR", 0) or 0),
            "GP_OBJECT_TYPE": rec.get("OBJECT_TYPE"),
        })

    if not rows:
        raise RuntimeError(f"No usable orbit data from {source}: the source could not be reached and nothing is "
                           "cached yet. Check the connection to celestrak.org, or set Space-Track credentials in .env.")
    df = pd.DataFrame(rows).set_index("NORAD_CAT_ID")
    if not satcat.empty:
        meta = satcat.reindex(df.index)
        df["OBJECT_TYPE"] = meta["OBJECT_TYPE"].map(TYPE_NAMES)
        df["OWNER"] = meta["OWNER"]
        df["OPS_STATUS"] = meta["OPS_STATUS_CODE"]
        df["RCS"] = pd.to_numeric(meta["RCS"], errors="coerce")
    else:
        df["OBJECT_TYPE"], df["OWNER"], df["OPS_STATUS"], df["RCS"] = None, None, None, np.nan
    # Space-Track GP records carry their own OBJECT_TYPE; use it where SATCAT has none
    df["OBJECT_TYPE"] = df["OBJECT_TYPE"].fillna(df["GP_OBJECT_TYPE"]).fillna("UNKNOWN")
    df = df.drop(columns="GP_OBJECT_TYPE")
    df["MANOEUVRABLE"] = (df["OBJECT_TYPE"] == "PAYLOAD") & df["OPS_STATUS"].isin(OPERATIONAL_CODES)
    df["RADIUS_M"] = df.apply(_radius_m, axis=1)
    df["IMPORTANT"] = df.index.isin(list(IMPORTANT_SATELLITES))

    print(f"[Catalog] {len(df):,} objects from {source}")
    return Catalog(objects=df, satrecs=satrecs, source=source, built_at=now)


if __name__ == "__main__":
    cat = build_catalog()
    print(cat.objects["OBJECT_TYPE"].value_counts())
    print(cat.objects.loc[cat.watchlist_ids(), ["OBJECT_NAME", "PERIGEE_KM", "RADIUS_M", "EPOCH_AGE_DAYS"]])
