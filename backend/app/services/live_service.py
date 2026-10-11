"""
Live screening for the API.

Runs live_pipeline.run_live() in a background thread and repeats it every
DASHBOARD_REFRESH_INTERVAL seconds (the pipeline only re-screens when new orbit
data arrives, otherwise it reuses its disk cache). HIGH/CRITICAL conjunctions
get avoidance plans from manoeuvre_planner in a second worker thread, and
operator accept/decline decisions go to decisions.py — the same audit log the
Streamlit dashboard uses.
"""

import json
import math
import queue
import threading
import time
from dataclasses import replace
from datetime import datetime, timezone
from typing import Optional

import numpy as np
import pandas as pd

import decisions
from config import (DASHBOARD_REFRESH_INTERVAL, DEFAULT_SPACECRAFT, MANOEUVRE_TARGET_LOG_PC,
                    MANOEUVRE_TARGET_MISS_KM, PROPAGATION_WINDOW_HOURS, RISK_LEVELS)
from live_pipeline import satellite_status, upcoming, with_decisions
from manoeuvre_planner import G0, conjunction_key
from risk_engine import (STATUS_COLORS, encounter_plane, level_color, log_pc, probability_of_collision,
                         risk_level, risk_status, tle_sigma_m)
from scenario import THREAT_ID_BASE
from space_weather import storm_level

from .common import clean, iso, num

ACTIONS = {"DANGER": "MANEUVER_RECOMMENDED", "REVIEW": "MONITOR", "SAFE": "HOLD", "MITIGATED": "MANEUVER_ACCEPTED"}
STATUS_COLOR = {**STATUS_COLORS, "MITIGATED": "#3DDC97"}
EARTH_RADIUS_KM = 6378.137
EARTH_ROTATION_RAD_S = 7.2921159e-5
UNCERTAINTY_LABELS = {
    "time_to_tca": "Time to closest approach (days)", "obs_age": "Age of the orbit data (days)",
    "h_per": "Perigee altitude (km)", "h_apo": "Apogee altitude (km)", "inc": "Inclination (deg)",
    "ecc": "Eccentricity", "otype": "Object type (0 payload, 1 rocket body, 2 debris, 3 unknown)",
    "span": "Object size (m)", "F10": "Solar flux F10.7 (sfu)", "F3M": "81-day mean F10.7 (sfu)",
    "SSN": "Sunspot number", "AP": "Geomagnetic Ap index",
}


class NotReady(RuntimeError):
    """Live screening has not produced a result yet."""


def _orbit_geometry(r: np.ndarray, v: np.ndarray, gmst: float) -> dict:
    """Right ascension of the ascending node, argument of latitude and sub-satellite point."""
    h = np.cross(r, v)
    node = np.array([-h[1], h[0], 0.0])
    rn = float(np.linalg.norm(r))
    if np.linalg.norm(node) < 1e-9:  # equatorial orbit
        raan, u = 0.0, math.atan2(r[1], r[0])
    else:
        raan = math.atan2(node[1], node[0])
        u = math.acos(float(np.clip(node @ r / (np.linalg.norm(node) * rn), -1, 1)))
        if r[2] < 0:
            u = 2 * math.pi - u
    lon = (math.atan2(r[1], r[0]) - gmst + math.pi) % (2 * math.pi) - math.pi
    return {"raan_deg": math.degrees(raan) % 360, "arg_latitude_deg": math.degrees(u) % 360,
            "lat_deg": math.degrees(math.asin(r[2] / rn)), "lon_deg": math.degrees(lon),
            "altitude_now_km": rn - EARTH_RADIUS_KM, "velocity_km_s": float(np.linalg.norm(v))}


