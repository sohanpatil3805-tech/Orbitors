import datetime

import spacetrack_client
from fastapi import APIRouter
from uncertainty_model import UncertaintyModel

from app.models.schemas import ScenarioRequest
from app.services import live_service, ml_service
from app.services.common import clean
from ._errors import run

router = APIRouter(tags=["System"])


def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


@router.get("/health")
def health_check():
    """Which parts of the system are working right now."""
    live = live_service.status()
    model_ok = ml_service.model is not None
    um_ok = UncertaintyModel.exists()
    data = ml_service.dataset_status()
    components = {
        "live_screening": live["phase"].upper(),
        "cdm_risk_model": "ACTIVE" if model_ok else "MISSING",
        "uncertainty_model": "ACTIVE" if um_ok else "MISSING",
        "esa_dataset": "ACTIVE" if data["test"] else "MISSING",
        "space_track": "CONFIGURED" if spacetrack_client.is_configured() else "NOT_CONFIGURED (using CelesTrak)",
    }
    healthy = live["phase"] == "ready" and model_ok and um_ok and data["test"]
    return {"status": "HEALTHY" if healthy else "DEGRADED", "services": components,
            "live_error": live.get("error"), "dataset": data, "timestamp_utc": _now()}


@router.get("/status")
def live_status():
    """Live screening progress and summary: catalogue, watchlist status counts, space weather, test scenario."""
    return live_service.status()


@router.post("/refresh")
def refresh(rescreen: bool = False):
    """Fetch new orbit data now (and, with rescreen=true, screen again even if the data has not changed)."""
    live_service.request_refresh(rescreen)
    return {"requested": True, "rescreen": rescreen}


@router.get("/space-weather")
def space_weather():
    """Today's solar and geomagnetic indices used by the uncertainty model, and the last 120 observed days."""
    import pandas as pd
    from http_cache import cache_age_seconds
    from space_weather import load_space_weather, storm_level, weather_for
    # Downloads belong to the live pipeline; here only its disk cache is read, so a slow or
    # unreachable CelesTrak never blocks this request.
    table = load_space_weather() if cache_age_seconds("SW-Last5Years.csv") is not None else pd.DataFrame()
    current = live_service.state.weather if live_service.state is not None else weather_for(table=table)
    history = []
    if not table.empty:
        recent = table[table["AP_AVG"].notna()].tail(120)
        history = [{"date": d.date().isoformat(), "f10_7": r["F10.7_OBS"], "ap": r["AP_AVG"]}
                   for d, r in recent.iterrows()]
    return clean({**current, "storm_level": storm_level(current.get("kp_max")), "history": history})


@router.get("/scenario")
def get_scenario():
    """The simulated threat currently injected (null when test mode is off)."""
    return {"enabled": live_service.threat is not None, "threat": live_service.threat}


@router.post("/scenario")
def set_scenario(req: ScenarioRequest):
    """
    Inject a simulated debris piece or satellite on a collision course with a
    watchlist satellite, so the alert → 3D → manoeuvre chain can be checked
    against a known answer. Real data is not changed. enabled=false clears it.
    """
    spec = None if not req.enabled else req.model_dump(exclude={"enabled"})
    run(live_service.set_scenario, spec)
    return {"enabled": spec is not None, "threat": spec, "message": "Re-screening with the new scenario"}
