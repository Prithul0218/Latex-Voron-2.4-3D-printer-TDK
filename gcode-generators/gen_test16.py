#!/usr/bin/env python3
"""test16: one line at bed centre, 10 layers, UNIDIRECTIONAL (all X+), laser on while printing."""
import math
FIL = math.pi * 0.875 ** 2
X0, LEN, Y = 150.0, 50.0, 175.0     # centred on a 350 x 350 bed: X150-200, Y175
NL, Z1, DZ = 10, 0.15, 0.10
AREA = 1.2 * 1.85 * 0.15            # 120 % flow = 0.333 mm^2/mm
SPEED = 5.0
OVERRUN = 2.0                       # laser-on, no extrusion: spot is 1 mm behind the nozzle
HOP = 1.0                           # lift for the return move so the nozzle doesn't drag through the line
RET_F = 1800                        # 30 mm/s return
P1, PUP = 15, 40
PARK = (350, 350)
S = lambda p: round(p / 100 * 255)
e = LEN * AREA / FIL
L = [f"; TEST 16 - single line at bed centre, {NL} layers, UNIDIRECTIONAL (X+ only)",
     f"; line X{X0:g} -> X{X0+LEN:g} at Y{Y:g}; layer 1 Z{Z1} laser {P1}% (S={S(P1)}); layers 2-{NL} +{DZ} mm each, laser {PUP}% (S={S(PUP)})",
     f"; flow {AREA:.4f} mm^2/mm (120 %), {SPEED:g} mm/s, E {e:.5f} per layer; laser stays on {OVERRUN:g} mm past the line end",
     f"; return to the left: laser off, lift {HOP:g} mm, X- at {RET_F//60} mm/s, lower to the next layer; no prime",
     f"; park at X{PARK[0]} Y{PARK[1]} at the end",
     "; wipe the nozzle tip clean before starting",
     "G90", "M83", "G28", "SET_VELOCITY_LIMIT ACCEL=300", "LASER_PWM S=0", "LASER_ARM",
     "; ---- purge (laser off)",
     "G1 Z5 F600", "G1 X50 Y320 F6000", "G1 Z0.2 F600", ";G1 E40 F120", "G1 X110 Y320 E28 F300", "G1 Z5 F600",
     "; ---- move to line start",
     f"G1 X{X0:.3f} Y{Y:.3f} F1800", f"G1 Z{Z1:.3f} F600"]
for k in range(NL):
    z = Z1 + k * DZ
    p = P1 if k == 0 else PUP
    if k:
        L += [f"; ---- return to start (laser off)",
              f"G1 Z{z - DZ + HOP:.3f} F600", f"G1 X{X0:.3f} F{RET_F}", f"G1 Z{z:.3f} F600"]
    L += [f"; ---- layer {k+1}/{NL} X+ | Z{z:.3f} | laser {p}%",
          f"LASER_PWM S={S(p)}",
          f"G1 X{X0+LEN:.3f} E{e:.5f} F{SPEED*60:.0f}",
          f"G1 X{X0+LEN+OVERRUN:.3f} F{SPEED*60:.0f}",
          "LASER_PWM S=0"]
ztop = Z1 + (NL - 1) * DZ
L += ["LASER_DISARM", f"G1 Z{ztop + 30:.3f} F600", f"G1 X{PARK[0]} Y{PARK[1]} F1800", "; end - parked"]
open("test16_single_line_unidirectional.gcode", "w").write("\n".join(L) + "\n")
