# Experiments: summary

Short summary of the test prints made with the G-code from [`../gcode-generators/`](../gcode-generators/). The full analysis is in the TDK paper.

All tests: 1.04 mm needle, matte ceramic tile bed, black-pigmented water-based latex (type and solids content: to be added). Flow percentages in tests 4–16 refer to 0.2775 mm²/mm (a 1.85 × 0.15 mm bead).

## Early prints
| Test | Setup | Result |
|---|---|---|
| Power ladder | 0–50 % duty in 5 % steps, 0.6 × 0.6 mm bead, 5 mm/s | 10–30 % gave decent lines; above that the width became inconsistent and the highest powers burned the latex. A 0.6 × 0.6 mm bead spread to ≈1.8 mm wide |
| Block 80 × 10 × 4 mm | 0.2 mm layers × 1.5 mm width, 60 %, X+ only | Cured well along most of each line; a blob on the needle tip dragged uncured latex to the line ends. **Shore A 30–35** (indicative: thin print folded over itself) |
| Post-processor dogbone | Orca dogbone through the post-processor, printed without laser | Clean dogbone outline; line order and angled grip lines handled correctly |

## Process-parameter campaign (tests 4–16)
| Test | Variables | Key observation |
|---|---|---|
| 5 | Laser 20–80 % × speed 5–25 mm/s, 0.15 mm gap | Lines 2.3–3.95 mm wide; width followed print order (tip blob) more than power; start-of-line breakup at ≥15 mm/s; ringing above 5 mm/s from the feed tube |
| 6–7 | Low power × slow speed, reversed order | Tip blobs confirmed; thick uncured line ends. Settled on 15 %, 5 mm/s |
| 8–9 | Nozzle gap × flow | 0.5 mm gap best; width ≈3.7 mm almost independent of flow (50–300 %) |
| 10 | Laser 15/30/45 % × gap 0.5–0.8 × flow 200–500 % | 0.7 mm gap best; clean first layers at 15 % / 200 % (4.2 mm wide) and 30 % / 500 % (4.42 mm) |
| 11–12 | Stacked layers, stack by stack | 2 layers fine; 3rd layer did not cure and slid off; 15 % too low for upper layers |
| 13 | Upper-layer laser 30/40/50 %, layer by layer | 40 % best; 3 layers = 0.08 mm total (≈0.027 mm per cured layer) |
| 14–16 | 10-layer stacks, bidirectional stacks, single-line stacks | Tip blob dominated; later runs affected by aged latex |

## Main findings so far
1. The latex sets its own bead width; slicer settings must follow it (≈3.7–4.4 mm at 0.5–0.7 mm gap).
2. Too small a nozzle gap (≤0.15 mm) flattens and widens the bead.
3. The laser power needed rises with volume per mm, and upper layers need more power than the first.
4. Layer-by-layer printing (minutes between layers) works better than stack-by-stack (seconds).
5. Build-up per cured layer is very low, consistent with high water content.
6. Nozzle-tip wetting is the dominant process defect.
7. Laser-only curing produced a solid elastomer (Shore A 30–35, indicative).

Later tests (17+: taller layers, cubes, drying time) are described in the paper.
