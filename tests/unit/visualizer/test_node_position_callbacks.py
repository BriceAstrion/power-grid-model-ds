# SPDX-FileCopyrightText: Contributors to the Power Grid Model project <powergridmodel@lfenergy.org>
#
# SPDX-License-Identifier: MPL-2.0

"""Regression tests for F04 node positioning in the integrated visualiser."""

from copy import deepcopy
from unittest.mock import patch

import numpy as np
from power_grid_model import ComponentType

from power_grid_model_ds._core.visualizer.callbacks.config import update_appliances


def test_appliance_visibility_preserves_node_separation():
    """Showing appliances must not change separated electrical-node positions."""
    parsed_elements = {
        "2": {
            "data": {"id": "2", "group": "node"},
            "position": {"x": 250.0, "y": -250.0},
            "classes": "node",
        },
        "3": {
            "data": {"id": "3", "group": "node"},
            "position": {"x": 250.0, "y": -250.0},
            "classes": "node",
        },
        "10_ghost_node": {
            "data": {
                "id": "10_ghost_node",
                "group": "sym_load_ghost_node",
            },
            "position": {"x": 250.0, "y": -250.0},
            "classes": "appliance-ghost-node",
            "selectable": False,
        },
        "10": {
            "data": {
                "id": "10",
                "group": "sym_load",
                "source": "2",
                "target": "10_ghost_node",
            },
            "classes": "appliance",
        },
    }

    original_elements = deepcopy(parsed_elements)
    initial_state = {"scale": 1.0, "manual_positions": {}}

    hidden, hidden_legend, next_state = update_appliances(
        show_appliances=False,
        component=None,
        quantity="none",
        scenario_number=None,
        node_scale=2.0,
        parsed_elements=parsed_elements,
        current_elements=None,
        position_state=initial_state,
        current_layout={"name": "preset"},
    )

    visible, visible_legend, final_state = update_appliances(
        show_appliances=True,
        component=None,
        quantity="none",
        scenario_number=None,
        node_scale=2.0,
        parsed_elements=parsed_elements,
        current_elements=hidden,
        position_state=next_state,
        current_layout={"name": "preset"},
    )

    hidden_ids = {element["data"]["id"] for element in hidden}
    visible_ids = {element["data"]["id"] for element in visible}

    assert hidden_ids == {"2", "3"}
    assert visible_ids == {"2", "3", "10", "10_ghost_node"}

    def node_positions(elements):
        return {
            element["data"]["id"]: element["position"] for element in elements if element["data"]["group"] == "node"
        }

    hidden_positions = node_positions(hidden)
    visible_positions = node_positions(visible)

    assert hidden_positions == visible_positions
    assert hidden_positions["2"] != hidden_positions["3"]
    assert abs(visible_positions["3"]["x"] - visible_positions["2"]["x"]) == 175.0

    assert hidden_legend == ""
    assert visible_legend == ""
    assert final_state["scale"] == 2.0
    assert final_state["manual_positions"] == {}
    assert parsed_elements == original_elements


def test_node_positions_restore_after_scaling():
    """Scaling 1 to 2 to 1 restores calculated node positions."""
    parsed_elements = {
        "2": {
            "data": {"id": "2", "group": "node"},
            "position": {"x": 250.0, "y": -250.0},
            "classes": "node",
        },
        "3": {
            "data": {"id": "3", "group": "node"},
            "position": {"x": 250.0, "y": -250.0},
            "classes": "node",
        },
    }

    original_elements = deepcopy(parsed_elements)
    state = {"scale": 1.0, "manual_positions": {}}

    initial, _, state = update_appliances(
        show_appliances=False,
        component=None,
        quantity="none",
        scenario_number=None,
        node_scale=1.0,
        parsed_elements=parsed_elements,
        current_elements=None,
        position_state=state,
        current_layout={"name": "preset"},
    )

    enlarged, _, state = update_appliances(
        show_appliances=False,
        component=None,
        quantity="none",
        scenario_number=None,
        node_scale=2.0,
        parsed_elements=parsed_elements,
        current_elements=initial,
        position_state=state,
        current_layout={"name": "preset"},
    )

    restored, _, state = update_appliances(
        show_appliances=False,
        component=None,
        quantity="none",
        scenario_number=None,
        node_scale=1.0,
        parsed_elements=parsed_elements,
        current_elements=enlarged,
        position_state=state,
        current_layout={"name": "preset"},
    )

    def positions(elements):
        return {
            element["data"]["id"]: element["position"] for element in elements if element["data"]["group"] == "node"
        }

    assert positions(enlarged) != positions(initial)
    assert positions(restored) == positions(initial)
    assert state["scale"] == 1.0
    assert state["manual_positions"] == {}
    assert parsed_elements == original_elements


