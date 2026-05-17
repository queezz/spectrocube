"""
SpectroCube core module.

Defines the SpectroCube class: a calibrated spectral dataset with
[frame, wavelength] dimensions, metadata, and NetCDF IO.
"""

from __future__ import annotations

import datetime
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
# SpectroCube
# ------------------------------------------------------------------

class SpectroCube:
    """
    Calibrated spectral dataset.

    Core dimensions:
        frame      : acquisition index (0, 1, 2, ...)
        wavelength : wavelength axis in nm (air or vacuum)

    Intensity array shape: (n_frames, n_wavelengths)
    Single acquisition: n_frames = 1, shape (1, n_wavelengths)

    Parameters
    ----------
    wavelength : array-like, shape (n_wavelengths,)
        Wavelength axis in nm.
    intensity : array-like, shape (n_frames, n_wavelengths) or (n_wavelengths,)
        Spectral intensity. 1D input is treated as single frame.
    instrument_id : str
        Short identifier for the instrument, e.g. "echelle_kyoto", "libs_lab".
    calibration_type : str
        One of: "counts", "relative", "absolute".
    intensity_units : str
        Physical units string, e.g. "counts", "a.u.", "ph/s/nm/sr".
    wavelength_medium : str
        "air" or "vacuum". Default: "air".
    wavelength_accuracy_nm : float, optional
        Estimated wavelength accuracy in nm (scalar, for fitting slack).
    exposure_s : float, optional
        Exposure time per frame in seconds.
    frame_interval_s : float, optional
        Time between frame starts in seconds.
    t_start : str or datetime, optional
        Acquisition start time (ISO 8601 string or datetime object).
    calibration_source : str, optional
        Description of flux/wavelength calibration source.
        Required (as warning) when calibration_type == "absolute".
    spectrometer : str, optional
        Spectrometer model/description.
    detector : str, optional
        Detector model/description.
    grating : str, optional
        Grating description.
    slit_um : float, optional
        Slit width in micrometers.
    shot_number : str or int, optional
        Shot/sample/run identifier.
    notes : str, optional
        Free-text notes.
    extra_attrs : dict, optional
        Any additional metadata to store.
    """

    def __init__(
        self,
        wavelength: np.ndarray,
        intensity: np.ndarray,
        instrument_id: str,
        calibration_type: str,
        intensity_units: str,
        wavelength_medium: str = "air",
        wavelength_accuracy_nm: float | None = None,
        exposure_s: float | None = None,
        frame_interval_s: float | None = None,
        t_start: str | datetime.datetime | None = None,
        calibration_source: str | None = None,
        spectrometer: str | None = None,
        detector: str | None = None,
        grating: str | None = None,
        slit_um: float | None = None,
        shot_number: str | int | None = None,
        notes: str | None = None,
        extra_attrs: dict[str, object] | None = None,
    ):
        wavelength = np.asarray(wavelength, dtype=float)
        intensity = np.asarray(intensity, dtype=float)

        # Promote 1D intensity to (1, n_wavelengths)
        if intensity.ndim == 1:
            intensity = intensity[np.newaxis, :]

        n_frames, n_wl = intensity.shape
        frame_index = np.arange(n_frames)

        # Build xarray Dataset
        self.ds = xr.Dataset(
            {
                "intensity": xr.DataArray(
                    intensity,
                    dims=["frame", "wavelength"],
                    attrs={"units": intensity_units, "long_name": "Spectral intensity"},
                ),
            },
            coords={
                "wavelength": xr.DataArray(
                    wavelength,
                    dims=["wavelength"],
                    attrs={"units": "nm", "medium": wavelength_medium, "long_name": "Wavelength"},
                ),
                "frame": xr.DataArray(
                    frame_index,
                    dims=["frame"],
                    attrs={"long_name": "Frame index"},
                ),
            },
        )

        # Required global attributes
        self.ds.attrs["spectrocube_version"] = SPECTROCUBE_VERSION
        self.ds.attrs["instrument_id"] = instrument_id
        self.ds.attrs["calibration_type"] = calibration_type
        self.ds.attrs["intensity_units"] = intensity_units
        self.ds.attrs["wavelength_medium"] = wavelength_medium

        # Optional attributes — only stored if provided
        _optional = {
            "wavelength_accuracy_nm": wavelength_accuracy_nm,
            "exposure_s": exposure_s,
            "frame_interval_s": frame_interval_s,
            "t_start": str(t_start) if t_start is not None else None,
            "calibration_source": calibration_source,
            "spectrometer": spectrometer,
            "detector": detector,
            "grating": grating,
            "slit_um": slit_um,
            "shot_number": str(shot_number) if shot_number is not None else None,
            "notes": notes,
        }
        for k, v in _optional.items():
            if v is not None:
                self.ds.attrs[k] = v

        if extra_attrs:
            self.ds.attrs.update(extra_attrs)

    # ------------------------------------------------------------------
    # Convenience properties
    # ------------------------------------------------------------------

    @property
    def wavelength(self) -> np.ndarray:
        return self.ds["wavelength"].values

    @property
    def intensity(self) -> np.ndarray:
        return self.ds["intensity"].values

    @property
    def n_frames(self) -> int:
        return self.ds.sizes["frame"]

    @property
    def n_wavelengths(self) -> int:
        return self.ds.sizes["wavelength"]

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

        # --- Required fields ---
        required = ["spectrocube_version", "instrument_id", "calibration_type", "intensity_units", "wavelength_medium"]
        for attr in required:
            if attr not in attrs or attrs[attr] in (None, ""):
                report.errors.append(f"Missing required attribute: '{attr}'")

        # --- calibration_type must be valid ---
        cal = attrs.get("calibration_type", "")
        if cal and cal not in VALID_CALIBRATION_TYPES:
            report.errors.append(
                f"calibration_type '{cal}' is not valid. Must be one of: {VALID_CALIBRATION_TYPES}"
            )

        # --- wavelength_medium must be valid ---
        medium = attrs.get("wavelength_medium", "")
        if medium and medium not in VALID_WAVELENGTH_MEDIUM:
            report.errors.append(
                f"wavelength_medium '{medium}' is not valid. Must be one of: {VALID_WAVELENGTH_MEDIUM}"
            )

        # --- Absolute calibration: units and source ---
        if cal == "absolute":
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

        # --- Wavelength sanity ---
        wl = self.wavelength
        if len(wl) == 0:
            report.errors.append("Wavelength axis is empty.")
        else:
            if not np.all(np.diff(wl) > 0):
                report.errors.append("Wavelength axis is not monotonically increasing.")
            if wl.min() < 100 or wl.max() > 25000:
                report.warnings.append(
                    f"Wavelength range [{wl.min():.1f}, {wl.max():.1f}] nm looks unusual. "
                    "Check units — should be nm."
                )

        # --- Intensity shape ---
        if self.intensity.shape[1] != len(wl):
            report.errors.append(
                f"Intensity shape {self.intensity.shape} is inconsistent with "
                f"wavelength length {len(wl)}."
            )

        # --- NaN / Inf check ---
        n_nan = int(np.sum(~np.isfinite(self.intensity)))
        if n_nan > 0:
            frac = n_nan / self.intensity.size
            report.warnings.append(
                f"Intensity contains {n_nan} non-finite values ({frac:.1%} of array). "
                "Check for bad pixels or stitching gaps."
            )

        # --- Optional but encouraged ---
        encouraged = ["spectrometer", "detector", "grating", "exposure_s"]
        missing_enc = [attr for attr in encouraged if attr not in attrs]
        if missing_enc:
            report.warnings.append(
                f"Optional but encouraged attributes not set: {missing_enc}"
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
            Output file path. Should end in .nc
        validate : bool
            If True, validate before saving. Saves anyway but prints report
            if there are warnings or errors.
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

        Returns a SpectroCube instance with .ds populated.
        The loaded object bypasses __init__ — ds is attached directly.
        Data is loaded eagerly so the file handle is released immediately.
        """
        ds = xr.load_dataset(path)
        obj = cls.__new__(cls)
        obj.ds = ds
        return obj

    # ------------------------------------------------------------------
    # Repr
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        attrs = self.ds.attrs
        return (
            f"SpectroCube("
            f"instrument='{attrs.get('instrument_id', '?')}', "
            f"frames={self.n_frames}, "
            f"wavelength=[{self.wavelength.min():.2f}..{self.wavelength.max():.2f}] nm, "
            f"calibration='{attrs.get('calibration_type', '?')}'"
            f")"
        )
