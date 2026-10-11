"""Request bodies (responses are plain JSON built by the services)."""

from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel, Field


class WhatIfRequest(BaseModel):
    """Recompute a conjunction's risk with the real Pc engine after scaling its inputs."""
    source: Literal["live", "esa"] = Field("live", description="'live' conjunction key or 'esa' test-set event")
    id: str = Field(..., description="Live conjunction key (e.g. 25544-990000-20261012T061500) or ESA event_id")
    miss_scale: float = Field(1.0, gt=0, le=100, description="Multiply the miss vector")
    sigma_scale: float = Field(1.0, gt=0, le=100, description="Multiply every position uncertainty (σ)")
    hbr_scale: float = Field(1.0, gt=0, le=100, description="Multiply the combined hard-body radius")


class CDMPredictRequest(BaseModel):
    """One conjunction data message as raw ESA dataset columns (any subset; the rest use training medians)."""
    event_id: str = Field("custom", description="Label echoed back in the response")
    cdm: Dict[str, Any] = Field(..., description="Column → value, e.g. {'miss_distance': 142.0, "
                                                 "'max_risk_estimate': -3.1, 'time_to_tca': 1.5, ...}")


class DecisionRequest(BaseModel):
    key: str = Field(..., description="Conjunction key")
    decision: Literal["ACCEPTED", "DECLINED"]
    option_index: Optional[int] = Field(None, ge=0, description="Index into the plan's options (required to accept)")
    note: str = Field("", max_length=500)


class ScenarioRequest(BaseModel):
    """A simulated object on a known collision course with a watchlist satellite (scenario.create_threat)."""
    enabled: bool = True
    primary_id: int = Field(25544, description="Watchlist satellite NORAD ID")
    hours_to_tca: float = Field(18.0, ge=3.0, le=60.0)
    miss_m: float = Field(25.0, ge=0.0, le=2000.0)
    crossing_deg: float = Field(70.0, ge=10.0, le=170.0)
    kind: Literal["debris", "satellite"] = "debris"


class ManeuverOptimizeRequest(BaseModel):
    """CDM-only manoeuvre estimate for an ESA test-set event."""
    event_id: int
    satellite_mass_kg: Optional[float] = Field(None, gt=0)
    isp_s: Optional[float] = Field(None, gt=0)
