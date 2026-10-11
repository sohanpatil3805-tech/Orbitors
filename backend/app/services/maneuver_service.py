import math
from typing import List, Dict, Any
from app.models.schemas import ManeuverTradeoffPoint, ManeuverOptimizationResponse

class ManeuverService:
    @staticmethod
    def calculate_optimal_maneuver(
        event_id: str,
        current_poc: float = 0.0003,
        miss_distance_m: float = 142.0,
        satellite_mass_kg: float = 420000.0, # ISS ~420,000 kg, or smallsat ~250 kg
        thruster_isp_s: float = 300.0        # Specific impulse of hydrazine/electric thruster
    ) -> ManeuverOptimizationResponse:
        """
        Calculates the Delta-V vs Residual Collision Risk trade-off curve (Slide 12 of Problem Statement).
        Determines the optimal sweet-spot burn where PoC drops safely below 1E-5 with minimum fuel.
        """
        tradeoff_points: List[ManeuverTradeoffPoint] = []
        
        # Test candidate Delta-V burns from 0.0 to 3.0 m/s in steps
        delta_v_candidates = [0.0, 0.1, 0.25, 0.40, 0.52, 0.75, 1.0, 1.5, 2.0, 3.0]
        
        optimal_dv = 0.52
        optimal_point = None

        for dv in delta_v_candidates:
            # Orbital dynamics approximation:
            # An along-track burn of Delta-V (m/s) expands radial/cross-track separation by roughly 800-1200 meters per m/s at TCA (after 1-2 orbits)
            separation_gain_m = dv * 950.0
            new_miss_distance_m = miss_distance_m + separation_gain_m
            
            # Risk decay is exponential with expanded miss distance: PoC ~ exp(-dist^2 / (2 * sigma^2))
            if dv == 0.0:
                residual_poc = current_poc
            else:
                decay_factor = math.exp(- (separation_gain_m / 150.0))
                residual_poc = max(1e-7, current_poc * decay_factor)

            # Tsiolkovsky rocket equation: fuel consumed = M * (1 - exp(-dv / (g0 * Isp)))
            g0 = 9.80665
            fuel_burned_fraction = 1.0 - math.exp(-dv / (g0 * thruster_isp_s))
            # Assume representative satellite mass for demonstration fuel calculation (~500 kg satellite)
            effective_mass_kg = 500.0
            fuel_kg = round(effective_mass_kg * fuel_burned_fraction, 3)

            is_safe = residual_poc < 0.00001 # 1E-5 (10x safer than 1E-4 threshold)
            is_optimal = False

            point = ManeuverTradeoffPoint(
                delta_v_ms=round(dv, 2),
                residual_poc=float(f"{residual_poc:.6e}"),
                miss_distance_m=round(new_miss_distance_m, 1),
                fuel_penalty_kg=fuel_kg,
                is_safe=is_safe,
                is_optimal_sweet_spot=False
            )
            tradeoff_points.append(point)

        # Identify sweet spot: the lowest delta-v that achieves safety (is_safe=True)
        safe_candidates = [p for p in tradeoff_points if p.is_safe]
        if safe_candidates:
            sweet_spot = safe_candidates[0]
            sweet_spot.is_optimal_sweet_spot = True
            optimal_dv = sweet_spot.delta_v_ms
            optimal_point = sweet_spot
        else:
            tradeoff_points[-1].is_optimal_sweet_spot = True
            optimal_dv = tradeoff_points[-1].delta_v_ms
            optimal_point = tradeoff_points[-1]

        alert_reduction = round((1.0 - (optimal_point.residual_poc / max(1e-9, current_poc))) * 100.0, 1)

        return ManeuverOptimizationResponse(
            event_id=event_id,
            recommended_delta_v_ms=optimal_dv,
            recommended_burn_direction="+Along-Track (Prograde) Velocity Vector",
            expected_residual_poc=optimal_point.residual_poc,
            expected_miss_distance_m=optimal_point.miss_distance_m,
            fuel_consumed_kg=optimal_point.fuel_penalty_kg,
            alert_reduction_percent=alert_reduction,
            trade_off_curve=tradeoff_points
        )

maneuver_service = ManeuverService()
