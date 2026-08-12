"""Real-time values the BMS reports to the inverter (47902-47910).

These duplicate part of :class:`~viessmann_modbus.battery.Battery` but are the
BMS's own live view rather than the inverter's cached copy.
"""

from __future__ import annotations

from modbus_connection.model import gauge, integer

from .model import ViessmannComponent


class RealtimeBms(ViessmannComponent):
    """The BMS's live charge/discharge limits and pack measurements."""

    charge_voltage_limit = gauge(47902, 0.1, signed=False, unit="V")
    charge_current_limit = gauge(47903, 0.1, signed=False, unit="A")
    discharge_voltage_limit = gauge(47904, 0.1, signed=False, unit="V")
    discharge_current_limit = gauge(47905, 0.1, signed=False, unit="A")
    battery_voltage = gauge(47906, 0.1, signed=False, unit="V")
    battery_current = gauge(47907, 0.1, signed=False, unit="A")
    soc = integer(47908, signed=False, unit="%")
    soh = integer(47909, signed=False, unit="%")
    temperature = gauge(47910, 0.1, signed=False, unit="°C")
