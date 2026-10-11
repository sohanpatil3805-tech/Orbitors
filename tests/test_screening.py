"""
Offline end-to-end check: a simulated threat on a known collision course must be
screened at the right time and distance, flagged DANGER, and the suggested burn
must clear it. Uses a built-in ISS element set, so no network is needed.
Run:  python -m unittest discover tests
"""

import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from sgp4 import omm
from sgp4.api import Satrec

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config import MANOEUVRE_TARGET_LOG_PC, MANOEUVRE_TARGET_MISS_KM  # noqa: E402
from manoeuvre_planner import ManoeuvrePlanner  # noqa: E402
from risk_engine import LiveRiskAssessor  # noqa: E402
from scenario import create_threat, with_threats  # noqa: E402
from screening import ObjectSource, screen  # noqa: E402

ISS = {"OBJECT_NAME": "ISS (ZARYA)", "OBJECT_ID": "1998-067A", "EPOCH": "2026-10-10T19:00:00.000000",
       "MEAN_MOTION": 15.50, "ECCENTRICITY": 0.0004, "INCLINATION": 51.63, "RA_OF_ASC_NODE": 120.0,
       "ARG_OF_PERICENTER": 80.0, "MEAN_ANOMALY": 280.0, "EPHEMERIS_TYPE": 0, "CLASSIFICATION_TYPE": "U",
       "NORAD_CAT_ID": 25544, "ELEMENT_SET_NO": 999, "REV_AT_EPOCH": 50000, "BSTAR": 0.0002,
       "MEAN_MOTION_DOT": 0.0001, "MEAN_MOTION_DDOT": 0}
T0 = datetime(2026, 10, 11, 0, 0, tzinfo=timezone.utc)


def _world():
    sat = Satrec()
    omm.initialize(sat, ISS)
    objects = pd.DataFrame([{
        "OBJECT_NAME": "ISS (ZARYA)", "EPOCH": pd.Timestamp(ISS["EPOCH"], tz="UTC"), "EPOCH_AGE_DAYS": 0.2,
        "SMA_KM": 6795.0, "ECCENTRICITY": 0.0004, "INCLINATION": 51.63, "PERIGEE_KM": 414.0, "APOGEE_KM": 420.0,
        "PERIOD_MIN": 1440 / 15.5, "BSTAR": 0.0002, "OBJECT_TYPE": "PAYLOAD", "OWNER": "ISS", "OPS_STATUS": "+",
        "RCS": np.nan, "MANOEUVRABLE": True, "RADIUS_M": 55.0, "IMPORTANT": True}], index=pd.Index([25544], name="NORAD_CAT_ID"))
    return objects, ObjectSource({25544: sat}, T0)


class TestScreeningAndPlanning(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        objects, source = _world()
        cls.threat = create_threat(objects, source, 25544, hours_to_tca=10.0, miss_m=30.0, crossing_deg=75.0)
        cls.objects, cls.source = with_threats(objects, source, [cls.threat])
        cls.assessor = LiveRiskAssessor(uncertainty_model=None, weather={})
        conj = screen(cls.objects, cls.source, [25544], horizon_h=24.0)
        cls.conj = cls.assessor.assess(conj, cls.objects, T0)

    def test_threat_found_at_injected_time_and_distance(self):
        hit = self.conj[(self.conj["TCA_S"] - self.threat.tca_s).abs() < 60]
        self.assertEqual(len(hit), 1)
        self.assertLess(abs(hit.iloc[0]["MISS_KM"] * 1000 - 30.0), 5.0)
        self.assertLess(abs(hit.iloc[0]["TCA_S"] - self.threat.tca_s), 1.0)

    def test_threat_is_danger(self):
        hit = self.conj[(self.conj["TCA_S"] - self.threat.tca_s).abs() < 60].iloc[0]
        self.assertEqual(hit["STATUS"], "DANGER")

    def test_suggested_burn_clears_threat(self):
        ev = self.conj[(self.conj["TCA_S"] - self.threat.tca_s).abs() < 60].iloc[0]
        planner = ManoeuvrePlanner(self.objects, self.source, self.assessor, T0, horizon_h=24.0, now=T0)
        plan = planner.plan(ev, check_conflicts=False)
        self.assertIsNotNone(plan.recommended)
        rec = plan.recommended
        self.assertGreaterEqual(rec.verified_miss_km, 0.9 * MANOEUVRE_TARGET_MISS_KM)
        self.assertLessEqual(rec.verified_log_pc, MANOEUVRE_TARGET_LOG_PC + 0.1)
        self.assertLess(rec.dv_ms, 1.0)   # a 30 m miss 10 h out needs centimetres per second, not metres


if __name__ == "__main__":
    unittest.main()
