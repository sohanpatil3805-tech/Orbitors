"""
OrbitGuard AI — Collision Avoidance Manoeuvre Simulator
Simulates delta-V manoeuvres and evaluates residual collision risk and fuel cost.
"""

import numpy as np
import pandas as pd
from typing import Optional
from dataclasses import dataclass, field

from config import MANOEUVRE_DV_OPTIONS, MANOEUVRE_DIRECTIONS


@dataclass
class ManoeuvreResult:
    """Result of a single manoeuvre simulation."""
    direction: str
    delta_v_ms: float
    original_risk: float
    residual_risk: float
    risk_reduction_pct: float
    delta_v_fuel_kg: float
    miss_distance_change_km: float
    new_miss_distance_km: float
    effectiveness_score: float  # risk reduction per unit fuel
    recommendation: str


@dataclass
class ManoeuvreReport:
    """Complete manoeuvre analysis report."""
    event_id: str
    original_risk: float
    original_miss_distance_km: float
    time_to_tca_hours: float
    results: list[ManoeuvreResult] = field(default_factory=list)
    best_option: Optional[ManoeuvreResult] = None
    no_manoeuvre_justified: bool = False


class ManoeuvreSimulator:
    """
    Simulates collision avoidance manoeuvres and evaluates trade-offs
    between risk reduction and fuel expenditure.
    """

    def __init__(
        self,
        predict_fn=None,
        spacecraft_mass_kg: float = 500.0,
        isp_s: float = 220.0,
    ):
        """
        Parameters
        ----------
        predict_fn : callable
            Function that takes feature array → risk prediction.
            If None, uses analytical approximation.
        spacecraft_mass_kg : float
            Dry mass of the spacecraft in kg.
        isp_s : float
            Specific impulse of the thruster in seconds.
        """
        self.predict_fn = predict_fn
        self.spacecraft_mass_kg = spacecraft_mass_kg
        self.isp_s = isp_s
        self.g0 = 9.80665  # m/s²

    def compute_fuel_mass(self, delta_v_ms: float) -> float:
        """
        Compute fuel mass required using the Tsiolkovsky rocket equation.

        ΔV = Isp × g₀ × ln(m₀ / m₁)
        → fuel = m₀ × (1 - exp(-ΔV / (Isp × g₀)))
        """
        exhaust_v = self.isp_s * self.g0
        fuel = self.spacecraft_mass_kg * (1 - np.exp(-delta_v_ms / exhaust_v))
        return fuel

    def estimate_miss_distance_change(
        self,
        delta_v_ms: float,
        direction: str,
        time_to_tca_hours: float,
        original_miss_distance_km: float,
    ) -> float:
        """
        Estimate how a manoeuvre changes the miss distance.
        Uses simplified orbital mechanics approximation.

        In reality, this depends on the geometry of the encounter,
        but for screening we use a linearised model.
        """
        time_to_tca_s = time_to_tca_hours * 3600.0

        # Direction-dependent effectiveness factor
        direction_factors = {
            "prograde": 1.0,
            "retrograde": 1.0,
            "normal": 0.8,
            "anti-normal": 0.8,
            "radial-in": 0.6,
            "radial-out": 0.6,
        }
        factor = direction_factors.get(direction, 0.5)

        # Miss distance change ≈ ΔV × time × factor (simplified, linear in ΔV)
        # Convert ΔV from m/s to km/s, time in seconds → change in km. For along-track
        # burns this is conservative: Clohessy–Wiltshire drift grows as ≈ 3·ΔV·t.
        # (No cap tied to the original miss distance: that froze the curve after a
        # few cm/s and hid how risk keeps falling with larger burns.)
        return (delta_v_ms / 1000.0) * time_to_tca_s * factor

    def estimate_residual_risk(
        self,
        original_risk: float,
        new_miss_distance_km: float,
        original_miss_distance_km: float,
        combined_sigma_km: float = 1.0,
    ) -> float:
        """
        Estimate residual collision risk after manoeuvre.

        Uses a Gaussian encounter model:
        Pc ∝ exp(-(d²) / (2σ²))

        The log₁₀ risk scales approximately as:
        Δlog₁₀Pc ≈ -(d_new² - d_old²) / (2σ² × ln(10))
        """
        if combined_sigma_km <= 0:
            combined_sigma_km = 1.0

        # Risk reduction in log space
        d_old_sq = (original_miss_distance_km / combined_sigma_km) ** 2
        d_new_sq = (new_miss_distance_km / combined_sigma_km) ** 2

        delta_log_risk = -(d_new_sq - d_old_sq) / (2.0 * np.log(10))

        residual = original_risk + delta_log_risk

        # Clamp to reasonable bounds
        residual = max(residual, -20.0)
        residual = min(residual, 0.0)

        return residual

    def _predict_risk(self, features: np.ndarray) -> float:
        """Model-predicted log10 Pc, or a default when no model is available."""
        if self.predict_fn is not None:
            return float(self.predict_fn(features.reshape(1, -1))[0])
        return -5.0

    @staticmethod
    def _encounter_state(features: np.ndarray, feature_names: list[str]) -> tuple[float, float, float]:
        """
        Extract (miss distance km, time to TCA hours, combined sigma km) from a
        feature vector. CDM distances and sigmas are in metres; time_to_tca in days.
        """
        def get(name):
            return float(features[feature_names.index(name)]) if name in feature_names else None

        miss_m = get("miss_distance")
        tca_days = get("time_to_tca")
        original_miss_km = miss_m / 1000.0 if miss_m is not None else 1.0
        time_to_tca_h = tca_days * 24.0 if tca_days is not None else 48.0

        combined_sigma_km = 1.0
        for sc in ["combined_uncertainty", "t_position_uncertainty", "c_position_uncertainty"]:
            sigma_m = get(sc)
            if sigma_m is not None and sigma_m > 0:
                combined_sigma_km = max(sigma_m / 1000.0, 0.01)
                break

        return original_miss_km, time_to_tca_h, combined_sigma_km

    def simulate_manoeuvre(
        self,
        features: np.ndarray,
        feature_names: list[str],
        delta_v_ms: float,
        direction: str,
        original_risk: Optional[float] = None,
    ) -> Optional[ManoeuvreResult]:
        """
        Simulate a single manoeuvre and compute residual risk.
        original_risk overrides the model prediction when given.
        """
        original_miss, time_to_tca, combined_sigma = self._encounter_state(features, feature_names)

        if original_risk is None:
            original_risk = self._predict_risk(features)

        # Compute miss distance change
        delta_miss = self.estimate_miss_distance_change(
            delta_v_ms, direction, time_to_tca, original_miss
        )
        new_miss = original_miss + delta_miss

        # Residual risk
        residual_risk = self.estimate_residual_risk(
            original_risk, new_miss, original_miss, combined_sigma
        )

        # Fuel cost
        fuel_kg = self.compute_fuel_mass(delta_v_ms)

        # Risk reduction
        risk_reduction = original_risk - residual_risk  # in log units
        risk_reduction_pct = (1 - 10 ** (residual_risk - original_risk)) * 100
        risk_reduction_pct = max(0, min(100, risk_reduction_pct))

        # Effectiveness score (risk reduction per kg of fuel)
        effectiveness = risk_reduction / (fuel_kg + 1e-8)

        # Recommendation
        if risk_reduction_pct > 90:
            recommendation = "STRONGLY RECOMMENDED"
        elif risk_reduction_pct > 70:
            recommendation = "RECOMMENDED"
        elif risk_reduction_pct > 40:
            recommendation = "CONSIDER"
        elif risk_reduction_pct > 10:
            recommendation = "MARGINAL BENEFIT"
        else:
            recommendation = "NOT JUSTIFIED"

        return ManoeuvreResult(
            direction=direction,
            delta_v_ms=delta_v_ms,
            original_risk=original_risk,
            residual_risk=residual_risk,
            risk_reduction_pct=risk_reduction_pct,
            delta_v_fuel_kg=fuel_kg,
            miss_distance_change_km=delta_miss,
            new_miss_distance_km=new_miss,
            effectiveness_score=effectiveness,
            recommendation=recommendation,
        )

    def analyse_conjunction(
        self,
        features: np.ndarray,
        feature_names: list[str],
        event_id: str = "",
        dv_options: Optional[list[float]] = None,
        directions: Optional[list[str]] = None,
        original_risk: Optional[float] = None,
    ) -> ManoeuvreReport:
        """
        Run a full manoeuvre analysis for a conjunction event.
        Tests multiple ΔV magnitudes and directions, ranks by effectiveness.
        original_risk overrides the model prediction when given.
        """
        dv_options = dv_options or MANOEUVRE_DV_OPTIONS
        directions = directions or list(MANOEUVRE_DIRECTIONS)

        original_miss, time_to_tca, _ = self._encounter_state(features, feature_names)

        if original_risk is None:
            original_risk = self._predict_risk(features)

        report = ManoeuvreReport(
            event_id=event_id,
            original_risk=original_risk,
            original_miss_distance_km=original_miss,
            time_to_tca_hours=time_to_tca,
        )

        # Simulate all combinations
        for dv in dv_options:
            for direction in directions:
                result = self.simulate_manoeuvre(features, feature_names, dv, direction, original_risk)
                if result is not None:
                    report.results.append(result)

        # Sort by effectiveness
        report.results.sort(key=lambda r: r.effectiveness_score, reverse=True)

        # Find best option
        viable = [r for r in report.results if r.risk_reduction_pct > 20]
        if viable:
            report.best_option = viable[0]
        elif report.results:
            report.best_option = report.results[0]

        # Check if any manoeuvre is justified
        if original_risk < -7.0:
            report.no_manoeuvre_justified = True

        return report

    def report_to_dataframe(self, report: ManoeuvreReport) -> pd.DataFrame:
        """Convert a ManoeuvreReport to a DataFrame for display."""
        rows = []
        for r in report.results:
            rows.append({
                "Direction": r.direction,
                "ΔV (m/s)": r.delta_v_ms,
                "Fuel (kg)": round(r.delta_v_fuel_kg, 3),
                "Original Risk": round(r.original_risk, 3),
                "Residual Risk": round(r.residual_risk, 3),
                "Risk Reduction %": round(r.risk_reduction_pct, 1),
                "New Miss Dist (km)": round(r.new_miss_distance_km, 1),
                "Effectiveness": round(r.effectiveness_score, 2),
                "Recommendation": r.recommendation,
            })

        df = pd.DataFrame(rows)
        return df
