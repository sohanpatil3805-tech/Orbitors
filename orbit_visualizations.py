"""
OrbitGuard AI — Orbital Visualization Utilities
Helper functions for creating 3D orbit visualizations and ground tracks.
"""

from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


# ─── Earth ────────────────────────────────────────────────────────────────────
EARTH_RADIUS_KM = 6371.0
MU_EARTH = 398600.4418  # km³/s²
TEXTURE_PATH = Path(__file__).parent / "assets" / "earth_texture.jpg"
SPACE_BG = "#03050d"


@lru_cache(maxsize=2)
def _earth_mesh(n_lat: int = 150, n_lon: int = 300):
    """
    Unit-sphere triangle mesh with one true RGB colour per vertex sampled from the
    Blue Marble texture (rows run north → south, columns west → east from −180°).
    Returns (lat, lon, i, j, k, hex colours) or None if the texture is missing.
    """
    try:
        from PIL import Image
        img = Image.open(TEXTURE_PATH).convert("RGB").resize((n_lon, n_lat), Image.LANCZOS)
    except Exception:
        return None
    rgb = np.asarray(img).reshape(-1, 3)
    colours = np.array([f"#{r:02x}{g:02x}{b:02x}" for r, g, b in rgb])
    lat = np.repeat(np.linspace(np.pi / 2, -np.pi / 2, n_lat), n_lon)
    lon = np.tile(np.linspace(-np.pi, np.pi, n_lon), n_lat)
    a = (np.arange(n_lat - 1)[:, None] * n_lon + np.arange(n_lon - 1)[None, :]).ravel()
    b, c, d = a + 1, a + n_lon, a + n_lon + 1
    idx_type = np.uint16 if n_lat * n_lon < 65536 else np.int32   # smaller payload to the browser
    i = np.concatenate([a, b]).astype(idx_type)
    j = np.concatenate([c, c]).astype(idx_type)
    k = np.concatenate([b, d]).astype(idx_type)
    return lat, lon, i, j, k, colours


def gmst_rad(when: Optional[datetime] = None) -> float:
    """Greenwich sidereal angle: rotates the Earth texture into the TEME frame used for orbits."""
    from sgp4.api import jday
    from sgp4.propagation import gstime
    when = when or datetime.now(timezone.utc)
    jd, fr = jday(when.year, when.month, when.day, when.hour, when.minute, when.second + when.microsecond * 1e-6)
    return float(gstime(jd + fr))


def create_3d_earth(when: Optional[datetime] = None, resolution: int = 50):
    """Textured Earth (NASA Blue Marble) oriented for `when` (default now), in km."""
    mesh = _earth_mesh()
    if mesh is None:  # texture missing: plain ocean-coloured sphere
        u, v = np.linspace(0, 2 * np.pi, resolution), np.linspace(0, np.pi, resolution)
        return go.Surface(x=EARTH_RADIUS_KM * np.outer(np.cos(u), np.sin(v)),
                          y=EARTH_RADIUS_KM * np.outer(np.sin(u), np.sin(v)),
                          z=EARTH_RADIUS_KM * np.outer(np.ones(resolution), np.cos(v)),
                          colorscale=[[0, "#0b2a4a"], [1, "#1d4f7a"]], showscale=False, hoverinfo="skip")
    lat, lon, i, j, k, colours = mesh
    lon = lon + gmst_rad(when)
    r = EARTH_RADIUS_KM
    return go.Mesh3d(
        x=(r * np.cos(lat) * np.cos(lon)).astype(np.float32),
        y=(r * np.cos(lat) * np.sin(lon)).astype(np.float32),
        z=(r * np.sin(lat)).astype(np.float32),
        i=i, j=j, k=k, vertexcolor=colours, hoverinfo="skip", name="Earth", showscale=False, flatshading=False,
        lighting=dict(ambient=0.8, diffuse=0.45, specular=0.05, roughness=0.95, fresnel=0.05),
        lightposition=dict(x=1e5, y=4e4, z=6e4),
    )


def create_atmosphere(scale: float = 1.025) -> go.Surface:
    """Thin translucent halo around the Earth."""
    u, v = np.linspace(0, 2 * np.pi, 60), np.linspace(0, np.pi, 30)
    r = EARTH_RADIUS_KM * scale
    return go.Surface(x=r * np.outer(np.cos(u), np.sin(v)), y=r * np.outer(np.sin(u), np.sin(v)),
                      z=r * np.outer(np.ones(len(u)), np.cos(v)), surfacecolor=np.zeros((len(u), len(v))),
                      colorscale=[[0, "rgb(96,180,255)"], [1, "rgb(96,180,255)"]], opacity=0.09,
                      showscale=False, hoverinfo="skip", name="Atmosphere",
                      lighting=dict(ambient=1.0, diffuse=0.0, specular=0.0))


