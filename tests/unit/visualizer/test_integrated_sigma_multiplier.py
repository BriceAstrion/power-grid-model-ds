# SPDX-FileCopyrightText: Contributors to the Power Grid Model project <powergridmodel@lfenergy.org>
#
# SPDX-License-Identifier: MPL-2.0

"""Regression tests for the integrated global sigma multiplier."""

import pytest
from dash.exceptions import PreventUpdate

from power_grid_model_ds._core.visualizer.callbacks.element_selection import (
    store_valid_sigma_multiplier,
)


@pytest.mark.parametrize("value", [0, 0.5, 1, 2, 2.5, 3, 5])
def test_accepts_valid_sigma_multiplier(value):
    """Accept finite non-negative numeric multipliers."""
    result = store_valid_sigma_multiplier(value)

    assert result == float(value)
    assert isinstance(result, float)


@pytest.mark.parametrize(
    "value",
    [
        None,
        "",
        "2",
        True,
        False,
        -1,
        -0.5,
        float("nan"),
        float("inf"),
        float("-inf"),
    ],
)
def test_invalid_sigma_multiplier_preserves_previous_state(value):
    """Prevent invalid input from replacing the last valid value."""
    with pytest.raises(PreventUpdate):
        store_valid_sigma_multiplier(value)


def test_valid_multiplier_after_invalid_input():
    """Accept a corrected value after an invalid input."""
    assert store_valid_sigma_multiplier(3) == 3.0

    with pytest.raises(PreventUpdate):
        store_valid_sigma_multiplier(-1)

    assert store_valid_sigma_multiplier(2.5) == 2.5


def test_zero_multiplier_after_positive_value():
    """Allow zero after a positive multiplier."""
    assert store_valid_sigma_multiplier(3) == 3.0
    assert store_valid_sigma_multiplier(0) == 0.0
