# System overview

## 1. Syringe extruder calibration: "virtual filament"

Klipper and the slicer are told the extruder feeds **1.75 mm filament**. `rotation_distance` is chosen so that 1 mm of virtual filament pushes out exactly the volume 1 mm of 1.75 mm filament would. Slicer settings (layer height, line width, flow) then work unchanged.

For a syringe of inner diameter **D** whose plunger moves **p** mm per motor revolution:

```
rotation_distance = (D / 1.75)² × p
```

Example: a 30 mm syringe and a 1 mm-per-revolution drive give `rotation_distance = (30/1.75)² × 1 = 293.88`.

Useful checks:
- **Volume per microstep** = π·(D/2)² · p / (full steps × microsteps).
- **Gravimetric check with water:** `G1 E<L>` of virtual filament should deliver `L × 2.405 mm³`, i.e. `L × 2.405 mg` of water.

Klipper requires a heater on `[extruder]`. A fixed resistor on the thermistor input (e.g. 100 kΩ for a 100k NTC) reads a constant room temperature; use watermark control and `min_extrude_temp: 0`. Start the slicer's machine G-code with `M104 S0` so it never waits for heating.

## 2. Laser control and safety

| Element | Configuration |
|---|---|
| `laser_power` | `[output_pin]`, plain on/off, `shutdown_value: 0` (module supply) |
| `laser_pwm` | `[pwm_tool]`, 1 kHz software PWM, `shutdown_value: 0`, `maximum_mcu_duration: 1.0` (watchdog) |
| Macros | `LASER_ARM` (power on, PWM 0), `LASER_DISARM` (PWM 0, power off), `LASER_PWM S=0–255` (beam power only) |

- `maximum_mcu_duration` is only accepted on `[pwm_tool]`; Klipper removed it from `[output_pin]` in 2024. The watchdog therefore sits on the PWM line, which is the line that fires the beam.
- Print files switch the power pin only at the start and end; during a print only the PWM value changes. Switching the power pin by hand then works as a lockout that no print file overrides.
- The configuration was tested: emergency stop turns the beam off immediately, and unplugging the CAN cable while lasing turns it off within 1 s.

## 3. Why print in one direction

If the curing spot trails the nozzle by a distance **d**, it only lands on the freshly laid bead when the nozzle moves away from it. For a line at angle φ to that direction, the spot lands d·sin φ to the side of the bead centre. It misses once d·sin φ > w/2, where w is the bead width:

| d | w = 0.6 mm | w = 1.1 mm |
|---|---|---|
| 0.5 mm | any angle | any angle |
| 1.0 mm | 17° | 33° |
| 2.0 mm | 9° | 16° |

Parts are therefore sliced as parallel rasters along the print axis and printed in one direction. The post-processor reports the share of bead length within the spot's reach ("laser coverage") for every file.

## 4. Practical notes for syringe extrusion

- **Retraction and pressure advance** need the plunger to reverse precisely; any backlash in the drive cancels small reverse moves.
- **Syringe compliance** (air, seal, the fluid itself) delays the flow at line starts. A small `unretract_extra_length` with `retract_length: 0` compensates.
- **Low-viscosity inks** can wet the outside of the nozzle and build up there. See Friedrich, L. & Begley, M. (2018), *J. Colloid Interface Sci.* 529, 599–609, doi:10.1016/j.jcis.2018.05.110; and Lewis, J. A. (2006), *Adv. Funct. Mater.* 16, 2193–2204.
