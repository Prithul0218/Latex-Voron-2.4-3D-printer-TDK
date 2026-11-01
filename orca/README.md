# OrcaSlicer settings

Start from a Voron 2.4 profile and change the settings below.

## Printer
| Tab | Setting |
|---|---|
| Basic | G-code flavor: Klipper; use relative E distances: on |
| Extruder | Nozzle diameter = your needle's inner diameter; layer height limits wide enough for your recipe |
| Extruder → Retraction | Length 0; Z-hop as needed; **Z-hop type: Normal** (Spiral produces arcs); wipe off |
| Others | Exclude objects: on (for per-object laser power) |

## Filament
- Diameter **1.75 mm** (virtual filament, matches Klipper)
- Nozzle temperature 0 (dummy heater)
- All fans 0 %; "slow down for layer cooling" off
- Flow ratio 1.0

## Process (unidirectional raster)
| Tab | Setting |
|---|---|
| Quality | Layer height and line width from your bead calibration (`gcode-generators/gen_bead_tests.py`); arc fitting **off** |
| Strength | Wall loops **0**; top/bottom shells 0; sparse infill 100 %; all infill patterns **Aligned Rectilinear**, direction along the print axis (0° for X), rotate solid infill off |
| Speed | Slow printing (a few mm/s) and moderate travel and acceleration suit syringe extrusion |
| Others | Spiral vase off; post-processing: none (use the browser post-processor) |

## Machine G-code

Start:
```
M104 S0                 ; Orca must not wait on the dummy heater
G90
M83
G28
LASER_ARM               ; optional - the post-processor adds it if missing
; purge line here if you do not use the post-processor's prime
```

End:
```
LASER_PWM S=0
LASER_DISARM
G91
G1 Z30 F600
G90
```

**Without the post-processor:** add `LASER_PWM S=<0-255>` at the end of the start G-code. The laser then stays on for the whole print, travels included, and lines printed toward the laser cure poorly.

**With the post-processor:** any `LASER_PWM` in the start G-code is removed and replaced by per-line control. If your start G-code has its own purge, untick "Prime the syringe" in the tool.
