# viessmann-modbus

Read a **Viessmann hybrid inverter** over Modbus from Python, as typed objects
rather than register numbers.

Viessmann's B1-generation hybrid inverters (Vitocharge-class, e.g. `HINV6.0-B1`)
are rebadged GoodWe units and expose the GoodWe register map: everything lives in
the holding-register space (FC03), 32-bit values are big-endian, and the inverter
answers on unit id **247** out of the box.

The library is built on
[modbus-connection](https://github.com/home-assistant-libs/modbus-connection): it
takes a `ModbusUnit` and never opens a connection itself, so it works over any
backend the caller chooses.

## Install

```bash
pip install viessmann-modbus
```

## Usage

```python
import asyncio

from modbus_connection import ModbusTcpParams
from modbus_connection.tmodbus import ModbusConnection

from viessmann_modbus import ViessmannHybridInverter


async def main() -> None:
    connection = ModbusConnection(ModbusTcpParams(host="192.168.1.50", port=502))
    try:
        device = ViessmannHybridInverter(connection.for_unit(247))
        await device.async_update()

        print(device.info.model, device.info.serial_number)
        print("PV:", device.inverter.pv_power_1, "+", device.inverter.pv_power_2, "W")
        print("Grid:", device.inverter.grid_power, "W", device.inverter.grid_mode)
        print("Mode:", device.inverter.work_mode)
        if device.battery is not None:
            print("Battery:", device.battery.soc, "%", device.inverter.battery_mode)
    finally:
        await connection.close()


asyncio.run(main())
```

## Sub-systems

`ViessmannHybridInverter` reads its identity once during setup, then probes for
the optional blocks and polls only what the installation answers.

| Attribute | Registers | What it covers |
| --- | --- | --- |
| `info` | 35001–35015 | Rated power, serial number, model. Read once, never polled. |
| `inverter` | 35103–35211 | PV strings, grid, load, temperatures, inverter-side battery, work mode, error code, energy counters. |
| `meter` | 36004–36026 | External meter: import/export totals and active power. |
| `battery` | 37002–37023 | BMS status, SoC/SoH, cell temperature and voltage extremes. |
| `bms` | 47902–47910 | The BMS's own real-time limits and measurements. |
| `settings` | 45127 | Configured Modbus address. |

`meter`, `battery`, `bms` and `settings` are `None` on an installation whose
inverter refuses those blocks — a unit without a battery or without a meter.
Only an *illegal address* or *illegal function* reply counts as absent: a
timeout or a busy device during setup is transient, so setup raises and the next
`async_update()` probes again rather than writing the sub-system off. Each
sub-system is a `Component`, can be refreshed on its own, and carries its own
update listeners.

The whole map is **read-only**: the upstream integration defines no writable
entity for this inverter, so no field here is marked writable.

## Partial updates

A poll reads each sub-system separately and returns an `UpdateReport`, so one
sub-system going quiet does not cost you the others:

```python
report = await device.async_update()
if not report.complete:
    for name, error in report.failed.items():
        print("stale:", name, error)
```

A sub-system whose read fails keeps its previous values and does not notify its
listeners; it is named in `report.failed` with the error that failed it, while
everything that did refresh lands in `report.updated`. Listeners fire only once
the whole poll is over, so a callback never sees a half-updated device. A
failure never drops a sub-system — it is polled again on the next update. Only a
dead link raises, as `ModbusConnectionError`.

Containment is per sub-system rather than per block: `inverter` is a single
sub-system spanning eight blocks, so one slow block there holds back all of its
fields.

## Raw register dump

`async_read_raw()` reads every register the device reads and returns it
undecoded, keyed by address space and address — the payload a bug report wants.
It covers `info`, which only setup reads, as well as the polled sub-systems, and
leaves out the blocks this installation does not have. The fields refresh, but no
listener fires — downloading a dump must not look like a poll.

```python
raw = await device.async_read_raw()
raw["holding"]  # {address: value} — everything on this inverter is FC03
```

The dump replays into `modbus-connection`'s mock backend through `load_raw()`, so
one attached to an issue can back a regression test with no hardware.

## Not supported

- **ASCII-over-TCP framing is not supported, under any circumstance.** The
  library takes a `ModbusUnit` from a connection you build, so give it an RTU or
  TCP/MBAP one; a unit backed by ASCII framing is not a supported configuration.
- Home Assistant's daily-delta pseudo-sensors (`grid_export_energy_today`,
  `grid_import_energy_today`) have no register behind them — they are computed
  in the integration from the lifetime totals — and are out of scope here. Use
  `meter.grid_export_energy_total` / `meter.grid_import_energy_total`.

## Reads

The inverter maps 16 disjoint address ranges (`REGISTER_RANGES`) and dislikes
wide reads, so a read never bridges a gap and never exceeds `MAX_READ_SPAN`
(10) registers. A full poll of every sub-system costs 15 block reads covering
82 registers.

Field names follow the upstream sensor keys, minus a prefix that would repeat
the sub-system name — `meter_active_power` is `meter.active_power`,
`realtime_bms_soc` is `bms.soc`. The inverter-side battery readings stay on
`inverter` (`inverter.battery_voltage`) and the BMS-side ones on `battery` /
`bms`, as upstream distinguishes them.

## Attribution

The register maps are based on
[homeassistant-solax-modbus](https://github.com/wills106/homeassistant-solax-modbus)
(Apache-2.0), specifically its `plugin_viessmann.py`, which was validated
against a Viessmann HINV6.0-B1 over Modbus TCP. This library is a derived work
and keeps that license.

## Development

```bash
uv sync
uv run pytest
uv run ruff check . && uv run ruff format --check .
uv run mypy
```

## License

Apache-2.0
