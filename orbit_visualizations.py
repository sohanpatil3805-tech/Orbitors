"""
OrbitGuard AI — Orbital Visualization Utilities
Helper functions for creating 3D orbit visualizations and ground tracks.
"""

import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from typing import Optional


# ─── Earth Constants ──────────────────────────────────────────────────────────
EARTH_RADIUS_KM = 6371.0
MU_EARTH = 398600.4418  # km³/s²


def create_3d_earth(resolution: int = 50) -> go.Surface:
    """Create a 3D Earth sphere using Plotly."""
    u = np.linspace(0, 2 * np.pi, resolution)
    v = np.linspace(0, np.pi, resolution)

    x = EARTH_RADIUS_KM * np.outer(np.cos(u), np.sin(v))
    y = EARTH_RADIUS_KM * np.outer(np.sin(u), np.sin(v))
    z = EARTH_RADIUS_KM * np.outer(np.ones(np.size(u)), np.cos(v))

    # Create color map for Earth (simple lat/lon coloring)
    colorscale = [
        [0.0, "#0a1628"],
        [0.2, "#0d2137"],
        [0.4, "#1a3a5c"],
        [0.6, "#0d4d2e"],
        [0.8, "#1a6b40"],
        [1.0, "#0a1628"],
    ]

    return go.Surface(
        x=x, y=y, z=z,
        colorscale=colorscale,
        showscale=False,
        opacity=0.8,
        hoverinfo="skip",
        lighting=dict(ambient=0.4, diffuse=0.6, specular=0.2),
    )


