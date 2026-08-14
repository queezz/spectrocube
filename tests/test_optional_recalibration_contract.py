"""Tests for the optional SpectroCube recalibration contract."""

from __future__ import annotations

import json

import numpy as np
import pytest
import xarray as xr

from spectrocube import (
    APPLIED_ABSOLUTE_CALIBRATION_FACTOR_FIELD,
    APPLIED_FACTOR_APPLICATION,
    DETECTOR_PIXEL_FIELD,
    ECHELLE_ORDER_FIELD,
    WAVELENGTH_POLYNOMIAL_COEFFICIENT_ORDER,
    WAVELENGTH_POLYNOMIAL_SCHEMA,
    WAVELENGTH_POLYNOMIALS_ATTR,
    SpectroCube,
)


def _plain_cube(*, absolute: bool = False) -> SpectroCube:
    wavelength = np.array([400.0, 401.0, 500.0, 501.0])
    return SpectroCube.from_arrays(
        wavelength,
        np.arange(8, dtype=float).reshape(2, 4) + 1.0,
        instrument_id="neutral_fixture",
        calibration_type="absolute" if absolute else "counts",
        intensity_units="W/m2/nm/sr" if absolute else "counts",
        wavelength_medium="air",
        **({"calibration_source": "fixture standard"} if absolute else {}),
    )


def _polynomial_payload(*, orders: tuple[int, ...] = (10, 11)) -> dict[str, object]:
    return {
        "schema": WAVELENGTH_POLYNOMIAL_SCHEMA,
        "coefficient_order": WAVELENGTH_POLYNOMIAL_COEFFICIENT_ORDER,
        "input": DETECTOR_PIXEL_FIELD,
        "input_units": "pixel",
        "output": "wavelength",
        "output_units": "nm",
        "orders": [
            {"order": order, "coefficients": [1.0e-6, -0.02, 400.0 + index * 100]}
            for index, order in enumerate(orders)
        ],
    }


def _add_detector_pixel(sc: SpectroCube) -> None:
    sc.ds.coords[DETECTOR_PIXEL_FIELD] = xr.DataArray(
        np.array([2047.0, 2046.0, 2047.0, 2046.0]),
        dims=("wavelength",),
        attrs={
            "units": "pixel",
            "detector_axis": "column",
            "reference_frame": "raw_detector",
            "index_origin": 0,
        },
    )


def _add_echelle_order(sc: SpectroCube) -> None:
    sc.ds.coords[ECHELLE_ORDER_FIELD] = xr.DataArray(
        np.array([10, 10, 11, 11], dtype=np.int16),
        dims=("wavelength",),
    )


def _add_polynomials(sc: SpectroCube, *, orders: tuple[int, ...] = (10, 11)) -> None:
    sc.ds.attrs[WAVELENGTH_POLYNOMIALS_ATTR] = json.dumps(
        _polynomial_payload(orders=orders),
        separators=(",", ":"),
        sort_keys=True,
    )


def _add_applied_factor(sc: SpectroCube) -> None:
    sc.ds[APPLIED_ABSOLUTE_CALIBRATION_FACTOR_FIELD] = xr.DataArray(
        np.array([0.5, 0.6, 0.7, 0.8]),
        dims=("wavelength",),
        attrs={
            "units": "W/m2/nm/sr per (counts/s)",
            "source_units": "counts/s",
            "application": APPLIED_FACTOR_APPLICATION,
        },
    )


def _complete_cube() -> SpectroCube:
    sc = _plain_cube(absolute=True)
    _add_detector_pixel(sc)
    _add_echelle_order(sc)
    _add_polynomials(sc)
    _add_applied_factor(sc)
    return sc


def test_plain_legacy_style_cube_remains_valid_without_optional_fields():
    sc = _plain_cube()
    sc.ds.attrs["spectrocube_version"] = "0.1.0"
    report = sc.validate()
    assert report.ok, str(report)


def test_complete_echelle_shaped_fixture_validates():
    report = _complete_cube().validate()
    assert report.ok, str(report)


@pytest.mark.parametrize("field", ["detector", "order", "polynomial", "factor"])
def test_each_optional_representation_can_appear_independently(field: str):
    sc = _plain_cube(absolute=field == "factor")
    {
        "detector": _add_detector_pixel,
        "order": _add_echelle_order,
        "polynomial": _add_polynomials,
        "factor": _add_applied_factor,
    }[field](sc)
    report = sc.validate()
    assert report.ok, str(report)


