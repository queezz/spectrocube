# Command-line tools

Two commands are installed with the package.

---

## `spectrocube-info`

Loads a file and prints a compact human-readable summary: instrument metadata,
wavelength range, intensity dimensions, optional attributes, and a one-line
validation result.

```bash
spectrocube-info output.nc
```

```
File:          output.nc
Instrument:    lab_spectrometer
Calibration:   relative (a.u.)
Wavelength:    air, 400.00–700.00 nm, 3000 points
Intensity:     frame=3, wavelength=3000

  spectrometer:              Echelle ESA-3
  detector:                  Andor iStar 334T
  grating:                   79 l/mm
  slit_um:                   50.0
  exposure_s:                0.5
  shot_number:               run_001

Validation:    ✓ valid
```

The exit code is always 0; `info` is informational and never blocks.

---

## `spectrocube-validate`

Validates a file and prints the full `ValidationReport`.
Exits **0** if there are no errors, **1** if any errors are found.
Warnings do not affect the exit code.

```bash
spectrocube-validate output.nc
echo $?   # 0

spectrocube-validate broken.nc
echo $?   # 1
```

Use this in CI pipelines or post-processing scripts to guard against writing
malformed files downstream.
