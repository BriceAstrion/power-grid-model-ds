# SPDX-FileCopyrightText: Contributors to the Power Grid Model project <powergridmodel@lfenergy.org>
#
# SPDX-License-Identifier: MPL-2.0

"""Regression tests for resetting electrical quantity colouring."""

from copy import deepcopy

from power_grid_model_ds._core.visualizer.callbacks.config import update_appliances
from power_grid_model_ds._core.visualizer.electrical_quantity_styling import (
    ELECTRICAL_HEATMAP_CLASS,
    apply_electrical_colors,
    clear_electrical_colors,
)


def _node(node_id: int, *, substation: bool = False) -> dict:
    """Create a minimal Cytoscape node."""
    classes = "node substation_node" if substation else "node"

    return {
        "data": {
            "id": str(node_id),
            "group": "node",
            "associated_ids": {"node": [node_id]},
        },
        "classes": classes,
    }


def _line(line_id: int) -> dict:
    """Create a minimal Cytoscape branch."""
    return {
        "data": {
            "id": str(line_id),
            "group": "line",
            "associated_ids": {"line": [line_id]},
        },
        "classes": "branch",
    }


def _parsed_elements() -> dict:
    """Create a graph containing a previously coloured node."""
    node = _node(1)
    node["data"]["electrical_color"] = "#DE2D26"
    node["data"]["electrical_value"] = 1.05
    return {"node-1": node}


def _assert_default_node(element: dict) -> None:
    """Check that the node uses its original component styling."""
    assert "electrical_color" not in element["data"]
    assert "electrical_value" not in element["data"]
    assert ELECTRICAL_HEATMAP_CLASS not in element["classes"].split()
    assert "node" in element["classes"].split()


def test_clearing_quantity_restores_default_colours():
    """Clearing Quantity restores the default appearance and legend."""
    elements, legend, _ = update_appliances(
        show_appliances=False,
        component=None,
        quantity=None,
        scenario_number=0,
        parsed_elements=_parsed_elements(),
    )

    assert len(elements) == 1
    _assert_default_node(elements[0])
    assert legend == ""


def test_clearing_scenario_restores_default_colours():
    """Clearing Scenario removes the active electrical visualisation."""
    elements, legend, _ = update_appliances(
        show_appliances=False,
        component="node",
        quantity="u_pu",
        scenario_number=None,
        parsed_elements=_parsed_elements(),
    )

    assert len(elements) == 1
    _assert_default_node(elements[0])
    assert legend == "Select a scenario to display electrical values."


def test_initial_empty_selection():
    """Both dropdowns can start without an active selection."""
    elements, legend, _ = update_appliances(
        show_appliances=False,
        component=None,
        quantity=None,
        scenario_number=None,
        parsed_elements=_parsed_elements(),
    )

    assert len(elements) == 1
    _assert_default_node(elements[0])
    assert legend == ""


def test_reset_removes_electrical_value():
    """Reset removes the result value and restores the node colour."""
    parsed_elements = _parsed_elements()

    elements, legend, _ = update_appliances(
        show_appliances=False,
        component="node",
        quantity="u_pu",
        scenario_number=None,
        parsed_elements=parsed_elements,
    )

    assert len(elements) == 1
    _assert_default_node(elements[0])
    assert legend == "Select a scenario to display electrical values."

    # The source graph must not be modified.
    assert parsed_elements["node-1"]["data"]["electrical_color"] == "#DE2D26"
    assert parsed_elements["node-1"]["data"]["electrical_value"] == 1.05


def test_reset_restores_default_node_color():
    node = _node(1)
    node["data"]["electrical_color"] = "#DE2D26"
    node["data"]["electrical_value"] = 1.05

    original = deepcopy(node)
    updated = clear_electrical_colors([node])

    _assert_default_node(updated[0])
    assert node == original


def test_reset_restores_substation_color():
    node = _node(16, substation=True)

    colored, _ = apply_electrical_colors([node], "node", {16: 1.05})

    updated = clear_electrical_colors(colored)

    assert updated == [node]
    assert "substation_node" in updated[0]["classes"].split()


def test_reset_does_not_modify_branch():
    branch = _line(18)

    updated = clear_electrical_colors([branch])

    assert updated == [branch]
    assert "electrical_color" not in updated[0]["data"]


def test_reset_preserves_topology():
    """Reset must not change element IDs, classes, or associations."""
    elements = [_node(1), _line(18)]

    elements[0]["data"]["electrical_color"] = "#DE2D26"
    elements[0]["data"]["electrical_value"] = 1.05

    updated = clear_electrical_colors(elements)

    assert len(updated) == len(elements)

    for original, restored in zip(elements, updated, strict=True):
        assert restored["data"]["id"] == original["data"]["id"]
        assert restored["data"]["associated_ids"] == original["data"]["associated_ids"]
        assert restored["classes"] == original["classes"]


def test_reset_previously_colored_branch():
    """Regression test for F01-DEF-01."""
    branch = _line(18)
    branch["data"]["source"] = "1"
    branch["data"]["target"] = "2"

    colored, _ = apply_electrical_colors([branch], "line", {18: 80.0})

    assert ELECTRICAL_HEATMAP_CLASS in colored[0]["classes"].split()
    assert "electrical_color" in colored[0]["data"]

    restored = clear_electrical_colors(colored)

    assert restored == [branch]


def test_switching_component_removes_previous_heatmap():
    """Only the currently selected component retains electrical styling."""
    original = [_node(1), _line(18)]

    colored, _ = apply_electrical_colors(original, "line", {18: 80.0})

    switched, _ = apply_electrical_colors(colored, "node", {1: 1.05})

    assert ELECTRICAL_HEATMAP_CLASS in switched[0]["classes"].split()
    assert switched[1] == original[1]


def test_repeated_coloring_does_not_duplicate_class():
    """Repeated scenario changes must not duplicate styling classes."""
    original = [_line(18)]

    colored, _ = apply_electrical_colors(original, "line", {18: 80.0})

    recolored, _ = apply_electrical_colors(colored, "line", {18: 90.0})

    assert recolored[0]["classes"].split().count(ELECTRICAL_HEATMAP_CLASS) == 1

    assert recolored[0]["data"]["electrical_value"] == 90.0
    assert clear_electrical_colors(recolored) == original
