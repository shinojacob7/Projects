"""
AgroScale Flask RESTful Application Backend.
Modular API providing IoT ingestion, automated rule dispatch, and zone state inspection.
"""

from datetime import datetime, timezone
from flask import Flask, request, jsonify
from models import init_db, FieldZone, SensorTelemetry, IrrigationEvent
from rule_engine import AgronomicRuleEngine


def create_app(session_factory=None, db_url="sqlite:///agroscale.db"):
    app = Flask(__name__)
    Session = session_factory if session_factory is not None else init_db(db_url)

    @app.route("/api/v1/health", methods=["GET"])
    def health():
        return jsonify({"status": "ONLINE", "service": "AgroScale-IoT-Engine"}), 200

    @app.route("/api/v1/zones", methods=["POST"])
    def create_zone():
        data = request.get_json() or {}
        required = ["zone_code", "crop_type", "target_moisture_min", "target_moisture_max"]
        for field in required:
            if field not in data:
                return jsonify({"error": f"Missing required field: {field}"}), 400

        with Session() as session:
            existing = session.query(FieldZone).filter_by(zone_code=data["zone_code"]).first()
            if existing:
                return jsonify({"error": "Zone code already registered"}), 409

            zone = FieldZone(
                zone_code=data["zone_code"],
                crop_type=data["crop_type"],
                area_hectares=float(data.get("area_hectares", 1.0)),
                target_moisture_min=float(data["target_moisture_min"]),
                target_moisture_max=float(data["target_moisture_max"]),
                valve_status="CLOSED",
                last_valve_change=None,
            )
            session.add(zone)
            session.commit()
            return jsonify({
                "id": zone.id,
                "zone_code": zone.zone_code,
                "crop_type": zone.crop_type,
                "valve_status": zone.valve_status,
            }), 201

    @app.route("/api/v1/telemetry", methods=["POST"])
    def ingest_telemetry():
        data = request.get_json() or {}
        required = ["zone_id", "soil_moisture_pct", "ambient_temp_c", "relative_humidity_pct"]
        for field in required:
            if field not in data:
                return jsonify({"error": f"Missing required telemetry field: {field}"}), 400

        zone_id = int(data["zone_id"])
        moisture = float(data["soil_moisture_pct"])
        temp_c = float(data["ambient_temp_c"])
        humidity = float(data["relative_humidity_pct"])
        solar = float(data.get("solar_radiation_wm2", 400.0))
        now = datetime.now(timezone.utc)

        with Session() as session:
            zone = session.query(FieldZone).filter_by(id=zone_id).first()
            if not zone:
                return jsonify({"error": "Zone not found"}), 404

            telemetry = SensorTelemetry(
                zone_id=zone.id,
                soil_moisture_pct=moisture,
                ambient_temp_c=temp_c,
                relative_humidity_pct=humidity,
                solar_radiation_wm2=solar,
                recorded_at=now,
            )
            session.add(telemetry)

            # Rule engine evaluation
            action_decision = AgronomicRuleEngine.evaluate_telemetry(zone, telemetry, now)
            event_data = None

            if action_decision is not None:
                action, reason, water_liters = action_decision
                new_status = "OPEN" if action == "START" else "CLOSED"
                zone.valve_status = new_status
                zone.last_valve_change = now

                event = IrrigationEvent(
                    zone_id=zone.id,
                    action=action,
                    reason=reason,
                    water_volume_liters=water_liters,
                    triggered_at=now,
                )
                session.add(event)
                session.flush()
                event_data = {
                    "event_id": event.id,
                    "action": action,
                    "reason": reason,
                    "water_volume_liters": water_liters,
                }

            session.commit()

            vpd = AgronomicRuleEngine.calculate_vpd(temp_c, humidity)
            return jsonify({
                "status": "INGESTED",
                "zone_id": zone.id,
                "current_valve_status": zone.valve_status,
                "calculated_vpd_kpa": vpd,
                "rule_event_triggered": event_data,
            }), 200

    @app.route("/api/v1/zones/<int:zone_id>/status", methods=["GET"])
    def get_zone_status(zone_id):
        with Session() as session:
            zone = session.query(FieldZone).filter_by(id=zone_id).first()
            if not zone:
                return jsonify({"error": "Zone not found"}), 404

            latest_telemetry = (
                session.query(SensorTelemetry)
                .filter_by(zone_id=zone.id)
                .order_by(SensorTelemetry.recorded_at.desc())
                .first()
            )

            vpd = None
            if latest_telemetry:
                vpd = AgronomicRuleEngine.calculate_vpd(
                    latest_telemetry.ambient_temp_c,
                    latest_telemetry.relative_humidity_pct,
                )

            recent_events = (
                session.query(IrrigationEvent)
                .filter_by(zone_id=zone.id)
                .order_by(IrrigationEvent.triggered_at.desc())
                .limit(5)
                .all()
            )

            return jsonify({
                "zone_id": zone.id,
                "zone_code": zone.zone_code,
                "crop_type": zone.crop_type,
                "valve_status": zone.valve_status,
                "current_vpd_kpa": vpd,
                "latest_telemetry": {
                    "soil_moisture_pct": latest_telemetry.soil_moisture_pct if latest_telemetry else None,
                    "ambient_temp_c": latest_telemetry.ambient_temp_c if latest_telemetry else None,
                    "relative_humidity_pct": latest_telemetry.relative_humidity_pct if latest_telemetry else None,
                } if latest_telemetry else None,
                "recent_events": [
                    {
                        "action": e.action,
                        "reason": e.reason,
                        "water_volume_liters": e.water_volume_liters,
                        "timestamp": e.triggered_at.isoformat(),
                    } for e in recent_events
                ],
            }), 200

    @app.route("/api/v1/zones/<int:zone_id>/override", methods=["POST"])
    def override_valve(zone_id):
        data = request.get_json() or {}
        new_status = data.get("valve_status")
        if new_status not in ["OPEN", "CLOSED"]:
            return jsonify({"error": "valve_status must be OPEN or CLOSED"}), 400

        with Session() as session:
            zone = session.query(FieldZone).filter_by(id=zone_id).first()
            if not zone:
                return jsonify({"error": "Zone not found"}), 404

            now = datetime.now(timezone.utc)
            zone.valve_status = new_status
            zone.last_valve_change = now

            event = IrrigationEvent(
                zone_id=zone.id,
                action="MANUAL_OVERRIDE",
                reason=f"Manual operator override to {new_status}",
                water_volume_liters=0.0,
                triggered_at=now,
            )
            session.add(event)
            session.commit()

            return jsonify({
                "zone_id": zone.id,
                "valve_status": zone.valve_status,
                "message": "Manual override applied successfully",
            }), 200

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=5000, debug=True)
