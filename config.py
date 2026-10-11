"""
OrbitGuard AI - Configuration Module
Centralised configuration for the entire OrbitGuard AI system.
"""

import os
from pathlib import Path

# ─── Project Paths ────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).parent
DATASET_DIR = PROJECT_ROOT / "Dataset"
MODEL_DIR = PROJECT_ROOT / "models"
CACHE_DIR = PROJECT_ROOT / ".cache"

# Create directories if they don't exist
MODEL_DIR.mkdir(exist_ok=True)
CACHE_DIR.mkdir(exist_ok=True)

# ─── Dataset Files ────────────────────────────────────────────────────────────
TRAIN_DATA_PATH = DATASET_DIR / "train_data.csv"
TEST_DATA_PATH = DATASET_DIR / "test_data.csv"

# ─── CelesTrak Configuration ─────────────────────────────────────────────────
CELESTRAK_BASE_URL = "https://celestrak.org/NORAD/elements/gp.php"
CELESTRAK_GROUPS = {
    "active": "Active Satellites",
    "stations": "Space Stations",
    "starlink": "Starlink",
    "oneweb": "OneWeb",
    "planet": "Planet",
    "spire": "Spire",
    "geo": "GEO Satellites",
    "cosmos-1408-debris": "Cosmos 1408 Debris",
    "fengyun-1c-debris": "Fengyun 1C Debris",
    "iridium-33-debris": "Iridium 33 Debris",
    "cosmos-2251-debris": "Cosmos 2251 Debris",
}
CELESTRAK_CACHE_TTL_SECONDS = 7200  # 2 hours — CelesTrak updates GP data every 2 h and returns 403 for earlier re-downloads

# ─── Model Configuration ─────────────────────────────────────────────────────
# Target column in the dataset
TARGET_COLUMN = "risk"

# Columns to exclude from features (c_object_type is label-encoded and kept)
EXCLUDE_COLUMNS = ["event_id", "mission_id", "risk"]

# Column used to group rows into conjunction events for train/validation splits
GROUP_COLUMN = "event_id"

# Risk threshold for binary classification alerts
RISK_THRESHOLD = -4.5  # log10(probability) — higher = more dangerous

# XGBoost GPU parameters for RTX 4060
XGBOOST_PARAMS = {
    "objective": "reg:squarederror",
    "device": "cuda",
    "tree_method": "hist",
    "n_estimators": 1000,
    "max_depth": 8,
    "learning_rate": 0.05,
    "subsample": 0.8,
    "colsample_bytree": 0.8,
    "min_child_weight": 5,
    "gamma": 0.1,
    "reg_alpha": 0.1,
    "reg_lambda": 1.0,
    "random_state": 42,
    "early_stopping_rounds": 50,
    "eval_metric": "rmse",
    "verbosity": 1,
}

# Fallback CPU parameters
XGBOOST_CPU_PARAMS = {
    **XGBOOST_PARAMS,
    "device": "cpu",
    "tree_method": "hist",
}

# ─── Space-Track (optional, more complete catalogue + official public CDMs) ──
# Credentials come from the environment or a git-ignored .env file:
#   SPACETRACK_USER=you@example.com
#   SPACETRACK_PASSWORD=...
SPACETRACK_BASE_URL = "https://www.space-track.org"
SPACETRACK_CACHE_TTL_SECONDS = 3600  # Space-Track asks for GP queries at most once per hour

# ─── Space Weather ────────────────────────────────────────────────────────────
SPACE_WEATHER_URL = "https://celestrak.org/SpaceData/SW-Last5Years.csv"
SPACE_WEATHER_CACHE_TTL_SECONDS = 6 * 3600
SATCAT_URL = "https://celestrak.org/pub/satcat.csv"
SATCAT_CACHE_TTL_SECONDS = 24 * 3600
SOCRATES_URL = "https://celestrak.org/SOCRATES/sort-minRange.csv"

# ─── Important satellites (watchlist) ────────────────────────────────────────
# Every refresh screens these against the whole catalogue. NORAD IDs missing
# from the current catalogue are skipped.
IMPORTANT_SATELLITES = {
    25544: "ISS (ZARYA)",
    48274: "CSS (TIANHE)",
    20580: "HST (Hubble)",
    25994: "TERRA",
    27424: "AQUA",
    37849: "SUOMI NPP",
    43013: "NOAA 20",
    39084: "LANDSAT 8",
    49260: "LANDSAT 9",
    39634: "SENTINEL-1A",
    40697: "SENTINEL-2A",
    42063: "SENTINEL-2B",
    41335: "SENTINEL-3A",
    38771: "METOP-B",
    43689: "METOP-C",
    43613: "ICESAT-2",
    39574: "GPM-CORE",
    41240: "JASON-3",
    46984: "SENTINEL-6",
    54754: "SWOT",
    36508: "CRYOSAT 2",
    44804: "CARTOSAT-3",
    44233: "RISAT-2B",
    51656: "EOS-04",
    54361: "EOS-06 (OCEANSAT-3)",
}

