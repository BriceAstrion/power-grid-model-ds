# SPDX-FileCopyrightText: Contributors to the Power Grid Model project <powergridmodel@lfenergy.org>
#
# SPDX-License-Identifier: MPL-2.0

"""Tests for scenario-specific measurement uncertainty extraction."""

from types import SimpleNamespace

import numpy as np
import pytest
from power_grid_model import ComponentType, DatasetType, initialize_array

from power_grid_model_ds._core.visualizer.electrical_uncertainty import (
    extract_uncertainty_relative_values,
    get_effective_sigma,
)

GROUP = ComponentType.sym_voltage_sensor


@pytest.fixture
def grid():
    return SimpleNamespace(
        sym_voltage_sensor=SimpleNamespace(id=np.array([11, 12, 13]), u_sigma=np.array([2.0, 4.0, 5.0]))
    )


@pytest.fixture
def updates():
    data = initialize_array(DatasetType.update, GROUP, (2, 2))
    data["id"] = [[12, 11], [11, 12]]
    data["u_sigma"] = [[8.0, np.nan], [0.0, 10.0]]
    return {GROUP: data}


def test_base_sigma(grid):
    assert get_effective_sigma(grid, None, GROUP, "u_sigma", 0) == {11: 2.0, 12: 4.0, 13: 5.0}


def test_reordered_updates_and_fallback(grid, updates):
    assert get_effective_sigma(grid, updates, GROUP, "u_sigma", 0) == {11: 2.0, 12: 8.0, 13: 5.0}
    assert get_effective_sigma(grid, updates, GROUP, "u_sigma", 1) == {11: 0.0, 12: 10.0, 13: 5.0}
    np.testing.assert_array_equal(grid.sym_voltage_sensor.u_sigma, [2.0, 4.0, 5.0])


def test_duplicate_update(grid, updates):
    updates[GROUP]["id"][0] = [11, 11]
    with pytest.raises(ValueError, match="Duplicate sensor update"):
        get_effective_sigma(grid, updates, GROUP, "u_sigma", 0)


@pytest.mark.parametrize("scenario", [-1, 2])
def test_invalid_scenario(grid, updates, scenario):
    with pytest.raises(IndexError):
        get_effective_sigma(grid, updates, GROUP, "u_sigma", scenario)


def test_ratios_by_id(grid, updates):
    output = initialize_array(DatasetType.sym_output, GROUP, (2, 3))
    output["id"] = [[13, 11, 12], [12, 13, 11]]
    output["u_residual"] = [[-10.0, 6.0, 16.0], [-20.0, 5.0, 1.0]]
    assert extract_uncertainty_relative_values(grid, updates, {GROUP: output}, (GROUP, "u_residual"), 0) == {
        13: 2.0,
        11: 3.0,
        12: 2.0,
    }
    assert extract_uncertainty_relative_values(grid, updates, {GROUP: output}, (GROUP, "u_residual"), 1) == {
        12: 2.0,
        13: 1.0,
    }


@pytest.mark.parametrize("sigma", [-1.0, 0.0, np.nan, np.inf])
def test_invalid_sigma_is_local(grid, sigma):
    grid.sym_voltage_sensor.u_sigma[0] = sigma
    output = initialize_array(DatasetType.sym_output, GROUP, (1, 3))
    output["id"] = [[11, 12, 13]]
    output["u_residual"] = [[10.0, -8.0, np.nan]]
    assert extract_uncertainty_relative_values(grid, None, {GROUP: output}, (GROUP, "u_residual"), 0) == {12: 2.0}
