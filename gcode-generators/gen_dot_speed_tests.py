#!/usr/bin/env python3
"""
gen_dot_speed_tests.py - dot-cure and speed x power tests for the syringe/laser latex printer.

  test4_dot_cure.gcode        4 laser powers (20..80 %) x 3 dot volumes (1x, 2x, 4x of a 1.85 x 0.15 mm disc)
                              dot extruded with the nozzle stationary, nozzle lifts, then moves X+ so the
                              laser spot (1 mm behind the nozzle) sweeps across the dot. G28 only, no G29.
  test5_speed_power.gcode     4 groups (20/40/60/80 % laser) x 5 speeds (5..25 mm/s), single 60 mm lines,
                              bead 1.85 x 0.15 mm. G28 then G29.
  ... tests 6-15 (see the functions below and docs/experiments.md)

Conventions carried over from gen_bead_tests.py:
  every laser-on move is X+ only, LASER_PWM S=0..255 (max_duty 1.0), LASER_ARM / LASER_DISARM once each,
  laser-off purge at X50->110 Y320 with 3x volume, nothing below X50, E in virtual 1.75 mm filament (M83).
"""
import math

FIL_AREA     = math.pi * 0.875 ** 2      # virtual 1.75 mm filament, mm^2
LASER_OFFSET = 1.0                       # mm, laser spot trails the nozzle in X (spot = nozzle X - 1)
ZHOP         = 1.0
TRAVEL_F     = 6000
BED_X_MIN    = 50.0

WIDTH, HEIGHT = 1.85, 0.15               # target bead
LINE_AREA     = WIDTH * HEIGHT           # 0.2775 mm^2 per mm of line
PURGE = dict(x=50.0, y=320.0, length=60.0, area=3 * LINE_AREA, z=0.2, speed=5.0)

POWERS = [20, 40, 60, 80]                # % duty

# --- test 4: dots -------------------------------------------------------------
DOT_BASE_VOL  = math.pi * (WIDTH / 2) ** 2 * HEIGHT   # 0.403 mm^3, disc 1.85 dia x 0.15
DOT_MULTS     = [1, 2, 4]                # columns; 1x is ~2 microsteps on a 30 mm syringe, may not appear
DOT_Z         = HEIGHT
DOT_E_F       = 120                      # mm/min virtual E for the stationary push
DOT_DWELL_MS  = 300                      # let the syringe catch up before lifting
DOT_LIFT      = 0.3                      # mm lift before moving, so the nozzle doesn't drag the dot
CURE_SPEED    = 5.0                      # mm/s spot sweep, same as the line tests
CURE_TRAVEL   = 3.0                      # nozzle moves d -> d+3, spot sweeps d-1 -> d+2 (dot edge at d+-0.925)
DOT_X         = [120.0, 135.0, 150.0]
DOT_Y0, DOT_PITCH = 140.0, 10.0

# --- test 5: speed x power lines ----------------------------------------------
SPEEDS        = [5, 10, 15, 20, 25]      # mm/s
LINE_Z        = HEIGHT
LINE_X0, LINE_LEN = 120.0, 90.0
OVERRUN       = LASER_OFFSET + 1.0       # laser stays on 2 mm past the bead end
LINE_PITCH    = 6.0
# start/end handling (test 5 only)
LINE_PRIME_E  = 0.6                      # virtual mm pushed with the nozzle stationary before each line (like unretract_extra_length)
PRIME_F       = 120                      # mm/min virtual E
COAST         = 1.0                      # last mm of each line moves without extrusion; stored syringe pressure fills it
WIPE          = 5.0                      # mm X+ at bead height after the line, laser on, no extrusion: smears ooze thin, stretches the bridge
BREAK_DX, BREAK_DZ = 2.0, 1.0            # then a diagonal X+/Z+ move (laser off) snaps the bridge while moving, not on one spot
GROUP_GAP     = 8.0                      # extra Y between power groups
LINE_Y0       = 100.0


def s_val(pct):
    return round(pct / 100 * 255)


