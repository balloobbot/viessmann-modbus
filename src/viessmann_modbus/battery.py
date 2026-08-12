"""Battery pack state as the inverter reports it (37002-37023)."""

from __future__ import annotations

from modbus_connection.model import enum, gauge, integer

from .enums import BmsStatus
from .model import ViessmannComponent


class Battery(ViessmannComponent):
    """State of charge/health and the pack's cell extremes."""

    bms_status = enum(37002, BmsStatus)
    soc = integer(37007, signed=False, unit="%")
    soh = integer(37008, signed=False, unit="%")
    max_cell_temperature = gauge(37020, 0.1, signed=False, unit="°C")
    min_cell_temperature = gauge(37021, 0.1, signed=False, unit="°C")
    max_cell_voltage = integer(37022, signed=False, unit="mV")
    min_cell_voltage = integer(37023, signed=False, unit="mV")
