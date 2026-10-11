"""
OrbitGuard AI — Collision Probability Engine (physics)

Computes the probability of collision (Pc) for a close approach with the standard
short-encounter model used in operational conjunction assessment
(Foster/Akella–Alfriend 2D Pc):

  1. Each object's 3x3 position covariance is built in its own RTN frame
     (radial, along-track, cross-track) and rotated into a common frame.
  2. The two covariances are added (independent errors).
  3. Everything is projected onto the encounter plane, perpendicular to the
     relative velocity.
  4. The 2D Gaussian is integrated over a disc whose radius is the combined
     hard-body radius of the two objects.

Validated against the ESA CDM dataset (see validate.py): with the CDM's own
covariance it reproduces ESA's risk values to ~0.03 in log10 Pc.

For live GP/TLE data there is no covariance, so it comes from the ML uncertainty
model (uncertainty_model.py) plus an assumed TLE error term (config.TLE_SIGMA_KM).
"""

from datetime import datetime, timezone
from typing import Optional

import numpy as np
import pandas as pd
from scipy.special import erf

from config import RISK_LEVELS, RISK_COLORS, TLE_SIGMA_KM, REVIEW_MISS_DISTANCE_KM

MU_EARTH_M = 398600.4418e9  # m^3/s^2
LOG_PC_FLOOR = -30.0
_GL_X, _GL_W = np.polynomial.legendre.leggauss(64)

# Dashboard status → path colour in the 3D view
STATUS_COLORS = {"DANGER": "#FF1744", "REVIEW": "#FF9100", "SAFE": "#FFFFFF"}


# ─── Covariance helpers ─────────────────────────────────────────────────────
def covariance_rtn(sig_r, sig_t, sig_n, corr_tr=0.0, corr_nr=0.0, corr_nt=0.0) -> np.ndarray:
    """(n,3,3) position covariance in RTN from sigmas (any length unit) and correlations."""
    sig_r, sig_t, sig_n = map(np.atleast_1d, (sig_r, sig_t, sig_n))
    n = len(sig_r)
    corr_tr, corr_nr, corr_nt = (np.broadcast_to(np.asarray(c, float), (n,)) for c in (corr_tr, corr_nr, corr_nt))
    C = np.zeros((n, 3, 3))
    C[:, 0, 0], C[:, 1, 1], C[:, 2, 2] = sig_r ** 2, sig_t ** 2, sig_n ** 2
    C[:, 0, 1] = C[:, 1, 0] = corr_tr * sig_r * sig_t
    C[:, 0, 2] = C[:, 2, 0] = corr_nr * sig_r * sig_n
    C[:, 1, 2] = C[:, 2, 1] = corr_nt * sig_t * sig_n
    return C


def _unit(v: np.ndarray) -> np.ndarray:
    return v / np.linalg.norm(v, axis=-1, keepdims=True)


def rtn_matrix(pos: np.ndarray, vel: np.ndarray) -> np.ndarray:
    """(n,3,3) matrix whose columns are the R, T, N unit vectors of each state."""
    R = _unit(pos)
    N = _unit(np.cross(pos, vel))
    T = np.cross(N, R)
    return np.stack([R, T, N], axis=2)


def rotate_covariance(C_rtn: np.ndarray, M: np.ndarray) -> np.ndarray:
    return M @ C_rtn @ np.transpose(M, (0, 2, 1))