def orbital_elements_to_positions(
    sma_km: float,
    ecc: float,
    inc_deg: float,
    raan_deg: float,
    argp_deg: float,
    n_points: int = 200,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Convert orbital elements to ECI (Earth-Centered Inertial) positions.
    Returns x, y, z arrays in km.
    """
    inc = np.radians(inc_deg)
    raan = np.radians(raan_deg)
    argp = np.radians(argp_deg)

    # True anomaly array
    nu = np.linspace(0, 2 * np.pi, n_points)

    # Orbital radius
    r = sma_km * (1 - ecc ** 2) / (1 + ecc * np.cos(nu))

    # Perifocal coordinates
    x_pf = r * np.cos(nu)
    y_pf = r * np.sin(nu)

    # Rotation matrices
    cos_raan, sin_raan = np.cos(raan), np.sin(raan)
    cos_inc, sin_inc = np.cos(inc), np.sin(inc)
    cos_argp, sin_argp = np.cos(argp), np.sin(argp)

    # ECI coordinates
    x = (cos_raan * cos_argp - sin_raan * sin_argp * cos_inc) * x_pf + \
        (-cos_raan * sin_argp - sin_raan * cos_argp * cos_inc) * y_pf

    y = (sin_raan * cos_argp + cos_raan * sin_argp * cos_inc) * x_pf + \
        (-sin_raan * sin_argp + cos_raan * cos_argp * cos_inc) * y_pf

    z = (sin_argp * sin_inc) * x_pf + (cos_argp * sin_inc) * y_pf

    return x, y, z


def mean_motion_to_sma(mean_motion_rev_day: float) -> float:
    """Convert mean motion (rev/day) to semi-major axis (km)."""
    if mean_motion_rev_day <= 0:
        return 0.0
    n_rad_s = mean_motion_rev_day * 2 * np.pi / 86400.0
    return (MU_EARTH / (n_rad_s ** 2)) ** (1.0 / 3.0)


def create_orbit_3d(
    sma_km: float,
    ecc: float,
    inc_deg: float,
    raan_deg: float,
    argp_deg: float,
    name: str = "Orbit",
    color: str = "#00E5FF",
    width: float = 2,
) -> go.Scatter3d:
    """Create a 3D orbit trace."""
    x, y, z = orbital_elements_to_positions(sma_km, ecc, inc_deg, raan_deg, argp_deg)

    return go.Scatter3d(
        x=x, y=y, z=z,
        mode="lines",
        name=name,
        line=dict(color=color, width=width),
        hoverinfo="name",
    )


def create_satellite_marker(
    sma_km: float,
    ecc: float,
    inc_deg: float,
    raan_deg: float,
    argp_deg: float,
    mean_anomaly_deg: float,
    name: str = "Satellite",
    color: str = "#FFD700",
    size: int = 6,
) -> go.Scatter3d:
    """Create a 3D marker at the satellite's current position."""
    nu_rad = np.radians(mean_anomaly_deg)  # Approximate true anomaly
    r = sma_km * (1 - ecc ** 2) / (1 + ecc * np.cos(nu_rad))

    inc = np.radians(inc_deg)
    raan = np.radians(raan_deg)
    argp = np.radians(argp_deg)

    x_pf = r * np.cos(nu_rad)
    y_pf = r * np.sin(nu_rad)

    cos_raan, sin_raan = np.cos(raan), np.sin(raan)
    cos_inc, sin_inc = np.cos(inc), np.sin(inc)
    cos_argp, sin_argp = np.cos(argp), np.sin(argp)

    x = (cos_raan * cos_argp - sin_raan * sin_argp * cos_inc) * x_pf + \
        (-cos_raan * sin_argp - sin_raan * cos_argp * cos_inc) * y_pf

    y = (sin_raan * cos_argp + cos_raan * sin_argp * cos_inc) * x_pf + \
        (-sin_raan * sin_argp + cos_raan * cos_argp * cos_inc) * y_pf

    z = (sin_argp * sin_inc) * x_pf + (cos_argp * sin_inc) * y_pf

    return go.Scatter3d(
        x=[x], y=[y], z=[z],
        mode="markers+text",
        name=name,
        marker=dict(size=size, color=color, symbol="diamond"),
        text=[name],
        textposition="top center",
        textfont=dict(size=10, color="white"),
    )


def create_conjunction_visualization(
    target_elements: dict,
    chaser_elements: dict,
    miss_distance_km: float = 0,
    risk_level: str = "UNKNOWN",
) -> go.Figure:
    """
    Create a 3D visualization of a conjunction event showing both orbits.

    Parameters
    ----------
    target_elements : dict with keys sma, ecc, inc, raan, argp, ma, name
    chaser_elements : dict with same keys
    miss_distance_km : miss distance at TCA
    risk_level : risk category string
    """
    fig = go.Figure()

    # Add Earth
    fig.add_trace(create_3d_earth())

    # Target orbit
    fig.add_trace(create_orbit_3d(
        target_elements["sma"], target_elements["ecc"],
        target_elements["inc"], target_elements["raan"],
        target_elements["argp"],
        name=f"Target: {target_elements.get('name', 'Satellite')}",
        color="#00E5FF",
    ))

    # Chaser orbit
    fig.add_trace(create_orbit_3d(
        chaser_elements["sma"], chaser_elements["ecc"],
        chaser_elements["inc"], chaser_elements["raan"],
        chaser_elements["argp"],
        name=f"Chaser: {chaser_elements.get('name', 'Debris')}",
        color="#FF6B35",
    ))

    # Satellite positions
    fig.add_trace(create_satellite_marker(
        target_elements["sma"], target_elements["ecc"],
        target_elements["inc"], target_elements["raan"],
        target_elements["argp"], target_elements.get("ma", 0),
        name=target_elements.get("name", "Target"),
        color="#00E5FF", size=8,
    ))

    fig.add_trace(create_satellite_marker(
        chaser_elements["sma"], chaser_elements["ecc"],
        chaser_elements["inc"], chaser_elements["raan"],
        chaser_elements["argp"], chaser_elements.get("ma", 0),
        name=chaser_elements.get("name", "Chaser"),
        color="#FF6B35", size=8,
    ))

    # Risk color
    risk_colors = {
        "CRITICAL": "#FF0040",
        "HIGH": "#FF6B35",
        "MEDIUM": "#FFD700",
        "LOW": "#00E676",
        "NEGLIGIBLE": "#40C4FF",
    }

    fig.update_layout(
        title=dict(
            text=f"Conjunction Visualization — {risk_level} Risk | Miss: {miss_distance_km:.1f} km",
            font=dict(size=16, color="white"),
        ),
        scene=dict(
            xaxis=dict(showgrid=False, showticklabels=False, title="", showbackground=False),
            yaxis=dict(showgrid=False, showticklabels=False, title="", showbackground=False),
            zaxis=dict(showgrid=False, showticklabels=False, title="", showbackground=False),
            bgcolor="rgba(5,5,15,1)",
            aspectmode="data",
        ),
        paper_bgcolor="rgba(5,5,15,1)",
        plot_bgcolor="rgba(5,5,15,1)",
        height=600,
        margin=dict(l=0, r=0, t=50, b=0),
        legend=dict(
            font=dict(color="white"),
            bgcolor="rgba(20,20,40,0.7)",
        ),
        font=dict(family="Inter, sans-serif"),
    )

    return fig


def create_risk_gauge(risk_value: float, event_id: str = "") -> go.Figure:
    """Create a risk gauge chart."""
    # Convert log10 risk to 0-100 scale for gauge
    # -20 → 0 (safest), 0 → 100 (most dangerous)
    gauge_value = max(0, min(100, (risk_value + 20) * 5))

    if risk_value >= -3.0:
        color = "#FF0040"
        label = "CRITICAL"
    elif risk_value >= -4.5:
        color = "#FF6B35"
        label = "HIGH"
    elif risk_value >= -6.0:
        color = "#FFD700"
        label = "MEDIUM"
    elif risk_value >= -7.5:
        color = "#00E676"
        label = "LOW"
    else:
        color = "#40C4FF"
        label = "NEGLIGIBLE"

    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=risk_value,
        number=dict(
            font=dict(size=36, color=color),
            suffix=" log₁₀Pc",
        ),
        title=dict(
            text=f"<b>{label}</b> Risk",
            font=dict(size=18, color=color),
        ),
        gauge=dict(
            axis=dict(
                range=[-15, 0],
                tickwidth=1,
                tickcolor="white",
                tickfont=dict(color="white"),
            ),
            bar=dict(color=color),
            bgcolor="rgba(20,20,40,0.5)",
            borderwidth=2,
            bordercolor="rgba(255,255,255,0.2)",
            steps=[
                dict(range=[-15, -7.5], color="rgba(64,196,255,0.2)"),
                dict(range=[-7.5, -6.0], color="rgba(0,230,118,0.2)"),
                dict(range=[-6.0, -4.5], color="rgba(255,215,0,0.2)"),
                dict(range=[-4.5, -3.0], color="rgba(255,107,53,0.2)"),
                dict(range=[-3.0, 0], color="rgba(255,0,64,0.2)"),
            ],
            threshold=dict(
                line=dict(color="white", width=3),
                thickness=0.8,
                value=risk_value,
            ),
        ),
    ))

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=300,
        margin=dict(l=30, r=30, t=60, b=20),
        font=dict(family="Inter, sans-serif", color="white"),
    )

    return fig


