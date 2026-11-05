# SPDX-FileCopyrightText: Contributors to the Power Grid Model project <powergridmodel@lfenergy.org>
#
# SPDX-License-Identifier: MPL-2.0

from copy import deepcopy
from math import isclose

from dash import Input, Output, State, callback
from dash.exceptions import PreventUpdate
from power_grid_model import ComponentType

from power_grid_model_ds._core.visualizer import server_state
from power_grid_model_ds._core.visualizer.electrical_quantity_legend import build_electrical_legend
from power_grid_model_ds._core.visualizer.electrical_quantity_styling import (
    apply_electrical_colors,
    clear_electrical_colors,
)
from power_grid_model_ds._core.visualizer.electrical_quantity_utils import extract_scenario_values
from power_grid_model_ds._core.visualizer.layout.cytoscape_styling import BRANCH_WIDTH, NODE_SIZE
from power_grid_model_ds._core.visualizer.layout.header_config import LayoutOptions
from power_grid_model_ds._core.visualizer.layout.layout_config import layout_with_config
from power_grid_model_ds._core.visualizer.layout.node_overlap import separate_coincident_nodes
from power_grid_model_ds._core.visualizer.parsing_utils import filter_out_appliances
from power_grid_model_ds._core.visualizer.styling_classification import StyleClass
from power_grid_model_ds._core.visualizer.typing import STYLESHEET


@callback(
    Output("stylesheet-store", "data", allow_duplicate=True),
    Output("cytoscape-graph", "stylesheet", allow_duplicate=True),
    Input("node-scale-input", "value"),
    Input("edge-scale-input", "value"),
    State("stylesheet-store", "data"),
    State("cytoscape-graph", "stylesheet"),
    prevent_initial_call=True,
)
def scale_elements(
    node_scale: float,
    edge_scale: float,
    stored_stylesheet: STYLESHEET,
    current_stylesheet: STYLESHEET,
) -> tuple[STYLESHEET, STYLESHEET]:
    """Scale graph elements while preserving temporary display highlights."""
    if stored_stylesheet is None or current_stylesheet is None:
        raise PreventUpdate

    scaling_rules = [
        (f".{StyleClass.BRANCH.value}", {"width": BRANCH_WIDTH * edge_scale}),
        (
            f".{StyleClass.NODE.value}",
            {
                "height": NODE_SIZE * node_scale,
                "width": NODE_SIZE * node_scale,
            },
        ),
        (
            f".{StyleClass.APPLIANCE_GHOST_NODE.value}",
            {
                "height": NODE_SIZE * node_scale * 0.25,
                "width": NODE_SIZE * node_scale * 0.25,
            },
        ),
        (f".{StyleClass.GENERATING_APPLIANCE.value}", {"width": BRANCH_WIDTH * edge_scale * 0.5}),
        (f".{StyleClass.LOADING_APPLIANCE.value}", {"width": BRANCH_WIDTH * edge_scale * 0.5}),
    ]

    def apply_scaling(stylesheet: STYLESHEET) -> STYLESHEET:
        updated = deepcopy(stylesheet)
        for selector, new_style in scaling_rules:
            updated.append({"selector": selector, "style": deepcopy(new_style)})
        return updated

    return apply_scaling(stored_stylesheet), apply_scaling(current_stylesheet)


@callback(
    Output("cytoscape-graph", "layout"),
    Input("dropdown-update-layout", "value"),
    State("source-available-store", "data"),
    prevent_initial_call=True,
)
def update_layout(layout: str, source_available: bool):
    """Callback to update the layout of the graph."""
    if not layout:
        raise PreventUpdate

    layout_config = layout_with_config(
        LayoutOptions(layout),
        source_available,
    )
    layout_config.update({"animate": True})
    return layout_config


@callback(
    Output("stylesheet-store", "data", allow_duplicate=True),
    Output("cytoscape-graph", "stylesheet", allow_duplicate=True),
    Input("show-arrows", "value"),
    State("stylesheet-store", "data"),
    State("cytoscape-graph", "stylesheet"),
    prevent_initial_call=True,
)
def update_arrows(show_arrows, stored_stylesheet, current_stylesheet):
    """Update arrow visibility without persisting temporary highlights."""
    if stored_stylesheet is None or current_stylesheet is None:
        raise PreventUpdate

    branch_selector = f".{StyleClass.BRANCH.value}"
    arrow_shape = "triangle" if show_arrows else "none"

    def apply_arrow_setting(stylesheet):
        updated = deepcopy(stylesheet)
        for rule in updated:
            if rule["selector"] == branch_selector and "target-arrow-shape" in rule["style"]:
                rule["style"]["target-arrow-shape"] = arrow_shape
        return updated

    return apply_arrow_setting(stored_stylesheet), apply_arrow_setting(current_stylesheet)


