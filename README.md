# spectrocube

**Docs:** [queezz.github.io/spectrocube](https://queezz.github.io/spectrocube/)

**SpectroCube** is a lightweight Python standard for calibrated spectroscopic datasets.
The current package and format version is **0.2.0**.
It defines a single class, `SpectroCube`, that wraps an [xarray](https://xarray.dev/) Dataset
with required metadata, a validated data structure, and NetCDF serialization.
The goal is a portable, self-describing file format that instrument packages can write
and analysis packages can read without sharing any instrument-specific code.

A SpectroCube always has a `wavelength` coordinate (1D, nm, monotonically increasing)
and an `intensity` data variable that depends on `wavelength`.
The intensity array can have any additional labeled dimensions —
`(wavelength,)` for a single spectrum, `(frame, wavelength)` for a shot sequence,
or `(chord, time, wavelength)` for multi-chord time-resolved data.
Calibration level, units, and provenance are stored as required global attributes.

Version 0.2.0 also defines four independently optional recalibration fields:
`detector_pixel`, `echelle_order`, `wavelength_polynomials_json`, and
`applied_absolute_calibration_factor`. Ordinary writers do not need to provide
them. See [SPEC.md](SPEC.md) for their exact alignment, metadata, JSON, and
partial-presence rules.

**This package defines the standard and provides the container class only.**
Fitting, plotting, wavelength calibration, instrument extraction, and analysis workflows
belong in separate packages that consume SpectroCube files.

---

## Quickstart

```python
import numpy as np
from spectrocube import SpectroCube

wl = np.linspace(400.0, 700.0, 3000)          # wavelength axis, nm
intensity = np.random.default_rng(0).random((5, 3000))  # 5 frames

sc = SpectroCube.from_arrays(
    wavelength=wl,
    intensity=intensity,
    instrument_id="my_spectrometer",
    calibration_type="counts",
    intensity_units="counts",
    wavelength_medium="air",
    exposure_s=0.1,
    spectrometer="Ocean HR4000",
)

print(sc)
# SpectroCube(instrument='my_spectrometer', dims=(frame=5, wavelength=3000), ...)

report = sc.validate()
print(report)

sc.save("output.nc")
sc2 = SpectroCube.load("output.nc")
```

---

## Command-line tools

After installation two commands are available:

```bash
# Print a compact summary of a saved file
spectrocube-info output.nc

# Validate a file; exits 0 if valid, 1 if errors found
spectrocube-validate output.nc
echo $?
```

Example output of `spectrocube-info`:

```
File:          output.nc
Instrument:    my_spectrometer
Calibration:   counts (counts)
Wavelength:    air, 400.00–700.00 nm, 3000 points
Intensity:     frame=5, wavelength=3000

  spectrometer:              Ocean HR4000
  exposure_s:                0.1

Validation:    ✓ valid
```

---

## Installation

```bash
pip install spectrocube
```

Development install with an external environment (no Lab helper required):

Windows PowerShell:

```powershell
git clone https://github.com/queezz/spectrocube
Set-Location spectrocube
python -m venv "$env:USERPROFILE\.venvs\spectrocube"
& "$env:USERPROFILE\.venvs\spectrocube\Scripts\python.exe" -m pip install -e ".[dev,docs]"
& "$env:USERPROFILE\.venvs\spectrocube\Scripts\python.exe" -m pytest
```

macOS / Linux:

```bash
git clone https://github.com/queezz/spectrocube
cd spectrocube
python3 -m venv ~/.venvs/spectrocube
~/.venvs/spectrocube/bin/python -m pip install -e ".[dev,docs]"
~/.venvs/spectrocube/bin/python -m pytest
```

Build the documentation locally:

```powershell
$spectrocubeSite = Join-Path ([System.IO.Path]::GetTempPath()) ("spectrocube-site-" + [guid]::NewGuid())
& "$env:USERPROFILE\.venvs\spectrocube\Scripts\python.exe" -m mkdocs build --strict --site-dir $spectrocubeSite
```

```bash
spectrocube_site="$(mktemp -d)"
~/.venvs/spectrocube/bin/python -m mkdocs build --strict --site-dir "$spectrocube_site"
```

---

## Key concepts

| Concept | Description |
|---|---|
| `intensity` | Required data variable; any shape as long as `wavelength` is a dim |
| `wavelength` | Required 1D coordinate in nm, must be monotonically increasing |
| `calibration_type` | `"counts"`, `"relative"`, or `"absolute"` |
| `wavelength_medium` | `"air"` or `"vacuum"` |
| `detector_pixel` | Optional detector coordinate aligned with `wavelength` |
| `echelle_order` | Optional integer order coordinate aligned with `wavelength` |
| `wavelength_polynomials_json` | Optional versioned per-order polynomial metadata |
| `applied_absolute_calibration_factor` | Optional positive factor used to produce stored absolute intensity |
| `.ds` | Direct access to the underlying `xr.Dataset` for xarray operations |

See [SPEC.md](SPEC.md) for the complete data model specification.

---
