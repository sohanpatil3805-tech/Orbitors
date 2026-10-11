"""
Fast offline checks of the physics used for risk and manoeuvres.
Run:  python -m unittest discover tests      (or: python -m pytest tests)
"""

import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from orbit_propagation import MU, burn_offset, burn_sensitivity, propagate_j2, rtn_basis  # noqa: E402
from risk_engine import (covariance_rtn, probability_of_collision, risk_level, risk_status,  # noqa: E402
                         max_probability_of_collision)

# Circular ISS-like orbit (TEME, km, km/s)
R0 = 6378.137 + 420.0
V0 = np.sqrt(MU / R0)
STATE = np.array([R0, 0.0, 0.0, 0.0, V0 * np.cos(np.radians(51.6)), V0 * np.sin(np.radians(51.6))])


class TestCollisionProbability(unittest.TestCase):
    def test_closed_form_head_on(self):
        for sigma, radius in [(10.0, 5.0), (100.0, 20.0), (500.0, 10.0)]:
            pc = probability_of_collision([[0, 0, 0]], [[0, 7000, 0]], covariance_rtn(sigma, sigma, sigma), [radius])[0]
            self.assertAlmostEqual(pc / (1 - np.exp(-radius ** 2 / (2 * sigma ** 2))), 1.0, places=5)

    def test_monte_carlo(self):
        rng = np.random.default_rng(1)
        C = covariance_rtn(80.0, 200.0, 40.0, 0.3, -0.2, 0.1)[0]
        miss, v, radius = np.array([30.0, -60.0, 20.0]), np.array([3000.0, 9000.0, -6000.0]), 15.0
        pc = probability_of_collision([miss], [v], C[None], [radius])[0]
        s = rng.multivariate_normal(miss, C, size=2_000_000)
        vh = v / np.linalg.norm(v)
        mc = np.mean(np.linalg.norm(s - np.outer(s @ vh, vh), axis=1) < radius)
        self.assertLess(abs(pc - mc), 4 * np.sqrt(mc * (1 - mc) / len(s)) + 1e-7)

    def test_far_miss_is_negligible(self):
        pc = probability_of_collision([[5000.0, 0, 0]], [[0, 7000, 0]], covariance_rtn(50, 50, 50), [10.0])[0]
        self.assertLess(pc, 1e-30 + 1e-12)

    def test_max_pc_bounds_pc(self):
        args = ([[200.0, 0, 0]], [[0, 7000, 0]], covariance_rtn(100, 300, 100), [10.0])
        self.assertGreaterEqual(max_probability_of_collision(*args)[0], probability_of_collision(*args)[0])

    def test_levels_and_status(self):
        self.assertEqual(risk_level(-2.5), "CRITICAL")
        self.assertEqual(risk_level(-4.0), "HIGH")
        self.assertEqual(risk_level(-5.0), "MEDIUM")
        self.assertEqual(risk_level(-7.0), "LOW")
        self.assertEqual(risk_level(-12.0), "NEGLIGIBLE")
        self.assertEqual(risk_status("HIGH", 5.0), "DANGER")
        self.assertEqual(risk_status("MEDIUM", 5.0), "REVIEW")
        self.assertEqual(risk_status("LOW", 0.5), "REVIEW")      # very close pass needs review
        self.assertEqual(risk_status("LOW", 5.0), "SAFE")


class TestManoeuvrePhysics(unittest.TestCase):
    def test_linear_model_matches_full_propagation(self):
        t = np.linspace(0, 43200, 61)
        S = burn_sensitivity(STATE, 0.0, t)
        for dv in ([0, 0.1, 0], [0.1, 0, 0], [0, 0, 0.1]):
            lin = np.einsum("tij,j->ti", S[:, :3], np.array(dv))
            full = burn_offset(STATE, 0.0, np.array(dv), t[-1], step_s=10.0)(t)[0]
            self.assertLess(np.abs(lin - full).max() / np.abs(full).max(), 0.01)

    def test_clohessy_wiltshire_along_track_drift(self):
        n = np.sqrt(MU / R0 ** 3)
        period = 2 * np.pi / n
        ts = np.array([1.0, 2.0]) * period
        dv = 0.1
        nominal = propagate_j2(STATE, 0.0, ts)
        off = burn_offset(STATE, 0.0, np.array([0, dv, 0]), ts[-1], step_s=5.0)(ts)[0] * 1000
        for k, tau in enumerate(ts):
            along = (rtn_basis(nominal[k, :3], nominal[k, 3:]).T @ off[k])[1]
            cw = 4 * dv / n * np.sin(n * tau) - 3 * dv * tau
            self.assertLess(abs(along - cw) / abs(cw), 0.05)

    def test_prograde_raises_orbit(self):
        off = burn_offset(STATE, 0.0, np.array([0, 0.5, 0]), 3000.0)
        dr, _ = off(np.array([2700.0]))   # ~half an orbit later the satellite is higher
        nominal = propagate_j2(STATE, 0.0, np.array([2700.0]))[0]
        self.assertGreater(dr[0] @ (nominal[:3] / np.linalg.norm(nominal[:3])), 0)

    def test_rocket_equation(self):
        fuel = 500.0 * (1 - np.exp(-1.0 / (220.0 * 9.80665)))
        self.assertAlmostEqual(fuel, 0.23171, places=4)


if __name__ == "__main__":
    unittest.main()
