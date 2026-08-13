"""What a poll actually asks the inverter for.

The upstream integration splits this map into 24 blocks — 3 identity, 8 in its
fast scan group and 13 in its medium one — capped at a start offset of 8
registers. This library drops the scan groups, so a full poll is those blocks
with the adjacent fast/medium pairs merged: every read below is either one of
the plugin's blocks or the union of neighbouring ones, and none is wider than
the widest read the plugin issues.

Reads are grouped by sub-system, each planned on its own so that one failing
block only holds back its own sub-system. The blocks are the same ones a single
pooled plan produced — the sub-systems own disjoint address ranges, so nothing
merges across them — but they come in sub-system order rather than address
order, which is why `settings` (45127) reads after `bms` (47902).
"""

from __future__ import annotations

from modbus_connection.mock import MockModbusUnit

from viessmann_modbus import MAX_READ_SPAN, REGISTER_RANGES, ViessmannHybridInverter

from .conftest import HOLDING

# (address, count) per read, in order.
EXPECTED_POLL = [
    (35103, 8),  # PV strings 1 and 2
    (35121, 5),  # grid voltage/current/frequency/power
    (35136, 5),  # grid mode + inverter and AC power
    (35169, 8),  # backup/load power, load percent, temperatures
    (35180, 5),  # battery voltage/current/power/mode
    (35187, 8),  # work mode, error code, PV energy total/today
    (35197, 9),  # runtime, load energy total/today
    (35206, 6),  # battery charge/discharge energy counters
    (36004, 1),  # meter communication status
    (36015, 4),  # meter grid export/import totals
    (36025, 2),  # meter active power
    (37002, 7),  # BMS status, SoC, SoH
    (37020, 4),  # cell extremes
    (47902, 9),  # real-time BMS block
    (45127, 1),  # configured Modbus address
]


def seeded_addresses() -> set[int]:
    """Every register the synthetic map fills — one per declared field word."""
    addresses: set[int] = set()
    for address, value in HOLDING.items():
        span = len(value) if isinstance(value, list) else 1
        addresses.update(range(address, address + span))
    return addresses


def blocks(unit: MockModbusUnit) -> list[tuple[int, int]]:
    return [(event.address, event.count) for event in unit.read_events]


async def test_poll_read_pattern(
    device: ViessmannHybridInverter, seeded_unit: MockModbusUnit
) -> None:
    seeded_unit.read_events.clear()
    await device.async_update()
    assert blocks(seeded_unit) == EXPECTED_POLL


async def test_poll_reuses_its_plan(
    device: ViessmannHybridInverter, seeded_unit: MockModbusUnit
) -> None:
    seeded_unit.read_events.clear()
    await device.async_update()
    first = blocks(seeded_unit)
    seeded_unit.read_events.clear()
    await device.async_update()
    assert blocks(seeded_unit) == first


async def test_every_read_is_holding(
    device: ViessmannHybridInverter, seeded_unit: MockModbusUnit
) -> None:
    seeded_unit.read_events.clear()
    await device.async_update()
    assert {event.register_type for event in seeded_unit.read_events} == {"holding"}


async def test_reads_stay_inside_the_declared_ranges(
    device: ViessmannHybridInverter, seeded_unit: MockModbusUnit
) -> None:
    """No read may bridge a gap the inverter does not map."""
    seeded_unit.read_events.clear()
    await device.async_update()
    for event in seeded_unit.read_events:
        last = event.address + event.count - 1
        assert any(
            low <= event.address and last <= high for low, high in REGISTER_RANGES
        ), f"read {event.address}-{last} crosses a range boundary"


async def test_reads_respect_the_width_cap(
    device: ViessmannHybridInverter, seeded_unit: MockModbusUnit
) -> None:
    seeded_unit.read_events.clear()
    await device.async_update()
    assert max(event.count for event in seeded_unit.read_events) <= MAX_READ_SPAN


async def test_the_unmapped_span_is_never_read(
    device: ViessmannHybridInverter, seeded_unit: MockModbusUnit
) -> None:
    """35016-35102 sits between two ranges and must stay untouched."""
    seeded_unit.read_events.clear()
    await device.async_update()
    read = {
        address
        for event in seeded_unit.read_events
        for address in range(event.address, event.address + event.count)
    }
    assert not read & set(range(35016, 35103))


async def test_every_field_is_read(device: ViessmannHybridInverter) -> None:
    """A poll plus setup covers every register the library declares."""
    covered: set[int] = set()
    for component in (
        device.info,
        device.inverter,
        device.meter,
        device.battery,
        device.bms,
        device.settings,
    ):
        assert component is not None
        raw = await component.async_read_raw()
        covered.update(raw["holding"])
    assert seeded_addresses() <= covered


async def test_a_solo_component_reads_only_its_own_registers(
    seeded_unit: MockModbusUnit, device: ViessmannHybridInverter
) -> None:
    assert device.battery is not None
    seeded_unit.read_events.clear()
    await device.battery.async_update()
    assert blocks(seeded_unit) == [(37002, 7), (37020, 4)]
