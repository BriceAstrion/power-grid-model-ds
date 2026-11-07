
# SPDX-FileCopyrightText: Contributors to the Power Grid Model project <powergridmodel@lfenergy.org>
#
# SPDX-License-Identifier: MPL-2.0

"""Callbacks for the selected-node diagnostic overview."""

from dash import Input, Output, callback, html

from power_grid_model_ds._core.visualizer import server_state


def find_voltage_sensors_for_node(node_id: int, grid) -> list[int]:
    """Return IDs of symmetric voltage sensors measuring the given node."""
    sensors = grid.sym_voltage_sensor.filter(measured_object=[node_id])
    return [int(sensor_id) for sensor_id in sensors.id]


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

    children = []

    for selected_node in selected_nodes:
        try:
            node_id = int(selected_node["id"])
        except (KeyError, TypeError, ValueError):
            children.append(message("The selected element is not a network node."))
            continue

        if node_id not in grid.node.id:
            children.append(message("The selected element is not a network node."))
            continue

        sensor_ids = find_voltage_sensors_for_node(node_id, grid)

        if sensor_ids:
            sensor_names = ", ".join(f"Sensor {sensor_id}" for sensor_id in sensor_ids)
            sensor_text = f"Voltage sensors: {sensor_names}"
        else:
            sensor_text = "No associated symmetric voltage sensors"

        children.append(
            html.Div(
                [
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
                    ),
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
                    ),
                ],
                style={
                    "paddingBottom": "10px",
                    "marginBottom": "10px",
                    "borderBottom": "1px solid #e2e8f0",
                },
            )
        )

    return children
