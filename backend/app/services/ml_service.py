"""
ML and dataset services for the API.

  * the trained full-CDM XGBoost risk model (collision_model.py, models/orbitguard_model*)
    with SHAP explanations (explainability.py);
  * replay of real ESA CDM events: ESA's risk, the model's prediction and the physics
    engine's recomputation for every CDM of an event. Events come from the model's
    held-out validation split of train_data.csv (complete histories up to closest
    approach); the public test set stops 2 days before TCA, so it is only a fallback;
  * "what-if" recomputation of an ESA CDM's risk with the validated Pc engine;
  * CDM-only manoeuvre estimates (manoeuvre_simulator.py) — ESA events have no
    orbit states, so the full planner cannot be used for them.
"""

import threading
from typing import Optional

import numpy as np
import pandas as pd

from config import (DEFAULT_SPACECRAFT, MANOEUVRE_TARGET_LOG_PC, RISK_THRESHOLD, TEST_DATA_PATH,
                    TRAIN_DATA_PATH)
from risk_engine import level_color, pc_from_cdm, risk_level, risk_status

from .common import clean, num

# Kelvins convention: decisions are taken on the latest CDM at least 2 days before closest approach
DECISION_LEAD_DAYS = 2.0
FEATURE_LABELS = {
    "max_risk_estimate": "Max risk estimate (CDM)", "max_risk_scaling": "Max risk scaling (CDM)",
    "miss_distance": "Miss distance (m)", "log_miss_distance": "log(1 + miss distance)",
    "relative_speed": "Relative speed (m/s)", "time_to_tca": "Time to closest approach (days)",
    "mahalanobis_distance": "Mahalanobis distance", "log_mahalanobis": "log(1 + Mahalanobis distance)",
    "relative_position_r": "Radial miss (m)", "relative_position_t": "Along-track miss (m)",
    "relative_position_n": "Cross-track miss (m)", "c_object_type": "Other object type",
    "t_sigma_r": "Satellite radial σ (m)", "t_sigma_t": "Satellite along-track σ (m)",
    "t_sigma_n": "Satellite cross-track σ (m)", "c_sigma_r": "Other object radial σ (m)",
    "c_sigma_t": "Other object along-track σ (m)", "c_sigma_n": "Other object cross-track σ (m)",
    "combined_uncertainty": "Combined position σ (m)", "risk_scaling_ratio": "Risk estimate / scaling",
    "F10": "Solar flux F10.7", "F3M": "81-day mean F10.7", "SSN": "Sunspot number", "AP": "Geomagnetic Ap",
    "c_position_covariance_det": "Other object covariance size (log det)",
    "t_position_covariance_det": "Satellite covariance size (log det)",
    "c_span": "Other object size (m)", "t_span": "Satellite size (m)",
}


