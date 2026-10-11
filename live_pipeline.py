"""
OrbitGuard AI — Live pipeline

    catalogue (Space-Track or CelesTrak) + SATCAT + space weather
        → SGP4 screening of the watchlist (+ any test threats)
        → Space-Track official CDMs merged in (if configured)
        → collision probability with ML-predicted uncertainty
        → watchlist summary and manoeuvre plans for HIGH/CRITICAL events

Results are cached on disk per catalogue version, so restarting the dashboard
does not re-screen until new orbit data arrives.
"""

import hashlib
import json
import pickle
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

import numpy as np
import pandas as pd

import spacetrack_client
from catalog import Catalog, build_catalog
from config import CACHE_DIR, PROPAGATION_WINDOW_HOURS
from manoeuvre_planner import ManoeuvrePlanner
from orbit_propagation import utc_now
from risk_engine import LiveRiskAssessor
from scenario import create_threat, with_threats
from screening import ObjectSource, screen, NEAR_KM
from space_weather import weather_for
from uncertainty_model import UncertaintyModel

STATE_CACHE = CACHE_DIR / "live_state.pkl"
STATUS_ORDER = {"DANGER": 2, "REVIEW": 1, "SAFE": 0}


@dataclass
class LiveState:
    t0: datetime
    catalog: Catalog
    objects: pd.DataFrame          # catalogue + simulated threats
    source: ObjectSource
    watch_ids: list
    conjunctions: pd.DataFrame     # assessed
    near: pd.DataFrame
    weather: dict
    official_cdms: int = 0
    threats: list = field(default_factory=list)
    key: str = ""

    def assessor(self) -> LiveRiskAssessor:
        return LiveRiskAssessor(load_uncertainty_model(), self.weather)

    def planner(self, spacecraft: Optional[dict] = None) -> ManoeuvrePlanner:
        return ManoeuvrePlanner(self.objects, self.source, self.assessor(), self.t0, spacecraft,
                                PROPAGATION_WINDOW_HOURS, baseline=self.conjunctions, near=self.near)


_UM = None


def load_uncertainty_model() -> Optional[UncertaintyModel]:
    global _UM
    if _UM is None and UncertaintyModel.exists():
        _UM = UncertaintyModel.load()
    return _UM


def _merge_official(conj: pd.DataFrame, cdms: Optional[list]) -> pd.DataFrame:
    conj = conj.copy()
    conj["OFFICIAL_PC"], conj["OFFICIAL_MISS_KM"] = np.nan, np.nan
    if conj.empty or not cdms:
        return conj
    off = pd.DataFrame(cdms)
    off["TCA"] = pd.to_datetime(off["TCA"], utc=True)
    off["PC"] = pd.to_numeric(off["PC"], errors="coerce")
    off["MIN_RNG"] = pd.to_numeric(off["MIN_RNG"], errors="coerce")
    for col in ("SAT_1_ID", "SAT_2_ID"):
        off[col] = pd.to_numeric(off[col], errors="coerce")
    for i, row in conj.iterrows():
        pair = {int(row["PRIMARY_ID"]), int(row["SECONDARY_ID"])}
        m = off[off.apply(lambda r: {r["SAT_1_ID"], r["SAT_2_ID"]} == pair, axis=1)
                & ((off["TCA"] - pd.Timestamp(row["TCA"])).abs() < pd.Timedelta(minutes=2))]
        if not m.empty:
            conj.at[i, "OFFICIAL_PC"] = float(m["PC"].max())
            conj.at[i, "OFFICIAL_MISS_KM"] = float(m["MIN_RNG"].min()) / 1000.0
    return conj


def _cache_key(catalog: Catalog, watch_ids: list) -> str:
    latest = str(catalog.objects["EPOCH"].max())
    blob = json.dumps([catalog.source, latest, len(catalog.objects), sorted(watch_ids)], default=str)
    return hashlib.sha1(blob.encode()).hexdigest()


