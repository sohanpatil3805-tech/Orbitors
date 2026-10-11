from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class SatelliteInfo(BaseModel):
    norad_id: int
    name: str
    international_designator: str
    altitude_km: float
    inclination_deg: float
    period_min: float
    status: str

class OrbitPoint(BaseModel):
    timestamp_utc: str
    x_km: float
    y_km: float
    z_km: float
    lat_deg: float
    lon_deg: float
    alt_km: float

class OrbitPathResponse(BaseModel):
    norad_id: int
    name: str
    period_min: float
    coordinates: List[OrbitPoint]

class CDMFeatureInput(BaseModel):
    event_id: str = Field(..., description="Unique conjunction event identifier")
    satellite_id: int = Field(25544, description="Primary NORAD ID (e.g. 25544 for ISS)")
    secondary_object_id: int = Field(39451, description="Secondary debris NORAD ID")
    time_to_tca_hours: float = Field(..., description="Hours remaining until Time of Closest Approach")
    miss_distance_m: float = Field(..., description="Estimated total miss distance in meters")
    relative_velocity_km_s: float = Field(..., description="Relative closing velocity in km/s")
    radial_miss_distance_m: float = Field(..., description="Radial miss distance component in meters")
    in_track_miss_distance_m: float = Field(..., description="In-track miss distance component in meters")
    cross_track_miss_distance_m: float = Field(..., description="Cross-track miss distance component in meters")
    radial_position_covariance: float = Field(..., description="Estimated radial position uncertainty")
    cdm_count_for_event: int = Field(1, description="Number of CDMs received for this encounter")
    solar_flux_f10_7: float = Field(150.0, description="Solar radio flux F10.7 index (solar drag parameter)")
    ap_geomagnetic_index: float = Field(15.0, description="Ap geomagnetic storm index")

class SHAPFeature(BaseModel):
    feature: str
    feature_label: str
    impact: float = Field(..., description="SHAP attribution value (positive increases risk, negative decreases)")
    direction: str = Field(..., description="'INCREASES_RISK' or 'REDUCES_RISK'")
    percentage_contribution: float
    explanation: str

class PredictionResponse(BaseModel):
    event_id: str
    raw_poc: float
    calibrated_poc: float
    risk_level: str = Field(..., description="'CRITICAL', 'WARNING', or 'NOMINAL'")
    go_no_go_decision: str = Field(..., description="'MANEUVER_RECOMMENDED' or 'HOLD'")
    confidence: float
    threshold_poc: float = 0.0001
    shap_explanations: List[SHAPFeature]
    recommended_burn_ms: float
    telemetry_readout: Dict[str, str]

class ConjunctionSummary(BaseModel):
    event_id: str
    primary_norad_id: int
    primary_name: str
    secondary_norad_id: int
    secondary_name: str
    tca_utc: str
    time_to_tca_hours: float
    miss_distance_m: float
    relative_velocity_km_s: float
    raw_poc: float
    calibrated_poc: float
    risk_level: str
    go_no_go_decision: str
    recommended_delta_v_ms: float = 0.0

class ScreeningResponse(BaseModel):
    satellite_norad_id: int
    satellite_name: str
    screening_window_days: int
    screened_at_utc: str
    total_screened_objects: int
    conjunctions_count: int
    high_risk_count: int
    conjunctions: List[ConjunctionSummary]

class ManeuverTradeoffPoint(BaseModel):
    delta_v_ms: float
    residual_poc: float
    miss_distance_m: float
    fuel_penalty_kg: float
    is_safe: bool
    is_optimal_sweet_spot: bool

class ManeuverOptimizationResponse(BaseModel):
    event_id: str
    recommended_delta_v_ms: float
    recommended_burn_direction: str
    expected_residual_poc: float
    expected_miss_distance_m: float
    fuel_consumed_kg: float
    alert_reduction_percent: float
    trade_off_curve: List[ManeuverTradeoffPoint]

class BenchmarkMetrics(BaseModel):
    model_name: str
    algorithm: str
    test_dataset: str
    f2_score: float
    baseline_f2_score: float
    brier_score: float
    baseline_brier_score: float
    recall_high_risk: float
    precision_high_risk: float
    roc_auc: float
    events_evaluated: int
    conclusion: str
