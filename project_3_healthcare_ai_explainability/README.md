# MedPathAI: Multi-Modal Disease Progression & Clinical Risk Predictor with SHAP Explainability (AI/ML)

## High-Impact Resume Bullets
* Built a calibrated clinical risk prediction pipeline analyzing vital signs and biochemical markers (eGFR, Troponin, HbA1c), achieving 0.7919 AUROC and a 0.1786 Brier score.
* Integrated SHAP (SHapley Additive exPlanations) TreeExplainer to produce local patient-level attribution cards and global feature importance rankings for ICU and bedside clinical teams.
* Implemented Platt scaling / sigmoid calibration guaranteeing mathematically verified risk probabilities suitable for medical triage workflows.
* Verified with comprehensive unit test coverage (`pytest`) and an automated simulation of triage ingestion across critical, elevated, and stable patient cohorts.