# ─── 2D probability of collision ────────────────────────────────────────────
def _pc_disc(miss2: np.ndarray, C2: np.ndarray, hbr: np.ndarray) -> np.ndarray:
    """Integrate a 2D Gaussian (mean miss2, covariance C2) over a disc of radius hbr at the origin."""
    w, V = np.linalg.eigh(C2)
    w = np.clip(w, 1e-12, None)
    m = np.einsum("nji,nj->ni", V, miss2)  # miss vector in principal axes
    sx, sy = np.sqrt(w[:, 0]), np.sqrt(w[:, 1])
    xm, ym = m[:, 0], m[:, 1]
    x = _GL_X[None, :] * hbr[:, None]
    half = np.sqrt(np.clip(hbr[:, None] ** 2 - x ** 2, 0, None))
    gx = np.exp(-(x - xm[:, None]) ** 2 / (2 * sx[:, None] ** 2)) / (np.sqrt(2 * np.pi) * sx[:, None])
    gy = 0.5 * (erf((ym[:, None] + half) / (np.sqrt(2) * sy[:, None]))
                - erf((ym[:, None] - half) / (np.sqrt(2) * sy[:, None])))
    return np.clip((gx * gy * _GL_W[None, :]).sum(axis=1) * hbr, 0.0, 1.0)


def encounter_plane(rel_pos: np.ndarray, rel_vel: np.ndarray, C: np.ndarray):
    """Project relative position and covariance onto the plane perpendicular to the relative velocity."""
    vh = _unit(rel_vel)
    xh = rel_pos - np.sum(rel_pos * vh, axis=1, keepdims=True) * vh
    xn = np.linalg.norm(xh, axis=1, keepdims=True)
    helper = np.where(np.abs(vh[:, :1]) < 0.9, np.array([[1.0, 0, 0]]), np.array([[0, 1.0, 0]]))
    fallback = _unit(np.cross(vh, helper))
    xh = np.where(xn > 1e-9, xh / np.maximum(xn, 1e-12), fallback)
    yh = np.cross(vh, xh)
    B = np.stack([xh, yh], axis=1)  # (n,2,3)
    return np.einsum("nij,nj->ni", B, rel_pos), B @ C @ np.transpose(B, (0, 2, 1))


def probability_of_collision(rel_pos, rel_vel, C, hbr) -> np.ndarray:
    """
    Pc for n encounters. rel_pos/rel_vel (n,3) and C (n,3,3) must share one frame
    and length unit; hbr (n,) is the combined hard-body radius in that unit.
    """
    rel_pos, rel_vel = np.atleast_2d(rel_pos).astype(float), np.atleast_2d(rel_vel).astype(float)
    miss2, C2 = encounter_plane(rel_pos, rel_vel, np.asarray(C, float).reshape(-1, 3, 3))
    return _pc_disc(miss2, C2, np.atleast_1d(np.asarray(hbr, float)))


def max_probability_of_collision(rel_pos, rel_vel, C, hbr) -> np.ndarray:
    """Worst-case Pc over a uniform scaling of the covariance (Alfano's maximum-probability idea)."""
    rel_pos, rel_vel = np.atleast_2d(rel_pos).astype(float), np.atleast_2d(rel_vel).astype(float)
    miss2, C2 = encounter_plane(rel_pos, rel_vel, np.asarray(C, float).reshape(-1, 3, 3))
    hbr = np.atleast_1d(np.asarray(hbr, float))
    best = np.zeros(len(hbr))
    for k in np.logspace(-3, 3, 61):
        best = np.maximum(best, _pc_disc(miss2, C2 * k ** 2, hbr))
    return best


def log_pc(pc) -> np.ndarray:
    return np.log10(np.clip(pc, 10.0 ** LOG_PC_FLOOR, 1.0))