def create_altitude_distribution(satellites_df: pd.DataFrame) -> go.Figure:
    """Create a histogram of satellite altitude distribution."""
    if "MEAN_MOTION" not in satellites_df.columns:
        return go.Figure()

    altitudes = []
    for _, row in satellites_df.iterrows():
        mm = row.get("MEAN_MOTION", 0)
        ecc = row.get("ECCENTRICITY", 0)
        if mm > 0:
            sma = mean_motion_to_sma(mm)
            alt = sma * (1 - ecc) - EARTH_RADIUS_KM
            if 0 < alt < 50000:
                altitudes.append(alt)

    fig = go.Figure()

    fig.add_trace(go.Histogram(
        x=altitudes,
        nbinsx=100,
        marker=dict(
            color="rgba(0,229,255,0.6)",
            line=dict(color="rgba(0,229,255,1)", width=1),
        ),
        hovertemplate="Altitude: %{x:.0f} km<br>Count: %{y}<extra></extra>",
    ))

    # Add orbital regime annotations
    for regime, (start, end, color) in {
        "LEO": (200, 2000, "rgba(0,229,255,0.1)"),
        "MEO": (2000, 35000, "rgba(255,215,0,0.05)"),
        "GEO": (35000, 36000, "rgba(255,107,53,0.15)"),
    }.items():
        fig.add_vrect(
            x0=start, x1=end,
            fillcolor=color,
            layer="below",
            line_width=0,
            annotation_text=regime,
            annotation_position="top",
            annotation_font=dict(color="white", size=11),
        )

    fig.update_layout(
        title=dict(text="Satellite Altitude Distribution", font=dict(size=16, color="white")),
        xaxis_title="Perigee Altitude (km)",
        yaxis_title="Number of Objects",
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(20,20,40,0.8)",
        height=400,
        font=dict(family="Inter, sans-serif", color="white"),
    )

    return fig
