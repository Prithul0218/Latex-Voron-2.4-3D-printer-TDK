#!/usr/bin/env python3
"""
gen_bead_tests.py - bead-geometry calibration for the syringe/laser latex printer.
  test1_volume_sweep.gcode   8 single lines, bead area 0.10 .. 0.45 mm2, nozzle gap 0.2 mm
  test2_gap_sweep.gcode      8 single lines, bead area 0.28 mm2, nozzle gap 0.05 .. 0.40 mm
  test3_pitch_patches.gcode  7 single-layer 15x15 mm patches, line pitch 0.70 .. 1.00 x width
Every line printed X- -> X+, laser PWM on while laying + overrun, power pin only at start/end.
"""
import math

FIL_AREA   = math.pi * 0.875 ** 2     # virtual 1.75 mm filament
SPEED      = 5.0                       # mm/s
LASER_PCT  = 60.0                      # % duty (max_duty 1.0 in LASER_PWM)
OVERRUN    = 10.0                      # mm laser-on past bead end
ZHOP       = 1.0
TRAVEL_F   = 6000
PURGE      = dict(x=50.0, y=320.0, length=60.0, area=0.84, z=0.2)   # 3x a 0.28 bead
S_VAL      = round(LASER_PCT / 100 * 255, 2)

T1_AREAS   = [0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.45]
T1_GAP     = 0.20
T2_AREA    = 0.28
T2_GAPS    = [0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40]
T3_AREA    = 0.28
T3_WIDTH   = 1.8                       # measured spread width; update after test 1
T3_GAP     = 0.15                      # update after test 2
T3_FACTORS = [0.70, 0.75, 0.80, 0.85, 0.90, 0.95, 1.00]
LINE_X0, LINE_LEN, LINE_Y0, LINE_PITCH = 120.0, 60.0, 140.0, 8.0


class G:
    def __init__(self, title, notes):
        self.l = [f"; {title}"] + [f"; {n}" for n in notes] + ["; every line X- -> X+ | laser LASER_PWM S=%g (%g %% duty) + %g mm overrun" % (S_VAL, LASER_PCT, OVERRUN)]
        self.l += ["G90", "M83", "G28", "LASER_PWM S=0", "G1 Z5 F600"]
        self.z = 5.0; self.e = 0.0; self.t = 0.0
    def travel(self, x, y, z):
        self.l += [f"G1 Z{max(self.z, z) + ZHOP:.3f} F600", f"G1 X{x:.3f} Y{y:.3f} F{TRAVEL_F}", f"G1 Z{z:.3f} F600"]
        self.z = z; self.t += 2
    def bead(self, x0, x1, y, z, area, laser, label=None):
        if label: self.l.append(f"; ---- {label}")
        self.travel(x0, y, z)
        e = (x1 - x0) * area / FIL_AREA
        if laser: self.l.append(f"LASER_PWM S={S_VAL:g}")
        self.l.append(f"G1 X{x1:.3f} Y{y:.3f} E{e:.5f} F{SPEED * 60:.0f}")
        self.e += e; self.t += (x1 - x0) / SPEED
        if laser:
            self.l.append(f"G1 X{x1 + OVERRUN:.3f} F{SPEED * 60:.0f}")
            self.l.append("LASER_PWM S=0"); self.t += OVERRUN / SPEED
    def start(self):
        self.l.append("LASER_ARM")
        p = PURGE
        self.bead(p["x"], p["x"] + p["length"], p["y"], p["z"], p["area"], False, "purge, laser off (3x volume)")
    def end(self):
        self.l += ["LASER_PWM S=0", "LASER_DISARM", f"G1 Z{self.z + 30:.3f} F600", "; end"]
        self.l.insert(1, f"; total E {self.e:.1f} virtual mm = {self.e * FIL_AREA / 1000:.2f} mL | est. {self.t / 60:.0f} min")
        return self.l


def test1():
    g = G("TEST 1 - VOLUME SWEEP", [f"nozzle gap {T1_GAP} mm, {SPEED} mm/s, lines front->back: " + ", ".join(f"{a:.2f}" for a in T1_AREAS) + " mm2 per mm",
                                   "measure each line: wet width, cured height"])
    g.start()
    for i, a in enumerate(T1_AREAS):
        g.bead(LINE_X0, LINE_X0 + LINE_LEN, LINE_Y0 + i * LINE_PITCH, T1_GAP, a, True, f"line {i + 1}: area {a:.2f} mm2  y={LINE_Y0 + i * LINE_PITCH:g}")
    return g.end()


def test2():
    g = G("TEST 2 - NOZZLE GAP SWEEP", [f"bead area {T2_AREA} mm2, {SPEED} mm/s, lines front->back gap: " + ", ".join(f"{z:.2f}" for z in T2_GAPS) + " mm",
                                       "pick the gap with the smoothest continuous line = layer height"])
    g.start()
    for i, z in enumerate(T2_GAPS):
        g.bead(LINE_X0, LINE_X0 + LINE_LEN, LINE_Y0 + i * LINE_PITCH, z, T2_AREA, True, f"line {i + 1}: gap {z:.2f} mm  y={LINE_Y0 + i * LINE_PITCH:g}")
    return g.end()


def test3():
    g = G("TEST 3 - LINE PITCH PATCHES", [f"bead area {T3_AREA} mm2, gap {T3_GAP} mm, width {T3_WIDTH} mm, patches front->back pitch factor: " + ", ".join(f"{f:.2f}" for f in T3_FACTORS),
                                         "15 x 15 mm each; pick the tightest pitch with no gaps or ridges"])
    g.start()
    y = 80.0
    for i, fct in enumerate(T3_FACTORS):
        pitch = T3_WIDTH * fct
        n = int(round((15.0 - T3_WIDTH) / pitch)) + 1
        g.l.append(f"; ==== patch {i + 1}: pitch {pitch:.3f} mm ({fct:.2f} x {T3_WIDTH}) , {n} lines, y {y:g}..{y + 15:g}")
        for k in range(n):
            yy = y + T3_WIDTH / 2 + k * pitch
            g.bead(LINE_X0, LINE_X0 + 15.0, yy, T3_GAP, T3_AREA, True)
        y += 23.0
    return g.end()


if __name__ == "__main__":
    for name, fn in (("test1_volume_sweep.gcode", test1), ("test2_gap_sweep.gcode", test2), ("test3_pitch_patches.gcode", test3)):
        out = fn()
        open(name, "w").write("\n".join(out) + "\n")
        print(name, "|", out[1])
