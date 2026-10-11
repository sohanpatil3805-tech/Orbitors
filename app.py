"""
OrbitGuard AI — Streamlit Dashboard
Real-time satellite collision risk assessment with explainable AI.
"""

import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from pathlib import Path
import time
import json

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


# ─── Session State Initialization ─────────────────────────────────────────────
if "model_loaded" not in st.session_state:
    st.session_state.model_loaded = False
if "celestrak_data" not in st.session_state:
    st.session_state.celestrak_data = None
if "last_refresh" not in st.session_state:
    st.session_state.last_refresh = None


# ─── Helper Functions ─────────────────────────────────────────────────────────
@st.cache_data(ttl=300)
def load_celestrak_data():
    """Fetch and cache CelesTrak live data."""
    from celestrak_fetcher import CelesTrakFetcher, compute_orbit_altitude_band

    fetcher = CelesTrakFetcher()
    active = fetcher.fetch_active_satellites()
    debris = fetcher.fetch_all_debris()
    stations = fetcher.fetch_stations()

    if not active.empty:
        active = compute_orbit_altitude_band(active)

    return {
        "active": active,
        "debris": debris,
        "stations": stations,
        "timestamp": pd.Timestamp.now(tz="UTC"),
        "summary": fetcher.get_catalog_summary(),
    }


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


def get_risk_badge(risk_value: float) -> str:
    """Return an HTML badge for a risk level."""
    if risk_value >= -3.0:
        return '<span style="background:#FF0040;color:white;padding:4px 12px;border-radius:20px;font-weight:600;font-size:0.85rem;">🔴 CRITICAL</span>'
    elif risk_value >= -4.5:
        return '<span style="background:#FF6B35;color:white;padding:4px 12px;border-radius:20px;font-weight:600;font-size:0.85rem;">🟠 HIGH</span>'
    elif risk_value >= -6.0:
        return '<span style="background:#FFD700;color:#1a1a1a;padding:4px 12px;border-radius:20px;font-weight:600;font-size:0.85rem;">🟡 MEDIUM</span>'
    elif risk_value >= -7.5:
        return '<span style="background:#00E676;color:#1a1a1a;padding:4px 12px;border-radius:20px;font-weight:600;font-size:0.85rem;">🟢 LOW</span>'
    else:
        return '<span style="background:#40C4FF;color:#1a1a1a;padding:4px 12px;border-radius:20px;font-weight:600;font-size:0.85rem;">🔵 NEGLIGIBLE</span>'


# ─── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("# 🛰️ OrbitGuard AI")
    st.markdown("*AI-Powered Collision Risk Assessment*")
    st.markdown("---")

    # Navigation
    page = st.radio(
        "🧭 Navigation",
        [
            "🏠 Dashboard",
            "🔴 Risk Alerts",
            "🌍 Live Tracking",
            "🧠 AI Explainability",
            "🚀 Manoeuvre Planner",
            "📊 Model Performance",
            "⚙️ Settings",
        ],
        label_visibility="collapsed",
    )

    st.markdown("---")

    # Data refresh
    st.markdown("### 📡 Data Status")
    if st.button("🔄 Refresh CelesTrak Data", width="stretch"):
        st.cache_data.clear()
        st.rerun()

    # Model status
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
        "OrbitGuard AI v1.0<br>RTX 4060 GPU Accelerated<br>"
        "© 2026 OrbitGuard Team"
        "</div>",
        unsafe_allow_html=True,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# DASHBOARD PAGE
