# SPDX-FileCopyrightText: Contributors to the Power Grid Model project <powergridmodel@lfenergy.org>
#
# SPDX-License-Identifier: MPL-2.0

"""Tests for the selected-node diagnostic overview."""

from unittest.mock import MagicMock, patch

from dash.development.base_component import Component
from power_grid_model import ComponentType, initialize_array

from power_grid_model_ds._core.model.grids.base import Grid
from power_grid_model_ds._core.visualizer.callbacks.diagnostic_overview import (
    find_voltage_sensors_for_node,
    update_diagnostic_overview,
)
from power_grid_model_ds.arrays import SymVoltageSensorArray


def _visible_text(component):
    """Collect visible text from nested Dash components."""
    if isinstance(component, (list, tuple)):
        return " ".join(_visible_text(child) for child in component)

    if isinstance(component, str):
        return component

    if isinstance(component, (int, float)):
        return str(component)

    if isinstance(component, Component):
        return _visible_text(getattr(component, "children", None))

    return ""


def _run_overview(grid, selected_nodes):
    """Run the diagnostics callback with a controlled grid."""
    with patch(
        "power_grid_model_ds._core.visualizer.callbacks.diagnostic_overview.server_state.get_grid",
        return_value=grid,
    ):
        return update_diagnostic_overview(selected_nodes)


def _example_grid():
    """Create a small network with three nodes."""
    return Grid.from_txt("S1 2 12", "2 3 23")


def test_overview_without_selection():
    """Prompt for selection without duplicating calculation status."""
    result = _run_overview(_example_grid(), None)
    text = _visible_text(result)

    assert "Select a network node to view diagnostics." in text
    assert "Calculation status" not in text
    assert "Succeeded:" not in text
    assert "Failed:" not in text


def test_overview_with_empty_selection():
    """An empty selection must display the selection prompt."""
    result = _run_overview(_example_grid(), [])

    assert "Select a network node to view diagnostics." in _visible_text(result)


def test_overview_with_selected_node():
    """A valid node must display its ID and sensor information."""
    result = _run_overview(_example_grid(), [{"id": "1"}])
    text = _visible_text(result)

    assert "Node 1" in text
    assert "No associated symmetric voltage sensors" in text
    assert "Calculation status" not in text


def test_overview_with_multiple_nodes():
    """Each selected network node must have its own diagnostic entry."""
    result = _run_overview(
        _example_grid(),
        [{"id": "1"}, {"id": "2"}],
    )
    text = _visible_text(result)

    assert text.count("Node") == 2
    assert "Node 1" in text
    assert "Node 2" in text
    assert "Select one network node at a time" not in text
    assert "Calculation status" not in text


def test_overview_with_three_selected_nodes():
    """Three selected nodes must produce three diagnostic entries."""
    result = _run_overview(
        _example_grid(),
        [{"id": "1"}, {"id": "2"}, {"id": "3"}],
    )
    text = _visible_text(result)

    assert text.count("Node") == 3

    for node_id in (1, 2, 3):
        assert f"Node {node_id}" in text


def test_overview_with_invalid_node():
    """An invalid node ID must not be presented as a network node."""
    result = _run_overview(
        _example_grid(),
        [{"id": "invalid"}],
    )

    assert "not a network node" in _visible_text(result)


def test_overview_with_nonexistent_node():
    """An ID absent from the grid must be rejected."""
    result = _run_overview(
        _example_grid(),
        [{"id": "999"}],
    )
    text = _visible_text(result)

    assert "not a network node" in text
    assert "Node 999" not in text


def test_overview_with_missing_node_id():
    """A selected element without an ID must be handled."""
    result = _run_overview(
        _example_grid(),
        [{}],
    )

    assert "not a network node" in _visible_text(result)


def test_overview_with_mixed_valid_and_invalid_nodes():
    """Invalid selections must not hide valid node diagnostics."""
    result = _run_overview(
        _example_grid(),
        [
            {"id": "1"},
            {"id": "invalid"},
            {"id": "2"},
        ],
    )
    text = _visible_text(result)

    assert "Node 1" in text
    assert "Node 2" in text
    assert "not a network node" in text
    assert text.count("Node") == 2


def test_overview_with_sensors_associated_with_each_node():
    """Each selected node displays only its associated sensors."""
    grid = _example_grid()
    data = initialize_array("input", ComponentType.sym_voltage_sensor, 2)

    data["id"] = [101, 202]
    data["measured_object"] = [1, 2]
    grid.sym_voltage_sensor = SymVoltageSensorArray(data=data)

    result = _run_overview(grid, [{"id": "1"}, {"id": "2"}])

    assert len(result) == 2

    first_node = _visible_text(result[0])
    second_node = _visible_text(result[1])

    assert "Node 1" in first_node
    assert "Sensor 101" in first_node
    assert "Sensor 202" not in first_node

    assert "Node 2" in second_node
    assert "Sensor 202" in second_node
    assert "Sensor 101" not in second_node


def test_overview_with_node_without_sensors():
    """Report when the selected node has no associated sensors."""
    grid = _example_grid()

    result = _run_overview(grid, [{"id": "2"}])

    text = _visible_text(result)

    assert "Node 2" in text
    assert "No associated symmetric voltage sensors" in text


def test_selected_node_displays_associated_voltage_sensors():
    """Show symmetric voltage sensors associated with a selected node."""

    grid = MagicMock()
    grid.node.id = [1, 2]
    grid.sym_voltage_sensor.filter.return_value.id = [101, 102]

    with patch(
        "power_grid_model_ds._core.visualizer.callbacks.diagnostic_overview.server_state.get_grid",
        return_value=grid,
    ):
        result = update_diagnostic_overview([{"id": 1}])

    content = _visible_text(result)

    assert "Node 1" in content
    assert "Sensor 101" in content
    assert "Sensor 102" in content
    grid.sym_voltage_sensor.filter.assert_called_once_with(measured_object=[1])


def test_real_grid_voltage_sensor_association():
    """Associate real symmetric voltage sensor records with their nodes."""
    grid = Grid.from_txt("S1 2 12", "2 3 23")
    data = initialize_array("input", ComponentType.sym_voltage_sensor, 2)

    data["id"] = [101, 202]
    data["measured_object"] = [1, 2]

    grid.sym_voltage_sensor = SymVoltageSensorArray(data=data)

    assert find_voltage_sensors_for_node(1, grid) == [101]
    assert find_voltage_sensors_for_node(2, grid) == [202]
    assert find_voltage_sensors_for_node(3, grid) == []
