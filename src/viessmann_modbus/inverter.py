"""The inverter's live measurements and energy counters (35103-35211)."""

from __future__ import annotations

from modbus_connection.model import enum, gauge, int32, uint32

from .enums import BatteryMode, GridMode, WorkMode
from .model import ViessmannComponent, gauge32


class Inverter(ViessmannComponent):
    """PV strings, grid, load, battery and the lifetime energy counters."""

    pv_voltage_1 = gauge(35103, 0.1, signed=False, unit="V")
    pv_current_1 = gauge(35104, 0.1, signed=False, unit="A")
    pv_power_1 = uint32(35105, unit="W")
    pv_voltage_2 = gauge(35107, 0.1, signed=False, unit="V")
    pv_current_2 = gauge(35108, 0.1, signed=False, unit="A")
    pv_power_2 = uint32(35109, unit="W")

    grid_voltage = gauge(35121, 0.1, signed=False, unit="V")
    grid_current = gauge(35122, 0.1, signed=False, unit="A")
    grid_frequency = gauge(35123, 0.01, signed=False, unit="Hz")
    grid_power = int32(35124, unit="W")
    grid_mode = enum(35136, GridMode)

    inverter_power = int32(35137, unit="W")
    ac_active_power = int32(35139, unit="W")

    backup_load_power = int32(35169, unit="W")
    load_power = int32(35171, unit="W")
    backup_load_percent = gauge(35173, 0.01, signed=False, unit="%")

    air_temperature = gauge(35174, 0.1, unit="°C")
    heatsink_temperature = gauge(35176, 0.1, unit="°C")

    battery_voltage = gauge(35180, 0.1, signed=False, unit="V")
    battery_current = gauge(35181, 0.1, unit="A")
    battery_power = int32(35182, unit="W")
    battery_mode = enum(35184, BatteryMode)

    work_mode = enum(35187, WorkMode)
    error_code = uint32(35189)
    """Fault bitmask; see :attr:`error_message` for the hexadecimal form."""

    pv_energy_total = gauge32(35191, 0.1, unit="kWh")
    pv_energy_today = gauge32(35193, 0.1, unit="kWh")
    runtime_total = uint32(35197, unit="h")

    load_energy_total = gauge32(35203, 0.1, unit="kWh")
    load_energy_today = gauge(35205, 0.1, signed=False, unit="kWh")
    battery_charge_energy_total = gauge32(35206, 0.1, unit="kWh")
    battery_charge_energy_today = gauge(35208, 0.1, signed=False, unit="kWh")
    battery_discharge_energy_total = gauge32(35209, 0.1, unit="kWh")
    battery_discharge_energy_today = gauge(35211, 0.1, signed=False, unit="kWh")

    @property
    def error_message(self) -> str | None:
        """:attr:`error_code` as the ``0x········`` string the inverter docs use."""
        code = self.error_code
        return None if code is None else f"0x{code:08x}"
