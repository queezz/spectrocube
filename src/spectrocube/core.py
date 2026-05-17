"""
SpectroCube core module.

Defines the SpectroCube class: a calibrated spectral dataset with an
arbitrary set of labeled dimensions, one of which must be "wavelength".
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import xarray as xr

# ------------------------------------------------------------------
# Constants
# ------------------------------------------------------------------

SPECTROCUBE_VERSION = "0.1.0"

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
        raise ValueError(
            f"dims must be provided explicitly for intensity with ndim={ndim}"
        )
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
        return tuple(self.ds["intensity"].dims)

    @property
    def sizes(self) -> dict[str, int]:
        """Mapping of every dimension name to its size."""
        return dict(self.ds.sizes)

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
