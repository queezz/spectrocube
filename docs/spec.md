# SpectroCube Data Model Specification

Version: 0.2.0

---

## Overview

A SpectroCube is an xarray `Dataset` representing a calibrated spectroscopic
measurement. It is stored as a NetCDF `.nc` file and can be read by software
that understands xarray or NetCDF.

The specification defines:

- one required data variable (`intensity`);
- one required coordinate (`wavelength`);
- five required global attributes;
- four optional, independently present recalibration representations;
- preservation of additional legal xarray coordinates, data variables, and
  NetCDF-safe attributes.

SpectroCube is an instrument-neutral container. Instrument packages populate
the fields they can support; calibration algorithms and instrument processing
remain outside this package.

## Required data variable

### `intensity`

The stored spectral signal.

| Property | Requirement |
|---|---|
| Type | `float64` when constructed with `from_arrays()` |
| Dimensions | Arbitrary, but `"wavelength"` must be one of them |
| Units | Stored in `ds.attrs["intensity_units"]` |

The variable may have any number of dimensions beyond `wavelength`.

## Required coordinate

### `wavelength`

| Property | Requirement |
|---|---|
| Dimensions | Exactly `("wavelength",)` |
| Units | Nanometres (`nm`) |
| Order | Strictly monotonically increasing |
| Range | Typically 100–25 000 nm; values outside this range warn |

The coordinate carries `units = "nm"` and a `medium` attribute mirroring
the global `wavelength_medium` attribute.

## Required global attributes

All five attributes must be present and non-empty.

| Attribute | Type | Description |
|---|---|---|
| `spectrocube_version` | str | Specification version used by the writer |
| `instrument_id` | str | Short instrument identifier |
| `calibration_type` | str | `"counts"`, `"relative"`, or `"absolute"` |
| `intensity_units` | str | Units of the stored `intensity` values |
| `wavelength_medium` | str | `"air"` or `"vacuum"` |

A plain 0.1-style cube containing only the required model remains valid under
0.2.0. Writers are not required to add any recalibration field.

## Recommended global attributes

| Attribute | Type | Description |
|---|---|---|
| `wavelength_accuracy_nm` | float | Estimated wavelength accuracy |
| `exposure_s` | float | Exposure time per frame |
| `frame_interval_s` | float | Time between frame starts |
| `t_start` | str | ISO 8601 acquisition start |
| `calibration_source` | str | Flux or wavelength calibration source |
| `spectrometer` | str | Spectrometer model or description |
| `detector` | str | Detector model or description |
| `grating` | str | Grating description |
| `slit_um` | float | Slit width in micrometres |
| `shot_number` | str | Shot, sample, or run identifier |
| `notes` | str | Free-text notes |

## Optional recalibration contract

Each representation below is optional. A writer may provide any one of them
without providing the other three. When two fields are both present, the
cross-field consistency rules below apply.

### `detector_pixel` coordinate

A one-dimensional real numeric auxiliary coordinate aligned exactly with
`wavelength`.

| Property | Requirement |
|---|---|
| Dimensions | Exactly `("wavelength",)` |
| Values | Finite real numbers |
| `units` | Exactly `"pixel"` |
| `detector_axis` | Non-empty axis name, such as `"column"` |
| `reference_frame` | Non-empty frame name, such as `"raw_detector"` |
| `index_origin` | Non-negative integer, normally `0` or `1` |

Values are detector coordinates, not positions within the stored wavelength
array. They must not be silently renumbered, reordered, or flipped separately
from wavelength and intensity. An Echelle writer preserves the raw detector
column used during extraction and sets `detector_axis = "column"`,
`reference_frame = "raw_detector"`, and its actual index origin. If the
wavelength axis is later reversed or sorted, `detector_pixel` is co-reordered
with it; the numeric values still refer to the raw detector.

Fractional values are allowed for sub-pixel coordinates.

### `echelle_order` coordinate

A one-dimensional integer auxiliary coordinate aligned exactly with
`wavelength`.

| Property | Requirement |
|---|---|
| Dimensions | Exactly `("wavelength",)` |
| Type | Integer, not boolean or floating point |
| Values | Non-negative order identifiers |

This field is optional even when another recalibration field is present.
Non-Echelle instruments do not provide it.

### `wavelength_polynomials_json` global attribute

A UTF-8 JSON string containing versioned per-order wavelength polynomials. It
is a string, rather than a nested Python object, so it serializes through the
supported NetCDF attribute path.

The version-1 object has this exact core vocabulary:

