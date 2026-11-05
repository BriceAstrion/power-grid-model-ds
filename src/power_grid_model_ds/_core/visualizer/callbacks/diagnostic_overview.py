# SPDX-FileCopyrightText: Contributors to the Power Grid Model project <powergridmodel@lfenergy.org>
#
# SPDX-License-Identifier: MPL-2.0

"""Callbacks for the selected-node diagnostic overview."""

from dash import Input, Output, callback, html

from power_grid_model_ds._core.visualizer import server_state
from power_grid_model_ds._core.visualizer.callbacks.voltage_comparison import (
    find_voltage_sensors_for_selection,
)


@callback(
    Output("diagnostic-overview-content", "children"),
    Input("cytoscape-graph", "selectedNodeData"),
)
def update_diagnostic_overview(selected_nodes):
    """Show compact diagnostics for the selected network node."""
    grid = server_state.get_grid()

    def message(text):
        return html.Div(
            [
                html.I(
                    className="bi bi-info-circle",
                    **{"aria-hidden": "true"},
                    style={"color": "#64748b", "fontSize": "14px"},
                ),
                html.Span(text),
            ],
            style={
                "display": "flex",
                "alignItems": "flex-start",
                "gap": "8px",
                "fontSize": "13px",
                "color": "#64748b",
            },
        )

    if not selected_nodes:
        return [message("Select a network node to view diagnostics.")]

    if len(selected_nodes) != 1:
        return [message("Select one network node at a time.")]

    selected_node = selected_nodes[0]

    try:
        node_id = int(selected_node["id"])
    except (KeyError, TypeError, ValueError):
        node_id = None

    if node_id is None or node_id not in grid.node.id:
        return [message("The selected element is not a network node.")]

    sensors = find_voltage_sensors_for_selection(selected_nodes, grid)

    children = [
        html.Div(
            [
                html.I(
                    className="bi bi-hash",
                    **{"aria-hidden": "true"},
                    style={"color": "#64748b"},
                ),
                html.Span("Node"),
                html.Span(
                    str(node_id),
                    style={
                        "backgroundColor": "#e9ecef",
                        "borderRadius": "6px",
                        "padding": "2px 9px",
                        "fontWeight": "600",
                        "color": "#212529",
                    },
                ),
            ],
            style={
                "display": "flex",
                "alignItems": "center",
                "gap": "8px",
                "fontSize": "13px",
            },
        )
    ]

    if sensors:
        sensor_names = ", ".join(sensor["label"] for sensor in sensors)
        sensor_text = f"Voltage sensors: {sensor_names}"
    else:
        sensor_text = "No associated symmetric voltage sensors"

    children.append(
        html.Div(
            [
                html.I(
                    className="bi bi-broadcast",
                    **{"aria-hidden": "true"},
                    style={"color": "#64748b"},
                ),
                html.Span(sensor_text),
            ],
            style={
                "display": "flex",
                "alignItems": "flex-start",
                "gap": "8px",
                "fontSize": "13px",
                "marginTop": "10px",
            },
        )
    )

    return children