class LiveService:
    def __init__(self):
        self._lock = threading.RLock()
        self.state = None                 # live_pipeline.LiveState
        self.phase = "idle"               # idle → loading → ready | error
        self.refreshing = False
        self.message = "Live screening has not started"
        self.error: Optional[str] = None
        self.updated_at: Optional[datetime] = None
        self.threat: Optional[dict] = None   # test-scenario spec for scenario.create_threat
        self.spacecraft = dict(DEFAULT_SPACECRAFT)
        self.version = ""
        self.plans: dict[str, dict] = {}
        self._plan_q: queue.Queue = queue.Queue()
        self._planner = None
        self._planner_state = None
        self._um_explainers: dict = {}
        self._wake = threading.Event()
        self._rescreen = False
        self._started = False

    # ── lifecycle ───────────────────────────────────────────────────────────
    def start(self):
        """Start the refresh loop and the manoeuvre planning worker (once)."""
        if self._started:
            return
        self._started = True
        threading.Thread(target=self._refresh_loop, name="orbitguard-live", daemon=True).start()
        threading.Thread(target=self._plan_worker, name="orbitguard-planner", daemon=True).start()

    def request_refresh(self, rescreen: bool = False):
        self._rescreen = self._rescreen or rescreen
        self._wake.set()

    def _refresh_loop(self):
        while True:
            rescreen, self._rescreen = self._rescreen, False
            self._wake.clear()
            self.refresh(rescreen)
            self._wake.wait(DASHBOARD_REFRESH_INTERVAL)

    def _progress(self, msg: str):
        self.message = msg
        print(f"[Live] {msg}")

    def refresh(self, rescreen: bool = False):
        """One run of the live pipeline; on failure the last good result keeps being served."""
        from live_pipeline import run_live
        threat = self.threat   # the scenario can change while this run is in progress
        self.refreshing = True
        if self.state is None:
            self.phase = "loading"
        try:
            state = run_live(threat_specs=[threat] if threat else [], progress=self._progress, rescreen=rescreen)
            self.set_state(state, threat)
        except Exception as e:
            self.error = f"{type(e).__name__}: {e}"
            self.message = "Live screening failed" + (" — serving the previous result" if self.state else "")
            self.phase = "ready" if self.state is not None else "error"
            print(f"[Live] {self.error}")
        finally:
            self.refreshing = False

    def set_state(self, state, threat: Optional[dict] = None):
        """Install a new live state (also used by tests with an offline catalogue); `threat` = scenario it used."""
        version = state.key + json.dumps(threat, sort_keys=True, default=str) + str(sorted(state.watch_ids))
        with self._lock:
            self.state = state
            self.phase, self.error, self.updated_at = "ready", None, datetime.now(timezone.utc)
            self.message = f"Screened {len(state.watch_ids)} satellites against {len(state.objects):,} objects"
            if version != self.version:
                self.version, self.plans = version, {}
        for key in self._open_keys(("DANGER",)):
            self.enqueue_plan(key)

    def _require(self):
        if self.state is None:
            raise NotReady(self.error or self.message)
        return self.state

    # ── conjunctions ────────────────────────────────────────────────────────
    def assessed(self, state=None) -> pd.DataFrame:
        """Upcoming conjunctions with operator decisions applied (KEY, DECISION, STATUS incl. MITIGATED)."""
        return with_decisions(upcoming((state or self._require()).conjunctions))

    def _open_keys(self, statuses) -> list:
        conj = self.assessed()
        return [] if conj.empty else conj.loc[conj["STATUS"].isin(statuses), "KEY"].tolist()

    def _row(self, key: str, state=None) -> pd.Series:
        conj = self.assessed(state)
        hit = conj[conj["KEY"] == key] if not conj.empty else conj
        if hit.empty:
            raise KeyError(f"Conjunction {key} is not in the current screening window")
        return hit.iloc[0]

    def conj_dict(self, row: pd.Series) -> dict:
        now = pd.Timestamp.now(tz="UTC")
        tca = pd.Timestamp(row["TCA"])
        key = row["KEY"] if "KEY" in row else conjunction_key(row)
        lp = float(row["LOG_PC"])
        status = str(row["STATUS"])
        return {
            "key": key,
            "primary_norad_id": int(row["PRIMARY_ID"]), "primary_name": row["PRIMARY_NAME"],
            "secondary_norad_id": int(row["SECONDARY_ID"]), "secondary_name": row["SECONDARY_NAME"],
            "secondary_type": row.get("SECONDARY_TYPE") if isinstance(row.get("SECONDARY_TYPE"), str) else "UNKNOWN",
            "simulated": int(row["SECONDARY_ID"]) >= THREAT_ID_BASE,
            "tca_utc": iso(tca), "time_to_tca_hours": (tca - now).total_seconds() / 3600.0,
            "miss_distance_m": float(row["MISS_KM"]) * 1000.0,
            "radial_miss_m": num(row["MISS_R_M"]), "along_track_miss_m": num(row["MISS_T_M"]),
            "cross_track_miss_m": num(row["MISS_N_M"]),
            "relative_velocity_km_s": float(row["REL_SPEED_KMS"]),
            "log_pc": lp, "pc": 10.0 ** lp, "log_pc_ours": num(row.get("LOG_PC_OURS")),
            "log_pc_max": num(row.get("LOG_PC_MAX")), "pc_source": row.get("PC_SOURCE"),
            "official_pc": num(row.get("OFFICIAL_PC")),
            "risk_level": row["RISK_LEVEL"], "risk_color": level_color(row["RISK_LEVEL"]),
            "status": status, "status_color": STATUS_COLOR.get(status, "#FFFFFF"),
            "recommended_action": ACTIONS.get(status, "HOLD"),
            "operator_decision": row.get("DECISION") or None,
            "plan_status": self.plans.get(key, {}).get("status"),
        }

    def conjunctions(self, norad_id: Optional[int] = None, levels: Optional[list] = None,
                     statuses: Optional[list] = None, limit: int = 500) -> list:
        conj = self.assessed()
        if conj.empty:
            return []
        if norad_id is not None:
            conj = conj[conj["PRIMARY_ID"] == norad_id]
        if levels:
            conj = conj[conj["RISK_LEVEL"].isin(levels)]
        if statuses:
            conj = conj[conj["STATUS"].isin(statuses)]
        conj = conj.sort_values("LOG_PC", ascending=False).head(limit)
        return clean([self.conj_dict(r) for _, r in conj.iterrows()])

    # ── satellites and orbits ───────────────────────────────────────────────
    def satellites(self) -> list:
        from orbit_visualizations import gmst_rad
        st = self._require()
        conj = self.assessed(st)
        status, worst = satellite_status(conj, st.watch_ids)
        now = pd.Timestamp.now(tz="UTC")
        now_s = (now - pd.Timestamp(st.t0)).total_seconds()
        R, V = st.source.states(list(st.watch_ids), np.array([now_s]))
        gmst = gmst_rad(now.to_pydatetime())
        out = []
        for i, sid in enumerate(st.watch_ids):
            obj = st.objects.loc[sid]
            mine = conj[conj["PRIMARY_ID"] == sid] if not conj.empty else conj
            w = worst.get(sid)
            if w is None and not mine.empty:
                w = mine.sort_values("LOG_PC", ascending=False).iloc[0]
            geo = _orbit_geometry(R[i, 0], V[i, 0], gmst) if np.all(np.isfinite(R[i, 0])) else {}
            out.append({
                "norad_id": int(sid), "name": obj["OBJECT_NAME"], "owner": obj.get("OWNER"),
                "object_type": obj.get("OBJECT_TYPE"), "manoeuvrable": bool(obj.get("MANOEUVRABLE", False)),
                "altitude_km": (float(obj["PERIGEE_KM"]) + float(obj["APOGEE_KM"])) / 2.0,
                "perigee_km": float(obj["PERIGEE_KM"]), "apogee_km": float(obj["APOGEE_KM"]),
                "inclination_deg": float(obj["INCLINATION"]), "eccentricity": float(obj["ECCENTRICITY"]),
                "period_min": float(obj["PERIOD_MIN"]), "epoch_age_days": float(obj["EPOCH_AGE_DAYS"]),
                "radius_m": float(obj["RADIUS_M"]), **geo,
                "status": status.get(sid, "SAFE"), "status_color": STATUS_COLOR.get(status.get(sid, "SAFE")),
                "risk_level": w["RISK_LEVEL"] if w is not None else "NEGLIGIBLE",
                "conjunctions": int(len(mine)),
                "worst_conjunction": self.conj_dict(w) if w is not None else None,
            })
        return clean(out)

    def orbit(self, norad_id: int, points: int = 120) -> dict:
        """SGP4 path over the next orbit (TEME km, plus latitude / longitude / altitude)."""
        from orbit_visualizations import gmst_rad
        st = self._require()
        if norad_id not in st.objects.index:
            raise KeyError(f"NORAD {norad_id} is not in the catalogue")
        obj = st.objects.loc[norad_id]
        now = pd.Timestamp.now(tz="UTC")
        offsets = np.linspace(0.0, float(obj["PERIOD_MIN"]) * 60.0, max(2, min(points, 2000)))
        r, _ = st.source.states([norad_id], (now - pd.Timestamp(st.t0)).total_seconds() + offsets)
        g0 = gmst_rad(now.to_pydatetime())
        coords = []
        for dt, p in zip(offsets, r[0]):
            if not np.all(np.isfinite(p)):
                continue
            rn = float(np.linalg.norm(p))
            lon = (math.atan2(p[1], p[0]) - g0 - EARTH_ROTATION_RAD_S * dt + math.pi) % (2 * math.pi) - math.pi
            coords.append({"timestamp_utc": iso(now + pd.Timedelta(seconds=float(dt))),
                           "x_km": p[0], "y_km": p[1], "z_km": p[2], "lat_deg": math.degrees(math.asin(p[2] / rn)),
                           "lon_deg": math.degrees(lon), "alt_km": rn - EARTH_RADIUS_KM})
        return clean({"norad_id": int(norad_id), "name": obj["OBJECT_NAME"], "period_min": float(obj["PERIOD_MIN"]),
                      "frame": "TEME", "coordinates": coords})

    # ── physics breakdown and explanation ───────────────────────────────────
    def _encounter(self, row: pd.Series, st=None):
        st = st or self._require()
        assessor = st.assessor()
        C, hbr = assessor.combined_covariance(row.to_frame().T, st.objects, st.t0)
        rel_p = (np.asarray(row["S_POS"], float) - np.asarray(row["P_POS"], float)) * 1000.0
        rel_v = (np.asarray(row["S_VEL"], float) - np.asarray(row["P_VEL"], float)) * 1000.0
        return assessor, C, hbr, rel_p, rel_v

    def _uncertainty_shap(self, um, rows: pd.DataFrame) -> dict:
        """SHAP contributions of each input to the predicted log10 sigma (R, T, N) of one object."""
        import shap
        from uncertainty_model import FEATURES, SIGMA_TARGETS
        X = rows[FEATURES].astype(float)
        out = {}
        for target in SIGMA_TARGETS:
            if target not in self._um_explainers:
                self._um_explainers[target] = shap.TreeExplainer(um.models[target])
            ex = self._um_explainers[target]
            sv = np.asarray(ex.shap_values(X))[0]
            base = float(np.atleast_1d(ex.expected_value)[0])
            feats = sorted(({"feature": f, "label": UNCERTAINTY_LABELS.get(f, f), "value": float(X.iloc[0][f]),
                             "shap_log10": float(s), "factor": float(10 ** s)} for f, s in zip(FEATURES, sv)),
                           key=lambda d: -abs(d["shap_log10"]))
            out[target.replace("log_sigma_", "")] = {"base_log10_m": base, "predicted_log10_m": base + float(sv.sum()),
                                                     "features": feats}
        return out

    def detail(self, key: str) -> dict:
        """Everything behind one conjunction's risk: geometry, covariance, and why the uncertainty is what it is."""
        st = self._require()
        row = self._row(key, st)
        assessor, C, hbr, rel_p, rel_v = self._encounter(row, st)
        miss2, C2 = encounter_plane(rel_p[None], rel_v[None], C)
        eig = np.sqrt(np.clip(np.linalg.eigvalsh(C2[0]), 0, None))
        mahal = float(np.sqrt(miss2[0] @ np.linalg.solve(C2[0], miss2[0])))
        tca = pd.Series([row["TCA"]])
        tca_days = float((pd.Timestamp(row["TCA"]) - pd.Timestamp(st.t0)).total_seconds() / 86400.0)
        objects = []
        for role, oid in (("primary", int(row["PRIMARY_ID"])), ("secondary", int(row["SECONDARY_ID"]))):
            obj = st.objects.loc[[oid]]
            total = np.sqrt(np.diag(assessor.object_covariance_rtn(obj, tca, st.t0)[0]))
            tle = tle_sigma_m(obj["EPOCH_AGE_DAYS"].to_numpy(float) + tca_days)[0]
            entry = {"role": role, "norad_id": oid, "name": obj.iloc[0]["OBJECT_NAME"],
                     "object_type": obj.iloc[0].get("OBJECT_TYPE"), "owner": obj.iloc[0].get("OWNER"),
                     "radius_m": float(obj.iloc[0]["RADIUS_M"]),
                     "epoch_age_days": float(obj.iloc[0]["EPOCH_AGE_DAYS"]),
                     "manoeuvrable": bool(obj.iloc[0].get("MANOEUVRABLE", False)),
                     "sigma_total_m": dict(zip("rtn", total)), "sigma_tle_m": dict(zip("rtn", tle)),
                     "sigma_ml_m": None, "ml_explanation": None}
            if assessor.um is not None:
                rows = assessor._object_rows(obj, np.array([tca_days]), st.t0)
                pred = assessor.um.predict(rows).iloc[0]
                entry["sigma_ml_m"] = {c: 10 ** float(pred[f"log_sigma_{c}"]) for c in "rtn"}
                entry["ml_inputs"] = {f: float(rows.iloc[0][f]) for f in rows.columns}
                entry["ml_explanation"] = self._uncertainty_shap(assessor.um, rows)
            objects.append(entry)
        return clean({
            "conjunction": self.conj_dict(row),
            "encounter": {
                "miss_vector_rtn_m": {"r": row["MISS_R_M"], "t": row["MISS_T_M"], "n": row["MISS_N_M"]},
                "encounter_plane_miss_m": float(np.linalg.norm(miss2[0])),
                "sigma_major_m": float(eig.max()), "sigma_minor_m": float(eig.min()),
                "mahalanobis_distance": mahal, "hard_body_radius_m": float(hbr[0]),
                "log_pc_ours": num(row.get("LOG_PC_OURS")), "log_pc_max": num(row.get("LOG_PC_MAX")),
                "log_pc_used": float(row["LOG_PC"]), "pc_source": row.get("PC_SOURCE"),
                "model": "2D Pc on the encounter plane; covariance = assumed TLE error + ML uncertainty model",
            },
            "objects": objects,
            "space_weather": st.weather,
        })

    def what_if(self, key: str, miss_scale: float = 1.0, sigma_scale: float = 1.0, hbr_scale: float = 1.0) -> dict:
        """Recompute this conjunction's Pc with the real engine after scaling miss distance, uncertainty or size."""
        st = self._require()
        row = self._row(key, st)
        _, C, hbr, rel_p, rel_v = self._encounter(row, st)

        def assess(p, cov, radius):
            lp = float(log_pc(probability_of_collision(p[None], rel_v[None], cov, radius))[0])
            level = risk_level(lp)
            return {"log_pc": lp, "pc": 10 ** lp, "risk_level": level, "status": risk_status(level, np.linalg.norm(p) / 1000),
                    "miss_distance_m": float(np.linalg.norm(p)), "hard_body_radius_m": float(radius[0])}

        return clean({"key": key, "scales": {"miss": miss_scale, "sigma": sigma_scale, "hard_body_radius": hbr_scale},
                      "baseline": assess(rel_p, C, hbr),
                      "modified": assess(rel_p * miss_scale, C * sigma_scale ** 2, hbr * hbr_scale)})

    # ── status ──────────────────────────────────────────────────────────────
    def status(self) -> dict:
        out = {"phase": self.phase, "refreshing": self.refreshing, "message": self.message, "error": self.error,
               "updated_at": self.updated_at, "window_hours": PROPAGATION_WINDOW_HOURS,
               "refresh_interval_s": DASHBOARD_REFRESH_INTERVAL, "test_scenario": self.threat}
        st = self.state
        if st is not None:
            conj = self.assessed(st)
            status, _ = satellite_status(conj, st.watch_ids)
            counts = {s: sum(1 for v in status.values() if v == s) for s in ("DANGER", "REVIEW", "MITIGATED", "SAFE")}
            levels = {lvl: int((conj["RISK_LEVEL"] == lvl).sum()) if not conj.empty else 0 for lvl in RISK_LEVELS}
            wx = dict(st.weather)
            wx["storm_level"] = storm_level(wx.get("kp_max"))
            out.update({"screened_at": st.t0, "catalogue_source": st.catalog.source,
                        "objects_tracked": int(len(st.objects)), "watchlist_size": len(st.watch_ids),
                        "satellite_status_counts": counts, "close_approaches": int(len(conj)),
                        "close_approaches_by_level": levels, "official_cdms_matched": int(st.official_cdms),
                        "space_weather": wx, "simulated_threats": len(st.threats)})
        return clean(out)

    # ── test scenario ───────────────────────────────────────────────────────
    def set_scenario(self, spec: Optional[dict]):
        """Inject (or clear, with None) a simulated threat on a collision course with a watchlist satellite."""
        if spec is not None and self.state is not None and spec["primary_id"] not in self.state.watch_ids:
            raise KeyError(f"NORAD {spec['primary_id']} is not on the watchlist")
        self.threat = spec
        self.request_refresh()

    # ── manoeuvre planning ──────────────────────────────────────────────────
    def enqueue_plan(self, key: str) -> dict:
        with self._lock:
            entry = self.plans.get(key)
            if entry is not None and entry["status"] != "error":
                return entry
            entry = {"status": "queued", "queued_at": time.time()}
            self.plans[key] = entry
            version = self.version
        self._plan_q.put((version, key))
        return entry

    def _get_planner(self, state):
        if self._planner is None or self._planner_state is not state:
            self._planner, self._planner_state = state.planner(self.spacecraft), state
        return self._planner

    def _plan_worker(self):
        while True:
            version, key = self._plan_q.get()
            with self._lock:
                entry, state = self.plans.get(key), self.state
                if entry is None or version != self.version or state is None:
                    continue
            self.compute_plan(key, entry, state)

    def compute_plan(self, key: str, entry: dict, state) -> dict:
        entry.update(status="computing", started_at=time.time())
        try:
            row = self._row(key, state)
            planner = self._get_planner(state)
            plan = planner.plan(row)
            curve = planner.tradeoff_curve(row, plan.recommended) if plan.recommended is not None else []
            entry.update(status="ready", plan=plan, curve=curve, finished_at=time.time())
        except Exception as e:
            entry.update(status="error", error=f"{type(e).__name__}: {e}", finished_at=time.time())
        return entry

    @staticmethod
    def plan_options(plan) -> list:
        """Recommended and alternative first, then the other verified options (same order as the dashboard)."""
        options = [o for o in (plan.recommended, plan.alternative) if o is not None]
        options += [o for o in plan.primary_options + plan.secondary_options
                    if o.verified_miss_km is not None and o not in options][:6]
        return options

    def set_spacecraft(self, spacecraft: dict) -> dict:
        with self._lock:
            self.spacecraft = dict(spacecraft)
            return dict(self.spacecraft)

    def _option_cost(self, dv_ms: float, spacecraft: Optional[dict] = None) -> tuple:
        sc = spacecraft if spacecraft is not None else self.spacecraft
        fuel = sc["mass_kg"] * -math.expm1(-dv_ms / (sc["isp_s"] * G0))
        duration = sc["mass_kg"] * dv_ms / sc["thrust_n"]
        return fuel, duration

    def option_dict(self, o, label: str, spacecraft: Optional[dict] = None) -> dict:
        miss = o.verified_miss_km if o.verified_miss_km is not None else o.new_miss_km
        lp = o.verified_log_pc if o.verified_log_pc is not None else o.new_log_pc
        fuel, duration = self._option_cost(o.dv_ms, spacecraft)
        return {"label": label, "mover_id": o.mover_id, "mover_name": o.mover_name, "role": o.role,
                "burn_time_utc": iso(o.burn_time), "lead_hours": o.lead_hours, "lead_orbits": o.lead_orbits,
                "direction": o.direction, "dv_ms": o.dv_ms, "dv_rtn_ms": list(o.dv_rtn_ms),
                "burn_duration_s": duration, "fuel_kg": fuel, "new_miss_km": miss,
                "new_log_pc": lp, "new_level": risk_level(lp), "verified": o.verified_miss_km is not None,
                "altitude_change_m": o.delta_sma_km * 1000.0, "conflicts": o.conflicts,
                "conflict_checked": o.conflict_checked, "clean": o.clean}

    def plan_view(self, key: str) -> dict:
        row = self._row(key)  # raises KeyError if the conjunction is gone
        entry = self.plans.get(key) or self.enqueue_plan(key)
        spacecraft = dict(self.spacecraft)
        out = {"key": key, "status": entry["status"], "error": entry.get("error"),
               "conjunction": self.conj_dict(row), "decision": decisions.decision_for(key),
               "target": {"log_pc": MANOEUVRE_TARGET_LOG_PC, "miss_km": MANOEUVRE_TARGET_MISS_KM},
               "spacecraft": spacecraft}
        if entry["status"] == "queued":
            out["queue_position"] = sum(1 for e in self.plans.values() if e["status"] == "queued")
        if entry["status"] == "ready":
            plan = entry["plan"]
            options = self.plan_options(plan)
            labels = ["Recommended" if o is plan.recommended else "Alternative" if o is plan.alternative
                      else f"Option {i + 1}" for i, o in enumerate(options)]
            out.update({"summary": plan.summary, "notes": plan.notes,
                        "secondary_manoeuvrable": plan.secondary_manoeuvrable,
                        "secondary_owner": plan.secondary_owner,
                        "options": [self.option_dict(o, lbl, spacecraft) for o, lbl in zip(options, labels)],
                        "tradeoff_curve": [{**p, "fuel_kg": self._option_cost(p["dv_ms"], spacecraft)[0]}
                                           for p in entry.get("curve", [])],
                        "computed_in_s": entry["finished_at"] - entry["started_at"]})
        return clean(out)

    def decide(self, key: str, decision: str, option_index: Optional[int] = None, note: str = "") -> dict:
        entry = self.plans.get(key)
        if entry is None or entry["status"] != "ready":
            raise NotReady("The manoeuvre plan for this conjunction is not ready yet")
        plan = entry["plan"]
        options = self.plan_options(plan)
        option = None
        if option_index is not None:
            if not 0 <= option_index < len(options):
                raise IndexError(f"option_index must be between 0 and {len(options) - 1}")
            option = options[option_index]
            fuel, duration = self._option_cost(option.dv_ms)
            option = replace(option, fuel_kg=fuel, burn_duration_s=duration)
        elif decision == "ACCEPTED":
            raise ValueError("Accepting a plan needs option_index")
        return clean(decisions.record(plan, option, decision, note))


live_service = LiveService()
