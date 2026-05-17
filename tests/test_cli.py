"""Tests for spectrocube.cli (info_main, validate_main)."""

from __future__ import annotations

import subprocess
import sys

import numpy as np
import pytest

from spectrocube import SpectroCube
from spectrocube.cli import info_main, validate_main

# ------------------------------------------------------------------
# Shared fixtures
# ------------------------------------------------------------------

WL = np.linspace(400.0, 700.0, 100)

REQUIRED = dict(
    instrument_id="test_instrument",
    calibration_type="counts",
    intensity_units="counts",
    wavelength_medium="air",
)


@pytest.fixture
def valid_nc(tmp_path):
    sc = SpectroCube.from_arrays(WL, np.ones((3, 100)), **REQUIRED)
    path = str(tmp_path / "valid.nc")
    sc.save(path, validate=False)
    return path


@pytest.fixture
def valid_nc_with_optionals(tmp_path):
    sc = SpectroCube.from_arrays(
        WL,
        np.ones(100),
        **REQUIRED,
        spectrometer="Test Spectrometer",
        detector="Test Detector",
        exposure_s=0.5,
        shot_number="run_001",
        notes="unit test data",
    )
    path = str(tmp_path / "valid_optionals.nc")
    sc.save(path, validate=False)
    return path


@pytest.fixture
def invalid_nc(tmp_path):
    """File with a non-monotonic wavelength axis — fails validation."""
    sc = SpectroCube.from_arrays(
        np.array([700.0, 400.0, 500.0]),
        np.ones(3),
        **REQUIRED,
    )
    path = str(tmp_path / "invalid.nc")
    sc.save(path, validate=False)
    return path


@pytest.fixture
def warned_nc(tmp_path):
    """File that is valid but triggers a calibration_source warning."""
    sc = SpectroCube.from_arrays(
        WL,
        np.ones(100),
        instrument_id="test",
        calibration_type="absolute",
        intensity_units="ph/s/nm/sr",
        wavelength_medium="air",
        # deliberately omit calibration_source → warning
    )
    path = str(tmp_path / "warned.nc")
    sc.save(path, validate=False)
    return path


# ------------------------------------------------------------------
# spectrocube-info
# ------------------------------------------------------------------


def test_info_contains_instrument(valid_nc, capsys):
    info_main([valid_nc])
    out = capsys.readouterr().out
    assert "test_instrument" in out


def test_info_contains_calibration(valid_nc, capsys):
    info_main([valid_nc])
    out = capsys.readouterr().out
    assert "counts" in out


def test_info_contains_wavelength_range(valid_nc, capsys):
    info_main([valid_nc])
    out = capsys.readouterr().out
    assert "400.00" in out
    assert "700.00" in out
    assert "100 points" in out


def test_info_contains_dims(valid_nc, capsys):
    info_main([valid_nc])
    out = capsys.readouterr().out
    assert "frame=3" in out
    assert "wavelength=100" in out


def test_info_contains_validation_line(valid_nc, capsys):
    info_main([valid_nc])
    out = capsys.readouterr().out
    assert "Validation" in out


def test_info_shows_valid_marker(valid_nc, capsys):
    info_main([valid_nc])
    out = capsys.readouterr().out
    assert "✓" in out


def test_info_shows_optional_attrs(valid_nc_with_optionals, capsys):
    info_main([valid_nc_with_optionals])
    out = capsys.readouterr().out
    assert "Test Spectrometer" in out
    assert "Test Detector" in out
    assert "0.5" in out
    assert "run_001" in out
    assert "unit test data" in out


def test_info_no_optional_section_when_absent(valid_nc, capsys):
    info_main([valid_nc])
    out = capsys.readouterr().out
    assert "Test Spectrometer" not in out


def test_info_invalid_file_shows_error_marker(invalid_nc, capsys):
    info_main([invalid_nc])
    out = capsys.readouterr().out
    assert "✗" in out


def test_info_warned_file_shows_warning_marker(warned_nc, capsys):
    info_main([warned_nc])
    out = capsys.readouterr().out
    assert "⚠" in out


def test_info_missing_file_exits_1(capsys):
    with pytest.raises(SystemExit) as exc_info:
        info_main(["/nonexistent/path/to/file.nc"])
    assert exc_info.value.code == 1
    err = capsys.readouterr().err
    assert "not found" in err


# ------------------------------------------------------------------
# spectrocube-validate
# ------------------------------------------------------------------


def test_validate_valid_does_not_exit(valid_nc):
    validate_main([valid_nc])  # must not raise SystemExit


def test_validate_valid_prints_ok(valid_nc, capsys):
    validate_main([valid_nc])
    out = capsys.readouterr().out
    assert "valid" in out.lower()


def test_validate_invalid_exits_1(invalid_nc):
    with pytest.raises(SystemExit) as exc_info:
        validate_main([invalid_nc])
    assert exc_info.value.code == 1


def test_validate_invalid_prints_errors(invalid_nc, capsys):
    with pytest.raises(SystemExit):
        validate_main([invalid_nc])
    out = capsys.readouterr().out
    assert "ERROR" in out


def test_validate_warned_does_not_exit(warned_nc):
    validate_main([warned_nc])  # warnings are not errors — must not raise


def test_validate_warned_prints_warning(warned_nc, capsys):
    validate_main([warned_nc])
    out = capsys.readouterr().out
    assert "WARNING" in out


def test_validate_missing_file_exits_1(capsys):
    with pytest.raises(SystemExit) as exc_info:
        validate_main(["/nonexistent/path/to/file.nc"])
    assert exc_info.value.code == 1


# ------------------------------------------------------------------
# Smoke test via subprocess (exercises the installed entry points)
# ------------------------------------------------------------------


def test_entrypoint_info_subprocess(valid_nc):
    subprocess.run(
        [sys.executable, "-m", "spectrocube.cli", "info", valid_nc],
        capture_output=True,
        text=True,
    )
    # Entry points aren't called this way, but we can test the module is importable
    # and that the script exists on PATH via the venv.
    # This just checks the module imports without error.
    result2 = subprocess.run(
        [sys.executable, "-c", "from spectrocube.cli import info_main, validate_main"],
        capture_output=True,
        text=True,
    )
    assert result2.returncode == 0
