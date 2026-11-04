# SPDX-FileCopyrightText: Contributors to the Power Grid Model project <powergridmodel@lfenergy.org>
#
# SPDX-License-Identifier: MPL-2.0

from copy import deepcopy

from dash import Input, Output, State, callback, html
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
from power_grid_model_ds._core.visualizer.parsing_utils import filter_out_appliances
from power_grid_model_ds._core.visualizer.scenario_status import CalculationStatus
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


@callback(
    Output("cytoscape-graph", "elements"),
    Output("electrical-quantity-legend", "children"),
    Input("show-appliances-store", "data"),
    Input("electrical-quantity-dropdown", "value"),
    Input("electrical-scenario-dropdown", "value"),
    State("parsed-elements-store", "data"),
)
def update_appliances(
    show_appliances,
    quantity,
    scenario_index,
    parsed_elements,
):
    """Compose graph elements using appliance visibility and electrical values."""
    if parsed_elements is None:
        raise PreventUpdate

    # Rebuild visible elements from the original parsed topology.
    # Do not reuse elements that may contain previous electrical colours.
    elements = list(parsed_elements.values()) if show_appliances else filter_out_appliances(parsed_elements.values())

    # Reset electrical colouring when no quantity is selected.
    if quantity in (None, "none"):
        return (
            clear_electrical_colors(elements),
            "No electrical quantity selected.",
        )

    # A quantity alone is insufficient: a scenario must also be selected.
    if scenario_index is None:
        return (
            clear_electrical_colors(elements),
            "Select a scenario to display electrical values.",
        )

    # F01 supports two node quantities.
    if quantity not in ("u_pu", "u_angle"):
        raise ValueError(f"Unsupported electrical quantity: {quantity}")

    # Suppress colouring for failed or unknown scenarios when status is available
    scenario_status = server_state.get_scenario_status()

    if scenario_status is not None:
        status = scenario_status.status_for(int(scenario_index))

        if status == CalculationStatus.FAILED:
            return (
                clear_electrical_colors(elements),
                "State-estimation calculation failed for the selected scenario. Electrical values are not displayed.",
            )

        if status == CalculationStatus.UNKNOWN:
            return (
                clear_electrical_colors(elements),
                "Calculation status is unknown for the selected scenario. Electrical values are not displayed.",
            )

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

    if scenario_status is None:
        legend_content.children.append(
            html.P(
                "Calculation status was not provided. "
                "Displayed values are not confirmed as successful "
                "calculation results.",
                className="electrical-legend-note",
            )
        )

    return colored_elements, legend_content
