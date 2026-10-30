# SPDX-FileCopyrightText: Contributors to the Power Grid Model project <powergridmodel@lfenergy.org>
#
# SPDX-License-Identifier: MPL-2.0

"""Callbacks for symmetric voltage comparisons."""

from dash import Input, Output, callback
from plotly.graph_objects import Figure

from power_grid_model_ds._core.visualizer import server_state
from power_grid_model_ds._core.visualizer.measurement_comparison import (
    prepare_voltage_comparison,
)
from power_grid_model_ds._core.visualizer.voltage_comparison_figure import (
    create_voltage_comparison_figure,
)


def format_scenario_failure_message(scenario_status):
    """Summarise solver-reported failures for the voltage comparison."""
    if scenario_status is None or not scenario_status.failed_scenarios:
        return ""

    messages = []

    for scenario in sorted(scenario_status.failed_scenarios):
        reason = scenario_status.error_for(scenario)

        if reason:
            reason = " ".join(reason.split())
            messages.append(f"Scenario {scenario} failed: {reason}")
        else:
            messages.append(f"Scenario {scenario} failed.")

    return " ".join(messages)

def find_voltage_sensors_for_selection(selected_nodes, grid):
    """Return symmetric voltage sensors for one selected network node."""
    if not selected_nodes or len(selected_nodes) != 1:
        return []

    try:
        node_id = int(selected_nodes[0]["id"])
    except (KeyError, TypeError, ValueError):
        return []

    # Only accept actual network nodes, not appliance or group elements.
    if node_id not in grid.node.id:
        return []

    sensors = grid.sym_voltage_sensor
    matches = sensors.filter(measured_object=[node_id])

    return [
        {"label": f"Sensor {int(sensor_id)}", "value": int(sensor_id)}
        for sensor_id in matches.id
    ]


@callback(
    Output("voltage-comparison-sensor", "options"),
    Output("voltage-comparison-sensor", "value"),
    Input("cytoscape-graph", "selectedNodeData"),
)
def update_voltage_sensor_options(selected_nodes):
    """List sensors associated with the selected node."""
    grid = server_state.get_grid()
    options = find_voltage_sensors_for_selection(selected_nodes, grid)

    selected_sensor = options[0]["value"] if options else None

    return options, selected_sensor


@callback(
    Output("voltage-comparison-graph", "figure"),
    Output("voltage-comparison-graph", "style"),
    Output("voltage-comparison-message", "children"),
    Input("voltage-comparison-sensor", "value"),
    Input("voltage-comparison-multiplier", "value"),
)
def update_voltage_comparison(sensor_id, multiplier):
    """Update the voltage comparison without rerunning state estimation."""
    if sensor_id is None:
        return (
            Figure(),
            {"display": "none"},
            "Select one node with a symmetric voltage sensor.",
        )

    try:
        scenario_status = server_state.get_scenario_status()

        comparison = prepare_voltage_comparison(
            grid=server_state.get_grid(),
            update_data=server_state.get_update_data(),
            output_data=server_state.get_output_data(),
            sensor_id=int(sensor_id),
            scenario_status=scenario_status,
        )

        figure = create_voltage_comparison_figure(
            comparison,
            multiplier=float(multiplier),
            scenario_status=scenario_status,
        )

        failure_message = format_scenario_failure_message(
            scenario_status
        )

    except (ValueError, TypeError, KeyError) as error:
        return (
            Figure(),
            {"display": "none"},
            f"Voltage comparison unavailable: {error}",
        )

    return figure, {"display": "block"}, failure_message
