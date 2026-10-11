"""
Model evaluation results for the API, read from the files the training and
validation scripts write:

  models/orbitguard_model_eval.json   collision_model.evaluate_splits()  (train / validation / test)
  models/orbitguard_model_meta.json   collision_model.train_full_pipeline()
  models/uncertainty/meta.json        uncertainty_model.py
  exports/model_summary.json          export_dataset.py (risk-level breakdown, feature importance)
  exports/validation_report.json      validate.py
"""

import json
from pathlib import Path

from config import EXPORT_DIR, MODEL_DIR, RISK_THRESHOLD
from uncertainty_model import UNCERTAINTY_DIR

from .common import clean

FILES = {
    "evaluation": MODEL_DIR / "orbitguard_model_eval.json",
    "training": MODEL_DIR / "orbitguard_model_meta.json",
    "uncertainty": UNCERTAINTY_DIR / "meta.json",
    "summary": EXPORT_DIR / "model_summary.json",
    "validation": EXPORT_DIR / "validation_report.json",
}


def _read(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _f2(m: dict):
    if "alert_f2" in m:
        return m["alert_f2"]
    p, r = m.get("alert_precision"), m.get("alert_recall")
    return 5 * p * r / (4 * p + r) if p and r else None


def validation_report() -> dict:
    rep = _read(FILES["validation"])
    if rep is None:
        raise FileNotFoundError("No validation report yet — run `python validate.py`")
    return rep


def metrics() -> dict:
    ev = _read(FILES["evaluation"]) or {}
    training = (_read(FILES["training"]) or {}).get("training_metrics", {})
    um = (_read(FILES["uncertainty"]) or {}).get("metrics", {})
    summary = _read(FILES["summary"]) or {}
    rep = _read(FILES["validation"])

    test = ev.get("test") or {k[5:]: v for k, v in training.items() if k.startswith("test_")}
    splits = [{"split": name, "rows": m.get("rows"), "r2": m.get("r2"), "rmse": m.get("rmse"), "mae": m.get("mae"),
               "alert_precision": m.get("alert_precision"), "alert_recall": m.get("alert_recall"),
               "alert_f1": m.get("alert_f1"), "alert_f2": _f2(m), "alert_accuracy": m.get("alert_accuracy"),
               "alerts_true": m.get("alert_positives_true"), "alerts_predicted": m.get("alert_positives_pred")}
              for name, m in ev.items()]

    uncertainty = [{"quantity": label, "ml_error_factor": 10 ** um[f"{k}_mae"],
                    "baseline_error_factor": 10 ** um[f"{k}_baseline_mae"]}
                   for k, label in (("log_sigma_r", "Radial σ"), ("log_sigma_t", "Along-track σ"),
                                    ("log_sigma_n", "Cross-track σ")) if f"{k}_mae" in um]

    importance = summary.get("feature_importance_gain", [])[:15]
    total = sum(f["importance"] for f in importance) or 1.0
    validation = None
    if rep is not None:
        checks = rep.get("checks", [])
        validation = {"generated_at": rep.get("generated_at"),
                      "passed": sum(1 for c in checks if c["passed"] is True),
                      "failed": sum(1 for c in checks if c["passed"] is False),
                      "skipped": sum(1 for c in checks if c["passed"] is None),
                      "checks": [{k: c.get(k) for k in ("section", "name", "what", "passed", "result", "criterion")}
                                 for c in checks]}

    return clean({
        "model_name": "OrbitGuard AI — full-CDM XGBoost risk model",
        "algorithm": "Gradient-boosted trees (XGBoost) on 118 CDM features + TreeSHAP explanations",
        "test_dataset": f"ESA Collision Avoidance Challenge test set ({test.get('rows', 0):,} CDMs)",
        "alert_threshold_log10_pc": RISK_THRESHOLD,
        "kpis": {"test_r2": test.get("r2"), "test_mae": test.get("mae"), "test_rmse": test.get("rmse"),
                 "alert_precision": test.get("alert_precision"), "alert_recall": test.get("alert_recall"),
                 "alert_f2": _f2(test), "alert_accuracy": test.get("alert_accuracy")},
        "splits": splits,
        "training": {"device": training.get("device"), "trees": training.get("n_estimators_used"),
                     "training_time_s": training.get("training_time_seconds"),
                     "features": summary.get("n_features")},
        "uncertainty_model": {"rows_trained": um.get("n_train_rows"), "rows_tested": um.get("n_test_rows"),
                              "errors": uncertainty},
        "feature_importance": [{"feature": f["feature"], "importance": f["importance"],
                                "share": f["importance"] / total} for f in importance],
        "risk_levels": summary.get("risk_levels"),
        "validation": validation,
        "sources": {name: path.exists() for name, path in FILES.items()},
        "conclusion": ("Scores are read from the saved evaluation files. The CDM model reproduces each CDM's "
                       "own risk value; the physics engine reproduces ESA's risk from CDM geometry and "
                       "covariance (validation A1)."),
    })
