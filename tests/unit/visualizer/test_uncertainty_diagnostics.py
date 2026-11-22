# SPDX-FileCopyrightText: Contributors to the Power Grid Model project <powergridmodel@lfenergy.org>
#
# SPDX-License-Identifier: MPL-2.0

"""Tests for uncertainty-relative measurement diagnostics."""

import numpy as np
import pytest

from power_grid_model_ds._core.visualizer.measurement_comparison import (
    MeasurementComparison,
    VoltageComparison,
)
from power_grid_model_ds._core.visualizer.uncertainty_diagnostics import get_uncertainty_relative_discrepancy


@pytest.fixture
def comparison():
    return MeasurementComparison(
        scenario_indices=np.array([0, 1, 2]),
        measured=np.array([10.0, 10.0, 10.0]),
        estimated=np.array([9.0, 11.0, 8.0]),
        sigma=np.array([2.0, 2.0, 2.0]),
    )


def test_calculates_discrepancy_relative_to_sigma(comparison):
    result = get_uncertainty_relative_discrepancy(comparison)

    np.testing.assert_allclose(result, [0.5, 0.5, 1.0])


def test_preserves_missing_values(comparison):
    comparison = MeasurementComparison(
        scenario_indices=np.array([0, 1, 2]),
        measured=np.array([10.0, np.nan, 10.0]),
        estimated=np.array([9.0, 9.0, 8.0]),
        sigma=np.array([2.0, 2.0, np.nan]),
    )

    result = get_uncertainty_relative_discrepancy(comparison)

    np.testing.assert_allclose(
        result,
        [0.5, np.nan, np.nan],
        equal_nan=True,
    )


def test_returns_nan_without_sigma(comparison):
    comparison = MeasurementComparison(
        scenario_indices=comparison.scenario_indices,
        measured=comparison.measured,
        estimated=comparison.estimated,
        sigma=None,
    )

    result = get_uncertainty_relative_discrepancy(comparison)

    assert np.all(np.isnan(result))


@pytest.mark.parametrize("zero", [0.0, -0.0])
def test_handles_zero_sigma(zero):
    comparison = MeasurementComparison(
        scenario_indices=np.array([0, 1]),
        measured=np.array([10.0, 10.0]),
        estimated=np.array([9.0, 10.0]),
        sigma=np.full(2, zero),
    )

    result = get_uncertainty_relative_discrepancy(comparison)

    assert np.isposinf(result[0])
    assert np.isnan(result[1])


def test_rejects_negative_sigma():
    comparison = MeasurementComparison(
        scenario_indices=np.array([0]),
        measured=np.array([10.0]),
        estimated=np.array([9.0]),
        sigma=np.array([-1.0]),
    )

    with pytest.raises(ValueError, match="Sigma values"):
        get_uncertainty_relative_discrepancy(comparison)


def test_supports_voltage_comparison():
    comparison = VoltageComparison(
        scenario_indices=np.array([0, 1]),
        measured=np.array([230.0, 235.0]),
        estimated=np.array([229.0, 231.0]),
        sigma=np.array([2.0, 2.0]),
    )

    result = get_uncertainty_relative_discrepancy(comparison)

    np.testing.assert_allclose(result, [0.5, 2.0])


def test_rejects_mismatched_comparison_shapes():
    comparison = MeasurementComparison(
        scenario_indices=np.array([0, 1]),
        measured=np.array([10.0, 10.0]),
        estimated=np.array([9.0]),
        sigma=np.array([2.0, 2.0]),
    )
    with pytest.raises(ValueError, match="matching shapes"):
        get_uncertainty_relative_discrepancy(comparison)


def test_nonfinite_measurement_and_estimate():
    comparison = MeasurementComparison(
        scenario_indices=np.arange(4),
        measured=np.array([np.inf, 10.0, np.inf, 10.0]),
        estimated=np.array([9.0, -np.inf, np.inf, 8.0]),
        sigma=np.full(4, 2.0),
    )
    np.testing.assert_allclose(
        get_uncertainty_relative_discrepancy(comparison), [np.nan, np.nan, np.nan, 1.0], equal_nan=True
    )
