#!/usr/bin/env python3
"""
unidir_laser.py - OrcaSlicer post-processor for a side-mounted curing laser.

What it does
  * Every extrusion move is made to travel in the "allowed" half-plane, i.e. with a
    positive component along PREF_DIR (direction from laser spot toward nozzle, so
    the spot trails the bead).  Polylines are split where they turn against PREF_DIR
    and the offending runs are printed reversed, with a laser-off travel between.
  * Each extruding run is wrapped in LASER_ON / LASER_OFF, optionally followed by a
    dry overrun so the trailing spot reaches the end of the bead.
  * Extrusion volume is preserved exactly (every segment keeps its own E value).

Orca setup (Process -> Others -> Post-processing scripts), one line:
    "C:\\Path\\to\\python.exe" "C:\\Path\\to\\unidir_laser.py";
Orca passes the G-code path as the last argument; the file is rewritten in place.

Per-object laser power: name an object in Orca with a token like "S128"
(e.g. "line S128") and enable Printer -> Others -> "Exclude objects". Every
LASER_ON inside that object becomes "LASER_ON S=128". Objects without a token use
the stored default (SET_GCODE_VARIABLE MACRO=LASER_ON VARIABLE=s VALUE=..).

Required Orca settings: relative E (M83, default for Klipper flavor), arc fitting OFF,
spiral vase OFF, wipe OFF.  Klipper needs LASER_ON / LASER_OFF macros and
[firmware_retraction] (G10/G11).
"""
import math
import re
import sys

# ------------------------------- USER PARAMETERS ------------------------------------
PREF_DIR_DEG = 0.0   # allowed print direction, deg CCW from +X (spot -> nozzle direction)
PERP_TOL_DEG = 10.0  # segments within this angle of perpendicular never split a run
MIN_RUN_MM   = 1.0   # runs shorter than this are not split off (Klipper output_pin
                     # schedules updates >= ~100 ms apart; 1 mm @ 10 mm/s = 100 ms)
OVERRUN_MM   = 1.0   # spot-to-nozzle distance: dry move so spot covers bead end
ZHOP_MM      = 1.0   # lift for inserted travels (0 = none)
TRAVEL_F     = 9000  # mm/min for inserted travels
RETRACT      = ("G10", "G11")  # firmware retract/unretract; None to disable
LASER_ON     = "LASER_ON"
LASER_OFF    = "LASER_OFF"
# -------------------------------------------------------------------------------------

UX, UY = math.cos(math.radians(PREF_DIR_DEG)), math.sin(math.radians(PREF_DIR_DEG))
SIN_TOL = math.sin(math.radians(PERP_TOL_DEG))
OBJ_POWER_RE = re.compile(r"(?:^|_)S(\d{1,3})(?=_|$)", re.I)
BREAK_TAGS = (";TYPE:", "; FEATURE:", ";LAYER_CHANGE", ";LAYER:", "; CHANGE_LAYER")


def parse(line):
    code = line.split(";", 1)[0].strip()
    if not code:
        return None, {}
    parts = code.split()
    params = {}
    for tok in parts[1:]:
        try:
            params[tok[0].upper()] = float(tok[1:])
        except (ValueError, IndexError):
            pass
    return parts[0].upper(), params


def seg_len(s):
    return math.hypot(s[2] - s[0], s[3] - s[1])


def classify(s):
    L = seg_len(s)
    if L < 1e-9:
        return 0
    c = ((s[2] - s[0]) * UX + (s[3] - s[1]) * UY) / L
    if abs(c) < SIN_TOL:
        return 0
    return 1 if c > 0 else -1


def split_runs(chain):
    """chain: list of (x0,y0,x1,y1,e,f). Returns list of [k, segs]."""
    runs = []
    for s in chain:
        k = classify(s)
        if runs and (k == 0 or runs[-1][0] in (0, k)):
            if runs[-1][0] == 0:
                runs[-1][0] = k
            runs[-1][1].append(s)
        else:
            runs.append([k, [s]])
    # absorb short runs into their predecessor, then re-merge equal neighbours
    changed = True
    while changed and len(runs) > 1:
        changed = False
        for i in range(1, len(runs)):
            if sum(seg_len(s) for s in runs[i][1]) < MIN_RUN_MM:
                runs[i - 1][1].extend(runs[i][1])
                del runs[i]
                changed = True
                break
        merged = [runs[0]]
        for r in runs[1:]:
            if r[0] == merged[-1][0] or r[0] == 0:
                merged[-1][1].extend(r[1])
            else:
                merged.append(r)
        runs = merged
    # first run might still be short & alone - fine.
    out = []
    for k, segs in runs:
        if k < 0:
            segs = [(s[2], s[3], s[0], s[1], s[4], s[5]) for s in reversed(segs)]
        out.append(segs)
    return out


def travel(out, cur, x, y, z):
    if RETRACT:
        out.append(RETRACT[0])
    if ZHOP_MM > 0:
        out.append(f"G1 Z{z + ZHOP_MM:.3f} F{TRAVEL_F}")
    out.append(f"G1 X{x:.3f} Y{y:.3f} F{TRAVEL_F}")
    if ZHOP_MM > 0:
        out.append(f"G1 Z{z:.3f} F{TRAVEL_F}")
    if RETRACT:
        out.append(RETRACT[1])


