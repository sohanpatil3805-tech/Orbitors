from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import datetime

from app.routers import (
    conjunctions_router,
    prediction_router,
    maneuver_router,
    benchmark_router
)

app = FastAPI(
    title="OrbitGuard AI — API",
    description="""
    ## Space Debris Collision-Risk Assessment & Fuel-Efficient Avoidance Platform
    
    Built for **Hackathon Challenge 1C: Space Debris Risk Prediction with AI**.
    
    ### Key Features:
    * **Orbital Conjunction Screening**: SGP4 propagation over 3-7 day forecast windows.
    * **ML Risk Calibration**: Calibrates collision probability (PoC) against noisy orbital uncertainty bubbles.
    * **Explainable AI (XAI)**: SHAP feature attribution explaining driving parameters behind alerts.
    * **Maneuver Optimization**: Fuel-minimal Delta-V trade-off curve calculation to safely bypass collision corridor.
    * **ESA Kelvins Replay Mode**: Authentic offline benchmark replay of real historical ESA close approaches.
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Enable CORS for frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In development, allow Vite frontend on any port/IP
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API Routers
app.include_router(conjunctions_router, prefix="/api")
app.include_router(prediction_router, prefix="/api")
app.include_router(maneuver_router, prefix="/api")
app.include_router(benchmark_router, prefix="/api")

@app.get("/", tags=["System"])
def root():
    return {
        "system": "OrbitGuard AI Mission Control API",
        "status": "OPERATIONAL",
        "documentation": "/docs",
        "timestamp_utc": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    }

@app.get("/api/health", tags=["System"])
def health_check():
    return {
        "status": "HEALTHY",
        "services": {
            "physics_sgp4": "ACTIVE",
            "ml_inference": "ACTIVE",
            "maneuver_optimizer": "ACTIVE",
            "catalog_database": "ACTIVE"
        },
        "timestamp_utc": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    }