```json
{
  "schema": "spectrocube.wavelength-polynomials/v1",
  "coefficient_order": "descending_power",
  "input": "detector_pixel",
  "input_units": "pixel",
  "output": "wavelength",
  "output_units": "nm",
  "orders": [
    {"order": 42, "coefficients": [1.25e-6, -0.031, 656.4]}
  ]
}
```

For coefficients `[c0, c1, ..., cn]`, evaluate

`wavelength_nm = c0*x**n + c1*x**(n-1) + ... + cn`

where `x` is the detector-pixel coordinate. Coefficients are finite JSON
numbers, the list is non-empty, and a multi-coefficient list does not begin
with zero. Each `order` is a unique non-negative JSON integer. Additional
JSON members are preserved and reserved for writer provenance; they do not
change the version-1 interpretation.

The attribute may appear without `detector_pixel` or `echelle_order` as
portable calibration provenance. If `echelle_order` is present, its distinct
values must exactly equal the polynomial order identifiers.

### `applied_absolute_calibration_factor` data variable

A one-dimensional real numeric auxiliary data variable aligned exactly with
`wavelength`. It records the positive multiplicative factor that produced
the stored absolute signal.

| Property | Requirement |
|---|---|
| Dimensions | Exactly `("wavelength",)` |
| Values | Finite and strictly positive |
| `units` | Non-empty units of factor per source signal |
| `source_units` | Non-empty units of the pre-factor source signal |
| `application` | Exact convention string shown below |
| Cube calibration | `calibration_type = "absolute"` |

The canonical `application` value is:

```text
stored_intensity = source_signal * applied_absolute_calibration_factor
```

This direction is normative. A later recalibrator can recover the source
signal by division and apply a replacement factor without guessing whether the
stored curve was multiplied or divided. A writer that exposure-normalizes
counts first can use `source_units = "counts/s"`; the factor then maps that
count rate to `intensity_units`.

## Partial-presence and consistency rules

- None of the four optional representations is required for an ordinary cube.
- Any one representation can validate alone when its own metadata is complete.
- `echelle_order` and `wavelength_polynomials_json`, when both present, must
  reference exactly the same order identifiers.
- `applied_absolute_calibration_factor` requires an absolute cube because its
  name and application state that the factor was applied to the stored signal.
- No other optional field implies the presence of the remaining bundle.
- All aligned fields use the same `wavelength` dimension. Writers must
  co-reorder them whenever they reorder wavelength and intensity.

## Calibration-type meanings

| Value | Meaning |
|---|---|
| `"counts"` | Raw detector counts; no flux calibration applied |
| `"relative"` | Spectrally corrected; relative intensities are meaningful |
| `"absolute"` | Flux-calibrated; intensity values are in physical units |

For `calibration_type == "absolute"`, `intensity_units` must be physical
rather than `"counts"` or `"a.u."`. Omitting `calibration_source` is a
warning.

## Dimension patterns

| Pattern | Shape example | Typical use |
|---|---|---|
| `("wavelength",)` | `(3000,)` | Single acquisition |
| `("frame", "wavelength")` | `(100, 3000)` | Shot sequence |
| `("time", "wavelength")` | `(100, 3000)` | Time-resolved |
| `("chord", "time", "wavelength")` | `(20, 100, 3000)` | Multi-chord |

`from_arrays()` infers dimensions for 1-D and 2-D intensity inputs.
Higher-dimensional inputs require explicit `dims`.

## Extra fields and preservation

Additional legal attributes, coordinates, and data variables are allowed.
`SpectroCube.from_dataset(ds)` wraps the supplied Dataset without copying,
normalizing, or discarding fields. `save()` and `load()` delegate to xarray
and preserve NetCDF-compatible extras. Callers remain responsible for using
NetCDF-safe attribute types.

## Serialization

Files are NetCDF-4 `.nc` files written by xarray `to_netcdf()`.
Structured optional metadata uses canonical JSON strings. Load with
`SpectroCube.load(path)` or `xr.load_dataset(path)`.

## Validation

`validate()` returns a `ValidationReport`; it never raises. `save()`
refuses to write when errors are present.

Validation rejects:

- missing required variables, coordinates, or attributes;
- invalid calibration or wavelength-medium values;
- malformed wavelength shape or ordering;
- optional fields with wrong dimensions, length, dtype, or non-finite values;
- incomplete detector convention or applied-factor interpretation metadata;
- malformed JSON, unsupported polynomial schema/ordering, duplicate orders,
  invalid coefficients, and inconsistent order references.

Non-finite intensity values and unusual wavelength ranges remain warnings.
