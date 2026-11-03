"""
Clinical Explainability Engine using SHAP (SHapley Additive exPlanations).
Provides local patient-level attribution and global feature importance.
"""

from typing import List, Dict, Any
import numpy as np
import shap


class ClinicalSHAPExplainer:
    def __init__(self, model, feature_names: List[str]):
        self.model = model
        self.feature_names = feature_names
        # Use TreeExplainer for Gradient Boosting model
        self.explainer = shap.TreeExplainer(self.model)

    def explain_instance(self, sample_scaled: np.ndarray, original_features: Dict[str, float]) -> Dict[str, Any]:
        """
        Computes SHAP attributions for a single patient sample.
        """
        if sample_scaled.ndim == 1:
            sample_scaled = sample_scaled.reshape(1, -1)

        shap_values = self.explainer.shap_values(sample_scaled)
        
        # In modern SHAP versions, binary classification returns either an array (n_samples, n_features)
        # or a list of two arrays. Handle both cleanly.
        if isinstance(shap_values, list):
            sv = shap_values[1][0] if len(shap_values) > 1 else shap_values[0][0]
        elif isinstance(shap_values, np.ndarray) and shap_values.ndim == 3:
            sv = shap_values[0, :, 1]
        else:
            sv = shap_values[0]

        attributions = []
        for name, impact in zip(self.feature_names, sv):
            attributions.append({
                "feature": name,
                "measured_value": original_features.get(name, 0.0),
                "shap_impact": float(impact),
                "direction": "RISK_INCREASING" if impact > 0 else "PROTECTIVE",
            })

        # Sort by magnitude of absolute impact
        attributions.sort(key=lambda x: abs(x["shap_impact"]), reverse=True)

        return {
            "top_drivers": attributions[:5],
            "all_attributions": attributions,
            "base_value": float(np.mean(self.explainer.expected_value)),
        }

    def compute_global_importance(self, X_scaled: np.ndarray) -> List[Dict[str, Any]]:
        shap_values = self.explainer.shap_values(X_scaled)
        if isinstance(shap_values, list):
            sv = shap_values[1] if len(shap_values) > 1 else shap_values[0]
        elif isinstance(shap_values, np.ndarray) and shap_values.ndim == 3:
            sv = shap_values[:, :, 1]
        else:
            sv = shap_values

        mean_abs_impact = np.mean(np.abs(sv), axis=0)
        ranked = []
        for name, score in zip(self.feature_names, mean_abs_impact):
            ranked.append({"feature": name, "mean_absolute_shap": float(score)})

        ranked.sort(key=lambda x: x["mean_absolute_shap"], reverse=True)
        return ranked
