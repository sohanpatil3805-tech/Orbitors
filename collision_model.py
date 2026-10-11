"""
OrbitGuard AI — GPU-Accelerated Collision Risk Model
XGBoost model with CUDA acceleration for RTX 4060, plus SHAP explainability.
"""

import os
import time
import json
from pathlib import Path
from typing import Optional, Tuple

import numpy as np
import pandas as pd
import joblib
import xgboost as xgb
from sklearn.metrics import (
    mean_squared_error,
    mean_absolute_error,
    r2_score,
    precision_score,
    recall_score,
    f1_score,
    fbeta_score,
)

from config import (
    XGBOOST_PARAMS,
    XGBOOST_CPU_PARAMS,
    MODEL_DIR,
    TARGET_COLUMN,
    GROUP_COLUMN,
    RISK_THRESHOLD,
)
from data_preprocessing import DataPreprocessor


class CollisionRiskModel:
    """
    GPU-accelerated XGBoost model for satellite collision risk prediction.
    Uses CUDA on RTX 4060 for training and inference.
    """

    def __init__(self, use_gpu: bool = True):
        self.use_gpu = use_gpu
        self.model: Optional[xgb.XGBRegressor] = None
        self.feature_names: list[str] = []
        self.preprocessor = DataPreprocessor()
        self.training_metrics: dict = {}
        self._check_gpu()

    def _check_gpu(self):
        """Check GPU availability and adjust parameters."""
        if self.use_gpu:
            try:
                # Test if CUDA is available via XGBoost
                test_params = {"device": "cuda", "tree_method": "hist", "n_estimators": 1}
                test_model = xgb.XGBRegressor(**test_params)
                test_X = np.random.randn(10, 5).astype(np.float32)
                test_y = np.random.randn(10).astype(np.float32)
                test_model.fit(test_X, test_y)
                print("[Model] ✅ CUDA GPU detected — using GPU acceleration")
                self.params = XGBOOST_PARAMS.copy()
            except Exception as e:
                print(f"[Model] ⚠️  GPU not available ({e}), falling back to CPU")
                self.use_gpu = False
                self.params = XGBOOST_CPU_PARAMS.copy()
        else:
            self.params = XGBOOST_CPU_PARAMS.copy()
            print("[Model] Using CPU mode")

    def train(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: np.ndarray,
        y_val: np.ndarray,
        feature_names: list[str],
    ) -> dict:
        """
        Train the collision risk model.

        Parameters
        ----------
        X_train, y_train : Training data and targets
        X_val, y_val : Validation data and targets
        feature_names : Names of features

        Returns
        -------
        dict : Training metrics
        """
        self.feature_names = feature_names

        print(f"\n{'='*60}")
        print(f"  Training OrbitGuard AI Collision Risk Model")
        print(f"  Device: {'CUDA (RTX 4060)' if self.use_gpu else 'CPU'}")
        print(f"  Training samples: {X_train.shape[0]:,}")
        print(f"  Validation samples: {X_val.shape[0]:,}")
        print(f"  Features: {X_train.shape[1]}")
        print(f"{'='*60}\n")

        # early_stopping_rounds / eval_metric are constructor arguments in XGBoost >= 2;
        # early stopping monitors the last eval_set entry (validation).
        self.model = xgb.XGBRegressor(**self.params)

        start_time = time.time()

        self.model.fit(
            X_train,
            y_train,
            eval_set=[(X_train, y_train), (X_val, y_val)],
            verbose=50,
        )

        elapsed = time.time() - start_time

        # Inputs are numpy arrays on the host, so predict on CPU
        self.model.set_params(device="cpu")

        # Compute metrics
        y_pred_train = self.model.predict(X_train)
        y_pred_val = self.model.predict(X_val)

        self.training_metrics = {
            "train_rmse": float(np.sqrt(mean_squared_error(y_train, y_pred_train))),
            "val_rmse": float(np.sqrt(mean_squared_error(y_val, y_pred_val))),
            "train_mae": float(mean_absolute_error(y_train, y_pred_train)),
            "val_mae": float(mean_absolute_error(y_val, y_pred_val)),
            "train_r2": float(r2_score(y_train, y_pred_train)),
            "val_r2": float(r2_score(y_val, y_pred_val)),
            "training_time_seconds": elapsed,
            "n_estimators_used": int(self.model.best_iteration) + 1
                if getattr(self.model, "best_iteration", None) is not None
                else int(self.params.get("n_estimators", 0)),
            "device": "cuda" if self.use_gpu else "cpu",
        }

        print(f"\n{'='*60}")
        print(f"  Training Complete in {elapsed:.1f}s")
        print(f"  Train RMSE: {self.training_metrics['train_rmse']:.4f}")
        print(f"  Val   RMSE: {self.training_metrics['val_rmse']:.4f}")
        print(f"  Val   R²:   {self.training_metrics['val_r2']:.4f}")
        print(f"  Val   MAE:  {self.training_metrics['val_mae']:.4f}")
        print(f"{'='*60}\n")

        return self.training_metrics

    def predict(self, X: np.ndarray) -> np.ndarray:
        """Predict collision risk (log10 probability)."""
        if self.model is None:
            raise ValueError("Model not trained. Call train() or load() first.")
        return self.model.predict(X)

    def predict_with_uncertainty(self, X: np.ndarray, n_iterations: int = 100) -> Tuple[np.ndarray, np.ndarray]:
        """
        Predict with uncertainty estimation using tree variance.
        Returns mean prediction and standard deviation.
        """
        if self.model is None:
            raise ValueError("Model not trained.")

        # Get prediction from each tree iteration
        preds = []
        booster = self.model.get_booster()
        dmatrix = xgb.DMatrix(X)

        max_iter = min(n_iterations, booster.num_boosted_rounds())
        step = max(1, booster.num_boosted_rounds() // max_iter)

        for i in range(step, booster.num_boosted_rounds() + 1, step):
            pred = booster.predict(dmatrix, iteration_range=(0, i))
            preds.append(pred)

        preds = np.array(preds)
        mean_pred = preds[-1]  # Full model prediction
        std_pred = np.std(preds, axis=0)  # Uncertainty from tree variance

        return mean_pred, std_pred

    def get_feature_importance(self, importance_type: str = "gain") -> pd.DataFrame:
        """Get feature importance rankings."""
        if self.model is None:
            raise ValueError("Model not trained.")

        importance = self.model.get_booster().get_score(importance_type=importance_type)

        df = pd.DataFrame([
            {"feature": self.feature_names[int(k.replace("f", ""))] if k.startswith("f") else k,
             "importance": v}
            for k, v in importance.items()
        ]).sort_values("importance", ascending=False).reset_index(drop=True)

        return df

    def save(self, name: str = "orbitguard_model") -> Path:
        """Save model and metadata to disk."""
        model_path = MODEL_DIR / f"{name}.json"
        meta_path = MODEL_DIR / f"{name}_meta.json"

        self.model.save_model(str(model_path))

        meta = {
            "feature_names": self.feature_names,
            "training_metrics": self.training_metrics,
            "use_gpu": self.use_gpu,
            "params": {k: str(v) for k, v in self.params.items()},
        }
        with open(meta_path, "w") as f:
            json.dump(meta, f, indent=2)

        # Save preprocessor
        preprocessor_path = MODEL_DIR / f"{name}_preprocessor.pkl"
        joblib.dump(self.preprocessor, str(preprocessor_path))

        print(f"[Model] Saved to {model_path}")
        return model_path

    def load(self, name: str = "orbitguard_model") -> None:
        """Load a saved model from disk."""
        model_path = MODEL_DIR / f"{name}.json"
        meta_path = MODEL_DIR / f"{name}_meta.json"
        preprocessor_path = MODEL_DIR / f"{name}_preprocessor.pkl"

        if not model_path.exists():
            raise FileNotFoundError(f"Model not found at {model_path}")

        self.model = xgb.XGBRegressor()
        self.model.load_model(str(model_path))
        self.model.set_params(device="cpu")

        with open(meta_path, "r") as f:
            meta = json.load(f)

        self.feature_names = meta["feature_names"]
        self.training_metrics = meta.get("training_metrics", {})

        if preprocessor_path.exists():
            self.preprocessor = joblib.load(str(preprocessor_path))

        print(f"[Model] Loaded from {model_path}")
        print(f"[Model] Features: {len(self.feature_names)}, "
              f"Val R²: {self.training_metrics.get('val_r2', 'N/A')}")


def alert_metrics(y_true: np.ndarray, y_pred: np.ndarray, threshold: float = RISK_THRESHOLD) -> dict:
    """Binary alert metrics: does the model flag the same events as high-risk (risk >= threshold)?"""
    t = y_true >= threshold
    p = y_pred >= threshold
    return {
        "alert_threshold": threshold,
        "alert_positives_true": int(t.sum()),
        "alert_positives_pred": int(p.sum()),
        "alert_precision": float(precision_score(t, p, zero_division=0)),
        "alert_recall": float(recall_score(t, p, zero_division=0)),
        "alert_f1": float(f1_score(t, p, zero_division=0)),
        # F2 weights recall over precision; it was the ESA Kelvins challenge's alert metric
        "alert_f2": float(fbeta_score(t, p, beta=2, zero_division=0)),
        "alert_accuracy": float((t == p).mean()),
    }


def split_by_event(groups: np.ndarray, val_size: float = 0.15, seed: int = 42) -> Tuple[np.ndarray, np.ndarray]:
    """
    Train/validation row indices split by event, so CDMs of one event never
    appear on both sides (a row-wise split leaks and inflates val scores).
    """
    from sklearn.model_selection import GroupShuffleSplit

    splitter = GroupShuffleSplit(n_splits=1, test_size=val_size, random_state=seed)
    return next(splitter.split(np.zeros(len(groups)), groups=groups))


def train_full_pipeline():
    """Run the complete training pipeline end-to-end."""

    # 1. Load and preprocess
    model = CollisionRiskModel(use_gpu=True)
    train_df, test_df = model.preprocessor.load_data()
    groups = train_df[GROUP_COLUMN].values

    X_train_full, y_train_full, X_test, y_test, feature_names = \
        model.preprocessor.prepare_for_training(train_df, test_df)

    # 2. Split training into train/val by event
    train_idx, val_idx = split_by_event(groups)
    X_train, X_val = X_train_full[train_idx], X_train_full[val_idx]
    y_train, y_val = y_train_full[train_idx], y_train_full[val_idx]

    # 3. Train
    metrics = model.train(X_train, y_train, X_val, y_val, feature_names)

    # 4. Evaluate on test set
    y_pred_test = model.predict(X_test)
    test_rmse = float(np.sqrt(mean_squared_error(y_test, y_pred_test)))
    test_mae = float(mean_absolute_error(y_test, y_pred_test))
    test_r2 = float(r2_score(y_test, y_pred_test))
    print(f"\n  Test RMSE: {test_rmse:.4f}")
    print(f"  Test MAE:  {test_mae:.4f}")
    print(f"  Test R²:   {test_r2:.4f}")

    metrics["test_rmse"] = test_rmse
    metrics["test_mae"] = test_mae
    metrics["test_r2"] = test_r2
    metrics.update({f"test_{k}": v for k, v in alert_metrics(y_test, y_pred_test).items()})
    metrics["n_train_rows"] = int(len(train_idx))
    metrics["n_val_rows"] = int(len(val_idx))
    metrics["n_test_rows"] = int(len(y_test))
    print(f"  Alerts (risk >= {RISK_THRESHOLD}): precision={metrics['test_alert_precision']:.3f} "
          f"recall={metrics['test_alert_recall']:.3f} f1={metrics['test_alert_f1']:.3f}")

    # 5. Feature importance
    fi = model.get_feature_importance()
    print(f"\nTop 15 features by gain:")
    print(fi.head(15).to_string(index=False))

    # 6. Save
    model.save()

    return model, metrics


EVAL_PATH = MODEL_DIR / "orbitguard_model_eval.json"


def evaluate_splits(model: "CollisionRiskModel" = None) -> dict:
    """
    Score the saved model on the same train / validation (event-grouped) / test
    rows used in training: R², RMSE, MAE and alert accuracy / precision / recall.
    Saved to models/orbitguard_model_eval.json for the dashboard.
    """
    if model is None:
        model = CollisionRiskModel(use_gpu=False)
        model.load()
    train_df, test_df = model.preprocessor.load_data()
    train_idx, val_idx = split_by_event(train_df[GROUP_COLUMN].values)
    X_all = model.preprocessor.transform(train_df)
    y_all = train_df[TARGET_COLUMN].to_numpy()
    splits = {
        "train": (X_all[train_idx], y_all[train_idx]),
        "validation": (X_all[val_idx], y_all[val_idx]),
        "test": (model.preprocessor.transform(test_df), test_df[TARGET_COLUMN].to_numpy()),
    }
    out = {}
    for name, (X, y) in splits.items():
        pred = model.predict(X)
        out[name] = {
            "rows": int(len(y)),
            "r2": float(r2_score(y, pred)),
            "rmse": float(np.sqrt(mean_squared_error(y, pred))),
            "mae": float(mean_absolute_error(y, pred)),
            **alert_metrics(y, pred),
        }
    EVAL_PATH.write_text(json.dumps(out, indent=2))
    return out


if __name__ == "__main__":
    model, metrics = train_full_pipeline()
    evaluate_splits(model)
