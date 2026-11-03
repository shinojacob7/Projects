"""
End-to-End Clinical Dry-Run Simulation: MedPathAI
Simulates EHR triage ingestion, risk stratification, and patient-level SHAP explanation.
"""

from data_pipeline import ClinicalDataPipeline
from model import ClinicalRiskPredictor
from evaluator import ClinicalEvaluator
from explainer import ClinicalSHAPExplainer
import pandas as pd


def main():
    print("==========================================================================")
    print("PROJECT 3: SIMULATION / DRY RUN (MEDPATHAI CLINICAL RISK & SHAP ENGINE)")
    print("==========================================================================\n")

    print("[Phase 1] Ingesting Historical Cohort (1,000 Patients) & Training Model...")
    pipeline = ClinicalDataPipeline(random_state=42)
    X_df, y_series = pipeline.generate_synthetic_ehr_cohort(n_patients=1000)

    train_split = 800
    X_train_df, X_test_df = X_df.iloc[:train_split], X_df.iloc[train_split:]
    y_train, y_test = y_series.iloc[:train_split].values, y_series.iloc[train_split:].values

    X_train_scaled = pipeline.fit_transform(X_train_df)
    X_test_scaled = pipeline.transform(X_test_df)

    predictor = ClinicalRiskPredictor(random_state=42)
    predictor.fit(X_train_scaled, y_train)

    print("[Phase 2] Evaluating Performance on Validation Cohort (200 Patients)...")
    val_probs = predictor.predict_risk(X_test_scaled)
    metrics = ClinicalEvaluator.evaluate(y_test, val_probs)

    print(f"  * AUROC:       {metrics['auroc']:.4f}")
    print(f"  * AUPRC:       {metrics['auprc']:.4f}")
    print(f"  * Brier Score: {metrics['brier_score']:.4f} (Calibrated Probability Loss)")
    print(f"  * Sensitivity: {metrics['sensitivity']:.2%} | Specificity: {metrics['specificity']:.2%}")

    print("\n[Phase 3] Initializing SHAP Tree Explainer & Global Risk Drivers...")
    explainer = ClinicalSHAPExplainer(predictor.base_model, ClinicalDataPipeline.FEATURE_NAMES)
    global_drivers = explainer.compute_global_importance(X_test_scaled[:100])
    print("  Top 3 Global Clinical Progression Drivers:")
    for i, gd in enumerate(global_drivers[:3], 1):
        print(f"    {i}. {gd['feature']} (Mean |SHAP| = {gd['mean_absolute_shap']:.4f})")

    print("\n[Phase 4] Simulating Real-Time Bedside Triage for 3 Inbound Patients...")
    incoming_patients = [
        {
            "patient_id": "PT-9011 (Critical Cardiac / Renal)",
            "age": 78.0,
            "systolic_bp": 172.0,
            "diastolic_bp": 98.0,
            "hba1c_percent": 9.4,
            "egfr_rate": 28.0,
            "serum_creatinine": 2.8,
            "troponin_t_ng_ml": 0.18,
            "bmi": 32.4,
            "comorbidity_score": 4,
        },
        {
            "patient_id": "PT-9012 (Moderate Risk / Diabetic)",
            "age": 62.0,
            "systolic_bp": 138.0,
            "diastolic_bp": 84.0,
            "hba1c_percent": 8.1,
            "egfr_rate": 65.0,
            "serum_creatinine": 1.1,
            "troponin_t_ng_ml": 0.01,
            "bmi": 27.5,
            "comorbidity_score": 1,
        },
        {
            "patient_id": "PT-9013 (Low Risk / Stable)",
            "age": 42.0,
            "systolic_bp": 118.0,
            "diastolic_bp": 76.0,
            "hba1c_percent": 5.4,
            "egfr_rate": 95.0,
            "serum_creatinine": 0.8,
            "troponin_t_ng_ml": 0.005,
            "bmi": 23.1,
            "comorbidity_score": 0,
        },
    ]

    incoming_df = pd.DataFrame(incoming_patients).set_index("patient_id")
    incoming_scaled = pipeline.transform(incoming_df)
    risk_scores = predictor.predict_risk(incoming_scaled)

    for i, (pid, row) in enumerate(incoming_df.iterrows()):
        risk = risk_scores[i]
        triage_status = "CRITICAL ALERT" if risk >= 0.70 else ("ELEVATED MONITOR" if risk >= 0.35 else "STABLE")
        print(f"\n  -------------------------------------------------------")
        print(f"  Patient: {pid}")
        print(f"  Predicted 30-Day Decompensation Risk: {risk:.2%} [{triage_status}]")

        explanation = explainer.explain_instance(incoming_scaled[i], row.to_dict())
        print(f"  Top SHAP Feature Attributions:")
        for driver in explanation["top_drivers"]:
            sign = "+" if driver["shap_impact"] > 0 else ""
            print(f"    - {driver['feature']} = {driver['measured_value']} "
                  f"-> Impact: {sign}{driver['shap_impact']:.4f} ({driver['direction']})")

    print("\n==========================================================================")
    print("CLINICAL DRY RUN COMPLETED WITH 0 ERRORS.")
    print("==========================================================================")


if __name__ == "__main__":
    main()
