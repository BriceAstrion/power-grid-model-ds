"""PoC-04: symmetric voltage measurement versus state-estimation output."""

import numpy as np
import plotly.graph_objects as go
from dash import Input, Output, callback
from power_grid_model import ComponentType

from power_grid_model_ds._core.visualizer.server_state import (
    get_grid, get_output_data, get_update_data,
)


def _field(record, name):
    return record[name] if name in record.dtype.names else None


def _matching_node_voltage(output, node_id, n):
    if output is None or ComponentType.node not in output:
        return None
    rows = output[ComponentType.node]
    if rows.ndim != 2 or rows.shape[0] != n:
        return None
    result = np.full(n, np.nan)
    if 'id' not in rows.dtype.names or 'u' not in rows.dtype.names:
        return None
    for index, scenario in enumerate(rows):
        matches = scenario[scenario['id'] == node_id]
        if len(matches) == 1:
            result[index] = matches[0]['u']
    return result


def _selected_node_id(node_data):
    if not node_data or len(node_data) != 1:
        return None, 'Select exactly one node to compare voltage measurements.'
    node_ids = node_data[0].get('associated_ids', {}).get('node', [])
    if len(node_ids) != 1:
        return None, 'The selection does not identify exactly one node.'
    return int(node_ids[0]), None



def _sensor_for_node(node_id):
    sensors = get_grid().sym_voltage_sensor

    matching_indices = np.flatnonzero(
        np.asarray(sensors["measured_object"]) == node_id
    )

    if matching_indices.size == 0:
        return None, (
            f"No symmetrical voltage sensor is associated with node {node_id}."
        )

    if matching_indices.size > 1:
        return None, (
            f"Node {node_id} has multiple voltage sensors; "
            "sensor-specific selection is not yet supported."
        )

    index = int(matching_indices[0])

    sensor = {
        "id": int(np.asarray(sensors["id"])[index]),
        "u_sigma": float(np.asarray(sensors["u_sigma"])[index]),
    }

    return sensor, None


def _measurement_records(sensor_id):
    updates = get_update_data()
    if updates is None or ComponentType.sym_voltage_sensor not in updates:
        return None, 'No batch voltage measurement updates are available.'
    records = updates[ComponentType.sym_voltage_sensor]
    if records.ndim != 2 or 'id' not in records.dtype.names or 'u_measured' not in records.dtype.names:
        return None, 'The voltage updates do not have the expected batch structure.'
    measured = np.full(records.shape[0], np.nan)
    for index, scenario in enumerate(records):
        matches = scenario[scenario['id'] == sensor_id]
        if len(matches) == 1:
            measured[index] = matches[0]['u_measured']
    return (records, measured), None


def _measurement_sigmas(sensor, records, sensor_id, count):
    sigma_values = np.full(count, float(sensor['u_sigma']))
    if 'u_sigma' not in records.dtype.names:
        return sigma_values
    for index, scenario in enumerate(records):
        matches = scenario[scenario['id'] == sensor_id]
        if len(matches) == 1:
            candidate = float(matches[0]['u_sigma'])
            if np.isfinite(candidate):
                sigma_values[index] = candidate
    return sigma_values


def make_comparison(node_data, multiplier):
    """Pure-ish plotting function, also callable in unit tests."""
    fig = go.Figure()
    node_id, error = _selected_node_id(node_data)
    if error:
        return fig, error
    sensor, error = _sensor_for_node(node_id)
    if error:
        return fig, error
    sensor_id = int(sensor['id'])
    measurement_data, error = _measurement_records(sensor_id)
    if error:
        return fig, error
    records, measured = measurement_data
    estimated = _matching_node_voltage(get_output_data(), node_id, len(measured))
    if estimated is None:
        return fig, 'Matching node voltage estimates are not available.'
    sigma_values = _measurement_sigmas(sensor, records, sensor_id, len(measured))
    if not np.isfinite(measured).any() or not np.isfinite(estimated).any():
        return fig, 'No finite matched measurement and estimate values were found.'
    try:
        k = float(multiplier)
    except (TypeError, ValueError):
        k = 1.0
    if not np.isfinite(k) or k < 0:
        return fig, 'Sigma multiplier must be a non-negative finite number.'
    x = np.arange(len(measured))
    fig.add_scatter(x=x, y=measured, name='Measured voltage', mode='lines')
    fig.add_scatter(x=x, y=estimated, name='Estimated voltage', mode='lines')
    # Band is centered on the measured series, not an automatic validity verdict.
    fig.add_scatter(x=x, y=measured + k * sigma_values, name='Measured + kσ', mode='lines', line={'dash': 'dot'})
    fig.add_scatter(x=x, y=measured - k * sigma_values, name='Measured - kσ', mode='lines', line={'dash': 'dot'}, fill='tonexty', fillcolor='rgba(100,100,100,0.12)')
    fig.update_layout(title=f'Node {node_id} · voltage sensor {sensor_id}', xaxis_title='Scenario index (15-minute intervals in workshop)', yaxis_title='Voltage (V)', template='plotly_white', hovermode='x unified')
    return fig, f'Comparison of {len(measured)} scenarios. The band is descriptive; being inside it does not establish estimate validity.'


@callback(
    Output('measurement-comparison-graph', 'figure'),
    Output('measurement-comparison-status', 'children'),
    Input('cytoscape-graph', 'selectedNodeData'),
    Input('sigma-multiplier', 'value'),
)

def update_measurement_comparison(node_data, multiplier):
    print(
        f"PoC-04 callback triggered: "
        f"multiplier={multiplier}, "
        f"selected_node={node_data}",
        flush=True,
    )

    figure, status = make_comparison(node_data, multiplier)

    return figure, f"k={multiplier} | {status}"

@callback(
    Output("measurement-comparison-graph", "figure"),
    Output("measurement-comparison-status", "children"),
    Input("cytoscape-graph", "selectedNodeData"),
    Input("sigma-multiplier", "value"),
)
def update_measurement_comparison(node_data, multiplier):
    return make_comparison(node_data, multiplier)