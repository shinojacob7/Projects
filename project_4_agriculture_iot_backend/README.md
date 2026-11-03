# AgroScale: Distributed IoT Telemetry & Automated Irrigation Rule Engine (Core SDE / Backend)

## High-Impact Resume Bullets
* Architected a high-throughput IoT telemetry ingestion backend using Python OOP, Flask, and SQLAlchemy, persisting multi-zone environmental sensors and actuator event streams.
* Engineered an agronomic decision engine computing real-time atmospheric Vapor Pressure Deficit (VPD) and soil depletion rates, triggering automated valve dispatches.
* Implemented pump motor debounce protection mechanisms preventing rapid-cycle burnout, coupled with manual operator override audit logging.
* Verified with comprehensive pytest suites (in-memory SQLite transaction isolation) and a 3-zone dry-run simulation across varying crop types and drought conditions.
