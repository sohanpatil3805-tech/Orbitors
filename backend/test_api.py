"""
End-to-end API checks against the real engine, without network access:

  * live endpoints use an offline catalogue (a built-in ISS element set) with a
    simulated debris threat on a collision course, assessed with the trained ML
    uncertainty model and planned with the real manoeuvre planner;
  * ML endpoints use the trained CDM model and Dataset/test_data.csv (skipped if absent);
  * operator decisions go to a temporary log, never the real audit trail.

Run from backend/:  python test_api.py      (or: python -m unittest test_api)
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

os.environ["ORBITGUARD_LIVE"] = "0"   # no background screening of the real catalogue
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402  (also puts the project root on sys.path)
from app.services import live_service  # noqa: E402

import decisions  # noqa: E402
from catalog import Catalog  # noqa: E402
from config import TEST_DATA_PATH, TRAIN_DATA_PATH  # noqa: E402
from live_pipeline import LiveState, load_uncertainty_model  # noqa: E402
from orbit_propagation import utc_now  # noqa: E402
from risk_engine import LiveRiskAssessor  # noqa: E402
from scenario import create_threat, with_threats  # noqa: E402
from screening import NEAR_KM, ObjectSource, screen  # noqa: E402
from space_weather import FALLBACK_WEATHER  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tests"))
from test_screening import ISS, _world  # noqa: E402


def offline_state() -> LiveState:
    """Live state for one ISS orbit plus a simulated debris piece 10 h ahead, 30 m away."""
    objects, source = _world()
    t0 = utc_now()
    source = ObjectSource(source.satrecs, t0)
    objects["EPOCH_AGE_DAYS"] = (pd.Timestamp(t0) - pd.Timestamp(ISS["EPOCH"], tz="UTC")).total_seconds() / 86400
    threat = create_threat(objects, source, 25544, hours_to_tca=10.0, miss_m=30.0, crossing_deg=75.0)
    all_objects, all_source = with_threats(objects, source, [threat])
    weather = {**FALLBACK_WEATHER, "date": None, "kp_max": None, "source": "offline test"}
    assessor = LiveRiskAssessor(load_uncertainty_model(), weather)
    conj, near = screen(all_objects, all_source, [25544], horizon_h=24.0, near_km=NEAR_KM)
    conj = assessor.assess(conj, all_objects, t0)
    catalog = Catalog(objects=objects, satrecs=source.satrecs, source="offline test catalogue", built_at=t0)
    return LiveState(t0, catalog, all_objects, all_source, [25544], conj, near, weather, 0, [threat], "offline-test")


class TestLiveAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls._log = decisions.DECISIONS_LOG
        cls._tmp = tempfile.TemporaryDirectory()
        decisions.DECISIONS_LOG = Path(cls._tmp.name) / "decisions.jsonl"
        cls.state = offline_state()
        live_service.set_state(cls.state)

    @classmethod
    def tearDownClass(cls):
        decisions.DECISIONS_LOG = cls._log
        cls._tmp.cleanup()

    def danger(self) -> dict:
        res = self.client.get("/api/conjunctions/screen", params={"status": "DANGER"})
        self.assertEqual(res.status_code, 200, res.text)
        conj = res.json()["conjunctions"]
        self.assertEqual(len(conj), 1, "the simulated threat must be the only DANGER conjunction")
        return conj[0]

    def test_1_status_and_health(self):
        st = self.client.get("/api/status").json()
        self.assertEqual(st["phase"], "ready")
        self.assertEqual(st["watchlist_size"], 1)
        self.assertEqual(st["satellite_status_counts"]["DANGER"], 1)
        self.assertIn(self.client.get("/api/health").json()["status"], ("HEALTHY", "DEGRADED"))

    def test_2_satellites_and_orbit(self):
        sats = self.client.get("/api/conjunctions/satellites").json()
        self.assertEqual([s["norad_id"] for s in sats], [25544])
        iss = sats[0]
        self.assertEqual(iss["status"], "DANGER")
        self.assertAlmostEqual(iss["inclination_deg"], 51.63, places=1)
        self.assertTrue(400 < iss["altitude_now_km"] < 440)
        self.assertTrue(7.5 < iss["velocity_km_s"] < 7.8)
        orbit = self.client.get("/api/conjunctions/orbit/25544", params={"points": 30}).json()
        self.assertEqual(len(orbit["coordinates"]), 30)
        self.assertTrue(all(380 < p["alt_km"] < 460 for p in orbit["coordinates"]))
        self.assertEqual(self.client.get("/api/conjunctions/orbit/1").status_code, 404)

    def test_3_conjunction_physics(self):
        ev = self.danger()
        self.assertTrue(ev["simulated"])
        self.assertLess(abs(ev["miss_distance_m"] - 30.0), 5.0)
        self.assertLess(abs(ev["time_to_tca_hours"] - 10.0), 0.2)
        self.assertIn(ev["risk_level"], ("CRITICAL", "HIGH"))
        self.assertEqual(ev["recommended_action"], "MANEUVER_RECOMMENDED")

        detail = self.client.get(f"/api/conjunctions/detail/{ev['key']}").json()
        enc = detail["encounter"]
        self.assertGreater(enc["sigma_major_m"], enc["sigma_minor_m"])
        self.assertLess(enc["mahalanobis_distance"], 1.0)   # a 30 m miss is deep inside the uncertainty
        sec = next(o for o in detail["objects"] if o["role"] == "secondary")
        self.assertIsNotNone(sec["ml_explanation"], "the ML uncertainty model must explain its prediction")
        self.assertEqual(len(sec["ml_explanation"]["t"]["features"]), 12)

        wi = self.client.post("/api/predict/what-if", json={"source": "live", "id": ev["key"], "miss_scale": 100.0}).json()
        self.assertLess(wi["modified"]["log_pc"], wi["baseline"]["log_pc"], "a 100x larger miss must lower the risk")
        self.assertEqual(self.client.get("/api/conjunctions/detail/nope").status_code, 404)

    def test_4_manoeuvre_plan_and_decision(self):
        ev = self.danger()
        entry = live_service.plans[ev["key"]]                 # queued automatically for DANGER events
        live_service.compute_plan(ev["key"], entry, self.state)  # no worker thread in tests: run it here
        plan = self.client.get(f"/api/maneuver/plan/{ev['key']}").json()
        self.assertEqual(plan["status"], "ready", plan.get("error"))
        rec = plan["options"][0]
        self.assertEqual(rec["label"], "Recommended")
        self.assertGreaterEqual(rec["new_miss_km"], 0.9 * plan["target"]["miss_km"])
        self.assertLessEqual(rec["new_log_pc"], plan["target"]["log_pc"] + 0.5)
        self.assertLess(rec["dv_ms"], 1.0)
        curve = plan["tradeoff_curve"]
        self.assertEqual(curve[0]["dv_ms"], 0.0)
        self.assertTrue(any(p["is_option"] for p in curve))
        self.assertLess(curve[-1]["log_pc"], curve[0]["log_pc"])

        res = self.client.post("/api/maneuver/decision", json={"key": ev["key"], "decision": "ACCEPTED",
                                                               "option_index": 0, "note": "test"})
        self.assertEqual(res.status_code, 200, res.text)
        self.assertEqual(self.client.get("/api/maneuver/decisions").json()[0]["decision"], "ACCEPTED")
        mitigated = self.client.get("/api/conjunctions/screen", params={"status": "MITIGATED"}).json()
        self.assertEqual(mitigated["conjunctions_count"], 1)
        self.assertEqual(mitigated["conjunctions"][0]["recommended_action"], "MANEUVER_ACCEPTED")


@unittest.skipUnless(TEST_DATA_PATH.exists() and TRAIN_DATA_PATH.exists(), "ESA dataset not in Dataset/")
class TestModelAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.events = cls.client.get("/api/predict/esa-events").json()

    def test_esa_events_and_replay(self):
        self.assertGreaterEqual(len(self.events), 3)
        self.assertIn("HIGH_RISK", {e["category"] for e in self.events})
        eid = self.events[0]["event_id"]
        rep = self.client.get(f"/api/predict/esa-replay/{eid}").json()
        self.assertEqual(len(rep["series"]), rep["n_cdms"])
        dec = rep["decision_cdm"]
        self.assertLess(abs(dec["model_risk"] - dec["esa_risk"]), 1.0, "model should track ESA's risk")
        self.assertAlmostEqual(rep["shap"]["prediction"], dec["model_risk"], places=3)
        self.assertEqual(self.client.get("/api/predict/esa-replay/-1").status_code, 404)

    def test_predict_raw_cdm(self):
        row = pd.read_csv(TEST_DATA_PATH, nrows=1).iloc[0]
        cdm = {k: (None if pd.isna(v) else (v.item() if isinstance(v, np.generic) else v))
               for k, v in row.drop(["risk"]).items()}
        res = self.client.post("/api/predict/", json={"event_id": "row0", "cdm": cdm}).json()
        self.assertLess(abs(res["predicted_log_pc"] - row["risk"]), 1.0)
        self.assertIsNotNone(res["physics_log_pc"])
        self.assertTrue(res["shap"]["features"])

    def test_what_if_and_cdm_manoeuvre(self):
        eid = next(e["event_id"] for e in self.events if e["category"] == "HIGH_RISK")
        wi = self.client.post("/api/predict/what-if", json={"source": "esa", "id": str(eid), "sigma_scale": 0.01}).json()
        self.assertLess(wi["modified"]["log_pc"], wi["baseline"]["log_pc"], "tiny uncertainty around a miss → lower Pc")
        opt = self.client.post("/api/maneuver/optimize", json={"event_id": eid}).json()
        self.assertIn("prograde", opt["curves"])
        self.assertIsNotNone(opt["best"])

    def test_benchmark(self):
        m = self.client.get("/api/benchmark/metrics").json()
        self.assertGreater(m["kpis"]["test_r2"], 0.99)
        self.assertGreater(m["kpis"]["alert_f2"], 0.9)
        self.assertEqual({s["split"] for s in m["splits"]}, {"train", "validation", "test"})
        self.assertEqual(len(m["uncertainty_model"]["errors"]), 3)
        self.assertGreater(m["validation"]["passed"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
