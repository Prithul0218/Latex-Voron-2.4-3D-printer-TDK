# Klipper configuration

**The full printer configuration (`printer.cfg` and included files) will be added on Monday.**

Until then, [`laser-reference.cfg`](laser-reference.cfg) contains the laser section and macros developed for this printer. It is a reference, not a drop-in file: pin names assume a BTT EBB36 on CAN (`EBBCan`).

## What the final configuration will contain
- [ ] `printer.cfg` (Voron 2.4 350, BTT Manta M8P + EBB36 over CAN)
- [ ] Syringe extruder: `rotation_distance: 293.88`, `filament_diameter: 1.75` (virtual), dummy heater (100 kΩ resistor on the thermistor input), `min_extrude_temp: 0`
- [ ] TMC driver settings for the syringe motor (stealthChop, interpolation)
- [ ] Laser section and macros (see reference file)
- [ ] `[firmware_retraction]` (`retract_length: 0`, `unretract_extra_length` as tuned)
- [ ] `[exclude_object]` (needed for per-object laser power in the post-processor)
- [ ] PRINT_START / PRINT_END / PAUSE / CANCEL_PRINT macros with laser hooks
