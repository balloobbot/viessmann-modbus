"""Static identity registers (35001-35015)."""

from __future__ import annotations

from modbus_connection.model import integer, string

from .model import ViessmannComponent


def _clean(value: str | None) -> str | None:
    """Strip the 0x00/0xFF padding the inverter pads short strings with."""
    if value is None:
        return None
    cleaned = value.replace("\x00", "").replace("\xff", "").strip()
    return cleaned or None


class DeviceInfo(ViessmannComponent):
    """Rated power, serial number and model name — read once, never polled."""

    rated_power = integer(35001, signed=False, unit="W")
    """Nameplate rated AC power."""

    _serial_number = string(35003, 8)
    _model = string(35011, 5)

    @property
    def serial_number(self) -> str | None:
        """Inverter serial number."""
        return _clean(self._serial_number)

    @property
    def model(self) -> str | None:
        """Inverter model name, e.g. ``HINV6.0-B1``."""
        return _clean(self._model)
