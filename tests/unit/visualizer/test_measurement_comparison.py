# SPDX-FileCopyrightText: Contributors to the Power Grid Model project <powergridmodel@lfenergy.org>
#
# SPDX-License-Identifier: MPL-2.0

"""Tests for measurement comparison data preparation."""

import numpy as np
import pytest
from power_grid_model import ComponentType, DatasetType, initialize_array

from power_grid_model_ds import Grid
from power_grid_model_ds._core.visualizer.measurement_comparison import (
    align_voltage_series,
    calculate_sigma_bands,
    prepare_voltage_comparison,
)
from power_grid_model_ds._core.visualizer.scenario_status import ScenarioStatus


def test_aligns_matching_scenarios():
    result = align_voltage_series(
        sensor_id=12001,
        node_id=1001,
        measurement_scenarios=np.array([0, 2, 3]),
        measured=np.array([230.0, 231.0, 229.0]),
        sigma=np.array([1.0, 1.5, 1.0]),
        estimate_scenarios=np.array([3, 0, 1, 2]),
        estimated=np.array([228.5, 229.5, 230.0, 230.5]),
    )

    np.testing.assert_array_equal(result.scenarios, [0, 2, 3])
    np.testing.assert_allclose(result.measured, [230.0, 231.0, 229.0])
    np.testing.assert_allclose(result.estimated, [229.5, 230.5, 228.5])
    np.testing.assert_allclose(result.sigma, [1.0, 1.5, 1.0])
    assert result.sensor_id == 12001
    assert result.node_id == 1001


def test_rejects_no_common_scenarios():
    with pytest.raises(ValueError, match="No matching"):
        align_voltage_series(
            sensor_id=12001,
            node_id=1001,
            measurement_scenarios=np.array([0, 1]),
            measured=np.array([230.0, 231.0]),
            sigma=np.array([1.0, 1.0]),
            estimate_scenarios=np.array([2, 3]),
            estimated=np.array([230.0, 231.0]),
        )


def test_rejects_duplicate_scenarios():
    with pytest.raises(ValueError, match="Duplicate"):
        align_voltage_series(
            sensor_id=12001,
            node_id=1001,
            measurement_scenarios=np.array([0, 0]),
            measured=np.array([230.0, 231.0]),
            sigma=np.array([1.0, 1.0]),
            estimate_scenarios=np.array([0, 1]),
            estimated=np.array([230.0, 231.0]),
        )


def test_rejects_invalid_sigma():
    with pytest.raises(ValueError, match="Sigma values must be positive"):
        align_voltage_series(
            sensor_id=12001,
            node_id=1001,
            measurement_scenarios=np.array([0, 1]),
            measured=np.array([230.0, 231.0]),
            sigma=np.array([1.0, 0.0]),
            estimate_scenarios=np.array([0, 1]),
            estimated=np.array([230.0, 231.0]),
        )


def test_rejects_non_finite_values():
    with pytest.raises(ValueError, match="non-finite"):
        align_voltage_series(
            sensor_id=12001,
            node_id=1001,
            measurement_scenarios=np.array([0, 1]),
            measured=np.array([230.0, np.nan]),
            sigma=np.array([1.0, 1.0]),
            estimate_scenarios=np.array([0, 1]),
            estimated=np.array([230.0, 231.0]),
        )


def test_prepares_voltage_comparison_from_pgm_datasets():
    """Match a voltage sensor to its node and align batch scenarios."""
    grid = Grid.empty()

    nodes = grid.node.__class__.empty(1)
    nodes.id = np.array([1001], dtype=np.int32)
    grid.append(nodes)

    sensors = grid.sym_voltage_sensor.__class__.empty(1)
    sensors.id = np.array([12001], dtype=np.int32)
    sensors.measured_object = np.array([1001], dtype=np.int32)
    grid.append(sensors)

    sensor_updates = initialize_array(
        DatasetType.update,
        ComponentType.sym_voltage_sensor,
        (3, 1),
    )
    sensor_updates["id"][:, 0] = 12001
    sensor_updates["u_measured"][:, 0] = [230.0, 231.0, 229.0]
    sensor_updates["u_sigma"][:, 0] = [1.0, 1.5, 1.0]

    node_outputs = initialize_array(
        DatasetType.sym_output,
        ComponentType.node,
        (3, 1),
    )
    node_outputs["id"][:, 0] = 1001
    node_outputs["u"][:, 0] = [229.5, 230.5, 228.5]

    result = prepare_voltage_comparison(
        grid=grid,
        update_data={ComponentType.sym_voltage_sensor: sensor_updates},
        output_data={ComponentType.node: node_outputs},
        sensor_id=12001,
    )

    assert result.sensor_id == 12001
    assert result.node_id == 1001

    np.testing.assert_array_equal(result.scenarios, [0, 1, 2])
    np.testing.assert_allclose(result.measured, [230.0, 231.0, 229.0])
    np.testing.assert_allclose(result.estimated, [229.5, 230.5, 228.5])
    np.testing.assert_allclose(result.sigma, [1.0, 1.5, 1.0])


