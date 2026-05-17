"""Tests for spectrocube.core."""

from __future__ import annotations

import os
import tempfile

import numpy as np
import pytest
import xarray as xr

from spectrocube import SpectroCube

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


# ------------------------------------------------------------------
# from_arrays — dim inference and construction
# ------------------------------------------------------------------


def test_1d_intensity_wavelength_only():
    sc = SpectroCube.from_arrays(WL, np.ones(100), **REQUIRED)
    assert sc.dims == ("wavelength",)
    assert sc.intensity.shape == (100,)
    assert sc.wavelength.shape == (100,)
    assert sc.sizes == {"wavelength": 100}


def test_2d_inferred_dims():
    sc = SpectroCube.from_arrays(WL, np.ones((5, 100)), **REQUIRED)
    assert sc.dims == ("frame", "wavelength")
    assert sc.intensity.shape == (5, 100)
    assert sc.sizes["frame"] == 5
    assert sc.sizes["wavelength"] == 100


def test_2d_explicit_dims():
    sc = SpectroCube.from_arrays(WL, np.ones((10, 100)), dims=("time", "wavelength"), **REQUIRED)
    assert sc.dims == ("time", "wavelength")
    assert sc.sizes["time"] == 10


def test_3d_explicit_dims():
    sc = SpectroCube.from_arrays(
        WL,
        np.ones((3, 5, 100)),
        dims=("chord", "time", "wavelength"),
        **REQUIRED,
    )
    assert sc.dims == ("chord", "time", "wavelength")
    assert sc.sizes["chord"] == 3
    assert sc.sizes["time"] == 5
    assert sc.sizes["wavelength"] == 100


def test_3d_requires_dims():
    with pytest.raises(ValueError, match="dims"):
        SpectroCube.from_arrays(WL, np.ones((3, 5, 100)), **REQUIRED)


def test_wavelength_must_be_in_dims():
    with pytest.raises(ValueError, match="wavelength"):
        SpectroCube.from_arrays(
            WL, np.ones((5, 100)), dims=("frame", "spatial"), **REQUIRED
        )


def test_dims_length_mismatch():
    with pytest.raises(ValueError, match="len\\(dims\\)"):
        SpectroCube.from_arrays(
            WL, np.ones((5, 100)), dims=("frame", "extra", "wavelength"), **REQUIRED
        )


def test_extra_attrs_stored():
    sc = SpectroCube.from_arrays(WL, np.ones(100), exposure_s=0.5, notes="test", **REQUIRED)
    assert sc.ds.attrs["exposure_s"] == 0.5
    assert sc.ds.attrs["notes"] == "test"


def test_none_attrs_not_stored():
    sc = SpectroCube.from_arrays(WL, np.ones(100), exposure_s=None, **REQUIRED)
    assert "exposure_s" not in sc.ds.attrs


def test_custom_coords_used():
    t = np.array([0.0, 1.0, 2.0])
    sc = SpectroCube.from_arrays(
        WL,
        np.ones((3, 100)),
        dims=("time", "wavelength"),
        coords={"time": t},
        **REQUIRED,
    )
    np.testing.assert_array_equal(sc.ds["time"].values, t)


def test_auto_integer_coords_generated():
    sc = SpectroCube.from_arrays(WL, np.ones((4, 100)), **REQUIRED)
    np.testing.assert_array_equal(sc.ds["frame"].values, np.arange(4))


def test_calibration_type_property():
    sc = SpectroCube.from_arrays(WL, np.ones(100), **REQUIRED)
    assert sc.calibration_type == "counts"


def test_repr_contains_key_info():
    sc = SpectroCube.from_arrays(WL, np.ones((3, 100)), **REQUIRED)
    r = repr(sc)
    assert "test_instrument" in r
    assert "frame=3" in r
    assert "wavelength=100" in r
    assert "counts" in r


# ------------------------------------------------------------------
# from_dataset
# ------------------------------------------------------------------


def test_from_dataset_roundtrip():
    sc1 = SpectroCube.from_arrays(WL, np.ones((2, 100)), **REQUIRED)
    sc2 = SpectroCube.from_dataset(sc1.ds)
    np.testing.assert_array_equal(sc1.wavelength, sc2.wavelength)
    np.testing.assert_array_equal(sc1.intensity, sc2.intensity)
    assert sc2.dims == sc1.dims


# ------------------------------------------------------------------
# save / load
# ------------------------------------------------------------------


def _save_load(sc: SpectroCube) -> SpectroCube:
    with tempfile.NamedTemporaryFile(suffix=".nc", delete=False) as f:
        path = f.name
    try:
        sc.save(path, validate=False)
        return SpectroCube.load(path)
    finally:
        os.unlink(path)


def test_save_load_1d():
    sc = SpectroCube.from_arrays(WL, np.ones(100), **REQUIRED)
    sc2 = _save_load(sc)
    np.testing.assert_array_equal(sc.wavelength, sc2.wavelength)
    np.testing.assert_array_equal(sc.intensity, sc2.intensity)
    assert sc2.dims == sc.dims
    assert sc2.calibration_type == sc.calibration_type


def test_save_load_2d():
    sc = SpectroCube.from_arrays(WL, np.random.default_rng(0).random((3, 100)), **REQUIRED)
    sc2 = _save_load(sc)
    np.testing.assert_array_almost_equal(sc.intensity, sc2.intensity)
    assert sc2.dims == ("frame", "wavelength")


