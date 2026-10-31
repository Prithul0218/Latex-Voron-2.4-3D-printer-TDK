# OrcaSlicer settings

Start from a Voron 2.4 350 profile and change the settings below. A profile export (`.orca_printer` / `.json`) **will be added**.

## Printer
| Tab | Setting |
|---|---|
| Basic | G-code flavor: Klipper; use relative E distances: on |
| Extruder | Nozzle diameter 1.04 mm; layer height limits wide enough for your recipe (e.g. 0.05–0.8 mm) |
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
| Quality | Layer height and line width from the bead tests (see `docs/experiments.md`); arc fitting **off** |
| Strength | Wall loops **0**; top/bottom shells 0; sparse infill 100 %; all infill patterns **Aligned Rectilinear**, direction **0°**, rotate solid infill off |
| Speed | Print ≤ 5 mm/s; travel 30 mm/s; acceleration 300 mm/s² (feed tube vibration) |
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
