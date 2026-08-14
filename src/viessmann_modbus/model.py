"""Viessmann-specific pieces layered on the ``modbus_connection.model`` framework.

The inverter serves everything from the holding-register space (FC03) — there
are no input registers, coils or discrete inputs — and stores 32-bit values in
big-endian word order, which is the framework default.
"""

from __future__ import annotations

from dataclasses import dataclass

from modbus_connection import ModbusError
from modbus_connection.model import Component, NumberField

from .ranges import MAX_READ_SPAN, REGISTER_RANGES


class ViessmannComponent(Component):
    """A sub-system: the inverter's readable ranges plus its read-width cap."""

    register_ranges = REGISTER_RANGES
    max_span = MAX_READ_SPAN


@dataclass(frozen=True)
class UpdateReport:
    """What one poll refreshed, by the device's sub-system attribute names.

    A failed sub-system kept its previous values and did not notify; the error
    that failed it rides along. A dead link is never in here — the update
    raises ``ModbusConnectionError`` instead of reporting partial silence, and
    a timeout with nothing answered yet raises just the same.
    """

    updated: set[str]
    failed: dict[str, ModbusError]

    @property
    def complete(self) -> bool:
        """Whether every polled sub-system refreshed."""
        return not self.failed


def gauge32(
    address: int,
    scale: float,
    *,
    signed: bool = False,
    unit: str | None = None,
) -> NumberField[float]:
    """A scaled 32-bit value over two consecutive registers."""
    return NumberField(address, count=2, signed=signed, scale=scale, unit=unit)
