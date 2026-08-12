"""Enumerated register values reported by the inverter."""

from __future__ import annotations

from enum import IntEnum


class WorkMode(IntEnum):
    """Inverter operating state (register 35187)."""

    WAIT = 0
    ON_GRID = 1
    OFF_GRID = 2
    FAULT = 3
    FLASH = 4
    CHECK = 5


class GridMode(IntEnum):
    """Grid connection state (register 35136)."""

    LOSS = 0
    OK = 1
    FAULT = 2


class BatteryMode(IntEnum):
    """What the battery is doing (register 35184)."""

    NO_BATTERY = 0
    STANDBY = 1
    DISCHARGING = 2
    CHARGING = 3


class BmsStatus(IntEnum):
    """Battery management system health (register 37002)."""

    IDLE = 0
    NORMAL = 1
    WARNING = 2
    FAULT = 3


class MeterCommunicationStatus(IntEnum):
    """Whether the inverter is talking to the energy meter (register 36004)."""

    NG = 0
    OK = 1
