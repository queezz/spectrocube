# spectrocube

**SpectroCube** is a lightweight Python standard for calibrated spectroscopic datasets.
It defines a single class, `SpectroCube`, that wraps an [xarray](https://xarray.dev/) Dataset
with required metadata, a validated data structure, and NetCDF serialization.

The goal is a portable, self-describing file format:
**instrument packages produce** SpectroCube files;
**analysis packages consume** them — without sharing any instrument-specific code.

---

## Package scope

This package contains:

- The `SpectroCube` class and its constructors
- The `ValidationReport` class
- Save / load via NetCDF

This package intentionally does **not** contain:

- Fitting or line identification
- Plotting or visualization
- Instrument-specific extraction or calibration logic
- Analysis workflows

---

## Data model at a glance

A SpectroCube always has:

- An `intensity` data variable (any shape, must include `wavelength` as a dimension)
- A `wavelength` coordinate (1D, nm, monotonically increasing)
- Five required global attributes: `spectrocube_version`, `instrument_id`,
  `calibration_type`, `intensity_units`, `wavelength_medium`

The underlying `xr.Dataset` is always accessible via `.ds` for direct xarray operations.

---

## Navigation

- [Specification](spec.md) — full data model definition
- [Usage](usage.md) — code examples
- [API Reference](reference.md) — class and method documentation
