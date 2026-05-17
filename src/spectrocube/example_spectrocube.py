"""
SpectroCube example: synthetic Echelle-like spectrum.

Demonstrates:
- Construction from numpy arrays
- Validation report
- Save to NetCDF
- Reload and inspect via xarray
- Deliberate mistakes to show validator output
"""

import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from spectrocube import SpectroCube

# ------------------------------------------------------------------
# 1. Synthetic data: hydrogen Balmer series region, 3 frames
# ------------------------------------------------------------------

# Stitched Echelle wavelength axis, 400-700 nm
wl = np.linspace(400.0, 700.0, 3000)  # nm, air

# Synthetic spectrum: continuum + Hα (656.3 nm) + Hβ (486.1 nm) + Hγ (434.0 nm)
def gaussian(x, center, width, amplitude):
    return amplitude * np.exp(-0.5 * ((x - center) / width) ** 2)

continuum = 50.0 + 0.01 * (wl - 400)
spectrum = (
    continuum
    + gaussian(wl, 656.28, 0.3, 5000)   # Hα
    + gaussian(wl, 486.13, 0.3, 1500)   # Hβ
    + gaussian(wl, 434.05, 0.3, 800)    # Hγ
    + np.random.default_rng(42).normal(0, 5, len(wl))  # noise
)

# 3 frames: simulate slight intensity variation between frames
intensity = np.stack([
    spectrum * (1.0 + 0.02 * i) for i in range(3)
])  # shape (3, 3000)

print(f"Wavelength shape: {wl.shape}")
print(f"Intensity shape:  {intensity.shape}")

# ------------------------------------------------------------------
# 2. Construct a valid SpectroCube (relative calibration)
# ------------------------------------------------------------------

print("\n" + "="*60)
print("Example 1: Relative calibration (typical lab Echelle)")
print("="*60)

sc = SpectroCube(
    wavelength=wl,
    intensity=intensity,
    instrument_id="echelle_kyoto",
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
    shot_number="run_2024_001",
    notes="H2 discharge, 5 Pa, synthetic example",
)

print(sc)

report = sc.validate()
print(report)

# ------------------------------------------------------------------
# 3. Save and reload
# ------------------------------------------------------------------

outfile = "/tmp/example_spectrocube.nc"
sc.save(outfile)
print(f"\nSaved to {outfile}")

sc2 = SpectroCube.load(outfile)
print(f"Reloaded: {sc2}")

# Inspect via xarray
print("\nxarray Dataset:")
print(sc2.ds)

print("\nAttributes:")
for k, v in sc2.ds.attrs.items():
    print(f"  {k}: {v}")

# xarray selection example: single frame, Hα region
ha_region = sc2.ds["intensity"].sel(
    frame=0,
    wavelength=slice(654, 659)
)
print(f"\nHα region, frame 0: {ha_region.values.shape} points, "
      f"peak={ha_region.values.max():.1f} {sc2.ds.attrs['intensity_units']}")

# ------------------------------------------------------------------
# 4. Absolute calibration example
# ------------------------------------------------------------------

print("\n" + "="*60)
print("Example 2: Absolute calibration (LHD-style)")
print("="*60)

# Fake absolute intensity: ph/s/nm/sr
intensity_abs = intensity * 1e12  # pretend we have a calibration factor

sc_abs = SpectroCube(
    wavelength=wl,
    intensity=intensity_abs,
    instrument_id="echelle_lhd",
    calibration_type="absolute",
    intensity_units="ph/s/nm/sr",
    wavelength_medium="air",
    wavelength_accuracy_nm=0.05,
    exposure_s=0.5,
    calibration_source="NIST-traceable tungsten ribbon lamp, 2023-11-15",
    spectrometer="Echelle ESA-3",
    detector="Andor iStar 334T",
    shot_number="LHD#196500",
)

print(sc_abs)
report_abs = sc_abs.validate()
print(report_abs)

# ------------------------------------------------------------------
# 5. Deliberately broken SpectroCube — show validator catching problems
# ------------------------------------------------------------------

print("\n" + "="*60)
print("Example 3: Broken SpectroCube — validator demo")
print("="*60)

sc_bad = SpectroCube(
    wavelength=wl,
    intensity=intensity,
    instrument_id="",                    # empty instrument_id
    calibration_type="absolute",         # absolute but wrong units + no source
    intensity_units="counts",            # wrong for absolute
    wavelength_medium="water",           # not a valid medium
)

# Inject some NaNs
sc_bad.ds["intensity"].values[0, 100:105] = np.nan

report_bad = sc_bad.validate()
print(report_bad)
