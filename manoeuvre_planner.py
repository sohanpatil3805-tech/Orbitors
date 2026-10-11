"""
OrbitGuard AI — Collision Avoidance Manoeuvre Planner

For a HIGH/CRITICAL conjunction it searches for the smallest impulsive burn that
brings the encounter below MANOEUVRE_TARGET_LOG_PC and beyond
MANOEUVRE_TARGET_MISS_KM:

  * burn times: 0.5 … 7.5 orbits before TCA (half-orbit offsets favour radial
    burns, whole orbits along-track burns), never sooner than
    MANOEUVRE_MIN_LEAD_HOURS from now;
  * directions: prograde / retrograde / radial ± / normal ± (RTN frame);
  * the burn's effect comes from a two-body + J2 model (linear sensitivity for
    the search, full nonlinear propagation to verify the chosen burn);
  * the new path is screened against the whole catalogue so a burn that creates
    a new close approach is rejected;
  * if the other object is a working satellite, the same search is run for it,
    so the operator can ask that satellite's owner to move instead.

Output per option: burn time, direction, ΔV, burn duration, fuel, new miss
distance and risk, altitude change, and any new conjunctions it causes.
"""

import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

import numpy as np
import pandas as pd

from config import (MANOEUVRE_TARGET_LOG_PC, MANOEUVRE_TARGET_MISS_KM, MANOEUVRE_MAX_DV,
                    MANOEUVRE_MIN_DV, MANOEUVRE_MIN_LEAD_HOURS, MANOEUVRE_DIRECTIONS, DEFAULT_SPACECRAFT)
from orbit_propagation import MU, burn_sensitivity, burn_offset, add_seconds, rtn_basis
from risk_engine import probability_of_collision, log_pc, risk_level
from screening import ObjectSource, screen, rescreen_near, NEAR_KM, MARGIN_KM
from config import SCREENING_DISTANCE_KM

LEAD_ORBITS = [0.5, 1.0, 1.5, 3.5, 7.5]
DV_GRID = np.logspace(np.log10(MANOEUVRE_MIN_DV), np.log10(MANOEUVRE_MAX_DV), 48)
WINDOW_S = 1200.0   # search ± this around the original TCA for the new closest approach
WINDOW_STEP_S = 1.0
G0 = 9.80665


@dataclass
class BurnOption:
    mover_id: int
    mover_name: str
    role: str                       # "primary" (watchlist satellite) or "secondary" (other object)
    burn_time: datetime
    lead_hours: float
    lead_orbits: float
    direction: str
    dv_ms: float
    dv_rtn_ms: tuple
    burn_duration_s: float
    fuel_kg: float
    new_miss_km: float
    new_log_pc: float
    new_level: str
    verified_miss_km: Optional[float] = None
    verified_log_pc: Optional[float] = None
    delta_sma_km: float = 0.0
    conflicts: list = field(default_factory=list)   # new close approaches caused by this burn
    conflict_checked: bool = False

    @property
    def clean(self) -> bool:
        return self.conflict_checked and not self.conflicts


@dataclass
class ManoeuvrePlan:
    key: str
    primary_id: int
    primary_name: str
    secondary_id: int
    secondary_name: str
    secondary_type: str
    secondary_manoeuvrable: bool
    secondary_owner: Optional[str]
    tca: datetime
    miss_km: float
    log_pc: float
    level: str
    primary_options: list = field(default_factory=list)
    secondary_options: list = field(default_factory=list)
    recommended: Optional[BurnOption] = None
    alternative: Optional[BurnOption] = None
    summary: str = ""
    notes: list = field(default_factory=list)


def conjunction_key(row) -> str:
    return f"{int(row['PRIMARY_ID'])}-{int(row['SECONDARY_ID'])}-{pd.Timestamp(row['TCA']).strftime('%Y%m%dT%H%M%S')}"


def _closest(rel_p: np.ndarray, rel_v: np.ndarray, step: float):
    """Straight-line closest approach within ±step/2 of each sample; returns the best sample per row."""
    vv = np.einsum("...j,...j->...", rel_v, rel_v)
    tau = np.clip(-np.einsum("...j,...j->...", rel_p, rel_v) / np.maximum(vv, 1e-15), -step / 2, step / 2)
    pts = rel_p + rel_v * tau[..., None]
    d = np.linalg.norm(pts, axis=-1)
    idx = np.argmin(d, axis=-1)
    take = lambda a: np.take_along_axis(a, idx[..., None, None], axis=-2)[..., 0, :]
    return np.take_along_axis(d, idx[..., None], axis=-1)[..., 0], take(pts), take(rel_v)