def test_dragged_node_position_preserved_during_scaling():
    """Scaling must preserve manually moved nodes."""
    parsed_elements = {
        "2": {
            "data": {"id": "2", "group": "node"},
            "position": {"x": 250.0, "y": -250.0},
        },
        "3": {
            "data": {"id": "3", "group": "node"},
            "position": {"x": 250.0, "y": -250.0},
        },
    }

    state = {"scale": 1.0, "manual_positions": {}}

    initial, _, state = update_appliances(
        show_appliances=False,
        component=None,
        quantity="none",
        scenario_number=None,
        node_scale=1.0,
        parsed_elements=parsed_elements,
        current_elements=None,
        position_state=state,
        current_layout={"name": "preset"},
    )

    dragged = deepcopy(initial)
    for element in dragged:
        if element["data"]["id"] == "2":
            element["position"] = {"x": 600.0, "y": -500.0}

    enlarged, _, state = update_appliances(
        show_appliances=False,
        component=None,
        quantity="none",
        scenario_number=None,
        node_scale=2.0,
        parsed_elements=parsed_elements,
        current_elements=dragged,
        position_state=state,
        current_layout={"name": "preset"},
    )

    positions = {
        element["data"]["id"]: element["position"] for element in enlarged if element["data"]["group"] == "node"
    }

    assert positions["2"] == {"x": 600.0, "y": -500.0}
    assert positions["3"] == {"x": 337.5, "y": -250.0}
    assert state["manual_positions"]["2"] == {
        "x": 600.0,
        "y": -500.0,
    }
    assert state["scale"] == 2.0


def test_dragged_node_position_preserved_when_toggling_appliances():
    """Showing appliances must preserve manually moved node positions."""
    parsed_elements = {
        "2": {
            "data": {"id": "2", "group": "node"},
            "position": {"x": 250.0, "y": -250.0},
        },
        "3": {
            "data": {"id": "3", "group": "node"},
            "position": {"x": 250.0, "y": -250.0},
        },
        "10_ghost_node": {
            "data": {
                "id": "10_ghost_node",
                "group": "sym_load_ghost_node",
            },
            "position": {"x": 250.0, "y": -250.0},
        },
        "10": {
            "data": {
                "id": "10",
                "group": "sym_load",
                "source": "2",
                "target": "10_ghost_node",
            },
        },
    }

    state = {"scale": 1.0, "manual_positions": {}}

    initial, _, state = update_appliances(
        show_appliances=False,
        component=None,
        quantity="none",
        scenario_number=None,
        node_scale=1.0,
        parsed_elements=parsed_elements,
        current_elements=None,
        position_state=state,
        current_layout={"name": "preset"},
    )

    dragged = deepcopy(initial)
    for element in dragged:
        if element["data"]["id"] == "2":
            element["position"] = {"x": 600.0, "y": -500.0}

    visible, _, state = update_appliances(
        show_appliances=True,
        component=None,
        quantity="none",
        scenario_number=None,
        node_scale=1.0,
        parsed_elements=parsed_elements,
        current_elements=dragged,
        position_state=state,
        current_layout={"name": "preset"},
    )

    positions = {
        element["data"]["id"]: element["position"] for element in visible if element["data"]["group"] == "node"
    }
    visible_ids = {element["data"]["id"] for element in visible}

    assert positions["2"] == {"x": 600.0, "y": -500.0}
    assert state["manual_positions"]["2"] == {
        "x": 600.0,
        "y": -500.0,
    }
    assert {"10", "10_ghost_node"}.issubset(visible_ids)
    assert state["scale"] == 1.0


