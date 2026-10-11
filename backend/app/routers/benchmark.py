from fastapi import APIRouter

from app.services import benchmark_service
from ._errors import run

router = APIRouter(prefix="/benchmark", tags=["Benchmark & Model Evaluation"])


@router.get("/metrics")
def get_benchmark_evaluation_metrics():
    """Saved evaluation of the trained models: train / validation / test scores, uncertainty model, validation checks."""
    return run(benchmark_service.metrics)


@router.get("/validation")
def get_validation_report():
    """Full validation report written by validate.py (physics, ML, screening and manoeuvre checks)."""
    return run(benchmark_service.validation_report)