class ModelService:
    def __init__(self):
        self._lock = threading.RLock()
        self._model = None
        self._model_error: Optional[str] = None
        self._explainer = None
        self._cdms: Optional[pd.DataFrame] = None
        self._events: Optional[pd.DataFrame] = None
        self.event_source = ""

    # ── loading ─────────────────────────────────────────────────────────────
    @property
    def model(self):
        with self._lock:
            if self._model is None and self._model_error is None:
                try:
                    from collision_model import CollisionRiskModel
                    m = CollisionRiskModel(use_gpu=False)   # inference runs on the CPU
                    m.load()
                    self._model = m
                except Exception as e:
                    self._model_error = f"{type(e).__name__}: {e}"
            return self._model

    def require_model(self):
        if self.model is None:
            raise FileNotFoundError(f"CDM risk model unavailable ({self._model_error}). "
                                    "Train it with `python collision_model.py`.")
        return self._model

    @property
    def explainer(self):
        with self._lock:
            if self._explainer is None:
                from explainability import RiskExplainer
                m = self.require_model()
                self._explainer = RiskExplainer(m.model, m.feature_names)
            return self._explainer

    @staticmethod
    def dataset_status() -> dict:
        return {"train": TRAIN_DATA_PATH.exists(), "test": TEST_DATA_PATH.exists(),
                "folder": str(TEST_DATA_PATH.parent)}

    def cdm_frame(self) -> pd.DataFrame:
        """
        CDMs of the replayable ESA events, with the model's prediction (PRED) and the
        physics engine's recomputation (PHYS).
        """
        with self._lock:
            if self._cdms is None:
                m = self.require_model()
                if TRAIN_DATA_PATH.exists():
                    from collision_model import split_by_event
                    from config import GROUP_COLUMN
                    train = pd.read_csv(TRAIN_DATA_PATH)
                    _, val_idx = split_by_event(train[GROUP_COLUMN].values)   # same split as training
                    df = train.iloc[val_idx].reset_index(drop=True)
                    self.event_source = ("held-out validation events from train_data.csv (event-grouped split "
                                         "the trees were not fitted on; full CDM history up to closest approach)")
                elif TEST_DATA_PATH.exists():
                    df = pd.read_csv(TEST_DATA_PATH)
                    self.event_source = "ESA test set (its CDMs stop 2 days before closest approach)"
                else:
                    raise FileNotFoundError("ESA dataset not found in Dataset/ — download train_data.zip and "
                                            "test_data.csv from https://kelvins.esa.int/collision-avoidance-challenge/data/")
                df["PRED"] = m.predict(m.preprocessor.transform(df))
                ok = df[["t_sigma_r", "c_sigma_r"]].notna().all(axis=1)
                df["PHYS"] = np.nan
                df.loc[ok, "PHYS"] = pc_from_cdm(df[ok])
                self._cdms = df
            return self._cdms

    # ── ESA events ──────────────────────────────────────────────────────────
    @staticmethod
    def _decision_index(rows: pd.DataFrame):
        """Index of the latest CDM issued at least DECISION_LEAD_DAYS before TCA (else the earliest CDM)."""
        early = rows[rows["time_to_tca"] >= DECISION_LEAD_DAYS]
        return early["time_to_tca"].idxmin() if not early.empty else rows["time_to_tca"].idxmax()

    def event_table(self) -> pd.DataFrame:
        with self._lock:
            if self._events is None:
                df = self.cdm_frame()
                recs = []
                for eid, g in df.groupby("event_id"):
                    final = g.loc[g["time_to_tca"].idxmin()]
                    dec = g.loc[self._decision_index(g)]
                    recs.append({"event_id": int(eid), "n_cdms": len(g), "mission_id": int(final["mission_id"]),
                                 "other_object_type": final["c_object_type"],
                                 "final_tca_days": float(final["time_to_tca"]),
                                 "final_risk": float(final["risk"]), "final_pred": float(final["PRED"]),
                                 "decision_tca_days": float(dec["time_to_tca"]),
                                 "decision_risk": float(dec["risk"]), "decision_pred": float(dec["PRED"]),
                                 "max_risk": float(g["risk"].max()), "max_ap": float(g["AP"].max()),
                                 "f10": float(final["F10"]), "miss_m": float(final["miss_distance"])})
                self._events = pd.DataFrame(recs).set_index("event_id")
            return self._events

    def esa_events(self) -> list:
        """A few real ESA events chosen to show different situations, picked from the data itself."""
        ev = self.event_table()
        multi = ev[ev["n_cdms"] >= 3]
        picks = []

        def take(df, category, title, description, n=1):
            for eid, r in df.head(n).iterrows():
                if eid not in [p["event_id"] for p in picks]:
                    picks.append({"event_id": int(eid), "category": category, "title": title,
                                  "description": description, **r.to_dict()})

        thr = RISK_THRESHOLD
        take(multi[(multi["final_risk"] >= thr) & (multi["final_pred"] >= thr)].sort_values("final_risk", ascending=False),
             "HIGH_RISK", "High-risk encounter, flagged by the model",
             f"ESA's final risk is above the 10^{thr} alert line and the model flags it too.", n=2)
        take(multi[(multi["decision_risk"] >= thr) & (multi["final_risk"] < -6.0)].sort_values("decision_risk", ascending=False),
             "FALSE_ALARM", "Early alert that faded",
             "Risk was above the alert line two days out, then fell as later CDMs refined the orbits.")
        take(multi[(multi["decision_risk"] < thr - 1.0) & (multi["final_risk"] >= thr)].sort_values("final_risk", ascending=False),
             "LATE_RISE", "Risk that rose late",
             "Looked low two days out and crossed the alert line only in the final CDMs.")
        take(multi[multi["final_risk"] > -10].sort_values("max_ap", ascending=False),
             "SPACE_WEATHER", "Encounter during a geomagnetic storm",
             "Highest geomagnetic activity (Ap) among non-negligible events; storms raise drag and orbit uncertainty.")
        take(multi[multi["final_risk"] <= -10].sort_values("n_cdms", ascending=False),
             "NEGLIGIBLE", "Routine pass", "Many CDMs, risk negligible throughout.")
        for p in picks:
            p["final_level"] = risk_level(p["final_risk"])
            p["final_level_color"] = level_color(p["final_level"])
            p["source"] = self.event_source
        return clean(picks)

    def _event_rows(self, event_id: int) -> pd.DataFrame:
        df = self.cdm_frame()
        rows = df[df["event_id"] == event_id]
        if rows.empty:
            raise KeyError(f"ESA event {event_id} is not among the replayable events")
        return rows.sort_values("time_to_tca", ascending=False)

    def _shap(self, X_row: np.ndarray, raw: pd.Series, top: int = 10) -> dict:
        ex = self.explainer.explain_single(X_row)
        feats = []
        for f in ex["top_features"][:top]:
            value = raw[f["feature"]] if f["feature"] == "c_object_type" else f["value"]
            feats.append({"feature": f["feature"], "label": FEATURE_LABELS.get(f["feature"], f["feature"]),
                          "value": value, "shap_value": f["shap_value"],
                          "direction": "INCREASES_RISK" if f["shap_value"] > 0 else "REDUCES_RISK"})
        total = sum(abs(f["shap_value"]) for f in feats) or 1.0
        for f in feats:
            f["share_of_top"] = abs(f["shap_value"]) / total
        return {"base_value": ex["base_value"], "prediction": ex["prediction"], "features": feats,
                "narrative": self.explainer.generate_narrative(X_row)}

    def replay(self, event_id: int) -> dict:
        """Every CDM of one ESA event, plus the SHAP explanation of the decision CDM."""
        m = self.require_model()
        rows = self._event_rows(event_id)
        X = m.preprocessor.transform(rows)
        idx = self._decision_index(rows)
        pos = list(rows.index).index(idx)
        dec = rows.loc[idx]
        series = [{"time_to_tca_days": r.time_to_tca, "hours_to_tca": r.time_to_tca * 24.0, "esa_risk": r.risk,
                   "model_risk": r.PRED, "physics_risk": num(r.PHYS), "miss_distance_m": r.miss_distance,
                   "relative_speed_m_s": r.relative_speed, "is_decision_cdm": i == idx}
                  for i, r in zip(rows.index, rows.itertuples())]
        final = rows.loc[rows["time_to_tca"].idxmin()]
        level = risk_level(float(dec["PRED"]))
        return clean({
            "event_id": event_id, "mission_id": dec["mission_id"], "n_cdms": len(rows), "source": self.event_source,
            "other_object_type": dec["c_object_type"],
            "decision_cdm": {
                "time_to_tca_days": dec["time_to_tca"], "esa_risk": dec["risk"], "model_risk": dec["PRED"],
                "physics_risk": num(dec["PHYS"]), "risk_level": level, "risk_color": level_color(level),
                "status": risk_status(level, float(dec["miss_distance"]) / 1000.0),
                "miss_distance_m": dec["miss_distance"], "relative_speed_m_s": dec["relative_speed"],
                "radial_miss_m": dec["relative_position_r"], "along_track_miss_m": dec["relative_position_t"],
                "cross_track_miss_m": dec["relative_position_n"],
                "sigma_m": {p: {c: num(dec[f"{p}_sigma_{c}"]) for c in "rtn"} for p in ("t", "c")},
                "space_weather": {k: num(dec[k]) for k in ("F10", "F3M", "SSN", "AP")},
            },
            "final_cdm": {"time_to_tca_days": final["time_to_tca"], "esa_risk": final["risk"],
                          "model_risk": final["PRED"], "risk_level": risk_level(float(final["risk"]))},
            "shap": self._shap(X[pos], dec),
            "series": series,
            "model_note": ("The CDM model predicts each CDM's own risk value (it reads the CDM's max-risk "
                           "fields), so it explains a CDM rather than forecasting the final risk."),
        })

    # ── prediction on a raw CDM ─────────────────────────────────────────────
    def predict_cdm(self, cdm: dict, event_id: str = "custom") -> dict:
        """Model risk and SHAP for one CDM given as raw dataset columns; missing columns use training medians."""
        m = self.require_model()
        df = pd.DataFrame([cdm])
        known = set(m.preprocessor.feature_columns)
        X = m.preprocessor.transform(df)
        pred = float(m.predict(X)[0])
        level = risk_level(pred)
        physics = None
        need = ["relative_position_r", "relative_position_t", "relative_position_n", "relative_velocity_r",
                "relative_velocity_t", "relative_velocity_n", "t_j2k_sma", "t_span", "c_span"] + \
               [f"{p}_sigma_{c}" for p in "tc" for c in "rtn"]
        if all(c in df and pd.notna(df[c].iloc[0]) for c in need):
            full = df.copy()
            for c in ("t_ct_r", "t_cn_r", "t_cn_t", "c_ct_r", "c_cn_r", "c_cn_t"):  # correlations default to 0
                full[c] = pd.to_numeric(full[c], errors="coerce").fillna(0.0) if c in full else 0.0
            physics = float(pc_from_cdm(full)[0])
        miss_km = float(cdm["miss_distance"]) / 1000.0 if "miss_distance" in cdm else np.inf
        return clean({"event_id": event_id, "predicted_log_pc": pred, "predicted_pc": 10 ** pred,
                      "risk_level": level, "risk_color": level_color(level), "status": risk_status(level, miss_km),
                      "physics_log_pc": physics, "columns_given": sorted(set(cdm) & known),
                      "columns_filled_with_training_medians": len(known - set(cdm)),
                      "shap": self._shap(X[0], df.iloc[0])})

    # ── what-if on an ESA CDM ───────────────────────────────────────────────
    def what_if(self, event_id: int, miss_scale: float = 1.0, sigma_scale: float = 1.0, hbr_scale: float = 1.0) -> dict:
        """Recompute the decision CDM's risk with the physics engine after scaling miss, uncertainty or size."""
        rows = self._event_rows(event_id)
        row = rows.loc[[self._decision_index(rows)]]
        if row[["t_sigma_r", "c_sigma_r"]].isna().any(axis=None):
            raise ValueError("This CDM has no covariance, so its risk cannot be recomputed")
        mod = row.copy()
        for c in ("relative_position_r", "relative_position_t", "relative_position_n", "miss_distance"):
            mod[c] = mod[c] * miss_scale
        for p in "tc":
            for c in "rtn":
                mod[f"{p}_sigma_{c}"] = mod[f"{p}_sigma_{c}"] * sigma_scale
            mod[f"{p}_span"] = mod[f"{p}_span"] * hbr_scale

        def assess(df):
            lp = float(pc_from_cdm(df)[0])
            level = risk_level(lp)
            return {"log_pc": lp, "pc": 10 ** lp, "risk_level": level,
                    "status": risk_status(level, float(df["miss_distance"].iloc[0]) / 1000.0),
                    "miss_distance_m": float(df["miss_distance"].iloc[0]),
                    "hard_body_radius_m": float((df["t_span"].iloc[0] + df["c_span"].iloc[0]) / 2.0)}

        return clean({"event_id": event_id, "esa_risk": float(row["risk"].iloc[0]),
                      "scales": {"miss": miss_scale, "sigma": sigma_scale, "hard_body_radius": hbr_scale},
                      "baseline": assess(row), "modified": assess(mod)})

    # ── CDM-only manoeuvre estimate ─────────────────────────────────────────
    def simulate_manoeuvre(self, event_id: int, mass_kg: Optional[float] = None, isp_s: Optional[float] = None) -> dict:
        """ΔV trade-off for an ESA event from manoeuvre_simulator (analytic, uses only CDM fields)."""
        from manoeuvre_simulator import ManoeuvreSimulator
        m = self.require_model()
        rows = self._event_rows(event_id)
        row = rows.loc[[self._decision_index(rows)]]
        X = m.preprocessor.transform(row)[0]
        sim = ManoeuvreSimulator(predict_fn=m.predict, spacecraft_mass_kg=mass_kg or DEFAULT_SPACECRAFT["mass_kg"],
                                 isp_s=isp_s or DEFAULT_SPACECRAFT["isp_s"])
        report = sim.analyse_conjunction(X, m.feature_names, event_id=str(event_id),
                                         original_risk=float(row["risk"].iloc[0]))
        curves: dict[str, list] = {}
        for r in sorted(report.results, key=lambda r: r.delta_v_ms):
            curves.setdefault(r.direction, []).append({
                "dv_ms": r.delta_v_ms, "residual_log_pc": r.residual_risk, "new_miss_km": r.new_miss_distance_km,
                "fuel_kg": r.delta_v_fuel_kg, "risk_reduction_pct": r.risk_reduction_pct,
                "recommendation": r.recommendation,
                "meets_target": r.residual_risk <= MANOEUVRE_TARGET_LOG_PC})
        meeting = [r for r in report.results if r.residual_risk <= MANOEUVRE_TARGET_LOG_PC]
        best = min(meeting, key=lambda r: r.delta_v_fuel_kg) if meeting else report.best_option
        return clean({
            "event_id": event_id, "original_log_pc": report.original_risk,
            "original_miss_km": report.original_miss_distance_km, "time_to_tca_hours": report.time_to_tca_hours,
            "no_manoeuvre_justified": report.no_manoeuvre_justified, "target_log_pc": MANOEUVRE_TARGET_LOG_PC,
            "best": None if best is None else {
                "direction": best.direction, "dv_ms": best.delta_v_ms, "fuel_kg": best.delta_v_fuel_kg,
                "residual_log_pc": best.residual_risk, "new_miss_km": best.new_miss_distance_km,
                "meets_target": best.residual_risk <= MANOEUVRE_TARGET_LOG_PC},
            "curves": curves,
            "spacecraft": {"mass_kg": sim.spacecraft_mass_kg, "isp_s": sim.isp_s},
            "method": ("Analytic CDM-only estimate (manoeuvre_simulator.py): Gaussian miss-distance model with "
                       "the CDM's combined uncertainty. Live conjunctions use the full J2 manoeuvre planner."),
        })


ml_service = ModelService()
