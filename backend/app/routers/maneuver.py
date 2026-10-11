from fastapi import APIRouter
from pydantic import BaseModel, Field
from app.models.schemas import ManeuverOptimizationResponse
from app.services.maneuver_service import maneuver_service

router = APIRouter(prefix="/maneuver", tags=["Avoidance Maneuver Optimizer"])

class ManeuverCalculationRequest(BaseModel):
    event_id: str = Field(..., description="Conjunction event ID")
    current_poc: float = Field(0.00028, description="Current estimated collision probability")
    miss_distance_m: float = Field(142.0, description="Current miss distance in meters")
    satellite_mass_kg: float = Field(500.0, description="Spacecraft dry mass in kg")

@router.post("/optimize", response_model=ManeuverOptimizationResponse)
def optimize_collision_avoidance_maneuver(request: ManeuverCalculationRequest):
    """
    Computes the Delta-V vs Residual Collision Risk trade-off curve (Slide 12 of Problem Statement).
    Finds the optimal minimal-burn sweet spot that suppresses risk below 1E-5.
    """
    return maneuver_service.calculate_optimal_maneuver(
        event_id=request.event_id,
        current_poc=request.current_poc,
        miss_distance_m=request.miss_distance_m,
        satellite_mass_kg=request.satellite_mass_kg
    )
