"""
OrbitGuard AI — Dataset Export
Exports the dataset the model was trained on, with model predictions, to JSON.

Outputs (in exports/):
    trained_dataset.json   — every training row: original CDM fields, engineered
                             features, split (train/val), predicted risk, risk level
    test_predictions.json  — every test row with actual vs predicted risk
    model_summary.json     — metrics, feature importance, risk-level breakdowns

Usage:
    python export_dataset.py              # full export
    python export_dataset.py --sample 5000  # first N rows of each set only
"""

import argparse
import json
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from config import EXPORT_DIR, TARGET_COLUMN, GROUP_COLUMN, RISK_LEVELS
from collision_model import CollisionRiskModel, split_by_event


def risk_level(values: np.ndarray) -> np.ndarray:
    """Vectorised log10 Pc → risk category (same thresholds as config.RISK_LEVELS)."""
    levels = np.full(len(values), "NEGLIGIBLE", dtype=object)
    # RISK_LEVELS is ordered most → least severe; assign least severe first so higher ones win
    for name, threshold in reversed(list(RISK_LEVELS.items())):
        levels[values >= threshold] = name
    return levels


def build_frame(model: CollisionRiskModel, raw: pd.DataFrame) -> pd.DataFrame:
    """Original columns + engineered features + predictions for a raw CDM frame."""
    prep = model.preprocessor
    X = prep.transform(raw)
    pred = model.predict(X)

    features = pd.DataFrame(X, columns=prep.final_feature_columns, index=raw.index)
    # c_object_type is label-encoded in the features; keep the readable original instead
    features = features.drop(columns=[c for c in features.columns if c in raw.columns])

    extra = {"predicted_risk": pred, "predicted_risk_level": risk_level(pred)}
    if TARGET_COLUMN in raw.columns:
        extra["risk_level"] = risk_level(raw[TARGET_COLUMN].values)
        extra["prediction_error"] = pred - raw[TARGET_COLUMN].values

    return pd.concat([raw, features, pd.DataFrame(extra, index=raw.index)], axis=1)


def write_json(df: pd.DataFrame, name: str) -> None:
    path = EXPORT_DIR / name
    df.to_json(path, orient="records", indent=None, double_precision=6)
    print(f"[Export] {path} — {len(df):,} rows, {path.stat().st_size / 1e6:.1f} MB")


def level_breakdown(df: pd.DataFrame) -> dict:
    """Count of actual vs predicted risk levels."""
    order = list(RISK_LEVELS)
    return {
        "actual": df["risk_level"].value_counts().reindex(order, fill_value=0).to_dict(),
        "predicted": df["predicted_risk_level"].value_counts().reindex(order, fill_value=0).to_dict(),
    }


def main():
    parser = argparse.ArgumentParser(description="Export the trained dataset to JSON")
    parser.add_argument("--sample", type=int, default=None, help="Only export the first N rows of each set")
    args = parser.parse_args()

    EXPORT_DIR.mkdir(exist_ok=True)

    model = CollisionRiskModel(use_gpu=False)
    model.load()

    train_raw, test_raw = model.preprocessor.load_data()

    # Reproduce the event-grouped split used during training
    split = np.full(len(train_raw), "train", dtype=object)
    _, val_idx = split_by_event(train_raw[GROUP_COLUMN].values)
    split[val_idx] = "val"

    if args.sample:
        train_raw = train_raw.head(args.sample)
        test_raw = test_raw.head(args.sample)
        split = split[: args.sample]

    print("[Export] Building training set...")
    train_out = build_frame(model, train_raw)
    train_out = pd.concat([pd.DataFrame({"split": split}, index=train_out.index), train_out], axis=1)
    write_json(train_out, "trained_dataset.json")

    print("[Export] Building test set...")
    test_out = build_frame(model, test_raw)
    write_json(test_out, "test_predictions.json")

    fi = model.get_feature_importance()
    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "model": "XGBoost regressor — target: risk (log10 collision probability)",
        "sampled": bool(args.sample),
        "rows": {
            "train": int((train_out["split"] == "train").sum()),
            "val": int((train_out["split"] == "val").sum()),
            "test": len(test_out),
        },
        "n_features": len(model.feature_names),
        "feature_names": model.feature_names,
        "training_metrics": model.training_metrics,
        "feature_importance_gain": fi.to_dict(orient="records"),
        "risk_levels": {
            "thresholds_log10_pc": {k: (v if np.isfinite(v) else None) for k, v in RISK_LEVELS.items()},
            "train": level_breakdown(train_out),
            "test": level_breakdown(test_out),
        },
    }
    path = EXPORT_DIR / "model_summary.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    print(f"[Export] {path}")


if __name__ == "__main__":
    main()
