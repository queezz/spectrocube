# Specification

Version: 0.1.0

---

## Overview

A SpectroCube is an xarray `Dataset` that represents a calibrated spectroscopic
measurement.  It is stored as a NetCDF `.nc` file and can be read by any software
that understands xarray or NetCDF.

---

## Data variable

### `intensity`

The spectral intensity array.

| Property | Requirement |
|---|---|
| Type | `float64` |
| Dimensions | Arbitrary, but `"wavelength"` must be one of them |
| Units | Stored in `ds.attrs["intensity_units"]` |

---

## Coordinate

### `wavelength`

| Property | Requirement |
|---|---|
| Dimensions | 1D only: `("wavelength",)` |
| Units | nanometres (nm) |
| Order | Strictly monotonically increasing |
| Range | Typically 100–25 000 nm; values outside this range trigger a validation warning |

The `wavelength` coordinate carries two attributes: `units = "nm"` and
`medium` mirroring the global `wavelength_medium` attribute.

---

## Global attributes

### Required

All five must be present and non-empty.

| Attribute | Type | Description |
|---|---|---|
| `spectrocube_version` | str | Version of this specification, e.g. `"0.1.0"` |
| `instrument_id` | str | Short identifier for the instrument |
| `calibration_type` | str | One of `"counts"`, `"relative"`, `"absolute"` |
| `intensity_units` | str | Physical units string, e.g. `"counts"`, `"a.u."`, `"ph/s/nm/sr"` |
| `wavelength_medium` | str | `"air"` or `"vacuum"` |

### Optional — recommended

| Attribute | Type | Description |
|---|---|---|
| `wavelength_accuracy_nm` | float | Estimated wavelength accuracy in nm |
| `exposure_s` | float | Exposure time per frame in seconds |
| `frame_interval_s` | float | Time between frame starts in seconds |
| `t_start` | str | Acquisition start time (ISO 8601) |
| `calibration_source` | str | Description of flux / wavelength calibration source |
| `spectrometer` | str | Spectrometer model or description |
| `detector` | str | Detector model or description |
| `grating` | str | Grating description |
| `slit_um` | float | Slit width in micrometres |
| `shot_number` | str | Shot / sample / run identifier |
| `notes` | str | Free-text notes |

---

## `calibration_type` meanings

| Value | Meaning |
|---|---|
| `"counts"` | Raw detector counts; no flux calibration applied |
| `"relative"` | Spectrally corrected; relative intensities meaningful, absolute values not |
| `"absolute"` | Fully flux-calibrated; values in physical units |

!!! note "Absolute calibration requirements"
    When `calibration_type == "absolute"`:

    - `intensity_units` must be a physical unit — not `"counts"` or `"a.u."`.
      Examples: `"ph/s/nm/sr"`, `"ph/s/nm"`, `"W/m2/nm"`.
    - `calibration_source` should describe the flux standard used.
      Omitting it produces a validation warning.

---

## Dimension patterns

`from_arrays()` infers dimensions automatically for 1D and 2D inputs.
Higher-dimensional inputs require `dims` to be passed explicitly.

| Pattern | Shape example | Typical use |
|---|---|---|
| `("wavelength",)` | `(3000,)` | Single acquisition |
| `("frame", "wavelength")` | `(100, 3000)` | Shot sequence (default 2D) |
| `("time", "wavelength")` | `(100, 3000)` | Time-resolved, explicit `dims` |
| `("chord", "time", "wavelength")` | `(20, 100, 3000)` | Multi-chord time-resolved |

Coordinate arrays for non-wavelength dimensions may be passed via the `coords`
parameter of `from_arrays()`.  Missing coordinates receive auto-generated integer ranges.

---

## Serialization

SpectroCube files are stored as **NetCDF-4** (`.nc`) via xarray's `to_netcdf()`.

- All data variables, coordinates, and global attributes round-trip exactly.
- Load with `SpectroCube.load(path)` or directly with `xr.load_dataset(path)`.
- NetCDF attributes must be scalar or string values.

---

## Validation

`sc.validate()` returns a `ValidationReport`.  `sc.save()` refuses to write if
errors are present.

| Check | Level |
|---|---|
| `intensity` in data variables | error |
| `wavelength` coordinate present and 1D | error |
| `wavelength` monotonically increasing | error |
| `intensity` depends on `wavelength` dim | error |
| Required attributes present and non-empty | error |
| `calibration_type` in allowed values | error |
| `wavelength_medium` in allowed values | error |
| Absolute calibration: physical `intensity_units` | error |
| Absolute calibration: `calibration_source` present | warning |
| Non-finite values in `intensity` | warning |
| Wavelength range outside 100–25 000 nm | warning |
