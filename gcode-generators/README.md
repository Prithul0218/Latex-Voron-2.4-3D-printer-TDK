# G-code generators

Python 3 scripts (no dependencies) that write calibration prints directly, without a slicer. Each script writes its `.gcode` files into the current directory; run it to regenerate the exact files that were printed.

## Conventions shared by all scripts

- **E units:** virtual 1.75 mm filament, relative E (`M83`). E per mm of line = bead area / 2.405 mm².
- **Laser:** every laser-on move goes X+ only. `LASER_PWM S=0–255` with `max_duty` 1.0 in the macro.
- **Power pin:** `LASER_ARM` once at the start and `LASER_DISARM` once at the end.
- **Purge:** a laser-off purge line (3× volume) before the first line; nothing goes below X50.

| Script | Output | Purpose |
|---|---|---|
| `gen_laser_power_lines.py` | `laser_power_lines.gcode` (+ dry run) | Laser power ladder: one line per power step |
| `gen_bead_tests.py` | `test1_volume_sweep`, `test2_gap_sweep`, `test3_pitch_patches` | Bead-geometry calibration: volume per mm, nozzle gap, line pitch |

Dry-run files (`*_DRYRUN.gcode`) contain the same moves 20 mm higher with no extrusion. Use them to check motion and laser switching with the laser module unpowered.

All parameters (powers, bead size, speed, positions) are set at the top of each script.