def test_save_load_3d():
    sc = SpectroCube.from_arrays(
        WL,
        np.ones((2, 4, 100)),
        dims=("chord", "time", "wavelength"),
        **REQUIRED,
    )
    sc2 = _save_load(sc)
    assert sc2.dims == ("chord", "time", "wavelength")
    assert sc2.sizes["chord"] == 2
    assert sc2.sizes["time"] == 4


def test_save_raises_on_validation_error():
    wl_bad = np.array([700.0, 400.0, 500.0])  # not monotonic
    sc = SpectroCube.from_arrays(wl_bad, np.ones(3), **REQUIRED)
    with tempfile.NamedTemporaryFile(suffix=".nc", delete=False) as f:
        path = f.name
    try:
        with pytest.raises(ValueError, match="validation errors"):
            sc.save(path, validate=True)
    finally:
        os.unlink(path)


# ------------------------------------------------------------------
# validate — passing cases
# ------------------------------------------------------------------


def test_validate_valid_1d():
    sc = SpectroCube.from_arrays(WL, np.ones(100), **REQUIRED)
    report = sc.validate()
    assert report.ok
    assert not report.warnings


def test_validate_valid_2d():
    sc = SpectroCube.from_arrays(WL, np.ones((5, 100)), **REQUIRED)
    report = sc.validate()
    assert report.ok


# ------------------------------------------------------------------
# validate — error cases
# ------------------------------------------------------------------


def test_validate_missing_intensity():
    ds = xr.Dataset(
        coords={"wavelength": xr.DataArray(WL, dims=["wavelength"])},
    )
    ds.attrs.update(
        spectrocube_version="0.1.0",
        instrument_id="x",
        calibration_type="counts",
        intensity_units="counts",
        wavelength_medium="air",
    )
    sc = SpectroCube.from_dataset(ds)
    report = sc.validate()
    assert not report.ok
    assert any("intensity" in e for e in report.errors)


def test_validate_missing_wavelength_coord():
    ds = xr.Dataset(
        {"intensity": xr.DataArray(np.ones((5, 100)), dims=["frame", "wavelength"])},
    )
    ds.attrs.update(
        spectrocube_version="0.1.0",
        instrument_id="x",
        calibration_type="counts",
        intensity_units="counts",
        wavelength_medium="air",
    )
    sc = SpectroCube.from_dataset(ds)
    report = sc.validate()
    assert not report.ok
    assert any("wavelength" in e for e in report.errors)


def test_validate_intensity_not_depending_on_wavelength():
    ds = xr.Dataset(
        {"intensity": xr.DataArray(np.ones((5, 100)), dims=["frame", "spatial"])},
        coords={"wavelength": xr.DataArray(WL, dims=["wavelength"])},
    )
    ds.attrs.update(
        spectrocube_version="0.1.0",
        instrument_id="x",
        calibration_type="counts",
        intensity_units="counts",
        wavelength_medium="air",
    )
    sc = SpectroCube.from_dataset(ds)
    report = sc.validate()
    assert not report.ok
    assert any("wavelength" in e for e in report.errors)


def test_validate_nonmonotonic_wavelength():
    wl = np.array([500.0, 400.0, 600.0])
    sc = SpectroCube.from_arrays(wl, np.ones(3), **REQUIRED)
    report = sc.validate()
    assert not report.ok
    assert any("monoton" in e for e in report.errors)


def test_validate_nonmonotonic_wavelength_2d():
    wl = np.array([600.0, 500.0, 400.0, 700.0])  # dip at start
    sc = SpectroCube.from_arrays(wl, np.ones((3, 4)), **REQUIRED)
    report = sc.validate()
    assert not report.ok


def test_validate_invalid_calibration_type():
    sc = SpectroCube.from_arrays(
        WL,
        np.ones(100),
        instrument_id="x",
        calibration_type="fancy",
        intensity_units="counts",
        wavelength_medium="air",
    )
    report = sc.validate()
    assert not report.ok
    assert any("calibration_type" in e for e in report.errors)


def test_validate_invalid_wavelength_medium():
    sc = SpectroCube.from_arrays(
        WL,
        np.ones(100),
        instrument_id="x",
        calibration_type="counts",
        intensity_units="counts",
        wavelength_medium="water",
    )
    report = sc.validate()
    assert not report.ok
    assert any("wavelength_medium" in e for e in report.errors)


def test_validate_absolute_missing_source_is_warning():
    sc = SpectroCube.from_arrays(
        WL,
        np.ones(100),
        instrument_id="x",
        calibration_type="absolute",
        intensity_units="ph/s/nm/sr",
        wavelength_medium="air",
    )
    report = sc.validate()
    assert report.ok  # no errors
    assert any("calibration_source" in w for w in report.warnings)


def test_validate_nonfinite_intensity_is_warning():
    intensity = np.ones(100)
    intensity[5] = np.nan
    sc = SpectroCube.from_arrays(WL, intensity, **REQUIRED)
    report = sc.validate()
    assert report.ok  # only warning, not error
    assert any("non-finite" in w for w in report.warnings)


def test_validate_missing_required_attr():
    sc = SpectroCube.from_arrays(WL, np.ones(100), **REQUIRED)
    del sc.ds.attrs["instrument_id"]
    report = sc.validate()
    assert not report.ok
    assert any("instrument_id" in e for e in report.errors)
