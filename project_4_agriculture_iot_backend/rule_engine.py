"""
Agronomic IoT Rule Engine & Actuator Control Logic.
Computes Vapor Pressure Deficit (VPD), moisture depletion, and pump debounce protection.
"""

import math
from datetime import datetime, timezone
from typing import Optional, Tuple
from models import FieldZone, SensorTelemetry


class AgronomicRuleEngine:
    MIN_VALVE_DWELL_SECONDS = 300  # 5-minute debounce window for pump motor safety

    @staticmethod
    def calculate_vpd(temp_c: float, humidity_pct: float) -> float:
        """
        Calculates atmospheric Vapor Pressure Deficit (VPD) in kilopascals (kPa)
        using the Tetens equation.
        """
        # Saturated vapor pressure (kPa)
        es = 0.61078 * math.exp((17.27 * temp_c) / (temp_c + 237.3))
        # Actual vapor pressure
        ea = es * (max(0.0, min(100.0, humidity_pct)) / 100.0)
        vpd = max(0.0, es - ea)
        return round(vpd, 3)

    @classmethod
    def evaluate_telemetry(
        cls,
        zone: FieldZone,
        telemetry: SensorTelemetry,
        current_time: Optional[datetime] = None,
    ) -> Optional[Tuple[str, str, float]]:
        """
        Evaluates sensor readings against crop threshold rules.
        Returns: Optional tuple (action: "START"|"STOP", reason: str, water_liters: float)
        """
        now = current_time or datetime.now(timezone.utc)

        # Enforce debounce window to prevent valve cycling
        if zone.last_valve_change is not None:
            last_change = zone.last_valve_change
            # Normalize naive / aware timestamps from SQLite
            if last_change.tzinfo is None and now.tzinfo is not None:
                last_change = last_change.replace(tzinfo=timezone.utc)
            elif last_change.tzinfo is not None and now.tzinfo is None:
                now = now.replace(tzinfo=timezone.utc)

            dwell_duration = (now - last_change).total_seconds()
            if dwell_duration < cls.MIN_VALVE_DWELL_SECONDS:
                return None  # Debounce lock active; prevent short-cycling

        vpd = cls.calculate_vpd(telemetry.ambient_temp_c, telemetry.relative_humidity_pct)
        moisture = telemetry.soil_moisture_pct

        # Rule 1: Saturated soil ceiling reached -> STOP valve
        if zone.valve_status == "OPEN" and moisture >= zone.target_moisture_max:
            return ("STOP", f"Soil moisture reached target saturation ceiling ({moisture:.1f}% >= {zone.target_moisture_max:.1f}%)", 0.0)

        # Rule 2: Critical drought / High atmospheric evaporative demand -> START valve
        if zone.valve_status == "CLOSED" and moisture < zone.target_moisture_min:
            deficit_pct = zone.target_moisture_max - moisture
            # Liters = area_hectares * 10,000 m2 * 0.15m root depth * deficit_fraction * 1000 L/m3
            water_needed = zone.area_hectares * 10000.0 * 0.15 * (deficit_pct / 100.0) * 1000.0

            if vpd > 1.6:
                reason = f"Urgent drought relief: high atmospheric VPD ({vpd:.2f} kPa) & low moisture ({moisture:.1f}%)"
            else:
                reason = f"Soil moisture below threshold ({moisture:.1f}% < {zone.target_moisture_min:.1f}%)"

            return ("START", reason, round(water_needed, 1))

        return None
