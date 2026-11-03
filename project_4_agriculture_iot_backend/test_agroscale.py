"""
Unit Test Suite for AgroScale Distributed IoT & Irrigation Backend.
"""

from datetime import datetime, timezone, timedelta
import pytest
from models import init_db, FieldZone, SensorTelemetry, IrrigationEvent
from rule_engine import AgronomicRuleEngine
from app import create_app


@pytest.fixture
def test_db_session():
    # In-memory SQLite for test isolation
    Session = init_db("sqlite:///:memory:")
    return Session


@pytest.fixture
def client(test_db_session):
    app = create_app(session_factory=test_db_session)
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_vpd_calculation_physics():
    # 25°C, 50% RH -> expected ~1.58 kPa
    vpd_moderate = AgronomicRuleEngine.calculate_vpd(temp_c=25.0, humidity_pct=50.0)
    assert 1.50 <= vpd_moderate <= 1.65

    # 35°C, 20% RH (Arid Heat) -> expected high VPD > 4.0 kPa
    vpd_arid = AgronomicRuleEngine.calculate_vpd(temp_c=35.0, humidity_pct=20.0)
    assert vpd_arid > 4.0

    # 20°C, 100% RH (Saturated mist) -> expected 0.0 kPa
    vpd_saturated = AgronomicRuleEngine.calculate_vpd(temp_c=20.0, humidity_pct=100.0)
    assert vpd_saturated == 0.0


def test_rule_engine_triggers():
    now = datetime.now(timezone.utc)
    old_time = now - timedelta(seconds=600)  # dwell expired

    zone = FieldZone(
        id=1,
        zone_code="ZONE-COR-01",
        crop_type="Corn",
        area_hectares=2.0,
        target_moisture_min=30.0,
        target_moisture_max=60.0,
        valve_status="CLOSED",
        last_valve_change=old_time,
    )

    # 1. Low moisture -> Should START
    low_telemetry = SensorTelemetry(
        zone_id=1,
        soil_moisture_pct=22.0,
        ambient_temp_c=32.0,
        relative_humidity_pct=35.0,
    )
    decision = AgronomicRuleEngine.evaluate_telemetry(zone, low_telemetry, now)
    assert decision is not None
    action, reason, water = decision
    assert action == "START"
    assert water > 0.0

    # 2. Debounce protection: if valve just changed 30 seconds ago, it must return None
    zone.valve_status = "OPEN"
    zone.last_valve_change = now - timedelta(seconds=30)
    high_telemetry = SensorTelemetry(
        zone_id=1,
        soil_moisture_pct=65.0,
        ambient_temp_c=28.0,
        relative_humidity_pct=70.0,
    )
    debounce_decision = AgronomicRuleEngine.evaluate_telemetry(zone, high_telemetry, now)
    assert debounce_decision is None  # Blocked by debounce guard!

    # 3. Saturation ceiling reached after debounce expires -> Should STOP
    zone.last_valve_change = now - timedelta(seconds=350)
    stop_decision = AgronomicRuleEngine.evaluate_telemetry(zone, high_telemetry, now)
    assert stop_decision is not None
    assert stop_decision[0] == "STOP"


def test_flask_api_full_cycle(client):
    # Health check
    res_h = client.get("/api/v1/health")
    assert res_h.status_code == 200

    # 1. Create Zone
    payload_zone = {
        "zone_code": "ZONE-VIN-01",
        "crop_type": "Wine Grapes",
        "area_hectares": 1.5,
        "target_moisture_min": 25.0,
        "target_moisture_max": 45.0,
    }
    res_zone = client.post("/api/v1/zones", json=payload_zone)
    assert res_zone.status_code == 201
    zone_id = res_zone.json["id"]

    # 2. Ingest drought telemetry (moisture 18% < min 25%)
    payload_telemetry = {
        "zone_id": zone_id,
        "soil_moisture_pct": 18.0,
        "ambient_temp_c": 36.0,
        "relative_humidity_pct": 28.0,
        "solar_radiation_wm2": 820.0,
    }
    res_tel = client.post("/api/v1/telemetry", json=payload_telemetry)
    assert res_tel.status_code == 200
    assert res_tel.json["current_valve_status"] == "OPEN"
    assert res_tel.json["rule_event_triggered"]["action"] == "START"

    # 3. Inspect Zone Status
    res_status = client.get(f"/api/v1/zones/{zone_id}/status")
    assert res_status.status_code == 200
    assert res_status.json["valve_status"] == "OPEN"
    assert res_status.json["current_vpd_kpa"] is not None
    assert len(res_status.json["recent_events"]) == 1

    # 4. Manual Override
    res_override = client.post(f"/api/v1/zones/{zone_id}/override", json={"valve_status": "CLOSED"})
    assert res_override.status_code == 200
    assert res_override.json["valve_status"] == "CLOSED"