# ═══════════════════════════════════════════════════════════════════════════════
if page == "🏠 Dashboard":
    st.markdown("# 🛰️ OrbitGuard AI — Mission Control")
    st.markdown("*Real-time collision risk assessment for Low Earth Orbit*")

    # Live data loading
    with st.spinner("📡 Fetching live orbital data from CelesTrak..."):
        data = load_celestrak_data()

    # ─── Key Metrics Row ──────────────────────────────────────────────────
    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        active_count = len(data["active"]) if data["active"] is not None and not data["active"].empty else 0
        st.metric("🛰️ Active Satellites", f"{active_count:,}")

    with col2:
        debris_count = len(data["debris"]) if data["debris"] is not None and not data["debris"].empty else 0
        st.metric("💥 Tracked Debris", f"{debris_count:,}")

    with col3:
        station_count = len(data["stations"]) if data["stations"] is not None and not data["stations"].empty else 0
        st.metric("🏗️ Space Stations", f"{station_count:,}")

    with col4:
        total = active_count + debris_count
        st.metric("📊 Total Objects", f"{total:,}")

    with col5:
        st.metric("⏱️ Last Update", data["timestamp"].strftime("%H:%M UTC"))

    st.markdown("---")

    # ─── Orbit Distribution & Risk Overview ───────────────────────────────
    col_left, col_right = st.columns([3, 2])

    with col_left:
        st.markdown("### 🌐 Orbital Population by Altitude")
        if not data["active"].empty:
            from orbit_visualizations import create_altitude_distribution
            fig = create_altitude_distribution(data["active"])
            st.plotly_chart(fig, width="stretch")

    with col_right:
        st.markdown("### 📋 Catalog Summary")
        if data["summary"]:
            summary_df = pd.DataFrame(
                [{"Category": k, "Count": v} for k, v in data["summary"].items()]
            ).sort_values("Count", ascending=False)
            st.dataframe(
                summary_df,
                width="stretch",
                hide_index=True,
                height=400,
            )

    # ─── Recent Conjunction Analysis (from dataset) ───────────────────────
    st.markdown("---")
    st.markdown("### 🔍 Conjunction Analysis — Training Data Overview")

    try:
        sample_df = load_dataset_sample(10000)

        col1, col2 = st.columns(2)

        with col1:
            # Risk distribution
            fig = go.Figure()
            fig.add_trace(go.Histogram(
                x=sample_df["risk"],
                nbinsx=80,
                marker=dict(
                    color="rgba(0,229,255,0.6)",
                    line=dict(color="rgba(0,229,255,1)", width=1),
                ),
                hovertemplate="Risk: %{x:.2f}<br>Count: %{y}<extra></extra>",
            ))

            # Add risk threshold lines
            for level, threshold, color in [
                ("CRITICAL", -3.0, "#FF0040"),
                ("HIGH", -4.5, "#FF6B35"),
                ("MEDIUM", -6.0, "#FFD700"),
            ]:
                fig.add_vline(
                    x=threshold, line_dash="dash", line_color=color,
                    annotation_text=level, annotation_font=dict(color=color, size=10),
                )

            fig.update_layout(
                title=dict(text="Collision Risk Distribution (log₁₀ Pc)", font=dict(size=14, color="white")),
                xaxis_title="Risk (log₁₀ collision probability)",
                yaxis_title="Count",
                template="plotly_dark",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(20,20,40,0.8)",
                height=400,
                font=dict(family="Inter, sans-serif", color="white"),
            )
            st.plotly_chart(fig, width="stretch")

        with col2:
            # Miss distance vs Risk scatter
            fig = px.scatter(
                sample_df.sample(min(2000, len(sample_df))),
                x="miss_distance",
                y="risk",
                color="time_to_tca",
                color_continuous_scale="Turbo",
                opacity=0.5,
                labels={
                    "miss_distance": "Miss Distance (m)",
                    "risk": "Risk (log₁₀ Pc)",
                    "time_to_tca": "Time to TCA (days)",
                },
                title="Miss Distance vs. Collision Risk",
            )
            fig.update_layout(
                template="plotly_dark",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(20,20,40,0.8)",
                height=400,
                font=dict(family="Inter, sans-serif", color="white"),
            )
            st.plotly_chart(fig, width="stretch")

    except Exception as e:
        st.info(f"Dataset preview: {e}")


