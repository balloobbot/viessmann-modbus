"""Communication settings (45127)."""

from __future__ import annotations

from modbus_connection.model import integer

from .model import ViessmannComponent


class Settings(ViessmannComponent):
    """The inverter's own view of its Modbus configuration."""

    configured_modbus_address = integer(45127, signed=False)
    """Unit id the inverter answers on; 247 out of the box."""
