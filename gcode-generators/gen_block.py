#!/usr/bin/env python3
"""
gen_block.py - solid block for the syringe/laser latex printer, same style as the
power ladder that worked: every line printed X- -> X+, laser on only while laying
a line (plus a 1 mm overrun so the trailing spot reaches the bead end).

Writes:
  latex_block_80x10x4.gcode         - real print
  latex_block_80x10x4_DRYRUN.gcode  - same moves 20 mm higher, no extrusion
"""
import math

# ------------------------------- PARAMETERS ------------------------------------------
SIZE_X, SIZE_Y, SIZE_Z = 80.0, 10.0, 4.0   # mm, outer size (X = line direction)
CENTER_X, CENTER_Y     = 175.0, 175.0      # bed centre of a Voron 350
LAYER_H      = 0.20
LINE_W       = 1.50
FIL_D        = 1.75     # virtual filament (Klipper/Orca)
ROT_DIST     = 293.88
PRINT_SPEED  = 5.0      # mm/s
TRAVEL_SPEED = 100.0
Z_SPEED      = 10.0
Z_HOP        = 1.0
LASER_PCT    = 60.0     # % PWM duty
DUTY_CAP     = 1.0      # max_duty in the LASER_ON macro
OVERRUN_MM   = 1.0      # laser stays on this far past the bead end (= spot-to-nozzle distance)
PURGE_GAP    = 8.0      # purge line this far in front of the block
PURGE_MULT   = 3.0      # purge line extrudes this many times a normal line's volume
START_GCODE  = "G28"
DRY_LIFT     = 20.0
# --------------------------------------------------------------------------------------

AREA = (LINE_W - LAYER_H) * LAYER_H + math.pi * (LAYER_H / 2) ** 2      # Orca bead model
SPACING_NOM = LINE_W - LAYER_H * (1 - math.pi / 4)                       # Orca line spacing
FIL_AREA = math.pi * (FIL_D / 2) ** 2
E_PER_MM = AREA / FIL_AREA
S_VAL = min(255.0, LASER_PCT / 100 / DUTY_CAP * 255)

N_LAYERS = max(1, round(SIZE_Z / LAYER_H))
span_y = SIZE_Y - LINE_W                                # centre-to-centre of outer lines
N_LINES = int(round(span_y / SPACING_NOM)) + 1
PITCH = span_y / (N_LINES - 1)
X0 = CENTER_X - SIZE_X / 2 + LINE_W / 2                 # bead centre start / end
X1 = CENTER_X + SIZE_X / 2 - LINE_W / 2
Y0 = CENTER_Y - SIZE_Y / 2 + LINE_W / 2
F_PRINT, F_TRAVEL, F_Z = PRINT_SPEED * 60, TRAVEL_SPEED * 60, Z_SPEED * 60


def fmt_s(v):
    return f"{v:.2f}".rstrip("0").rstrip(".")


def build(dry):
    g, tot = [], {"e": 0.0, "t": 0.0}
    lift = DRY_LIFT if dry else 0.0
    line_len = X1 - X0
    e_line = line_len * E_PER_MM

    def go(x, y, z):
        g.append(f"G1 Z{z + Z_HOP:.3f} F{F_Z:.0f}")
        g.append(f"G1 X{x:.3f} Y{y:.3f} F{F_TRAVEL:.0f}")
        g.append(f"G1 Z{z:.3f} F{F_Z:.0f}")
        tot["t"] += 1.2 + 2 * Z_HOP / Z_SPEED

    def bead(x_end, y, e, laser):
        if laser:
            g.append(f"LASER_ON S={fmt_s(S_VAL)}")
        g.append(f"G1 X{x_end:.3f} Y{y:.3f}" + ("" if dry else f" E{e:.5f}") + f" F{F_PRINT:.0f}")
        if not dry:
            tot["e"] += e
        tot["t"] += (x_end - X0) / PRINT_SPEED
        if laser:
            if OVERRUN_MM > 0:
                g.append(f"G1 X{x_end + OVERRUN_MM:.3f} F{F_PRINT:.0f}")
                tot["t"] += OVERRUN_MM / PRINT_SPEED
            g.append("LASER_OFF")

    g += [
        "; LATEX BLOCK" + ("  ** DRY RUN: no extrusion, +20 mm Z **" if dry else ""),
        f"; block {SIZE_X:g} x {SIZE_Y:g} mm, {N_LAYERS} layers x {LAYER_H} = {N_LAYERS * LAYER_H:.1f} mm tall",
        f"; {N_LINES} lines per layer at {PITCH:.3f} mm pitch | bead {LINE_W} x {LAYER_H} mm, "
        f"area {AREA:.4f} mm2, E/mm {E_PER_MM:.5f} | {PRINT_SPEED} mm/s",
        f"; laser {LASER_PCT:g} % duty = LASER_ON S={fmt_s(S_VAL)} (max_duty {DUTY_CAP}) | every line X- -> X+",
        "G90", "M83", START_GCODE,
        f"G1 Z{5 + lift:.3f} F{F_Z:.0f}",
        "LASER_ARM",
        f"; ---- purge line, laser off, {PURGE_MULT:g}x volume",
    ]
    z1 = LAYER_H + lift
    py = Y0 - PURGE_GAP
    go(X0, py, z1)
    bead(X1, py, e_line * PURGE_MULT, laser=False)

    for k in range(N_LAYERS):
        z = LAYER_H * (k + 1) + lift
        g.append(f";LAYER_CHANGE")
        g.append(f"; ---- layer {k + 1}/{N_LAYERS}  Z={z - lift:.2f}")
        for i in range(N_LINES):
            y = Y0 + i * PITCH
            go(X0, y, z)
            bead(X1, y, e_line, laser=True)

    g += ["LASER_DISARM", f"G1 Z{LAYER_H * N_LAYERS + lift + 30:.3f} F{F_Z:.0f}", "; end"]
    ml = tot["e"] * FIL_AREA / 1000
    g.insert(1, f"; total E {tot['e']:.1f} virtual mm = {ml:.2f} mL = {tot['e'] / ROT_DIST:.2f} mm plunger"
                f" | est. {tot['t'] / 60:.0f} min")
    return g


if __name__ == "__main__":
    for dry, name in ((False, "latex_block_80x10x4.gcode"), (True, "latex_block_80x10x4_DRYRUN.gcode")):
        out = build(dry)
        with open(name, "w") as fh:
            fh.write("\n".join(out) + "\n")
        print(name, "|", out[1])
