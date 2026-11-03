"""
Flask REST API for GridNeuro Smart Grid Dispatch Optimizer.
Interfaces PyTorch inference engine with SQLite persistence and RESTful endpoints.
"""

from datetime import datetime, timezone
import sqlite3
from flask import Flask, request, jsonify

try:
    from ml.model import get_pretrained_forecaster
except ModuleNotFoundError:
    from backend.ml.model import get_pretrained_forecaster


def init_db(db_path: str = "gridneuro.db"):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS grid_sectors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sector_name TEXT UNIQUE NOT NULL,
            installed_capacity_mw REAL NOT NULL
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS forecast_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sector_name TEXT NOT NULL,
            hour INTEGER NOT NULL,
            temp_c REAL NOT NULL,
            solar_wm2 REAL NOT NULL,
            predicted_mw REAL NOT NULL,
            dispatch_decision TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
    # Seed default sectors if not present
    cur.execute("INSERT OR IGNORE INTO grid_sectors (sector_name, installed_capacity_mw) VALUES ('Metro-Downtown', 800.0)")
    cur.execute("INSERT OR IGNORE INTO grid_sectors (sector_name, installed_capacity_mw) VALUES ('Industrial-Valley', 1200.0)")
    cur.execute("INSERT OR IGNORE INTO grid_sectors (sector_name, installed_capacity_mw) VALUES ('Suburban-West', 450.0)")
    conn.commit()
    conn.close()


def create_app(db_path: str = "gridneuro.db", forecaster_model=None):
    app = Flask(__name__)
    init_db(db_path)
    model = forecaster_model if forecaster_model is not None else get_pretrained_forecaster()

    @app.route("/api/v1/health", methods=["GET"])
    def health():
        return jsonify({"status": "ONLINE", "service": "GridNeuro-FullStack-AI"}), 200

    @app.route("/api/v1/forecast", methods=["POST"])
    def generate_forecast():
        data = request.get_json() or {}
        required = ["sector_name", "hour", "day_of_week", "temp_c", "solar_wm2", "industrial_idx"]
        for field in required:
            if field not in data:
                return jsonify({"error": f"Missing required parameter: {field}"}), 400

        sector = data["sector_name"]
        hour = int(data["hour"])
        dow = int(data["day_of_week"])
        temp_c = float(data["temp_c"])
        solar = float(data["solar_wm2"])
        ind_idx = float(data["industrial_idx"])

        # 1. PyTorch Neural Inference
        predicted_mw = model.predict_megawatts(
            hour=hour,
            day_of_week=dow,
            temp_c=temp_c,
            solar_wm2=solar,
            industrial_idx=ind_idx,
        )

        # 2. Dispatch Optimization Rules
        if predicted_mw > 550.0:
            dispatch = "RAMP_PEAKER_PLANTS_AND_BATTERY_DISCHARGE"
        elif predicted_mw < 450.0 and solar > 600.0:
            dispatch = "CURTAIL_SOLAR_CHARGE_GRID_BATTERIES"
        else:
            dispatch = "BASELOAD_COMBINED_CYCLE_OPTIMAL"

        now_iso = datetime.now(timezone.utc).isoformat()

        # 3. SQL Persistence
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO forecast_records (sector_name, hour, temp_c, solar_wm2, predicted_mw, dispatch_decision, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (sector, hour, temp_c, solar, predicted_mw, dispatch, now_iso))
        record_id = cur.lastrowid
        conn.commit()
        conn.close()

        return jsonify({
            "record_id": record_id,
            "sector_name": sector,
            "predicted_load_mw": predicted_mw,
            "dispatch_decision": dispatch,
            "spinning_reserve_target_mw": round(predicted_mw * 0.15, 2),
            "created_at": now_iso,
        }), 200

    @app.route("/api/v1/sectors/<string:sector_name>/history", methods=["GET"])
    def get_history(sector_name):
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("""
            SELECT id, hour, temp_c, solar_wm2, predicted_mw, dispatch_decision, created_at
            FROM forecast_records
            WHERE sector_name = ?
            ORDER BY id DESC LIMIT 10
        """, (sector_name,))
        rows = cur.fetchall()
        conn.close()

        results = [
            {
                "id": r[0],
                "hour": r[1],
                "temp_c": r[2],
                "solar_wm2": r[3],
                "predicted_mw": r[4],
                "dispatch_decision": r[5],
                "created_at": r[6],
            } for r in rows
        ]
        return jsonify({"sector_name": sector_name, "records": results}), 200

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=5050, debug=True)
