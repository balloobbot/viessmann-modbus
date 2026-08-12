"""The top-level Viessmann inverter object."""

from __future__ import annotations

from typing import TYPE_CHECKING

from modbus_connection import ModbusExceptionError
from modbus_connection.model import Component, ComponentGroup

from .battery import Battery
from .bms import RealtimeBms
from .device_info import DeviceInfo
from .inverter import Inverter
from .meter import Meter
from .settings import Settings

if TYPE_CHECKING:
    from modbus_connection import ModbusUnit


async def _optional[C: Component](component: C) -> C | None:
    """Read a sub-system that not every installation has; ``None`` if absent."""
    try:
        await component.async_update()
    except ModbusExceptionError:
        return None
    return component


class ViessmannHybridInverter:
    """A Viessmann hybrid inverter (GoodWe-compatible map) behind a ``ModbusUnit``.

    Validated upstream against a HINV6.0-B1 over Modbus TCP, which answers on
    unit id 247 by default::

        device = ViessmannHybridInverter(unit)
        await device.async_update()
        device.info.model
        device.inverter.pv_power_1
        device.inverter.work_mode
        if device.battery is not None:
            device.battery.soc

    ASCII framing is not supported — give this class a unit from an RTU or
    TCP/MBAP connection.

    :attr:`info` is read once during setup and never polled again. The meter,
    battery, BMS and settings blocks are absent on some installations, so setup
    probes them and a poll refreshes only the ones that answered.
    """

    def __init__(self, unit: ModbusUnit) -> None:
        self._unit = unit
        self.info = DeviceInfo(unit)
        self.inverter = Inverter(unit)
        # Settled by async_setup(), which probes for each of them.
        self.meter: Meter | None = None
        self.battery: Battery | None = None
        self.bms: RealtimeBms | None = None
        self.settings: Settings | None = None
        self._group: ComponentGroup | None = None

    @property
    def polled_components(self) -> tuple[Component, ...]:
        """The sub-systems a poll refreshes."""
        return (
            self.inverter,
            *(c for c in (self.meter, self.battery, self.bms, self.settings) if c),
        )

    async def async_setup(self) -> None:
        """Read the identity registers and settle which sub-systems exist.

        Run by the first :meth:`async_update` if the caller does not run it
        itself. A failure leaves the device unset up, so the next update retries.
        """
        await self.info.async_update()
        self.meter = await _optional(Meter(self._unit))
        self.battery = await _optional(Battery(self._unit))
        self.bms = await _optional(RealtimeBms(self._unit))
        self.settings = await _optional(Settings(self._unit))
        self._group = ComponentGroup(self._unit, list(self.polled_components))

    async def async_update(self) -> None:
        """Refresh every present sub-system in one pooled set of block reads."""
        if self._group is None:
            await self.async_setup()
        assert self._group is not None  # async_setup() always builds it
        await self._group.async_update()
