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
    "2019-006": "Indian ASAT Debris",
}
CELESTRAK_CACHE_TTL_SECONDS = 300  # 5 minutes

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

# ─── Collision Screening Parameters ──────────────────────────────────────────
# Distance threshold in km for initial conjunction screening
SCREENING_DISTANCE_KM = 25.0

# Time window for propagation (hours ahead)
PROPAGATION_WINDOW_HOURS = 72

# Time step for propagation (seconds)
PROPAGATION_STEP_SECONDS = 60

# ─── Manoeuvre Simulation ─────────────────────────────────────────────────────
# Delta-V options to simulate (m/s)
MANOEUVRE_DV_OPTIONS = [0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0]

# Directions for manoeuvre burns
MANOEUVRE_DIRECTIONS = ["prograde", "retrograde", "normal", "anti-normal", "radial-in", "radial-out"]

# ─── Exports ──────────────────────────────────────────────────────────────────
EXPORT_DIR = PROJECT_ROOT / "exports"

# ─── Dashboard Configuration ─────────────────────────────────────────────────
STREAMLIT_PAGE_TITLE = "OrbitGuard AI 🛰️"
STREAMLIT_PAGE_ICON = "🛰️"
STREAMLIT_LAYOUT = "wide"

# Refresh interval in seconds for live data
DASHBOARD_REFRESH_INTERVAL = 300

# Map configuration
MAP_STYLE = "mapbox://styles/mapbox/dark-v11"

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
