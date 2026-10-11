"""
OrbitGuard AI — Space Weather
Daily solar and geomagnetic indices from CelesTrak (SW-Last5Years.csv).

Solar activity heats the upper atmosphere, which raises drag on LEO objects and
makes their orbits harder to predict. The uncertainty model uses these indices
with the same names as the ESA CDM dataset:

    F10  daily observed 10.7 cm solar radio flux (sfu)
    F3M  81-day average of F10.7 (the dataset's "3-month" flux)
    SSN  international sunspot number
    AP   daily average geomagnetic Ap index
"""

import io
from datetime import datetime, timezone
from typing import Optional

import pandas as pd

from config import SPACE_WEATHER_URL, SPACE_WEATHER_CACHE_TTL_SECONDS
from http_cache import cached_text

# Medians of the ESA CDM training data; used only if no space weather is available
FALLBACK_WEATHER = {"F10": 72.0, "F3M": 73.0, "SSN": 13.0, "AP": 6.0}


def load_space_weather(force: bool = False) -> pd.DataFrame:
    """Daily space weather table indexed by date (observed + predicted rows)."""
    text = cached_text(SPACE_WEATHER_URL, "SW-Last5Years.csv", SPACE_WEATHER_CACHE_TTL_SECONDS, force=force)
    if text is None:
        return pd.DataFrame()
    df = pd.read_csv(io.StringIO(text))
    df["DATE"] = pd.to_datetime(df["DATE"])
    return df.set_index("DATE").sort_index()


def weather_for(date: Optional[datetime] = None, table: Optional[pd.DataFrame] = None) -> dict:
    """
    Space weather indices for `date` (default: now), taken from the most recent
    row on or before that date that has an observed Ap value. Includes the
    source date so the dashboard can show how fresh it is.
    """
    table = load_space_weather() if table is None else table
    date = date or datetime.now(timezone.utc)
    if table.empty:
        return {**FALLBACK_WEATHER, "date": None, "kp_max": None, "source": "fallback (dataset medians)"}

    day = pd.Timestamp(date.date())
    observed = table[table["AP_AVG"].notna() & (table.index <= day)]
    if observed.empty:
        return {**FALLBACK_WEATHER, "date": None, "kp_max": None, "source": "fallback (dataset medians)"}
    row = observed.iloc[-1]

    kp_cols = [f"KP{i}" for i in range(1, 9)]
    kp_max = row[kp_cols].max() / 10.0 if all(c in row for c in kp_cols) else None
    return {
        "F10": float(row["F10.7_OBS"]),
        "F3M": float(row.get("F10.7_OBS_LAST81", row.get("F10.7_OBS_CENTER81"))),
        "SSN": float(row["ISN"]),
        "AP": float(row["AP_AVG"]),
        "kp_max": None if kp_max is None else float(kp_max),
        "date": observed.index[-1].date().isoformat(),
        "source": "CelesTrak SW-Last5Years",
    }


def storm_level(kp_max: Optional[float]) -> str:
    """NOAA G-scale label for the day's maximum Kp."""
    if kp_max is None:
        return "unknown"
    if kp_max >= 9: return "G5 extreme storm"
    if kp_max >= 8: return "G4 severe storm"
    if kp_max >= 7: return "G3 strong storm"
    if kp_max >= 6: return "G2 moderate storm"
    if kp_max >= 5: return "G1 minor storm"
    return "quiet"


if __name__ == "__main__":
    print(weather_for())
