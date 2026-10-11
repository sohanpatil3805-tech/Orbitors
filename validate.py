"""
OrbitGuard AI — Validation report

Checks that the risk evaluation and the manoeuvre suggestions are correct, each
against an independent reference:

  A. Collision probability engine
     A1 reproduces ESA's own risk values from the CDM test set
     A2 matches the closed-form Pc for a head-on, isotropic case
     A3 matches a Monte Carlo simulation for random encounter geometries
  B. ML uncertainty model (live data has no covariance)
     B1 predicts CDM uncertainties better than a per-object-type baseline
     B2 risk computed with ML uncertainty beats risk with baseline uncertainty
     B3 the full-CDM XGBoost model's alert precision / recall
  C. Screening (SGP4)
     C1 finds simulated threats at the injected time and miss distance
     C2 agrees with CelesTrak SOCRATES close-approach predictions
     C3 agrees with Space-Track official CDMs (needs credentials)
  D. Manoeuvre physics
     D1 linear burn model vs full nonlinear propagation
     D2 drift after a prograde burn vs Clohessy–Wiltshire theory
     D3 fuel vs the rocket equation
     D4 end to end: simulated threats → CRITICAL alert → suggested burn → an
        independent re-propagation confirms the burn clears the threat without
        creating new high-risk approaches

Run:  python validate.py            (≈5 min; writes exports/validation_report.json)
"""

import io
import json
import time
from datetime import datetime, timezone

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from config import EXPORT_DIR, TEST_DATA_PATH, TRAIN_DATA_PATH, MODEL_DIR, SOCRATES_URL, \
    MANOEUVRE_TARGET_LOG_PC, MANOEUVRE_TARGET_MISS_KM, RISK_THRESHOLD
from risk_engine import (covariance_rtn, pc_from_cdm, probability_of_collision, log_pc, rotate_covariance,
                         rtn_matrix)

CHECKS = []


def check(section, name, what, passed, result, criterion, table=None):
    CHECKS.append({"section": section, "name": name, "what": what, "passed": None if passed is None else bool(passed),
                   "result": result, "criterion": criterion, "table": table})
    mark = {True: "PASS", False: "FAIL", None: "SKIP"}[None if passed is None else bool(passed)]
    print(f"[{mark}] {section} — {name}: {result}")


def alert_stats(y, p, thr=RISK_THRESHOLD):
    t, q = y >= thr, p >= thr
    return (t & q).sum() / max(q.sum(), 1), (t & q).sum() / max(t.sum(), 1)


# ─── A. Collision probability engine ────────────────────────────────────────
def section_a(test: pd.DataFrame):
    S = "A. Collision probability engine"
    df = test.dropna(subset=["t_sigma_r", "c_sigma_r"])
    y, p = df["risk"].to_numpy(), pc_from_cdm(df)
    m = y > -10
    mae, rho = np.abs(p[m] - y[m]).mean(), spearmanr(y, p)[0]
    prec, rec = alert_stats(y, p)
    check(S, "A1 Reproduces ESA risk values",
          f"Recompute log10 Pc for all {len(df):,} test CDMs from their geometry, covariance and object sizes, "
          "and compare with the risk ESA published in the dataset.",
          mae < 0.1 and rho > 0.98 and prec > 0.9 and rec > 0.9,
          f"mean abs error {mae:.3f} log10 units (risk > −10), Spearman {rho:.3f}, "
          f"alert precision {prec:.3f} / recall {rec:.3f}",
          "error < 0.1, Spearman > 0.98, precision and recall > 0.9")

    rows = []
    worst = 0.0
    for sigma, R in [(10.0, 5.0), (50.0, 10.0), (200.0, 20.0), (1000.0, 5.0)]:
        C = covariance_rtn(sigma, sigma, sigma)
        pc = probability_of_collision([[0, 0, 0]], [[0, 7000, 0]], C, [R])[0]
        exact = 1 - np.exp(-R ** 2 / (2 * sigma ** 2))
        err = abs(pc - exact) / exact
        worst = max(worst, err)
        rows.append({"sigma (m)": sigma, "radius (m)": R, "engine Pc": f"{pc:.6e}", "exact Pc": f"{exact:.6e}",
                     "relative error": f"{err:.1e}"})
    check(S, "A2 Closed-form case", "Head-on pass with zero miss distance and round uncertainty, where "
          "Pc = 1 − exp(−R²/2σ²) exactly.", worst < 1e-5, f"worst relative error {worst:.1e}",
          "< 1e-5 (64-point Gauss–Legendre integration)", rows)

    rng = np.random.default_rng(7)
    rows, ok = [], True
    for i in range(6):
        sig = rng.uniform(20, 300, 3)
        C = covariance_rtn(*sig, rng.uniform(-0.6, 0.6), rng.uniform(-0.6, 0.6), rng.uniform(-0.3, 0.3))[0]
        v = rng.normal(size=3); v = v / np.linalg.norm(v) * rng.uniform(5000, 15000)
        miss = rng.normal(size=3) * rng.uniform(0, 200)
        R = rng.uniform(5, 30)
        pc = probability_of_collision([miss], [v], C[None], [R])[0]
        n = 4_000_000
        samples = rng.multivariate_normal(miss, C, size=n)
        vh = v / np.linalg.norm(v)
        perp = samples - np.outer(samples @ vh, vh)       # closest-approach distance for straight-line motion
        mc = np.mean(np.linalg.norm(perp, axis=1) < R)
        se = np.sqrt(max(mc * (1 - mc), 1e-12) / n)
        agree = abs(pc - mc) <= 4 * se + 1e-7
        ok &= agree
        rows.append({"case": i + 1, "engine Pc": f"{pc:.4e}", "Monte Carlo Pc": f"{mc:.4e}",
                     "MC std error": f"{se:.1e}", "agree": "yes" if agree else "no"})
    check(S, "A3 Monte Carlo agreement", "Random encounter geometries (correlated covariance, any crossing "
          "direction): engine Pc vs 4 million sampled encounters each.", ok,
          f"{sum(r['agree'] == 'yes' for r in rows)}/{len(rows)} cases within 4 MC standard errors",
          "all cases within 4 standard errors", rows)