# ─── Collision Screening Parameters ──────────────────────────────────────────
# Close approaches nearer than this are reported (km)
SCREENING_DISTANCE_KM = 10.0

# Extra altitude margin for the perigee/apogee pre-filter (km)
SCREENING_ALTITUDE_PAD_KM = 30.0

# Time window for propagation (hours ahead)
PROPAGATION_WINDOW_HOURS = 72

# Time step for propagation (seconds); closest approaches between samples are
# found with a straight-line relative-motion estimate and then refined.
PROPAGATION_STEP_SECONDS = 60

# ─── Live risk model ─────────────────────────────────────────────────────────
# Public GP/TLE orbits carry no covariance. The uncertainty model (trained on
# ESA CDMs) predicts catalogue-quality sigmas; TLE-quality error is added on top.
# Values are 1-sigma in km: at-epoch error + growth per day since the TLE epoch.
# Rough LEO figures from published TLE accuracy studies (e.g. Flohrer et al. 2008).
TLE_SIGMA_KM = {
    "r": (0.10, 0.05),
    "t": (0.40, 0.60),
    "n": (0.10, 0.05),
}
# Hard-body radius by object type when no size is known (m)
DEFAULT_OBJECT_RADIUS_M = {"PAYLOAD": 5.0, "ROCKET BODY": 4.0, "DEBRIS": 0.5, "UNKNOWN": 1.0}
# Conjunctions nearer than this are flagged at least "review" (orange)
REVIEW_MISS_DISTANCE_KM = 1.0

# ─── Manoeuvre Planning ──────────────────────────────────────────────────────
# A suggested burn must bring the conjunction below this risk (log10 Pc) …
MANOEUVRE_TARGET_LOG_PC = -7.0
# … and at least this far apart (km)
MANOEUVRE_TARGET_MISS_KM = 2.0
# ΔV search limits (m/s)
MANOEUVRE_MAX_DV = 5.0
MANOEUVRE_MIN_DV = 0.001
# Earliest a burn can be scheduled from now (hours)
MANOEUVRE_MIN_LEAD_HOURS = 1.0
# Burn directions in the satellite's RTN frame
MANOEUVRE_DIRECTIONS = {
    "prograde": (0.0, 1.0, 0.0),
    "retrograde": (0.0, -1.0, 0.0),
    "radial-out": (1.0, 0.0, 0.0),
    "radial-in": (-1.0, 0.0, 0.0),
    "normal": (0.0, 0.0, 1.0),
    "anti-normal": (0.0, 0.0, -1.0),
}
# Default spacecraft used when the operator has not set one
DEFAULT_SPACECRAFT = {"mass_kg": 500.0, "isp_s": 220.0, "thrust_n": 1.0}
# ΔV magnitudes (m/s) tried by the CDM-only manoeuvre simulator (ESA dataset events
# have no orbit states, so manoeuvre_simulator.py estimates their burns analytically)
MANOEUVRE_DV_OPTIONS = [0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1.0, 2.0]

# Operator accept/decline log
DECISIONS_LOG = PROJECT_ROOT / "logs" / "manoeuvre_decisions.jsonl"

# ─── Exports ──────────────────────────────────────────────────────────────────
EXPORT_DIR = PROJECT_ROOT / "exports"

# ─── Dashboard Configuration ─────────────────────────────────────────────────
STREAMLIT_PAGE_TITLE = "OrbitGuard AI 🛰️"
STREAMLIT_PAGE_ICON = "🛰️"
STREAMLIT_LAYOUT = "wide"

# How often the dashboard checks for new live data (seconds). CelesTrak only
# publishes new GP data every 2 hours, so new screening results follow that.
DASHBOARD_REFRESH_INTERVAL = 300

# Risk level color mapping
RISK_COLORS = {
    "CRITICAL": "#FF0040",
    "HIGH": "#FF6B35",
    "MEDIUM": "#FFD700",
    "LOW": "#00E676",
    "NEGLIGIBLE": "#40C4FF",
}

# Risk level thresholds (log10 collision probability)
RISK_LEVELS = {
    "CRITICAL": -3.0,
    "HIGH": -4.5,
    "MEDIUM": -6.0,
    "LOW": -7.5,
    "NEGLIGIBLE": float("-inf"),
}
