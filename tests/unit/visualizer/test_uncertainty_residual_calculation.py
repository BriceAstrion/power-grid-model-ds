# SPDX-FileCopyrightText: Contributors to the Power Grid Model project <powergridmodel@lfenergy.org>
#
# SPDX-License-Identifier: MPL-2.0

"""Tests for the shared residual-based numerical diagnostic."""

import numpy as np
import pytest

from power_grid_model_ds._core.visualizer.uncertainty_diagnostics import (
    calculate_uncertainty_relative_discrepancy,
)


def test_absolute_discrepancy():
    result = calculate_uncertainty_relative_discrepancy(np.array([-10.0, 10.0, 0.0]), np.array([5.0, 5.0, 5.0]))
    np.testing.assert_allclose(result, [2.0, 2.0, 0.0])


def test_nonfinite_inputs():
    result = calculate_uncertainty_relative_discrepancy(
        np.array([np.nan, np.inf, -np.inf, 1.0, 1.0, 1.0]),
        np.array([1.0, 1.0, 1.0, np.nan, np.inf, -np.inf]),
    )
    assert np.all(np.isnan(result))


def test_missing_sigma():
    result = calculate_uncertainty_relative_discrepancy(np.array([1.0, 2.0]), None)
    assert np.all(np.isnan(result))


@pytest.mark.parametrize("zero", [0.0, -0.0])
def test_zero_sigma(zero):
    result = calculate_uncertainty_relative_discrepancy(np.array([-1.0, 0.0]), np.full(2, zero))
    assert np.isposinf(result[0])
    assert np.isnan(result[1])


def test_negative_sigma():
    with pytest.raises(ValueError, match="Sigma values"):
        calculate_uncertainty_relative_discrepancy(np.array([1.0]), np.array([-1.0]))


def test_mismatched_shapes():
    with pytest.raises(ValueError, match="matching shapes"):
        calculate_uncertainty_relative_discrepancy(np.ones(2), np.ones(1))


def test_empty_arrays():
    result = calculate_uncertainty_relative_discrepancy(np.empty(0), np.empty(0))
    assert result.shape == (0,)


def test_preserves_shape_and_inputs():
    residual = np.array([[-2.0, 4.0], [6.0, -8.0]])
    sigma = np.full((2, 2), 2.0)
    original = residual.copy()
    result = calculate_uncertainty_relative_discrepancy(residual, sigma)
    np.testing.assert_allclose(result, [[1.0, 2.0], [3.0, 4.0]])
    np.testing.assert_array_equal(residual, original)
    np.testing.assert_array_equal(sigma, np.full((2, 2), 2.0))
