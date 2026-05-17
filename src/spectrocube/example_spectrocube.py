"""
SpectroCube example: synthetic hydrogen emission spectrum.

Demonstrates:
- Construction with from_arrays (1D, 2D, custom dims)
- Validation report
- Save to NetCDF and reload
- Direct xarray access via .ds
- Deliberate mistakes to show validator output
"""

import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from spectrocube import SpectroCube

# ------------------------------------------------------------------
# Synthetic data helpers
# ------------------------------------------------------------------

rng = np.random.default_rng(42)
wl = np.linspace(400.0, 700.0, 3000)  # nm, air


def gaussian(x, center, width, amplitude):
    return amplitude * np.exp(-0.5 * ((x - center) / width) ** 2)


continuum = 50.0 + 0.01 * (wl - 400)
spectrum = (
    continuum
    + gaussian(wl, 656.28, 0.3, 5000)  # Hα
    + gaussian(wl, 486.13, 0.3, 1500)  # Hβ
    + gaussian(wl, 434.05, 0.3, 800)   # Hγ
    + rng.normal(0, 5, len(wl))
)

# ------------------------------------------------------------------
# Example 1: single spectrum (1D)
# ------------------------------------------------------------------

print("=" * 60)
print("Example 1: Single spectrum — 1D intensity")
print("=" * 60)

sc_1d = SpectroCube.from_arrays(
    wavelength=wl,
    intensity=spectrum,
    instrument_id="lab_spectrometer",
    calibration_type="relative",
    intensity_units="a.u.",
    wavelength_medium="air",
)
print(sc_1d)
print(sc_1d.validate())

# ------------------------------------------------------------------
# Example 2: multi-frame sequence (2D, inferred dims)
# ------------------------------------------------------------------

print("\n" + "=" * 60)
print("Example 2: Multi-frame — 2D intensity, dims inferred")
print("=" * 60)

intensity_2d = np.stack([spectrum * (1.0 + 0.02 * i) for i in range(3)])

sc = SpectroCube.from_arrays(
    wavelength=wl,
    intensity=intensity_2d,
    instrument_id="lab_spectrometer",
    calibration_type="relative",
    intensity_units="a.u.",
    wavelength_medium="air",
    wavelength_accuracy_nm=0.05,
    exposure_s=0.5,
    frame_interval_s=1.0,
    spectrometer="Echelle ESA-3",
    detector="Andor iStar 334T",
    grating="79 l/mm",
    slit_um=50.0,
    shot_number="run_001",
    notes="Synthetic Balmer series, 3 frames",
)
print(sc)
print(sc.validate())

# ------------------------------------------------------------------
# Example 3: custom dims (time + wavelength)
# ------------------------------------------------------------------

print("\n" + "=" * 60)
print("Example 3: Custom dims — (time, wavelength)")
print("=" * 60)

time_axis = np.arange(5) * 0.1  # seconds
sc_time = SpectroCube.from_arrays(
    wavelength=wl,
    intensity=np.stack([spectrum * (1 + 0.05 * i) for i in range(5)]),
    dims=("time", "wavelength"),
    coords={"time": time_axis},
    instrument_id="lab_spectrometer",
    calibration_type="counts",
    intensity_units="counts",
    wavelength_medium="air",
)
print(sc_time)
print(f"  dims: {sc_time.dims}, sizes: {sc_time.sizes}")

# ------------------------------------------------------------------
# Example 4: save and reload
# ------------------------------------------------------------------

print("\n" + "=" * 60)
print("Example 4: Save and reload")
print("=" * 60)

outfile = "/tmp/example_spectrocube.nc"
sc.save(outfile)
print(f"Saved to {outfile}")

sc2 = SpectroCube.load(outfile)
print(f"Reloaded: {sc2}")

# Direct xarray access
ha_region = sc2.ds["intensity"].sel(frame=0, wavelength=slice(654, 659))
print(
    f"Hα region, frame 0: {ha_region.values.shape} points, "
    f"peak = {ha_region.values.max():.1f} {sc2.ds.attrs['intensity_units']}"
)

# ------------------------------------------------------------------
# Example 5: absolute calibration
# ------------------------------------------------------------------

print("\n" + "=" * 60)
print("Example 5: Absolute calibration")
print("=" * 60)

sc_abs = SpectroCube.from_arrays(
    wavelength=wl,
    intensity=intensity_2d * 1e12,
    instrument_id="calibrated_spectrometer",
    calibration_type="absolute",
    intensity_units="ph/s/nm/sr",
    wavelength_medium="air",
    calibration_source="NIST-traceable tungsten ribbon lamp, 2024-03-15",
    exposure_s=0.5,
    spectrometer="Echelle ESA-3",
    detector="Andor iStar 334T",
    shot_number="run_002",
)
print(sc_abs)
print(sc_abs.validate())

# ------------------------------------------------------------------
# Example 6: deliberate errors — validator demo
# ------------------------------------------------------------------

print("\n" + "=" * 60)
print("Example 6: Broken SpectroCube — validator demo")
print("=" * 60)

sc_bad = SpectroCube.from_arrays(
    wavelength=wl,
    intensity=intensity_2d,
    instrument_id="",           # empty — required field
    calibration_type="absolute",  # absolute but wrong units and no source
    intensity_units="counts",   # invalid for absolute
    wavelength_medium="water",  # not a valid medium
)
sc_bad.ds["intensity"].values[0, 100:105] = np.nan  # inject NaNs

report_bad = sc_bad.validate()
print(report_bad)
