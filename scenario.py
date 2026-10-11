"""
OrbitGuard AI — Test scenarios

Injects a simulated object on a known collision course with a watchlist
satellite, so the whole chain (screening → risk → 3D alert → manoeuvre
suggestion) can be checked against a ground truth:

  * at the chosen time of closest approach the threat sits `miss_m` metres from
    the satellite (radially) and crosses its path at `crossing_deg`;
  * the threat is propagated with the J2 model both ways from that point.

Used by the dashboard's test mode and by validate.py.
"""

from dataclasses import dataclass

import numpy as np
import pandas as pd

from screening import EphemerisObject, ObjectSource

THREAT_ID_BASE = 990000


@dataclass
class Threat:
    object_id: int
    primary_id: int
    tca_s: float
    miss_m: float
    kind: str
    ephemeris: EphemerisObject
    row: pd.Series


def _rotate(v: np.ndarray, axis: np.ndarray, angle_rad: float) -> np.ndarray:
    k = axis / np.linalg.norm(axis)
    return v * np.cos(angle_rad) + np.cross(k, v) * np.sin(angle_rad) + k * (k @ v) * (1 - np.cos(angle_rad))


def create_threat(objects: pd.DataFrame, source: ObjectSource, primary_id: int, hours_to_tca: float,
                  miss_m: float = 30.0, crossing_deg: float = 60.0, kind: str = "debris",
                  horizon_h: float = 72.0, index: int = 0) -> Threat:
    """A simulated debris piece (kind='debris') or working satellite (kind='satellite')."""
    tca_s = hours_to_tca * 3600.0
    r_p, v_p = source.state(primary_id, tca_s)
    r_p, v_p = r_p[0], v_p[0]
    radial = r_p / np.linalg.norm(r_p)
    v_s = _rotate(v_p, radial, np.radians(crossing_deg))
    r_s = r_p + radial * (miss_m / 1000.0)
    eph = EphemerisObject(np.concatenate([r_s, v_s]), tca_s, horizon_h * 3600.0)

    oid = THREAT_ID_BASE + index
    p = objects.loc[primary_id]
    satellite = kind == "satellite"
    row = pd.Series({
        "OBJECT_NAME": f"TEST-{'SAT' if satellite else 'DEBRIS'}-{index + 1} (simulated)",
        "EPOCH": pd.Timestamp.now(tz="UTC"), "EPOCH_AGE_DAYS": 0.1,
        "SMA_KM": p["SMA_KM"], "ECCENTRICITY": p["ECCENTRICITY"], "INCLINATION": p["INCLINATION"],
        "PERIGEE_KM": p["PERIGEE_KM"], "APOGEE_KM": p["APOGEE_KM"], "PERIOD_MIN": p["PERIOD_MIN"],
        "BSTAR": 0.0, "OBJECT_TYPE": "PAYLOAD" if satellite else "DEBRIS",
        "OWNER": "TEST" if satellite else None, "OPS_STATUS": "+" if satellite else None, "RCS": np.nan,
        "MANOEUVRABLE": satellite, "RADIUS_M": 5.0 if satellite else 0.5, "IMPORTANT": False,
    }, name=oid)
    return Threat(oid, primary_id, tca_s, miss_m, kind, eph, row)


def with_threats(objects: pd.DataFrame, source: ObjectSource, threats: list[Threat]):
    """Catalogue table and position source that include the simulated threats."""
    if not threats:
        return objects, source
    objs = pd.concat([objects, pd.DataFrame([t.row for t in threats])])
    objs.index.name = objects.index.name
    eph = {**(source.ephemerides or {}), **{t.object_id: t.ephemeris for t in threats}}
    return objs, ObjectSource(source.satrecs, source.t0, eph)
