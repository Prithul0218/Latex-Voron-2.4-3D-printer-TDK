# G-code generators

Python 3 scripts (no dependencies) that write the calibration and process-parameter test prints directly, without a slicer. Each script writes its `.gcode` files into the current directory; run it to regenerate the exact files that were printed.

## Conventions shared by all scripts

- **E units:** virtual 1.75 mm filament, relative E (`M83`). E per mm of line = bead area / 2.405 mm².
- **Laser:** every laser-on move goes X+ only, except test 15 and the first version of test 16, which were bidirectional on purpose. `LASER_PWM S=0–255` with `max_duty` 1.0 in the macro.
- **Power pin:** `LASER_ARM` once at the start and `LASER_DISARM` once at the end.
- **Purge:** a laser-off purge line (3× volume) before the first line; nothing goes below X50.
- **Flow:** "100 % flow" in tests 4–16 means a 1.85 × 0.15 mm bead = 0.2775 mm²/mm.

| Script | Output | Purpose |
|---|---|---|
| `gen_laser_power_lines.py` | `laser_power_lines.gcode` (+ dry run) | Power ladder: 11 lines, 0–50 % duty in 5 % steps, 0.6 × 0.6 mm bead, 5 mm/s |
| `gen_block.py` | `latex_block_80x10x4.gcode` (+ dry run) | Solid 80 × 10 × 4 mm block, X-parallel lines, as printed: 0.2 mm layers × 1.5 mm width, 60 % laser, 1 mm overrun |
| `gen_bead_tests.py` | `test1_volume_sweep`, `test2_gap_sweep`, `test3_pitch_patches` | First bead-geometry calibration: volume per mm, nozzle gap, line pitch |
| `gen_dot_speed_tests.py` | `test4` … `test15` | Process-parameter campaign: dot cure, power × speed, gap × flow, laser columns, layer stacks, layer-by-layer printing, bidirectional stacks |
| `gen_test16.py` | `test16_single_line_unidirectional.gcode` | Single 50 mm line, 10 layers, unidirectional |

Dry-run files (`*_DRYRUN.gcode`) contain the same moves 20 mm higher with no extrusion. Use them to check motion and laser switching with the laser module unpowered.

Results of each test are summarised in [`../docs/experiments.md`](../docs/experiments.md).
