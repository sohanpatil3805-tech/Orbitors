"""
OrbitGuard AI — CelesTrak Live Data Fetcher
Fetches live TLE / GP element data from CelesTrak for real-time orbital awareness.
"""

import json
import time
import hashlib
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional

import numpy as np
import pandas as pd
import requests

from config import (
    CELESTRAK_BASE_URL,
    CELESTRAK_GROUPS,
    CELESTRAK_CACHE_TTL_SECONDS,
    CACHE_DIR,
)


class CelesTrakFetcher:
    """Handles fetching and caching of CelesTrak orbital element data."""

    def __init__(self, cache_dir: Optional[Path] = None, cache_ttl: int = CELESTRAK_CACHE_TTL_SECONDS):
        self.cache_dir = cache_dir or CACHE_DIR / "celestrak"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_ttl = cache_ttl

    def _cache_key(self, group: str, fmt: str) -> str:
        """Generate a cache filename for a given request."""
        raw = f"{group}_{fmt}"
        return hashlib.md5(raw.encode()).hexdigest() + ".json"

    def _is_cache_valid(self, cache_path: Path) -> bool:
        """Check if a cache file exists and is within TTL."""
        if not cache_path.exists():
            return False
        age = time.time() - cache_path.stat().st_mtime
        return age < self.cache_ttl

    def fetch_group(self, group: str, fmt: str = "json") -> list[dict]:
        """
        Fetch orbital elements for a CelesTrak group.

        Parameters
        ----------
        group : str
            CelesTrak group name (e.g., 'active', 'stations', 'starlink').
        fmt : str
            Response format — 'json' for GP element JSON.

        Returns
        -------
        list[dict]
            List of satellite GP element dictionaries.
        """
        cache_path = self.cache_dir / self._cache_key(group, fmt)

        if self._is_cache_valid(cache_path):
            with open(cache_path, "r") as f:
                return json.load(f)

        url = f"{CELESTRAK_BASE_URL}?GROUP={group}&FORMAT={fmt}"
        try:
            resp = requests.get(url, timeout=30)
            resp.raise_for_status()
            data = resp.json()

            with open(cache_path, "w") as f:
                json.dump(data, f)

            return data
        except requests.RequestException as e:
            print(f"[CelesTrak] Error fetching {group}: {e}")
            if cache_path.exists():
                with open(cache_path, "r") as f:
                    return json.load(f)
            return []

    def fetch_all_debris(self) -> pd.DataFrame:
        """Fetch all known debris groups and combine into a single DataFrame."""
        debris_groups = [
            "cosmos-1408-debris",
            "fengyun-1c-debris",
            "iridium-33-debris",
            "cosmos-2251-debris",
            "2019-006",
        ]
        all_debris = []
        for group in debris_groups:
            data = self.fetch_group(group)
            for item in data:
                item["DEBRIS_SOURCE"] = group
            all_debris.extend(data)

        if not all_debris:
            return pd.DataFrame()

        df = pd.DataFrame(all_debris)
        df["FETCH_TIMESTAMP"] = datetime.now(timezone.utc).isoformat()
        return df

    def fetch_active_satellites(self) -> pd.DataFrame:
        """Fetch all active satellites and return as DataFrame."""
        data = self.fetch_group("active")
        if not data:
            return pd.DataFrame()

        df = pd.DataFrame(data)
        df["FETCH_TIMESTAMP"] = datetime.now(timezone.utc).isoformat()
        return df

    def fetch_stations(self) -> pd.DataFrame:
        """Fetch space stations (ISS, Tiangong, etc.)."""
        data = self.fetch_group("stations")
        if not data:
            return pd.DataFrame()
        return pd.DataFrame(data)

    def get_satellite_by_norad_id(self, norad_id: int, group: str = "active") -> Optional[dict]:
        """Look up a satellite by its NORAD catalog ID."""
        data = self.fetch_group(group)
        for sat in data:
            if sat.get("NORAD_CAT_ID") == norad_id:
                return sat
        return None

    def get_catalog_summary(self) -> dict:
        """Get a summary of tracked objects across all groups."""
        summary = {}
        for group_key, group_name in CELESTRAK_GROUPS.items():
            try:
                data = self.fetch_group(group_key)
                summary[group_name] = len(data)
            except Exception:
                summary[group_name] = 0
        return summary

    @staticmethod
    def gp_to_orbital_elements(gp_record: dict) -> dict:
        """
        Convert a CelesTrak GP JSON record to standard orbital elements.

        Returns dict with keys:
            epoch, semi_major_axis_km, eccentricity, inclination_deg,
            raan_deg, arg_perigee_deg, mean_anomaly_deg, mean_motion_rev_day,
            bstar, period_min
        """
        mean_motion = gp_record.get("MEAN_MOTION", 0)
        period_min = 1440.0 / mean_motion if mean_motion > 0 else float("inf")

        # Semi-major axis from mean motion (Kepler's third law)
        mu_earth = 398600.4418  # km³/s²
        if mean_motion > 0:
            n_rad_s = mean_motion * 2 * np.pi / 86400.0
            sma = (mu_earth / (n_rad_s ** 2)) ** (1.0 / 3.0)
        else:
            sma = 0.0

        return {
            "object_name": gp_record.get("OBJECT_NAME", "UNKNOWN"),
            "norad_id": gp_record.get("NORAD_CAT_ID", 0),
            "epoch": gp_record.get("EPOCH", ""),
            "semi_major_axis_km": sma,
            "eccentricity": gp_record.get("ECCENTRICITY", 0),
            "inclination_deg": gp_record.get("INCLINATION", 0),
            "raan_deg": gp_record.get("RA_OF_ASC_NODE", 0),
            "arg_perigee_deg": gp_record.get("ARG_OF_PERICENTER", 0),
            "mean_anomaly_deg": gp_record.get("MEAN_ANOMALY", 0),
            "mean_motion_rev_day": mean_motion,
            "bstar": gp_record.get("BSTAR", 0),
            "period_min": period_min,
            "apogee_km": sma * (1 + gp_record.get("ECCENTRICITY", 0)) - 6371.0,
            "perigee_km": sma * (1 - gp_record.get("ECCENTRICITY", 0)) - 6371.0,
        }


