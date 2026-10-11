"""
OrbitGuard AI — Orbit propagation helpers

* SGP4 states for catalogue objects (TEME frame, km and km/s).
* A numerical two-body + J2 propagator used to work out how a burn changes a
  trajectory. Burns are applied differentially: the new path is
      SGP4 path + (numerical path with burn − numerical path without burn),
  so the SGP4 catalogue orbit stays the reference and only the burn's effect
  comes from the numerical model.
"""

from datetime import datetime, timedelta, timezone

import numpy as np
from scipy.integrate import solve_ivp
from sgp4.api import SatrecArray, jday

MU = 398600.4418        # km^3/s^2
R_EARTH = 6378.137      # km
J2 = 1.08262668e-3


def to_jd(t0: datetime, seconds: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    jd0, fr0 = jday(t0.year, t0.month, t0.day, t0.hour, t0.minute, t0.second + t0.microsecond * 1e-6)
    fr = fr0 + np.asarray(seconds, float) / 86400.0
    return np.full_like(fr, jd0), fr


def sgp4_states(satrecs: list, t0: datetime, seconds: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Positions (n,T,3), velocities (n,T,3) and error codes (n,T) for many Satrecs."""
    jd, fr = to_jd(t0, seconds)
    err, r, v = SatrecArray(satrecs).sgp4(jd, fr)
    return r, v, err


def sgp4_state(satrec, t0: datetime, seconds) -> tuple[np.ndarray, np.ndarray]:
    """Position/velocity (T,3) of one Satrec."""
    secs = np.atleast_1d(np.asarray(seconds, float))
    r, v, _ = sgp4_states([satrec], t0, secs)
    return r[0], v[0]


def _rhs(_t, x):
    r = x[:3]
    rn = np.linalg.norm(r)
    z2 = (r[2] / rn) ** 2
    k = 1.5 * J2 * MU * R_EARTH ** 2 / rn ** 5
    a = -MU * r / rn ** 3 + k * r * np.array([5 * z2 - 1, 5 * z2 - 1, 5 * z2 - 3])
    return np.concatenate([x[3:], a])


def propagate_j2(state0: np.ndarray, t_start: float, t_eval: np.ndarray) -> np.ndarray:
    """
    Propagate a TEME state (km, km/s) from t_start to each time in t_eval
    (seconds, may lie before or after t_start). Returns (T,6).
    """
    t_eval = np.asarray(t_eval, float)
    out = np.empty((len(t_eval), 6))
    for mask, end in ((t_eval >= t_start, t_eval.max(initial=t_start)), (t_eval < t_start, t_eval.min(initial=t_start))):
        if not mask.any():
            continue
        if end == t_start:
            out[mask] = state0
            continue
        ts = t_eval[mask]
        order = np.argsort(ts) if end > t_start else np.argsort(-ts)
        sol = solve_ivp(_rhs, (t_start, end), state0, t_eval=ts[order], rtol=1e-11, atol=1e-9, method="DOP853")
        res = np.empty((len(ts), 6))
        res[order] = sol.y.T
        out[mask] = res
    return out


def rtn_basis(r: np.ndarray, v: np.ndarray) -> np.ndarray:
    """3x3 matrix with columns R, T, N for one state."""
    R = r / np.linalg.norm(r)
    N = np.cross(r, v)
    N /= np.linalg.norm(N)
    return np.stack([R, np.cross(N, R), N], axis=1)


def burn_deviation(state_b: np.ndarray, t_burn: float, dv_rtn_ms: np.ndarray, t_eval: np.ndarray) -> np.ndarray:
    """
    Position change (T,3) in km at times t_eval (≥ t_burn) caused by an impulsive
    burn dv_rtn_ms (m/s, RTN of the state at the burn), from the J2 model.
    """
    t_eval = np.asarray(t_eval, float)
    dv = rtn_basis(state_b[:3], state_b[3:]) @ (np.asarray(dv_rtn_ms, float) / 1000.0)
    after = t_eval >= t_burn
    dev = np.zeros((len(t_eval), 3))
    if after.any():
        nominal = propagate_j2(state_b, t_burn, t_eval[after])
        burned = propagate_j2(state_b + np.concatenate([np.zeros(3), dv]), t_burn, t_eval[after])
        dev[after] = burned[:, :3] - nominal[:, :3]
    return dev


def burn_sensitivity(state_b: np.ndarray, t_burn: float, t_eval: np.ndarray, eps_ms: float = 0.01) -> np.ndarray:
    """
    (T,6,3) matrix S so that state change ≈ S @ dv_rtn (dv in m/s; position
    change in km, velocity change in km/s). Built from three small
    finite-difference burns; burn effects are linear for the small ΔV used in
    collision avoidance (checked in validate.py).
    """
    t_eval = np.asarray(t_eval, float)
    after = t_eval >= t_burn
    S = np.zeros((len(t_eval), 6, 3))
    if not after.any():
        return S
    nominal = propagate_j2(state_b, t_burn, t_eval[after])
    basis = rtn_basis(state_b[:3], state_b[3:])
    for k in range(3):
        dv = basis[:, k] * eps_ms / 1000.0
        burned = propagate_j2(state_b + np.concatenate([np.zeros(3), dv]), t_burn, t_eval[after])
        S[after, :, k] = (burned - nominal) / eps_ms
    return S


def burn_offset(state_b: np.ndarray, t_burn: float, dv_rtn_ms: np.ndarray, t_end: float, step_s: float = 20.0):
    """
    Callable seconds -> (dr, dv) giving the change of a trajectory (km, km/s) caused
    by an impulsive burn; zero before the burn. The change is propagated once on a
    grid up to t_end and interpolated (cubic Hermite), so it is cheap to evaluate
    many times while screening the planned path.
    """
    from scipy.interpolate import CubicHermiteSpline

    dv = rtn_basis(state_b[:3], state_b[3:]) @ (np.asarray(dv_rtn_ms, float) / 1000.0)
    burned_state = state_b + np.concatenate([np.zeros(3), dv])
    grid = np.arange(t_burn, max(t_end, t_burn + step_s) + step_s, step_s)
    diff = propagate_j2(burned_state, t_burn, grid) - propagate_j2(state_b, t_burn, grid)
    spline = CubicHermiteSpline(grid, diff[:, :3], diff[:, 3:], axis=0)
    dspline = spline.derivative()

    def offset(seconds: np.ndarray):
        seconds = np.asarray(seconds, float)
        dr, dvv = np.zeros((len(seconds), 3)), np.zeros((len(seconds), 3))
        after = seconds >= t_burn
        if after.any():
            s = np.minimum(seconds[after], grid[-1])
            dr[after], dvv[after] = spline(s), dspline(s)
        return dr, dvv

    return offset


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def add_seconds(t0: datetime, seconds: float) -> datetime:
    return t0 + timedelta(seconds=float(seconds))
