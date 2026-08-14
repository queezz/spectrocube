# Changelog

Public SpectroCube package and format history.

## 0.2.0 — 2026-08-14

- Defined optional, independently present `detector_pixel`, `echelle_order`,
  `wavelength_polynomials_json`, and
  `applied_absolute_calibration_factor` representations.
- Added validation for exact wavelength alignment, numeric and integer types,
  finite values, detector convention metadata, strict versioned polynomial
  JSON, applied-factor direction and units, and cross-field order references.
- Preserved ordinary 0.1-style cubes and arbitrary legal xarray/NetCDF extras.
- Added installed specification and changelog resources, synchronized public
  version checks, external scratch defaults, and documented release gates.

## 0.1.0 — 2026

- Established the instrument-neutral xarray/NetCDF container, validation
  report, save/load API, and inspection commands.
