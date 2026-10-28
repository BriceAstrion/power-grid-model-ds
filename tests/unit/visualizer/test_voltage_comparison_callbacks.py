# SPDX-FileCopyrightText: Contributors to the Power Grid Model project <powergridmodel@lfenergy.org>
#
# SPDX-License-Identifier: MPL-2.0

"""Tests for symmetric voltage comparison callbacks."""

import numpy as np
import pytest

from power_grid_model import ComponentType, DatasetType, initialize_array

from power_grid_model_ds import Grid
from power_grid_model_ds._core.visualizer import server_state
from power_grid_model_ds._core.visualizer.callbacks.voltage_comparison import (
    find_voltage_sensors_for_selection,
    update_voltage_comparison,
    update_voltage_sensor_options,
)


@pytest.fixture
def voltage_grid():
    grid = Grid.empty()

    nodes = grid.node.__class__.empty(2)
    nodes.id = np.array([1001, 2001], dtype=np.int32)
    grid.append(nodes)

    sensors = grid.sym_voltage_sensor.__class__.empty(2)
    sensors.id = np.array([12001, 12002], dtype=np.int32)
    sensors.measured_object = np.array([1001, 2001], dtype=np.int32)
    grid.append(sensors)

    return grid


@pytest.fixture
def voltage_datasets():
    updates = initialize_array(
        DatasetType.update,
        ComponentType.sym_voltage_sensor,
        (2, 2),
    )
    updates["id"][:] = [[12001, 12002], [12001, 12002]]
    updates["u_measured"][:] = [[230.0, 235.0], [231.0, 236.0]]
    updates["u_sigma"][:] = [[1.0, 2.0], [1.5, 2.5]]

    outputs = initialize_array(
        DatasetType.sym_output,
        ComponentType.node,
        (2, 2),
    )
    outputs["id"][:] = [[1001, 2001], [1001, 2001]]
    outputs["u"][:] = [[229.5, 234.5], [230.5, 235.5]]

    return (
        {ComponentType.sym_voltage_sensor: updates},
        {ComponentType.node: outputs},
    )


def test_finds_sensor_for_selected_node(voltage_grid):
    options = find_voltage_sensors_for_selection(
        [{"id": "1001"}],
        voltage_grid,
    )

    assert options == [{"label": "Sensor 12001", "value": 12001}]


def test_rejects_multiple_selected_nodes(voltage_grid):
    options = find_voltage_sensors_for_selection(
        [{"id": "1001"}, {"id": "2001"}],
        voltage_grid,
    )

    assert options == []


def test_rejects_unknown_node(voltage_grid):
    options = find_voltage_sensors_for_selection(
        [{"id": "9999"}],
        voltage_grid,
    )

    assert options == []


def test_sensor_options_callback(voltage_grid, monkeypatch):
    monkeypatch.setattr(server_state, "get_grid", lambda: voltage_grid)

    options, selected = update_voltage_sensor_options(
        [{"id": "2001"}]
    )

    assert options == [{"label": "Sensor 12002", "value": 12002}]
    assert selected == 12002


def test_comparison_callback_updates_sigma_bands(
    voltage_grid,
    voltage_datasets,
    monkeypatch,
):
    updates, outputs = voltage_datasets

    monkeypatch.setattr(server_state, "get_grid", lambda: voltage_grid)
    monkeypatch.setattr(server_state, "get_update_data", lambda: updates)
    monkeypatch.setattr(server_state, "get_output_data", lambda: outputs)

    figure_3sigma, style, message = update_voltage_comparison(12001, 3.0)
    figure_2sigma, _, _ = update_voltage_comparison(12001, 2.0)

    assert style == {"display": "block"}
    assert message == ""

    np.testing.assert_allclose(
        figure_3sigma.data[0].y,
        [227.0, 226.5],
    )
    np.testing.assert_allclose(
        figure_2sigma.data[0].y,
        [228.0, 228.0],
    )

    np.testing.assert_array_equal(
        figure_3sigma.data[3].y,
        figure_2sigma.data[3].y,
    )


def test_comparison_callback_handles_missing_data(
    voltage_grid,
    monkeypatch,
):
    monkeypatch.setattr(server_state, "get_grid", lambda: voltage_grid)
    monkeypatch.setattr(server_state, "get_update_data", lambda: None)
    monkeypatch.setattr(server_state, "get_output_data", lambda: None)

    figure, style, message = update_voltage_comparison(12001, 3.0)

    assert style == {"display": "none"}
    assert len(figure.data) == 0
    assert "unavailable" in message.lower()


def test_comparison_callback_handles_no_sensor():
    figure, style, message = update_voltage_comparison(None, 3.0)

    assert style == {"display": "none"}
    assert len(figure.data) == 0
    assert "Select one node" in message
