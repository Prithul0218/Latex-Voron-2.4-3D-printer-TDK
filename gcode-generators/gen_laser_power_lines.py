#!/usr/bin/env python3
"""
gen_laser_power_lines.py - laser power ladder for the syringe/laser latex printer.

Prints single parallel lines, one laser power per line, every line printed
X-min -> X-max (0 deg to the laser, spot trailing the nozzle).

Writes two files:
  laser_power_lines.gcode         - real print
  laser_power_lines_DRYRUN.gcode  - same moves 20 mm higher, no extrusion,
                                    laser commands kept so you can check the pins

Matches the Klipper setup: virtual 1.75 mm filament, relative E, and the
LASER_ARM / LASER_ON S=<0-255> / LASER_OFF / LASER_DISARM macros (S=255 = 100 % duty).
"""
import math

# ------------------------------- PARAMETERS ------------------------------------------
LAYER_H      = 0.60     # mm, nozzle height above bed for the lines
LINE_W       = 0.60     # mm, nominal bead width
FIL_D        = 1.75     # virtual filament diameter (must match Klipper / Orca)
ROT_DIST     = 293.88   # Klipper rotation_distance, only used for the stats header
PRINT_SPEED  = 5.0      # mm/s
TRAVEL_SPEED = 100.0    # mm/s
Z_SPEED      = 10.0     # mm/s
Z_HOP        = 1.0      # mm lift for travels
RETRACT_MM   = 0.0      # virtual mm; leave 0 until the backlash is fixed

X_START      = 145.0    # lines run X_START -> X_START + LINE_LEN  (laser axis = +X)
LINE_LEN     = 60.0
Y_FIRST      = 145.0    # first line (S=0) - front of the bed on a Voron
PITCH        = 6.0      # mm between line centres (~4.8 mm gap)

# Laser power per line, S = 0-255 -> duty = S/255 x 100 %. S=0 is the no-laser control.
POWERS       = [round(2.55 * pct, 2) for pct in range(0, 51, 5)]   # 0 %, 5 % ... 50 % (exact, S may be fractional)
OVERRUN_MM   = 1.0      # dry move past bead end with laser on = spot-to-nozzle distance

PURGE        = True     # laser-off prime line 10 mm in front of the first line
START_GCODE  = "G28"     # your start sequence, WITHOUT hotend heating
DRY_LIFT     = 20.0     # dry-run file: everything this much higher (absolute Z, no offsets)
# --------------------------------------------------------------------------------------

AREA = (LINE_W - LAYER_H) * LAYER_H + math.pi * (LAYER_H / 2) ** 2   # Orca flow model
FIL_AREA = math.pi * (FIL_D / 2) ** 2
E_PER_MM = AREA / FIL_AREA
F_PRINT, F_TRAVEL, F_Z = PRINT_SPEED * 60, TRAVEL_SPEED * 60, Z_SPEED * 60


def build(dry_run):
    g = []
    zl = LAYER_H + (DRY_LIFT if dry_run else 0.0)   # working Z
    tot = {"e": 0.0, "t": 0.0}
    x_end = X_START + LINE_LEN

    def travel_to(x, y):
        if RETRACT_MM > 0 and not dry_run:
            g.append(f"G1 E-{RETRACT_MM:.4f} F1800")
        g.append(f"G1 Z{zl + Z_HOP:.3f} F{F_Z:.0f}")
        g.append(f"G1 X{x:.3f} Y{y:.3f} F{F_TRAVEL:.0f}")
        g.append(f"G1 Z{zl:.3f} F{F_Z:.0f}")
        if RETRACT_MM > 0 and not dry_run:
            g.append(f"G1 E{RETRACT_MM:.4f} F1800")
        tot["t"] += 1.5 + 2 * Z_HOP / Z_SPEED

    def line(y, s, label):
        e = LINE_LEN * E_PER_MM
        desc = "laser off" if s is None else f"S={s:g}  duty {s / 255 * 100:.1f} %"
        g.append(f"; ---- {label}: {desc}  y={y:.1f}")
        travel_to(X_START, y)
        if s is not None:
            g.append(f"LASER_ON S={s:g}")
        if dry_run:
            g.append(f"G1 X{x_end:.3f} Y{y:.3f} F{F_PRINT:.0f}")
        else:
            g.append(f"G1 X{x_end:.3f} Y{y:.3f} E{e:.5f} F{F_PRINT:.0f}")
            tot["e"] += e
        if s is not None and OVERRUN_MM > 0:
            g.append(f"G1 X{x_end + OVERRUN_MM:.3f} F{F_PRINT:.0f}")
        if s is not None:
            g.append("LASER_OFF")
        tot["t"] += (LINE_LEN + OVERRUN_MM) / PRINT_SPEED

    g += [
        "; LASER POWER LADDER" + ("  ** DRY RUN: no extrusion, +20 mm Z **" if dry_run else ""),
        f"; layer {LAYER_H} mm | width {LINE_W} mm | {PRINT_SPEED} mm/s | "
        f"bead area {AREA:.4f} mm2 | E/mm {E_PER_MM:.5f}",
        "; lines front->back: " + ", ".join(f"{s / 255 * 100:g}%" for s in POWERS),
        "; every line printed X- -> X+",
        "G90",
        "M83",
        START_GCODE,
    ]
    g.append(f"G1 Z{zl + 5:.3f} F{F_Z:.0f}")
    g.append("LASER_ARM")
    if PURGE:
        line(Y_FIRST - 10, None, "purge")
    for i, s in enumerate(POWERS):
        line(Y_FIRST + i * PITCH, s, f"line {i + 1:2d}")
    g.append("LASER_DISARM")
    g.append(f"G1 Z{zl + 30:.3f} F{F_Z:.0f}")
    g.append("; end")

    ml = tot["e"] * FIL_AREA / 1000
    g.insert(1, f"; total E {tot['e']:.2f} virtual mm = {ml:.3f} mL = "
                f"{tot['e'] / ROT_DIST:.3f} mm plunger | est. {tot['t'] / 60:.1f} min")
    return g


if __name__ == "__main__":
    for dry, name in ((False, "laser_power_lines.gcode"),
                      (True, "laser_power_lines_DRYRUN.gcode")):
        out = build(dry)
        with open(name, "w") as fh:
            fh.write("\n".join(out) + "\n")
        print(f"{name}: {out[1]}")