class G:
    def __init__(self, title, notes, mesh):
        self.l = [f"; {title}"] + [f"; {n}" for n in notes]
        self.l += ["G90", "M83", "G28"]
        if mesh:
            self.l.append("G29")
        self.l += ["LASER_PWM S=0", "G1 Z5 F600"]
        self.z, self.x, self.e, self.t = 5.0, 0.0, 0.0, 0.0
        self.hop = ZHOP
        self.travel_f = TRAVEL_F

    def travel(self, x, y, z):
        self.l += [f"G1 Z{max(self.z, z) + self.hop:.3f} F600", f"G1 X{x:.3f} Y{y:.3f} F{self.travel_f}", f"G1 Z{z:.3f} F600"]
        self.z, self.x = z, x
        self.t += 2

    def bead(self, x0, x1, y, z, area, speed, pct, label):
        self.l.append(f"; ---- {label}")
        self.travel(x0, y, z)
        e = (x1 - x0) * area / FIL_AREA
        f = speed * 60
        if pct:
            self.l.append(f"LASER_PWM S={s_val(pct)}")
        self.l.append(f"G1 X{x1:.3f} Y{y:.3f} E{e:.5f} F{f:.0f}")
        self.e += e
        self.t += (x1 - x0) / speed
        if pct:
            self.l.append(f"G1 X{x1 + OVERRUN:.3f} F{f:.0f}")
            self.l.append("LASER_PWM S=0")
            self.t += OVERRUN / speed
            x1 += OVERRUN
        self.x = x1

    def line(self, x0, x1, y, z, area, speed, pct, label):
        """Test-5 line: stationary prime, bead with coast, laser-on wipe, diagonal bridge break."""
        self.l.append(f"; ---- {label}")
        self.travel(x0, y, z)
        f = speed * 60
        self.l.append(f"G1 E{LINE_PRIME_E:.3f} F{PRIME_F}")          # prime, laser off, nozzle still
        self.e += LINE_PRIME_E
        self.t += LINE_PRIME_E / PRIME_F * 60
        xc = x1 - COAST
        e = (xc - x0) * area / FIL_AREA
        self.l.append(f"LASER_PWM S={s_val(pct)}")
        self.l.append(f"G1 X{xc:.3f} E{e:.5f} F{f:.0f}")
        self.l.append(f"G1 X{x1:.3f} F{f:.0f}")                       # coast
        self.l.append(f"G1 X{x1 + WIPE:.3f} F{f:.0f}")                # wipe + laser overrun (>= {OVERRUN} mm)
        self.l.append("LASER_PWM S=0")
        xe = x1 + WIPE + BREAK_DX
        self.l.append(f"G1 X{xe:.3f} Z{z + BREAK_DZ:.3f} F{f:.0f}")   # diagonal lift, laser off
        self.e += e
        self.t += (x1 + WIPE - x0) / speed + math.hypot(BREAK_DX, BREAK_DZ) / speed
        self.x, self.z = xe, z + BREAK_DZ

    def dot(self, x, y, vol, pct, label):
        self.l.append(f"; ---- {label}")
        self.travel(x, y, DOT_Z)
        e = vol / FIL_AREA
        self.l.append(f"G1 E{e:.5f} F{DOT_E_F}")                    # stationary push
        self.l.append(f"G4 P{DOT_DWELL_MS}")
        self.l.append(f"G1 Z{DOT_Z + DOT_LIFT:.3f} F600")           # lift, laser still off
        self.z = DOT_Z + DOT_LIFT
        self.l.append(f"LASER_PWM S={s_val(pct)}")                  # spot now at x-1, just outside the dot
        self.l.append(f"G1 X{x + CURE_TRAVEL:.3f} F{CURE_SPEED * 60:.0f}")  # spot sweeps x-1 -> x+2
        self.l.append("LASER_PWM S=0")
        self.x = x + CURE_TRAVEL
        self.e += e
        self.t += 0.5 + DOT_DWELL_MS / 1000 + CURE_TRAVEL / CURE_SPEED

    def start(self, purge=None):
        self.l.append("LASER_ARM")
        p = purge or PURGE
        self.bead(p["x"], p["x"] + p["length"], p["y"], p["z"], p["area"], p["speed"], 0,
                  "purge, laser off (3x volume)")

    def end(self, path):
        self.l += ["LASER_PWM S=0", "LASER_DISARM", f"G1 Z{self.z + 30:.3f} F600", "; end"]
        self.l.insert(1, f"; total E {self.e:.2f} virtual mm = {self.e * FIL_AREA / 1000:.3f} mL | est. {self.t / 60:.1f} min")
        open(path, "w").write("\n".join(self.l) + "\n")


def test4():
    g = G("TEST 4 - dot cure: laser power x dot volume",
          [f"rows (front->back, Y{DOT_Y0:g}..): laser {POWERS} %  = LASER_PWM S {[s_val(p) for p in POWERS]}",
           f"columns (X {DOT_X}): dot volume {DOT_MULTS} x {DOT_BASE_VOL:.3f} mm^3 (disc {WIDTH} dia x {HEIGHT} mm)",
           f"each dot: stationary push at Z{DOT_Z}, dwell {DOT_DWELL_MS} ms, lift {DOT_LIFT} mm,",
           f"  then nozzle moves X+ {CURE_TRAVEL} mm at {CURE_SPEED} mm/s with laser on; spot ({LASER_OFFSET} mm behind) sweeps the dot",
           "no G29 (as requested): first layer depends on Z offset only"], mesh=False)
    g.start()
    for r, pct in enumerate(POWERS):
        y = DOT_Y0 + r * DOT_PITCH
        for x, m in zip(DOT_X, DOT_MULTS):
            g.dot(x, y, m * DOT_BASE_VOL, pct, f"laser {pct}% | dot {m}x = {m * DOT_BASE_VOL:.3f} mm^3 | X{x:g} Y{y:g}")
    g.end("test4_dot_cure.gcode")


