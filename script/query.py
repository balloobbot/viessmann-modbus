#!/usr/bin/env python3

"""Query a Viessmann hybrid inverter and print every value.

Reads one inverter once and dumps it to the terminal — the quickest way to check
a real inverter with no application around it.

::

    uv run script/query.py 192.168.1.50 --unit 247
    uv run script/query.py /dev/ttyUSB0 --transport serial --unit 247
"""

from __future__ import annotations

import argparse
import asyncio

from modbus_connection import ModbusError
from modbus_connection.cli_helper import (
    CountingUnit,
    add_connection_args,
    connect_from_args,
    print_component,
)

from viessmann_modbus import ViessmannHybridInverter

# The inverter is RS-485 RTU. The documented install reaches it through a
# gateway converting Modbus TCP to RTU (socket framing); a transparent gateway
# (rtu) and the RS-485 line itself are the other two paths. ASCII is never one.
CONNECTIONS = (("tcp", "socket"), ("tcp", "rtu"), ("serial", "rtu"))

# Identity first, then the sub-systems in poll order. Everything below
# ``inverter`` is absent on an installation whose inverter refuses the block.
SUB_SYSTEMS = (
    ("info", "Device"),
    ("inverter", "Inverter"),
    ("meter", "Meter"),
    ("battery", "Battery"),
    ("bms", "Realtime BMS"),
    ("settings", "Settings"),
)


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    add_connection_args(parser, connections=CONNECTIONS)
    parser.add_argument("--unit", type=int, default=247, help="Modbus unit id")
    args = parser.parse_args()

    try:
        connection = await connect_from_args(args)
    except ModbusError as err:
        # A timeout stringifies empty; name the class so the line still reads.
        print(f"Could not connect: {str(err) or type(err).__name__}")
        return 1

    counting = CountingUnit(connection.for_unit(args.unit))
    device = ViessmannHybridInverter(counting)
    try:
        report = await device.async_update()  # sets up on the first call
    except ModbusError as err:
        print(f"Could not read the inverter: {str(err) or type(err).__name__}")
        return 1
    finally:
        await connection.close()

    for name, title in SUB_SYSTEMS:
        component = getattr(device, name)
        if component is None:
            continue  # a block this installation does not have
        print()
        print_component(component, title=title)

    # A poll contains a failed sub-system rather than raising, so say which
    # values above are stale.
    for name, error in report.failed.items():
        print(f"\n{name}: not refreshed ({error})")
    print(f"\n{counting.reads} Modbus reads")
    return 0


raise SystemExit(asyncio.run(main()))
