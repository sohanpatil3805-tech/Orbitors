"""
OrbitGuard AI — Streamlit Dashboard
Live collision screening of important satellites, explainable risk, and
operator-approved avoidance manoeuvres.
"""

import json
import sys
import threading
import time
from datetime import datetime, timezone

# Log messages contain emoji; on Windows a redirected console defaults to cp1252 and
# would crash on them, so force UTF-8 output.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from config import (DASHBOARD_REFRESH_INTERVAL, DEFAULT_SPACECRAFT, EXPORT_DIR, IMPORTANT_SATELLITES,
                    MANOEUVRE_TARGET_LOG_PC, MANOEUVRE_TARGET_MISS_KM, PROPAGATION_WINDOW_HOURS,
                    REVIEW_MISS_DISTANCE_KM, RISK_COLORS)

# ─── Page Configuration ──────────────────────────────────────────────────────
st.set_page_config(
    page_title="OrbitGuard AI 🛰️",
    page_icon="🛰️",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ─── Custom CSS ───────────────────────────────────────────────────────────────
def inject_custom_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&family=JetBrains+Mono:wght@400;500;600&display=swap');

    /* ─── Global ─────────────────────────────────────────────────────── */
    .stApp {
        background: linear-gradient(135deg, #0a0a1a 0%, #0d1b2a 30%, #1b2838 60%, #0a0a1a 100%);
        font-family: 'Inter', sans-serif;
    }

    /* ─── Sidebar ────────────────────────────────────────────────────── */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0d1117 0%, #161b22 100%);
        border-right: 1px solid rgba(0, 229, 255, 0.15);
    }

    [data-testid="stSidebar"] .stMarkdown h1,
    [data-testid="stSidebar"] .stMarkdown h2,
    [data-testid="stSidebar"] .stMarkdown h3 {
        color: #00E5FF !important;
    }

    /* ─── Metric Cards ───────────────────────────────────────────────── */
    [data-testid="stMetric"] {
        background: linear-gradient(135deg, rgba(13, 27, 42, 0.8), rgba(27, 40, 56, 0.6));
        border: 1px solid rgba(0, 229, 255, 0.2);
        border-radius: 12px;
        padding: 16px 20px;
        box-shadow: 0 4px 20px rgba(0, 229, 255, 0.05);
        transition: all 0.3s ease;
    }

    [data-testid="stMetric"]:hover {
        border-color: rgba(0, 229, 255, 0.5);
        box-shadow: 0 4px 30px rgba(0, 229, 255, 0.12);
        transform: translateY(-2px);
    }

    [data-testid="stMetricLabel"] {
        color: rgba(255, 255, 255, 0.7) !important;
        font-size: 0.85rem !important;
        font-weight: 500 !important;
        letter-spacing: 0.5px;
        text-transform: uppercase;
    }

    [data-testid="stMetricValue"] {
        color: #00E5FF !important;
        font-weight: 700 !important;
        font-size: 1.8rem !important;
    }

    /* ─── Headers ────────────────────────────────────────────────────── */
    h1, h2, h3 {
        font-family: 'Inter', sans-serif !important;
        font-weight: 700 !important;
    }

    h1 {
        background: linear-gradient(135deg, #00E5FF, #7C4DFF, #FF6B35);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        font-size: 2.5rem !important;
        letter-spacing: -0.5px;
    }

    /* ─── Data Tables ────────────────────────────────────────────────── */
    .stDataFrame {
        border-radius: 12px;
        overflow: hidden;
    }

    [data-testid="stDataFrame"] > div {
        border: 1px solid rgba(0, 229, 255, 0.15);
        border-radius: 12px;
    }

    /* ─── Buttons ────────────────────────────────────────────────────── */
    .stButton > button {
        background: linear-gradient(135deg, #00E5FF 0%, #7C4DFF 100%);
        color: white;
        border: none;
        border-radius: 8px;
        font-weight: 600;
        padding: 0.5rem 1.5rem;
        transition: all 0.3s ease;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }

    .stButton > button:hover {
        box-shadow: 0 4px 20px rgba(0, 229, 255, 0.3);
        transform: translateY(-1px);
    }

    /* ─── Tab styling ────────────────────────────────────────────────── */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background: rgba(13, 27, 42, 0.5);
        border-radius: 12px;
        padding: 4px;
    }

    .stTabs [data-baseweb="tab"] {
        border-radius: 8px;
        padding: 8px 20px;
        color: rgba(255, 255, 255, 0.6);
        font-weight: 500;
    }

    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, rgba(0, 229, 255, 0.2), rgba(124, 77, 255, 0.2));
        color: #00E5FF !important;
    }

    /* ─── Expander ───────────────────────────────────────────────────── */
    .streamlit-expanderHeader {
        background: rgba(13, 27, 42, 0.5);
        border: 1px solid rgba(0, 229, 255, 0.15);
        border-radius: 8px;
        color: white !important;
    }

    /* ─── Alert boxes ────────────────────────────────────────────────── */
    .risk-critical {
        background: linear-gradient(135deg, rgba(255, 0, 64, 0.15), rgba(255, 0, 64, 0.05));
        border-left: 4px solid #FF0040;
        border-radius: 8px;
        padding: 16px 20px;
        margin: 8px 0;
    }
    .risk-high {
        background: linear-gradient(135deg, rgba(255, 107, 53, 0.15), rgba(255, 107, 53, 0.05));
        border-left: 4px solid #FF6B35;
        border-radius: 8px;
        padding: 16px 20px;
        margin: 8px 0;
    }
    .risk-medium {
        background: linear-gradient(135deg, rgba(255, 215, 0, 0.15), rgba(255, 215, 0, 0.05));
        border-left: 4px solid #FFD700;
        border-radius: 8px;
        padding: 16px 20px;
        margin: 8px 0;
    }
    .risk-low {
        background: linear-gradient(135deg, rgba(0, 230, 118, 0.15), rgba(0, 230, 118, 0.05));
        border-left: 4px solid #00E676;
        border-radius: 8px;
        padding: 16px 20px;
        margin: 8px 0;
    }

    /* ─── Glassmorphism panels ───────────────────────────────────────── */
    .glass-panel {
        background: rgba(13, 27, 42, 0.6);
        backdrop-filter: blur(20px);
        -webkit-backdrop-filter: blur(20px);
        border: 1px solid rgba(0, 229, 255, 0.15);
        border-radius: 16px;
        padding: 24px;
        margin: 8px 0;
    }

    /* ─── Pulse animation for critical alerts ────────────────────────── */
    @keyframes pulse-red {
        0% { box-shadow: 0 0 0 0 rgba(255, 0, 64, 0.4); }
        70% { box-shadow: 0 0 0 10px rgba(255, 0, 64, 0); }
        100% { box-shadow: 0 0 0 0 rgba(255, 0, 64, 0); }
    }

    .pulse-alert {
        animation: pulse-red 2s infinite;
    }

    /* ─── Status banner and chips ────────────────────────────────────── */
    .og-banner {
        display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 12px;
        padding: 14px 20px; margin: 6px 0 14px; border-radius: 14px;
        background: rgba(13, 22, 42, 0.72); border: 1px solid rgba(120, 160, 255, 0.18);
        backdrop-filter: blur(12px);
    }
    .og-banner .og-head { font-weight: 600; font-size: 1.02rem; color: #EAF0FF; }
    .og-danger { border-left: 4px solid #FF3B5C; box-shadow: 0 0 24px rgba(255, 59, 92, 0.12); }
    .og-review { border-left: 4px solid #FFA62B; }
    .og-safe { border-left: 4px solid #3DDC97; }
    .og-chip {
        display: inline-block; margin-left: 8px; padding: 4px 12px; border-radius: 999px;
        font-size: 0.82rem; font-weight: 600; letter-spacing: 0.2px;
    }
    .og-chip-danger { background: rgba(255, 59, 92, 0.14); color: #FF8DA1; border: 1px solid rgba(255, 59, 92, 0.35); }
    .og-chip-review { background: rgba(255, 166, 43, 0.12); color: #FFC56B; border: 1px solid rgba(255, 166, 43, 0.32); }
    .og-chip-safe { background: rgba(220, 232, 255, 0.08); color: #DCE8FF; border: 1px solid rgba(220, 232, 255, 0.22); }
    .og-chip-ok { background: rgba(61, 220, 151, 0.12); color: #7DEBB9; border: 1px solid rgba(61, 220, 151, 0.32); }
    [data-testid="stPlotlyChart"] { border-radius: 16px; overflow: hidden; border: 1px solid rgba(120, 160, 255, 0.14); }

    /* ─── Scrollbar ──────────────────────────────────────────────────── */
    ::-webkit-scrollbar { width: 6px; height: 6px; }
    ::-webkit-scrollbar-track { background: rgba(13, 27, 42, 0.3); }
    ::-webkit-scrollbar-thumb {
        background: rgba(0, 229, 255, 0.3);
        border-radius: 3px;
    }
    ::-webkit-scrollbar-thumb:hover { background: rgba(0, 229, 255, 0.5); }
    </style>
    """, unsafe_allow_html=True)


inject_custom_css()


# ─── Helper Functions ─────────────────────────────────────────────────────────
@st.cache_resource
def load_model():
    """Load the trained collision risk model."""
    from collision_model import CollisionRiskModel
    model = CollisionRiskModel(use_gpu=True)
    try:
        model.load()
        return model, True
    except FileNotFoundError:
        return model, False


@st.cache_data(ttl=3600)
def load_dataset_sample(n_samples: int = 5000):
    """Load a sample from the training dataset for analysis."""
    from data_preprocessing import DataPreprocessor

    preprocessor = DataPreprocessor()
    train_df = pd.read_csv("Dataset/train_data.csv", nrows=n_samples)
    return train_df


@st.cache_data(ttl=3600)
def load_test_sample(n_samples: int = 5000):
    """Load a sample from the held-out test dataset."""
    return pd.read_csv("Dataset/test_data.csv", nrows=n_samples)


def predict_risk(model, df: pd.DataFrame) -> np.ndarray:
    """Model-predicted log10 Pc for raw CDM rows."""
    return model.predict(model.preprocessor.transform(df))


# ─── Constants ────────────────────────────────────────────────────────────────
LEVELS = ["CRITICAL", "HIGH", "MEDIUM", "LOW", "NEGLIGIBLE"]
STATUSES = ["DANGER", "REVIEW", "SAFE", "MITIGATED"]
STATUS_LABEL = {"DANGER": "🔴 DANGER", "REVIEW": "🟠 REVIEW", "SAFE": "⚪ SAFE", "MITIGATED": "🟢 MITIGATED"}
LEVEL_LABEL = {"CRITICAL": "🔴 CRITICAL", "HIGH": "🟠 HIGH", "MEDIUM": "🟡 MEDIUM", "LOW": "🟢 LOW",
               "NEGLIGIBLE": "🔵 NEGLIGIBLE"}
G0 = 9.80665
PLOT_LAYOUT = dict(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(20,20,40,0.8)",
                   font=dict(family="Inter, sans-serif", color="white"))


# ─── Session state ────────────────────────────────────────────────────────────
for key, default in {
    "refresh_nonce": 0,
    "test_mode": False,
    "threat": {"primary_id": 25544, "hours_to_tca": 18.0, "miss_m": 25.0, "crossing_deg": 70.0, "kind": "debris"},
    "extra_watch": [],
    "spacecraft": dict(DEFAULT_SPACECRAFT),
}.items():
    if key not in st.session_state:
        st.session_state[key] = default


# ─── Live data ────────────────────────────────────────────────────────────────
def refresh_bucket() -> int:
    return int(time.time() // DASHBOARD_REFRESH_INTERVAL)


def threat_specs() -> list:
    return [dict(st.session_state.threat)] if st.session_state.test_mode else []


@st.cache_resource(max_entries=3, show_spinner=False)
def get_live_state(bucket: int, nonce: int, extra_watch: tuple, threats_json: str):
    from live_pipeline import run_live
    return run_live(extra_watch=list(extra_watch), threat_specs=json.loads(threats_json), rescreen=nonce > 0)


def live_state():
    with st.spinner("📡 Updating orbits and screening the watchlist (about a minute when new orbit data arrives)…"):
        return get_live_state(refresh_bucket() if st.session_state.refresh_nonce == 0 else 0,
                              st.session_state.refresh_nonce, tuple(st.session_state.extra_watch),
                              json.dumps(threat_specs(), sort_keys=True))


def upcoming(conj: pd.DataFrame) -> pd.DataFrame:
    if conj.empty:
        return conj
    return conj[pd.to_datetime(conj["TCA"], utc=True) > pd.Timestamp.now(tz="UTC")]


def effective_status(conj: pd.DataFrame) -> pd.DataFrame:
    """Mark conjunctions whose avoidance burn the operator accepted as MITIGATED."""
    from decisions import latest
    from manoeuvre_planner import conjunction_key
    conj = conj.copy()
    if conj.empty:
        conj["KEY"], conj["DECISION"] = [], []
        return conj
    decided = latest()
    conj["KEY"] = [conjunction_key(r) for _, r in conj.iterrows()]
    conj["DECISION"] = [decided.get(k, {}).get("decision", "") for k in conj["KEY"]]
    conj.loc[conj["DECISION"] == "ACCEPTED", "STATUS"] = "MITIGATED"
    return conj


def satellite_status(conj: pd.DataFrame, watch_ids: list) -> tuple[dict, dict]:
    """Worst status per watchlist satellite and its worst open conjunction."""
    order = {"DANGER": 3, "REVIEW": 2, "MITIGATED": 1, "SAFE": 0}
    status, worst = {}, {}
    for sid in watch_ids:
        mine = conj[conj["PRIMARY_ID"] == sid] if not conj.empty else conj
        if mine.empty:
            status[sid] = "SAFE"
            continue
        status[sid] = max(mine["STATUS"], key=lambda s: order[s])
        open_ = mine[mine["STATUS"].isin(["DANGER", "REVIEW"])]
        if not open_.empty:
            worst[sid] = open_.sort_values("LOG_PC", ascending=False).iloc[0]
    return status, worst


# ─── Background manoeuvre planning ────────────────────────────────────────────
@st.cache_resource
def plan_registry() -> dict:
    return {}


def _run_plans(state, events: pd.DataFrame, job: dict):
    from manoeuvre_planner import conjunction_key
    try:
        planner = state.planner()
        for _, row in events.iterrows():
            key = conjunction_key(row)
            try:
                job["plans"][key] = planner.plan(row)
            except Exception as e:  # keep planning the others
                job["errors"][key] = f"{type(e).__name__}: {e}"
            job["done"] += 1
    finally:
        job["running"] = False


def plan_job(state) -> dict:
    """Start (once per data version) background planning for every HIGH/CRITICAL conjunction."""
    reg = plan_registry()
    job_key = state.key + json.dumps(threat_specs(), sort_keys=True) + str(sorted(state.watch_ids))
    if job_key not in reg:
        events = upcoming(state.conjunctions)
        events = events[events["STATUS"] == "DANGER"].sort_values("LOG_PC", ascending=False) \
            if not events.empty else events
        job = {"plans": {}, "errors": {}, "total": len(events), "done": 0, "running": True,
               "started": time.time()}
        reg[job_key] = job
        threading.Thread(target=_run_plans, args=(state, events, job), daemon=True).start()
    return reg[job_key]


def option_cost(dv_ms: float) -> tuple[float, float]:
    """Fuel (kg) and burn duration (s) for the operator's spacecraft settings."""
    sc = st.session_state.spacecraft
    return sc["mass_kg"] * (1 - np.exp(-dv_ms / (sc["isp_s"] * G0))), sc["mass_kg"] * dv_ms / sc["thrust_n"]


# ─── Formatting ───────────────────────────────────────────────────────────────
def conj_table(conj: pd.DataFrame) -> pd.DataFrame:
    now = pd.Timestamp.now(tz="UTC")
    tca = pd.to_datetime(conj["TCA"], utc=True)
    df = pd.DataFrame({
        "Status": conj["STATUS"].map(STATUS_LABEL),
        "Risk": conj["RISK_LEVEL"].map(LEVEL_LABEL),
        "Satellite": conj["PRIMARY_NAME"],
        "Other object": conj["SECONDARY_NAME"],
        "Type": conj["SECONDARY_TYPE"],
        "TCA (UTC)": tca.dt.strftime("%Y-%m-%d %H:%M:%S"),
        "Hours to TCA": ((tca - now).dt.total_seconds() / 3600).round(1),
        "Miss (m)": (conj["MISS_KM"] * 1000).round(0),
        "Radial (m)": conj["MISS_R_M"].round(0),
        "Along-track (m)": conj["MISS_T_M"].round(0),
        "Cross-track (m)": conj["MISS_N_M"].round(0),
        "Speed (km/s)": conj["REL_SPEED_KMS"].round(2),
        "log₁₀ Pc": conj["LOG_PC"].round(2),
        "Worst-case log₁₀ Pc": conj["LOG_PC_MAX"].round(2),
        "Pc source": conj["PC_SOURCE"],
    })
    if "OFFICIAL_PC" in conj and conj["OFFICIAL_PC"].notna().any():
        df["Space-Track Pc"] = conj["OFFICIAL_PC"]
    if "DECISION" in conj:
        df["Operator decision"] = conj["DECISION"]
    return df


def status_banner(n_danger: int, n_review: int, n_safe: int, n_mitigated: int = 0):
    """Summary strip above the globe: one tone-coloured headline plus status chips."""
    if n_danger:
        tone, head = "og-danger", (f"{n_danger} satellite{'s' if n_danger != 1 else ''} at high or critical risk "
                                   f"in the next {PROPAGATION_WINDOW_HOURS} h — suggestions on the 🚀 Manoeuvre Planner")
    elif n_review:
        tone, head = "og-review", f"No high-risk events · {n_review} satellite{'s' if n_review != 1 else ''} to review"
    else:
        tone, head = "og-safe", "All watchlist satellites are safe for the screening window"
    chips = (f'<span class="og-chip og-chip-danger">● {n_danger} danger</span>'
             f'<span class="og-chip og-chip-review">● {n_review} review</span>'
             f'<span class="og-chip og-chip-safe">● {n_safe} safe</span>'
             + (f'<span class="og-chip og-chip-ok">● {n_mitigated} manoeuvre accepted</span>' if n_mitigated else ""))
    st.markdown(f'<div class="og-banner {tone}"><div class="og-head">{head}</div><div>{chips}</div></div>',
                unsafe_allow_html=True)


# ─── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("# 🛰️ OrbitGuard AI")
    st.markdown("*AI-Powered Collision Risk Assessment*")
    st.markdown("---")

    page = st.radio(
        "🧭 Navigation",
        [
            "🛰️ Mission Control",
            "🔴 Risk Alerts",
            "🌍 3D Orbit View",
            "🚀 Manoeuvre Planner",
            "🧠 AI Explainability",
            "📊 Model Performance",
            "🧪 Validation",
            "⚙️ Settings",
        ],
        label_visibility="collapsed",
    )

    st.markdown("---")
    st.markdown("### 📡 Data Status")
    if st.button("🔄 Refresh Data", width="stretch"):
        st.session_state.refresh_nonce += 1
        st.cache_data.clear()
        st.rerun()

    @st.fragment(run_every=60)
    def auto_refresh():
        """Re-runs the app when the refresh interval rolls over, so data updates without a click."""
        bucket = refresh_bucket()
        if st.session_state.get("seen_bucket") not in (None, bucket):
            st.session_state.seen_bucket = bucket
            st.session_state.refresh_nonce = 0
            st.rerun(scope="app")
        st.session_state.seen_bucket = bucket
        left = DASHBOARD_REFRESH_INTERVAL - time.time() % DASHBOARD_REFRESH_INTERVAL
        st.caption(f"Auto-refresh in {left / 60:.0f} min · new orbit data every 2 h")

    auto_refresh()

    if st.session_state.test_mode:
        st.warning("🧪 Test mode: a simulated threat is injected")

    model, model_available = load_model()
    if model_available:
        st.success("✅ Model loaded")
        metrics = model.training_metrics
        if metrics:
            st.metric("Val R²", f"{metrics.get('val_r2', 0):.4f}")
            st.metric("Val RMSE", f"{metrics.get('val_rmse', 0):.4f}")
    else:
        st.warning("⚠️ No trained model found")
        st.info("Run `python collision_model.py` to train")

    st.markdown("---")
    st.markdown(
        "<div style='text-align:center;color:rgba(255,255,255,0.3);font-size:0.75rem;'>"
        "OrbitGuard AI v2.0<br>RTX 4060 GPU Accelerated<br>"
        "© 2026 OrbitGuard Team"
        "</div>",
        unsafe_allow_html=True,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# MISSION CONTROL PAGE
# ═══════════════════════════════════════════════════════════════════════════════
if page == "🛰️ Mission Control":
    st.markdown("# 🛰️ OrbitGuard AI — Mission Control")
    st.markdown(f"*Live collision screening of important satellites for the next {PROPAGATION_WINDOW_HOURS} hours*")

    state = live_state()
    conj = effective_status(upcoming(state.conjunctions))
    status, worst = satellite_status(conj, state.watch_ids)
    n_danger = sum(1 for s in status.values() if s == "DANGER")
    n_review = sum(1 for s in status.values() if s == "REVIEW")
    wx = state.weather

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("🛰️ Objects tracked", f"{len(state.objects):,}")
    c2.metric("⭐ Watchlist", len(state.watch_ids))
    c3.metric("🔴 In danger", n_danger)
    c4.metric("🟠 To review", n_review)
    c5.metric("📋 Close approaches", f"{len(conj):,}")
    c6.metric("☀️ F10.7 / Kp", f"{wx['F10']:.0f} / {wx['kp_max'] if wx.get('kp_max') is not None else '–'}")
    st.caption(f"Orbits: {state.catalog.source} · screened {pd.Timestamp(state.t0):%Y-%m-%d %H:%M} UTC · "
               f"space weather {wx.get('date') or 'fallback'} · "
               f"{state.official_cdms} Space-Track official CDMs matched")
    n_mitigated = sum(1 for v in status.values() if v == "MITIGATED")
    status_banner(n_danger, n_review, len(status) - n_danger - n_review - n_mitigated, n_mitigated)

    f1, f2 = st.columns(2)
    show_status = f1.multiselect("Status", STATUSES, default=STATUSES, key="mc_status")
    show_levels = f2.multiselect("Risk level", LEVELS, default=LEVELS, key="mc_levels")
    from live_pipeline import watchlist_summary
    summary = watchlist_summary(state)
    summary["STATUS"] = summary["NORAD_CAT_ID"].map(status)
    view = summary[summary["STATUS"].isin(show_status) & summary["RISK_LEVEL"].isin(show_levels)]

    from orbit_visualizations import create_risk_orbit_view
    now = pd.Timestamp.now(tz="UTC")
    st.plotly_chart(create_risk_orbit_view(state.source, state.objects, view["NORAD_CAT_ID"].tolist(), status, worst,
                                           now_s=(now - pd.Timestamp(state.t0)).total_seconds(),
                                           when=now.to_pydatetime(), height=860),
                    width="stretch", config={"displaylogo": False})
    st.caption("Drag to rotate, scroll to zoom, hover for details, click legend entries to hide them. "
               "Paths show the next orbit; dotted = the other object near closest approach, ✕ = closest-approach point.")

    st.markdown("### ⭐ Risk of important satellites")
    st.dataframe(
        pd.DataFrame({
            "Status": view["STATUS"].map(STATUS_LABEL),
            "Satellite": view["SATELLITE"],
            "NORAD": view["NORAD_CAT_ID"],
            "Altitude (km)": view["ALTITUDE_KM"],
            "Worst risk": view["RISK_LEVEL"].map(LEVEL_LABEL),
            "Max log₁₀ Pc": view["MAX_LOG_PC"].round(2),
            "Closest pass (km)": view["CLOSEST_KM"].round(3),
            "Worst with": view["WORST_WITH"],
            "When (UTC)": pd.to_datetime(view["WORST_TCA"], utc=True).dt.strftime("%d %b %H:%M"),
            "Close approaches": view["CONJUNCTIONS"],
        }),
        width="stretch", hide_index=True, height=min(60 + 35 * len(view), 520),
    )


# ═══════════════════════════════════════════════════════════════════════════════
# RISK ALERTS PAGE
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "🔴 Risk Alerts":
    st.markdown("# 🔴 Conjunction Risk Alerts")
    st.markdown("*Every close approach (< 10 km) of a watchlist satellite in the screening window*")

    state = live_state()
    conj = effective_status(upcoming(state.conjunctions))

    f1, f2, f3 = st.columns(3)
    levels = f1.multiselect("Risk level", LEVELS, default=["CRITICAL", "HIGH", "MEDIUM"])
    statuses = f2.multiselect("Status", STATUSES, default=STATUSES)
    sats = f3.multiselect("Satellite", sorted(conj["PRIMARY_NAME"].unique()) if not conj.empty else [])
    f4, f5, f6 = st.columns(3)
    types = f4.multiselect("Other object type", ["PAYLOAD", "DEBRIS", "ROCKET BODY", "UNKNOWN"],
                           default=["PAYLOAD", "DEBRIS", "ROCKET BODY", "UNKNOWN"])
    max_hours = f5.slider("Within the next (hours)", 1, PROPAGATION_WINDOW_HOURS, PROPAGATION_WINDOW_HOURS)
    max_miss = f6.slider("Miss distance under (km)", 0.1, 10.0, 10.0, 0.1)

    view = conj
    if not view.empty:
        hours = (pd.to_datetime(view["TCA"], utc=True) - pd.Timestamp.now(tz="UTC")).dt.total_seconds() / 3600
        view = view[view["RISK_LEVEL"].isin(levels) & view["STATUS"].isin(statuses)
                    & view["SECONDARY_TYPE"].fillna("UNKNOWN").isin(types)
                    & (hours <= max_hours) & (view["MISS_KM"] <= max_miss)]
        if sats:
            view = view[view["PRIMARY_NAME"].isin(sats)]
        view = view.sort_values("LOG_PC", ascending=False)

    c = st.columns(5)
    for col, lvl in zip(c, LEVELS):
        col.metric(LEVEL_LABEL[lvl], int((view["RISK_LEVEL"] == lvl).sum()) if not view.empty else 0)

    st.markdown(f"### 📋 {len(view):,} close approaches")
    if view.empty:
        st.info("No close approaches match these filters.")
    else:
        st.dataframe(conj_table(view), width="stretch", hide_index=True, height=520,
                     column_config={"Space-Track Pc": st.column_config.NumberColumn(format="%.2e")})
        st.caption("Pc = probability of collision. Our Pc uses public orbits (SGP4) with uncertainty from the ML "
                   "model plus assumed TLE error; Space-Track's official Pc replaces it when a public CDM exists. "
                   "Worst-case Pc assumes the least favourable uncertainty size.")


# ═══════════════════════════════════════════════════════════════════════════════
# 3D ORBIT VIEW PAGE
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "🌍 3D Orbit View":
    st.markdown("# 🌍 3D Orbit View")
    state = live_state()
    conj = effective_status(upcoming(state.conjunctions))
    status, worst = satellite_status(conj, state.watch_ids)

    tab1, tab2 = st.tabs(["🌐 Risk View", "🔍 Catalogue"])
    with tab1:
        names = {sid: state.objects.loc[sid, "OBJECT_NAME"] for sid in state.watch_ids}
        only_risk = st.toggle("Show only satellites at risk", value=False)
        default = [s for s in state.watch_ids if not only_risk or status.get(s) in ("DANGER", "REVIEW")]
        chosen = st.multiselect("Satellites", state.watch_ids, default=default, format_func=lambda s: names[s])

        from decisions import latest
        from orbit_propagation import burn_offset
        planned = {}
        for entry in latest().values():
            opt = entry.get("option")
            if entry["decision"] != "ACCEPTED" or not opt or opt.get("mover_id") not in chosen:
                continue
            burn_s = (pd.Timestamp(opt["burn_time"]) - pd.Timestamp(state.t0)).total_seconds()
            tca_s = (pd.Timestamp(entry["tca"]) - pd.Timestamp(state.t0)).total_seconds()
            if tca_s < 0:
                continue
            r, v = state.source.state(opt["mover_id"], burn_s)
            if np.all(np.isfinite(r)):
                off = burn_offset(np.concatenate([r[0], v[0]]), burn_s, np.array(opt["dv_rtn_ms"]),
                                  tca_s + 6000.0)
                planned[opt["mover_id"]] = (off, burn_s, tca_s)

        from orbit_visualizations import create_risk_orbit_view
        now = pd.Timestamp.now(tz="UTC")
        st.plotly_chart(create_risk_orbit_view(state.source, state.objects, chosen, status, worst, planned,
                                               now_s=(now - pd.Timestamp(state.t0)).total_seconds(),
                                               when=now.to_pydatetime(), height=900),
                        width="stretch", config={"displaylogo": False})
        st.caption("Paths show the next orbit from now. For red/orange satellites the other object's path "
                   "±15 min around the closest approach is dashed, and ✕ marks the closest-approach point.")

    with tab2:
        search = st.text_input("🔍 Search by name or NORAD ID")
        cat = state.objects.reset_index(names="NORAD_CAT_ID")
        if search:
            cat = cat[cat["OBJECT_NAME"].str.contains(search, case=False, na=False)
                      | cat["NORAD_CAT_ID"].astype(str).str.contains(search)]
        st.markdown(f"**{len(cat):,} objects** · source: {state.catalog.source}")
        st.dataframe(cat[["NORAD_CAT_ID", "OBJECT_NAME", "OBJECT_TYPE", "OWNER", "PERIGEE_KM", "APOGEE_KM",
                          "INCLINATION", "EPOCH_AGE_DAYS", "RADIUS_M", "MANOEUVRABLE"]].head(500).round(2),
                     width="stretch", hide_index=True, height=480)


# ═══════════════════════════════════════════════════════════════════════════════
# MANOEUVRE PLANNER PAGE
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "🚀 Manoeuvre Planner":
    st.markdown("# 🚀 Collision Avoidance Manoeuvre Planner")
    st.markdown(f"*Automatic burn suggestions for every HIGH/CRITICAL conjunction — target: risk below "
                f"10^{MANOEUVRE_TARGET_LOG_PC:.0f} and at least {MANOEUVRE_TARGET_MISS_KM:g} km apart, "
                f"without creating new high-risk approaches*")

    with st.expander("⚙️ Spacecraft parameters (used for fuel and burn duration)", expanded=False):
        sc = st.session_state.spacecraft
        c1, c2, c3 = st.columns(3)
        sc["mass_kg"] = c1.number_input("Mass (kg)", 10.0, 500000.0, float(sc["mass_kg"]), 10.0)
        sc["isp_s"] = c2.number_input("Thruster Isp (s)", 50.0, 5000.0, float(sc["isp_s"]), 10.0)
        sc["thrust_n"] = c3.number_input("Thrust (N)", 0.001, 5000.0, float(sc["thrust_n"]), 0.1)

    state = live_state()
    job = plan_job(state)

    from decisions import latest, history, record

    @st.fragment(run_every=5 if job["running"] else None)
    def planner_view():
        conj = effective_status(upcoming(state.conjunctions))
        events = conj[conj["STATUS"].isin(["DANGER", "MITIGATED"])].sort_values("LOG_PC", ascending=False) \
            if not conj.empty else conj
        if job["running"]:
            st.progress(job["done"] / max(job["total"], 1),
                        text=f"Planning manoeuvres… {job['done']} of {job['total']} conjunctions done")
        if events.empty:
            st.success("No HIGH or CRITICAL conjunctions — no manoeuvre needed.")
            return
        decided = latest()
        for _, ev in events.iterrows():
            key = ev["KEY"]
            plan = job["plans"].get(key)
            box = st.container(border=True)
            css = "risk-low" if ev["STATUS"] == "MITIGATED" else "risk-critical"
            box.markdown(
                f'<div class="{css}"><b>{STATUS_LABEL[ev["STATUS"]]} · {LEVEL_LABEL[ev["RISK_LEVEL"]]}</b> &nbsp; '
                f'<b>{ev["PRIMARY_NAME"]}</b> vs <b>{ev["SECONDARY_NAME"]}</b> ({ev["SECONDARY_TYPE"]}) &nbsp;|&nbsp; '
                f'TCA <code>{pd.Timestamp(ev["TCA"]):%Y-%m-%d %H:%M:%S} UTC</code> &nbsp;|&nbsp; '
                f'miss <code>{ev["MISS_KM"] * 1000:,.0f} m</code> &nbsp;|&nbsp; '
                f'log₁₀ Pc <code>{ev["LOG_PC"]:.2f}</code> &nbsp;|&nbsp; '
                f'speed <code>{ev["REL_SPEED_KMS"]:.1f} km/s</code></div>', unsafe_allow_html=True)
            if plan is None:
                msg = job["errors"].get(key)
                if msg:
                    box.error(f"Planning failed: {msg}")
                else:
                    box.info("⏳ Computing manoeuvre options…")
                continue

            box.markdown(f"**Suggestion:** {plan.summary}")
            options = [o for o in [plan.recommended, plan.alternative] if o is not None]
            options += [o for o in plan.primary_options + plan.secondary_options
                        if o.verified_miss_km is not None and o not in options][:6]
            if options:
                rows = []
                for i, o in enumerate(options):
                    fuel, dur = option_cost(o.dv_ms)
                    rows.append({
                        "Option": "⭐ Recommended" if o is plan.recommended else ("Alternative" if o is plan.alternative else f"Option {i + 1}"),
                        "Who moves": f"{o.mover_name} ({'this satellite' if o.role == 'primary' else 'other operator'})",
                        "Burn time (UTC)": f"{o.burn_time:%Y-%m-%d %H:%M:%S}",
                        "Lead": f"{o.lead_orbits:g} orbits ({o.lead_hours:.1f} h)",
                        "Direction": o.direction,
                        "ΔV (cm/s)": round(o.dv_ms * 100, 2),
                        "Burn time (s)": round(dur, 1),
                        "Fuel (g)": round(fuel * 1000, 1),
                        "Altitude change (m)": round(o.delta_sma_km * 1000),
                        "New miss (km)": round(o.verified_miss_km if o.verified_miss_km is not None else o.new_miss_km, 2),
                        "New log₁₀ Pc": round(o.verified_log_pc if o.verified_log_pc is not None else o.new_log_pc, 2),
                        "New conflicts": ("none" if o.clean else (f"{len(o.conflicts)} high-risk" if o.conflict_checked else "not checked")),
                    })
                box.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)
            for note in plan.notes:
                box.caption(f"ℹ️ {note}")
            if plan.recommended and plan.recommended.conflicts:
                box.dataframe(pd.DataFrame(plan.recommended.conflicts), width="stretch", hide_index=True)

            prior = decided.get(key)
            if prior:
                icon = "✅" if prior["decision"] == "ACCEPTED" else "❌"
                box.markdown(f"{icon} **{prior['decision']}** at {prior['time']} UTC"
                             + (f" — {prior['option']['direction']} {prior['option']['dv_ms'] * 100:.2f} cm/s"
                                if prior.get("option") else ""))
            if options:
                labels = [f"{r['Option']}: {r['Who moves']}, {r['Direction']} {r['ΔV (cm/s)']} cm/s at {r['Burn time (UTC)']}"
                          for r in rows]
                pick = labels.index(box.selectbox("Option", labels, key=f"opt_{key}"))
                note = box.text_input("Operator note (optional)", key=f"note_{key}")
                b1, b2 = box.columns(2)
                if b1.button("✅ Accept", key=f"acc_{key}", width="stretch"):
                    record(plan, options[pick], "ACCEPTED", note)
                    st.rerun(scope="app")
                if b2.button("❌ Decline", key=f"dec_{key}", width="stretch"):
                    record(plan, options[pick], "DECLINED", note)
                    st.rerun(scope="app")

    planner_view()

    hist = history()
    if hist:
        st.markdown("### 🗂️ Decision log")
        st.dataframe(pd.DataFrame([{
            "Time (UTC)": h["time"], "Decision": h["decision"], "Satellite": h["primary"], "Other": h["secondary"],
            "TCA": h["tca"], "Moves": (h.get("option") or {}).get("mover_name"),
            "Direction": (h.get("option") or {}).get("direction"),
            "ΔV (cm/s)": round((h.get("option") or {}).get("dv_ms", 0) * 100, 2), "Note": h.get("note", ""),
        } for h in reversed(hist)]), width="stretch", hide_index=True)
        st.caption("Saved to logs/manoeuvre_decisions.jsonl. Accepted burns appear as green dashed paths in the 3D view.")


# ═══════════════════════════════════════════════════════════════════════════════
# AI EXPLAINABILITY PAGE
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "🧠 AI Explainability":
    st.markdown("# 🧠 AI Explainability — SHAP Analysis")
    st.markdown("*Understand WHY the model predicts specific risk levels*")

    if not model_available:
        st.warning("⚠️ Train the model first by running: `python collision_model.py`")
        st.info("Once trained, this page will show SHAP feature importance, waterfall charts, and dependence plots.")

        # Show placeholder with dataset features
        st.markdown("### 📊 Dataset Feature Preview")
        try:
            sample = load_dataset_sample(100)
            st.dataframe(sample.head(10), width="stretch", height=300)

            st.markdown("### 🔧 Key Features in the Model")
            feature_descriptions = {
                "miss_distance": "Closest approach distance between objects (meters)",
                "relative_speed": "Relative velocity between objects (m/s)",
                "time_to_tca": "Time until closest approach (days)",
                "mahalanobis_distance": "Statistical distance accounting for covariance",
                "max_risk_estimate": "Maximum risk estimate from CDM",
                "t_sigma_r/t/n": "Target position uncertainty in R/T/N frame",
                "c_sigma_r/t/n": "Chaser position uncertainty in R/T/N frame",
                "t_j2k_sma": "Target semi-major axis (km)",
                "relative_position_r/t/n": "Relative position in R/T/N frame (m)",
            }
            for feat, desc in feature_descriptions.items():
                st.markdown(f"- **`{feat}`**: {desc}")

        except Exception as e:
            st.error(f"Error: {e}")

    else:
        from explainability import RiskExplainer

        try:
            explainer = RiskExplainer(model.model, model.feature_names)

            tab1, tab2, tab3 = st.tabs(["📊 Feature Importance", "🔍 Single Event", "📈 Dependence"])

            with tab1:
                st.markdown("### Global Feature Importance")
                sample_df = load_dataset_sample(2000)
                X_sample = model.preprocessor.transform(sample_df)

                fig = explainer.create_summary_plot(X_sample)
                st.plotly_chart(fig, width="stretch")

            with tab2:
                st.markdown("### Single Event Explanation")
                event_idx = st.number_input("Event index", 0, len(X_sample) - 1, 0)

                fig = explainer.create_waterfall_chart(X_sample[event_idx])
                st.plotly_chart(fig, width="stretch")

                narrative = explainer.generate_narrative(X_sample[event_idx])
                st.markdown(narrative)

            with tab3:
                st.markdown("### Feature Dependence")
                top_feats = model.get_feature_importance()["feature"].head(20).tolist()
                feat = st.selectbox("Select feature", top_feats)
                fig = explainer.create_dependence_plot(X_sample, feat)
                st.plotly_chart(fig, width="stretch")

        except Exception as e:
            st.error(f"Explainability error: {e}")


    # ─── Live uncertainty model ──────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### 🌦️ Live uncertainty model — what drives orbit uncertainty")
    st.markdown("Public orbit data has no uncertainty, so OrbitGuard predicts it from altitude, object type, size, "
                "time to closest approach, time since last observation and **space weather**. "
                "Bars show each input's share of the model's gain for each predicted quantity.")
    from uncertainty_model import UncertaintyModel
    if UncertaintyModel.exists():
        um = UncertaintyModel.load()
        imp = um.feature_importance()
        imp = imp / imp.sum(axis=0)
        names = {"log_sigma_r": "radial σ", "log_sigma_t": "along-track σ", "log_sigma_n": "cross-track σ",
                 "corr_tr": "corr R–T", "corr_nr": "corr R–N", "corr_nt": "corr T–N"}
        long = imp.rename(columns=names).reset_index(names="input").melt(id_vars="input", var_name="output",
                                                                          value_name="share")
        fig = px.bar(long, x="share", y="input", color="output", orientation="h", barmode="group", height=520)
        fig.update_layout(**PLOT_LAYOUT, xaxis_tickformat=".0%")
        st.plotly_chart(fig, width="stretch")
        wx_share = imp.loc[[c for c in ["F10", "F3M", "SSN", "AP"] if c in imp.index]].sum()
        st.caption("Space weather (F10.7, its 81-day mean, sunspot number, Ap) share: "
                   + ", ".join(f"{names[k]} {v:.0%}" for k, v in wx_share.items()))
    else:
        st.info("Train it with `python uncertainty_model.py`.")


# ═══════════════════════════════════════════════════════════════════════════════
# MODEL PERFORMANCE PAGE
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "📊 Model Performance":
    st.markdown("# 📊 Model Performance & Diagnostics")

    if model_available:
        metrics = model.training_metrics

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Train RMSE", f"{metrics.get('train_rmse', 0):.4f}")
        with col2:
            st.metric("Val RMSE", f"{metrics.get('val_rmse', 0):.4f}")
        with col3:
            st.metric("Val R²", f"{metrics.get('val_r2', 0):.4f}")
        with col4:
            st.metric("Train Time", f"{metrics.get('training_time_seconds', 0):.1f}s")

        if "test_r2" in metrics:
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Test RMSE", f"{metrics['test_rmse']:.4f}")
            with col2:
                st.metric("Test R²", f"{metrics['test_r2']:.4f}")
            with col3:
                st.metric("Alert Precision", f"{metrics.get('test_alert_precision', 0):.3f}")
            with col4:
                st.metric("Alert Recall", f"{metrics.get('test_alert_recall', 0):.3f}")
            st.caption(
                f"Alerts = events with risk ≥ {metrics.get('test_alert_threshold', -4.5)} log₁₀ Pc. "
                "Validation rows are split by event, so no event appears in both train and validation."
            )

        st.markdown("---")

        # Predicted vs actual on held-out test data
        st.markdown("### 🎯 Predicted vs. Actual Risk (Test Set)")
        try:
            test_df = load_test_sample(5000)
            pred = predict_risk(model, test_df)
            fig = go.Figure()
            fig.add_trace(go.Scattergl(
                x=test_df["risk"], y=pred, mode="markers",
                marker=dict(size=4, color="rgba(0,229,255,0.45)"),
                hovertemplate="Actual: %{x:.3f}<br>Predicted: %{y:.3f}<extra></extra>",
                name="Events",
            ))
            fig.add_trace(go.Scatter(
                x=[-30, 0], y=[-30, 0], mode="lines",
                line=dict(color="rgba(255,255,255,0.4)", dash="dash"), name="Perfect",
            ))
            fig.update_layout(
                xaxis_title="Actual risk (log₁₀ Pc)",
                yaxis_title="Predicted risk (log₁₀ Pc)",
                template="plotly_dark",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(20,20,40,0.8)",
                height=500,
                font=dict(family="Inter, sans-serif", color="white"),
            )
            st.plotly_chart(fig, width="stretch")
        except Exception as e:
            st.error(f"Prediction error: {e}")

        st.markdown("---")

        # Feature importance
        st.markdown("### 🏆 Feature Importance (XGBoost Gain)")
        try:
            fi_df = model.get_feature_importance()
            top_n = st.slider("Top N features", 5, 50, 20)

            fig = go.Figure()
            fi_top = fi_df.head(top_n)

            fig.add_trace(go.Bar(
                y=fi_top["feature"][::-1],
                x=fi_top["importance"][::-1],
                orientation="h",
                marker=dict(
                    color=fi_top["importance"][::-1],
                    colorscale="Turbo",
                    showscale=True,
                ),
            ))

            fig.update_layout(
                title=dict(text=f"Top {top_n} Features by Gain", font=dict(color="white", size=14)),
                template="plotly_dark",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(20,20,40,0.8)",
                height=600,
                margin=dict(l=250),
                font=dict(family="Inter, sans-serif", color="white"),
            )
            st.plotly_chart(fig, width="stretch")
        except Exception as e:
            st.error(f"Feature importance error: {e}")

        # Model info
        st.markdown("---")
        st.markdown("### ⚙️ Model Configuration")
        st.json(metrics)

    else:
        st.warning("⚠️ No trained model available.")
        st.markdown("""
        ### 🚀 How to Train

        Run the following command to train the model with GPU acceleration:

        ```bash
        python collision_model.py
        ```

        This will:
        1. Load the CDM conjunction dataset (162K+ events)
        2. Engineer 100+ features
        3. Train XGBoost with CUDA on your RTX 4060
        4. Save the model to `models/orbitguard_model.json`
        """)



# ═══════════════════════════════════════════════════════════════════════════════
# VALIDATION PAGE
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "🧪 Validation":
    st.markdown("# 🧪 Validation — is the risk and manoeuvre logic correct?")
    st.markdown("Run `python validate.py` (about 5 minutes) to regenerate this report, and `python -m pytest tests` "
                "for the fast unit checks.")
    report_path = EXPORT_DIR / "validation_report.json"
    if not report_path.exists():
        st.warning("No validation report yet. Run `python validate.py`.")
    else:
        report = json.loads(report_path.read_text())
        checks = report["checks"]
        passed = sum(1 for c in checks if c["passed"])
        skipped = sum(1 for c in checks if c["passed"] is None)
        c1, c2, c3 = st.columns(3)
        c1.metric("Checks passed", f"{passed} / {len(checks) - skipped}")
        c2.metric("Skipped", skipped, help="Space-Track checks need credentials")
        c3.metric("Generated", report["generated_at"][:16].replace("T", " ") + " UTC")
        for section in dict.fromkeys(c["section"] for c in checks):
            st.markdown(f"### {section}")
            for c in [c for c in checks if c["section"] == section]:
                box = st.container(border=True)
                icon = {True: "✅", False: "❌", None: "⏭️"}[c["passed"]]
                box.markdown(f"{icon} **{c['name']}**")
                box.caption(c["what"])
                box.markdown(f"Result: **{c['result']}** · Pass rule: {c['criterion']}")
                if c.get("table"):
                    box.dataframe(pd.DataFrame(c["table"]), width="stretch", hide_index=True)


# ═══════════════════════════════════════════════════════════════════════════════
# SETTINGS PAGE
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "⚙️ Settings":
    st.markdown("# ⚙️ Settings")
    import spacetrack_client
    from space_weather import load_space_weather, storm_level

    st.markdown("### 📡 Data sources")
    state = live_state()
    c1, c2, c3 = st.columns(3)
    c1.metric("Orbit catalogue", state.catalog.source.split(" (")[0], f"{len(state.catalog.objects):,} objects")
    c2.metric("Space-Track", "connected" if spacetrack_client.is_configured() else "not configured",
              f"{state.official_cdms} official CDMs matched")
    c3.metric("Space weather", state.weather.get("date") or "fallback", storm_level(state.weather.get("kp_max")))
    if not spacetrack_client.is_configured():
        st.info("To use Space-Track (full catalogue + official conjunction messages), create a free account at "
                "space-track.org and add a `.env` file in the project folder:\n\n"
                "```\nSPACETRACK_USER=you@example.com\nSPACETRACK_PASSWORD=your-password\n```\n"
                "`.env` is git-ignored. Restart the app afterwards.")

    sw = load_space_weather()
    if not sw.empty:
        recent = sw[sw["AP_AVG"].notna() & (sw.index <= pd.Timestamp.now().normalize())].tail(120)  # observed only
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=recent.index, y=recent["F10.7_OBS"], name="F10.7 (sfu)", line=dict(color="#FFD700")))
        fig.add_trace(go.Bar(x=recent.index, y=recent["AP_AVG"], name="Ap", yaxis="y2", marker_color="rgba(124,77,255,0.6)"))
        fig.update_layout(**PLOT_LAYOUT, height=320, title="Space weather — last 120 days",
                          yaxis=dict(title="F10.7"), yaxis2=dict(title="Ap", overlaying="y", side="right"))
        st.plotly_chart(fig, width="stretch")

    st.markdown("---")
    st.markdown("### ⭐ Watchlist")
    st.caption(f"{len(IMPORTANT_SATELLITES)} important satellites are always screened (config.IMPORTANT_SATELLITES). "
               "Add more here; each extra satellite adds a few seconds to screening.")
    payloads = state.catalog.objects[state.catalog.objects["OBJECT_TYPE"] == "PAYLOAD"]
    options = [i for i in payloads.index if i not in IMPORTANT_SATELLITES]
    extra = st.multiselect("Extra satellites", options, default=st.session_state.extra_watch,
                           format_func=lambda i: f"{payloads.loc[i, 'OBJECT_NAME']} ({i})")
    if extra != st.session_state.extra_watch:
        st.session_state.extra_watch = extra
        st.rerun()

    st.markdown("---")
    st.markdown("### 🧪 Test scenario")
    st.caption("Injects a simulated object on a known collision course with a watchlist satellite, so you can see "
               "the red alert, the 3D path and the manoeuvre suggestion end to end. Real data is not changed.")
    t = dict(st.session_state.threat)
    enabled = st.toggle("Inject a simulated threat", value=st.session_state.test_mode)
    names = {sid: state.catalog.objects.loc[sid, "OBJECT_NAME"] for sid in state.catalog.watchlist_ids()}
    c1, c2 = st.columns(2)
    t["primary_id"] = c1.selectbox("Satellite", list(names), index=list(names).index(t["primary_id"]) if t["primary_id"] in names else 0,
                                   format_func=lambda s: names[s])
    t["kind"] = c2.radio("Threat", ["debris", "satellite"], index=0 if t["kind"] == "debris" else 1, horizontal=True,
                         format_func=lambda k: "Debris (cannot move)" if k == "debris" else "Working satellite (can move)")
    c3, c4, c5 = st.columns(3)
    t["hours_to_tca"] = c3.slider("Hours until closest approach", 3.0, 60.0, float(t["hours_to_tca"]), 1.0)
    t["miss_m"] = c4.slider("Miss distance (m)", 0.0, 2000.0, float(t["miss_m"]), 5.0)
    t["crossing_deg"] = c5.slider("Crossing angle (°)", 10.0, 170.0, float(t["crossing_deg"]), 5.0)
    if enabled != st.session_state.test_mode or t != st.session_state.threat:
        st.session_state.test_mode, st.session_state.threat = enabled, t
        st.rerun()

    st.markdown("---")
    st.markdown("### 🎯 Model accuracy")
    from collision_model import EVAL_PATH
    if EVAL_PATH.exists():
        ev = json.loads(EVAL_PATH.read_text())
        st.markdown("**CDM risk model (XGBoost, 118 features)** — scored on the same event-grouped train / "
                    "validation split used in training and on the held-out test file.")
        cols = st.columns(3)
        for col, split in zip(cols, ["train", "validation", "test"]):
            m = ev[split]
            col.metric(f"{split.title()} R²", f"{m['r2']:.4f}", help=f"{m['rows']:,} rows")
            col.metric(f"{split.title()} alert accuracy", f"{m['alert_accuracy']:.2%}",
                       help="Share of rows where the model and ESA agree on high risk (log10 Pc ≥ −4.5) or not")
        st.dataframe(pd.DataFrame([{
            "Split": split.title(), "Rows": f"{m['rows']:,}", "R²": round(m["r2"], 4),
            "RMSE (log₁₀ Pc)": round(m["rmse"], 3), "MAE (log₁₀ Pc)": round(m["mae"], 3),
            "Alert accuracy": f"{m['alert_accuracy']:.2%}", "Alert precision": f"{m['alert_precision']:.3f}",
            "Alert recall": f"{m['alert_recall']:.3f}", "Alert F1": f"{m['alert_f1']:.3f}",
        } for split, m in ev.items()]), width="stretch", hide_index=True)
        st.caption("Alert accuracy is high partly because only 1–2% of rows are high-risk; precision and recall "
                   "show how well those rare alerts are caught.")
    else:
        st.info("Score the CDM model on train / validation / test with "
                "`python -c \"from collision_model import evaluate_splits; evaluate_splits()\"`.")

    from uncertainty_model import UNCERTAINTY_DIR
    um_meta = UNCERTAINTY_DIR / "meta.json"
    if um_meta.exists():
        um = json.loads(um_meta.read_text())["metrics"]
        st.markdown("**Live uncertainty model** — typical error on held-out CDMs (as a factor; 1.5× = within 50%), "
                    "compared with a per-object-type baseline.")
        st.dataframe(pd.DataFrame([{
            "Predicts": label, "ML error": f"{10 ** um[k + '_mae']:.2f}×",
            "Baseline error": f"{10 ** um[k + '_baseline_mae']:.2f}×",
        } for k, label in [("log_sigma_r", "Radial uncertainty"), ("log_sigma_t", "Along-track uncertainty"),
                           ("log_sigma_n", "Cross-track uncertainty")]]), width="stretch", hide_index=True)

    report_path = EXPORT_DIR / "validation_report.json"
    if report_path.exists():
        rep = json.loads(report_path.read_text())
        checks = rep["checks"]
        ok = sum(1 for c in checks if c["passed"])
        skipped = sum(1 for c in checks if c["passed"] is None)
        a1 = next((c for c in checks if c["name"].startswith("A1")), None)
        st.markdown(f"**Validation** ({rep['generated_at'][:10]}): {ok} of {len(checks) - skipped} checks passed"
                    + (f", {skipped} skipped" if skipped else "")
                    + (f" · risk engine vs ESA: {a1['result']}" if a1 else "") + " — details on the 🧪 Validation page.")
    else:
        st.caption("Validation not run yet — `python validate.py`.")

    st.markdown("---")
    st.markdown("### 🖥️ GPU Status")
    try:
        import subprocess
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total,memory.used,memory.free,temperature.gpu,utilization.gpu",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True,
        )
        if result.returncode == 0:
            parts = result.stdout.strip().split(", ")
            if len(parts) >= 6:
                col1, col2, col3 = st.columns(3)
                col1.metric("🖥️ GPU", parts[0])
                col1.metric("🌡️ Temperature", f"{parts[4]}°C")
                col2.metric("💾 VRAM Total", f"{parts[1]} MB")
                col2.metric("📊 VRAM Used", f"{parts[2]} MB")
                col3.metric("📈 GPU Utilization", f"{parts[5]}%")
                col3.metric("💾 VRAM Free", f"{parts[3]} MB")
    except Exception:
        st.info("GPU info unavailable")

    st.markdown("---")
    st.markdown("### 🔧 Configuration")
    import config
    st.json({
        "screening": {"window_hours": config.PROPAGATION_WINDOW_HOURS, "step_s": config.PROPAGATION_STEP_SECONDS,
                      "report_within_km": config.SCREENING_DISTANCE_KM},
        "risk_levels_log10_pc": {k: v for k, v in config.RISK_LEVELS.items() if v != float("-inf")},
        "review_if_miss_under_km": config.REVIEW_MISS_DISTANCE_KM,
        "assumed_tle_sigma_km (at epoch, per day)": config.TLE_SIGMA_KM,
        "manoeuvre_target": {"log10_pc": config.MANOEUVRE_TARGET_LOG_PC, "miss_km": config.MANOEUVRE_TARGET_MISS_KM,
                             "max_dv_ms": config.MANOEUVRE_MAX_DV},
        "auto_refresh_s": config.DASHBOARD_REFRESH_INTERVAL,
    })