def test5():
    g = G("TEST 5 - lines: laser power groups x print speed",
          [f"bead {WIDTH} x {HEIGHT} mm = {LINE_AREA:.4f} mm^2/mm, Z {LINE_Z}, lines {LINE_LEN:g} mm from X{LINE_X0:g}",
           f"groups front->back: laser {POWERS} %; inside each group front->back speeds {SPEEDS} mm/s",
           f"each line: {LINE_PRIME_E} virtual mm stationary prime (laser off), bead with last {COAST:g} mm coasted,",
           f"  {WIPE:g} mm wipe at bead height with laser on (covers the {LASER_OFFSET:g} mm spot offset), then diagonal",
           f"  X+{BREAK_DX:g}/Z+{BREAK_DZ:g} lift with laser off to break the nozzle-bead liquid bridge while moving",
           f"line pitch {LINE_PITCH:g} mm, +{GROUP_GAP:g} mm between groups",
           "energy per mm falls as 1/speed inside each group - that is the variable being tested"], mesh=True)
    g.start()
    y = LINE_Y0
    for pct in POWERS:
        for sp in SPEEDS:
            g.line(LINE_X0, LINE_X0 + LINE_LEN, y, LINE_Z, LINE_AREA, sp, pct,
                   f"laser {pct}% (S={s_val(pct)}) | {sp} mm/s | Y{y:g}")
            y += LINE_PITCH
        y += GROUP_GAP
    g.end("test5_speed_power.gcode")


# --- test 6: low power x slow speed, printed in REVERSE order (puddle check) ----
T6_POWERS   = [5, 15, 25, 35]            # % laser, front -> back on the bed (same layout as test 5)
T6_SPEEDS   = [2, 4, 6, 8, 10]           # mm/s, front -> back inside each group
T6_LEN      = 50.0                       # 90 - 40 mm
T6_HOP      = 3.0                        # higher travel hop so a hanging strand can't touch down


def test6(powers=T6_POWERS, speeds=T6_SPEEDS, num=6, path="test6_low_power_slow_reverse.gcode"):
    g = G(f"TEST {num} - low laser x slow speed, REVERSE print order (nozzle-puddle check)",
          [f"bed layout front->back: laser {powers} % = LASER_PWM S {[s_val(p) for p in powers]}; inside each group speeds {speeds} mm/s",
           f"PRINT ORDER IS REVERSED: starts at the back ({powers[-1]} % / {speeds[-1]} mm/s), ends at the front ({powers[0]} % / {speeds[0]} mm/s)",
           f"bead {WIDTH} x {HEIGHT} mm = {LINE_AREA:.4f} mm^2/mm, Z {LINE_Z}, lines {T6_LEN:g} mm from X{LINE_X0:g}",
           f"each line: {LINE_PRIME_E} virtual mm stationary prime (laser off), last {COAST:g} mm coasted, {WIPE:g} mm laser-on wipe,",
           f"  diagonal X+{BREAK_DX:g}/Z+{BREAK_DZ:g} lift (laser off); travel hop {T6_HOP:g} mm",
           "wipe the nozzle tip clean by hand before starting"], mesh=True)
    g.hop = T6_HOP
    g.start()
    slots, y = [], LINE_Y0
    for pct in powers:
        for sp in speeds:
            slots.append((y, pct, sp))
            y += LINE_PITCH
        y += GROUP_GAP
    for n, (y, pct, sp) in enumerate(reversed(slots), 1):
        g.line(LINE_X0, LINE_X0 + T6_LEN, y, LINE_Z, LINE_AREA, sp, pct,
               f"#{n} printed | laser {pct}% (S={s_val(pct)}) | {sp} mm/s | Y{y:g}")
    g.end(path)


# --- test 8: nozzle gap (layer height) x flow at fixed 15 % / 5 mm/s, REVERSE order ----
T8_PCT, T8_SPEED = 15, 5
T8_GAPS  = [0.05, 0.10, 0.15, 0.20, 0.25]   # mm nozzle-to-bed, front -> back groups
T8_FLOWS = [0.6, 0.8, 1.0, 1.2, 1.4]        # x the previous bead (1.85 x 0.15 = 0.2775 mm^2/mm), front -> back in group
T8_TRAVEL_F = 1800                          # 30 mm/s travel
T8_ACCEL    = 300                           # mm/s^2 for everything after G29 (vibration -> inconsistent lines)


