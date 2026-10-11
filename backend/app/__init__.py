"""
OrbitGuard AI — FastAPI backend.

The services wrap the project's real engine at the repository root
(live_pipeline, risk_engine, screening, manoeuvre_planner, collision_model,
uncertainty_model, ...), so the root is put on the import path here. It is
appended, so this `app` package always wins over any root-level module.
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))
