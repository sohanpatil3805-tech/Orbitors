"""
OrbitGuard AI — Data Preprocessing Pipeline
Handles loading, cleaning, feature engineering, and preparation of CDM conjunction data.
"""

import numpy as np
import pandas as pd
from sklearn.preprocessing import LabelEncoder, StandardScaler
from typing import Tuple, Optional

from config import (
    TRAIN_DATA_PATH,
    TEST_DATA_PATH,
    TARGET_COLUMN,
    EXCLUDE_COLUMNS,
)


class DataPreprocessor:
    """End-to-end data preprocessing for conjunction risk assessment."""

    def __init__(self):
        self.label_encoders: dict[str, LabelEncoder] = {}
        self.scaler: Optional[StandardScaler] = None
        self.feature_columns: list[str] = []
        self.categorical_columns: list[str] = []
        self.numerical_columns: list[str] = []
        self.fill_values: dict[str, float] = {}
        self.final_feature_columns: list[str] = []

    def load_data(self, train_path=None, test_path=None) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Load training and test data from CSV files."""
        train_path = train_path or TRAIN_DATA_PATH
        test_path = test_path or TEST_DATA_PATH

        print(f"[Data] Loading training data from {train_path}...")
        train_df = pd.read_csv(train_path)
        print(f"[Data] Loaded {len(train_df):,} training rows × {train_df.shape[1]} columns")

        print(f"[Data] Loading test data from {test_path}...")
        test_df = pd.read_csv(test_path)
        print(f"[Data] Loaded {len(test_df):,} test rows × {test_df.shape[1]} columns")

        return train_df, test_df

    def identify_columns(self, df: pd.DataFrame) -> None:
        """Identify feature columns, separating categorical from numerical."""
        all_cols = list(df.columns)
        feature_cols = [c for c in all_cols if c not in EXCLUDE_COLUMNS]

        self.categorical_columns = []
        self.numerical_columns = []

        for col in feature_cols:
            # pandas >= 3 stores text as "str" rather than "object"
            if not pd.api.types.is_numeric_dtype(df[col]):
                self.categorical_columns.append(col)
            else:
                self.numerical_columns.append(col)

        self.feature_columns = feature_cols
        print(f"[Data] Features: {len(feature_cols)} total "
              f"({len(self.numerical_columns)} numeric, {len(self.categorical_columns)} categorical)")

    def handle_missing_values(self, df: pd.DataFrame, fit: bool = True) -> pd.DataFrame:
        """Handle missing values with appropriate strategies.

        With fit=True the training medians are stored and reused for later
        (test / inference) data, so a single row can be filled consistently.
        """
        df = df.copy()

        # Count missing values before
        total_missing = df[self.feature_columns].isnull().sum().sum()
        if total_missing > 0:
            print(f"[Data] Handling {total_missing:,} missing values...")

        # Numerical: fill with median
        for col in self.numerical_columns:
            if col not in df.columns:
                continue
            if fit:
                self.fill_values[col] = float(df[col].median())
            if df[col].isnull().any():
                df[col] = df[col].fillna(self.fill_values.get(col, df[col].median()))

        # Categorical: fill with mode or "UNKNOWN"
        for col in self.categorical_columns:
            if col in df.columns and df[col].isnull().any():
                mode_val = df[col].mode()
                fill_val = mode_val.iloc[0] if len(mode_val) > 0 else "UNKNOWN"
                df[col] = df[col].fillna(fill_val)

        return df

    def encode_categoricals(self, df: pd.DataFrame, fit: bool = True) -> pd.DataFrame:
        """Encode categorical columns using LabelEncoder."""
        df = df.copy()

        for col in self.categorical_columns:
            if col not in df.columns:
                continue

            if fit:
                le = LabelEncoder()
                # Add an 'UNKNOWN' class to handle unseen labels at test time
                all_values = list(df[col].astype(str).unique()) + ["UNKNOWN"]
                le.fit(all_values)
                self.label_encoders[col] = le

            if col in self.label_encoders:
                le = self.label_encoders[col]
                mapping = {c: i for i, c in enumerate(le.classes_)}
                unknown = mapping["UNKNOWN"]
                df[col] = df[col].astype(str).map(mapping).fillna(unknown).astype(np.int32)

        return df

    def engineer_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Create derived features that improve collision risk prediction."""
        df = df.copy()

        # ─── Relative dynamics features ───────────────────────────────────
        if all(c in df.columns for c in ["relative_position_r", "relative_position_t", "relative_position_n"]):
            df["relative_position_magnitude"] = np.sqrt(
                df["relative_position_r"] ** 2 +
                df["relative_position_t"] ** 2 +
                df["relative_position_n"] ** 2
            )

        if all(c in df.columns for c in ["relative_velocity_r", "relative_velocity_t", "relative_velocity_n"]):
            df["relative_velocity_magnitude"] = np.sqrt(
                df["relative_velocity_r"] ** 2 +
                df["relative_velocity_t"] ** 2 +
                df["relative_velocity_n"] ** 2
            )

        # ─── Time-related features ────────────────────────────────────────
        if "time_to_tca" in df.columns:
            df["log_time_to_tca"] = np.log1p(np.abs(df["time_to_tca"]))
            df["time_to_tca_hours"] = df["time_to_tca"] * 24.0
            df["time_to_tca_squared"] = df["time_to_tca"] ** 2

        # ─── Covariance features ──────────────────────────────────────────
        if all(c in df.columns for c in ["t_sigma_r", "t_sigma_t", "t_sigma_n"]):
            df["t_position_uncertainty"] = np.sqrt(
                df["t_sigma_r"] ** 2 + df["t_sigma_t"] ** 2 + df["t_sigma_n"] ** 2
            )

        if all(c in df.columns for c in ["c_sigma_r", "c_sigma_t", "c_sigma_n"]):
            df["c_position_uncertainty"] = np.sqrt(
                df["c_sigma_r"] ** 2 + df["c_sigma_t"] ** 2 + df["c_sigma_n"] ** 2
            )

        if "t_position_uncertainty" in df.columns and "c_position_uncertainty" in df.columns:
            df["combined_uncertainty"] = np.sqrt(
                df["t_position_uncertainty"] ** 2 + df["c_position_uncertainty"] ** 2
            )

        # ─── Orbital element differences ──────────────────────────────────
        if "t_j2k_sma" in df.columns and "c_j2k_sma" in df.columns:
            df["delta_sma"] = np.abs(df["t_j2k_sma"] - df["c_j2k_sma"])

        if "t_j2k_ecc" in df.columns and "c_j2k_ecc" in df.columns:
            df["delta_ecc"] = np.abs(df["t_j2k_ecc"] - df["c_j2k_ecc"])

        if "t_j2k_inc" in df.columns and "c_j2k_inc" in df.columns:
            df["delta_inc"] = np.abs(df["t_j2k_inc"] - df["c_j2k_inc"])

        # ─── Altitude features ────────────────────────────────────────────
        if all(c in df.columns for c in ["t_h_apo", "t_h_per"]):
            df["t_altitude_avg"] = (df["t_h_apo"] + df["t_h_per"]) / 2.0

        if all(c in df.columns for c in ["c_h_apo", "c_h_per"]):
            df["c_altitude_avg"] = (df["c_h_apo"] + df["c_h_per"]) / 2.0

        # ─── Observation quality features ─────────────────────────────────
        if "t_obs_used" in df.columns and "t_obs_available" in df.columns:
            df["t_obs_ratio"] = df["t_obs_used"] / (df["t_obs_available"] + 1e-8)

        if "c_obs_used" in df.columns and "c_obs_available" in df.columns:
            df["c_obs_ratio"] = df["c_obs_used"] / (df["c_obs_available"] + 1e-8)

        # ─── Mahalanobis distance log ─────────────────────────────────────
        if "mahalanobis_distance" in df.columns:
            df["log_mahalanobis"] = np.log1p(df["mahalanobis_distance"])

        # ─── Miss distance log ────────────────────────────────────────────
        if "miss_distance" in df.columns:
            df["log_miss_distance"] = np.log1p(df["miss_distance"])

        # ─── Covariance determinants ──────────────────────────────────────
        # Raw determinants reach ~1e47, beyond float32 range; use signed log10.
        for col in ["t_position_covariance_det", "c_position_covariance_det"]:
            if col in df.columns:
                df[col] = np.sign(df[col]) * np.log10(1.0 + np.abs(df[col]))

        # ─── Max risk scaling ratio ───────────────────────────────────────
        if "max_risk_estimate" in df.columns and "max_risk_scaling" in df.columns:
            df["risk_scaling_ratio"] = df["max_risk_estimate"] / (df["max_risk_scaling"] + 1e-8)

        # Replace inf values
        df = df.replace([np.inf, -np.inf], np.nan)
        for col in df.select_dtypes(include=[np.number]).columns:
            if df[col].isnull().any():
                fill = self.fill_values.get(col)
                df[col] = df[col].fillna(fill if fill is not None else df[col].median())

        return df

    def prepare_for_training(
        self,
        train_df: pd.DataFrame,
        test_df: pd.DataFrame,
        scale: bool = False,
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, list[str]]:
        """
        Full preprocessing pipeline: identify, clean, engineer, encode, split.

        Returns
        -------
        X_train, y_train, X_test, y_test, feature_names
        """
        # 1. Identify columns
        self.identify_columns(train_df)

        # 2. Handle missing values (medians learned from training data only)
        train_df = self.handle_missing_values(train_df, fit=True)
        test_df = self.handle_missing_values(test_df, fit=False)

        # 3. Engineer features (fill values for derived columns come from training data)
        train_df = self.engineer_features(train_df)
        for col in train_df.select_dtypes(include=[np.number]).columns:
            if col not in self.fill_values:
                self.fill_values[col] = float(train_df[col].median())
        test_df = self.engineer_features(test_df)

        # 4. Encode categoricals
        train_df = self.encode_categoricals(train_df, fit=True)
        test_df = self.encode_categoricals(test_df, fit=False)

        # 5. Re-identify columns after feature engineering
        all_feature_cols = [
            c for c in train_df.columns
            if c not in EXCLUDE_COLUMNS and c in test_df.columns
        ]

        # 6. Extract arrays
        y_train = train_df[TARGET_COLUMN].values if TARGET_COLUMN in train_df.columns else None
        y_test = test_df[TARGET_COLUMN].values if TARGET_COLUMN in test_df.columns else None

        feature_cols_final = [c for c in all_feature_cols if c != TARGET_COLUMN]
        self.final_feature_columns = feature_cols_final
        X_train = self._to_float32(train_df[feature_cols_final].values)
        X_test = self._to_float32(test_df[feature_cols_final].values)

        # 7. Optional scaling
        if scale:
            self.scaler = StandardScaler()
            X_train = self.scaler.fit_transform(X_train)
            X_test = self.scaler.transform(X_test)

        print(f"[Data] Final shapes: X_train={X_train.shape}, X_test={X_test.shape}")
        return X_train, y_train, X_test, y_test, feature_cols_final

    @staticmethod
    def _to_float32(values: np.ndarray) -> np.ndarray:
        """Cast to float32, clipping to the representable range so nothing becomes inf."""
        limit = np.finfo(np.float32).max
        return np.clip(values.astype(np.float64), -limit, limit).astype(np.float32)

    def transform(self, df: pd.DataFrame) -> np.ndarray:
        """
        Transform raw CDM rows into the model's feature matrix using the
        state fitted in prepare_for_training(). Use this for inference.
        """
        if not self.final_feature_columns:
            raise ValueError("Preprocessor not fitted. Call prepare_for_training() first.")
        df = self.handle_missing_values(df, fit=False)
        df = self.engineer_features(df)
        df = self.encode_categoricals(df, fit=False)
        for col in self.final_feature_columns:
            if col not in df.columns:
                df[col] = self.fill_values.get(col, 0.0)
        X = self._to_float32(df[self.final_feature_columns].values)
        if self.scaler is not None:
            X = self.scaler.transform(X)
        return X

    def get_risk_category(self, risk_value: float) -> str:
        """Convert a log10 risk value to a human-readable category."""
        if risk_value >= -3.0:
            return "CRITICAL"
        elif risk_value >= -4.5:
            return "HIGH"
        elif risk_value >= -6.0:
            return "MEDIUM"
        elif risk_value >= -7.5:
            return "LOW"
        else:
            return "NEGLIGIBLE"


if __name__ == "__main__":
    preprocessor = DataPreprocessor()
    train_df, test_df = preprocessor.load_data()

    X_train, y_train, X_test, y_test, feature_names = preprocessor.prepare_for_training(
        train_df, test_df
    )

    print(f"\nFeature count: {len(feature_names)}")
    print(f"Training target range: [{y_train.min():.2f}, {y_train.max():.2f}]")
    print(f"Test target range:     [{y_test.min():.2f}, {y_test.max():.2f}]")