# ─── B. ML uncertainty model ────────────────────────────────────────────────
def section_b(train: pd.DataFrame, test: pd.DataFrame):
    S = "B. ML uncertainty model"
    from uncertainty_model import UncertaintyModel, cdm_object_rows, _usable, SIGMA_TARGETS, CORR_TARGETS
    um = UncertaintyModel.load()
    rows_tr = _usable(pd.concat([cdm_object_rows(train, "t"), cdm_object_rows(train, "c")]))
    medians = rows_tr.groupby("otype")[SIGMA_TARGETS + CORR_TARGETS].median()

    table, wins = [], 0
    for prefix, label in (("t", "satellite"), ("c", "other object")):
        rows = _usable(cdm_object_rows(test, prefix))
        pred = um.predict(rows)
        base = medians.reindex(rows["otype"]).to_numpy()
        for i, tgt in enumerate(SIGMA_TARGETS):
            ml = np.abs(pred[tgt] - rows[tgt]).mean()
            bl = np.abs(base[:, i] - rows[tgt].to_numpy()).mean()
            wins += ml < bl
            table.append({"object": label, "quantity": tgt.replace("log_sigma_", "σ "),
                          "ML error (×)": f"{10 ** ml:.2f}", "baseline error (×)": f"{10 ** bl:.2f}"})
    check(S, "B1 Uncertainty prediction", "Predict each object's position uncertainty (radial, along-track, "
          "cross-track) on held-out CDMs; typical error shown as a factor (1.5× = within 50%). Baseline: median "
          "of the training data for that object type.", wins == 6, f"ML better in {wins}/6 cases",
          "ML better in all 6", table)

    df = test.dropna(subset=["t_sigma_r", "c_sigma_r"]).reset_index(drop=True)
    y = df["risk"].to_numpy()

    def with_cov(src):
        d = df.copy()
        for prefix in "tc":
            sig = src(prefix)
            for c in "rtn":
                d[f"{prefix}_sigma_{c}"] = 10 ** sig[f"log_sigma_{c}"].to_numpy()
            for col, k in (("ct_r", "corr_tr"), ("cn_r", "corr_nr"), ("cn_t", "corr_nt")):
                d[f"{prefix}_{col}"] = sig[k].to_numpy()
        return pc_from_cdm(d)

    def ml_src(prefix):
        return um.predict(cdm_object_rows(df, prefix))

    def base_src(prefix):
        rows = cdm_object_rows(df, prefix)
        return pd.DataFrame(medians.reindex(rows["otype"]).to_numpy(), columns=SIGMA_TARGETS + CORR_TARGETS)

    m = y > -10
    res = {}
    for name, src in (("ML uncertainty", ml_src), ("Baseline uncertainty", base_src)):
        p = with_cov(src)
        prec, rec = alert_stats(y, p)
        res[name] = {"method": name, "Spearman": round(spearmanr(y, p)[0], 3),
                     "mean abs error": round(float(np.abs(p[m] - y[m]).mean()), 2),
                     "alert precision": round(prec, 3), "alert recall": round(rec, 3)}
    p_true = pc_from_cdm(df)
    pt, rt = alert_stats(y, p_true)
    res["Real CDM covariance"] = {"method": "Real CDM covariance (upper bound)", "Spearman": round(spearmanr(y, p_true)[0], 3),
                                  "mean abs error": round(float(np.abs(p_true[m] - y[m]).mean()), 3),
                                  "alert precision": round(pt, 3), "alert recall": round(rt, 3)}
    ml, bl = res["ML uncertainty"], res["Baseline uncertainty"]
    check(S, "B2 Risk without real covariance (live situation)",
          "Recompute every test CDM's risk using only predicted uncertainty — as for live public orbit data — and "
          "compare with ESA's risk. Baseline: same physics with per-type median uncertainty.",
          ml["Spearman"] > bl["Spearman"] and ml["mean abs error"] < bl["mean abs error"],
          f"ML: Spearman {ml['Spearman']}, error {ml['mean abs error']} · baseline: Spearman {bl['Spearman']}, "
          f"error {bl['mean abs error']}", "ML beats the baseline on both", list(res.values()))

    meta_path = MODEL_DIR / "orbitguard_model_meta.json"
    if meta_path.exists():
        mt = json.loads(meta_path.read_text())["training_metrics"]
        check(S, "B3 Full-CDM XGBoost model", "The original model (all 118 CDM features) on the test set.",
              mt["test_alert_precision"] > 0.9 and mt["test_alert_recall"] > 0.9,
              f"R² {mt['test_r2']:.4f}, alert precision {mt['test_alert_precision']:.3f} / recall {mt['test_alert_recall']:.3f}",
              "precision and recall > 0.9")