def test_automatic_layout_positions_preserved_during_scaling():
    """Scaling must preserve positions calculated by Cytoscape."""
    parsed_elements = {
        "2": {
            "data": {"id": "2", "group": "node"},
            "position": {"x": 250.0, "y": -250.0},
        },
        "3": {
            "data": {"id": "3", "group": "node"},
            "position": {"x": 250.0, "y": -250.0},
        },
    }

    current_elements = [
        {
            "data": {"id": "2", "group": "node"},
            "position": {"x": 100.0, "y": 300.0},
        },
        {
            "data": {"id": "3", "group": "node"},
            "position": {"x": 500.0, "y": 300.0},
        },
    ]

    elements, _, position_state = update_appliances(
        show_appliances=False,
        component=None,
        quantity="none",
        scenario_number=None,
        node_scale=2.0,
        parsed_elements=parsed_elements,
        current_elements=current_elements,
        position_state={
            "scale": 1.0,
            "manual_positions": {},
        },
        current_layout={"name": "breadthfirst"},
    )

    positions = {element["data"]["id"]: element["position"] for element in elements}

    assert positions["2"] == {"x": 100.0, "y": 300.0}
    assert positions["3"] == {"x": 500.0, "y": 300.0}
    assert position_state["manual_positions"] == {}
    assert position_state["scale"] == 2.0


def test_electrical_quantity_change_preserves_dragged_node():
    """Changing electrical quantity must preserve manually moved nodes."""
    parsed_elements = {
        "2": {
            "data": {
                "id": "2",
                "group": "node",
                "associated_ids": {"node": [2]},
            },
            "position": {"x": 250.0, "y": -250.0},
        },
        "3": {
            "data": {
                "id": "3",
                "group": "node",
                "associated_ids": {"node": [3]},
            },
            "position": {"x": 250.0, "y": -250.0},
        },
    }

    original_elements = deepcopy(parsed_elements)
    state = {"scale": 1.0, "manual_positions": {}}

    # Initialise the graph without electrical colouring.
    initial, _, state = update_appliances(
        show_appliances=False,
        component=None,
        quantity="none",
        scenario_number=None,
        node_scale=1.0,
        parsed_elements=parsed_elements,
        current_elements=None,
        position_state=state,
        current_layout={"name": "preset"},
    )

    # Simulate dragging node 2 to a new position.
    dragged = deepcopy(initial)
    for element in dragged:
        if element["data"]["id"] == "2":
            element["position"] = {"x": 600.0, "y": -500.0}

    # Provide controlled state-estimation output for scenario 0.
    node_output = np.zeros(
        (1, 2),
        dtype=[
            ("id", "i4"),
            ("u_pu", "f8"),
            ("u_angle", "f8"),
        ],
    )
    node_output["id"] = [[2, 3]]
    node_output["u_pu"] = [[0.98, 1.02]]
    node_output["u_angle"] = [[-0.10, 0.15]]

    output = {ComponentType.node: node_output}

    with patch(
        "power_grid_model_ds._core.visualizer.callbacks.config.server_state.get_output_data",
        return_value=output,
    ):
        updated, legend, state = update_appliances(
            show_appliances=False,
            component="node",
            quantity="u_pu",
            scenario_number=1,
            node_scale=1.0,
            parsed_elements=parsed_elements,
            current_elements=dragged,
            position_state=state,
            current_layout={"name": "preset"},
        )

    # F04: The manually dragged node must retain its position.
    positions = {
        element["data"]["id"]: element["position"] for element in updated if element["data"]["group"] == "node"
    }

    assert positions["2"] == {"x": 600.0, "y": -500.0}
    assert state["manual_positions"]["2"] == {
        "x": 600.0,
        "y": -500.0,
    }
    assert state["scale"] == 1.0

    # F01: Both nodes must display the correct scenario values.
    electrical_values = {
        element["data"]["id"]: element["data"]["electrical_value"]
        for element in updated
        if element["data"]["group"] == "node"
    }

    assert electrical_values == {
        "2": 0.98,
        "3": 1.02,
    }

    # F01: The legend must identify the selected electrical quantity.
    assert legend.children[0].children == ("Voltage magnitude (p.u.) - Scenario 1")

    # F04: Updating the graph must not modify the parsed topology.
    assert parsed_elements == original_elements
