"""Fixtures: a Viessmann inverter over modbus-connection's in-memory mock backend.

The mock backend (and its ``mock_modbus_unit`` fixture) ship with
``modbus-connection`` as an auto-registered pytest plugin, so there is no real
server or socket here — just an address-keyed store seeded with inverter-shaped
values. Everything on this device is a holding register.
"""

from __future__ import annotations

import struct

import pytest
from modbus_connection.mock import MockModbusUnit

from viessmann_modbus import ViessmannHybridInverter


def ascii_words(text: str) -> list[int]:
    """Pack ASCII into 16-bit registers, two chars per register (hi, lo)."""
    if len(text) % 2:
        text += "\0"
    return [(ord(text[i]) << 8) | ord(text[i + 1]) for i in range(0, len(text), 2)]


def u32(value: int) -> list[int]:
    """Split an unsigned 32-bit value into two big-endian-ordered words."""
    return [(value >> 16) & 0xFFFF, value & 0xFFFF]


def s32(value: int) -> list[int]:
    """Split a signed 32-bit value into two big-endian-ordered words."""
    return u32(value & 0xFFFFFFFF)


def s16(value: int) -> int:
    """Two's-complement a signed 16-bit value into one register word."""
    return value & 0xFFFF


def f32(value: float) -> list[int]:
    """Split an IEEE-754 single into two big-endian-ordered words."""
    hi, lo = struct.unpack(">HH", struct.pack(">f", value))
    return [hi, lo]


# Raw holding-register words keyed by address; the decoded value is in the
# comment. Covers every field the library declares.
HOLDING: dict[int, int | list[int]] = {
    # -- identity --
    35001: 6000,  # rated power 6000 W
    35003: ascii_words("9010KETU00123\0\0\0"),  # serial, NUL-padded
    35011: ascii_words("HINV6.0-B1"),  # model
    # -- PV strings --
    35103: 3251,  # 325.1 V
    35104: 82,  # 8.2 A
    35105: u32(2665),  # 2665 W
    35107: 2980,  # 298.0 V
    35108: 55,  # 5.5 A
    35109: u32(1639),  # 1639 W
    # -- grid --
    35121: 2301,  # 230.1 V
    35122: 87,  # 8.7 A
    35123: 4998,  # 49.98 Hz
    35124: s32(-1250),  # -1250 W (exporting)
    35136: 1,  # GridMode.OK
    35137: s32(3800),  # 3800 W
    35139: s32(3750),  # 3750 W
    # -- load --
    35169: s32(420),  # 420 W
    35171: s32(1310),  # 1310 W
    35173: 3500,  # 35.0 %
    35174: s16(-55),  # -5.5 °C
    35176: 412,  # 41.2 °C
    # -- battery, inverter side --
    35180: 3985,  # 398.5 V
    35181: s16(-123),  # -12.3 A
    35182: s32(-4901),  # -4901 W
    35184: 2,  # BatteryMode.DISCHARGING
    # -- state and energy --
    35187: 1,  # WorkMode.ON_GRID
    35189: u32(0x00010040),  # error code
    35191: u32(41234),  # 4123.4 kWh
    35193: u32(152),  # 15.2 kWh
    35197: u32(8760),  # 8760 h
    35203: u32(30012),  # 3001.2 kWh
    35205: 91,  # 9.1 kWh
    35206: u32(15003),  # 1500.3 kWh
    35208: 34,  # 3.4 kWh
    35209: u32(14001),  # 1400.1 kWh
    35211: 28,  # 2.8 kWh
    # -- meter --
    36004: 1,  # MeterCommunicationStatus.OK
    36015: f32(1234567.0),  # 1234.567 kWh
    36017: f32(2345678.0),  # 2345.678 kWh
    36025: s32(-820),  # -820 W
    # -- battery, BMS side --
    37002: 1,  # BmsStatus.NORMAL
    37007: 74,  # 74 %
    37008: 99,  # 99 %
    37020: 231,  # 23.1 °C
    37021: 220,  # 22.0 °C
    37022: 3312,  # 3312 mV
    37023: 3298,  # 3298 mV
    # -- settings --
    45127: 247,
    # -- real-time BMS --
    47902: 5480,  # 548.0 V
    47903: 250,  # 25.0 A
    47904: 4400,  # 440.0 V
    47905: 300,  # 30.0 A
    47906: 3985,  # 398.5 V
    47907: 123,  # 12.3 A
    47908: 74,  # 74 %
    47909: 99,  # 99 %
    47910: 235,  # 23.5 °C
}


@pytest.fixture
def seeded_unit(mock_modbus_unit: MockModbusUnit) -> MockModbusUnit:
    """A unit answering the full Viessmann register map."""
    mock_modbus_unit.holding.update(HOLDING)
    return mock_modbus_unit


@pytest.fixture
async def device(seeded_unit: MockModbusUnit) -> ViessmannHybridInverter:
    """A set-up, polled inverter."""
    inverter = ViessmannHybridInverter(seeded_unit)
    await inverter.async_update()
    return inverter
