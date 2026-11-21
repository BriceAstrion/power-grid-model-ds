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

    assert figure.layout.title.text == "Uncertainty-relative discrepancy"
    assert figure.layout.xaxis.title.text == "Scenario Index"


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
        "Infinite discrepancy",
        "Unavailable",
        "Unavailable",
    ]
