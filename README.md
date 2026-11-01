# Latex Voron 2.4 3D printer: software for laser-assisted printing of water-based latex

Software, firmware notes and slicer settings for a Voron 2.4 adapted to extrude water-based latex from a syringe and cure it with a laser that trails the nozzle.

This repository accompanies a TDK research paper (BME, Department of Polymer Engineering):
*System development and process characterization for laser-assisted 3D printing of water-based latex.*

> **DOI:** to be added after the first Zenodo release (`10.5281/zenodo.XXXXXXX`).

## What's in here

| Folder | Contents | Status |
|---|---|---|
| [`postprocessor/`](postprocessor/) | **Latex Laser Post-Processor**: a browser tool that turns OrcaSlicer G-code into unidirectional, laser-gated G-code. Includes its verification suite | ready |
| [`gcode-generators/`](gcode-generators/) | Python scripts for calibration prints (laser power ladder, bead-geometry tests) | ready |
| [`klipper/`](klipper/) | Klipper configuration | **to be added on Monday** (a reference laser section is included) |
| [`orca/`](orca/) | OrcaSlicer settings and start/end G-code | ready |
| [`docs/`](docs/) | Syringe extruder calibration ("virtual filament"), laser control and safety, why printing in one direction matters | ready |

## Overview

The syringe extruder is configured in Klipper as an ordinary extruder fed with **"virtual" 1.75 mm filament**, so normal slicer settings (layer height, line width, flow) apply unchanged. The curing spot sits a short distance behind the nozzle, so a bead is only cured when the nozzle moves away from the spot. The post-processor rewrites sliced G-code so every bead is laid in that direction, and switches the laser on only while a bead is being deposited.

## Quick start

1. **Klipper:** set the extruder `rotation_distance` for your syringe (see [`docs/system-overview.md`](docs/system-overview.md)), and add the laser section and macros (see [`klipper/`](klipper/)).
2. **Slice** in OrcaSlicer with the settings in [`orca/`](orca/): no walls, Aligned Rectilinear infill along the print axis, filament diameter 1.75.
3. **Post-process:** open [`postprocessor/latex-laser-postprocessor.html`](postprocessor/latex-laser-postprocessor.html) in any browser (it works offline). Drop in the G-code, set the print direction, spot offset and laser power, check the preview, then save.
4. **Print**, with laser safety goggles rated for your laser's wavelength and a hardware switch in the laser supply.

## Safety

Diode laser modules used for curing are typically Class 4. Wear goggles rated for the wavelength, enclose the printer, and keep a physical switch in the laser supply.

The reference Klipper configuration drops both laser pins to 0 on emergency stop. A 1 s watchdog on the PWM line also turns the beam off if the host or CAN link is lost. The software is not a substitute for a hardware interlock.

## Citing

Please cite the Zenodo record for this repository (see [`CITATION.cff`](CITATION.cff)).

## License

Code: MIT (see [`LICENSE`](LICENSE)).
