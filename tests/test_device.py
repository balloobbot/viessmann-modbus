"""Setup, optional sub-systems, and the read-only nature of the map."""

from __future__ import annotations

import pytest
from modbus_connection import IllegalDataAddressError, ModbusTimeoutError
from modbus_connection.mock import MockModbusUnit
from modbus_connection.model import Component

from viessmann_modbus import (
    Battery,
    DeviceInfo,
    Inverter,
    Meter,
    RealtimeBms,
    Settings,
    ViessmannHybridInverter,
)


async def test_setup_finds_every_sub_system(device: ViessmannHybridInverter) -> None:
    assert device.meter is not None
    assert device.battery is not None
    assert device.bms is not None
    assert device.settings is not None
    assert len(device.polled_components) == 5


async def test_an_installation_without_a_battery(seeded_unit: MockModbusUnit) -> None:
    """A refused block drops that sub-system instead of failing every poll."""
    seeded_unit.fail_read(37002, IllegalDataAddressError())
    device = ViessmannHybridInverter(seeded_unit)
    await device.async_update()

    assert device.battery is None
    assert device.meter is not None
    assert device.inverter.pv_voltage_1 == 325.1


async def test_an_installation_without_a_meter(seeded_unit: MockModbusUnit) -> None:
    seeded_unit.fail_read(36015, IllegalDataAddressError())
    device = ViessmannHybridInverter(seeded_unit)
    await device.async_update()

    assert device.meter is None
    assert device.battery is not None


async def test_an_unreachable_device_raises(seeded_unit: MockModbusUnit) -> None:
    """A transport failure is not an absent sub-system: it must propagate."""
    seeded_unit.fail_requests(ModbusTimeoutError())
    device = ViessmannHybridInverter(seeded_unit)
    with pytest.raises(ModbusTimeoutError):
        await device.async_update()


async def test_setup_retries_after_a_failure(seeded_unit: MockModbusUnit) -> None:
    seeded_unit.fail_requests(ModbusTimeoutError())
    device = ViessmannHybridInverter(seeded_unit)
    with pytest.raises(ModbusTimeoutError):
        await device.async_update()

    seeded_unit.fail_requests(None)
    await device.async_update()
    assert device.info.model == "HINV6.0-B1"


async def test_listeners_fire_per_sub_system(device: ViessmannHybridInverter) -> None:
    seen: list[str] = []
    device.inverter.add_update_listener(lambda: seen.append("inverter"))
    assert device.battery is not None
    device.battery.add_update_listener(lambda: seen.append("battery"))

    await device.async_update()
    assert sorted(seen) == ["battery", "inverter"]


@pytest.mark.parametrize(
    "component",
    [DeviceInfo, Inverter, Meter, Battery, RealtimeBms, Settings],
)
def test_no_field_is_writable(component: type[Component]) -> None:
    """The upstream plugin defines no numbers, selects or switches: read-only."""
    fields = [value for value in vars(component).values() if hasattr(value, "writable")]
    assert fields  # the component declares something
    assert not any(field.writable for field in fields)
