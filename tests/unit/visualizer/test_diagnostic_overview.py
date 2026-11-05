from unittest.mock import MagicMock, patch

from dash.development.base_component import Component
from power_grid_model import ComponentType, initialize_array

from power_grid_model_ds._core.model.grids.base import Grid
from power_grid_model_ds._core.visualizer.app import get_app_layout
from power_grid_model_ds._core.visualizer.callbacks.diagnostic_overview import (
    find_voltage_sensors_for_node,
    update_diagnostic_overview,
)
from power_grid_model_ds.arrays import SymVoltageSensorArray


def collect_text(component):
    if isinstance(component, str):
        return component
    if isinstance(component, (list, tuple)):
        return " ".join(collect_text(child) for child in component)
    if isinstance(component, Component):
        return collect_text(component.children)
    return ""


def test_no_selection():
    assert "Select a network node" in collect_text(update_diagnostic_overview(None))


def test_invalid_selection():
    with patch(
        "power_grid_model_ds._core.visualizer.callbacks.diagnostic_overview.server_state.get_grid",
        return_value=Grid.empty(),
    ):
        result = update_diagnostic_overview([{"id": "invalid"}])

    assert "not a network node" in collect_text(result)


def test_nonexistent_node():
    with patch(
        "power_grid_model_ds._core.visualizer.callbacks.diagnostic_overview.server_state.get_grid",
        return_value=Grid.empty(),
    ):
        result = update_diagnostic_overview([{"id": 999999}])

    assert "not a network node" in collect_text(result)


def test_multiple_selected_nodes():
    grid = Grid.from_txt("1 2", "2 3")

    with patch(
        "power_grid_model_ds._core.visualizer.callbacks.diagnostic_overview.server_state.get_grid",
        return_value=grid,
    ):
        result = update_diagnostic_overview([{"id": 1}, {"id": 2}])

    content = collect_text(result)
    assert "Node 1" in content
    assert "Node 2" in content
    assert content.count("No associated symmetric voltage sensors") == 2


def test_app_layout_contains_diagnostics_panel():
    layout = get_app_layout(Grid.empty())

    panels = [child for child in layout.children if getattr(child, "id", None) == "diagnostic-overview"]

    assert len(panels) == 1
    assert "Selected-node diagnostics" in collect_text(panels[0])


def test_empty_selection():
    result = update_diagnostic_overview([])
    assert "Select a network node" in collect_text(result)


def test_missing_node_id():
    with patch(
        "power_grid_model_ds._core.visualizer.callbacks.diagnostic_overview.server_state.get_grid",
        return_value=Grid.empty(),
    ):
        result = update_diagnostic_overview([{}])

    assert "not a network node" in collect_text(result)


def test_multiple_valid_and_invalid_nodes():
    grid = Grid.from_txt("1 2", "2 3")

    with patch(
        "power_grid_model_ds._core.visualizer.callbacks.diagnostic_overview.server_state.get_grid",
        return_value=grid,
    ):
        result = update_diagnostic_overview([{"id": 1}, {"id": "invalid"}, {"id": 2}])

    assert len(result) == 3
    assert "Node 1" in collect_text(result[0])
    assert "not a network node" in collect_text(result[1])
    assert "Node 2" in collect_text(result[2])


def test_voltage_sensor_lookup_filters_by_node():
    grid = MagicMock()
    grid.sym_voltage_sensor.filter.return_value.id = [101, 102]

    result = find_voltage_sensors_for_node(1, grid)

    assert result == [101, 102]
    grid.sym_voltage_sensor.filter.assert_called_once_with(measured_object=[1])


def test_selected_node_displays_associated_voltage_sensors():
    grid = MagicMock()
    grid.node.id = [1, 2]
    grid.sym_voltage_sensor.filter.return_value.id = [101, 102]

    with patch(
        "power_grid_model_ds._core.visualizer.callbacks.diagnostic_overview.server_state.get_grid",
        return_value=grid,
    ):
        result = update_diagnostic_overview([{"id": 1}])

    content = collect_text(result)

    assert "Node 1" in content
    assert "Sensor 101" in content
    assert "Sensor 102" in content
    grid.sym_voltage_sensor.filter.assert_called_once_with(measured_object=[1])


def test_real_grid_voltage_sensor_association():
    """Associate actual symmetric voltage sensor records with nodes."""
    grid = Grid.from_txt("S1 2 12", "2 3 23")
    data = initialize_array("input", ComponentType.sym_voltage_sensor, 2)

    data["id"] = [101, 202]
    data["measured_object"] = [1, 2]
    grid.sym_voltage_sensor = SymVoltageSensorArray(data=data)

    assert find_voltage_sensors_for_node(1, grid) == [101]
    assert find_voltage_sensors_for_node(2, grid) == [202]
    assert find_voltage_sensors_for_node(3, grid) == []
