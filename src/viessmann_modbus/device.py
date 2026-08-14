"""The top-level Viessmann inverter object."""

from __future__ import annotations

from typing import TYPE_CHECKING

from modbus_connection import (
    IllegalDataAddressError,
    IllegalFunctionError,
    ModbusConnectionError,
    ModbusError,
)
from modbus_connection.model import Component

from .battery import Battery
from .bms import RealtimeBms
from .device_info import DeviceInfo
from .inverter import Inverter
from .meter import Meter
from .model import UpdateReport
from .settings import Settings

if TYPE_CHECKING:
    from modbus_connection import ModbusUnit

# Every sub-system attribute a poll may refresh, in read order.
_POLLED = ("inverter", "meter", "battery", "bms", "settings")


async def _optional[C: Component](component: C) -> C | None:
    """Read a sub-system that not every installation has; ``None`` if absent.

    Only a refusal of the address itself proves absence. Anything else — a
    timeout, a busy device — is transient, and propagates so that setup is
    retried rather than recording the sub-system as missing for good.
    """
    try:
        await component.async_update()
    except (IllegalDataAddressError, IllegalFunctionError):
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

    Sub-systems are read one at a time, so a sub-system whose read fails keeps
    its previous values while the rest still refresh — see :meth:`async_update`.
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
        self._polled: list[str] | None = None

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
        self._polled = [name for name in _POLLED if getattr(self, name) is not None]

    async def async_update(self) -> UpdateReport:
        """Refresh every present sub-system, one at a time.

        A sub-system whose read fails keeps its previous values and is named in
        the report with its error, while the rest still refresh. Listeners fire
        only after every sub-system has been tried, and only on the ones that
        refreshed. A failure of the link itself raises ``ModbusConnectionError``
        instead of reporting.
        """
        if self._polled is None:
            await self.async_setup()
        assert self._polled is not None  # async_setup() builds it
        updated: set[str] = set()
        failed: dict[str, ModbusError] = {}
        for name in self._polled:
            component: Component = getattr(self, name)
            try:
                await component.async_update(notify=False)
            except ModbusConnectionError:
                raise
            except ModbusError as err:
                failed[name] = err
            else:
                updated.add(name)
        for name in updated:
            fresh: Component = getattr(self, name)
            fresh.notify()
        return UpdateReport(updated, failed)

    async def async_read_raw(self) -> dict[str, dict[int, int | bool]]:
        """Every register this device reads, undecoded — for diagnostics.

        Covers :attr:`info`, which only setup reads, as well as the polled
        sub-systems, so a dump carries the registers naming the inverter. Left
        out are the blocks this installation does not have. The first call sets
        the device up.

        The fields refresh, but no listener fires: a dump is not a poll.
        """
        if self._polled is None:
            await self.async_setup()
        assert self._polled is not None  # async_setup() builds it
        raw: dict[str, dict[int, int | bool]] = {}
        for name in ("info", *self._polled):
            component: Component = getattr(self, name)
            for space, values in (await component.async_read_raw(notify=False)).items():
                raw.setdefault(space, {}).update(values)
        return raw
