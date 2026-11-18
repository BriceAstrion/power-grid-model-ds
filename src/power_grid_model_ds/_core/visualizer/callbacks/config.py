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
from power_grid_model_ds._core.visualizer.electrical_quantity_utils import (
    extract_scenario_values,
    get_available_scalar_attributes,
    get_scenario_count,
)
from power_grid_model_ds._core.visualizer.layout.cytoscape_styling import BRANCH_WIDTH, NODE_SIZE
from power_grid_model_ds._core.visualizer.layout.header_config import LayoutOptions
from power_grid_model_ds._core.visualizer.layout.layout_config import layout_with_config
from power_grid_model_ds._core.visualizer.layout.node_overlap import separate_coincident_nodes
from power_grid_model_ds._core.visualizer.layout.transformer_rendering import prepare_transformer_rendering
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
        if element.get("data", {}).get("group") == "node" and element.get("position") is not None
    }


def _positions_equal(left, right):
    """Compare coordinates with tolerance for Cytoscape floating-point values."""
    return all(isclose(left[axis], right[axis], abs_tol=1e-6) for axis in ("x", "y"))


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
    Output("electrical-quantity-dropdown", "options"),
    Output("electrical-quantity-dropdown", "value"),
    Output("electrical-quantity-dropdown", "disabled"),
    Input("electrical-component-dropdown", "value"),
    State("electrical-available-attributes", "data"),
)
def update_electrical_attributes(component, available_attributes):
    """Offer only scalar output attributes of the selected component."""
    attributes = (available_attributes or {}).get(component, [])
    options = [{"label": name, "value": name} for name in attributes]
    return options, None, not bool(options)


def _scenario_validation_message(value, count):
    """Return a warning for invalid user input, or None when valid."""
    if not count:
        return None
    if value is None or value == "":
        return f"Enter a whole-number scenario between 1 and {count}."
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return f"Enter a whole-number scenario between 1 and {count}."
    if not float(value).is_integer():
        return f"Scenario must be a whole number between 1 and {count}."
    if not 1 <= value <= count:
        return f"Scenario {int(value)} does not exist. Available scenarios: 1-{count}."
    return None


@callback(
    Output("electrical-scenario-warning", "style"),
    Output("electrical-scenario-warning-text", "children"),
    Input("electrical-scenario-input", "value"),
    State("electrical-scenario-count", "data"),
)
def update_scenario_warning(value, scenario_count):
    """Show a floating warning only when a nonempty scenario is invalid."""
    if value is None or value == "":
        return {"display": "none"}, ""
    message = _scenario_validation_message(value, scenario_count)
    return ({"display": "none"} if message is None else {"display": "block"}), message or ""


# pylint: disable-next=too-many-arguments,too-many-positional-arguments
def _prepare_appliance_elements(  # noqa: PLR0913, PLR0917
    show_appliances, node_scale, parsed_elements, current_elements, position_state, current_layout
):
    """Position nodes and apply appliance visibility without losing dragged positions."""
    display_elements = separate_coincident_nodes(parsed_elements, node_scale=node_scale)
    previous_scale = position_state.get("scale", 1.0) if position_state else 1.0
    manual_positions = dict(position_state.get("manual_positions", {})) if position_state else {}
    current_positions = _node_positions(current_elements)

    if current_layout and current_layout.get("name") == LayoutOptions.PRESET.value:
        manual_positions = _apply_preset_positions(
            parsed_elements, display_elements, current_positions, previous_scale, manual_positions
        )
    else:
        _apply_automatic_positions(display_elements, current_positions)
        manual_positions = {}

    new_position_state = {"scale": node_scale, "manual_positions": manual_positions}
    elements = list(display_elements.values()) if show_appliances else filter_out_appliances(display_elements.values())
    return elements, new_position_state


def _electrical_display(elements, component, quantity, scenario_number):
    """Apply scalar heatmap colours and return the corresponding legend."""
    if not component or not quantity or quantity == "none":
        return clear_electrical_colors(elements), ""

    if scenario_number is None:
        return clear_electrical_colors(elements), "Select a scenario to display electrical values."

    output_data = server_state.get_output_data()
    available = get_available_scalar_attributes(output_data)
    if quantity not in available.get(component, []):
        return clear_electrical_colors(elements), "The selected attribute is unavailable."

    scenario_count = get_scenario_count(output_data)
    if _scenario_validation_message(scenario_number, scenario_count) is not None:
        return clear_electrical_colors(elements), f"Enter a scenario between 1 and {scenario_count}."

    values = extract_scenario_values(output_data, ComponentType(component), quantity, int(scenario_number) - 1)
    colored_elements, summary = apply_electrical_colors(elements, component, values)
    legend_content = build_electrical_legend(
        scenario_index=int(scenario_number) - 1,
        summary=summary,
        quantity=quantity,
        component_group=component,
    )
    return colored_elements, legend_content


@callback(
    Output("cytoscape-graph", "elements"),
    Output("electrical-quantity-legend", "children"),
    Output("node-position-state-store", "data"),
    Input("show-appliances-store", "data"),
    Input("electrical-component-dropdown", "value"),
    Input("electrical-quantity-dropdown", "value"),
    Input("electrical-scenario-input", "value"),
    Input("node-scale-input", "value"),
    State("parsed-elements-store", "data"),
    State("cytoscape-graph", "elements"),
    State("node-position-state-store", "data"),
    State("cytoscape-graph", "layout"),
)
def update_appliances(  # pylint: disable=too-many-arguments,too-many-positional-arguments  # noqa: PLR0913, PLR0917
    show_appliances,
    component,
    quantity,
    scenario_number=None,
    node_scale=1.0,
    parsed_elements=None,
    current_elements=None,
    position_state=None,
    current_layout=None,
):
    """Compose integrated node positioning with the generic scalar heatmap."""
    if parsed_elements is None or node_scale is None or node_scale <= 0:
        raise PreventUpdate

    elements, new_position_state = _prepare_appliance_elements(
        show_appliances, node_scale, parsed_elements, current_elements, position_state, current_layout
    )
    elements, legend_content = _electrical_display(elements, component, quantity, scenario_number)
    if current_layout and current_layout.get("name") == LayoutOptions.PRESET.value:
        elements = prepare_transformer_rendering(elements)
    return elements, legend_content, new_position_state