def test8(gaps=T8_GAPS, flows=T8_FLOWS, num=8, path="test8_gap_x_flow.gcode", pitch=LINE_PITCH, y0=LINE_Y0):
    g = G(f"TEST {num} - nozzle gap x flow, laser 15 % / 5 mm/s, REVERSE print order",
          [f"bed layout front->back: gap {gaps} mm; inside each group flow {[int(f*100) for f in flows]} % "
           f"of {LINE_AREA:.4f} mm^2/mm = {[round(f*LINE_AREA, 3) for f in flows]}",
           "flow is NOT scaled with gap: volume per mm and gap are varied independently",
           f"line pitch {pitch:g} mm, +{GROUP_GAP:g} mm between groups, first line Y{y0:g}",
           f"laser {T8_PCT} % (S={s_val(T8_PCT)}), {T8_SPEED} mm/s, lines {T6_LEN:g} mm from X{LINE_X0:g}",
           f"PRINT ORDER IS REVERSED: starts at the back (gap {gaps[-1]} / {int(flows[-1]*100)} %), ends at the front",
           f"each line: {LINE_PRIME_E} virtual mm stationary prime (laser off), last {COAST:g} mm coasted, {WIPE:g} mm laser-on wipe,",
           f"  diagonal X+{BREAK_DX:g}/Z+{BREAK_DZ:g} lift (laser off); travel hop {T6_HOP:g} mm",
           "re-check Z offset with the paper test first: the 0.05 mm group is meaningless if Z is off by 0.05",
           f"travel {T8_TRAVEL_F // 60} mm/s, accel {T8_ACCEL} mm/s^2 (set after G29; stays until Klipper restart)",
           "wipe the nozzle tip clean by hand before starting"], mesh=True)
    g.hop = T6_HOP
    g.travel_f = T8_TRAVEL_F
    g.l.insert(g.l.index("G29") + 1, f"SET_VELOCITY_LIMIT ACCEL={T8_ACCEL}")
    g.start()
    slots, y = [], y0
    for gap in gaps:
        for fl in flows:
            slots.append((y, gap, fl))
            y += pitch
        y += GROUP_GAP
    for n, (y, gap, fl) in enumerate(reversed(slots), 1):
        g.line(LINE_X0, LINE_X0 + T6_LEN, y, gap, fl * LINE_AREA, T8_SPEED, T8_PCT,
               f"#{n} printed | gap {gap:.2f} mm | flow {int(fl*100)} % = {fl*LINE_AREA:.4f} mm^2/mm | Y{y:g}")
    g.end(path)


# --- test 10: 3 laser columns x nozzle gap groups x flow, 15 % ... 45 %, 5 mm/s ----
T10_POWERS = [15, 30, 45]                  # % laser, one column each, left -> right
T10_COL_X  = [70.0, 140.0, 210.0]          # line start X per column (line 50 mm + 5 wipe + 2 break = 57 mm)
T10_GAPS   = [0.5, 0.6, 0.7, 0.8]          # mm, groups front -> back
T10_FLOWS  = [2.0, 3.0, 4.0, 5.0]          # x 0.2775 mm^2/mm, front -> back inside each group
T10_PITCH, T10_Y0 = 10.0, 60.0


def test10(path="test10_power_cols_gap_flow.gcode"):
    g = G("TEST 10 - 3 laser columns x nozzle gap x flow, 5 mm/s",
          [f"columns left->right: laser {T10_POWERS} % = LASER_PWM S {[s_val(p) for p in T10_POWERS]}, lines start at X {T10_COL_X}",
           f"groups front->back: gap {T10_GAPS} mm; inside each group flow {[int(f*100) for f in T10_FLOWS]} % "
           f"of {LINE_AREA:.4f} = {[round(f*LINE_AREA, 3) for f in T10_FLOWS]} mm^2/mm",
           f"line pitch {T10_PITCH:g} mm, +{GROUP_GAP:g} mm between groups, first row Y{T10_Y0:g}",
           "PRINT ORDER: rows back -> front (reversed); each row prints all 3 columns left -> right,",
           "  so every laser power sees the same nozzle-puddle state (power not confounded with print order)",
           f"each line {T6_LEN:g} mm at {T8_SPEED} mm/s: {LINE_PRIME_E} virtual mm stationary prime (laser off), last {COAST:g} mm coasted,",
           f"  {WIPE:g} mm laser-on wipe, diagonal X+{BREAK_DX:g}/Z+{BREAK_DZ:g} lift (laser off); travel hop {T6_HOP:g} mm",
           f"travel {T8_TRAVEL_F // 60} mm/s, accel {T8_ACCEL} mm/s^2 (set after G29; stays until Klipper restart)",
           "uses ~2.4 mL latex: check the syringe fill; wipe the nozzle tip before starting"], mesh=True)
    g.hop = T6_HOP
    g.travel_f = T8_TRAVEL_F
    g.l.insert(g.l.index("G29") + 1, f"SET_VELOCITY_LIMIT ACCEL={T8_ACCEL}")
    g.start()
    rows, y = [], T10_Y0
    for gap in T10_GAPS:
        for fl in T10_FLOWS:
            rows.append((y, gap, fl))
            y += T10_PITCH
        y += GROUP_GAP
    n = 0
    for y, gap, fl in reversed(rows):
        for x0, pct in zip(T10_COL_X, T10_POWERS):
            n += 1
            g.line(x0, x0 + T6_LEN, y, gap, fl * LINE_AREA, T8_SPEED, pct,
                   f"#{n} printed | laser {pct}% (S={s_val(pct)}) | gap {gap:.2f} mm | flow {int(fl*100)} % = {fl*LINE_AREA:.4f} mm^2/mm | X{x0:g} Y{y:g}")
    g.end(path)