def process(lines):
    out = [f"{LASER_OFF} ; unidir_laser: safe start"]
    x = y = z = 0.0
    feed = 1200.0
    chain, chain_comments = [], []
    chain_start = None
    absolute_e_warned = False
    obj_power = None
    width = [0.6]                      # updated from Orca ;WIDTH: comments
    cover = {"ok": 0.0, "all": 0.0}    # bead length the trailing spot can reach

    def laser_on_cmd():
        if obj_power is None:
            return LASER_ON
        return f"{LASER_ON} S={obj_power}"

    def next_is_xy_travel(i):
        for j in range(i, len(lines)):
            cmd, p = parse(lines[j])
            if cmd in ("G0", "G1", "G2", "G3"):
                return "X" in p and "Y" in p
        return True

    def flush(i):
        nonlocal chain, chain_comments
        if not chain:
            return
        out.extend(chain_comments)
        cx, cy = chain[0][0], chain[0][1]
        last_f = None
        for segs in split_runs(chain):
            sx, sy = segs[0][0], segs[0][1]
            if math.hypot(sx - cx, sy - cy) > 1e-3:
                travel(out, (cx, cy), sx, sy, z)
                last_f = None
            out.append(laser_on_cmd())
            for s in segs:
                L = seg_len(s)
                if L > 0:
                    c = ((s[2] - s[0]) * UX + (s[3] - s[1]) * UY) / L
                    sin = math.sqrt(max(0.0, 1 - c * c))
                    cover["all"] += L
                    if c > 0 and OVERRUN_MM * sin <= width[0] / 2:
                        cover["ok"] += L
                f = f" F{s[5]:.0f}" if s[5] != last_f else ""
                last_f = s[5]
                out.append(f"G1 X{s[2]:.3f} Y{s[3]:.3f} E{s[4]:.5f}{f}")
            cx, cy = segs[-1][2], segs[-1][3]
            if OVERRUN_MM > 0:
                L = seg_len(segs[-1]) or 1.0
                ox = cx + (segs[-1][2] - segs[-1][0]) / L * OVERRUN_MM
                oy = cy + (segs[-1][3] - segs[-1][1]) / L * OVERRUN_MM
                out.append(f"G1 X{ox:.3f} Y{oy:.3f}")
                cx, cy = ox, oy
            out.append(LASER_OFF)
        ex, ey = chain[-1][2], chain[-1][3]
        if math.hypot(ex - cx, ey - cy) > 1e-3 and not next_is_xy_travel(i):
            travel(out, (cx, cy), ex, ey, z)  # restore position Orca expects
        out.append(f"G1 F{feed:.0f}")
        chain, chain_comments = [], []

    for i, raw in enumerate(lines):
        line = raw.rstrip("\n")
        cmd, p = parse(line)
        stripped = line.strip()

        if cmd is None:  # comment / blank
            if stripped.startswith(";WIDTH:"):
                try:
                    width[0] = float(stripped[7:])
                except ValueError:
                    pass
            if chain and not stripped.startswith(BREAK_TAGS):
                chain_comments.append(line)
                continue
            flush(i)
            out.append(line)
            continue

        if cmd == "M82" and not absolute_e_warned:
            sys.stderr.write("unidir_laser: absolute E (M82) found - enable relative E in Orca\n")
            absolute_e_warned = True

        if cmd in ("G0", "G1"):
            if "F" in p:
                feed = p["F"]
            has_xy = "X" in p or "Y" in p
            nx, ny = p.get("X", x), p.get("Y", y)
            e = p.get("E", 0.0)
            z_change = "Z" in p and abs(p["Z"] - z) > 1e-6
            if has_xy and e > 0 and not z_change:
                chain.append((x, y, nx, ny, e, feed))
                x, y = nx, ny
                continue
            if not has_xy and "E" not in p and "Z" not in p and chain:
                continue  # pure feedrate change inside a chain (carried per segment)
            flush(i)
            x, y = nx, ny
            if "Z" in p:
                z = p["Z"]
            out.append(line)
            continue

        flush(i)
        if cmd == "EXCLUDE_OBJECT_START":
            m = re.search(r"NAME=(\S+)", line, re.I)
            pm = OBJ_POWER_RE.search(m.group(1)) if m else None
            obj_power = min(int(pm.group(1)), 255) if pm else None
        elif cmd == "EXCLUDE_OBJECT_END":
            obj_power = None
        if cmd in ("G2", "G3"):
            sys.stderr.write("unidir_laser: arc moves found - disable arc fitting in Orca\n")
            x, y = p.get("X", x), p.get("Y", y)
        out.append(line)

    flush(len(lines))
    out.append(f"{LASER_OFF} ; unidir_laser: safe end")
    if cover["all"] > 0:
        pct = 100 * cover["ok"] / cover["all"]
        msg = (f"unidir_laser: {pct:.1f} % of {cover['all']:.0f} mm bead is inside the laser "
               f"cone (spot offset {OVERRUN_MM} mm); the rest runs too far off the laser axis to cure")
        out.insert(0, "; " + msg)
        sys.stderr.write(msg + "\n")
    return out


def main():
    path = sys.argv[-1]
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        lines = fh.readlines()
    result = process(lines)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(result) + "\n")


if __name__ == "__main__":
    main()