def add_earth(fig: go.Figure, when: Optional[datetime] = None) -> go.Figure:
    fig.add_trace(create_3d_earth(when))
    fig.add_trace(create_atmosphere())
    return fig


def space_scene(eye=(0.82, 0.82, 0.42)) -> dict:
    """Shared 3D scene: black space, no axes, camera close enough that the Earth fills the view."""
    hidden = dict(visible=False, showbackground=False, showgrid=False, zeroline=False, showspikes=False)
    return dict(xaxis=hidden, yaxis=hidden, zaxis=hidden, bgcolor=SPACE_BG, aspectmode="data",
                camera=dict(eye=dict(x=eye[0], y=eye[1], z=eye[2]), up=dict(x=0, y=0, z=1)), dragmode="orbit")


HOVER_STYLE = dict(bgcolor="rgba(10,16,34,0.92)", bordercolor="rgba(120,160,255,0.35)",
                   font=dict(family="Inter, sans-serif", size=12, color="white"))


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
    fig = add_earth(go.Figure())

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
        scene=space_scene(),
        paper_bgcolor=SPACE_BG,
        plot_bgcolor=SPACE_BG,
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


# ─── Live risk view ───────────────────────────────────────────────────────────
STATUS_STYLE = {
    "DANGER": dict(color="#FF3B5C", width=4.5, glow="rgba(255,59,92,0.18)", glow_width=11, marker=7,
                   group="Danger — high / critical risk"),
    "REVIEW": dict(color="#FFA62B", width=3, glow=None, glow_width=0, marker=5,
                   group="Review — medium risk or < 1 km"),
    "MITIGATED": dict(color="#3DDC97", width=2.5, glow=None, glow_width=0, marker=4, group="Manoeuvre accepted"),
    "SAFE": dict(color="rgba(220,232,255,0.42)", width=1.4, glow=None, glow_width=0, marker=3, group="Safe"),
}
_ORDER = {"SAFE": 0, "MITIGATED": 1, "REVIEW": 2, "DANGER": 3}


