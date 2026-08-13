"""One failing block must not take the rest of the poll with it.

The upstream integration reads its blocks independently and tolerates a failure
(``auto_block_ignore_readerror=True``): the failing block's sensors keep their
last values while everything else refreshes. The library mirrors that at
sub-system granularity.
"""

from __future__ import annotations

import pytest
from modbus_connection import ModbusConnectionError, ModbusTimeoutError
from modbus_connection.mock import MockModbusUnit

from viessmann_modbus import ViessmannHybridInverter


async def test_a_failed_sub_system_leaves_the_rest_fresh(
    device: ViessmannHybridInverter, seeded_unit: MockModbusUnit
) -> None:
    assert device.battery is not None
    before = device.inverter.load_power

    seeded_unit.holding[35171] = [0, 1500]  # load power changes on the device
    seeded_unit.holding[35103] = 3300  # so does PV string 1 voltage
    seeded_unit.holding[37007] = 80  # and the battery's SoC
    seeded_unit.fail_read(35169, ModbusTimeoutError("slow load block"))
    report = await device.async_update()

    assert not report.complete
    assert set(report.failed) == {"inverter"}
    assert isinstance(report.failed["inverter"], ModbusTimeoutError)
    assert {"meter", "battery", "bms", "settings"} <= report.updated
    assert device.battery.soc == 80
    assert device.inverter.load_power == before
    # The whole sub-system is held back, not just the block that failed: the
    # 35103 block was read before the failure but its value is never stored.
    assert device.inverter.pv_voltage_1 == 325.1


async def test_listeners_fire_at_the_end_and_only_for_fresh_components(
    device: ViessmannHybridInverter, seeded_unit: MockModbusUnit
) -> None:
    assert device.settings is not None
    seen: list[int] = []
    device.settings.add_update_listener(
        lambda: seen.append(len(seeded_unit.read_events))
    )
    device.inverter.add_update_listener(lambda: seen.append(-1))

    seeded_unit.fail_read(35169, ModbusTimeoutError("slow load block"))
    seeded_unit.read_events.clear()
    await device.async_update()

    # One notification, after every sub-system was tried; none for the failure.
    assert seen == [len(seeded_unit.read_events)]


async def test_a_dead_link_raises_instead_of_reporting(
    device: ViessmannHybridInverter, seeded_unit: MockModbusUnit
) -> None:
    seeded_unit.fail_requests(ModbusConnectionError("link down"))
    with pytest.raises(ModbusConnectionError):
        await device.async_update()


async def test_every_sub_system_refreshes_on_a_healthy_device(
    device: ViessmannHybridInverter,
) -> None:
    report = await device.async_update()
    assert report.complete
    assert report.failed == {}
    assert report.updated == {"inverter", "meter", "battery", "bms", "settings"}


async def test_a_failed_sub_system_is_polled_again_next_time(
    device: ViessmannHybridInverter, seeded_unit: MockModbusUnit
) -> None:
    """A poll failure says nothing about whether the sub-system exists."""
    assert device.battery is not None
    seeded_unit.fail_read(37002, ModbusTimeoutError("slow battery block"))
    assert set((await device.async_update()).failed) == {"battery"}

    seeded_unit.fail_read(37002, None)
    seeded_unit.holding[37007] = 80
    report = await device.async_update()

    assert report.complete
    assert device.battery.soc == 80
