"""JSON helpers: numpy / pandas values → plain Python, NaN and inf → None."""

import math
from datetime import datetime

import numpy as np
import pandas as pd


def clean(o):
    """Recursively convert a result into JSON-safe Python types."""
    if isinstance(o, dict):
        return {str(k): clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple, np.ndarray, pd.Series)):
        return [clean(v) for v in (o.tolist() if isinstance(o, (np.ndarray, pd.Series)) else o)]
    if isinstance(o, (bool, np.bool_)):
        return bool(o)
    if isinstance(o, (int, np.integer)):
        return int(o)
    if isinstance(o, (float, np.floating)):
        f = float(o)
        return f if math.isfinite(f) else None
    if isinstance(o, (pd.Timestamp, datetime)):
        return None if pd.isna(o) else iso(o)
    if o is None or o is pd.NaT or o is pd.NA:
        return None
    return o


def iso(t) -> str:
    """ISO-8601 UTC timestamp."""
    ts = pd.Timestamp(t)
    ts = ts.tz_localize("UTC") if ts.tzinfo is None else ts.tz_convert("UTC")
    return ts.isoformat().replace("+00:00", "Z")


def num(x):
    """Float, or None for missing / non-finite values."""
    try:
        f = float(x)
    except (TypeError, ValueError):
        return None
    return f if math.isfinite(f) else None