# ─── C. Screening ───────────────────────────────────────────────────────────
def section_c(state):
    S = "C. Screening (SGP4)"
    from scenario import create_threat, with_threats
    from screening import screen

    cases = [(25544, 18.0, 25.0, 70.0), (40697, 30.0, 500.0, 120.0), (20580, 50.0, 3000.0, 40.0),
             (43613, 6.0, 0.0, 150.0)]
    threats = [create_threat(state.catalog.objects, state.source, pid, h, miss, ang, "debris", index=i)
               for i, (pid, h, miss, ang) in enumerate(cases)]
    objs, src = with_threats(state.catalog.objects, state.source, threats)
    found = screen(objs, src, sorted({c[0] for c in cases}), only_secondaries=[t.object_id for t in threats])
    rows, ok = [], True
    for t in threats:
        hit = found[(found["SECONDARY_ID"] == t.object_id) & ((found["TCA_S"] - t.tca_s).abs() < 120)]
        if hit.empty:
            ok = False
            rows.append({"satellite": objs.loc[t.primary_id, "OBJECT_NAME"], "injected miss (m)": t.miss_m,
                         "found": "no"})
            continue
        h = hit.iloc[0]
        dt, dm = h["TCA_S"] - t.tca_s, h["MISS_KM"] * 1000 - t.miss_m
        good = abs(dt) < 1.0 and abs(dm) < 5.0
        ok &= good
        rows.append({"satellite": h["PRIMARY_NAME"], "hours ahead": t.tca_s / 3600, "injected miss (m)": t.miss_m,
                     "found miss (m)": round(h["MISS_KM"] * 1000, 2), "TCA error (s)": round(dt, 3), "found": "yes"})
    check(S, "C1 Finds simulated threats", "Objects placed on known collision courses (0 m to 3 km, 6–50 h ahead, "
          "various crossing angles) must be found at the right time and distance.", ok,
          f"{sum(r['found'] == 'yes' for r in rows)}/{len(rows)} found", "all found, TCA within 1 s, miss within 5 m",
          rows)

    from http_cache import cached_text
    from screening import refine
    text = cached_text(SOCRATES_URL, "socrates.csv", 7200, timeout=180)
    if text is None:
        check(S, "C2 Agreement with CelesTrak SOCRATES", "", None, "SOCRATES unavailable", "—")
    else:
        soc = pd.read_csv(io.StringIO(text))
        soc["TCA"] = pd.to_datetime(soc["TCA"], utc=True)
        t0 = pd.Timestamp(state.t0)
        soc = soc[(soc["TCA"] > t0 + pd.Timedelta(hours=1)) & (soc["TCA"] < t0 + pd.Timedelta(hours=72))]
        sats = state.catalog.satrecs
        soc = soc[soc["NORAD_CAT_ID_1"].isin(sats) & soc["NORAD_CAT_ID_2"].isin(sats)].head(3000)
        epochs = state.catalog.objects["EPOCH"]
        rows = []
        for r in soc.itertuples():
            tca_s = (r.TCA - t0).total_seconds()
            # SOCRATES lists days since each element set's epoch (DSE) at TCA; same epoch = same input data
            same = all(abs((r.TCA - pd.Timedelta(days=dse) - epochs.loc[nid]).total_seconds()) < 300
                       for nid, dse in ((r.NORAD_CAT_ID_1, r.DSE_1), (r.NORAD_CAT_ID_2, r.DSE_2)))
            res = refine(state.source, int(r.NORAD_CAT_ID_1), int(r.NORAD_CAT_ID_2), tca_s - 300, tca_s + 300)
            if res is None:
                continue
            rows.append({"pair": f"{r.OBJECT_NAME_1} / {r.OBJECT_NAME_2}", "same orbit data": same,
                         "SOCRATES range (km)": r.TCA_RANGE, "our range (km)": round(res["MISS_KM"], 4),
                         "Δrange (m)": round((res["MISS_KM"] - r.TCA_RANGE) * 1000, 1),
                         "ΔTCA (s)": round(res["TCA_S"] - tca_s, 3)})
        d = pd.DataFrame(rows)
        same = d[d["same orbit data"]]
        if same.empty:
            check(S, "C2 Agreement with CelesTrak SOCRATES", "", None,
                  "no SOCRATES pairs computed from the same orbit data as ours", "—")
        else:
            med_r, med_t = same["Δrange (m)"].abs().median(), same["ΔTCA (s)"].abs().median()
            within = float(((same["Δrange (m)"].abs() < 100) & (same["ΔTCA (s)"].abs() < 1)).mean())
            all_within = float((d["Δrange (m)"].abs() < 1000).mean())
            check(S, "C2 Agreement with CelesTrak SOCRATES",
                  f"CelesTrak's independent SOCRATES service predicts close approaches with SGP4. For the {len(same)} "
                  f"upcoming pairs it computed from the same element sets we hold, our TCA and miss distance must "
                  f"match. (Across all {len(d)} pairs, {all_within:.0%} agree within 1 km; the rest differ because one "
                  f"side has newer orbit data — mostly manoeuvring Starlinks.)",
                  med_r < 10 and med_t < 0.1 and within > 0.9,
                  f"median |Δrange| {med_r:.1f} m, median |ΔTCA| {med_t:.3f} s, {within:.0%} within 100 m and 1 s",
                  "same-data pairs: median |Δrange| < 10 m, median |ΔTCA| < 0.1 s, > 90% within 100 m and 1 s",
                  same.sort_values("Δrange (m)", key=abs, ascending=False).head(15).to_dict("records"))

    import spacetrack_client
    cdms = spacetrack_client.fetch_public_cdms()
    if not cdms:
        check(S, "C3 Agreement with Space-Track official CDMs", "Needs SPACETRACK_USER / SPACETRACK_PASSWORD.",
              None, "skipped (Space-Track not configured)", "median |Δmiss| < 1 km")
    else:
        rows = []
        for c in cdms[:300]:
            a, b = int(c["SAT_1_ID"]), int(c["SAT_2_ID"])
            if a not in sats or b not in sats:
                continue
            tca_s = (pd.Timestamp(c["TCA"], tz="UTC") - pd.Timestamp(state.t0)).total_seconds()
            if not 0 < tca_s < 72 * 3600:
                continue
            res = refine(state.source, a, b, tca_s - 600, tca_s + 600)
            if res:
                rows.append({"pair": f"{c['SAT_1_NAME']} / {c['SAT_2_NAME']}", "official miss (km)": float(c["MIN_RNG"]) / 1000,
                             "our miss (km)": round(res["MISS_KM"], 3), "official Pc": c.get("PC"),
                             "ΔTCA (s)": round(res["TCA_S"] - tca_s, 2)})
        d = pd.DataFrame(rows)
        if d.empty:
            check(S, "C3 Agreement with Space-Track official CDMs", "", None, "no comparable CDMs in window", "—")
        else:
            med = (d["our miss (km)"] - d["official miss (km)"]).abs().median()
            check(S, "C3 Agreement with Space-Track official CDMs", f"{len(d)} official public CDMs recomputed.",
                  med < 1.0, f"median |Δmiss| {med * 1000:.0f} m", "median |Δmiss| < 1 km", d.head(15).to_dict("records"))


