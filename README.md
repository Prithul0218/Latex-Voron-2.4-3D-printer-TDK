# Latex Voron 2.4 3D printer: laser-assisted 3D printing of water-based latex

Open hardware notes, firmware configuration and software for a **Voron 2.4 (350 mm)** converted into a **syringe-extrusion printer with laser curing** of water-based latex. The latex is deposited as a bead and cured in place by a diode laser whose spot trails the nozzle by about 1 mm.

This repository accompanies a TDK research paper (BME, Department of Polymer Engineering):
*System development and process characterization for laser-assisted 3D printing of water-based latex.*

> **DOI:** to be added after the first Zenodo release (`10.5281/zenodo.XXXXXXX`).

## What's in here

| Folder | Contents | Status |
|---|---|---|
| [`postprocessor/`](postprocessor/) | **Latex Laser Post-Processor**: a browser tool that turns OrcaSlicer G-code into unidirectional, laser-gated G-code. Includes its verification suite | ready |
| [`gcode-generators/`](gcode-generators/) | Python scripts that generate the calibration and process-parameter test prints (power ladder, blocks, bead tests, tests 4–16) | ready |
| [`klipper/`](klipper/) | Klipper configuration | **to be added on Monday** (a reference laser section is included) |
| [`orca/`](orca/) | OrcaSlicer settings and start/end G-code | ready (profile export to be added) |
| [`hardware/`](hardware/) | Syringe extruder, laser mount, wiring, bill of materials, CAD | **to be added** |
| [`docs/`](docs/) | System overview: extruder calibration, laser control and safety, curing geometry, known limits | ready |

## The system in one paragraph

A 30 mm syringe is driven by a NEMA 17 through an M6 × 1 mm threaded rod and pushes latex through a 1.04 mm needle. Klipper treats the syringe as an ordinary extruder fed with **"virtual" 1.75 mm filament** (`rotation_distance = (30/1.75)² × 1 mm = 293.88`), so normal slicer settings apply. A NEJE N30820 diode laser (5.5 W optical, used defocused) sits next to the needle; its spot is ≈1 mm behind the nozzle on the X− side. Fresh latex is therefore only cured when the nozzle moves **toward X+**, so parts are printed as X-parallel lines in one direction. The post-processor enforces that direction and switches the laser on only while a bead is being laid.

## Quick start

1. **Klipper:** set the extruder `rotation_distance` and add the laser section and macros. See [`klipper/`](klipper/) and [`docs/system-overview.md`](docs/system-overview.md).
2. **Slice** in OrcaSlicer with the settings in [`orca/`](orca/): no walls, Aligned Rectilinear at 0°, filament diameter 1.75.
3. **Post-process:** open [`postprocessor/latex-laser-postprocessor.html`](postprocessor/latex-laser-postprocessor.html) in any browser (it works offline). Drop in the G-code, choose the laser power, check the preview, then save.
4. **Print**, with laser safety goggles rated for 445–450 nm and a hardware switch in the laser supply.

## Safety

The NEJE N30820 is a Class 4 laser. Wear goggles rated for its wavelength, enclose the printer, and keep a physical switch in the laser supply.

The Klipper configuration drops both laser pins to 0 on emergency stop. A 1 s watchdog on the PWM line also turns the beam off if the host or CAN link is lost; both were tested. The software is not a substitute for a hardware interlock.

## Citing

Please cite the Zenodo record for this repository (see [`CITATION.cff`](CITATION.cff)). The DOI will be added here after the first release.

## License

Code: MIT (see [`LICENSE`](LICENSE)). Documentation and example G-code may be reused with attribution.
