"""
End-to-End IoT Telemetry Simulation & Automated Irrigation Cycle.
Simulates a multi-zone diurnal weather cycle and actuator control.
"""

from app import create_app
from models import init_db
import json


def main():
    print("==========================================================================")
    print("PROJECT 4: SIMULATION / DRY RUN (AGROSCALE IOT TELEMETRY & RULE ENGINE)")
    print("==========================================================================\n")

    app = create_app(db_url="sqlite:///agroscale_sim.db")
    client = app.test_client()

    print("[Phase 1] Provisioning 3 Agricultural Field Zones via REST API...")
    zones = [
        {"zone_code": "ZONE-ALMOND-01", "crop_type": "Almonds", "area_hectares": 3.0, "target_moisture_min": 28.0, "target_moisture_max": 55.0},
        {"zone_code": "ZONE-CORN-02", "crop_type": "Sweet Corn", "area_hectares": 5.0, "target_moisture_min": 32.0, "target_moisture_max": 65.0},
        {"zone_code": "ZONE-VINEYARD-03", "crop_type": "Cabernet Sauvignon", "area_hectares": 2.5, "target_moisture_min": 20.0, "target_moisture_max": 40.0},
    ]

    zone_ids = {}
    for z in zones:
        res = client.post("/api/v1/zones", json=z)
        assert res.status_code == 201
        zone_ids[z["crop_type"]] = res.json["id"]
        print(f"  + Registered Zone #{res.json['id']}: {z['crop_type']} ({z['zone_code']}) - Initial Valve: {res.json['valve_status']}")

    print("\n[Phase 2] Simulating Afternoon High-Heat Telemetry (Drought Stress Ingestion)...")
    drought_readings = [
        {"zone_id": zone_ids["Almonds"], "soil_moisture_pct": 21.5, "ambient_temp_c": 37.2, "relative_humidity_pct": 22.0, "solar_radiation_wm2": 910.0},
        {"zone_id": zone_ids["Sweet Corn"], "soil_moisture_pct": 26.0, "ambient_temp_c": 36.5, "relative_humidity_pct": 25.0, "solar_radiation_wm2": 890.0},
        {"zone_id": zone_ids["Cabernet Sauvignon"], "soil_moisture_pct": 28.0, "ambient_temp_c": 35.0, "relative_humidity_pct": 30.0, "solar_radiation_wm2": 850.0}, # Still above min
    ]

    for read in drought_readings:
        res = client.post("/api/v1/telemetry", json=read)
        assert res.status_code == 200
        z_id = read["zone_id"]
        status = res.json["current_valve_status"]
        vpd = res.json["calculated_vpd_kpa"]
        event = res.json["rule_event_triggered"]

        print(f"\n  -> Ingested Telemetry for Zone #{z_id}: Moisture={read['soil_moisture_pct']}%, Temp={read['ambient_temp_c']}°C, VPD={vpd} kPa")
        print(f"     Valve Status: {status}")
        if event:
            print(f"     [ACTION TRIGGERED] {event['action']} - Reason: {event['reason']}")
            print(f"     Target Dispense Volume: {event['water_volume_liters']:,.1f} Liters")
        else:
            print("     No actuator state transition required (threshold satisfied)")

    print("\n[Phase 3] Querying Zone State & Event Audit History...")
    for crop, zid in zone_ids.items():
        res = client.get(f"/api/v1/zones/{zid}/status")
        assert res.status_code == 200
        data = res.json
        print(f"  * Zone #{zid} ({crop}): Valve={data['valve_status']} | Current VPD={data['current_vpd_kpa']} kPa")
        for ev in data["recent_events"]:
            print(f"      Event History: [{ev['action']}] {ev['reason']} ({ev['water_volume_liters']} L)")

    print("\n==========================================================================")
    print("AGROSCALE DRY RUN COMPLETED WITH 0 ERRORS.")
    print("==========================================================================")


if __name__ == "__main__":
    main()