# --- test 11: stacked layers on a 0.7 mm first layer, 2 recipe columns ----
T11_COLS    = [(70.0, 30, 5.0), (140.0, 15, 2.0)]   # (start X, laser %, flow x 0.2775) left -> right
T11_FIRST_Z = 0.7
T11_LAYERS  = [3, 2]                               # groups front -> back
T11_DZ      = [0.025, 0.05, 0.075, 0.1, 0.5]       # layer height for layers 2+, front -> back in group
T11_PITCH, T11_Y0 = 10.0, 60.0
T11_PURGE   = dict(PURGE, y=300.0)                 # keep everything inside Y50-310


def test11(path="test11_layer_stacks.gcode"):
    g = G("TEST 11 - stacked lines: layer count x layer height, first layer Z0.7",
          [f"columns left->right: " + ", ".join(f"X{x:g}: laser {p} % (S={s_val(p)}), flow {int(f*100)} % = {f*LINE_AREA:.4f} mm^2/mm" for x, p, f in T11_COLS),
           f"every layer of a stack uses its column's laser and flow; layer 1 at Z{T11_FIRST_Z}, layer n at Z{T11_FIRST_Z} + (n-1) x dz",
           f"groups front->back: {T11_LAYERS} layers; inside each group dz {T11_DZ} mm front->back",
           f"line pitch {T11_PITCH:g} mm, +{GROUP_GAP:g} mm between groups, first row Y{T11_Y0:g}; purge at Y{T11_PURGE['y']:g}",
           "PRINT ORDER: rows back -> front; in each row the left stack (all layers) then the right stack",
           f"each layer: {T6_LEN:g} mm at {T8_SPEED} mm/s, {LINE_PRIME_E} virtual mm prime (laser off), {COAST:g} mm coast, {WIPE:g} mm laser-on wipe,",
           f"  diagonal X+{BREAK_DX:g}/Z+{BREAK_DZ:g} lift (laser off); travel hop {T6_HOP:g} mm",
           f"travel {T8_TRAVEL_F // 60} mm/s, accel {T8_ACCEL} mm/s^2 (set after G29; stays until Klipper restart)"], mesh=True)
    g.hop = T6_HOP
    g.travel_f = T8_TRAVEL_F
    g.l.insert(g.l.index("G29") + 1, f"SET_VELOCITY_LIMIT ACCEL={T8_ACCEL}")
    g.start(T11_PURGE)
    rows, y = [], T11_Y0
    for nl in T11_LAYERS:
        for dz in T11_DZ:
            rows.append((y, nl, dz))
            y += T11_PITCH
        y += GROUP_GAP
    n = 0
    for y, nl, dz in reversed(rows):
        for x0, pct, fl in T11_COLS:
            n += 1
            for k in range(nl):
                z = T11_FIRST_Z + k * dz
                g.line(x0, x0 + T6_LEN, y, z, fl * LINE_AREA, T8_SPEED, pct,
                       f"stack #{n} layer {k+1}/{nl} | laser {pct}% | flow {int(fl*100)} % | dz {dz} | Z{z:.3f} | X{x0:g} Y{y:g}")
    g.end(path)


# --- test 12: first layer fixed (15 %, 200 %, Z0.7); upper-layer laser x layer height; 2 vs 3 layers ----
T12_BASE_PCT, T12_FLOW = 15, 2.0                   # layer 1 recipe; upper layers use the same flow
T12_COLS    = [(70.0, 3)]                          # (start X, number of layers); 3-layer stacks only
T12_POWERS  = [15, 30, 45, 60]                     # % laser for layers 2+, groups front -> back
T12_DZ      = [0.2, 0.1, 0.075, 0.05, 0.025]       # layer height for layers 2+, front (tallest) -> back