class ManoeuvrePlanner:
    def __init__(self, objects: pd.DataFrame, source: ObjectSource, assessor, t0: datetime,
                 spacecraft: Optional[dict] = None, horizon_h: float = 72.0,
                 baseline: Optional[pd.DataFrame] = None, near: Optional[pd.DataFrame] = None,
                 now: Optional[datetime] = None):
        """
        `baseline` (assessed conjunctions) and `near` (passes within NEAR_KM) come from
        the main screening run; they let a planned burn be checked for new conflicts
        without screening the whole catalogue again. Objects missing from them
        (e.g. a secondary satellite asked to move) are screened on demand.
        """
        self.objects = objects
        self.source = source
        self.assessor = assessor
        self.t0 = t0
        self.sc = {**DEFAULT_SPACECRAFT, **(spacecraft or {})}
        self.horizon_h = horizon_h
        self.now = now          # None = the real clock (burns can't be scheduled in the past)
        self._baseline = {} if baseline is None or baseline.empty else {
            pid: g for pid, g in baseline.groupby("PRIMARY_ID")}
        self._near = {} if near is None or near.empty else {pid: g for pid, g in near.groupby("PRIMARY_ID")}
        self._screened = set(self._near) | set(self._baseline)
        self.time_budget_s = 45.0   # per plan; later conflict checks are skipped once spent
        self._deadline = float("inf")

    def _context(self, mover: int):
        """Baseline conjunctions and near passes for `mover`, screening it if needed."""
        if mover not in self._screened:
            base, near = screen(self.objects, self.source, [mover], horizon_h=self.horizon_h, near_km=NEAR_KM)
            self._baseline[mover] = self.assessor.assess(base, self.objects, self.t0) if not base.empty else base
            self._near[mover] = near
            self._screened.add(mover)
        return self._baseline.get(mover, pd.DataFrame()), self._near.get(mover, pd.DataFrame())

    def _now_s(self) -> float:
        now = pd.Timestamp(self.now) if self.now is not None else pd.Timestamp.now(tz="UTC")
        return (now - pd.Timestamp(self.t0)).total_seconds()

    # ── public ──────────────────────────────────────────────────────────────
    def plan(self, conj: pd.Series, check_conflicts: bool = True) -> ManoeuvrePlan:
        sec = self.objects.loc[conj["SECONDARY_ID"]]
        plan = ManoeuvrePlan(
            key=conjunction_key(conj), primary_id=int(conj["PRIMARY_ID"]), primary_name=conj["PRIMARY_NAME"],
            secondary_id=int(conj["SECONDARY_ID"]), secondary_name=conj["SECONDARY_NAME"],
            secondary_type=str(sec.get("OBJECT_TYPE", "UNKNOWN")),
            secondary_manoeuvrable=bool(sec.get("MANOEUVRABLE", False)),
            secondary_owner=None if pd.isna(sec.get("OWNER")) else str(sec.get("OWNER")),
            tca=pd.Timestamp(conj["TCA"]).to_pydatetime(), miss_km=float(conj["MISS_KM"]),
            log_pc=float(conj["LOG_PC"]), level=str(conj["RISK_LEVEL"]),
        )
        C, hbr = self.assessor.combined_covariance(conj.to_frame().T, self.objects, self.t0)
        self._deadline = time.monotonic() + self.time_budget_s

        plan.primary_options = self._search(plan.primary_id, plan.secondary_id, conj, C[0], hbr[0], "primary")
        if plan.secondary_manoeuvrable:
            plan.secondary_options = self._search(plan.secondary_id, plan.primary_id, conj, C[0], hbr[0], "secondary")

        best_p = self._best(plan.primary_options, check_conflicts, plan.secondary_id)
        # The other satellite's options are only screened in full when ours can't avoid new conflicts
        need_secondary = best_p is None or not best_p.clean
        best_s = self._best(plan.secondary_options, check_conflicts and need_secondary, plan.primary_id)
        self._recommend(plan, best_p, best_s)
        return plan

    def tradeoff_curve(self, conj: pd.Series, option: BurnOption, n: int = 30) -> list[dict]:
        """
        New miss distance, log10 Pc and fuel at the conjunction as ΔV varies, for
        `option`'s mover, burn time and direction (same linear J2 model as the search).
        The first point is ΔV = 0 (no burn); the option's own ΔV is included.
        """
        mover = option.mover_id
        other = int(conj["SECONDARY_ID"]) if mover == int(conj["PRIMARY_ID"]) else int(conj["PRIMARY_ID"])
        C, hbr = self.assessor.combined_covariance(conj.to_frame().T, self.objects, self.t0)
        tw = float(conj["TCA_S"]) + np.arange(-WINDOW_S, WINDOW_S + WINDOW_STEP_S, WINDOW_STEP_S)
        R, V = self.source.states([mover, other], tw)
        burn_s = (pd.Timestamp(option.burn_time) - pd.Timestamp(self.t0)).total_seconds()
        rb, vb = self.source.state(mover, burn_s)
        S = burn_sensitivity(np.concatenate([rb[0], vb[0]]), burn_s, tw)
        unit = np.asarray(option.dv_rtn_ms, float) / max(option.dv_ms, 1e-12)
        lo = max(option.dv_ms / 30.0, MANOEUVRE_MIN_DV)
        hi = min(max(option.dv_ms * 4.0, lo * 10), MANOEUVRE_MAX_DV)
        dvs = np.unique(np.concatenate([[0.0, option.dv_ms], np.logspace(np.log10(lo), np.log10(hi), n)]))
        dev = np.einsum("wij,kj->kwi", S, unit[None, :] * dvs[:, None])
        miss, p, v = _closest((R[1] - R[0])[None] - dev[..., :3], (V[1] - V[0])[None] - dev[..., 3:], WINDOW_STEP_S)
        lp = log_pc(probability_of_collision(p * 1000.0, v * 1000.0, np.repeat(C[:1], len(dvs), 0),
                                             np.full(len(dvs), hbr[0])))
        m0, isp = self.sc["mass_kg"], self.sc["isp_s"]
        return [{"dv_ms": float(dv), "miss_km": float(m), "log_pc": float(l), "level": risk_level(float(l)),
                 "fuel_kg": float(m0 * (1 - np.exp(-dv / (isp * G0)))),
                 "meets_target": bool(l <= MANOEUVRE_TARGET_LOG_PC and m >= MANOEUVRE_TARGET_MISS_KM),
                 "is_option": bool(np.isclose(dv, option.dv_ms))}
                for dv, m, l in zip(dvs, miss, lp)]

    # ── search ──────────────────────────────────────────────────────────────
    def _search(self, mover: int, other: int, conj: pd.Series, C: np.ndarray, hbr: float, role: str) -> list:
        tca_s = float(conj["TCA_S"])
        period_s = float(self.objects.loc[mover, "PERIOD_MIN"]) * 60.0
        tw = tca_s + np.arange(-WINDOW_S, WINDOW_S + WINDOW_STEP_S, WINDOW_STEP_S)
        R, V = self.source.states([mover, other], tw)
        rel0_p, rel0_v = R[1] - R[0], V[1] - V[0]           # other − mover (km, km/s)
        min_burn_s = self._now_s() + MANOEUVRE_MIN_LEAD_HOURS * 3600

        dirs = list(MANOEUVRE_DIRECTIONS.items())
        units = np.array([u for _, u in dirs], float)                 # (D,3)
        dv_vecs = (units[:, None, :] * DV_GRID[None, :, None]).reshape(-1, 3)  # (D*G,3)

        options = []
        for lead in LEAD_ORBITS:
            burn_s = tca_s - lead * period_s
            if burn_s < min_burn_s:
                continue
            rb, vb = self.source.state(mover, burn_s)
            state_b = np.concatenate([rb[0], vb[0]])
            if not np.all(np.isfinite(state_b)):
                continue
            S = burn_sensitivity(state_b, burn_s, tw)                   # (W,6,3)

            def evaluate(dvs: np.ndarray):
                dev = np.einsum("wij,kj->kwi", S, dvs)                 # (K,W,6)
                miss, p, v = _closest(rel0_p[None] - dev[..., :3], rel0_v[None] - dev[..., 3:], WINDOW_STEP_S)
                lp = log_pc(probability_of_collision(p * 1000.0, v * 1000.0,
                                                     np.repeat(C[None], len(dvs), 0), np.full(len(dvs), hbr)))
                return miss, lp

            miss, lp = evaluate(dv_vecs)
            ok = ((lp <= MANOEUVRE_TARGET_LOG_PC) & (miss >= MANOEUVRE_TARGET_MISS_KM)).reshape(len(dirs), -1)
            for d_i, (name, unit) in enumerate(dirs):
                hits = np.flatnonzero(ok[d_i])
                if not len(hits):
                    continue
                g = hits[0]
                lo, hi = (DV_GRID[g - 1] if g > 0 else 0.0), DV_GRID[g]
                for _ in range(12):  # bisection to the smallest ΔV that meets the target
                    mid = 0.5 * (lo + hi)
                    m_, l_ = evaluate(np.array([unit]) * mid)
                    if l_[0] <= MANOEUVRE_TARGET_LOG_PC and m_[0] >= MANOEUVRE_TARGET_MISS_KM:
                        hi = mid
                    else:
                        lo = mid
                m_, l_ = evaluate(np.array([unit]) * hi)
                options.append(self._option(mover, role, burn_s, lead, name, np.array(unit) * hi,
                                            state_b, float(m_[0]), float(l_[0])))
        options.sort(key=lambda o: (o.dv_ms, -o.lead_hours))
        # Verify the cheapest few with full nonlinear propagation
        for o in options[:6]:
            self._verify(o, other, tw, rel0_p, R, V, C, hbr)
        return options

    def _option(self, mover, role, burn_s, lead, direction, dv_rtn, state_b, miss, lp) -> BurnOption:
        dv = float(np.linalg.norm(dv_rtn))
        m0, isp, thrust = self.sc["mass_kg"], self.sc["isp_s"], self.sc["thrust_n"]
        r, v = state_b[:3], state_b[3:]
        v_new = v + rtn_basis(r, v) @ (dv_rtn / 1000.0)
        sma = lambda vel: 1.0 / (2.0 / np.linalg.norm(r) - vel @ vel / MU)
        return BurnOption(
            mover_id=int(mover), mover_name=str(self.objects.loc[mover, "OBJECT_NAME"]), role=role,
            burn_time=add_seconds(self.t0, burn_s), lead_hours=(burn_s - self._now_s()) / 3600.0,
            lead_orbits=lead, direction=direction, dv_ms=dv, dv_rtn_ms=tuple(float(x) for x in dv_rtn),
            burn_duration_s=m0 * dv / thrust, fuel_kg=m0 * (1 - np.exp(-dv / (isp * G0))),
            new_miss_km=miss, new_log_pc=lp, new_level=risk_level(lp),
            delta_sma_km=float(sma(v_new) - sma(v)),
        )

    def _verify(self, o: BurnOption, other, tw, rel0_p, R, V, C, hbr):
        burn_s = (pd.Timestamp(o.burn_time) - pd.Timestamp(self.t0)).total_seconds()
        rb, vb = self.source.state(o.mover_id, burn_s)
        offset = burn_offset(np.concatenate([rb[0], vb[0]]), burn_s, np.array(o.dv_rtn_ms), float(tw.max()), step_s=5.0)
        dr, dvv = offset(tw)
        miss, p, v = _closest((rel0_p - dr)[None], ((V[1] - V[0]) - dvv)[None], WINDOW_STEP_S)
        o.verified_miss_km = float(miss[0])
        o.verified_log_pc = float(log_pc(probability_of_collision(p * 1000.0, v * 1000.0, C[None], np.array([hbr])))[0])

    # ── conflicts and recommendation ───────────────────────────────────────
    def check_conflicts(self, o: BurnOption, other_id: int) -> BurnOption:
        """
        Close approaches the burn creates or makes worse (ignoring the conjunction
        being avoided and ones that already existed at the same or higher risk).
        """
        burn_s = (pd.Timestamp(o.burn_time) - pd.Timestamp(self.t0)).total_seconds()
        rb, vb = self.source.state(o.mover_id, burn_s)
        offset = burn_offset(np.concatenate([rb[0], vb[0]]), burn_s, np.array(o.dv_rtn_ms), self.horizon_h * 3600.0)
        baseline, near = self._context(o.mover_id)

        grid = np.arange(max(burn_s, 0.0), self.horizon_h * 3600.0, 60.0)
        max_shift = float(np.linalg.norm(offset(grid)[0], axis=1).max()) if len(grid) else 0.0
        if max_shift < NEAR_KM - SCREENING_DISTANCE_KM - MARGIN_KM and near is not None and not near.empty:
            new = rescreen_near(self.objects, self.source, o.mover_id, near, offset, start_s=max(burn_s, 0.0))
        else:  # large path change: screen the whole catalogue again
            new = screen(self.objects, self.source, [o.mover_id], horizon_h=self.horizon_h,
                         offsets={o.mover_id: offset}, start_s=max(burn_s, 0.0))
        o.conflicts = []
        if not new.empty:
            new = self.assessor.assess(new, self.objects, self.t0)
            for r in new[(new["STATUS"] == "DANGER") & (new["SECONDARY_ID"] != other_id)].itertuples():
                if not baseline.empty:
                    same = baseline[(baseline["SECONDARY_ID"] == r.SECONDARY_ID)
                                    & ((baseline["TCA_S"] - r.TCA_S).abs() < 600)]
                    if not same.empty and same["LOG_PC"].max() >= r.LOG_PC - 0.3:
                        continue  # already existed before the burn, not made worse
                o.conflicts.append({
                    "object_id": int(r.SECONDARY_ID), "object_name": r.SECONDARY_NAME,
                    "object_type": r.SECONDARY_TYPE, "tca": pd.Timestamp(r.TCA).isoformat(),
                    "miss_km": float(r.MISS_KM), "log_pc": float(r.LOG_PC), "level": r.RISK_LEVEL,
                    "manoeuvrable": bool(self.objects.loc[r.SECONDARY_ID].get("MANOEUVRABLE", False)),
                })
        o.conflict_checked = True
        return o

    @staticmethod
    def _verified(options: list) -> list:
        return [o for o in options if o.verified_miss_km is not None
                and o.verified_log_pc <= MANOEUVRE_TARGET_LOG_PC + 0.5
                and o.verified_miss_km >= 0.8 * MANOEUVRE_TARGET_MISS_KM]

    def _best(self, options: list, check: bool, other_id: int, tries: int = 6) -> Optional[BurnOption]:
        """Cheapest verified option that creates no new HIGH/CRITICAL conjunction (else the one with fewest)."""
        verified = self._verified(options)
        if not check or not verified:
            return verified[0] if verified else None
        checked = []
        for o in verified[:tries]:
            if checked and time.monotonic() > self._deadline:
                break
            self.check_conflicts(o, other_id)
            if o.clean:
                return o
            checked.append(o)
        return min(checked, key=lambda o: (len(o.conflicts), o.dv_ms))

    def _recommend(self, plan: ManoeuvrePlan, best_p: Optional[BurnOption], best_s: Optional[BurnOption]):
        who = plan.secondary_owner or "its operator"
        if plan.secondary_manoeuvrable and "STARLINK" in plan.secondary_name.upper():
            plan.notes.append("Starlink satellites avoid conjunctions autonomously — share any planned burn "
                              "with SpaceX through Space-Track so both sides don't move into each other.")
        if best_p is None and best_s is None:
            plan.summary = ("No single burn within limits meets the target. Escalate: obtain precise orbit data "
                            "(Space-Track CDM / operator ephemeris) and consider a larger or earlier manoeuvre.")
            return
        def rank(o):
            return (not o.clean, len(o.conflicts), o.role != "primary", o.dv_ms)
        ranked = sorted([o for o in (best_p, best_s) if o is not None], key=rank)
        plan.recommended = ranked[0]
        plan.alternative = ranked[1] if len(ranked) > 1 else None

        r = plan.recommended
        if r.role == "primary":
            plan.summary = (f"Manoeuvre {r.mover_name}: {r.direction} burn of {r.dv_ms * 100:.1f} cm/s "
                            f"at {r.burn_time:%Y-%m-%d %H:%M:%S} UTC.")
        else:
            reason = (f"no burn of {plan.primary_name} meets the target" if best_p is None
                      else f"every burn of {plan.primary_name} checked creates new high-risk approaches")
            plan.summary = (f"Ask {who} to manoeuvre {r.mover_name}: {r.direction} burn of "
                            f"{r.dv_ms * 100:.1f} cm/s at {r.burn_time:%Y-%m-%d %H:%M:%S} UTC — {reason}.")
        if plan.alternative is not None and plan.alternative.role == "secondary":
            checked = "" if plan.alternative.conflict_checked else " — not yet screened for new conflicts"
            plan.notes.append(f"{plan.secondary_name} is a working satellite ({who}); it could move instead "
                              f"({plan.alternative.direction}, {plan.alternative.dv_ms * 100:.1f} cm/s{checked}).")
        if r.conflicts:
            movers = [c["object_name"] for c in r.conflicts if c["manoeuvrable"]]
            plan.notes.append("No conflict-free burn was found; this one still causes new high-risk approaches: "
                              + ", ".join(f"{c['object_name']} ({c['level']}, {c['miss_km']:.2f} km)" for c in r.conflicts)
                              + (f". These satellites may also need to move: {', '.join(movers)}." if movers else "."))
        if r.direction in ("prograde", "retrograde"):
            plan.notes.append(f"Along-track burns change altitude by {r.delta_sma_km * 1000:+.0f} m; plan an equal "
                              f"and opposite burn after TCA to return to the original orbit.")
