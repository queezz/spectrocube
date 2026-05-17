# Usage

## Constructing a SpectroCube

### Single spectrum

Pass a 1D intensity array.  Dimensions are inferred as `("wavelength",)`.

```python
import numpy as np
from spectrocube import SpectroCube

wl = np.linspace(400.0, 700.0, 3000)
spectrum = np.ones(3000) * 100.0

sc = SpectroCube.from_arrays(
    wavelength=wl,
    intensity=spectrum,
    instrument_id="my_spectrometer",
    calibration_type="counts",
    intensity_units="counts",
    wavelength_medium="air",
)
print(sc)
# SpectroCube(instrument='my_spectrometer', dims=(wavelength=3000), ...)
```

### Multi-frame sequence

Pass a 2D array `(n_frames, n_wavelengths)`.
Dimensions are inferred as `("frame", "wavelength")`.

```python
intensity = np.random.default_rng(0).random((10, 3000)) * 1000

sc = SpectroCube.from_arrays(
    wavelength=wl,
    intensity=intensity,
    instrument_id="my_spectrometer",
    calibration_type="counts",
    intensity_units="counts",
    wavelength_medium="air",
    exposure_s=0.1,
    spectrometer="Ocean HR4000",
    detector="CCD-1024",
)
print(sc.dims)   # ('frame', 'wavelength')
print(sc.sizes)  # {'frame': 10, 'wavelength': 3000}
```

### Custom dimensions

Supply `dims` explicitly for non-default names or for arrays with 3+ dimensions.

```python
# 2D: rename the leading axis
sc = SpectroCube.from_arrays(
    wavelength=wl,
    intensity=np.ones((50, 3000)),
    dims=("time", "wavelength"),
    instrument_id="my_spectrometer",
    calibration_type="relative",
    intensity_units="a.u.",
    wavelength_medium="air",
)

# 3D: multi-chord time-resolved
sc = SpectroCube.from_arrays(
    wavelength=wl,
    intensity=np.ones((20, 50, 3000)),
    dims=("chord", "time", "wavelength"),
    instrument_id="tomographic_spectrometer",
    calibration_type="relative",
    intensity_units="a.u.",
    wavelength_medium="air",
)
print(sc.dims)   # ('chord', 'time', 'wavelength')
```

### Providing coordinate arrays

Pass a `coords` dict to label non-wavelength dimensions with real values.

```python
time_axis = np.arange(50) * 0.02  # seconds

sc = SpectroCube.from_arrays(
    wavelength=wl,
    intensity=np.ones((50, 3000)),
    dims=("time", "wavelength"),
    coords={"time": time_axis},
    instrument_id="my_spectrometer",
    calibration_type="counts",
    intensity_units="counts",
    wavelength_medium="air",
)
```

### Absolute calibration

Set `calibration_type="absolute"` and provide physical units and a calibration source.

```python
sc_abs = SpectroCube.from_arrays(
    wavelength=wl,
    intensity=np.ones((5, 3000)) * 1e14,
    instrument_id="calibrated_spectrometer",
    calibration_type="absolute",
    intensity_units="ph/s/nm/sr",
    wavelength_medium="air",
    calibration_source="NIST-traceable tungsten lamp, 2024-03-15",
    exposure_s=1.0,
)
```

---

## Validation

```python
report = sc.validate()

if report.ok:
    print("Valid:", report)
else:
    print("Errors found:")
    for e in report.errors:
        print(" ", e)

for w in report.warnings:
    print("Warning:", w)
```

`validate()` always returns a `ValidationReport`; it never raises.
`save()` raises `ValueError` if the report has errors.

---

## Save and load

```python
sc.save("output.nc")               # validates before writing by default
sc.save("output.nc", validate=False)  # skip validation

sc2 = SpectroCube.load("output.nc")
```

---

## Accessing the underlying Dataset

All xarray operations are available directly through `.ds`.

```python
# Select a wavelength slice using xarray
ha_region = sc.ds["intensity"].sel(wavelength=slice(654, 659))

# Select a single frame
frame_0 = sc.ds["intensity"].isel(frame=0)

# Check all attributes
for key, val in sc.ds.attrs.items():
    print(f"{key}: {val}")
```

---

## Wrapping an existing Dataset

If you already have an `xr.Dataset` with the right structure, use `from_dataset()`.

```python
import xarray as xr

ds = xr.load_dataset("some_file.nc")
sc = SpectroCube.from_dataset(ds)
report = sc.validate()
```

---

## Complete example

```python
import numpy as np
from spectrocube import SpectroCube

rng = np.random.default_rng(42)
wl = np.linspace(400.0, 700.0, 3000)

def gaussian(x, center, width, amp):
    return amp * np.exp(-0.5 * ((x - center) / width) ** 2)

continuum = 50.0 + 0.01 * (wl - 400)
spectrum = (
    continuum
    + gaussian(wl, 656.28, 0.3, 5000)  # Hα
    + gaussian(wl, 486.13, 0.3, 1500)  # Hβ
    + rng.normal(0, 5, len(wl))
)
intensity = np.stack([spectrum * (1.0 + 0.02 * i) for i in range(3)])

sc = SpectroCube.from_arrays(
    wavelength=wl,
    intensity=intensity,
    instrument_id="lab_spectrometer",
    calibration_type="relative",
    intensity_units="a.u.",
    wavelength_medium="air",
    wavelength_accuracy_nm=0.05,
    exposure_s=0.5,
    spectrometer="Echelle ESA-3",
    detector="Andor iStar 334T",
    shot_number="run_001",
    notes="Synthetic Balmer series, 3 frames",
)

print(sc)
print(sc.validate())

sc.save("/tmp/example.nc")
sc2 = SpectroCube.load("/tmp/example.nc")
print(sc2)
```