@callback(
    Output("show-appliances-store", "data"),
    Input("show-appliances", "value"),
)
def update_appliance_visibility(show_appliances):
    """Store appliance visibility independently of electrical colouring."""
    return bool(show_appliances)


def _node_positions(elements):
    """Extract electrical-node positions using Cytoscape element IDs."""
    return {
        str(element["data"]["id"]): dict(element["position"])
        for element in (elements or [])
        if element.get("data", {}).get("group") == "node"
        and element.get("position") is not None
    }


def _positions_equal(left, right):
    """Compare coordinates with tolerance for Cytoscape floating-point values."""
    return all(
        isclose(left[axis], right[axis], abs_tol=1e-6)
        for axis in ("x", "y")
    )


def _apply_preset_positions(
    parsed_elements,
    display_elements,
    current_positions,
    previous_scale,
    manual_positions,
):
    """Preserve dragged nodes while recalculating untouched node positions."""
    previous_elements = separate_coincident_nodes(
        parsed_elements,
        node_scale=previous_scale,
    )

    for previous_element in previous_elements.values():
        if previous_element.get("data", {}).get("group") != "node":
            continue

        node_id = str(previous_element["data"]["id"])
        current_position = current_positions.get(node_id)
        expected_position = previous_element.get("position")

        if (
            current_position is not None
            and expected_position is not None
            and not _positions_equal(current_position, expected_position)
        ):
            manual_positions[node_id] = dict(current_position)

    for element in display_elements.values():
        if element.get("data", {}).get("group") != "node":
            continue

        node_id = str(element["data"]["id"])
        if node_id in manual_positions:
            element["position"] = dict(manual_positions[node_id])

    return manual_positions


def _apply_automatic_positions(display_elements, current_positions):
    """Preserve positions generated by the selected Cytoscape layout."""
    for element in display_elements.values():
        if element.get("data", {}).get("group") != "node":
            continue

        node_id = str(element["data"]["id"])
        if node_id in current_positions:
            element["position"] = dict(current_positions[node_id])



@callback(
    Output("cytoscape-graph", "elements"),
    Output("electrical-quantity-legend", "children"),
    Output("node-position-state-store", "data"),
    Input("show-appliances-store", "data"),
    Input("electrical-quantity-dropdown", "value"),
    Input("electrical-scenario-dropdown", "value"),
    Input("node-scale-input", "value"),
    State("parsed-elements-store", "data"),
    State("cytoscape-graph", "elements"),
    State("node-position-state-store", "data"),
    State("cytoscape-graph", "layout"),
)
def update_appliances(  # noqa: PLR0913, PLR0917
    show_appliances,
    quantity,
    scenario_index,
    node_scale=1.0,
    parsed_elements=None,
    current_elements=None,
    position_state=None,
    current_layout=None,
):
    """Compose graph positions, appliance visibility, and electrical values."""
    if parsed_elements is None or node_scale is None or node_scale <= 0:
        raise PreventUpdate

    display_elements = separate_coincident_nodes(
        parsed_elements,
        node_scale=node_scale,
    )

    previous_scale = position_state.get("scale", 1.0) if position_state else 1.0
    manual_positions = dict(position_state.get("manual_positions", {})) if position_state else {}
    current_positions = _node_positions(current_elements)

    if current_layout and current_layout.get("name") == LayoutOptions.PRESET.value:
        manual_positions = _apply_preset_positions(
            parsed_elements,
            display_elements,
            current_positions,
            previous_scale,
            manual_positions,
        )
    else:
        _apply_automatic_positions(display_elements, current_positions)
        manual_positions = {}

    new_position_state = {
        "scale": node_scale,
        "manual_positions": manual_positions,
    }

    elements = (
        list(display_elements.values())
        if show_appliances
        else filter_out_appliances(display_elements.values())
    )

    # Reset electrical colouring and hide the legend when no quantity is selected.
    if quantity in (None, "none"):
        return (
            clear_electrical_colors(elements),
            "",
            new_position_state,
        )

    # A quantity alone is insufficient: a scenario must also be selected.
    if scenario_index is None:
        return (
            clear_electrical_colors(elements),
            "Select a scenario to display electrical values.",
            new_position_state,
        )

    # F01 supports two node quantities.
    if quantity not in ("u_pu", "u_angle"):
        raise ValueError(f"Unsupported electrical quantity: {quantity}")

    values = extract_scenario_values(
        server_state.get_output_data(),
        ComponentType.node,
        quantity,
        scenario_index,
    )

    colored_elements, legend = apply_electrical_colors(
        elements,
        ComponentType.node.value,
        values,
    )

    legend_content = build_electrical_legend(
        scenario_index=scenario_index,
        minimum=legend["minimum"],
        maximum=legend["maximum"],
        missing_count=legend["missing_count"],
        quantity=quantity,
    )

    return colored_elements, legend_content, new_position_state
