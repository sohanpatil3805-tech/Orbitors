from typing import List, Optional

from fastapi import APIRouter, Query

from app.services import live_service
from ._errors import run

router = APIRouter(prefix="/conjunctions", tags=["Conjunctions & Screening"])


@router.get("/satellites")
def get_watchlist_satellites():
    """Watchlist satellites from the live catalogue with their current status and worst upcoming conjunction."""
    return run(live_service.satellites)


@router.get("/screen")
def screen_conjunctions(
    norad_id: Optional[int] = Query(None, description="Only this watchlist satellite (default: all)"),
    level: Optional[List[str]] = Query(None, description="Risk levels to keep, e.g. CRITICAL, HIGH"),
    status: Optional[List[str]] = Query(None, description="Statuses to keep: DANGER, REVIEW, SAFE, MITIGATED"),
    limit: int = Query(500, ge=1, le=5000),
):
    """Every upcoming close approach (< 10 km) found by SGP4 screening, worst first, with collision probability."""
    conj = run(live_service.conjunctions, norad_id, level, status, limit)
    summary = run(live_service.status)
    return {"satellite_norad_id": norad_id, "screened_at_utc": summary.get("screened_at"),
            "screening_window_hours": summary.get("window_hours"),
            "total_screened_objects": summary.get("objects_tracked"),
            "catalogue_source": summary.get("catalogue_source"),
            "conjunctions_count": len(conj),
            "high_risk_count": sum(1 for c in conj if c["risk_level"] in ("CRITICAL", "HIGH")),
            "conjunctions": conj}


@router.get("/orbit/{norad_id}")
def get_orbit_coordinates(norad_id: int, points: int = Query(120, ge=2, le=2000)):
    """SGP4 positions over the next orbit (TEME km, latitude, longitude, altitude) for 3D rendering."""
    return run(live_service.orbit, norad_id, points)


@router.get("/detail/{key}")
def get_conjunction_detail(key: str):
    """Physics breakdown of one conjunction plus SHAP explanations of the ML-predicted orbit uncertainty."""
    return run(live_service.detail, key)
