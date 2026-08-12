"""viessmann-modbus — read a Viessmann hybrid inverter over Modbus.

Construct :class:`ViessmannHybridInverter` with a ``modbus_connection.ModbusUnit``,
call ``await device.async_update()``, then read its sub-systems as normal Python
objects::

    device.info.model
    device.inverter.pv_power_1
    device.inverter.work_mode
    device.meter.grid_import_energy_total
    device.battery.soc

The register map is the GoodWe-compatible one the Viessmann B1 hybrid inverters
expose, taken from the ``plugin_viessmann.py`` register map of
`homeassistant-solax-modbus <https://github.com/wills106/homeassistant-solax-modbus>`_
(Apache-2.0). Everything lives in the holding-register space (FC03).

ASCII-over-TCP framing is not supported.
"""

from .battery import Battery
from .bms import RealtimeBms
from .device import ViessmannHybridInverter
from .device_info import DeviceInfo
from .enums import (
    BatteryMode,
    BmsStatus,
    GridMode,
    MeterCommunicationStatus,
    WorkMode,
)
from .inverter import Inverter
from .meter import Meter
from .model import ViessmannComponent
from .ranges import MAX_READ_SPAN, REGISTER_RANGES
from .settings import Settings

__all__ = [
    "MAX_READ_SPAN",
    "REGISTER_RANGES",
    "Battery",
    "BatteryMode",
    "BmsStatus",
    "DeviceInfo",
    "GridMode",
    "Inverter",
    "Meter",
    "MeterCommunicationStatus",
    "RealtimeBms",
    "Settings",
    "ViessmannComponent",
    "ViessmannHybridInverter",
    "WorkMode",
]
