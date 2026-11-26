# SPDX-FileCopyrightText: Contributors to the Power Grid Model project <powergridmodel@lfenergy.org>
#
# SPDX-License-Identifier: MPL-2.0

from power_grid_model_ds._core.model.grids.base import Grid
from power_grid_model_ds._core.visualizer import server_state
from power_grid_model_ds._core.visualizer.callbacks.element_selection import display_selected_elements
from power_grid_model_ds.arrays import NodeArray


def _records(panel):
    return panel.children[0].data


def _selection_records(node_data, edge_data):
    result = display_selected_elements(node_data, edge_data)
    return {result[index].children: _records(result[index + 1]) for index in range(0, len(result), 2)}


def test_multiple_selected_nodes_preserve_component_ids():
    """Resolve visual node IDs to the original PGM IDs and attributes."""
    grid = Grid.empty()
    grid.node = NodeArray.empty(2)
    grid.node.id = [101, 205]
    grid.node.u_rated = [10000.0, 20000.0]
    server_state.set_app_state(grid)

    selected_nodes = [
        {
            "id": "visual-node-101",
            "group": "node",
            "associated_ids": {"node": [101]},
        },
        {
            "id": "visual-node-205",
            "group": "node",
            "associated_ids": {"node": [205]},
        },
    ]

    records = _selection_records(selected_nodes, [])

    assert set(records) == {"node"}
    assert {record["id"] for record in records["node"]} == {101, 205}
    assert {record["u_rated"] for record in records["node"]} == {
        10000.0,
        20000.0,
    }


def test_selected_line_preserves_component_details():
    grid = Grid.from_txt("1 2 19")
    server_state.set_app_state(grid)

    selected_edges = [
        {
            "id": "visual-edge-19",
            "group": "line",
            "associated_ids": {"line": [19]},
        }
    ]
    records = _selection_records([], selected_edges)

    assert set(records) == {"line"}
    assert len(records["line"]) == 1
    assert records["line"][0]["id"] == 19
    assert records["line"][0]["from_node"] == 1
    assert records["line"][0]["to_node"] == 2


def test_associated_component_types_are_displayed():
    grid = Grid.from_txt("1 2 19")
    server_state.set_app_state(grid)

    selected_nodes = [{"associated_ids": {"node": [1], "line": [19]}}]

    records = _selection_records(selected_nodes, [])

    assert set(records) == {"node", "line"}
    assert [record["id"] for record in records["node"]] == [1]
    assert [record["id"] for record in records["line"]] == [19]


def test_duplicate_component_ids_are_not_displayed_twice():
    grid = Grid.from_txt("1 2 19")
    server_state.set_app_state(grid)

    selected_nodes = [{"associated_ids": {"node": [1]}}]
    selected_edges = [{"associated_ids": {"node": [1], "line": [19]}}]

    records = _selection_records(selected_nodes, selected_edges)

    assert [record["id"] for record in records["node"]] == [1]
    assert [record["id"] for record in records["line"]] == [19]


def test_component_details_update_when_selection_changes():
    grid = Grid.from_txt("1 2 19")
    server_state.set_app_state(grid)

    first = _selection_records([{"associated_ids": {"node": [1]}}], [])
    second = _selection_records([{"associated_ids": {"node": [2]}}], [])

    assert [record["id"] for record in first["node"]] == [1]
    assert [record["id"] for record in second["node"]] == [2]
    assert len(second["node"]) == 1
