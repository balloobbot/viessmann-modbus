"""Every field decodes the synthetic register map to its engineering value."""

from __future__ import annotations

from modbus_connection.mock import MockModbusUnit

from viessmann_modbus import (
    BatteryMode,
    BmsStatus,
    DeviceInfo,
    GridMode,
    MeterCommunicationStatus,
    ViessmannHybridInverter,
    WorkMode,
)

from .conftest import ascii_words


async def test_device_info(device: ViessmannHybridInverter) -> None:
    assert device.info.rated_power == 6000
    assert device.info.serial_number == "9010KETU00123"
    assert device.info.model == "HINV6.0-B1"


async def test_strings_strip_ff_padding(seeded_unit: MockModbusUnit) -> None:
    """The inverter pads short strings with 0xFF as well as NUL."""
    seeded_unit.holding[35011] = [*ascii_words("HINV6.0"), 0xFFFF]
    info = DeviceInfo(seeded_unit)
    await info.async_update()
    assert info.model == "HINV6.0"


async def test_pv_strings(device: ViessmannHybridInverter) -> None:
    inverter = device.inverter
    assert inverter.pv_voltage_1 == 325.1
    assert inverter.pv_current_1 == 8.2
    assert inverter.pv_power_1 == 2665
    assert inverter.pv_voltage_2 == 298.0
    assert inverter.pv_current_2 == 5.5
    assert inverter.pv_power_2 == 1639


async def test_grid(device: ViessmannHybridInverter) -> None:
    inverter = device.inverter
    assert inverter.grid_voltage == 230.1
    assert inverter.grid_current == 8.7
    assert inverter.grid_frequency == 49.98
    assert inverter.grid_power == -1250  # signed: negative exports
    assert inverter.grid_mode is GridMode.OK
    assert inverter.inverter_power == 3800
    assert inverter.ac_active_power == 3750


async def test_load_and_temperatures(device: ViessmannHybridInverter) -> None:
    inverter = device.inverter
    assert inverter.backup_load_power == 420
    assert inverter.load_power == 1310
    assert inverter.backup_load_percent == 35.0
    assert inverter.air_temperature == -5.5  # signed
    assert inverter.heatsink_temperature == 41.2


async def test_inverter_side_battery(device: ViessmannHybridInverter) -> None:
    inverter = device.inverter
    assert inverter.battery_voltage == 398.5
    assert inverter.battery_current == -12.3  # signed
    assert inverter.battery_power == -4901  # signed
    assert inverter.battery_mode is BatteryMode.DISCHARGING


async def test_state_and_energy(device: ViessmannHybridInverter) -> None:
    inverter = device.inverter
    assert inverter.work_mode is WorkMode.ON_GRID
    assert inverter.error_code == 0x00010040
    assert inverter.error_message == "0x00010040"
    assert inverter.pv_energy_total == 4123.4
    assert inverter.pv_energy_today == 15.2
    assert inverter.runtime_total == 8760
    assert inverter.load_energy_total == 3001.2
    assert inverter.load_energy_today == 9.1
    assert inverter.battery_charge_energy_total == 1500.3
    assert inverter.battery_charge_energy_today == 3.4
    assert inverter.battery_discharge_energy_total == 1400.1
    assert inverter.battery_discharge_energy_today == 2.8


async def test_meter(device: ViessmannHybridInverter) -> None:
    assert device.meter is not None
    assert device.meter.communication_status is MeterCommunicationStatus.OK
    assert device.meter.grid_export_energy_total == 1234.567  # float32 Wh -> kWh
    assert device.meter.grid_import_energy_total == 2345.678
    assert device.meter.active_power == -820  # signed


async def test_battery(device: ViessmannHybridInverter) -> None:
    assert device.battery is not None
    assert device.battery.bms_status is BmsStatus.NORMAL
    assert device.battery.soc == 74
    assert device.battery.soh == 99
    assert device.battery.max_cell_temperature == 23.1
    assert device.battery.min_cell_temperature == 22.0
    assert device.battery.max_cell_voltage == 3312
    assert device.battery.min_cell_voltage == 3298


async def test_realtime_bms(device: ViessmannHybridInverter) -> None:
    assert device.bms is not None
    assert device.bms.charge_voltage_limit == 548.0
    assert device.bms.charge_current_limit == 25.0
    assert device.bms.discharge_voltage_limit == 440.0
    assert device.bms.discharge_current_limit == 30.0
    assert device.bms.battery_voltage == 398.5
    assert device.bms.battery_current == 12.3
    assert device.bms.soc == 74
    assert device.bms.soh == 99
    assert device.bms.temperature == 23.5


async def test_settings(device: ViessmannHybridInverter) -> None:
    assert device.settings is not None
    assert device.settings.configured_modbus_address == 247


async def test_unknown_enum_code_decodes_to_none(
    seeded_unit: MockModbusUnit,
) -> None:
    seeded_unit.holding[35187] = 99
    device = ViessmannHybridInverter(seeded_unit)
    await device.async_update()
    assert device.inverter.work_mode is None


async def test_values_are_none_before_the_first_read(
    seeded_unit: MockModbusUnit,
) -> None:
    device = ViessmannHybridInverter(seeded_unit)
    assert device.inverter.pv_voltage_1 is None
    assert device.info.model is None
