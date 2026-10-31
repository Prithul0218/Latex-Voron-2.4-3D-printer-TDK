# Latex Laser Post-Processor

A single-file browser tool, [`latex-laser-postprocessor.html`](latex-laser-postprocessor.html), that rewrites OrcaSlicer G-code for a printer whose curing laser trails the nozzle. Open it in any browser; it runs fully offline and nothing is uploaded.

## Why it exists

The laser spot sits ≈1 mm behind the nozzle on one side (X− on this printer), so a bead is only cured when the nozzle moves away from the spot (toward X+). OrcaSlicer has no option to print in one direction only.

When a line runs at angle φ to the allowed direction, the spot lands d·sin φ to the side of the bead (d = spot distance). It misses once that offset exceeds half the bead width. For d = 1 mm and a 0.6 mm bead, the limit is about 17°.

## What it does

1. **One-direction printing:** splits each extrusion path wherever it turns back toward the laser, prints those pieces reversed, and inserts lifted travels between them. Total extrusion is unchanged.
2. **Laser per line:** `LASER_PWM S=<power>` before each piece and `LASER_PWM S=0` after it. A laser-on overrun (default 1 mm, the spot distance) continues past the bead end so the trailing spot covers it. The overrun always runs in the print direction.
3. **Power pin only at start and end:** adds `LASER_ARM` once before the first bead and `LASER_DISARM` once at the end, unless the file already contains them. Any other laser commands in the source (`LASER_ON`, `LASER_OFF`, `M3`/`M4`/`M5`, earlier `LASER_PWM`) are removed. During the print only the PWM value changes.
4. **Laser power in the interface:** a global power (% duty) plus a slider per object, so a power ladder can be set up on one Orca plate. Object names containing a token like `S128` start at that power. Requires "Exclude objects" in Orca and `[exclude_object]` in Klipper.
5. **Syringe prime (optional):** stationary take-up plus a laser-off purge line before the first bead (default X50, Y320, toward X+).
6. **G10/G11:** removed unless "Firmware retract" is ticked (then Klipper needs `[firmware_retraction]`).
7. **Checks and preview:** confirms extrusion is unchanged, reports laser coverage (the share of bead the spot can reach), counts laser runs and added travels, and warns about absolute E, arcs, `G92 X/Y` and moves below the bed X minimum. The toolpath preview shows the original and processed file layer by layer, coloured by curing state.

The processed file is saved as `.gcode` when the page is opened from disk. Inside claude.ai it is saved as `.gcode.txt`; remove the `.txt` before uploading to the printer.

## Required Klipper macros

`LASER_ARM`, `LASER_DISARM` and `LASER_PWM S=0–255` (beam power only, never the power pin). See [`../klipper/laser-reference.cfg`](../klipper/laser-reference.cfg).

## Required Orca settings

Relative E, arc fitting off, Z-hop type Normal, spiral vase off. For best laser coverage: wall loops 0, every infill pattern Aligned Rectilinear at 0°. See [`../orca/`](../orca/).

## Verification

[`tests/`](tests/) contains an independent simulator that replays G-code like a printer and compares every bead in the Orca input with the processed output:
- no bead missing or extra;
- no bead printed toward the laser;
- the laser is on for every bead and off for every travel and Z move;
- feedrates are unchanged;
- overruns have the right length and direction;
- exactly one power-on and one power-off;
- running a file through twice gives identical beads.

```bash
cd tests
python3 make_inputs.py
grep -v "LASER_ARM\|LASER_DISARM" in_dogbone.gcode > in_dogbone_noarm.gcode
bash check_all.sh          # needs Node + Playwright (Chromium)
```

The test inputs are synthetic G-code in OrcaSlicer's Klipper format: a dogbone and zig-zag paths, with mid-path `SET_VELOCITY_LIMIT` / `M204` / `;WIDTH:` changes, single-axis travels and G10/G11.

### Bugs found and fixed during development
- **Wrong start point after a reversed piece** (gaps and a backwards bead in dogbone grips). Orca inserts commands mid-path; after a reversed piece the nozzle was not where Orca assumed. The tool now tracks the real nozzle position separately and travels to Orca's start point first. Before the fix, 20 of 260 dogbone beads were misplaced while total extrusion still matched; after it, 0 of 260.
- **Overrun direction:** the overrun followed the last short zig-zag step and swept sideways across neighbouring beads. It now always follows the print direction.
- **`S=` parameter parsing** in the preview (beads shown as "laser off").

## Legacy

[`legacy/unidir_laser.py`](legacy/unidir_laser.py) is the first Python version. It is **outdated**: it still contains the wrong-start-point bug and uses the older `LASER_ON`/`LASER_OFF` macros. It is kept only for the record; use the HTML tool.