# ─── ESA CDM rows (dataset validation) ──────────────────────────────────────
def pc_from_cdm(df: pd.DataFrame, use_correlations: bool = True) -> np.ndarray:
    """
    log10 Pc recomputed from CDM fields. Relative state is in the target's RTN
    frame; the chaser's covariance is in its own RTN frame, rebuilt from the
    target's circular-orbit velocity plus the relative state.
    Hard-body radius = (target span + chaser span) / 2.
    """
    n = len(df)
    rel_p = df[["relative_position_r", "relative_position_t", "relative_position_n"]].to_numpy(float)
    rel_v = df[["relative_velocity_r", "relative_velocity_t", "relative_velocity_n"]].to_numpy(float)
    a = df["t_j2k_sma"].to_numpy(float) * 1000.0
    pos_t = np.stack([a, np.zeros(n), np.zeros(n)], 1)
    vel_t = np.stack([np.zeros(n), np.sqrt(MU_EARTH_M / a), np.zeros(n)], 1)

    def cov(p):
        corr = [df[f"{p}_{k}"].to_numpy(float) if use_correlations else 0.0 for k in ("ct_r", "cn_r", "cn_t")]
        return covariance_rtn(df[f"{p}_sigma_r"].to_numpy(float), df[f"{p}_sigma_t"].to_numpy(float),
                              df[f"{p}_sigma_n"].to_numpy(float), *corr)

    C = cov("t") + rotate_covariance(cov("c"), rtn_matrix(pos_t + rel_p, vel_t + rel_v))
    hbr = (df["t_span"].to_numpy(float) + df["c_span"].to_numpy(float)) / 2.0
    return log_pc(probability_of_collision(rel_p, rel_v, C, hbr))


# ─── Risk levels and dashboard status ──────────────────────────────────────
def risk_level(log_pc_value: float) -> str:
    for level in ("CRITICAL", "HIGH", "MEDIUM", "LOW"):
        if log_pc_value >= RISK_LEVELS[level]:
            return level
    return "NEGLIGIBLE"


def risk_status(level: str, miss_km: float) -> str:
    """DANGER (red) for HIGH/CRITICAL, REVIEW (orange) for MEDIUM or a very close pass, else SAFE (white)."""
    if level in ("CRITICAL", "HIGH"):
        return "DANGER"
    if level == "MEDIUM" or miss_km < REVIEW_MISS_DISTANCE_KM:
        return "REVIEW"
    return "SAFE"


def level_color(level: str) -> str:
    return RISK_COLORS.get(level, "#FFFFFF")


# ─── Live assessment ───────────────────────────────────────────────────────
def tle_sigma_m(days_since_epoch: np.ndarray) -> np.ndarray:
    """(n,3) assumed GP/TLE 1-sigma error in R, T, N (metres) after propagating `days`."""
    d = np.clip(np.asarray(days_since_epoch, float), 0, None)
    return np.stack([(TLE_SIGMA_KM[c][0] + TLE_SIGMA_KM[c][1] * d) * 1000.0 for c in "rtn"], axis=1)


