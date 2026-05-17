# SpectroCube Data Model Specification

Version: 0.1.0

---

## Overview

A SpectroCube is an xarray `Dataset` that represents a calibrated spectroscopic
measurement.  It is stored as a NetCDF `.nc` file and can be read by any software
that understands xarray or NetCDF.

The specification defines:

- one required data variable (`intensity`)
- one required coordinate (`wavelength`)
- a set of required and optional global attributes

---

## Data variable

### `intensity`

The spectral intensity array.

| Property | Requirement |
|---|---|
| Type | `float64` |
| Dimensions | Arbitrary, but `"wavelength"` must be one of them |
| Units | Stored in `ds.attrs["intensity_units"]` |

The `intensity` variable may have any number of dimensions beyond `wavelength`.
Common patterns are described in [Dimension patterns](#dimension-patterns) below.

---

## Coordinate

### `wavelength`

| Property | Requirement |
|---|---|
| Dimensions | 1D only: `("wavelength",)` |
| Units | nanometres (nm) |
| Order | Strictly monotonically increasing |
| Range | Typically 100–25 000 nm; values outside this range trigger a validation warning |

The `wavelength` coordinate carries two attributes:

| Attribute | Value |
|---|---|
| `units` | `"nm"` |
| `medium` | `"air"` or `"vacuum"` (mirrors the global `wavelength_medium` attr) |

---

## Global attributes

### Required

All five attributes must be present and non-empty.  Missing or empty values are
reported as errors by `validate()`.

| Attribute | Type | Description |
|---|---|---|
| `spectrocube_version` | str | Version of this specification, e.g. `"0.1.0"` |
| `instrument_id` | str | Short identifier for the instrument, e.g. `"echelle_kyoto"` |
| `calibration_type` | str | One of `"counts"`, `"relative"`, `"absolute"` |
| `intensity_units` | str | Physical units string, e.g. `"counts"`, `"a.u."`, `"ph/s/nm/sr"` |
| `wavelength_medium` | str | `"air"` or `"vacuum"` |

### Optional — recommended

These attributes are not required but are strongly encouraged for reproducibility.

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

Additional arbitrary attributes may be stored; they are preserved through
save/load but ignored by `validate()`.

---

## `calibration_type` meanings

| Value | Meaning |
|---|---|
| `"counts"` | Raw detector counts; no flux calibration applied |
| `"relative"` | Spectrally flat or instrument-response-corrected; relative intensities are meaningful but absolute values are not |
| `"absolute"` | Fully flux-calibrated; intensity values are in physical units |

### Absolute calibration requirements

When `calibration_type == "absolute"`:

- `intensity_units` must be a physical unit string — not `"counts"` or `"a.u."`.
  Examples: `"ph/s/nm/sr"`, `"ph/s/nm"`, `"W/m2/nm"`, `"W/m2/nm/sr"`.
- `calibration_source` should be set to describe the flux standard used
  (e.g. `"NIST-traceable tungsten ribbon lamp, 2024-03-15"`).
  Omitting it is a validation warning, not an error.

---

## Dimension patterns

The `intensity` array may have any dimensions as long as `"wavelength"` is one of them.
`from_arrays()` infers dimensions for 1D and 2D inputs; higher-dimensional inputs
require the caller to pass `dims` explicitly.

| Pattern | Shape example | Typical use |
|---|---|---|
| `("wavelength",)` | `(3000,)` | Single acquisition |
| `("frame", "wavelength")` | `(100, 3000)` | Shot sequence, default 2D inference |
| `("time", "wavelength")` | `(100, 3000)` | Time-resolved, explicit `dims` |
| `("chord", "time", "wavelength")` | `(20, 100, 3000)` | Multi-chord time-resolved |

For dimensions other than `"wavelength"`, coordinate arrays may be supplied via the
`coords` parameter of `from_arrays()`.  If omitted, integer ranges starting at 0 are
generated automatically.

---

## Serialization

SpectroCube files are stored as **NetCDF-4** (`.nc`) using xarray's `to_netcdf()`.

- All data variables, coordinates, and global attributes round-trip exactly.
- NetCDF attributes are limited to scalars and strings; do not store Python objects
  in `**attrs` unless they can be serialized to a basic type.
- Load with `SpectroCube.load(path)` or directly with `xr.load_dataset(path)`.

---

## Validation

`sc.validate()` returns a `ValidationReport` with `.errors` (blocking) and
`.warnings` (informational).  A cube with errors should not be treated as
authoritative.  `sc.save()` refuses to write if errors are present.

Checks performed by `validate()`:

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
