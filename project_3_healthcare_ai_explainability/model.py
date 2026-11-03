"""
Clinical Risk Prediction Model Architecture with Probability Calibration.
"""

from typing import Dict, Any, Tuple
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.calibration import CalibratedClassifierCV


class ClinicalRiskPredictor:
    def __init__(self, random_state: int = 42):
        self.random_state = random_state
        base_estimator = GradientBoostingClassifier(
            n_estimators=100,
            learning_rate=0.08,
            max_depth=3,
            subsample=0.85,
            random_state=self.random_state,
        )
        # Platt calibration via sigmoid to guarantee trustworthy clinical probabilities
        self.calibrated_model = CalibratedClassifierCV(
            estimator=base_estimator,
            method="sigmoid",
            cv=3,
        )
        self.base_model = base_estimator
        self.is_trained = False

    def fit(self, X: np.ndarray, y: np.ndarray) -> "ClinicalRiskPredictor":
        # Fit base model first for SHAP explainer access
        self.base_model.fit(X, y)
        self.calibrated_model.fit(X, y)
        self.is_trained = True
        return self

    def predict_risk(self, X: np.ndarray) -> np.ndarray:
        """Returns calibrated probabilities for 30-day decompensation."""
        if not self.is_trained:
            raise RuntimeError("Model is not fitted yet.")
        return self.calibrated_model.predict_proba(X)[:, 1]

    def predict_binary(self, X: np.ndarray, threshold: float = 0.5) -> np.ndarray:
        risks = self.predict_risk(X)
        return (risks >= threshold).astype(int)