def test12(path="test12_upper_layer_power_x_height.gcode"):
    g = G("TEST 12 - upper-layer laser x layer height; 2-layer and 3-layer stacks",
          [f"layer 1 always: Z{T11_FIRST_Z}, laser {T12_BASE_PCT} % (S={s_val(T12_BASE_PCT)}), flow {int(T12_FLOW*100)} % = {T12_FLOW*LINE_AREA:.4f} mm^2/mm",
           f"layers 2+: same flow, laser = group power, Z = {T11_FIRST_Z} + (n-1) x dz",
           "columns: " + ", ".join(f"X{x:g} = {nl} layers" for x, nl in T12_COLS),
           f"groups front->back: upper-layer laser {T12_POWERS} % = S {[s_val(p) for p in T12_POWERS]}",
           f"inside each group dz front->back: {T12_DZ} mm (tallest at the front)",
           f"line pitch {T11_PITCH:g} mm, +{GROUP_GAP:g} mm between groups, first row Y{T11_Y0:g}; purge at Y{T11_PURGE['y']:g}",
           "PRINT ORDER: rows back -> front; in each row the left stack (all layers) then the right stack",
           f"each layer: {T6_LEN:g} mm at {T8_SPEED} mm/s, {LINE_PRIME_E} virtual mm prime (laser off), {COAST:g} mm coast, {WIPE:g} mm laser-on wipe,",
           f"  diagonal X+{BREAK_DX:g}/Z+{BREAK_DZ:g} lift (laser off); travel hop {T6_HOP:g} mm",
           f"travel {T8_TRAVEL_F // 60} mm/s, accel {T8_ACCEL} mm/s^2 (set after G29; stays until Klipper restart)"], mesh=True)
    g.hop = T6_HOP
    g.travel_f = T8_TRAVEL_F
    g.l.insert(g.l.index("G29") + 1, f"SET_VELOCITY_LIMIT ACCEL={T8_ACCEL}")
    g.start(T11_PURGE)
    rows, y = [], T11_Y0
    for pct in T12_POWERS:
        for dz in T12_DZ:
            rows.append((y, pct, dz))
            y += T11_PITCH
        y += GROUP_GAP
    n = 0
    for y, pct, dz in reversed(rows):
        for x0, nl in T12_COLS:
            n += 1
            for k in range(nl):
                z = T11_FIRST_Z + k * dz
                lp = T12_BASE_PCT if k == 0 else pct
                g.line(x0, x0 + T6_LEN, y, z, T12_FLOW * LINE_AREA, T8_SPEED, lp,
                       f"stack #{n} layer {k+1}/{nl} | laser {lp}% | flow {int(T12_FLOW*100)} % | dz {dz} | Z{z:.3f} | X{x0:g} Y{y:g}")
    g.end(path)


# --- test 13: like test 12 (3 layers, one column) but upper laser 30/40/50 % and printed LAYER BY LAYER ----
T13_POWERS = [30, 40, 50]                          # % laser for layers 2-3, groups front -> back
T13_NL, T13_X0 = 3, 150.0                       # X150 so the previous plate (X50-127) can stay on the bed
T13_PURGE = dict(PURGE, x=150.0, y=300.0)          # purge moved right too, clear of the old purge at X50-110


def test13(path="test13_layerwise_power_x_height.gcode"):
    g = G("TEST 13 - 3-layer stacks printed LAYER BY LAYER: upper-layer laser x layer height",
          [f"layer 1 always: Z{T11_FIRST_Z}, laser {T12_BASE_PCT} % (S={s_val(T12_BASE_PCT)}), flow {int(T12_FLOW*100)} % = {T12_FLOW*LINE_AREA:.4f} mm^2/mm",
           f"layers 2-3: same flow, laser = group power, Z = {T11_FIRST_Z} + (n-1) x dz; one column at X{T13_X0:g}",
           f"groups front->back: upper-layer laser {T13_POWERS} % = S {[s_val(p) for p in T13_POWERS]}",
           f"inside each group dz front->back: {T12_DZ} mm (tallest at the front)",
           f"line pitch {T11_PITCH:g} mm, +{GROUP_GAP:g} mm between groups, first row Y{T11_Y0:g}; purge X{T13_PURGE['x']:g}->{T13_PURGE['x']+T13_PURGE['length']:g} at Y{T13_PURGE['y']:g}",
           "PRINT ORDER: all of layer 1 (rows back -> front), then all of layer 2, then all of layer 3",
           f"each line: {T6_LEN:g} mm at {T8_SPEED} mm/s, {LINE_PRIME_E} virtual mm prime (laser off), {COAST:g} mm coast, {WIPE:g} mm laser-on wipe,",
           f"  diagonal X+{BREAK_DX:g}/Z+{BREAK_DZ:g} lift (laser off); travel hop {T6_HOP:g} mm",
           f"travel {T8_TRAVEL_F // 60} mm/s, accel {T8_ACCEL} mm/s^2 (set after G29; stays until Klipper restart)",
           "wipe the nozzle tip clean before starting"], mesh=True)
    g.hop = T6_HOP
    g.travel_f = T8_TRAVEL_F
    g.l.insert(g.l.index("G29") + 1, f"SET_VELOCITY_LIMIT ACCEL={T8_ACCEL}")
    g.start(T13_PURGE)
    rows, y = [], T11_Y0
    for pct in T13_POWERS:
        for dz in T12_DZ:
            rows.append((y, pct, dz))
            y += T11_PITCH
        y += GROUP_GAP
    for k in range(T13_NL):
        g.l.append(f"; ======== LAYER {k+1} of {T13_NL} ========")
        for y, pct, dz in reversed(rows):
            z = T11_FIRST_Z + k * dz
            lp = T12_BASE_PCT if k == 0 else pct
            g.line(T13_X0, T13_X0 + T6_LEN, y, z, T12_FLOW * LINE_AREA, T8_SPEED, lp,
                   f"layer {k+1}/{T13_NL} | upper laser group {pct}% | this layer {lp}% | dz {dz} | Z{z:.3f} | Y{y:g}")
    g.end(path)


