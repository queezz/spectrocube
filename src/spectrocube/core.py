"""
SpectroCube core module.

Defines the SpectroCube class: a calibrated spectral dataset with an
arbitrary set of labeled dimensions, one of which must be "wavelength".
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import xarray as xr

# ------------------------------------------------------------------
# Constants
# ------------------------------------------------------------------

SPECTROCUBE_VERSION = "0.2.0"

DETECTOR_PIXEL_FIELD = "detector_pixel"
ECHELLE_ORDER_FIELD = "echelle_order"
WAVELENGTH_POLYNOMIALS_ATTR = "wavelength_polynomials_json"
APPLIED_ABSOLUTE_CALIBRATION_FACTOR_FIELD = "applied_absolute_calibration_factor"

WAVELENGTH_POLYNOMIAL_SCHEMA = "spectrocube.wavelength-polynomials/v1"
WAVELENGTH_POLYNOMIAL_COEFFICIENT_ORDER = "descending_power"
APPLIED_FACTOR_APPLICATION = (
    "stored_intensity = source_signal * applied_absolute_calibration_factor"
)

VALID_WAVELENGTH_MEDIUM = ("air", "vacuum")

VALID_CALIBRATION_TYPES = ("counts", "relative", "absolute")

# Units that are acceptable for absolute calibration
ABSOLUTE_UNIT_HINTS = ("ph/s/nm/sr", "ph/s/nm", "W/m2/nm", "W/m2/nm/sr")


# ------------------------------------------------------------------
# Validation report
# ------------------------------------------------------------------


@dataclass
class ValidationReport:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return len(self.errors) == 0

    def __str__(self) -> str:
        lines = []
        if self.ok and not self.warnings:
            lines.append("✓ SpectroCube is valid.")
        if self.errors:
            lines.append(f"✗ {len(self.errors)} error(s):")
            for e in self.errors:
                lines.append(f"  ERROR   {e}")
        if self.warnings:
            lines.append(f"⚠ {len(self.warnings)} warning(s):")
            for w in self.warnings:
                lines.append(f"  WARNING {w}")
        return "\n".join(lines)


# ------------------------------------------------------------------
# Private helpers used by SpectroCube
# ------------------------------------------------------------------


def _resolve_dims(ndim: int, dims: tuple[str, ...] | None) -> tuple[str, ...]:
    """Return validated dimension names for an intensity array."""
    if ndim == 1:
        return ("wavelength",)
    if ndim == 2:
        return tuple(dims) if dims is not None else ("frame", "wavelength")
    if dims is None:
        raise ValueError(f"dims must be provided explicitly for intensity with ndim={ndim}")
    return tuple(dims)


def _build_xr_coords(
    wavelength: np.ndarray,
    wavelength_medium: str,
    intensity: np.ndarray,
    resolved_dims: tuple[str, ...],
    extra_coords: dict[str, np.ndarray],
) -> dict[str, xr.DataArray]:
    """Build the coordinate dict for a new Dataset."""
    xr_coords: dict[str, xr.DataArray] = {
        "wavelength": xr.DataArray(
            wavelength,
            dims=["wavelength"],
            attrs={"units": "nm", "medium": wavelength_medium, "long_name": "Wavelength"},
        )
    }
    for i, dim in enumerate(resolved_dims):
        if dim != "wavelength":
            arr = extra_coords[dim] if dim in extra_coords else np.arange(intensity.shape[i])
            xr_coords[dim] = xr.DataArray(np.asarray(arr), dims=[dim])
    return xr_coords


def _check_wavelength_coord(ds: xr.Dataset, report: ValidationReport) -> None:
    """Validate the wavelength coordinate; append to *report* in place."""
    if "wavelength" not in ds.coords:
        report.errors.append("'wavelength' coordinate not found.")
        return
    wl_da = ds.coords["wavelength"]
    if wl_da.ndim != 1:
        report.errors.append(f"'wavelength' coordinate must be 1D, got {wl_da.ndim}D.")
        return
    wl = wl_da.values
    if len(wl) == 0:
        report.errors.append("Wavelength axis is empty.")
    elif not np.all(np.diff(wl) > 0):
        report.errors.append("Wavelength axis is not monotonically increasing.")
    if len(wl) > 0 and (wl.min() < 100 or wl.max() > 25000):
        report.warnings.append(
            f"Wavelength range [{wl.min():.1f}, {wl.max():.1f}] nm looks unusual. "
            "Check units — should be nm."
        )


def _check_absolute_calibration(
    attrs: dict, report: ValidationReport  # type: ignore[type-arg]
) -> None:
    """Validate absolute-calibration requirements; append to *report* in place."""
    units = attrs.get("intensity_units", "")
    if units in ("counts", "a.u.", ""):
        report.errors.append(
            f"calibration_type is 'absolute' but intensity_units is '{units}'. "
            f"Provide physical units, e.g. one of: {ABSOLUTE_UNIT_HINTS}"
        )
    if "calibration_source" not in attrs:
        report.warnings.append(
            "calibration_type is 'absolute' but 'calibration_source' is not set. "
            "Document the flux standard used."
        )


def _is_real_numeric_dtype(dtype: np.dtype[Any]) -> bool:
    """Return whether *dtype* holds non-boolean real numbers."""
    return bool(
        np.issubdtype(dtype, np.number)
        and not np.issubdtype(dtype, np.bool_)
        and not np.issubdtype(dtype, np.complexfloating)
    )


def _check_wavelength_field_shape(
    ds: xr.Dataset,
    report: ValidationReport,
    name: str,
) -> xr.DataArray | None:
    """Return an aligned 1-D optional field, or record shape errors."""
    if name not in ds:
        return None
    field = ds[name]
    if field.dims != ("wavelength",):
        report.errors.append(
            f"'{name}' must have exactly dimensions ('wavelength',), got {field.dims!r}."
        )
        return None
    expected = ds.sizes.get("wavelength")
    if expected is not None and field.size != expected:
        report.errors.append(
            f"'{name}' length {field.size} does not match wavelength length {expected}."
        )
        return None
    return field


def _require_nonempty_string_attr(
    field: xr.DataArray,
    report: ValidationReport,
    field_name: str,
    attr_name: str,
) -> str | None:
    value = field.attrs.get(attr_name)
    if not isinstance(value, str) or not value.strip():
        report.errors.append(f"'{field_name}' requires a non-empty '{attr_name}' attribute.")
        return None
    return value


def _check_detector_pixel(ds: xr.Dataset, report: ValidationReport) -> None:
    field = _check_wavelength_field_shape(ds, report, DETECTOR_PIXEL_FIELD)
    if field is None:
        return
    if not _is_real_numeric_dtype(field.dtype):
        report.errors.append(
            f"'{DETECTOR_PIXEL_FIELD}' must have a real numeric dtype, got {field.dtype}."
        )
    elif not np.all(np.isfinite(field.values)):
        report.errors.append(f"'{DETECTOR_PIXEL_FIELD}' must contain only finite values.")

    units = _require_nonempty_string_attr(field, report, DETECTOR_PIXEL_FIELD, "units")
    if units is not None and units != "pixel":
        report.errors.append(
            f"'{DETECTOR_PIXEL_FIELD}' attribute 'units' must be 'pixel', got {units!r}."
        )
    _require_nonempty_string_attr(field, report, DETECTOR_PIXEL_FIELD, "detector_axis")
    _require_nonempty_string_attr(field, report, DETECTOR_PIXEL_FIELD, "reference_frame")
    index_origin = field.attrs.get("index_origin")
    if (
        isinstance(index_origin, (bool, np.bool_))
        or not isinstance(index_origin, (int, np.integer))
        or int(index_origin) < 0
    ):
        report.errors.append(
            f"'{DETECTOR_PIXEL_FIELD}' requires a non-negative integer " "'index_origin' attribute."
        )


def _check_echelle_order(ds: xr.Dataset, report: ValidationReport) -> set[int] | None:
    field = _check_wavelength_field_shape(ds, report, ECHELLE_ORDER_FIELD)
    if field is None:
        return None
    if np.issubdtype(field.dtype, np.bool_) or not np.issubdtype(field.dtype, np.integer):
        report.errors.append(
            f"'{ECHELLE_ORDER_FIELD}' must have an integer dtype, got {field.dtype}."
        )
        return None
    values = np.asarray(field.values)
    if np.any(values < 0):
        report.errors.append(f"'{ECHELLE_ORDER_FIELD}' values must be non-negative.")
        return None
    return {int(value) for value in np.unique(values)}


def _reject_json_constant(value: str) -> None:
    raise ValueError(f"non-standard JSON constant {value!r}")


def _unique_json_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON member {key!r}")
        result[key] = value
    return result


def _check_polynomial_order(
    item: object,
    index: int,
    identifiers: set[int],
    report: ValidationReport,
) -> bool:
    """Validate one per-order polynomial record."""
    label = f"'{WAVELENGTH_POLYNOMIALS_ATTR}' orders[{index}]"
    if not isinstance(item, dict):
        report.errors.append(f"{label} must be a JSON object.")
        return False
    valid = True
    order = item.get("order")
    if isinstance(order, bool) or not isinstance(order, int) or order < 0:
        report.errors.append(f"{label}.order must be a non-negative integer.")
        valid = False
    elif order in identifiers:
        report.errors.append(f"{label}.order duplicates order identifier {order}.")
        valid = False
    else:
        identifiers.add(order)

    coefficients = item.get("coefficients")
    if not isinstance(coefficients, list) or not coefficients:
        report.errors.append(f"{label}.coefficients must be a non-empty list.")
        return False
    if any(
        isinstance(coefficient, bool)
        or not isinstance(coefficient, (int, float))
        or not np.isfinite(coefficient)
        for coefficient in coefficients
    ):
        report.errors.append(f"{label}.coefficients must contain only finite JSON numbers.")
        valid = False
    elif len(coefficients) > 1 and coefficients[0] == 0:
        report.errors.append(
            f"{label}.coefficients must not start with zero; encode the actual degree."
        )
        valid = False
    return valid


def _check_wavelength_polynomials(
    attrs: dict[str, Any],
    report: ValidationReport,
) -> set[int] | None:
    if WAVELENGTH_POLYNOMIALS_ATTR not in attrs:
        return None
    raw = attrs[WAVELENGTH_POLYNOMIALS_ATTR]
    if not isinstance(raw, str):
        report.errors.append(
            f"'{WAVELENGTH_POLYNOMIALS_ATTR}' must be a JSON string for NetCDF portability."
        )
        return None
    try:
        payload = json.loads(
            raw,
            parse_constant=_reject_json_constant,
            object_pairs_hook=_unique_json_object,
        )
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        report.errors.append(f"'{WAVELENGTH_POLYNOMIALS_ATTR}' is malformed JSON: {exc}")
        return None
    if not isinstance(payload, dict):
        report.errors.append(f"'{WAVELENGTH_POLYNOMIALS_ATTR}' must decode to a JSON object.")
        return None

    expected_scalars = {
        "schema": WAVELENGTH_POLYNOMIAL_SCHEMA,
        "coefficient_order": WAVELENGTH_POLYNOMIAL_COEFFICIENT_ORDER,
        "input": DETECTOR_PIXEL_FIELD,
        "input_units": "pixel",
        "output": "wavelength",
        "output_units": "nm",
    }
    structure_ok = True
    for key, expected in expected_scalars.items():
        if payload.get(key) != expected:
            report.errors.append(
                f"'{WAVELENGTH_POLYNOMIALS_ATTR}' field {key!r} must be {expected!r}."
            )
            structure_ok = False

    orders = payload.get("orders")
    if not isinstance(orders, list) or not orders:
        report.errors.append(
            f"'{WAVELENGTH_POLYNOMIALS_ATTR}' field 'orders' must be a non-empty list."
        )
        return None

    identifiers: set[int] = set()
    for index, item in enumerate(orders):
        if not _check_polynomial_order(item, index, identifiers, report):
            structure_ok = False

    return identifiers if structure_ok else None


def _check_applied_absolute_calibration_factor(
    ds: xr.Dataset,
    report: ValidationReport,
) -> None:
    name = APPLIED_ABSOLUTE_CALIBRATION_FACTOR_FIELD
    field = _check_wavelength_field_shape(ds, report, name)
    if field is None:
        return
    if not _is_real_numeric_dtype(field.dtype):
        report.errors.append(f"'{name}' must have a real numeric dtype, got {field.dtype}.")
    else:
        values = np.asarray(field.values)
        if not np.all(np.isfinite(values)):
            report.errors.append(f"'{name}' must contain only finite values.")
        if np.any(values <= 0):
            report.errors.append(f"'{name}' values must be strictly positive.")

    _require_nonempty_string_attr(field, report, name, "units")
    _require_nonempty_string_attr(field, report, name, "source_units")
    application = _require_nonempty_string_attr(field, report, name, "application")
    if application is not None and application != APPLIED_FACTOR_APPLICATION:
        report.errors.append(
            f"'{name}' attribute 'application' must be {APPLIED_FACTOR_APPLICATION!r}."
        )
    if ds.attrs.get("calibration_type") != "absolute":
        report.errors.append(
            f"'{name}' is an applied absolute-calibration factor, so "
            "calibration_type must be 'absolute'."
        )


# ------------------------------------------------------------------
# SpectroCube
# ------------------------------------------------------------------


class SpectroCube:
    """
    Calibrated spectral dataset.

    The intensity array can have any number of labeled dimensions, but
    "wavelength" must always be one of them.  Common shapes:

        (wavelength,)                        — single spectrum
        (frame, wavelength)                  — time series / shot sequence
        (chord, time, wavelength)            — multi-chord time-resolved

    Use the class-method constructors rather than instantiating directly:

        SpectroCube.from_arrays(wavelength, intensity, ...)
        SpectroCube.from_dataset(ds)
        SpectroCube.load(path)

    The underlying xarray Dataset is always available as ``.ds``.
    """

    ds: xr.Dataset

    # ------------------------------------------------------------------
    # Constructors
    # ------------------------------------------------------------------

    @classmethod
    def from_arrays(
        cls,
        wavelength: np.ndarray,
        intensity: np.ndarray,
        instrument_id: str,
        calibration_type: str,
        intensity_units: str,
        wavelength_medium: str = "air",
        dims: tuple[str, ...] | None = None,
        coords: dict[str, np.ndarray] | None = None,
        **attrs: object,
    ) -> SpectroCube:
        """
        Construct a SpectroCube from numpy arrays.

        Parameters
        ----------
        wavelength : array-like, shape (n_wavelengths,)
            Wavelength axis in nm.
        intensity : array-like
            Spectral intensity.  Dimension inference rules:

            * 1D → dims forced to ``("wavelength",)``
            * 2D → dims inferred as ``("frame", "wavelength")`` when *dims*
              is not supplied
            * 3D or higher → *dims* must be provided explicitly

        instrument_id : str
            Short identifier for the instrument.
        calibration_type : str
            One of ``"counts"``, ``"relative"``, ``"absolute"``.
        intensity_units : str
            Physical units string, e.g. ``"counts"``, ``"a.u."``,
            ``"ph/s/nm/sr"``.
        wavelength_medium : str
            ``"air"`` or ``"vacuum"``.  Default: ``"air"``.
        dims : tuple of str, optional
            Dimension names for intensity.  Must include ``"wavelength"``.
        coords : dict mapping dim-name → array-like, optional
            Coordinate arrays for non-wavelength dimensions.  Dimensions
            not listed here receive auto-generated integer ranges.
        **attrs
            Additional metadata stored in ``ds.attrs``, e.g.
            ``exposure_s=0.5``, ``spectrometer="Echelle ESA-3"``.
        """
        wavelength = np.asarray(wavelength, dtype=float)
        intensity = np.asarray(intensity, dtype=float)

        resolved_dims = _resolve_dims(intensity.ndim, dims)

        if "wavelength" not in resolved_dims:
            raise ValueError(f"'wavelength' must be in dims, got {resolved_dims!r}")

        if len(resolved_dims) != intensity.ndim:
            raise ValueError(
                f"len(dims)={len(resolved_dims)} does not match intensity.ndim={intensity.ndim}"
            )

        xr_coords = _build_xr_coords(
            wavelength, wavelength_medium, intensity, resolved_dims, coords or {}
        )

        ds = xr.Dataset(
            {
                "intensity": xr.DataArray(
                    intensity,
                    dims=list(resolved_dims),
                    attrs={"units": intensity_units, "long_name": "Spectral intensity"},
                ),
            },
            coords=xr_coords,
        )

        ds.attrs["spectrocube_version"] = SPECTROCUBE_VERSION
        ds.attrs["instrument_id"] = instrument_id
        ds.attrs["calibration_type"] = calibration_type
        ds.attrs["intensity_units"] = intensity_units
        ds.attrs["wavelength_medium"] = wavelength_medium

        for k, v in attrs.items():
            if v is not None:
                ds.attrs[k] = v

        return cls.from_dataset(ds)

    @classmethod
    def from_dataset(cls, ds: xr.Dataset) -> SpectroCube:
        """
        Wrap an existing xarray Dataset as a SpectroCube.

        The caller is responsible for ensuring the Dataset has the expected
        structure (``intensity`` data variable, ``wavelength`` coordinate,
        required global attributes).  Use ``validate()`` to check.
        """
        obj = cls.__new__(cls)
        obj.ds = ds
        return obj

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def wavelength(self) -> np.ndarray:
        return self.ds["wavelength"].values

    @property
    def intensity(self) -> np.ndarray:
        return self.ds["intensity"].values

    @property
    def dims(self) -> tuple[str, ...]:
        """Ordered dimension names of the intensity array."""
        return tuple(str(dim) for dim in self.ds["intensity"].dims)

    @property
    def sizes(self) -> dict[str, int]:
        """Mapping of every dimension name to its size."""
        return {str(dim): int(size) for dim, size in self.ds.sizes.items()}

    @property
    def calibration_type(self) -> str:
        return self.ds.attrs["calibration_type"]

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate(self) -> ValidationReport:
        """Check the SpectroCube for required fields and consistency."""
        report = ValidationReport()
        attrs = self.ds.attrs

        # --- "intensity" must exist ---
        if "intensity" not in self.ds.data_vars:
            report.errors.append("'intensity' not found in data variables.")
            return report

        # --- Required global attributes ---
        required = [
            "spectrocube_version",
            "instrument_id",
            "calibration_type",
            "intensity_units",
            "wavelength_medium",
        ]
        for attr in required:
            if attr not in attrs or attrs[attr] in (None, ""):
                report.errors.append(f"Missing required attribute: '{attr}'")

        # --- calibration_type and wavelength_medium validity ---
        cal = attrs.get("calibration_type", "")
        if cal and cal not in VALID_CALIBRATION_TYPES:
            report.errors.append(
                f"calibration_type '{cal}' is not valid. Must be one of: {VALID_CALIBRATION_TYPES}"
            )
        medium = attrs.get("wavelength_medium", "")
        if medium and medium not in VALID_WAVELENGTH_MEDIUM:
            report.errors.append(
                f"wavelength_medium '{medium}' is not valid. "
                f"Must be one of: {VALID_WAVELENGTH_MEDIUM}"
            )

        if cal == "absolute":
            _check_absolute_calibration(attrs, report)

        _check_wavelength_coord(self.ds, report)

        _check_detector_pixel(self.ds, report)
        echelle_orders = _check_echelle_order(self.ds, report)
        polynomial_orders = _check_wavelength_polynomials(attrs, report)
        _check_applied_absolute_calibration_factor(self.ds, report)
        if (
            echelle_orders is not None
            and polynomial_orders is not None
            and echelle_orders != polynomial_orders
        ):
            report.errors.append(
                f"'{WAVELENGTH_POLYNOMIALS_ATTR}' order identifiers "
                f"{sorted(polynomial_orders)} do not match '{ECHELLE_ORDER_FIELD}' "
                f"values {sorted(echelle_orders)}."
            )

        # --- intensity must depend on the wavelength dimension ---
        intensity_dims = self.ds["intensity"].dims
        if "wavelength" not in intensity_dims:
            report.errors.append(
                f"'intensity' does not depend on 'wavelength' dimension "
                f"(dims: {tuple(intensity_dims)!r})."
            )

        # --- NaN / Inf check ---
        intensity_vals = self.ds["intensity"].values
        n_nan = int(np.sum(~np.isfinite(intensity_vals)))
        if n_nan > 0:
            frac = n_nan / intensity_vals.size
            report.warnings.append(
                f"Intensity contains {n_nan} non-finite values ({frac:.1%} of array). "
                "Check for bad pixels or stitching gaps."
            )

        return report

    # ------------------------------------------------------------------
    # IO
    # ------------------------------------------------------------------

    def save(self, path: str, validate: bool = True) -> None:
        """
        Save to NetCDF (.nc).

        Parameters
        ----------
        path : str
            Output file path.  Should end in ``.nc``.
        validate : bool
            If True, validate before saving.  Prints a report on warnings;
            raises ``ValueError`` on errors.
        """
        if validate:
            report = self.validate()
            if not report.ok or report.warnings:
                print(report)
                if not report.ok:
                    raise ValueError("SpectroCube has validation errors. Fix before saving.")

        self.ds.to_netcdf(path)

    @classmethod
    def load(cls, path: str) -> SpectroCube:
        """
        Load a SpectroCube from a NetCDF file.

        Data is loaded eagerly so the file handle is released immediately.
        """
        return cls.from_dataset(xr.load_dataset(path))

    # ------------------------------------------------------------------
    # Repr
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        attrs = self.ds.attrs
        if "intensity" in self.ds.data_vars:
            dims_str = ", ".join(f"{d}={self.ds.sizes[d]}" for d in self.dims)
        else:
            dims_str = "?"
        wl_da = self.ds.coords.get("wavelength")
        if wl_da is not None:
            wl_str = f"[{wl_da.values.min():.2f}..{wl_da.values.max():.2f}] nm"
        else:
            wl_str = "?"
        return (
            f"SpectroCube("
            f"instrument='{attrs.get('instrument_id', '?')}', "
            f"dims=({dims_str}), "
            f"wavelength={wl_str}, "
            f"calibration='{attrs.get('calibration_type', '?')}'"
            f")"
        )
