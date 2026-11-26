# SPDX-FileCopyrightText: Contributors to the Power Grid Model project <powergridmodel@lfenergy.org>
#
# SPDX-License-Identifier: MPL-2.0

"""Tests for uncertainty diagnostic figures."""

from typing import Any, cast

import numpy as np

from power_grid_model_ds._core.visualizer.measurement_comparison import MeasurementComparison
from power_grid_model_ds._core.visualizer.uncertainty_diagnostic_plot import create_uncertainty_diagnostic_figure


def test_creates_uncertainty_diagnostic_figure():
    comparison = MeasurementComparison(
        scenario_indices=np.array([0, 1, 2]),
        measured=np.array([10.0, 10.0, 10.0]),
        estimated=np.array([9.0, 11.0, 8.0]),
        sigma=np.array([2.0, 2.0, 2.0]),
    )

    figure = create_uncertainty_diagnostic_figure(comparison)
    data = cast(tuple[Any, ...], figure.data)

    assert len(data) == 1

    np.testing.assert_array_equal(
        data[0].x,
        [0, 1, 2],
    )

    np.testing.assert_allclose(
        data[0].y,
        [0.5, 0.5, 1.0],
    )

    hovertemplate = data[0].hovertemplate

    assert "Scenario: %{x}" in hovertemplate
    assert "Measured: %{customdata[1]}" in hovertemplate
    assert "Calculated: %{customdata[2]}" in hovertemplate
    assert "Sigma: %{customdata[3]}" in hovertemplate
    assert "Absolute normalized residual: %{customdata[0]}" in hovertemplate

    assert figure.layout.title.text == "Normalized residual"
    assert figure.layout.xaxis.title.text == "Scenario Index"
    assert figure.layout.yaxis.title.text == "Absolute normalized residual"
    assert figure.layout.yaxis.ticksuffix == " sigma"
    assert data[0].name == "Absolute normalized residual"


def test_includes_one_sigma_reference_line():
    comparison = MeasurementComparison(
        scenario_indices=np.array([0]),
        measured=np.array([10.0]),
        estimated=np.array([9.0]),
        sigma=np.array([2.0]),
    )

    figure = create_uncertainty_diagnostic_figure(comparison)

    assert len(figure.layout.shapes) == 1
    assert figure.layout.shapes[0].y0 == 1.0
    assert figure.layout.shapes[0].y1 == 1.0


def test_preserves_missing_and_infinite_diagnostic_information():
    comparison = MeasurementComparison(
        scenario_indices=np.array([0, 1, 2]),
        measured=np.array([10.0, 10.0, np.nan]),
        estimated=np.array([9.0, 10.0, 9.0]),
        sigma=np.array([0.0, 0.0, 2.0]),
    )

    figure = create_uncertainty_diagnostic_figure(comparison)
    data = cast(tuple[Any, ...], figure.data)

    np.testing.assert_allclose(
        data[0].y,
        [np.nan, np.nan, np.nan],
        equal_nan=True,
    )

    assert list(data[0].customdata) == [
        ["Positive infinity", "10", "9", "0"],
        ["Unavailable", "10", "10", "0"],
        ["Unavailable", "Unavailable", "9", "2"],
    ]


def test_undefined_discrepancies_have_visible_annotation():
    comparison = MeasurementComparison(
        scenario_indices=np.array([0, 1, 2]),
        measured=np.array([10.0, 10.0, np.nan]),
        estimated=np.array([9.0, 10.0, 9.0]),
        sigma=np.array([0.0, 0.0, 2.0]),
    )
    figure = create_uncertainty_diagnostic_figure(comparison)
    text = " ".join(str(annotation.text) for annotation in figure.layout.annotations)
    assert "0: zero sigma; nonzero difference" in text
    assert "1: zero sigma; zero difference" in text
    assert "2: measurement or estimate unavailable" in text


def test_hides_sigma_reference_when_all_discrepancies_unavailable():
    comparison = MeasurementComparison(
        scenario_indices=np.array([0, 1, 2]),
        measured=np.array([230.0, 235.0, 230.0]),
        estimated=np.array([229.0, 231.0, 228.0]),
        sigma=np.array([0.0, 0.0, 0.0]),
    )

    figure = create_uncertainty_diagnostic_figure(comparison)

    assert not figure.layout.shapes
    assert any("Unavailable scenarios (3)" in annotation.text for annotation in figure.layout.annotations)


