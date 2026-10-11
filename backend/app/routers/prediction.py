from fastapi import APIRouter

from app.models.schemas import CDMPredictRequest, WhatIfRequest
from app.services import live_service, ml_service
from ._errors import run

router = APIRouter(prefix="/predict", tags=["ML Prediction & Explainability"])


@router.post("/")
def predict_collision_risk(req: CDMPredictRequest):
    """
    Risk of one conjunction data message from the trained XGBoost CDM model, with
    TreeSHAP feature attributions and (when geometry and covariance are given)
    the physics engine's own Pc.
    """
    return run(ml_service.predict_cdm, req.cdm, req.event_id)


@router.get("/esa-events")
def get_esa_events():
    """Real events from the ESA test set, chosen from the data to show different situations."""
    return run(ml_service.esa_events)


@router.get("/esa-replay/{event_id}")
def replay_esa_event(event_id: int):
    """Every CDM of an ESA event (ESA risk, model risk, physics risk) and SHAP for the CDM 2 days before TCA."""
    return run(ml_service.replay, event_id)


@router.post("/what-if")
def what_if(req: WhatIfRequest):
    """Recompute a live conjunction's or ESA CDM's Pc with the validated engine after scaling its inputs."""
    if req.source == "live":
        return run(live_service.what_if, req.id, req.miss_scale, req.sigma_scale, req.hbr_scale)
    return run(lambda: ml_service.what_if(int(req.id), req.miss_scale, req.sigma_scale, req.hbr_scale))