def create_risk_orbit_view(source, objects: pd.DataFrame, sat_ids: list, status: dict,
                           worst_events: dict, planned_offsets: dict | None = None,
                           now_s: float = 0.0, height: int = 820, when: Optional[datetime] = None) -> go.Figure:
    """
    3D view of watchlist satellites over a textured Earth, coloured by status:
    red with a soft glow (DANGER), amber (REVIEW), green (manoeuvre accepted)
    and faint white (SAFE, one legend entry to keep the view clean). At-risk
    satellites also show the other object's path around closest approach
    (dotted) and the closest-approach point (✕); details are on hover.

    source         : screening.ObjectSource (TEME positions, km)
    status         : sat_id -> status string
    worst_events   : sat_id -> conjunction row (pd.Series) for red/orange satellites
    planned_offsets: sat_id -> (offset callable, burn_s, tca_s) for accepted manoeuvres
    """
    planned_offsets = planned_offsets or {}
    fig = add_earth(go.Figure(), when)

    def path(sid):
        period_s = float(objects.loc[sid, "PERIOD_MIN"]) * 60.0
        r, _ = source.states([sid], now_s + np.linspace(0, period_s, 200))
        return r[0]

    # Safe satellites: one combined trace (None breaks the line between satellites)
    safe = [s for s in sat_ids if status.get(s, "SAFE") == "SAFE"]
    if safe:
        st = STATUS_STYLE["SAFE"]
        xs, ys, zs, names, now_pts = [], [], [], [], []
        for sid in safe:
            p = path(sid)
            name = str(objects.loc[sid, "OBJECT_NAME"])
            xs += list(p[:, 0]) + [None]
            ys += list(p[:, 1]) + [None]
            zs += list(p[:, 2]) + [None]
            names += [name] * len(p) + [None]
            now_pts.append(p[0])
        now_pts = np.array(now_pts)
        fig.add_trace(go.Scatter3d(x=xs, y=ys, z=zs, mode="lines", name=f"{len(safe)} satellites",
                                   legendgroup="SAFE", legendgrouptitle_text=st["group"],
                                   line=dict(color=st["color"], width=st["width"]), hovertext=names,
                                   hovertemplate="%{hovertext} · safe<extra></extra>"))
        fig.add_trace(go.Scatter3d(x=now_pts[:, 0], y=now_pts[:, 1], z=now_pts[:, 2], mode="markers",
                                   legendgroup="SAFE", showlegend=False,
                                   marker=dict(size=st["marker"], color="rgba(235,242,255,0.9)"),
                                   hovertext=[str(objects.loc[s, "OBJECT_NAME"]) for s in safe],
                                   hovertemplate="%{hovertext} (now)<extra></extra>"))

    at_risk = sorted([s for s in sat_ids if status.get(s, "SAFE") != "SAFE"], key=lambda s: _ORDER[status[s]])
    titled = set()
    for sid in at_risk:
        stt = status[sid]
        st = STATUS_STYLE[stt]
        name = str(objects.loc[sid, "OBJECT_NAME"])
        p = path(sid)
        group = dict(legendgroup=stt)
        if stt not in titled:
            group["legendgrouptitle_text"] = st["group"]
            titled.add(stt)
        ev = worst_events.get(sid)
        detail = (f"<br>closest approach with {ev['SECONDARY_NAME']}<br>{pd.Timestamp(ev['TCA']):%d %b %H:%M} UTC · "
                  f"{ev['MISS_KM'] * 1000:,.0f} m · log₁₀ Pc {ev['LOG_PC']:.1f}") if ev is not None else ""
        if st["glow"]:
            fig.add_trace(go.Scatter3d(x=p[:, 0], y=p[:, 1], z=p[:, 2], mode="lines", showlegend=False,
                                       line=dict(color=st["glow"], width=st["glow_width"]), hoverinfo="skip",
                                       legendgroup=stt))
        fig.add_trace(go.Scatter3d(x=p[:, 0], y=p[:, 1], z=p[:, 2], mode="lines", name=name, **group,
                                   line=dict(color=st["color"], width=st["width"]),
                                   hovertemplate=f"<b>{name}</b> · {stt.lower()}{detail}<extra></extra>"))
        fig.add_trace(go.Scatter3d(
            x=[p[0, 0]], y=[p[0, 1]], z=[p[0, 2]], mode="markers+text" if stt == "DANGER" else "markers",
            marker=dict(size=st["marker"], color=st["color"], line=dict(color="white", width=1.5)),
            text=[f"  {name}"], textposition="middle right",
            textfont=dict(color="#FFD3DA", size=12, family="Inter, sans-serif"),
            showlegend=False, legendgroup=stt, hovertemplate=f"<b>{name}</b> (now){detail}<extra></extra>"))

        if ev is not None and stt in ("DANGER", "REVIEW"):
            tca_s = float(ev["TCA_S"])
            rs, _ = source.states([int(ev["SECONDARY_ID"])], tca_s + np.linspace(-600, 600, 81))
            fig.add_trace(go.Scatter3d(
                x=rs[0, :, 0], y=rs[0, :, 1], z=rs[0, :, 2], mode="lines", showlegend=False, legendgroup=stt,
                line=dict(color=st["color"], width=2.5, dash="dot"),
                hovertemplate=f"{ev['SECONDARY_NAME']} (±10 min of closest approach)<extra></extra>"))
            q = np.asarray(ev["P_POS"])
            fig.add_trace(go.Scatter3d(x=[q[0]], y=[q[1]], z=[q[2]], mode="markers", showlegend=False,
                                       legendgroup=stt, marker=dict(size=6, color=st["color"], symbol="x"),
                                       hovertemplate=f"<b>Closest approach</b>{detail}<extra></extra>"))

    for sid, (offset, burn_s, tca_s) in planned_offsets.items():
        if sid not in sat_ids:
            continue
        period_s = float(objects.loc[sid, "PERIOD_MIN"]) * 60.0
        span = np.linspace(max(burn_s, now_s), tca_s + 0.5 * period_s, 240)
        rp, _ = source.states([sid], span)
        q = rp[0] + offset(span)[0]
        fig.add_trace(go.Scatter3d(x=q[:, 0], y=q[:, 1], z=q[:, 2], mode="lines",
                                   name=f"{objects.loc[sid, 'OBJECT_NAME']} — planned path",
                                   legendgroup="PLANNED", legendgrouptitle_text="Accepted manoeuvres",
                                   line=dict(color="#3DDC97", width=3.5, dash="dash"),
                                   hovertemplate="Path after the accepted burn<extra></extra>"))

    fig.update_layout(
        scene=space_scene(), paper_bgcolor=SPACE_BG, height=height, margin=dict(l=0, r=0, t=0, b=0),
        legend=dict(x=0.01, y=0.98, xanchor="left", yanchor="top", bgcolor="rgba(8,12,28,0.72)",
                    bordercolor="rgba(120,160,255,0.25)", borderwidth=1, itemsizing="constant",
                    font=dict(color="#E6ECFF", size=11, family="Inter, sans-serif"),
                    grouptitlefont=dict(size=11, color="#9FB3E6"), groupclick="toggleitem", tracegroupgap=6),
        hoverlabel=HOVER_STYLE, font=dict(family="Inter, sans-serif"),
        uirevision="orbit-view",   # keep the user's camera between refreshes
    )
    return fig
