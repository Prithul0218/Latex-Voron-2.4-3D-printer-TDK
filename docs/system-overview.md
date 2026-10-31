# System overview

## 1. Extruder calibration: "virtual filament"

Klipper and the slicer are told the extruder feeds **1.75 mm filament**. `rotation_distance` is chosen so that 1 mm of virtual filament pushes out exactly the volume that 1 mm of 1.75 mm filament would. Slicer settings (layer height, line width, flow) then work unchanged.

| Quantity | Value |
|---|---|
| Syringe bore area | π · 15² = 706.86 mm² |
| Plunger travel per motor revolution | 1 mm (M6 × 1, direct drive) → 706.86 mm³/rev |
| Virtual filament area | π · 0.875² = 2.405 mm² |
| **rotation_distance** | 706.86 / 2.405 = (30 / 1.75)² × 1 mm = **293.88** |
| Resolution | 200 × 32 = 6400 microsteps/rev → 0.110 mm³ per microstep |
| Motor speed at 5 mm/s, 0.28 mm²/mm bead | ≈0.3 rpm, so stealthChop with interpolation |
| Torque at 2 bar back-pressure | ≈141 N on the plunger → ≈0.09 N·m (rod efficiency about 25 %); NEMA 17 ≈0.4 N·m |

Klipper requires a heater on `[extruder]`: a 100 kΩ resistor on the thermistor input reads a constant 25 °C (watermark control, `min_extrude_temp: 0`). The slicer start G-code begins with `M104 S0`.

**Status:** line widths and heights set in the slicer came out as expected on the printer. A gravimetric check (`G1 E2000` of water should weigh 4.81 g) is still open because no scale was available.

## 2. Laser control and safety

| Element | Configuration |
|---|---|
| `laser_power` | `[output_pin]` on EBB36 PB13, on/off, `shutdown_value: 0` |
| `laser_pwm` | `[pwm_tool]` on PB9, 1 kHz software PWM, `shutdown_value: 0`, `maximum_mcu_duration: 1.0` |
| Macros | `LASER_ARM` (power on, PWM 0), `LASER_DISARM` (PWM 0, power off), `LASER_PWM S=0–255` (beam power only) |

- `maximum_mcu_duration` is only accepted on `[pwm_tool]`; Klipper removed it from `[output_pin]` in 2024. The watchdog therefore sits on the PWM line, which is the line that fires the beam.
- Print files switch the power pin only at the start and end; during a print only the PWM value changes.
- **Tested:** emergency stop turns the laser off immediately; unplugging the CAN cable while lasing turns it off within 1 s.

## 3. Curing geometry

The defocused rectangular spot lies ≈1 mm behind the needle on the X− side, so only moves toward X+ put the spot on fresh latex.

For a line at angle φ to X, the spot lands d·sin φ to the side of the bead centre. It misses once d·sin φ > w/2, where d is the spot distance and w the bead width:

| d | w = 0.6 mm | w = 1.1 mm |
|---|---|---|
| 0.5 mm | any angle | any angle |
| 1.0 mm | 17° | 33° |
| 2.0 mm | 9° | 16° |

Parts are therefore printed as X-parallel rasters in one direction. On a synthetic dogbone-style test, 98.6 % of the bead length was within the spot's reach for X-only rasters, against 16 % for a typical "1 wall + ±45° infill" slice.

## 4. Known process limits

| Limit | Effect | Mitigation |
|---|---|---|
| Lead-screw backlash (plain M6 nut) | Reverse moves under ≈15–60 virtual mm do nothing, so retraction and pressure advance don't work | Anti-backlash nut / T8 screw |
| Syringe compliance | ≈1–2 s flow lag, thin line starts | Small `unretract_extra_length` (0.2–0.4); remove air from the syringe |
| Nozzle-tip wetting | A latex blob grows on the needle and drags uncured latex | Wipe before every run; water-repellent tip coating; wipe station |
| Feed tube vibration | Ringing above 5 mm/s | ≤5 mm/s print, 30 mm/s travel, 300 mm/s²; secure the tube |
| Latex stability in the syringe | After ~2 days the latex coagulated; the liquid left behind spread more and cured poorly | Fresh latex per session; record batch and fill time |

Low-viscosity inks wetting the nozzle and forming unstable lines: Friedrich, L. & Begley, M. (2018), *J. Colloid Interface Sci.* 529, 599–609, doi:10.1016/j.jcis.2018.05.110. Ink requirements for direct ink writing: Lewis, J. A. (2006), *Adv. Funct. Mater.* 16, 2193–2204.
