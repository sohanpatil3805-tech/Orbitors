import decisions
from fastapi import APIRouter

from app.models.schemas import DecisionRequest, ManeuverOptimizeRequest, SpacecraftRequest
from app.services import live_service, ml_service
from app.services.common import clean
from ._errors import run

router = APIRouter(prefix="/maneuver", tags=["Avoidance Maneuver Planner"])


@router.get("/spacecraft")
def get_spacecraft_parameters():
    return dict(live_service.spacecraft)


@router.put("/spacecraft")
def set_spacecraft_parameters(req: SpacecraftRequest):
    """Update the mass, Isp and thrust used for every live burn cost estimate."""
    return live_service.set_spacecraft(req.model_dump())


@router.get("/plan/{key}")
def get_maneuver_plan(key: str):
    """
    Avoidance plan for a live conjunction from the J2 manoeuvre planner: smallest
    verified burn, alternatives (including asking the other operator to move),
    new conflicts it would cause, and the ΔV vs risk trade-off curve.
    Plans run in the background — poll until status is 'ready'.
    """
    return run(live_service.plan_view, key)


@router.post("/decision")
def record_decision(req: DecisionRequest):
    """Accept or decline a suggested burn (appended to logs/manoeuvre_decisions.jsonl)."""
    return run(live_service.decide, req.key, req.decision, req.option_index, req.note)


@router.get("/decisions")
def get_decision_history():
    """Operator decision audit trail, newest first."""
    return clean(list(reversed(decisions.history())))


@router.post("/optimize")
def optimize_esa_event(req: ManeuverOptimizeRequest):
    """CDM-only ΔV trade-off for an ESA test-set event (no orbit states, so an analytic estimate)."""
    return run(ml_service.simulate_manoeuvre, req.event_id, req.satellite_mass_kg, req.isp_s)