def test_calculates_default_three_sigma_bands():
    comparison = align_voltage_series(
        sensor_id=12001,
        node_id=1001,
        measurement_scenarios=np.array([0, 1]),
        measured=np.array([230.0, 231.0]),
        sigma=np.array([1.0, 2.0]),
        estimate_scenarios=np.array([0, 1]),
        estimated=np.array([229.5, 230.5]),
    )

    lower, upper = calculate_sigma_bands(comparison)

    np.testing.assert_allclose(lower, [227.0, 225.0])
    np.testing.assert_allclose(upper, [233.0, 237.0])


def test_calculates_bands_with_custom_multiplier():
    comparison = align_voltage_series(
        sensor_id=12001,
        node_id=1001,
        measurement_scenarios=np.array([0]),
        measured=np.array([230.0]),
        sigma=np.array([1.5]),
        estimate_scenarios=np.array([0]),
        estimated=np.array([229.0]),
    )

    lower, upper = calculate_sigma_bands(comparison, multiplier=2.0)

    np.testing.assert_allclose(lower, [227.0])
    np.testing.assert_allclose(upper, [233.0])


@pytest.mark.parametrize("multiplier", [-1.0, np.nan, np.inf])
def test_rejects_invalid_sigma_multiplier(multiplier):
    comparison = align_voltage_series(
        sensor_id=12001,
        node_id=1001,
        measurement_scenarios=np.array([0]),
        measured=np.array([230.0]),
        sigma=np.array([1.0]),
        estimate_scenarios=np.array([0]),
        estimated=np.array([229.5]),
    )

    with pytest.raises(ValueError, match="Sigma multiplier"):
        calculate_sigma_bands(comparison, multiplier=multiplier)


def test_prepares_partial_updates_with_failed_scenario():
    """Keep successful estimates when another scenario has failed."""
    grid = Grid.empty()

    nodes = grid.node.__class__.empty(1)
    nodes.id = np.array([1001], dtype=np.int32)
    grid.append(nodes)

    sensors = grid.sym_voltage_sensor.__class__.empty(1)
    sensors.id = np.array([12001], dtype=np.int32)
    sensors.measured_object = np.array([1001], dtype=np.int32)
    sensors.u_measured = np.array([10489.37])
    sensors.u_sigma = np.array([1.0])
    grid.append(sensors)

    # Scenario 0 retains the original measurements.
    # Scenario 1 has infinite sigma and fails state estimation.
    sensor_updates = initialize_array(
        DatasetType.update,
        ComponentType.sym_voltage_sensor,
        (2, 1),
    )
    sensor_updates["id"][:, 0] = 12001
    sensor_updates["u_sigma"][1, 0] = np.inf

    # The solver retains both batch rows, including the failed scenario.
    node_outputs = initialize_array(
        DatasetType.sym_output,
        ComponentType.node,
        (2, 1),
    )

    # Scenario 0 succeeded.
    node_outputs["id"][0, 0] = 1001
    node_outputs["u"][0, 0] = 10488.27

    # Scenario 1 failed and has no valid node output.
    node_outputs["id"][1, 0] = -1
    node_outputs["u"][1, 0] = 0.0

    status = ScenarioStatus(
        succeeded_scenarios=frozenset({0}),
        failed_scenarios=frozenset({1}),
    )

    result = prepare_voltage_comparison(
        grid=grid,
        update_data={
            ComponentType.sym_voltage_sensor: sensor_updates
        },
        output_data={
            ComponentType.node: node_outputs
        },
        sensor_id=12001,
        scenario_status=status,
    )

    np.testing.assert_array_equal(result.scenarios, [0, 1])
    np.testing.assert_allclose(
        result.measured,
        [10489.37, 10489.37],
    )
    np.testing.assert_allclose(
        result.estimated,
        [10488.27, np.nan],
        equal_nan=True,
    )
    np.testing.assert_allclose(
        result.sigma,
        [1.0, np.nan],
        equal_nan=True,
    )


