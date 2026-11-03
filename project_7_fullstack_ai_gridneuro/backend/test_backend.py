"""
Unit Test Suite for GridNeuro PyTorch ML Engine & Flask Backend.
"""

import pytest
import torch
from ml.model import GridDemandForecaster, get_pretrained_forecaster
from app import create_app


@pytest.fixture
def test_app(tmp_path):
    db_file = str(tmp_path / "test_grid.db")
    app = create_app(db_path=db_file)
    app.config["TESTING"] = True
    return app


def test_pytorch_model_inference():
    model = get_pretrained_forecaster()
    mw = model.predict_megawatts(hour=14, day_of_week=2, temp_c=34.5, solar_wm2=850.0, industrial_idx=0.9)
    assert isinstance(mw, float)
    assert 50.0 <= mw <= 1200.0


def test_flask_health_and_forecast_api(test_app):
    client = test_app.test_client()

    # Health check
    res_h = client.get("/api/v1/health")
    assert res_h.status_code == 200
    assert res_h.json["status"] == "ONLINE"

    # POST Forecast request
    payload = {
        "sector_name": "Metro-Downtown",
        "hour": 17,
        "day_of_week": 3,
        "temp_c": 38.0,
        "solar_wm2": 650.0,
        "industrial_idx": 0.85,
    }
    res_f = client.post("/api/v1/forecast", json=payload)
    assert res_f.status_code == 200
    data = res_f.json
    assert "predicted_load_mw" in data
    assert "dispatch_decision" in data
    assert data["sector_name"] == "Metro-Downtown"
    assert data["spinning_reserve_target_mw"] > 0.0

    # Query Sector History
    res_hist = client.get("/api/v1/sectors/Metro-Downtown/history")
    assert res_hist.status_code == 200
    assert len(res_hist.json["records"]) == 1
    assert res_hist.json["records"][0]["predicted_mw"] == data["predicted_load_mw"]
