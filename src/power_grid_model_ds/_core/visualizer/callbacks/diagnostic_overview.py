# SPDX-FileCopyrightText: Contributors to the Power Grid Model project <powergridmodel@lfenergy.org>
#
# SPDX-License-Identifier: MPL-2.0

"""Selected-node diagnostics for the F07 visualiser."""

from dash import Input, Output, callback, html

from power_grid_model_ds._core.visualizer import server_state


def find_voltage_sensors_for_node(node_id, grid):
    """Return symmetric voltage sensor IDs associated with a node."""
    sensors = grid.sym_voltage_sensor.filter(measured_object=[node_id])
    return [int(sensor_id) for sensor_id in sensors.id]


@callback(
    Output("diagnostic-overview-content", "children"),
    Input("cytoscape-graph", "selectedNodeData"),
)
def update_diagnostic_overview(selected_nodes):
    """Display diagnostics for each selected network node."""
    if not selected_nodes:
        return html.P("Select a network node to view diagnostics.")

    grid = server_state.get_grid()
    children = []

    for selected_node in selected_nodes:
        try:
            node_id = int(selected_node["id"])
        except (KeyError, TypeError, ValueError):
            children.append(html.P("The selected element is not a network node."))
            continue

        if node_id not in grid.node.id:
            children.append(html.P("The selected element is not a network node."))
            continue

        sensor_ids = find_voltage_sensors_for_node(node_id, grid)
        sensor_text = (
            "Voltage sensors: " + ", ".join(f"Sensor {sensor_id}" for sensor_id in sensor_ids)
            if sensor_ids
            else "No associated symmetric voltage sensors"
        )

        children.append(
            html.Div(
                [
                    html.Strong(f"Node {node_id}"),
                    html.P(sensor_text, style={"margin": "6px 0 0"}),
                ],
                style={
                    "padding": "10px 0",
                    "borderBottom": "1px solid #e2e8f0",
                },
            )
        )

    return children
