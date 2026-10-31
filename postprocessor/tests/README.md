# Post-processor verification

- `make_inputs.py`: writes synthetic test inputs in OrcaSlicer's Klipper G-code format (dogbone with zig-zag infill, mid-path `SET_VELOCITY_LIMIT` / `M204` / `;WIDTH:` changes, single-axis travels).
- `runjs.js`: runs the post-processor from `../latex-laser-postprocessor.html` in headless Chromium (Playwright) with given settings.
- `verify.py`: independent machine simulator; compares every bead in input and output (missing, extra, printed toward the laser, laser state, power pin, extrusion totals).
- `extra_checks.py`: feedrates, overrun length and direction, idempotence (second pass), laser commands present.
- `check_all.sh`: runs everything for three setting combinations.

```bash
python3 make_inputs.py
grep -v "LASER_ARM\|LASER_DISARM" in_dogbone.gcode > in_dogbone_noarm.gcode
bash check_all.sh
```
Requires Python 3, Node.js and Playwright with Chromium.