def _screen_catalogue(catalog: Catalog, watch_ids: list, weather: dict, force: bool, say) -> dict:
    """Screen the watchlist against the real catalogue (cached on disk per catalogue version)."""
    key = _cache_key(catalog, watch_ids)
    if not force and STATE_CACHE.exists():
        try:
            cached = pickle.loads(STATE_CACHE.read_bytes())
            if cached.get("key") == key:
                return cached
        except Exception:
            pass
    t0 = utc_now()
    source = ObjectSource(catalog.satrecs, t0)
    say(f"Screening {len(watch_ids)} satellites against {len(catalog.objects):,} objects "
        f"(SGP4, next {PROPAGATION_WINDOW_HOURS} h)…")
    conj, near = screen(catalog.objects, source, watch_ids, near_km=NEAR_KM)
    say("Computing collision probabilities…")
    conj = _merge_official(conj, spacetrack_client.fetch_public_cdms())
    conj = LiveRiskAssessor(load_uncertainty_model(), weather).assess(conj, catalog.objects, t0)
    result = {"key": key, "t0": t0, "conjunctions": conj, "near": near,
              "official_cdms": int(conj["OFFICIAL_PC"].notna().sum()) if "OFFICIAL_PC" in conj else 0}
    STATE_CACHE.write_bytes(pickle.dumps(result))
    return result


def run_live(force: bool = False, extra_watch: Optional[list] = None,
             threat_specs: Optional[list] = None, progress=None, rescreen: bool = False) -> LiveState:
    """
    Full live refresh. `force` re-downloads sources (subject to their cache rules),
    `rescreen` recomputes screening even if the catalogue has not changed.
    `threat_specs` is a list of dicts for scenario.create_threat
    (primary_id, hours_to_tca, miss_m, crossing_deg, kind); simulated threats are
    screened separately and added to the real results.
    """
    say = progress or (lambda msg: print(f"[Live] {msg}"))
    say("Loading orbit catalogue…")
    catalog = build_catalog(force=force)
    weather = weather_for()
    watch_ids = catalog.watchlist_ids(extra_watch)
    base = _screen_catalogue(catalog, watch_ids, weather, force or rescreen, say)

    t0 = base["t0"]
    source = ObjectSource(catalog.satrecs, t0)
    specs = [s for s in (threat_specs or []) if s["primary_id"] in catalog.satrecs]
    threats = [create_threat(catalog.objects, source, index=i, horizon_h=PROPAGATION_WINDOW_HOURS, **s)
               for i, s in enumerate(specs)]
    objects, source = with_threats(catalog.objects, source, threats)
    conj, near = base["conjunctions"], base["near"]
    if threats:
        prim = sorted({t.primary_id for t in threats})
        t_conj, t_near = screen(objects, source, prim, only_secondaries=[t.object_id for t in threats], near_km=NEAR_KM)
        if not t_conj.empty:
            t_conj = LiveRiskAssessor(load_uncertainty_model(), weather).assess(t_conj, objects, t0)
            conj = pd.concat([conj, t_conj], ignore_index=True)
        near = pd.concat([near, t_near], ignore_index=True)

    return LiveState(t0, catalog, objects, source, watch_ids, conj, near, weather,
                     base.get("official_cdms", 0), threats, base["key"])


def watchlist_summary(state: LiveState) -> pd.DataFrame:
    """One row per watchlist satellite with its worst upcoming conjunction."""
    conj = state.conjunctions
    rows = []
    for sid in state.watch_ids:
        obj = state.objects.loc[sid]
        mine = conj[conj["PRIMARY_ID"] == sid] if not conj.empty else conj
        base = {"NORAD_CAT_ID": sid, "SATELLITE": obj["OBJECT_NAME"], "ALTITUDE_KM": round(float(obj["PERIGEE_KM"])),
                "CONJUNCTIONS": len(mine)}
        if mine.empty:
            rows.append({**base, "STATUS": "SAFE", "RISK_LEVEL": "NEGLIGIBLE", "MAX_LOG_PC": np.nan,
                         "CLOSEST_KM": np.nan, "WORST_WITH": "—", "WORST_TCA": pd.NaT})
            continue
        worst = mine.sort_values("LOG_PC", ascending=False).iloc[0]
        status = max(mine["STATUS"], key=lambda s: STATUS_ORDER[s])
        rows.append({**base, "STATUS": status, "RISK_LEVEL": worst["RISK_LEVEL"], "MAX_LOG_PC": worst["LOG_PC"],
                     "CLOSEST_KM": mine["MISS_KM"].min(), "WORST_WITH": worst["SECONDARY_NAME"],
                     "WORST_TCA": worst["TCA"]})
    df = pd.DataFrame(rows)
    df["_order"] = df["STATUS"].map(STATUS_ORDER)
    return df.sort_values(["_order", "MAX_LOG_PC"], ascending=[False, False]).drop(columns="_order").reset_index(drop=True)


if __name__ == "__main__":
    import time
    t = time.time()
    st = run_live(force=False)
    print(f"done in {time.time() - t:.0f}s; {len(st.conjunctions)} conjunctions")
    print(watchlist_summary(st).to_string())