class LiveRiskAssessor:
    """Collision probability for screened conjunctions between catalogue objects."""

    def __init__(self, uncertainty_model=None, weather: Optional[dict] = None):
        self.um = uncertainty_model
        self.weather = weather or {}

    def _object_rows(self, objs: pd.DataFrame, time_to_tca_days: np.ndarray, now: datetime) -> pd.DataFrame:
        from uncertainty_model import OBJECT_TYPE_CODES, WEATHER
        rows = pd.DataFrame({
            "time_to_tca": time_to_tca_days,
            "obs_age": objs["EPOCH_AGE_DAYS"].to_numpy(float),
            "h_per": objs["PERIGEE_KM"].to_numpy(float),
            "h_apo": objs["APOGEE_KM"].to_numpy(float),
            "inc": objs["INCLINATION"].to_numpy(float),
            "ecc": objs["ECCENTRICITY"].to_numpy(float),
            "otype": objs["OBJECT_TYPE"].map(OBJECT_TYPE_CODES).fillna(3).to_numpy(float),
            "span": 2.0 * objs["RADIUS_M"].to_numpy(float),
        })
        for w in WEATHER:
            rows[w] = float(self.weather.get(w, np.nan))
        return rows

    def object_covariance_rtn(self, objs: pd.DataFrame, tca: pd.Series, now: datetime) -> np.ndarray:
        """(n,3,3) position covariance in metres², object's own RTN frame, at TCA."""
        tca_days = ((pd.to_datetime(tca, utc=True) - pd.Timestamp(now)).dt.total_seconds() / 86400.0).to_numpy()
        tle = tle_sigma_m(objs["EPOCH_AGE_DAYS"].to_numpy(float) + tca_days)
        C = covariance_rtn(tle[:, 0], tle[:, 1], tle[:, 2])
        if self.um is not None:
            p = self.um.predict(self._object_rows(objs, tca_days, now))
            C = C + covariance_rtn(10 ** p["log_sigma_r"].to_numpy(), 10 ** p["log_sigma_t"].to_numpy(),
                                   10 ** p["log_sigma_n"].to_numpy(), p["corr_tr"].to_numpy(),
                                   p["corr_nr"].to_numpy(), p["corr_nt"].to_numpy())
        return C

    def combined_covariance(self, conj: pd.DataFrame, objects: pd.DataFrame, now: datetime):
        """Combined position covariance (n,3,3, m², inertial) and hard-body radius (n, m) at each TCA."""
        p_pos = np.stack(conj["P_POS"].to_numpy()) * 1000.0
        p_vel = np.stack(conj["P_VEL"].to_numpy()) * 1000.0
        s_pos = np.stack(conj["S_POS"].to_numpy()) * 1000.0
        s_vel = np.stack(conj["S_VEL"].to_numpy()) * 1000.0
        p_obj = objects.reindex(conj["PRIMARY_ID"].to_numpy())
        s_obj = objects.reindex(conj["SECONDARY_ID"].to_numpy())
        C = (rotate_covariance(self.object_covariance_rtn(p_obj, conj["TCA"], now), rtn_matrix(p_pos, p_vel))
             + rotate_covariance(self.object_covariance_rtn(s_obj, conj["TCA"], now), rtn_matrix(s_pos, s_vel)))
        hbr = p_obj["RADIUS_M"].to_numpy(float) + s_obj["RADIUS_M"].to_numpy(float)
        return C, hbr

    def assess(self, conj: pd.DataFrame, objects: pd.DataFrame, now: Optional[datetime] = None) -> pd.DataFrame:
        """
        Add LOG_PC, LOG_PC_OURS, LOG_PC_MAX, RISK_LEVEL and STATUS to screened conjunctions.
        `conj` needs PRIMARY_ID, SECONDARY_ID, TCA, MISS_KM and states at TCA
        (P_POS/P_VEL/S_POS/S_VEL, km and km/s, common inertial frame). If it has an
        OFFICIAL_PC column (Space-Track public CDM), that value is used where present,
        because it comes from precise orbits with real covariance.
        """
        now = now or datetime.now(timezone.utc)
        out = conj.copy()
        if out.empty:
            for col in ("LOG_PC", "LOG_PC_OURS", "LOG_PC_MAX", "RISK_LEVEL", "STATUS", "PC_SOURCE"):
                out[col] = pd.Series(dtype=float if col.startswith("LOG") else object)
            return out
        C, hbr = self.combined_covariance(out, objects, now)
        rel_pos = (np.stack(out["S_POS"].to_numpy()) - np.stack(out["P_POS"].to_numpy())) * 1000.0
        rel_vel = (np.stack(out["S_VEL"].to_numpy()) - np.stack(out["P_VEL"].to_numpy())) * 1000.0

        out["LOG_PC_OURS"] = log_pc(probability_of_collision(rel_pos, rel_vel, C, hbr))
        out["LOG_PC_MAX"] = log_pc(max_probability_of_collision(rel_pos, rel_vel, C, hbr))
        out["LOG_PC"] = out["LOG_PC_OURS"]
        out["PC_SOURCE"] = "OrbitGuard (TLE + ML uncertainty)"
        if "OFFICIAL_PC" in out:
            has = out["OFFICIAL_PC"].notna()
            out.loc[has, "LOG_PC"] = log_pc(out.loc[has, "OFFICIAL_PC"].to_numpy(float))
            out.loc[has, "PC_SOURCE"] = "Space-Track public CDM"
        out["RISK_LEVEL"] = [risk_level(v) for v in out["LOG_PC"]]
        out["STATUS"] = [risk_status(l, m) for l, m in zip(out["RISK_LEVEL"], out["MISS_KM"])]
        return out
