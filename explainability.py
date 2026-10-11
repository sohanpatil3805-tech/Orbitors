"""
OrbitGuard AI — SHAP Explainability Module
Provides model-agnostic explanations for collision risk predictions using SHAP.
"""

import numpy as np
import pandas as pd
import shap
import plotly.graph_objects as go
import plotly.express as px
from typing import Optional


class RiskExplainer:
    """
    SHAP-based explainability for the collision risk model.
    Explains WHY the model predicts a certain risk level.
    """

    def __init__(self, model, feature_names: list[str]):
        """
        Parameters
        ----------
        model : trained XGBoost model (xgb.XGBRegressor)
        feature_names : list of feature column names
        """
        self.model = model
        self.feature_names = feature_names
        self.explainer: Optional[shap.TreeExplainer] = None
        self._initialise_explainer()

    def _initialise_explainer(self):
        """Create the SHAP TreeExplainer."""
        try:
            self.explainer = shap.TreeExplainer(self.model)
            print("[SHAP] TreeExplainer initialised successfully")
        except Exception as e:
            print(f"[SHAP] Warning: Could not initialise TreeExplainer: {e}")
            self.explainer = None

    def explain_single(self, X_single: np.ndarray) -> dict:
        """
        Explain a single prediction.

        Parameters
        ----------
        X_single : 1D or 2D array of feature values for one sample

        Returns
        -------
        dict with keys: prediction, base_value, shap_values, top_features
        """
        if self.explainer is None:
            return {"error": "Explainer not available"}

        X = X_single.reshape(1, -1) if X_single.ndim == 1 else X_single[:1]
        shap_values = self.explainer.shap_values(X)

        if isinstance(shap_values, list):
            shap_values = shap_values[0]

        sv = shap_values[0]
        base_value = self.explainer.expected_value
        if isinstance(base_value, np.ndarray):
            base_value = float(base_value[0])

        prediction = float(base_value + sv.sum())

        # Sort features by absolute SHAP impact
        feature_impacts = []
        for i, (name, val, shapval) in enumerate(zip(self.feature_names, X[0], sv)):
            feature_impacts.append({
                "feature": name,
                "value": float(val),
                "shap_value": float(shapval),
                "abs_impact": float(abs(shapval)),
                "direction": "increases risk" if shapval > 0 else "decreases risk",
            })

        feature_impacts.sort(key=lambda x: x["abs_impact"], reverse=True)

        return {
            "prediction": prediction,
            "base_value": float(base_value),
            "shap_values": sv.tolist(),
            "top_features": feature_impacts[:15],
            "total_features": len(feature_impacts),
        }

    def explain_batch(self, X: np.ndarray) -> np.ndarray:
        """
        Compute SHAP values for a batch of samples.

        Returns
        -------
        np.ndarray : SHAP values matrix (n_samples × n_features)
        """
        if self.explainer is None:
            return np.zeros_like(X)

        shap_values = self.explainer.shap_values(X)
        if isinstance(shap_values, list):
            shap_values = shap_values[0]
        return shap_values

    def create_waterfall_chart(self, X_single: np.ndarray, event_id: str = "") -> go.Figure:
        """
        Create an interactive Plotly waterfall chart showing SHAP contributions.
        """
        explanation = self.explain_single(X_single)

        if "error" in explanation:
            fig = go.Figure()
            fig.add_annotation(text="Explainer not available", showarrow=False)
            return fig

        top = explanation["top_features"][:12]

        features = [f["feature"] for f in reversed(top)]
        values = [f["shap_value"] for f in reversed(top)]
        feature_vals = [f["value"] for f in reversed(top)]

        colors = ["#FF0040" if v > 0 else "#00E676" for v in values]

        fig = go.Figure()

        fig.add_trace(go.Bar(
            y=features,
            x=values,
            orientation="h",
            marker_color=colors,
            text=[f"{v:+.3f}" for v in values],
            textposition="auto",
            hovertemplate=(
                "<b>%{y}</b><br>"
                "SHAP value: %{x:.4f}<br>"
                "Feature value: %{customdata:.4f}<br>"
                "<extra></extra>"
            ),
            customdata=feature_vals,
        ))

        # Add base value line
        fig.add_vline(x=0, line_dash="dash", line_color="rgba(255,255,255,0.3)")

        title = f"Risk Explanation"
        if event_id:
            title += f" — Event {event_id}"
        title += f" (Prediction: {explanation['prediction']:.3f})"

        fig.update_layout(
            title=dict(text=title, font=dict(size=16, color="white")),
            xaxis_title="SHAP Value (impact on risk prediction)",
            yaxis_title="",
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(20,20,40,0.8)",
            height=500,
            margin=dict(l=200, r=40, t=60, b=40),
            font=dict(family="Inter, sans-serif", color="white"),
        )

        return fig

    def create_summary_plot(self, X: np.ndarray, max_samples: int = 500) -> go.Figure:
        """
        Create an interactive SHAP summary (beeswarm-style) plot.
        """
        if X.shape[0] > max_samples:
            idx = np.random.choice(X.shape[0], max_samples, replace=False)
            X_sample = X[idx]
        else:
            X_sample = X

        shap_values = self.explain_batch(X_sample)

        # Mean absolute SHAP value per feature
        mean_abs = np.mean(np.abs(shap_values), axis=0)
        top_indices = np.argsort(mean_abs)[-20:][::-1]

        top_features = [self.feature_names[i] for i in top_indices]
        top_mean_abs = mean_abs[top_indices]

        fig = go.Figure()

        fig.add_trace(go.Bar(
            y=list(reversed(top_features)),
            x=list(reversed(top_mean_abs)),
            orientation="h",
            marker=dict(
                color=list(reversed(top_mean_abs)),
                colorscale="Turbo",
                showscale=True,
                colorbar=dict(title="Mean |SHAP|"),
            ),
            hovertemplate="<b>%{y}</b><br>Mean |SHAP|: %{x:.4f}<extra></extra>",
        ))

        fig.update_layout(
            title=dict(
                text="Feature Importance — Mean |SHAP| Values",
                font=dict(size=16, color="white"),
            ),
            xaxis_title="Mean |SHAP Value|",
            yaxis_title="",
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(20,20,40,0.8)",
            height=600,
            margin=dict(l=220, r=40, t=60, b=40),
            font=dict(family="Inter, sans-serif", color="white"),
        )

        return fig

    def create_dependence_plot(
        self,
        X: np.ndarray,
        feature_name: str,
        interaction_feature: Optional[str] = None,
        max_samples: int = 1000,
    ) -> go.Figure:
        """
        Create a SHAP dependence plot for a single feature.
        """
        if feature_name not in self.feature_names:
            fig = go.Figure()
            fig.add_annotation(text=f"Feature '{feature_name}' not found", showarrow=False)
            return fig

        if X.shape[0] > max_samples:
            idx = np.random.choice(X.shape[0], max_samples, replace=False)
            X_sample = X[idx]
        else:
            X_sample = X

        shap_values = self.explain_batch(X_sample)

        feat_idx = self.feature_names.index(feature_name)
        feat_values = X_sample[:, feat_idx]
        feat_shap = shap_values[:, feat_idx]

        if interaction_feature and interaction_feature in self.feature_names:
            int_idx = self.feature_names.index(interaction_feature)
            color_values = X_sample[:, int_idx]
            color_label = interaction_feature
        else:
            color_values = feat_shap
            color_label = "SHAP value"

        fig = go.Figure()

        fig.add_trace(go.Scatter(
            x=feat_values,
            y=feat_shap,
            mode="markers",
            marker=dict(
                size=4,
                color=color_values,
                colorscale="Turbo",
                showscale=True,
                colorbar=dict(title=color_label),
                opacity=0.6,
            ),
            hovertemplate=(
                f"<b>{feature_name}</b>: %{{x:.4f}}<br>"
                f"SHAP: %{{y:.4f}}<br>"
                f"<extra></extra>"
            ),
        ))

        fig.add_hline(y=0, line_dash="dash", line_color="rgba(255,255,255,0.3)")

        fig.update_layout(
            title=dict(
                text=f"SHAP Dependence — {feature_name}",
                font=dict(size=16, color="white"),
            ),
            xaxis_title=feature_name,
            yaxis_title=f"SHAP value for {feature_name}",
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(20,20,40,0.8)",
            height=500,
            font=dict(family="Inter, sans-serif", color="white"),
        )

        return fig

    def generate_narrative(self, X_single: np.ndarray) -> str:
        """
        Generate a human-readable narrative explanation.
        """
        explanation = self.explain_single(X_single)

        if "error" in explanation:
            return "Unable to generate explanation."

        pred = explanation["prediction"]
        base = explanation["base_value"]
        top = explanation["top_features"][:5]

        # Risk category
        if pred >= -3.0:
            level = "CRITICAL"
            emoji = "🔴"
        elif pred >= -4.5:
            level = "HIGH"
            emoji = "🟠"
        elif pred >= -6.0:
            level = "MEDIUM"
            emoji = "🟡"
        elif pred >= -7.5:
            level = "LOW"
            emoji = "🟢"
        else:
            level = "NEGLIGIBLE"
            emoji = "🔵"

        narrative = f"{emoji} **Risk Level: {level}** (log₁₀ Pc = {pred:.3f})\n\n"
        narrative += f"The baseline collision probability is {base:.3f}. "
        narrative += "The following factors most strongly influenced this assessment:\n\n"

        for i, feat in enumerate(top, 1):
            direction = "↑" if feat["shap_value"] > 0 else "↓"
            impact = "increases" if feat["shap_value"] > 0 else "decreases"
            narrative += (
                f"**{i}. {feat['feature']}** = {feat['value']:.4g} "
                f"→ {direction} {impact} risk by {abs(feat['shap_value']):.4f}\n"
            )

        return narrative