# --- test 14: 40 % upper layers only, 10 layers, layer by layer, behind test 13 on the same bed ----
T14_PCT, T14_NL, T14_X0, T14_Y0 = 40, 10, 150.0, 230.0   # rows Y230-270, above test 13 (Y60-216)
T14_PURGE = dict(PURGE, x=220.0, y=300.0)                 # clear of old purges at X50-110 and X150-210, Y300


def test14(path="test14_40pct_10_layers.gcode"):
    g = G("TEST 14 - 10-layer stacks, upper layers 40 %, printed LAYER BY LAYER",
          [f"layer 1: Z{T11_FIRST_Z}, laser {T12_BASE_PCT} % (S={s_val(T12_BASE_PCT)}); layers 2-{T14_NL}: laser {T14_PCT} % (S={s_val(T14_PCT)}); all flow {int(T12_FLOW*100)} % = {T12_FLOW*LINE_AREA:.4f} mm^2/mm",
           f"layer n at Z = {T11_FIRST_Z} + (n-1) x dz; rows front->back dz {T12_DZ} mm, Y{T14_Y0:g}..{T14_Y0 + T11_PITCH*(len(T12_DZ)-1):g}, X{T14_X0:g}",
           f"purge X{T14_PURGE['x']:g}->{T14_PURGE['x']+T14_PURGE['length']:g} at Y{T14_PURGE['y']:g}",
           f"PRINT ORDER: all of layer 1 (rows back -> front), then layer 2, ... layer {T14_NL}",
           f"each line: {T6_LEN:g} mm at {T8_SPEED} mm/s, {LINE_PRIME_E} virtual mm prime (laser off), {COAST:g} mm coast, {WIPE:g} mm laser-on wipe,",
           f"  diagonal X+{BREAK_DX:g}/Z+{BREAK_DZ:g} lift (laser off); travel hop {T6_HOP:g} mm",
           f"travel {T8_TRAVEL_F // 60} mm/s, accel {T8_ACCEL} mm/s^2 (set after G29; stays until Klipper restart)",
           "wipe the nozzle tip clean before starting"], mesh=True)
    g.hop = T6_HOP
    g.travel_f = T8_TRAVEL_F
    g.l.insert(g.l.index("G29") + 1, f"SET_VELOCITY_LIMIT ACCEL={T8_ACCEL}")
    g.start(T14_PURGE)
    rows = [(T14_Y0 + i * T11_PITCH, dz) for i, dz in enumerate(T12_DZ)]
    for k in range(T14_NL):
        g.l.append(f"; ======== LAYER {k+1} of {T14_NL} ========")
        for y, dz in reversed(rows):
            z = T11_FIRST_Z + k * dz
            lp = T12_BASE_PCT if k == 0 else T14_PCT
            g.line(T14_X0, T14_X0 + T6_LEN, y, z, T12_FLOW * LINE_AREA, T8_SPEED, lp,
                   f"layer {k+1}/{T14_NL} | laser {lp}% | dz {dz} | Z{z:.3f} | Y{y:g}")
    g.end(path)


# --- test 15: BIDIRECTIONAL stacks (no travel between layers), no prime ----
T15_X0, T15_LEN = 220.0, 50.0
T15_NL          = 10                               # even -> every stack ends back at the left end
T15_DZ          = [0.05, 0.10, 0.15]               # layer height, front -> back
T15_Y           = [230.0, 240.0, 250.0]
T15_PURGE       = dict(PURGE, x=220.0, y=310.0)    # old purges at Y300 (X50-110, X150-210, X220-280)