def test_detector_pixel_preserves_pre_orientation_raw_columns():
    sc = _plain_cube()
    _add_detector_pixel(sc)
    np.testing.assert_array_equal(sc.ds[DETECTOR_PIXEL_FIELD], [2047, 2046, 2047, 2046])
    assert sc.ds[DETECTOR_PIXEL_FIELD].attrs == {
        "units": "pixel",
        "detector_axis": "column",
        "reference_frame": "raw_detector",
        "index_origin": 0,
    }
    assert sc.validate().ok


@pytest.mark.parametrize(
    ("values", "dims", "attrs", "message"),
    [
        ([1.0, 2.0], ("pixel",), {}, "dimensions"),
        ([1.0, 2.0, 3.0, np.nan], ("wavelength",), {}, "finite"),
        (["a", "b", "c", "d"], ("wavelength",), {}, "numeric dtype"),
        ([1.0, 2.0, 3.0, 4.0], ("wavelength",), {}, "requires a non-empty 'units'"),
    ],
)
def test_detector_pixel_rejects_bad_shape_values_dtype_or_convention(values, dims, attrs, message):
    sc = _plain_cube()
    sc.ds.coords[DETECTOR_PIXEL_FIELD] = xr.DataArray(values, dims=dims, attrs=attrs)
    report = sc.validate()
    assert not report.ok
    assert any(message in error for error in report.errors)


def test_detector_pixel_rejects_invalid_origin():
    sc = _plain_cube()
    _add_detector_pixel(sc)
    sc.ds[DETECTOR_PIXEL_FIELD].attrs["index_origin"] = 0.5
    assert any("index_origin" in error for error in sc.validate().errors)


def test_echelle_order_requires_integer_nonnegative_values():
    sc = _plain_cube()
    sc.ds.coords[ECHELLE_ORDER_FIELD] = xr.DataArray(
        np.array([10.0, 10.0, 11.0, 11.0]), dims=("wavelength",)
    )
    assert any("integer dtype" in error for error in sc.validate().errors)

    sc.ds.coords[ECHELLE_ORDER_FIELD] = xr.DataArray(
        np.array([10, 10, -1, -1]), dims=("wavelength",)
    )
    assert any("non-negative" in error for error in sc.validate().errors)


@pytest.mark.parametrize(
    ("raw", "message"),
    [
        ("{broken", "malformed JSON"),
        ('{"schema":"a","schema":"b"}', "duplicate JSON member"),
        (json.dumps([]), "JSON object"),
        (json.dumps({}), "field 'schema'"),
        (
            json.dumps({**_polynomial_payload(), "coefficient_order": "ascending_power"}),
            "coefficient_order",
        ),
        (json.dumps({**_polynomial_payload(), "orders": []}), "non-empty list"),
    ],
)
def test_polynomial_json_rejects_malformed_schema(raw: str, message: str):
    sc = _plain_cube()
    sc.ds.attrs[WAVELENGTH_POLYNOMIALS_ATTR] = raw
    report = sc.validate()
    assert not report.ok
    assert any(message in error for error in report.errors)


@pytest.mark.parametrize(
    ("orders", "message"),
    [
        ([{"order": True, "coefficients": [1.0]}], "non-negative integer"),
        ([{"order": 10, "coefficients": []}], "non-empty list"),
        ([{"order": 10, "coefficients": [1.0, "x"]}], "finite JSON numbers"),
        ([{"order": 10, "coefficients": [0.0, 1.0]}], "actual degree"),
        (
            [
                {"order": 10, "coefficients": [1.0]},
                {"order": 10, "coefficients": [2.0]},
            ],
            "duplicates order identifier",
        ),
    ],
)
def test_polynomial_json_rejects_invalid_order_records(orders, message: str):
    sc = _plain_cube()
    payload = {**_polynomial_payload(), "orders": orders}
    sc.ds.attrs[WAVELENGTH_POLYNOMIALS_ATTR] = json.dumps(payload)
    report = sc.validate()
    assert not report.ok
    assert any(message in error for error in report.errors)


def test_polynomial_json_rejects_nonstandard_nonfinite_json_number():
    sc = _plain_cube()
    raw = json.dumps(_polynomial_payload()).replace("1e-06", "NaN", 1)
    sc.ds.attrs[WAVELENGTH_POLYNOMIALS_ATTR] = raw
    assert any("malformed JSON" in error for error in sc.validate().errors)


