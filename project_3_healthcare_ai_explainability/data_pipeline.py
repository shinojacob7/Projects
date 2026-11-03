"""
Clinical Data Preprocessing & Feature Pipeline for MedPathAI.
Handles vital signs, laboratory biomarkers, standardization, and synthetic EHR dataset generation.
"""

from dataclasses import dataclass
from typing import List, Tuple
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split


@dataclass
class ClinicalFeatures:
    feature_names: List[str]


class ClinicalDataPipeline:
    FEATURE_NAMES = [
        "age",
        "systolic_bp",
        "diastolic_bp",
        "hba1c_percent",
        "egfr_rate",
        "serum_creatinine",
        "troponin_t_ng_ml",
        "bmi",
        "comorbidity_score",
    ]

    def __init__(self, random_state: int = 42):
        self.random_state = random_state
        self.scaler = StandardScaler()
        self.is_fitted = False

    def generate_synthetic_ehr_cohort(self, n_patients: int = 1200) -> Tuple[pd.DataFrame, pd.Series]:
        """
        Generates realistic EHR synthetic patient cohort with non-linear clinical risk interactions.
        """
        rng = np.random.default_rng(self.random_state)

        age = rng.normal(loc=64.0, scale=12.0, size=n_patients).clip(30, 95)
        systolic_bp = rng.normal(loc=136.0, scale=18.0, size=n_patients).clip(90, 210)
        diastolic_bp = rng.normal(loc=84.0, scale=10.0, size=n_patients).clip(55, 125)
        hba1c = rng.normal(loc=7.2, scale=1.5, size=n_patients).clip(4.8, 14.0)
        egfr = rng.normal(loc=62.0, scale=22.0, size=n_patients).clip(10, 120)
        creatinine = rng.normal(loc=1.3, scale=0.6, size=n_patients).clip(0.5, 4.5)
        troponin = rng.exponential(scale=0.03, size=n_patients).clip(0.001, 0.45)
        bmi = rng.normal(loc=28.5, scale=5.0, size=n_patients).clip(18.0, 50.0)
        comorbidity = rng.integers(low=0, high=6, size=n_patients)

        df = pd.DataFrame({
            "age": age,
            "systolic_bp": systolic_bp,
            "diastolic_bp": diastolic_bp,
            "hba1c_percent": hba1c,
            "egfr_rate": egfr,
            "serum_creatinine": creatinine,
            "troponin_t_ng_ml": troponin,
            "bmi": bmi,
            "comorbidity_score": comorbidity,
        })

        # Clinically calibrated log-odds score
        log_odds = (
            0.04 * (df["age"] - 60)
            + 0.03 * (df["systolic_bp"] - 130)
            + 0.35 * (df["hba1c_percent"] - 7.0)
            - 0.05 * (df["egfr_rate"] - 60)
            + 0.80 * (df["serum_creatinine"] - 1.2)
            + 8.0 * df["troponin_t_ng_ml"]
            + 0.25 * df["comorbidity_score"]
            - 0.80
        )
        probabilities = 1.0 / (1.0 + np.exp(-log_odds))
        labels = (rng.uniform(size=n_patients) < probabilities).astype(int)

        return df, pd.Series(labels, name="decompensation_30d")

    def fit_transform(self, X: pd.DataFrame) -> np.ndarray:
        self.scaler.fit(X[self.FEATURE_NAMES])
        self.is_fitted = True
        return self.scaler.transform(X[self.FEATURE_NAMES])

    def transform(self, X: pd.DataFrame) -> np.ndarray:
        if not self.is_fitted:
            raise RuntimeError("Pipeline must be fitted prior to transform.")
        return self.scaler.transform(X[self.FEATURE_NAMES])