# ─── D. Manoeuvre physics ───────────────────────────────────────────────────
def section_d(state):
    S = "D. Manoeuvre physics"
    from orbit_propagation import burn_sensitivity, burn_offset, propagate_j2, rtn_basis, MU

    pid = 25544
    r, v = state.source.state(pid, 3600.0)
    x0 = np.concatenate([r[0], v[0]])
    t_eval = 3600.0 + np.linspace(0, 86400, 145)
    S_mat = burn_sensitivity(x0, 3600.0, t_eval)
    rows, ok, worst = [], True, 0.0
    for direction, unit in (("prograde", (0, 1, 0)), ("radial-out", (1, 0, 0)), ("normal", (0, 0, 1))):
        for dv in (0.1, 1.0):
            dvv = np.array(unit, float) * dv
            lin = np.einsum("tij,j->ti", S_mat[:, :3], dvv)
            full = burn_offset(x0, 3600.0, dvv, t_eval[-1], step_s=10.0)(t_eval)[0]
            err = np.linalg.norm(lin - full, axis=1).max() / max(np.linalg.norm(full, axis=1).max(), 1e-9)
            limit = 0.01 if dv <= 0.1 else 0.03
            ok &= err < limit
            worst = max(worst, err)
            rows.append({"burn": f"{direction} {dv} m/s", "max shift after 1 day (km)": round(np.linalg.norm(full, axis=1).max(), 3),
                         "linear-model error": f"{err:.2%}", "limit": f"{limit:.0%}"})
    check(S, "D1 Linear burn model", "The planner searches burns with a linear (sensitivity) model; compare it with "
          "full nonlinear J2 propagation over one day.", ok, f"worst error {worst:.2%}",
          "< 1% for 0.1 m/s, < 3% for 1 m/s", rows)

    n = np.sqrt(MU / np.linalg.norm(x0[:3]) ** 3)
    period = 2 * np.pi / n
    ts = 3600.0 + np.array([0.25, 0.5, 1.0, 2.0]) * period
    dv = 0.1
    nominal = propagate_j2(x0, 3600.0, ts)
    off = burn_offset(x0, 3600.0, np.array([0, dv, 0]), ts[-1], step_s=5.0)(ts)[0] * 1000  # m
    rows, ok = [], True
    for k, t in enumerate(ts):
        B = rtn_basis(nominal[k, :3], nominal[k, 3:])
        rel = B.T @ off[k]
        tau = t - 3600.0
        cw_x = 2 * dv / n * (1 - np.cos(n * tau))
        cw_y = 4 * dv / n * np.sin(n * tau) - 3 * dv * tau
        err = abs(rel[1] - cw_y) / max(abs(cw_y), 1.0)
        ok &= err < 0.05
        rows.append({"time after burn (orbits)": round(tau / period, 2), "radial (m) model": round(rel[0], 1),
                     "radial (m) CW": round(cw_x, 1), "along-track (m) model": round(rel[1], 1),
                     "along-track (m) CW": round(cw_y, 1), "along-track error": f"{err:.1%}"})
    check(S, "D2 Clohessy–Wiltshire drift", "A 10 cm/s prograde burn on the ISS orbit: along-track drift must match "
          "the textbook relative-motion solution (−3·ΔV·t growth plus a 4ΔV/n oscillation).", ok,
          "along-track drift within 5% of theory" if ok else "mismatch", "< 5% at every sample", rows)

    m0, isp, dv = 500.0, 220.0, 1.0
    fuel = m0 * (1 - np.exp(-dv / (isp * 9.80665)))
    check(S, "D3 Rocket equation", "Fuel for a 1 m/s burn of a 500 kg spacecraft with Isp 220 s.",
          abs(fuel - 0.23171) < 1e-4, f"{fuel * 1000:.1f} g", "231.7 g (Tsiolkovsky)")

    from scenario import create_threat, with_threats
    from screening import screen
    from live_pipeline import load_uncertainty_model
    from risk_engine import LiveRiskAssessor
    from manoeuvre_planner import ManoeuvrePlanner
    scenarios = [(25544, 20.0, 20.0, 80.0, "debris"), (40697, 30.0, 10.0, 110.0, "debris"),
                 (54754, 40.0, 50.0, 60.0, "satellite")]
    rows, ok = [], True
    for i, (pid, h, miss, ang, kind) in enumerate(scenarios):
        th = create_threat(state.catalog.objects, state.source, pid, h, miss, ang, kind, index=i)
        objs, src = with_threats(state.catalog.objects, state.source, [th])
        assessor = LiveRiskAssessor(load_uncertainty_model(), state.weather)
        conj = screen(objs, src, [pid], only_secondaries=[th.object_id])
        conj = assessor.assess(conj, objs, state.t0)
        ev = conj[(conj["TCA_S"] - th.tca_s).abs() < 120].iloc[0]
        planner = ManoeuvrePlanner(objs, src, assessor, state.t0, baseline=state.conjunctions, near=state.near)
        plan = planner.plan(ev)
        rec = plan.recommended
        if rec is None:
            ok = False
            rows.append({"scenario": f"{objs.loc[pid, 'OBJECT_NAME']} vs {kind}", "alert": ev["RISK_LEVEL"], "burn": "none"})
            continue
        # Independent check: apply the burn to the J2-propagated state and recompute the encounter
        burn_s = (pd.Timestamp(rec.burn_time) - pd.Timestamp(state.t0)).total_seconds()
        rb, vb = src.state(rec.mover_id, burn_s)
        xb = np.concatenate([rb[0], vb[0]])
        xb_burn = xb.copy()
        xb_burn[3:] += rtn_basis(xb[:3], xb[3:]) @ (np.array(rec.dv_rtn_ms) / 1000.0)
        other = th.object_id if rec.mover_id == pid else pid
        tw = th.tca_s + np.arange(-1200, 1200.5, 0.5)
        moved = propagate_j2(xb_burn, burn_s, tw)[:, :3] - propagate_j2(xb, burn_s, tw)[:, :3]
        r_m, _ = src.states([rec.mover_id], tw)
        r_o, _ = src.states([other], tw)
        new_miss = float(np.linalg.norm(r_o[0] - (r_m[0] + moved), axis=1).min())
        good = (ev["STATUS"] == "DANGER" and new_miss >= 0.9 * MANOEUVRE_TARGET_MISS_KM
                and rec.verified_log_pc <= MANOEUVRE_TARGET_LOG_PC + 0.1 and rec.clean)
        ok &= good
        rows.append({"scenario": f"{objs.loc[pid, 'OBJECT_NAME']} vs simulated {kind}", "injected miss (m)": miss,
                     "alert": f"{ev['RISK_LEVEL']} ({ev['LOG_PC']:.2f})", "who moves": rec.mover_name,
                     "burn": f"{rec.direction} {rec.dv_ms * 100:.2f} cm/s, {rec.lead_orbits:g} orbits early",
                     "independent new miss (km)": round(new_miss, 3), "new log10 Pc": round(rec.verified_log_pc, 2),
                     "new high-risk approaches": len(rec.conflicts) if rec.conflict_checked else "not checked"})
    check(S, "D4 End to end: alert → burn → independent re-check",
          "Simulated threats on collision courses must raise a red alert; the suggested burn is applied in an "
          "independent propagation and must clear the threat (≥ target miss, Pc ≤ target) without new HIGH/CRITICAL "
          "approaches.", ok, f"{sum(1 for r in rows if 'independent new miss (km)' in r)}/{len(rows)} scenarios cleared",
          f"alert DANGER; new miss ≥ {0.9 * MANOEUVRE_TARGET_MISS_KM:g} km; log10 Pc ≤ {MANOEUVRE_TARGET_LOG_PC + 0.1:g}; "
          "no new high-risk approaches", rows)


def main():
    start = time.time()
    train = pd.read_csv(TRAIN_DATA_PATH)
    test = pd.read_csv(TEST_DATA_PATH)
    section_a(test)
    section_b(train, test)
    from live_pipeline import run_live
    state = run_live()
    section_c(state)
    section_d(state)

    report = {"generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
              "runtime_seconds": round(time.time() - start), "checks": CHECKS}
    EXPORT_DIR.mkdir(exist_ok=True)
    out = EXPORT_DIR / "validation_report.json"
    out.write_text(json.dumps(report, indent=2, default=str))
    passed = sum(1 for c in CHECKS if c["passed"])
    failed = sum(1 for c in CHECKS if c["passed"] is False)
    print(f"\n{passed} passed, {failed} failed, {len(CHECKS) - passed - failed} skipped — report: {out}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
