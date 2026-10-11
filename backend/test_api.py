import sys
import os

# Add backend directory to path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from fastapi.testclient import TestClient
from app.main import app

def test_orbitguard_backend():
    client = TestClient(app)

    print("[TEST] Testing OrbitGuard AI API...")

    # 1. Health check
    res = client.get("/api/health")
    assert res.status_code == 200, f"Health check failed: {res.text}"
    print("  [PASS] [1/6] Health check passed:", res.json()["status"])

    # 2. Satellites catalog
    res = client.get("/api/conjunctions/satellites")
    assert res.status_code == 200, f"Satellites endpoint failed: {res.text}"
    sats = res.json()
    assert len(sats) >= 5, "Catalog should have at least 5 satellites"
    print(f"  [PASS] [2/6] Satellite catalog passed: {len(sats)} satellites found")

    # 3. Screening conjunctions for ISS (25544)
    res = client.get("/api/conjunctions/screen?norad_id=25544&days=3")
    assert res.status_code == 200, f"Screening failed: {res.text}"
    screening = res.json()
    assert screening["conjunctions_count"] > 0, "Should detect conjunctions for ISS"
    print(f"  [PASS] [3/6] Conjunction screening passed: {screening['conjunctions_count']} events detected (Critical: {screening['high_risk_count']})")

    # 4. 3D Orbit path calculation
    res = client.get("/api/conjunctions/orbit/25544?points=30")
    assert res.status_code == 200, f"Orbit path failed: {res.text}"
    orbit = res.json()
    assert len(orbit["coordinates"]) == 30, "Should return 30 3D orbit coordinate points"
    print(f"  [PASS] [4/6] 3D Orbit coordinates passed: {len(orbit['coordinates'])} points computed")

    # 5. ML Prediction with SHAP XAI
    test_cdm = {
        "event_id": "TEST-ISS-2026-001",
        "satellite_id": 25544,
        "secondary_object_id": 33758,
        "time_to_tca_hours": 36.0,
        "miss_distance_m": 142.0,
        "relative_velocity_km_s": 14.7,
        "radial_miss_distance_m": 38.5,
        "in_track_miss_distance_m": 125.0,
        "cross_track_miss_distance_m": 54.0,
        "radial_position_covariance": 120.0,
        "cdm_count_for_event": 5,
        "solar_flux_f10_7": 162.0,
        "ap_geomagnetic_index": 22.0
    }
    res = client.post("/api/predict/", json=test_cdm)
    assert res.status_code == 200, f"ML prediction failed: {res.text}"
    pred = res.json()
    assert "shap_explanations" in pred, "Prediction must have SHAP explanations"
    assert len(pred["shap_explanations"]) > 0, "Must contain SHAP features"
    assert pred["risk_level"] == "CRITICAL", "Test close pass should be CRITICAL"
    print(f"  [PASS] [5/6] ML Prediction & SHAP passed: Risk={pred['risk_level']}, Decision={pred['go_no_go_decision']}, SHAP features={len(pred['shap_explanations'])}")

    # 6. Maneuver optimization (Delta-V trade-off curve)
    maneuver_req = {
        "event_id": "TEST-ISS-2026-001",
        "current_poc": 0.00028,
        "miss_distance_m": 142.0,
        "satellite_mass_kg": 500.0
    }
    res = client.post("/api/maneuver/optimize", json=maneuver_req)
    assert res.status_code == 200, f"Maneuver optimization failed: {res.text}"
    opt = res.json()
    assert opt["recommended_delta_v_ms"] > 0, "Should recommend positive delta-v"
    assert len(opt["trade_off_curve"]) > 5, "Trade-off curve must have points for scatter plot"
    print(f"  [PASS] [6/6] Maneuver Optimization passed: Recommended burn={opt['recommended_delta_v_ms']} m/s, Trade-off points={len(opt['trade_off_curve'])}")

    print("\n>>> ALL 6 BACKEND TESTS PASSED SUCCESSFULLY! <<<\n")

if __name__ == "__main__":
    test_orbitguard_backend()
