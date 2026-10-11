"""
OrbitGuard AI — Conjunction Screening (SGP4)

Finds close approaches between watchlist satellites ("primaries") and every other
catalogue object over the next PROPAGATION_WINDOW_HOURS.

  1. Altitude pre-filter: two objects can only meet if their perigee–apogee
     ranges overlap (plus a margin).
  2. Coarse pass: SGP4 positions every PROPAGATION_STEP_SECONDS. Within each step
     the relative motion is treated as a straight line, which gives the closest
     approach inside that step without missing fast (≈15 km/s) crossings.
  3. Refinement: Brent minimisation of the exact SGP4 distance around each
     candidate gives the time of closest approach (TCA) and miss distance.

Objects that keep station with a primary (docked vehicles, formation flyers;
relative speed < 0.1 km/s) are skipped: the short-encounter Pc model does not
apply to them.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Optional

import numpy as np
import pandas as pd
from scipy.interpolate import CubicHermiteSpline
from scipy.optimize import minimize_scalar

from config import (SCREENING_DISTANCE_KM, SCREENING_ALTITUDE_PAD_KM,
                    PROPAGATION_WINDOW_HOURS, PROPAGATION_STEP_SECONDS)
from orbit_propagation import sgp4_states, propagate_j2, add_seconds

MIN_RELATIVE_SPEED_KMS = 0.1
CHUNK = 400
# Passes within this distance are kept so a planned burn can be re-checked cheaply
NEAR_KM = 100.0

# offset(seconds) -> (dr, dv) arrays (T,3) added to a primary's SGP4 path (used for burns)
Offset = Callable[[np.ndarray], tuple[np.ndarray, np.ndarray]]


class EphemerisObject:
    """An object without a TLE (e.g. a test-scenario threat), propagated with the J2 model."""

    def __init__(self, state: np.ndarray, t_state: float, horizon_s: float, step_s: float = 20.0):
        self.grid = np.arange(-step_s, horizon_s + 2 * step_s, step_s)
        states = propagate_j2(np.asarray(state, float), t_state, self.grid)
        self._r = CubicHermiteSpline(self.grid, states[:, :3], states[:, 3:], axis=0)
        self._v = self._r.derivative()

    def states(self, seconds: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        s = np.asarray(seconds, float)
        return self._r(s), self._v(s)


@dataclass
class ObjectSource:
    """Position provider for catalogue (SGP4) and ephemeris objects."""
    satrecs: dict
    t0: datetime
    ephemerides: Optional[dict] = None

    def states(self, ids: list, seconds: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        seconds = np.asarray(seconds, float)
        r = np.full((len(ids), len(seconds), 3), np.nan)
        v = np.full_like(r, np.nan)
        eph = self.ephemerides or {}
        sat_idx = [i for i, oid in enumerate(ids) if oid not in eph]
        if sat_idx:
            rr, vv, err = sgp4_states([self.satrecs[ids[i]] for i in sat_idx], self.t0, seconds)
            rr[err != 0], vv[err != 0] = np.nan, np.nan
            r[sat_idx], v[sat_idx] = rr, vv
        for i, oid in enumerate(ids):
            if oid in eph:
                r[i], v[i] = eph[oid].states(seconds)
        return r, v

    def state(self, oid, seconds) -> tuple[np.ndarray, np.ndarray]:
        r, v = self.states([oid], np.atleast_1d(seconds))
        return r[0], v[0]


def _candidates(objects: pd.DataFrame, pid, pad_km: float) -> np.ndarray:
    p = objects.loc[pid]
    ok = ((objects["PERIGEE_KM"] <= p["APOGEE_KM"] + pad_km)
          & (objects["APOGEE_KM"] >= p["PERIGEE_KM"] - pad_km))
    ok &= objects.index != pid
    return objects.index[ok].to_numpy()


def _coarse_hits(dr, dv, step, threshold):
    """(object, sample, distance) where the straight-line closest approach within ±step/2 is under threshold."""
    vv = np.einsum("ktj,ktj->kt", dv, dv)
    tau = np.clip(-np.einsum("ktj,ktj->kt", dr, dv) / np.maximum(vv, 1e-12), -step / 2, step / 2)
    dmin = np.nan_to_num(np.linalg.norm(dr + dv * tau[..., None], axis=2), nan=np.inf)
    idx = np.argwhere(dmin < threshold)
    return idx, dmin[idx[:, 0], idx[:, 1]]


MARGIN_KM = 2.0  # covers curvature of the relative path within one step


def _merge(hits: list, step_s: float) -> list:
    """Merge hits of the same pair in neighbouring samples into (pid, sid, t_first, t_last) events."""
    hits = sorted(hits)
    events = []
    for pid, sid, t in hits:
        if events and events[-1][:2] == (pid, sid) and t - events[-1][3] <= 2 * step_s:
            events[-1] = (pid, sid, events[-1][2], t)
        else:
            events.append((pid, sid, t, t))
    return events


def _refine_events(objects, source, events, step_s, threshold_km, offsets) -> pd.DataFrame:
    rows = []
    for pid, sid, t_first, t_last in events:
        row = refine(source, pid, sid, t_first - step_s, t_last + step_s, offsets.get(pid))
        if row is not None and row["MISS_KM"] < threshold_km and row["REL_SPEED_KMS"] >= MIN_RELATIVE_SPEED_KMS:
            rows.append(row)
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    df["TCA"] = [add_seconds(source.t0, s) for s in df["TCA_S"]]
    df["PRIMARY_NAME"] = objects["OBJECT_NAME"].reindex(df["PRIMARY_ID"]).to_numpy()
    df["SECONDARY_NAME"] = objects["OBJECT_NAME"].reindex(df["SECONDARY_ID"]).to_numpy()
    df["SECONDARY_TYPE"] = objects["OBJECT_TYPE"].reindex(df["SECONDARY_ID"]).to_numpy()
    df["HOURS_TO_TCA"] = df["TCA_S"] / 3600.0
    return df.sort_values(["MISS_KM"]).reset_index(drop=True)


def screen(objects: pd.DataFrame, source: ObjectSource, primary_ids: list,
           horizon_h: float = PROPAGATION_WINDOW_HOURS, step_s: float = PROPAGATION_STEP_SECONDS,
           threshold_km: float = SCREENING_DISTANCE_KM, offsets: Optional[dict[int, Offset]] = None,
           start_s: float = 0.0, only_secondaries: Optional[list] = None,
           near_km: Optional[float] = None):
    """
    Screen primaries against the catalogue. `offsets` shifts a primary's path
    (a planned burn). Returns one row per close approach.

    With `near_km`, also returns every coarse pass nearer than near_km as a
    DataFrame (PRIMARY_ID, SECONDARY_ID, T_S, DIST_KM); `rescreen_near` uses it
    to check a planned burn without screening the whole catalogue again.
    """
    offsets = offsets or {}
    times = np.arange(start_s, horizon_h * 3600.0 + step_s, step_s)
    P, PV = source.states(primary_ids, times)
    for i, pid in enumerate(primary_ids):
        if pid in offsets:
            dr, dv = offsets[pid](times)
            P[i] += dr
            PV[i] += dv

    # Burns shift a path mostly along-track, so the altitude filter keeps the screening margin
    pad = SCREENING_ALTITUDE_PAD_KM + threshold_km
    cand = {pid: (set(only_secondaries) if only_secondaries is not None
                  else set(_candidates(objects, pid, pad)))
            for pid in primary_ids}
    union = sorted(set().union(*cand.values()) - set(primary_ids)) if cand else []
    # Primaries can also meet each other
    union += [pid for pid in primary_ids if any(pid in c for c in cand.values())]

    detect_km = max(threshold_km + MARGIN_KM, near_km or 0.0)
    hits, near = [], []
    for c0 in range(0, len(union), CHUNK):
        ids = union[c0:c0 + CHUNK]
        R, RV = source.states(ids, times)
        id_pos = {oid: k for k, oid in enumerate(ids)}
        for i, pid in enumerate(primary_ids):
            rows = [id_pos[o] for o in ids if o in cand[pid] and o != pid]
            if not rows:
                continue
            idx, dist = _coarse_hits(R[rows] - P[i][None], RV[rows] - PV[i][None], step_s, detect_km)
            for (k, t_idx), d in zip(idx, dist):
                sid, t = ids[rows[k]], times[t_idx]
                if near_km:
                    near.append((pid, sid, t, d))
                if d < threshold_km + MARGIN_KM:
                    hits.append((pid, sid, t))

    df = _refine_events(objects, source, _merge(hits, step_s), step_s, threshold_km, offsets)
    if near_km is None:
        return df
    return df, pd.DataFrame(near, columns=["PRIMARY_ID", "SECONDARY_ID", "T_S", "DIST_KM"])


def rescreen_near(objects: pd.DataFrame, source: ObjectSource, pid, near: pd.DataFrame, offset: Offset,
                  start_s: float, step_s: float = PROPAGATION_STEP_SECONDS,
                  threshold_km: float = SCREENING_DISTANCE_KM) -> pd.DataFrame:
    """
    Close approaches of `pid` after a planned burn (`offset`), checking only passes
    from an earlier `screen(..., near_km=...)` run. A pass can only come within
    threshold if old distance − path shift < threshold, so others are skipped.
    """
    near = near[(near["PRIMARY_ID"] == pid) & (near["T_S"] >= start_s - step_s)]
    if near.empty:
        return pd.DataFrame()
    shift = np.linalg.norm(offset(near["T_S"].to_numpy())[0], axis=1)
    near = near[near["DIST_KM"].to_numpy() - shift < threshold_km + MARGIN_KM]
    hits = list(zip(near["PRIMARY_ID"], near["SECONDARY_ID"], near["T_S"]))
    return _refine_events(objects, source, _merge(hits, step_s), step_s, threshold_km, {pid: offset})


def refine(source: ObjectSource, pid, sid, t_lo: float, t_hi: float,
           offset: Optional[Offset] = None) -> Optional[dict]:
    """Exact TCA between two objects inside [t_lo, t_hi] seconds."""
    def rel(t):
        rp, vp = source.state(pid, t)
        if offset is not None:
            dr, dv = offset(np.atleast_1d(t))
            rp, vp = rp + dr, vp + dv
        rs, vs = source.state(sid, t)
        return rp[0], vp[0], rs[0], vs[0]

    def dist(t):
        rp, _, rs, _ = rel(t)
        d = np.linalg.norm(rs - rp)
        return d if np.isfinite(d) else 1e9

    res = minimize_scalar(dist, bounds=(t_lo, t_hi), method="bounded", options={"xatol": 1e-3})
    rp, vp, rs, vs = rel(res.x)
    if not np.all(np.isfinite(np.concatenate([rp, rs]))):
        return None
    d_rel, v_rel = rs - rp, vs - vp
    R = rp / np.linalg.norm(rp)
    N = np.cross(rp, vp); N /= np.linalg.norm(N)
    T = np.cross(N, R)
    return {
        "PRIMARY_ID": pid, "SECONDARY_ID": sid, "TCA_S": float(res.x),
        "MISS_KM": float(np.linalg.norm(d_rel)), "REL_SPEED_KMS": float(np.linalg.norm(v_rel)),
        "MISS_R_M": float(d_rel @ R * 1000), "MISS_T_M": float(d_rel @ T * 1000), "MISS_N_M": float(d_rel @ N * 1000),
        "P_POS": rp, "P_VEL": vp, "S_POS": rs, "S_VEL": vs,
    }
