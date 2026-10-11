import datetime
import os
import sys
from contextlib import asynccontextmanager

# Pipeline progress messages contain characters a Windows cp1252 console cannot encode
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import (
    benchmark_router,
    conjunctions_router,
    maneuver_router,
    prediction_router,
    system_router,
)
from app.services import live_service


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Live screening runs in background threads; ORBITGUARD_LIVE=0 turns it off (e.g. for offline tests)
    if os.environ.get("ORBITGUARD_LIVE", "1") != "0":
        live_service.start()
    yield


app = FastAPI(
    title="OrbitGuard AI — API",
    description="""
    ## Collision-risk assessment and avoidance planning for important satellites

    Serves the same engine as the Streamlit dashboard (`dashboard.py`):

    * **Live screening** — SGP4 screening of the watchlist against the CelesTrak / Space-Track catalogue for the next 72 h,
      refreshed automatically when new orbit data arrives (`/api/status`, `/api/conjunctions/*`).
    * **Collision probability** — 2D Pc with covariance from the ML uncertainty model (6 XGBoost regressors trained on ESA CDMs)
      plus assumed TLE error; SHAP explains the predicted uncertainty (`/api/conjunctions/detail/{key}`).
    * **Manoeuvre planner** — smallest verified burn, screened against the catalogue for new conflicts, with operator
      accept / decline (`/api/maneuver/*`).
    * **CDM risk model** — the trained full-CDM XGBoost model with TreeSHAP, replaying real ESA test-set events
      (`/api/predict/*`).
    * **Evaluation** — saved train / validation / test scores and the validation report (`/api/benchmark/*`).
    * **Test scenario** — inject a simulated threat with a known answer (`/api/scenario`).
    """,
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# The Vite dev server proxies /api, so CORS only matters when the frontend is served elsewhere
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(system_router, prefix="/api")
app.include_router(conjunctions_router, prefix="/api")
app.include_router(prediction_router, prefix="/api")
app.include_router(maneuver_router, prefix="/api")
app.include_router(benchmark_router, prefix="/api")


@app.get("/", tags=["System"])
def root():
    return {
        "system": "OrbitGuard AI Mission Control API",
        "status": live_service.phase.upper(),
        "documentation": "/docs",
        "timestamp_utc": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
    }