def compute_orbit_altitude_band(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute altitude band categories for satellites based on mean motion.

    Categories: LEO (<2000 km), MEO (2000-35786 km), GEO (~35786 km), HEO (highly elliptical)
    """
    mu = 398600.4418
    earth_radius = 6371.0

    def classify(row):
        mm = row.get("MEAN_MOTION", 0)
        ecc = row.get("ECCENTRICITY", 0)
        if mm <= 0:
            return "UNKNOWN"
        n_rad_s = mm * 2 * np.pi / 86400.0
        sma = (mu / (n_rad_s ** 2)) ** (1.0 / 3.0)
        apogee = sma * (1 + ecc) - earth_radius
        perigee = sma * (1 - ecc) - earth_radius

        if ecc > 0.25:
            return "HEO"
        elif apogee < 2000:
            return "LEO"
        elif apogee < 35000:
            return "MEO"
        elif apogee < 40000:
            return "GEO"
        else:
            return "HEO"

    df = df.copy()
    df["ORBIT_BAND"] = df.apply(classify, axis=1)
    return df


if __name__ == "__main__":
    fetcher = CelesTrakFetcher()

    print("=" * 60)
    print("  CelesTrak Live Data Fetch Test")
    print("=" * 60)

    # Fetch active satellites
    active = fetcher.fetch_active_satellites()
    print(f"\nActive satellites: {len(active)}")

    # Fetch debris
    debris = fetcher.fetch_all_debris()
    print(f"Debris objects:   {len(debris)}")

    # Fetch stations
    stations = fetcher.fetch_stations()
    print(f"Space stations:   {len(stations)}")

    # Show catalog summary
    print("\n--- Catalog Summary ---")
    summary = fetcher.get_catalog_summary()
    for name, count in summary.items():
        print(f"  {name:30s}: {count:>6,d}")
