"""
Command-line inspection tools for SpectroCube files.

Entry points
------------
spectrocube-info      PATH  — print a compact human-readable summary
spectrocube-validate  PATH  — validate and exit 0 (ok) or 1 (errors)
"""

from __future__ import annotations

import argparse
import sys

from spectrocube.core import SpectroCube

# Optional attrs printed by the info command, in display order.
_INFO_ATTRS = (
    "spectrometer",
    "detector",
    "grating",
    "slit_um",
    "exposure_s",
    "frame_interval_s",
    "t_start",
    "calibration_source",
    "shot_number",
    "wavelength_accuracy_nm",
    "notes",
)


def _load_or_exit(path: str) -> SpectroCube:
    try:
        return SpectroCube.load(path)
    except FileNotFoundError:
        print(f"Error: file not found: {path}", file=sys.stderr)
        sys.exit(1)
    except Exception as exc:  # noqa: BLE001
        print(f"Error loading {path!r}: {exc}", file=sys.stderr)
        sys.exit(1)


def _validation_summary(sc: SpectroCube) -> str:
    report = sc.validate()
    if report.ok and not report.warnings:
        return "✓ valid"
    if report.ok:
        return f"⚠ valid with {len(report.warnings)} warning(s)"
    return f"✗ {len(report.errors)} error(s), {len(report.warnings)} warning(s)"


def _print_info(sc: SpectroCube, path: str) -> None:
    """Print a compact summary of *sc* to stdout."""
    attrs = sc.ds.attrs
    cal = attrs.get("calibration_type", "?")
    units = attrs.get("intensity_units", "?")
    medium = attrs.get("wavelength_medium", "?")

    print(f"File:          {path}")
    print(f"Instrument:    {attrs.get('instrument_id', '?')}")
    print(f"Calibration:   {cal} ({units})")

    if "wavelength" in sc.ds.coords:
        wl = sc.wavelength
        print(f"Wavelength:    {medium}, {wl.min():.2f}\u2013{wl.max():.2f} nm, {len(wl)} points")
    else:
        print(f"Wavelength:    {medium}, (coordinate missing)")

    if "intensity" in sc.ds.data_vars:
        dims_str = ", ".join(f"{d}={sc.ds.sizes[d]}" for d in sc.dims)
        print(f"Intensity:     {dims_str}")
    else:
        print("Intensity:     (variable missing)")

    present = [(k, attrs[k]) for k in _INFO_ATTRS if k in attrs]
    if present:
        print()
        for k, v in present:
            print(f"  {k + ':':<26} {v}")

    print()
    print(f"Validation:    {_validation_summary(sc)}")


def info_main(argv: list[str] | None = None) -> None:
    """Entry point for ``spectrocube-info``."""
    parser = argparse.ArgumentParser(
        prog="spectrocube-info",
        description="Print a summary of a SpectroCube .nc file.",
    )
    parser.add_argument("path", help="Path to a SpectroCube .nc file")
    args = parser.parse_args(argv)

    sc = _load_or_exit(args.path)
    _print_info(sc, args.path)


def validate_main(argv: list[str] | None = None) -> None:
    """Entry point for ``spectrocube-validate``."""
    parser = argparse.ArgumentParser(
        prog="spectrocube-validate",
        description="Validate a SpectroCube .nc file. Exits 0 if valid, 1 if errors found.",
    )
    parser.add_argument("path", help="Path to a SpectroCube .nc file")
    args = parser.parse_args(argv)

    sc = _load_or_exit(args.path)
    report = sc.validate()
    print(report)

    if not report.ok:
        sys.exit(1)
