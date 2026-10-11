from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
from app.models.schemas import CDMFeatureInput, PredictionResponse
from app.services.ml_service import ml_service
from app.services.data_service import DataService

router = APIRouter(prefix="/predict", tags=["ML Prediction & Explainability"])

@router.post("/", response_model=PredictionResponse)
def predict_collision_risk(cdm: CDMFeatureInput):
    """
    Evaluates incoming Conjunction Data Message (CDM) features.
    Outputs:
    1. Calibrated Collision Probability (PoC)
    2. Go / No-Go Decision against 1E-4 threshold
    3. SHAP Feature Attribution Explanations
    4. Operational Telemetry Readout for mission operators
    """
    return ml_service.predict(cdm)

@router.get("/esa-events")
def get_historical_esa_events():
    """Returns the list of real ESA Kelvins 2019 benchmark events for offline replay"""
    return DataService.get_esa_events()

@router.get("/esa-replay/{event_id}", response_model=PredictionResponse)
def replay_esa_event(event_id: str):
    """
    Replays an authentic ESA Kelvins competition event, showing the ML model's
    early forecast 2-3 days prior to TCA.
    """
    event = DataService.get_esa_event(event_id)
    if not event:
        raise HTTPException(status_code=404, detail=f"ESA Event {event_id} not found in catalog")

    cdm_input = CDMFeatureInput(
        event_id=event["event_id"],
        satellite_id=event["satellite_id"],
        secondary_object_id=event["secondary_object_id"],
        time_to_tca_hours=event["time_to_tca_hours"],
        miss_distance_m=event["miss_distance_m"],
        relative_velocity_km_s=event["relative_velocity_km_s"],
        radial_miss_distance_m=event["radial_miss_distance_m"],
        in_track_miss_distance_m=event["in_track_miss_distance_m"],
        cross_track_miss_distance_m=event["cross_track_miss_distance_m"],
        radial_position_covariance=event["radial_position_covariance"],
        cdm_count_for_event=event.get("cdm_count_for_event", 3),
        solar_flux_f10_7=event.get("solar_flux_f10_7", 150.0),
        ap_geomagnetic_index=event.get("ap_geomagnetic_index", 15.0)
    )

    return ml_service.predict(cdm_input)
