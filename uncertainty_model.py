"""
OrbitGuard AI — Orbit Uncertainty Model (ML)

Public orbit data (GP/TLE from CelesTrak or Space-Track) has no covariance, but
collision probability depends on it. This model learns, from 162K ESA conjunction
data messages, how position uncertainty depends on:

    time to closest approach, time since the last observation, altitude,
    inclination, eccentricity, object type, object size, and space weather
    (F10.7 solar flux, its 81-day mean, sunspot number, Ap geomagnetic index).

It predicts, for one object, log10 of the 1-sigma position uncertainty in the
radial / along-track / cross-track directions (metres) and the three correlation
coefficients between them. Six GPU XGBoost regressors, one per output.

Train:  python uncertainty_model.py
"""

import json
import time
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb

from config import MODEL_DIR, TRAIN_DATA_PATH, TEST_DATA_PATH

UNCERTAINTY_DIR = MODEL_DIR / "uncertainty"
OBJECT_TYPE_CODES = {"PAYLOAD": 0, "ROCKET BODY": 1, "DEBRIS": 2, "UNKNOWN": 3, "TBA": 3}
WEATHER = ["F10", "F3M", "SSN", "AP"]
FEATURES = ["time_to_tca", "obs_age", "h_per", "h_apo", "inc", "ecc", "otype", "span"] + WEATHER
SIGMA_TARGETS = ["log_sigma_r", "log_sigma_t", "log_sigma_n"]
CORR_TARGETS = ["corr_tr", "corr_nr", "corr_nt"]
# CDMs use ~1 Earth radius (6.4e7 m) as a "no information" placeholder sigma
PLACEHOLDER_LOG_SIGMA = 7.0

PARAMS = dict(n_estimators=600, max_depth=7, learning_rate=0.05, subsample=0.8,
              colsample_bytree=0.9, min_child_weight=5, tree_method="hist", random_state=42)


def cdm_object_rows(df: pd.DataFrame, prefix: str) -> pd.DataFrame:
    """One feature/target row per CDM for the target ('t') or chaser ('c') object."""
    otype = 0 if prefix == "t" else df["c_object_type"].map(OBJECT_TYPE_CODES).fillna(3)
    out = pd.DataFrame({
        "time_to_tca": df["time_to_tca"],
        "obs_age": df[f"{prefix}_time_lastob_end"],
        "h_per": df[f"{prefix}_h_per"],
        "h_apo": df[f"{prefix}_h_apo"],
        "inc": df[f"{prefix}_j2k_inc"],
        "ecc": df[f"{prefix}_j2k_ecc"],
        "otype": otype,
        "span": df[f"{prefix}_span"],
    })
    for w in WEATHER:
        out[w] = df[w]
    for c in "rtn":
        out[f"log_sigma_{c}"] = np.log10(df[f"{prefix}_sigma_{c}"].clip(lower=1e-3))
    out["corr_tr"] = df[f"{prefix}_ct_r"].clip(-1, 1)
    out["corr_nr"] = df[f"{prefix}_cn_r"].clip(-1, 1)
    out["corr_nt"] = df[f"{prefix}_cn_t"].clip(-1, 1)
    return out


def _usable(rows: pd.DataFrame) -> pd.DataFrame:
    rows = rows.dropna(subset=SIGMA_TARGETS + CORR_TARGETS)
    return rows[(rows[SIGMA_TARGETS] < PLACEHOLDER_LOG_SIGMA).all(axis=1)]


class UncertaintyModel:
    def __init__(self):
        self.models: dict[str, xgb.XGBRegressor] = {}
        self.metrics: dict = {}

    # ── training ────────────────────────────────────────────────────────────
    def train(self, train_df: pd.DataFrame, test_df: pd.DataFrame, use_gpu: bool = True) -> dict:
        rows = _usable(pd.concat([cdm_object_rows(train_df, "t"), cdm_object_rows(train_df, "c")]))
        test_rows = _usable(pd.concat([cdm_object_rows(test_df, "t"), cdm_object_rows(test_df, "c")]))
        print(f"[Uncertainty] training on {len(rows):,} object-rows, testing on {len(test_rows):,}")

        start = time.time()
        for target in SIGMA_TARGETS + CORR_TARGETS:
            params = {**PARAMS, "device": "cuda" if use_gpu else "cpu"}
            m = xgb.XGBRegressor(**params)
            m.fit(rows[FEATURES], rows[target])
            m.set_params(device="cpu")
            self.models[target] = m

        pred = self.predict(test_rows)
        # Baseline: median of the training data for each object type
        medians = rows.groupby("otype")[SIGMA_TARGETS + CORR_TARGETS].median()
        base = medians.reindex(test_rows["otype"]).to_numpy()
        self.metrics = {"training_time_seconds": time.time() - start, "n_train_rows": len(rows),
                        "n_test_rows": len(test_rows)}
        for i, target in enumerate(SIGMA_TARGETS + CORR_TARGETS):
            err = np.abs(pred[target].to_numpy() - test_rows[target].to_numpy())
            base_err = np.abs(base[:, i] - test_rows[target].to_numpy())
            self.metrics[f"{target}_mae"] = float(err.mean())
            self.metrics[f"{target}_baseline_mae"] = float(np.nanmean(base_err))
        return self.metrics

    # ── inference ───────────────────────────────────────────────────────────
    def predict(self, rows: pd.DataFrame) -> pd.DataFrame:
        X = rows[FEATURES].astype(float)
        out = {t: self.models[t].predict(X) for t in SIGMA_TARGETS + CORR_TARGETS}
        out = pd.DataFrame(out, index=rows.index)
        out[CORR_TARGETS] = out[CORR_TARGETS].clip(-0.99, 0.99)
        return out

    def feature_importance(self) -> pd.DataFrame:
        imp = {t: m.get_booster().get_score(importance_type="gain") for t, m in self.models.items()}
        df = pd.DataFrame(imp).fillna(0.0)
        df.index = [FEATURES[int(k[1:])] if k.startswith("f") and k[1:].isdigit() else k for k in df.index]
        return df

    # ── persistence ─────────────────────────────────────────────────────────
    def save(self, directory: Path = UNCERTAINTY_DIR):
        directory.mkdir(parents=True, exist_ok=True)
        for t, m in self.models.items():
            m.save_model(str(directory / f"{t}.ubj"))
        (directory / "meta.json").write_text(json.dumps({"features": FEATURES, "metrics": self.metrics}, indent=2))

    @classmethod
    def load(cls, directory: Path = UNCERTAINTY_DIR) -> "UncertaintyModel":
        um = cls()
        for t in SIGMA_TARGETS + CORR_TARGETS:
            m = xgb.XGBRegressor()
            m.load_model(str(directory / f"{t}.ubj"))
            um.models[t] = m
        um.metrics = json.loads((directory / "meta.json").read_text()).get("metrics", {})
        return um

    @staticmethod
    def exists(directory: Path = UNCERTAINTY_DIR) -> bool:
        return all((directory / f"{t}.ubj").exists() for t in SIGMA_TARGETS + CORR_TARGETS)


if __name__ == "__main__":
    train_df = pd.read_csv(TRAIN_DATA_PATH)
    test_df = pd.read_csv(TEST_DATA_PATH)
    um = UncertaintyModel()
    metrics = um.train(train_df, test_df)
    um.save()
    print(json.dumps(metrics, indent=2))
    print(f"[Uncertainty] saved to {UNCERTAINTY_DIR}")