# ═══════════════════════════════════════════════════════════════════════════════
# RISK ALERTS PAGE
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "🔴 Risk Alerts":
    st.markdown("# 🔴 Conjunction Risk Alerts")
    st.markdown("*Ranked close approach events with AI-predicted collision probabilities*")

    try:
        sample_df = load_dataset_sample(5000)

        # Filter high-risk events
        risk_threshold = st.slider(
            "Risk Threshold (log₁₀ Pc)",
            min_value=-15.0,
            max_value=0.0,
            value=-6.0,
            step=0.5,
        )

        if model_available:
            sample_df = sample_df.copy()
            sample_df["predicted_risk"] = predict_risk(model, sample_df)
            risk_col = "predicted_risk"
            st.caption("Ranked by **AI-predicted** risk; the CDM-reported risk is shown alongside.")
        else:
            risk_col = "risk"
            st.caption("No trained model — ranked by CDM-reported risk.")

        alerts_df = sample_df[sample_df[risk_col] >= risk_threshold].copy()
        alerts_df = alerts_df.sort_values(risk_col, ascending=False).head(50)

        st.markdown(f"### 📊 {len(alerts_df)} Events Above Threshold")

        if not alerts_df.empty:
            for idx, row in alerts_df.head(20).iterrows():
                risk = row[risk_col]
                cdm_note = f'CDM: <code>{row["risk"]:.3f}</code> &nbsp;|&nbsp; ' if model_available else ""
                badge = get_risk_badge(risk)

                if risk >= -3.0:
                    css_class = "risk-critical"
                elif risk >= -4.5:
                    css_class = "risk-high"
                elif risk >= -6.0:
                    css_class = "risk-medium"
                else:
                    css_class = "risk-low"

                st.markdown(
                    f'<div class="{css_class}">'
                    f'{badge} &nbsp; '
                    f'<b>Event {row.get("event_id", idx)}</b> &nbsp;|&nbsp; '
                    f'Risk: <code>{risk:.3f}</code> &nbsp;|&nbsp; {cdm_note}'
                    f'Miss: <code>{row.get("miss_distance", 0):,.0f} m</code> &nbsp;|&nbsp; '
                    f'TCA: <code>{row.get("time_to_tca", 0):.2f} days</code> &nbsp;|&nbsp; '
                    f'Rel. Speed: <code>{row.get("relative_speed", 0):,.0f} m/s</code>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

            # Summary stats
            st.markdown("---")
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                critical = len(alerts_df[alerts_df[risk_col] >= -3.0])
                st.metric("🔴 Critical", critical)
            with col2:
                high = len(alerts_df[(alerts_df[risk_col] >= -4.5) & (alerts_df[risk_col] < -3.0)])
                st.metric("🟠 High", high)
            with col3:
                medium = len(alerts_df[(alerts_df[risk_col] >= -6.0) & (alerts_df[risk_col] < -4.5)])
                st.metric("🟡 Medium", medium)
            with col4:
                low = len(alerts_df[alerts_df[risk_col] < -6.0])
                st.metric("🟢 Low", low)

    except Exception as e:
        st.error(f"Error loading alerts: {e}")


# ═══════════════════════════════════════════════════════════════════════════════
# LIVE TRACKING PAGE
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "🌍 Live Tracking":
    st.markdown("# 🌍 Live Satellite Tracking")
    st.markdown("*Real-time CelesTrak orbital data with 3D visualization*")

    with st.spinner("📡 Fetching live data..."):
        data = load_celestrak_data()

    if not data["active"].empty:
        tab1, tab2, tab3 = st.tabs(["🔍 Search & Explore", "🌐 3D Orbit View", "📊 Statistics"])

        with tab1:
            search = st.text_input("🔍 Search satellite by name or NORAD ID")

            display_df = data["active"].copy()
            if search:
                mask = (
                    display_df["OBJECT_NAME"].str.contains(search, case=False, na=False) |
                    display_df["NORAD_CAT_ID"].astype(str).str.contains(search, na=False)
                )
                display_df = display_df[mask]

            st.markdown(f"**Showing {len(display_df):,} satellites**")

            # Select columns to display
            display_cols = [
                "OBJECT_NAME", "NORAD_CAT_ID", "INCLINATION",
                "ECCENTRICITY", "MEAN_MOTION", "EPOCH", "ORBIT_BAND",
            ]
            available_cols = [c for c in display_cols if c in display_df.columns]
            st.dataframe(
                display_df[available_cols].head(200),
                width="stretch",
                hide_index=True,
                height=500,
            )

        with tab2:
            st.markdown("### 🌐 3D Orbit Visualization")

            # Let user select satellites to visualize
            sat_names = data["active"]["OBJECT_NAME"].head(100).tolist()
            selected_sats = st.multiselect(
                "Select satellites to visualize (max 5)",
                sat_names,
                default=sat_names[:2] if len(sat_names) >= 2 else sat_names[:1],
                max_selections=5,
            )

            if selected_sats:
                from orbit_visualizations import (
                    create_3d_earth, create_orbit_3d,
                    create_satellite_marker, mean_motion_to_sma,
                )

                fig = go.Figure()
                fig.add_trace(create_3d_earth())

                colors = ["#00E5FF", "#FF6B35", "#7C4DFF", "#00E676", "#FFD700"]

                for i, sat_name in enumerate(selected_sats):
                    sat_data = data["active"][data["active"]["OBJECT_NAME"] == sat_name].iloc[0]
                    sma = mean_motion_to_sma(sat_data.get("MEAN_MOTION", 14))

                    fig.add_trace(create_orbit_3d(
                        sma, sat_data.get("ECCENTRICITY", 0),
                        sat_data.get("INCLINATION", 0),
                        sat_data.get("RA_OF_ASC_NODE", 0),
                        sat_data.get("ARG_OF_PERICENTER", 0),
                        name=sat_name, color=colors[i % len(colors)],
                    ))

                    fig.add_trace(create_satellite_marker(
                        sma, sat_data.get("ECCENTRICITY", 0),
                        sat_data.get("INCLINATION", 0),
                        sat_data.get("RA_OF_ASC_NODE", 0),
                        sat_data.get("ARG_OF_PERICENTER", 0),
                        sat_data.get("MEAN_ANOMALY", 0),
                        name=sat_name, color=colors[i % len(colors)],
                    ))

                fig.update_layout(
                    scene=dict(
                        xaxis=dict(showgrid=False, showticklabels=False, title="", showbackground=False),
                        yaxis=dict(showgrid=False, showticklabels=False, title="", showbackground=False),
                        zaxis=dict(showgrid=False, showticklabels=False, title="", showbackground=False),
                        bgcolor="rgba(5,5,15,1)",
                        aspectmode="data",
                    ),
                    paper_bgcolor="rgba(5,5,15,1)",
                    height=700,
                    margin=dict(l=0, r=0, t=20, b=0),
                    legend=dict(font=dict(color="white"), bgcolor="rgba(20,20,40,0.7)"),
                )
                st.plotly_chart(fig, width="stretch")

        with tab3:
            st.markdown("### 📊 Orbital Statistics")
            if "ORBIT_BAND" in data["active"].columns:
                col1, col2 = st.columns(2)

                with col1:
                    band_counts = data["active"]["ORBIT_BAND"].value_counts()
                    fig = go.Figure(go.Pie(
                        labels=band_counts.index,
                        values=band_counts.values,
                        hole=0.5,
                        marker=dict(colors=["#00E5FF", "#FFD700", "#FF6B35", "#7C4DFF", "#888"]),
                        textinfo="label+percent",
                        textfont=dict(color="white"),
                    ))
                    fig.update_layout(
                        title=dict(text="Orbit Band Distribution", font=dict(color="white", size=14)),
                        paper_bgcolor="rgba(0,0,0,0)",
                        plot_bgcolor="rgba(0,0,0,0)",
                        height=400,
                        font=dict(family="Inter, sans-serif", color="white"),
                        legend=dict(font=dict(color="white")),
                    )
                    st.plotly_chart(fig, width="stretch")

                with col2:
                    # Inclination distribution
                    fig = go.Figure()
                    fig.add_trace(go.Histogram(
                        x=data["active"]["INCLINATION"],
                        nbinsx=60,
                        marker=dict(color="rgba(124,77,255,0.6)", line=dict(color="#7C4DFF", width=1)),
                    ))
                    fig.update_layout(
                        title=dict(text="Inclination Distribution", font=dict(color="white", size=14)),
                        xaxis_title="Inclination (°)",
                        yaxis_title="Count",
                        template="plotly_dark",
                        paper_bgcolor="rgba(0,0,0,0)",
                        plot_bgcolor="rgba(20,20,40,0.8)",
                        height=400,
                        font=dict(family="Inter, sans-serif", color="white"),
                    )
                    st.plotly_chart(fig, width="stretch")

    else:
        st.warning("Could not fetch live satellite data. Check your internet connection.")


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


# ═══════════════════════════════════════════════════════════════════════════════
# MANOEUVRE PLANNER PAGE
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "🚀 Manoeuvre Planner":
    st.markdown("# 🚀 Collision Avoidance Manoeuvre Planner")
    st.markdown("*Simulate delta-V burns and evaluate risk/fuel trade-offs*")

    from manoeuvre_simulator import ManoeuvreSimulator

    col1, col2 = st.columns([1, 1])

    with col1:
        st.markdown("### ⚙️ Spacecraft Parameters")
        mass = st.number_input("Spacecraft Mass (kg)", 50.0, 10000.0, 500.0, 50.0)
        isp = st.number_input("Thruster Isp (s)", 50.0, 500.0, 220.0, 10.0)

    with col2:
        st.markdown("### 📐 Conjunction Parameters")
        miss_dist = st.number_input("Miss Distance (m)", 10.0, 100000.0, 500.0, 10.0)
        rel_speed = st.number_input("Relative Speed (m/s)", 100.0, 20000.0, 13000.0, 100.0)
        time_to_tca = st.number_input("Time to TCA (hours)", 1.0, 168.0, 48.0, 1.0)
        sigma_m = st.number_input("Combined Position Uncertainty σ (m)", 1.0, 50000.0, 200.0, 10.0)
        current_risk = st.slider("Current Risk (log₁₀ Pc)", -15.0, 0.0, -4.0, 0.5)

    if st.button("🚀 Run Manoeuvre Analysis", width="stretch"):
        predict_fn = model.predict if model_available else None
        sim = ManoeuvreSimulator(
            predict_fn=predict_fn,
            spacecraft_mass_kg=mass,
            isp_s=isp,
        )

        # Create synthetic feature vector
        n_features = len(model.feature_names) if model_available else 100
        features = np.zeros(n_features, dtype=np.float32)

        feature_names = model.feature_names if model_available else (
            ["miss_distance", "relative_speed", "time_to_tca", "combined_uncertainty"]
            + [f"f{i}" for i in range(4, n_features)]
        )

        # Set known values (CDM units: metres, m/s, days)
        for fname, fval in [
            ("miss_distance", miss_dist),
            ("relative_speed", rel_speed),
            ("time_to_tca", time_to_tca / 24.0),
            ("combined_uncertainty", sigma_m),
        ]:
            if fname in feature_names:
                features[feature_names.index(fname)] = fval

        # The hand-entered conjunction is not a full CDM, so use the user's risk
        report = sim.analyse_conjunction(
            features, feature_names,
            event_id="MANUAL",
            original_risk=current_risk,
        )

        # Display results
        from orbit_visualizations import create_risk_gauge

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("### Current Risk")
            fig = create_risk_gauge(current_risk)
            st.plotly_chart(fig, width="stretch")

        with col2:
            if report.best_option:
                st.markdown("### Best Option Risk")
                fig = create_risk_gauge(report.best_option.residual_risk)
                st.caption(
                    f"{report.best_option.direction} burn, ΔV {report.best_option.delta_v_ms} m/s, "
                    f"{report.best_option.delta_v_fuel_kg:.3f} kg fuel"
                )
                st.plotly_chart(fig, width="stretch")

        st.markdown("---")
        st.markdown("### 📋 Manoeuvre Options (Ranked by Effectiveness)")

        results_df = sim.report_to_dataframe(report)
        results_df = results_df.sort_values("Risk Reduction %", ascending=False)

        st.dataframe(
            results_df,
            width="stretch",
            hide_index=True,
            height=400,
        )

        # Fuel vs Risk Reduction chart
        fig = px.scatter(
            results_df,
            x="Fuel (kg)",
            y="Risk Reduction %",
            color="Direction",
            size="ΔV (m/s)",
            hover_data=["Recommendation"],
            title="Fuel Cost vs. Risk Reduction",
        )
        fig.update_layout(
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(20,20,40,0.8)",
            height=400,
            font=dict(family="Inter, sans-serif", color="white"),
        )
        st.plotly_chart(fig, width="stretch")


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
# SETTINGS PAGE
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "⚙️ Settings":
    st.markdown("# ⚙️ Settings")

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
                with col1:
                    st.metric("🖥️ GPU", parts[0])
                    st.metric("🌡️ Temperature", f"{parts[4]}°C")
                with col2:
                    st.metric("💾 VRAM Total", f"{parts[1]} MB")
                    st.metric("📊 VRAM Used", f"{parts[2]} MB")
                with col3:
                    st.metric("📈 GPU Utilization", f"{parts[5]}%")
                    st.metric("💾 VRAM Free", f"{parts[3]} MB")
    except Exception:
        st.info("GPU info unavailable")

    st.markdown("---")
    st.markdown("### 📡 CelesTrak Configuration")

    from config import CELESTRAK_GROUPS
    st.markdown("**Tracked Orbital Groups:**")
    for key, name in CELESTRAK_GROUPS.items():
        st.markdown(f"- `{key}` → {name}")

    st.markdown("---")
    st.markdown("### 🔧 Model Parameters")
    from config import XGBOOST_PARAMS
    st.json(XGBOOST_PARAMS)