def test_polynomial_order_references_match_echelle_order_when_both_present():
    sc = _plain_cube()
    _add_echelle_order(sc)
    _add_polynomials(sc, orders=(10, 12))
    report = sc.validate()
    assert not report.ok
    assert any("do not match" in error for error in report.errors)


@pytest.mark.parametrize(
    ("values", "dims", "attrs", "message"),
    [
        ([0.5, 0.6], ("factor_sample",), {}, "dimensions"),
        ([0.5, 0.6, np.inf, 0.8], ("wavelength",), {}, "finite"),
        ([0.5, 0.0, 0.7, 0.8], ("wavelength",), {}, "strictly positive"),
        (["a", "b", "c", "d"], ("wavelength",), {}, "numeric dtype"),
    ],
)
def test_applied_factor_rejects_bad_shape_values_or_dtype(values, dims, attrs, message):
    sc = _plain_cube(absolute=True)
    sc.ds[APPLIED_ABSOLUTE_CALIBRATION_FACTOR_FIELD] = xr.DataArray(values, dims=dims, attrs=attrs)
    report = sc.validate()
    assert not report.ok
    assert any(message in error for error in report.errors)


def test_applied_factor_requires_interpretation_metadata():
    sc = _plain_cube(absolute=True)
    _add_applied_factor(sc)
    del sc.ds[APPLIED_ABSOLUTE_CALIBRATION_FACTOR_FIELD].attrs["source_units"]
    assert any("source_units" in error for error in sc.validate().errors)

    _add_applied_factor(sc)
    sc.ds[APPLIED_ABSOLUTE_CALIBRATION_FACTOR_FIELD].attrs["application"] = "divide"
    assert any("application" in error for error in sc.validate().errors)


def test_applied_factor_requires_absolute_stored_signal():
    sc = _plain_cube()
    _add_applied_factor(sc)
    assert any("calibration_type" in error for error in sc.validate().errors)


def test_dataset_conversion_preserves_arbitrary_legal_extras():
    sc = _complete_cube()
    sc.ds.attrs["writer_extension"] = "kept"
    sc.ds.coords["sample_label"] = xr.DataArray(np.array(["a", "b"], dtype="U1"), dims=("frame",))
    sc.ds["uncertainty"] = xr.DataArray(
        np.full((2, 4), 0.25), dims=("frame", "wavelength"), attrs={"units": "same"}
    )
    original = sc.ds
    wrapped = SpectroCube.from_dataset(original)
    assert wrapped.ds is original
    assert wrapped.ds.identical(original)
    assert wrapped.validate().ok


def test_netcdf_roundtrip_preserves_contract_and_unknown_extras(tmp_path):
    sc = _complete_cube()
    sc.ds.attrs["writer_extension"] = "kept"
    sc.ds.coords["sample_index"] = xr.DataArray(np.array([4, 7]), dims=("frame",))
    sc.ds["uncertainty"] = xr.DataArray(
        np.full((2, 4), 0.25), dims=("frame", "wavelength"), attrs={"units": "same"}
    )
    path = tmp_path / "optional-contract.nc"
    sc.save(str(path))
    loaded = SpectroCube.load(str(path))

    assert loaded.validate().ok
    assert loaded.ds.attrs[WAVELENGTH_POLYNOMIALS_ATTR] == sc.ds.attrs[WAVELENGTH_POLYNOMIALS_ATTR]
    assert loaded.ds.attrs["writer_extension"] == "kept"
    np.testing.assert_array_equal(loaded.ds[DETECTOR_PIXEL_FIELD], sc.ds[DETECTOR_PIXEL_FIELD])
    np.testing.assert_array_equal(loaded.ds[ECHELLE_ORDER_FIELD], sc.ds[ECHELLE_ORDER_FIELD])
    np.testing.assert_array_equal(
        loaded.ds[APPLIED_ABSOLUTE_CALIBRATION_FACTOR_FIELD],
        sc.ds[APPLIED_ABSOLUTE_CALIBRATION_FACTOR_FIELD],
    )
    np.testing.assert_array_equal(loaded.ds["sample_index"], sc.ds["sample_index"])
    np.testing.assert_array_equal(loaded.ds["uncertainty"], sc.ds["uncertainty"])
