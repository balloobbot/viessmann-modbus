"""One failing block must not take the rest of the poll with it.

The upstream integration reads its blocks independently and tolerates a failure
(``auto_block_ignore_readerror=True``): the failing block's sensors keep their
last values while everything else refreshes. The library mirrors that at
sub-system granularity.
"""

from __future__ import annotations

import pytest
from modbus_connection import (
    ModbusConnectionError,
    ModbusTimeoutError,
    ServerDeviceBusyError,
)
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
    seeded_unit.fail_read(35169, ServerDeviceBusyError())
    report = await device.async_update()

    assert not report.complete
    assert set(report.failed) == {"inverter"}
    assert isinstance(report.failed["inverter"], ServerDeviceBusyError)
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

    seeded_unit.fail_read(35169, ServerDeviceBusyError())
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


async def test_a_timeout_with_nothing_answered_raises(
    device: ViessmannHybridInverter, seeded_unit: MockModbusUnit
) -> None:
    """A silent device must not be walked sub-system by sub-system.

    The first sub-system polled is the probe: with no refresh and no refusal
    behind it, a timeout there means the device is gone, and carrying on would
    only pay four more of them.
    """
    seeded_unit.fail_read(35103, ModbusTimeoutError("device asleep"))
    with pytest.raises(ModbusTimeoutError):
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


async def test_a_busy_probe_does_not_latch_a_sub_system_as_absent(
    seeded_unit: MockModbusUnit,
) -> None:
    """Only a refused address proves absence; a busy device is transient.

    Setup propagates the error rather than recording the battery as missing,
    so the device stays unset up and the next update probes it again.
    """
    seeded_unit.fail_read(37002, ServerDeviceBusyError())
    device = ViessmannHybridInverter(seeded_unit)
    with pytest.raises(ServerDeviceBusyError):
        await device.async_update()

    seeded_unit.fail_read(37002, None)
    report = await device.async_update()

    assert device.battery is not None
    assert device.battery.soc == 74
    assert "battery" in report.updated
