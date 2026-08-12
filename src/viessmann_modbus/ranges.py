"""The address windows the inverter is known to answer.

Derived mechanically from ``plugin_viessmann.py``: the upstream integration
splits its sensors into read blocks at every ``newblock=True`` marker and
whenever an entity starts more than ``block_size`` (8) registers past the block
start, then reads each block on real hardware. These ranges are the union of
those blocks, so nothing here claims a register the integration does not read.

They matter in both directions: the inverter does not map the space between the
blocks, and a read may not bridge it, while inside a range the planner is free
to merge over registers no field claims.
"""

from __future__ import annotations

# (low, high) inclusive — sorted, non-overlapping.
REGISTER_RANGES: tuple[tuple[int, int], ...] = (
    (35001, 35001),  # rated power
    (35003, 35015),  # serial number, model
    (35103, 35110),  # PV strings 1 and 2
    (35121, 35125),  # grid voltage/current/frequency/power
    (35136, 35140),  # grid mode, inverter and AC power
    (35169, 35176),  # backup and load power, temperatures
    (35180, 35184),  # battery voltage/current/power/mode
    (35187, 35194),  # work mode, error code, PV energy
    (35197, 35211),  # runtime and the load/battery energy counters
    (36004, 36004),  # meter communication status
    (36015, 36018),  # meter grid export/import totals
    (36025, 36026),  # meter active power
    (37002, 37008),  # BMS status, SoC, SoH
    (37020, 37023),  # cell temperature and voltage extremes
    (45127, 45127),  # configured Modbus address
    (47902, 47910),  # real-time BMS limits and measurements
)

# The upstream plugin caps a block at a start offset of 8 registers, so its
# widest possible read is that plus a two-register value.
MAX_READ_SPAN = 10
