# SPDX-FileCopyrightText: Contributors to the Power Grid Model project <powergridmodel@lfenergy.org>
#
# SPDX-License-Identifier: MPL-2.0
"""Integration-level tests using actual PGM-DS Grid and PGM batch arrays.

No mock grid, monkeypatch or synthetic SimpleNamespace is used.
The batch output represents deterministic fixtures, not a solved power flow.
"""

import numpy as np
import pytest
from numpy.testing import assert_allclose, assert_array_equal
from power_grid_model import ComponentType, DatasetType, MeasuredTerminalType, initialize_array

from power_grid_model_ds import Grid
from power_grid_model_ds._core.visualizer.measurement_comparison import (
    get_associated_sensor_data,
    get_sensor_comparison,
    get_sigma_bounds,
)


def _grid_with_voltage_sensor():
    grid = Grid.empty()
    nodes = grid.node.__class__.empty(1)
    nodes.id = np.array([1001], dtype=np.int32)
    grid.append(nodes)
    sensors = grid.sym_voltage_sensor.__class__.empty(1)
    sensors.id = np.array([12001], dtype=np.int32)
    sensors.measured_object = np.array([1001], dtype=np.int32)
    sensors.u_measured = np.array([230.0])
    sensors.u_sigma = np.array([2.0])
    grid.append(sensors)
    return grid


def _grid_with_source_power_sensor():
    grid = Grid.empty()
    nodes = grid.node.__class__.empty(1)
    nodes.id = np.array([1001], dtype=np.int32)
    grid.append(nodes)
    sources = grid.source.__class__.empty(1)
    sources.id = np.array([2001], dtype=np.int32)
    sources.node = np.array([1001], dtype=np.int32)
    grid.append(sources)
    sensors = grid.sym_power_sensor.__class__.empty(1)
    sensors.id = np.array([12002], dtype=np.int32)
    sensors.measured_object = np.array([2001], dtype=np.int32)
    sensors.measured_terminal_type = np.array([MeasuredTerminalType.source.value])
    sensors.p_measured = np.array([10.0])
    sensors.q_measured = np.array([4.0])
    sensors.p_sigma = np.array([0.5])
    sensors.q_sigma = np.array([0.25])
    grid.append(sensors)
    return grid


def test_real_grid_voltage_mapping_and_comparison():
    grid = _grid_with_voltage_sensor()
    assert get_associated_sensor_data(grid, ComponentType.sym_voltage_sensor, 12001, "u_measured") == (
        ComponentType.node,
        "u",
        1001,
    )
    output = initialize_array(DatasetType.sym_output, ComponentType.node, (3, 1))
    output["id"][:, 0] = 1001
    output["u"][:, 0] = [229.0, 231.0, 228.0]
    updates = initialize_array(DatasetType.update, ComponentType.sym_voltage_sensor, (3, 1))
    updates["id"][:, 0] = 12001
    updates["u_measured"][1, 0] = 235.0
    comparison = get_sensor_comparison(
        grid,
        ComponentType.sym_voltage_sensor,
        12001,
        "u_measured",
        {ComponentType.sym_voltage_sensor: updates},
        {ComponentType.node: output},
    )
    assert_array_equal(comparison.scenario_indices, [0, 1, 2])
    assert_allclose(comparison.measured, [230.0, 235.0, 230.0])
    assert_allclose(comparison.estimated, [229.0, 231.0, 228.0])
    assert_allclose(comparison.sigma, [2.0, 2.0, 2.0])
    lower, upper = get_sigma_bounds(comparison, 2.0)
    assert_allclose(lower, [226.0, 231.0, 226.0])
    assert_allclose(upper, [234.0, 239.0, 234.0])


@pytest.mark.parametrize(
    ("measured_attr", "output_attr", "base", "sigma"),
    [
        ("p_measured", "p", 10.0, 0.5),
        ("q_measured", "q", 4.0, 0.25),
    ],
)
def test_real_grid_source_power_mapping_and_comparison(measured_attr, output_attr, base, sigma):
    grid = _grid_with_source_power_sensor()
    assert get_associated_sensor_data(grid, ComponentType.sym_power_sensor, 12002, measured_attr) == (
        ComponentType.source,
        output_attr,
        2001,
    )
    output = initialize_array(DatasetType.sym_output, ComponentType.source, (3, 1))
    output["id"][:, 0] = 2001
    output[output_attr][:, 0] = [base - 1, base + 1, base - 2]
    comparison = get_sensor_comparison(
        grid, ComponentType.sym_power_sensor, 12002, measured_attr, None, {ComponentType.source: output}
    )
    assert_array_equal(comparison.scenario_indices, [0, 1, 2])
    assert_allclose(comparison.measured, [base] * 3)
    assert_allclose(comparison.estimated, [base - 1, base + 1, base - 2])
    assert_allclose(comparison.sigma, [sigma] * 3)
    lower, upper = get_sigma_bounds(comparison, 2.0)
    assert_allclose(lower, [base - 2 * sigma] * 3)
    assert_allclose(upper, [base + 2 * sigma] * 3)


def test_real_grid_missing_source_sensor_target_rejected():
    grid = _grid_with_source_power_sensor()
    # A sensor referring to a removed source must not silently match another component.
    grid.source = grid.source.__class__.empty(0)
    with pytest.raises(ValueError, match="was not found"):
        get_associated_sensor_data(grid, ComponentType.sym_power_sensor, 12002, "p_measured")
