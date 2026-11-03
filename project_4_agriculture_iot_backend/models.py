"""
Relational Database Models for AgroScale IoT Irrigation Engine.
Built with SQLAlchemy 2.0 and SQLite.
"""

from datetime import datetime, timezone
from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Float,
    DateTime,
    ForeignKey,
)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

Base = declarative_base()


class FieldZone(Base):
    __tablename__ = "field_zones"

    id = Column(Integer, primary_key=True, autoincrement=True)
    zone_code = Column(String(32), unique=True, nullable=False, index=True)
    crop_type = Column(String(64), nullable=False)
    area_hectares = Column(Float, nullable=False, default=1.0)
    target_moisture_min = Column(Float, nullable=False)  # e.g., 25.0%
    target_moisture_max = Column(Float, nullable=False)  # e.g., 50.0%
    valve_status = Column(String(16), nullable=False, default="CLOSED")  # OPEN / CLOSED
    last_valve_change = Column(DateTime, nullable=True, default=None)

    telemetries = relationship("SensorTelemetry", back_populates="zone", cascade="all, delete-orphan")
    events = relationship("IrrigationEvent", back_populates="zone", cascade="all, delete-orphan")


class SensorTelemetry(Base):
    __tablename__ = "sensor_telemetry"

    id = Column(Integer, primary_key=True, autoincrement=True)
    zone_id = Column(Integer, ForeignKey("field_zones.id"), nullable=False, index=True)
    soil_moisture_pct = Column(Float, nullable=False)
    ambient_temp_c = Column(Float, nullable=False)
    relative_humidity_pct = Column(Float, nullable=False)
    solar_radiation_wm2 = Column(Float, nullable=False, default=450.0)
    recorded_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)

    zone = relationship("FieldZone", back_populates="telemetries")


class IrrigationEvent(Base):
    __tablename__ = "irrigation_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    zone_id = Column(Integer, ForeignKey("field_zones.id"), nullable=False, index=True)
    action = Column(String(16), nullable=False)  # "START" or "STOP"
    reason = Column(String(128), nullable=False)
    water_volume_liters = Column(Float, nullable=False, default=0.0)
    triggered_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)

    zone = relationship("FieldZone", back_populates="events")


def init_db(database_url: str = "sqlite:///agroscale.db"):
    engine = create_engine(database_url, echo=False)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)