def test_complete_series_uses_only_lines():
    comparison = MeasurementComparison(
        scenario_indices=np.arange(3),
        measured=np.array([10.0, 10.0, 10.0]),
        estimated=np.array([9.0, 11.0, 8.0]),
        sigma=np.full(3, 2.0),
    )

    figure = create_uncertainty_diagnostic_figure(comparison)
    data = cast(tuple[Any, ...], figure.data)

    assert len(data) == 1
    assert data[0].mode == "lines"


def test_missing_scenarios_preserve_line_gaps():
    comparison = MeasurementComparison(
        scenario_indices=np.arange(5),
        measured=np.array([10.0, 10.0, np.nan, 10.0, 10.0]),
        estimated=np.full(5, 9.0),
        sigma=np.full(5, 2.0),
    )

    figure = create_uncertainty_diagnostic_figure(comparison)
    data = cast(tuple[Any, ...], figure.data)

    assert len(data) == 1
    assert data[0].connectgaps is False

    np.testing.assert_allclose(
        data[0].y,
        [0.5, 0.5, np.nan, 0.5, 0.5],
        equal_nan=True,
    )


def test_isolated_finite_values_remain_visible():
    comparison = MeasurementComparison(
        scenario_indices=np.arange(7),
        measured=np.array([10.0, np.nan, 12.0, np.nan, 10.0, 11.0, np.nan]),
        estimated=np.full(7, 9.0),
        sigma=np.full(7, 2.0),
    )

    figure = create_uncertainty_diagnostic_figure(comparison)
    data = cast(tuple[Any, ...], figure.data)

    assert len(data) == 2
    assert data[0].mode == "lines"
    assert data[1].mode == "markers"

    np.testing.assert_array_equal(data[1].x, [0, 2])
    np.testing.assert_allclose(data[1].y, [0.5, 1.5])

    assert list(data[1].customdata[0]) == ["0.5", "10", "9", "2"]
    assert list(data[1].customdata[1]) == ["1.5", "12", "9", "2"]
    assert data[1].hovertemplate == data[0].hovertemplate


def test_single_scenario_remains_visible():
    comparison = MeasurementComparison(
        scenario_indices=np.array([0]),
        measured=np.array([10.0]),
        estimated=np.array([9.0]),
        sigma=np.array([2.0]),
    )

    figure = create_uncertainty_diagnostic_figure(comparison)
    data = cast(tuple[Any, ...], figure.data)

    assert len(data) == 2
    assert data[1].mode == "markers"
    np.testing.assert_array_equal(data[1].x, [0])
    np.testing.assert_allclose(data[1].y, [0.5])


def test_scenario_axis_uses_automatic_tick_spacing():
    comparison = MeasurementComparison(
        scenario_indices=np.arange(3),
        measured=np.full(3, 10.0),
        estimated=np.full(3, 9.0),
        sigma=np.full(3, 2.0),
    )

    figure = create_uncertainty_diagnostic_figure(comparison)

    assert figure.layout.xaxis.tickmode == "auto"
    assert figure.layout.xaxis.dtick is None
    assert figure.layout.xaxis.tickformat == "d"


def test_annual_series_preserves_all_scenarios():
    scenario_count = 35040

    comparison = MeasurementComparison(
        scenario_indices=np.arange(scenario_count),
        measured=np.full(scenario_count, 10.0),
        estimated=np.full(scenario_count, 9.0),
        sigma=np.full(scenario_count, 2.0),
    )

    figure = create_uncertainty_diagnostic_figure(comparison)
    data = cast(tuple[Any, ...], figure.data)

    assert len(data) == 1
    assert data[0].mode == "lines"

    np.testing.assert_array_equal(
        data[0].x,
        comparison.scenario_indices,
    )

    np.testing.assert_allclose(
        data[0].y,
        np.full(scenario_count, 0.5),
    )

    assert len(data[0].customdata) == scenario_count
