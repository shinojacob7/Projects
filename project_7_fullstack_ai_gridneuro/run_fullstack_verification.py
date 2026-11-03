"""
Orchestrates Verification 2 for Project 7: Full-Stack AI Product.
Spawns Flask PyTorch backend server, runs Dart frontend HTTP client against it, and asserts roundtrip completion.
"""

import sys
import time
import threading
import subprocess
import requests
from backend.app import create_app


def start_flask_server():
    app = create_app(db_path="gridneuro_fullstack.db")
    app.run(host="127.0.0.1", port=5050, debug=False, use_reloader=False)


def main():
    print("==========================================================================")
    print("PROJECT 7: FULL-STACK AI PRODUCT INTEGRATION / DRY RUN (GRIDNEURO)")
    print("==========================================================================\n")

    print("[Step 1] Booting Flask Backend & Loading PyTorch Neural Forecaster on Port 5050...")
    server_thread = threading.Thread(target=start_flask_server, daemon=True)
    server_thread.start()

    # Poll health endpoint until online
    for _ in range(15):
        try:
            r = requests.get("http://127.0.0.1:5050/api/v1/health", timeout=1)
            if r.status_code == 200:
                print("  -> Flask Backend + PyTorch Service is HEALTHY and READY.")
                break
        except Exception:
            time.sleep(0.5)
    else:
        print("Failed to start Flask server.")
        sys.exit(1)

    print("\n[Step 2] Spawning Dart/Flutter Frontend Client to Execute HTTP Request...")
    cmd = ["dart", "run", "test/integration_dry_run.dart"]
    result = subprocess.run(cmd, cwd="frontend", capture_output=True, text=True, shell=True)

    print(result.stdout)
    if result.stderr:
        print("Client stderr:", result.stderr)

    assert result.returncode == 0, f"Dart Client failed with return code {result.returncode}"

    print("[Step 3] Verifying Database Record Persistence in SQLite...")
    import sqlite3
    conn = sqlite3.connect("gridneuro_fullstack.db")
    cur = conn.cursor()
    cur.execute("SELECT id, sector_name, predicted_mw, dispatch_decision FROM forecast_records ORDER BY id DESC LIMIT 1")
    row = cur.fetchone()
    conn.close()

    print(f"  -> SQLite Verified: Record #{row[0]} | Sector: {row[1]} | AI Load: {row[2]} MW | Decision: {row[3]}")

    print("\n==========================================================================")
    print("FULL-STACK AI DRY RUN PIPELINE COMPLETED WITH 0 ERRORS.")
    print("==========================================================================")


if __name__ == "__main__":
    main()
