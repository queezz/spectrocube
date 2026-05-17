# spectrocube

**SpectroCube** is a lightweight Python standard for calibrated spectroscopic datasets.
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

## Installation

```bash
pip install spectrocube
```

Development install (includes test and doc dependencies):

```bash
git clone https://github.com/queezz/spectrocube
cd spectrocube
pip install -e ".[dev]"
pytest
```

Build the documentation locally:

```bash
pip install -e ".[docs]"
mkdocs serve
```

---

## Key concepts

| Concept | Description |
|---|---|
| `intensity` | Required data variable; any shape as long as `wavelength` is a dim |
| `wavelength` | Required 1D coordinate in nm, must be monotonically increasing |
| `calibration_type` | `"counts"`, `"relative"`, or `"absolute"` |
| `wavelength_medium` | `"air"` or `"vacuum"` |
| `.ds` | Direct access to the underlying `xr.Dataset` for xarray operations |

See [SPEC.md](SPEC.md) for the complete data model specification.

---

## Virtual environment

Linux / macOS:

```bash
python3 -m venv ~/.venvs/spectrocube
source ~/.venvs/spectrocube/bin/activate
pip install -e ".[dev]"
```

Windows PowerShell:

```powershell
python -m venv "$env:USERPROFILE/.venvs/spectrocube"
& "$env:USERPROFILE/.venvs/spectrocube/Scripts/Activate.ps1"
pip install -e ".[dev]"
```