def test15(path="test15_bidirectional_stacks.gcode"):
    area = T12_FLOW * LINE_AREA
    g = G("TEST 15 - BIDIRECTIONAL 10-layer stacks: odd layers X+, even layers X-, no travel between layers",
          [f"layer 1: Z{T11_FIRST_Z}, laser {T12_BASE_PCT} % (S={s_val(T12_BASE_PCT)}); layers 2-{T15_NL}: laser {T14_PCT} % (S={s_val(T14_PCT)}); flow {int(T12_FLOW*100)} % = {area:.4f} mm^2/mm",
           f"rows front->back: dz {T15_DZ} mm at Y {T15_Y}; lines X{T15_X0:g} <-> X{T15_X0+T15_LEN:g}",
           "each stack: layer 1 X+, step up dz in place (laser off), layer 2 X- back, ... ends at the left end after layer 10",
           "no stationary prime, no wipe/overrun between layers; only travel is left end -> next row's left end (hop)",
           "NOTE: laser spot is 1 mm behind the nozzle on X+ passes but 1 mm AHEAD on X- passes, so an X- layer is",
           "  cured from above by the next X+ pass; the last layer (X-) is followed by a laser-only X+ cure pass",
           f"PRINT ORDER: rows back -> front; purge X{T15_PURGE['x']:g}->{T15_PURGE['x']+T15_PURGE['length']:g} at Y{T15_PURGE['y']:g}",
           f"travel {T8_TRAVEL_F // 60} mm/s, accel {T8_ACCEL} mm/s^2 (set after G29; stays until Klipper restart)",
           "wipe the nozzle tip clean before starting"], mesh=True)
    g.hop = T6_HOP
    g.travel_f = T8_TRAVEL_F
    g.l.insert(g.l.index("G29") + 1, f"SET_VELOCITY_LIMIT ACCEL={T8_ACCEL}")
    g.start(T15_PURGE)
    f = T8_SPEED * 60
    xl, xr = T15_X0, T15_X0 + T15_LEN
    e_pass = T15_LEN * area / FIL_AREA
    for y, dz in reversed(list(zip(T15_Y, T15_DZ))):
        g.l.append(f"; ======== STACK dz {dz} | Y{y:g} ========")
        g.travel(xl, y, T11_FIRST_Z)
        z = T11_FIRST_Z
        for k in range(T15_NL):
            pct = T12_BASE_PCT if k == 0 else T14_PCT
            if k > 0:
                z = T11_FIRST_Z + k * dz
                g.l.append(f"G1 Z{z:.3f} F600")                      # step up in place, laser off
                g.z = z
            xe = xr if k % 2 == 0 else xl
            g.l.append(f"; ---- layer {k+1}/{T15_NL} {'X+' if k % 2 == 0 else 'X-'} | laser {pct}% | dz {dz} | Z{z:.3f} | Y{y:g}")
            g.l.append(f"LASER_PWM S={s_val(pct)}")
            g.l.append(f"G1 X{xe:.3f} E{e_pass:.5f} F{f:.0f}")
            g.l.append("LASER_PWM S=0")
            g.e += e_pass
            g.t += T15_LEN / T8_SPEED + 0.2
        # last layer was X-: its spot ran ahead, so give it a laser-only X+ cure pass at the same Z
        g.l.append(f"; ---- final cure pass X+ (no extrusion) | laser {T14_PCT}% | Z{z:.3f}")
        g.l.append(f"LASER_PWM S={s_val(T14_PCT)}")
        g.l.append(f"G1 X{xr + LASER_OFFSET + 1:.3f} F{f:.0f}")
        g.l.append("LASER_PWM S=0")
        g.l.append(f"G1 X{xr + LASER_OFFSET + 1 + BREAK_DX:.3f} Z{z + BREAK_DZ:.3f} F{f:.0f}")
        g.z = z + BREAK_DZ
        g.t += (T15_LEN + 2) / T8_SPEED
    g.end(path)


if __name__ == "__main__":
    test4()
    test5()
    test6()
    test6(powers=[10, 14, 18, 22], speeds=[4, 6, 8], num=7, path="test7_power_10-22_reverse.gcode")
    test8()
    test8(gaps=[0.2, 0.3, 0.4, 0.5], flows=[0.5, 1.0, 1.5, 2.0, 2.5, 3.0], num=9, path="test9_gap_x_flow_wide.gcode",
          pitch=8.0, y0=60.0)   # wider pitch: 300 % lines may spread past 6 mm
    test10()
    test11()
    test12()
    test13()
    test14()
    test15()
