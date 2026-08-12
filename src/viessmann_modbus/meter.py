"""The external energy meter the inverter reads (36004-36026)."""

from __future__ import annotations

from modbus_connection.model import enum, float32, int32

from .enums import MeterCommunicationStatus
from .model import ViessmannComponent


class Meter(ViessmannComponent):
    """Grid-side meter: import/export counters and instantaneous power."""

    communication_status = enum(36004, MeterCommunicationStatus)
    grid_export_energy_total = float32(36015, scale=0.001, unit="kWh")
    grid_import_energy_total = float32(36017, scale=0.001, unit="kWh")
    active_power = int32(36025, unit="W")
    """Grid-side power; positive imports from the grid."""
