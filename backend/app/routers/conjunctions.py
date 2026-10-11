from fastapi import APIRouter, HTTPException, Query
from typing import List, Dict, Any
import datetime
from app.models.schemas import SatelliteInfo, ScreeningResponse, OrbitPathResponse, ConjunctionSummary
from app.services.data_service import DataService
from app.services.physics_service import PhysicsService

router = APIRouter(prefix="/conjunctions", tags=["Conjunctions & Screening"])

@router.get("/satellites", response_model=List[SatelliteInfo])
def get_catalog_satellites():
    """Returns list of tracked mission satellites (ISS, Tiangong, Hubble, Starlink, Sentinel)"""
    return DataService.get_satellites()

@router.get("/screen", response_model=ScreeningResponse)
def screen_conjunctions(
    norad_id: int = Query(25544, description="NORAD Catalog ID (e.g., 25544 for ISS)"),
    days: int = Query(3, description="Screening window in days ahead (1-7 days)")
):
    """
    Screens for close passes over the next N days using SGP4 propagation and conjunction catalog.
    Matches the 3-minute hackathon demo script (Slide 6 in PDF 1).
    """
    sat = DataService.get_satellite(norad_id)
    if not sat:
        raise HTTPException(status_code=404, detail=f"Satellite with NORAD ID {norad_id} not found")

    conjunctions_data = DataService.generate_screening_conjunctions(norad_id, days)
    conjunction_summaries = [ConjunctionSummary(**c) for c in conjunctions_data]
    high_risk_count = sum(1 for c in conjunction_summaries if c.risk_level == "CRITICAL")

    return ScreeningResponse(
        satellite_norad_id=sat["norad_id"],
        satellite_name=sat["name"],
        screening_window_days=days,
        screened_at_utc=datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        total_screened_objects=39842, # Realistic tracked catalog size
        conjunctions_count=len(conjunction_summaries),
        high_risk_count=high_risk_count,
        conjunctions=conjunction_summaries
    )

@router.get("/orbit/{norad_id}", response_model=OrbitPathResponse)
def get_orbit_coordinates(norad_id: int = 25544, points: int = 60):
    """
    Computes 3D Earth-Centered Inertial coordinates and lat/lon/alt
    for 3D globe rendering in the frontend.
    """
    sat = DataService.get_satellite(norad_id)
    if not sat:
        raise HTTPException(status_code=404, detail=f"Satellite with NORAD ID {norad_id} not found")

    coords = PhysicsService.get_orbit_path(norad_id, points)
    return OrbitPathResponse(
        norad_id=sat["norad_id"],
        name=sat["name"],
        period_min=sat["period_min"],
        coordinates=coords
    )

@router.get("/detail/{event_id}")
def get_conjunction_detail(event_id: str):
    """Returns complete telemetry details for a specific conjunction event"""
    esa_event = DataService.get_esa_event(event_id)
    if esa_event:
        return esa_event
    
    # Check simulated event
    conjs = DataService.generate_screening_conjunctions(25544, 3)
    for c in conjs:
        if c["event_id"] == event_id:
            return c

    raise HTTPException(status_code=404, detail=f"Event {event_id} not found")
