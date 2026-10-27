"""Automated tests for POC-03's numerical and Plotly rendering behaviour."""
import numpy as np
import pytest

from poc03_plotly_sigma_bands import build_figure, example_fixture, prepare_band


def band(k=2.0, fixture=None):
    return prepare_band(**(example_fixture() if fixture is None else fixture), multiplier=k)


def test_tc01_chart_has_measured_estimated_and_band():
    fig = build_figure(band())
    assert [t.name for t in fig.data] == ["Lower band", "Sigma band", "Measured", "Estimated"]
    assert fig.data[1].fill == "tonexty"
    assert fig.layout.yaxis.title.text == "Voltage magnitude (V)"
    assert len(fig.data[2].x) == len(fig.data[3].x) == 5


def test_tc02_band_boundaries_match_independent_calculation():
    result = band(2.0)
    np.testing.assert_allclose(result["lower"], [228.8, 229.6, 229.0, 229.0, 229.7])
    np.testing.assert_allclose(result["upper"], [230.8, 232.0, 231.0, 231.8, 232.1])


def test_tc03_multiplier_changes_only_boundaries():
    a, b = band(1), band(3)
    for key in ("time", "measured", "estimated", "sigma"):
        np.testing.assert_array_equal(a[key], b[key])
    assert not np.array_equal(a["lower"], b["lower"])
    assert not np.array_equal(a["upper"], b["upper"])
    fa, fb = build_figure(a), build_figure(b)
    for idx in (2, 3):
        np.testing.assert_array_equal(fa.data[idx].y, fb.data[idx].y)


def test_tc04_zero_multiplier_collapses_to_centre():
    result = band(0)
    np.testing.assert_array_equal(result["lower"], result["estimated"])
    np.testing.assert_array_equal(result["upper"], result["estimated"])


@pytest.mark.parametrize("bad", [-1, float("nan"), float("inf")])
def test_tc05_invalid_multiplier_rejected(bad):
    with pytest.raises(ValueError, match="multiplier"):
        band(bad)


def test_tc06_missing_estimate_keeps_gap():
    fixture = example_fixture()
    fixture["estimated"][2] = np.nan
    result = band(fixture=fixture)
    assert np.isnan(result["lower"][2])
    assert np.isnan(result["upper"][2])
    fig = build_figure(result)
    assert all(t.connectgaps is False for t in fig.data)


def test_tc07_missing_measurement_does_not_invent_value():
    fixture = example_fixture()
    fixture["measured"][1] = np.nan
    result = band(fixture=fixture)
    assert np.isnan(result["measured"][1])
    assert np.isfinite(result["lower"][1])


def test_tc08_negative_sigma_rejected():
    fixture = example_fixture()
    fixture["sigma"][0] = -0.5
    with pytest.raises(ValueError, match="Sigma"):
        band(fixture=fixture)


def test_tc09_missing_sigma_for_estimate_rejected():
    fixture = example_fixture()
    fixture["sigma"][0] = np.nan
    with pytest.raises(ValueError, match="Sigma"):
        band(fixture=fixture)


def test_tc10_length_mismatch_rejected():
    fixture = example_fixture()
    fixture["sigma"] = fixture["sigma"][:-1]
    with pytest.raises(ValueError, match="equal nonzero lengths"):
        band(fixture=fixture)


def test_tc11_nonmonotonic_timestamps_rejected():
    fixture = example_fixture()
    fixture["time"][1] = fixture["time"][0]
    with pytest.raises(ValueError, match="strictly increasing"):
        band(fixture=fixture)


def test_tc12_input_arrays_are_not_modified():
    fixture = example_fixture()
    original = {k: v.copy() for k, v in fixture.items()}
    band(fixture=fixture)
    for key in fixture:
        np.testing.assert_array_equal(fixture[key], original[key])


def test_tc13_chart_boundaries_match_calculated_values():
    result = band(1.5)
    fig = build_figure(result)
    np.testing.assert_allclose(fig.data[0].y, result["lower"])
    np.testing.assert_allclose(fig.data[1].y, result["upper"])
    np.testing.assert_allclose(fig.data[2].y, result["measured"])
    np.testing.assert_allclose(fig.data[3].y, result["estimated"])


def test_tc14_infinite_voltage_rejected():
    fixture = example_fixture()
    fixture["measured"][0] = float("inf")
    with pytest.raises(ValueError, match="infinity"):
        band(fixture=fixture)
