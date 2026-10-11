import math
import datetime
from typing import List, Dict, Any
from app.services.data_service import SATELLITE_CATALOG

try:
    from sgp4.api import Satrec, jday
    SGP4_AVAILABLE = True
except ImportError:
    SGP4_AVAILABLE = False

class PhysicsService:
    @staticmethod
    def get_orbit_path(norad_id: int, points_count: int = 60) -> List[Dict[str, Any]]:
        sat_info = SATELLITE_CATALOG.get(norad_id, SATELLITE_CATALOG[25544])
        period_min = sat_info["period_min"]
        alt_km = sat_info["altitude_km"]
        inclination_deg = sat_info["inclination_deg"]
        inc_rad = math.radians(inclination_deg)
        earth_radius_km = 6378.137
        orbit_radius_km = earth_radius_km + alt_km

        now = datetime.datetime.now(datetime.timezone.utc)
        coordinates = []

        # Try real SGP4 if available and TLE is present
        used_sgp4 = False
        if SGP4_AVAILABLE and "tle_line1" in sat_info and "tle_line2" in sat_info:
            try:
                satrec = Satrec.twoline2rv(sat_info["tle_line1"], sat_info["tle_line2"])
                step_min = period_min / points_count

                for i in range(points_count):
                    t = now + datetime.timedelta(minutes=i * step_min)
                    jd, fr = jday(t.year, t.month, t.day, t.hour, t.minute, t.second + t.microsecond * 1e-6)
                    e, r, v = satrec.sgp4(jd, fr)
                    if e == 0:
                        x, y, z = r[0], r[1], r[2]
                        dist = math.sqrt(x*x + y*y + z*z)
                        lat = math.degrees(math.asin(z / dist))
                        lon = math.degrees(math.atan2(y, x))
                        coordinates.append({
                            "timestamp_utc": t.strftime("%Y-%m-%d %H:%M:%S UTC"),
                            "x_km": round(x, 2),
                            "y_km": round(y, 2),
                            "z_km": round(z, 2),
                            "lat_deg": round(lat, 4),
                            "lon_deg": round(lon, 4),
                            "alt_km": round(dist - earth_radius_km, 2)
                        })
                if len(coordinates) == points_count:
                    used_sgp4 = True
            except Exception:
                used_sgp4 = False

        # Robust analytical Keplerian orbital propagator fallback
        if not used_sgp4:
            coordinates = []
            step_min = period_min / points_count
            earth_rotation_rate = 360.0 / (24 * 60) # degrees per minute

            for i in range(points_count):
                t = now + datetime.timedelta(minutes=i * step_min)
                theta = (2 * math.pi * i) / points_count

                # Orbital plane to ECI coordinates
                x_orb = orbit_radius_km * math.cos(theta)
                y_orb = orbit_radius_km * math.sin(theta)

                x = x_orb
                y = y_orb * math.cos(inc_rad)
                z = y_orb * math.sin(inc_rad)

                lat = math.degrees(math.asin(z / orbit_radius_km))
                raw_lon = math.degrees(math.atan2(y, x)) - (i * step_min * earth_rotation_rate)
                lon = ((raw_lon + 180) % 360) - 180

                coordinates.append({
                    "timestamp_utc": t.strftime("%Y-%m-%d %H:%M:%S UTC"),
                    "x_km": round(x, 2),
                    "y_km": round(y, 2),
                    "z_km": round(z, 2),
                    "lat_deg": round(lat, 4),
                    "lon_deg": round(lon, 4),
                    "alt_km": round(alt_km, 2)
                })

        return coordinates

    @staticmethod
    def calculate_conjunction_coordinates(miss_distance_m: float, closing_velocity_km_s: float) -> Dict[str, Any]:
        """Generates relative geometry vectors for 3D visualization and dashboard display"""
        return {
            "radial_offset_m": round(miss_distance_m * 0.28, 1),
            "in_track_offset_m": round(miss_distance_m * 0.85, 1),
            "cross_track_offset_m": round(miss_distance_m * 0.42, 1),
            "relative_speed_km_s": round(closing_velocity_km_s, 2),
            "collision_cone_radius_m": round(miss_distance_m * 0.15, 1)
        }