def test_prepares_comparison_when_first_scenario_fails():
    """Map an estimate to scenario 1 when scenario 0 fails."""
    grid = Grid.empty()

    nodes = grid.node.__class__.empty(1)
    nodes.id = np.array([1001], dtype=np.int32)
    grid.append(nodes)

    sensors = grid.sym_voltage_sensor.__class__.empty(1)
    sensors.id = np.array([12001], dtype=np.int32)
    sensors.measured_object = np.array([1001], dtype=np.int32)
    sensors.u_measured = np.array([230.0])
    sensors.u_sigma = np.array([1.0])
    grid.append(sensors)

    sensor_updates = initialize_array(
        DatasetType.update,
        ComponentType.sym_voltage_sensor,
        (2, 1),
    )
    sensor_updates["id"][:, 0] = 12001
    sensor_updates["u_sigma"][0, 0] = np.inf

    node_outputs = initialize_array(
        DatasetType.sym_output,
        ComponentType.node,
        (2, 1),
    )

    # Scenario 0 failed: no valid output for node 1001.
    node_outputs["id"][0, 0] = -1

    # Scenario 1 succeeded.
    node_outputs["id"][1, 0] = 1001
    node_outputs["u"][1, 0] = 229.5

    status = ScenarioStatus(
        succeeded_scenarios=frozenset({1}),
        failed_scenarios=frozenset({0}),
    )

    result = prepare_voltage_comparison(
        grid=grid,
        update_data={
            ComponentType.sym_voltage_sensor: sensor_updates
        },
        output_data={
            ComponentType.node: node_outputs
        },
        sensor_id=12001,
        scenario_status=status,
    )

    np.testing.assert_array_equal(result.scenarios, [0, 1])

    np.testing.assert_allclose(
        result.measured,
        [230.0, 230.0],
    )

    np.testing.assert_allclose(
        result.estimated,
        [np.nan, 229.5],
        equal_nan=True,
    )

    np.testing.assert_allclose(
        result.sigma,
        [np.nan, 1.0],
        equal_nan=True,
    )


def test_preserves_valid_sigma_when_state_estimation_fails():
    """Keep valid measurement uncertainty when estimation fails."""
    grid = Grid.empty()

    nodes = grid.node.__class__.empty(1)
    nodes.id = np.array([1001], dtype=np.int32)
    grid.append(nodes)

    sensors = grid.sym_voltage_sensor.__class__.empty(1)
    sensors.id = np.array([12001], dtype=np.int32)
    sensors.measured_object = np.array([1001], dtype=np.int32)
    sensors.u_measured = np.array([230.0])
    sensors.u_sigma = np.array([1.0])
    grid.append(sensors)

    updates = initialize_array(
        DatasetType.update,
        ComponentType.sym_voltage_sensor,
        (2, 1),
    )
    updates["id"][:, 0] = 12001
    updates["u_measured"][:, 0] = [230.0, 231.0]
    updates["u_sigma"][:, 0] = [1.0, 1.5]

    outputs = initialize_array(
        DatasetType.sym_output,
        ComponentType.node,
        (2, 1),
    )
    outputs["id"][0, 0] = 1001
    outputs["u"][0, 0] = 229.5

    # Scenario 1 has no valid node output.
    outputs["id"][1, 0] = -1

    status = ScenarioStatus(
        succeeded_scenarios=frozenset({0}),
        failed_scenarios=frozenset({1}),
    )

    comparison = prepare_voltage_comparison(
        grid=grid,
        update_data={ComponentType.sym_voltage_sensor: updates},
        output_data={ComponentType.node: outputs},
        sensor_id=12001,
        scenario_status=status,
    )

    np.testing.assert_allclose(
        comparison.measured,
        [230.0, 231.0],
    )
    np.testing.assert_allclose(
        comparison.estimated,
        [229.5, np.nan],
        equal_nan=True,
    )
    np.testing.assert_allclose(
        comparison.sigma,
        [1.0, 1.5],
    )

    lower, upper = calculate_sigma_bands(comparison, multiplier=3.0)

    np.testing.assert_allclose(lower, [227.0, 226.5])
    np.testing.assert_allclose(upper, [233.0, 235.5])


def test_preserves_available_estimate_with_unknown_scenario_status():
    """Keep an available estimate without claiming calculation success."""
    grid = Grid.empty()

    nodes = grid.node.__class__.empty(1)
    nodes.id = np.array([1001], dtype=np.int32)
    grid.append(nodes)

    sensors = grid.sym_voltage_sensor.__class__.empty(1)
    sensors.id = np.array([12001], dtype=np.int32)
    sensors.measured_object = np.array([1001], dtype=np.int32)
    sensors.u_measured = np.array([230.0])
    sensors.u_sigma = np.array([1.0])
    grid.append(sensors)

    updates = initialize_array(
        DatasetType.update,
        ComponentType.sym_voltage_sensor,
        (2, 1),
    )
    updates["id"][:, 0] = 12001
    updates["u_measured"][:, 0] = [230.0, 231.0]
    updates["u_sigma"][:, 0] = [1.0, 1.0]

    outputs = initialize_array(
        DatasetType.sym_output,
        ComponentType.node,
        (2, 1),
    )
    outputs["id"][:, 0] = 1001
    outputs["u"][:, 0] = [229.5, 230.5]

    status = ScenarioStatus(
        succeeded_scenarios=frozenset({0}),
        failed_scenarios=frozenset(),
    )

    comparison = prepare_voltage_comparison(
        grid=grid,
        update_data={ComponentType.sym_voltage_sensor: updates},
        output_data={ComponentType.node: outputs},
        sensor_id=12001,
        scenario_status=status,
    )

    np.testing.assert_array_equal(comparison.scenarios, [0, 1])
    np.testing.assert_allclose(
        comparison.estimated,
        [229.5, 230.5],
    )
