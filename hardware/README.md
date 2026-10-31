# Hardware

**To be added:** CAD files, bill of materials, wiring diagram and photos.

## Summary (from the development log)
| Item | Value |
|---|---|
| Base machine | Voron 2.4, 350 mm |
| Boards | BTT Manta M8P; BTT EBB36 toolhead board over CAN |
| Syringe extruder | 30 mm ID syringe, M6 × 1 mm threaded rod, plain nut, direct drive, NEMA 17 (1.8°, 32 microsteps) |
| Nozzle | 1.04 mm ID metal Luer-lock needle |
| Refill | 3-way stopcock at the syringe Luer lock (nozzle / filling tube) |
| Laser | NEJE N30820, 5.5 W optical (manufacturer rating), TTL PWM; defocused, rectangular spot ≈1 mm behind the needle on the X− side |
| Laser wiring | 12 V supply switched by EBB36 PB13; PWM on PB9 |
| Bed | Matte ceramic floor tile |

## Placeholders
- [ ] `cad/` – syringe drive, laser mount, needle holder (STEP + source)
- [ ] `bom.md`
- [ ] `wiring.md` / diagram (laser supply, PWM line, pulldown)
- [ ] Photos

## Known hardware limits and planned upgrades
- Lead-screw backlash (plain M6 nut, ≈0.05–0.2 mm) rules out retraction and pressure advance. Planned: anti-backlash nut or T8 screw (T8×2 → `rotation_distance: 587.76`).
- Syringe compliance (air, seal, latex) causes a ≈1–2 s flow lag at line starts.
- The unsecured feed tube vibrates above 5 mm/s print speed. Planned: clamp and route it.
- Latex wets the outside of the needle tip and a growing blob forms. Planned: water-repellent tip coating and a wipe station.
