"""
Unit Test Suite for MedPathAI Healthcare Risk Predictor.
"""

import pytest
import numpy as np
import pandas as pd
from data_pipeline import ClinicalDataPipeline
from model import ClinicalRiskPredictor
from evaluator import ClinicalEvaluator
from explainer import ClinicalSHAPExplainer


@pytest.fixture
def pipeline_data():
    pipeline = ClinicalDataPipeline(random_state=42)
    X_df, y_series = pipeline.generate_synthetic_ehr_cohort(n_patients=600)
    X_scaled = pipeline.fit_transform(X_df)
    return {
        "pipeline": pipeline,
        "X_df": X_df,
        "y": y_series.values,
        "X_scaled": X_scaled,
    }


def test_pipeline_cohort_generation(pipeline_data):
    X_df = pipeline_data["X_df"]
    y = pipeline_data["y"]
    assert len(X_df) == 600
    assert len(y) == 600
    assert set(X_df.columns) == set(ClinicalDataPipeline.FEATURE_NAMES)
    # Target prevalence check (reasonable clinical balance between 20% and 60%)
    pos_rate = np.mean(y)
    assert 0.20 <= pos_rate <= 0.60


def test_pipeline_scaling(pipeline_data):
    X_scaled = pipeline_data["X_scaled"]
    # Scaled features should have mean approx 0 and std approx 1
    means = np.mean(X_scaled, axis=0)
    stds = np.std(X_scaled, axis=0)
    assert np.allclose(means, 0.0, atol=1e-2)
    assert np.allclose(stds, 1.0, atol=1e-2)


def test_model_training_and_probabilities(pipeline_data):
    X_scaled = pipeline_data["X_scaled"]
    y = pipeline_data["y"]

    model = ClinicalRiskPredictor(random_state=42)
    model.fit(X_scaled, y)

    probabilities = model.predict_risk(X_scaled)
    assert len(probabilities) == len(y)
    # Calibrated probabilities must be strictly bounded in [0.0, 1.0]
    assert np.all(probabilities >= 0.0)
    assert np.all(probabilities <= 1.0)

    binary_preds = model.predict_binary(X_scaled, threshold=0.5)
    assert set(binary_preds).issubset({0, 1})


def test_clinical_evaluator_metrics(pipeline_data):
    X_scaled = pipeline_data["X_scaled"]
    y = pipeline_data["y"]

    model = ClinicalRiskPredictor(random_state=42)
    model.fit(X_scaled[:450], y[:450])
    test_probs = model.predict_risk(X_scaled[450:])
    test_y = y[450:]

    metrics = ClinicalEvaluator.evaluate(test_y, test_probs, threshold=0.5)

    assert "auroc" in metrics
    assert "brier_score" in metrics
    assert metrics["auroc"] > 0.70  # Should beat random chance strongly
    assert 0.0 <= metrics["brier_score"] <= 0.25  # Good calibration


def test_shap_explainability_consistency(pipeline_data):
    X_scaled = pipeline_data["X_scaled"]
    y = pipeline_data["y"]
    X_df = pipeline_data["X_df"]

    model = ClinicalRiskPredictor(random_state=42)
    model.fit(X_scaled, y)

    explainer = ClinicalSHAPExplainer(model.base_model, ClinicalDataPipeline.FEATURE_NAMES)
    sample_patient = X_df.iloc[0].to_dict()
    explanation = explainer.explain_instance(X_scaled[0], sample_patient)

    assert "top_drivers" in explanation
    assert len(explanation["top_drivers"]) == 5
    for driver in explanation["top_drivers"]:
        assert "feature" in driver
        assert "shap_impact" in driver
        assert driver["direction"] in ["RISK_INCREASING", "PROTECTIVE"]

    global_rank = explainer.compute_global_importance(X_scaled[:50])
    assert len(global_rank) == len(ClinicalDataPipeline.FEATURE_NAMES)
