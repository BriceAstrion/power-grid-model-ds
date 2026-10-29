
# SPDX-FileCopyrightText: Contributors to the Power Grid Model project <powergridmodel@lfenergy.org>
#
# SPDX-License-Identifier: MPL-2.0

"""Callbacks for the selected-node diagnostic overview."""

from dash import Input, Output, callback, html

from power_grid_model_ds._core.visualizer import server_state
from power_grid_model_ds._core.visualizer.callbacks.voltage_comparison import (
    find_voltage_sensors_for_selection,
)
from power_grid_model_ds._core.visualizer.scenario_status import ScenarioStatus


def build_calculation_summary(status: ScenarioStatus | None) -> list:
    """Summarise reported calculation outcomes without inferring unknown results."""
    if status is None:
        return [html.P("Calculation status unavailable.")]

    succeeded = len(status.succeeded_scenarios)
    failed = len(status.failed_scenarios)

    children = [
        html.H6("Calculation status"),
        html.P(f"Succeeded: {succeeded}"),
        html.P(f"Failed: {failed}"),
        html.P("Unknown: not counted (total scenario count unavailable)."),
    ]

    if status.failed_scenarios:
        children.append(html.H6("Reported failures"))

        failures = []
        for scenario in sorted(status.failed_scenarios):
            reason = status.error_for(scenario)
            description = f"Scenario {scenario}: {reason}" if reason else f"Scenario {scenario}: failed"
            failures.append(html.Li(description))

        children.append(html.Ul(failures))

    return children


@callback(
    Output("diagnostic-overview-content", "children"),
    Input("cytoscape-graph", "selectedNodeData"),
)
def update_diagnostic_overview(selected_nodes):
    """Show node-specific information and reported calculation outcomes."""
    grid = server_state.get_grid()
    status = server_state.get_scenario_status()

    children = []

    if not selected_nodes:
        children.append(html.P("Select one network node to inspect its diagnostics."))

    elif len(selected_nodes) != 1:
        children.append(html.P("Select one network node at a time."))

    else:
        selected_node = selected_nodes[0]

        try:
            node_id = int(selected_node["id"])
        except (KeyError, TypeError, ValueError):
            node_id = None

        if node_id is None or node_id not in grid.node.id:
            children.append(html.P("The selected element is not a network node."))

        else:
            children.append(html.H6(f"Selected node: {node_id}"))

            sensors = find_voltage_sensors_for_selection(selected_nodes, grid)

            if sensors:
                sensor_names = ", ".join(sensor["label"] for sensor in sensors)
                children.append(html.P(f"Voltage sensors: {sensor_names}"))
            else:
                children.append(html.P("No symmetric voltage sensors associated with this node."))

    children.append(html.Hr())
    children.extend(build_calculation_summary(status))

    return children
