"""POC-04: Isolated Cytoscape-to-Plotly selection integration.

The selection shape follows PGM-DS parsers.py and element_selection.py.
Synthetic PGM arrays are used for the runnable demonstration. This does NOT
modify or run inside the original PGM-DS visualiser.

POC-01 maps sensor IDs to estimated node voltages. POC-04 displays these
pairs by scenario index, not timestamp. No sigma band or SE calculation is
claimed in this experiment.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from typing import Any, Callable

import numpy as np
import plotly.graph_objects as go

from poc01_voltage_mapping import map_voltage_measurements


@dataclass(frozen=True)
class Selection:
    status: str
    message: str
    node_id: int | None = None
    sensor_id: int | None = None


def _single_int_id(values: Any) -> int | None:
    """Accept one integral component ID; reject malformed/multiple IDs."""
    if not isinstance(values, (list, tuple)) or len(values) != 1:
        return None
    value = values[0]
    if isinstance(value, (bool, np.bool_)):
        return None
    if isinstance(value, (int, np.integer)):
        return int(value)
    if isinstance(value, str) and value.isdecimal():
        return int(value)
    return None


def _validate_selected_node(node: Any) -> tuple[Selection | None, tuple[int, dict] | None]:
    if not isinstance(node, dict) or node.get("group") != "node":
        return Selection("unsupported_selection", "The selected element is not a network node."), None
    associated = node.get("associated_ids")
    if not isinstance(associated, dict):
        return Selection("invalid_selection", "Selected node has no valid associated_ids mapping."), None
    node_id = _single_int_id(associated.get("node"))
    if node_id is None or str(node.get("id")) != str(node_id):
        return Selection("invalid_selection", "The selected node identifier is inconsistent."), None
    return None, (node_id, associated)


def _resolve_sensor(node_id: int, associated: dict) -> Selection:
    sensor_ids = associated.get("sym_voltage_sensor", [])
    if not isinstance(sensor_ids, (list, tuple)):
        return Selection("invalid_selection", "The voltage-sensor association is invalid.")
    if not sensor_ids:
        return Selection("no_sensor", f"Node {node_id} has no associated symmetric voltage sensor.", node_id)
    if len(sensor_ids) > 1:
        return Selection("multiple_sensors", f"Node {node_id} has multiple voltage sensors; sensor choice is not implemented.", node_id)
    sensor_id = _single_int_id(sensor_ids)
    if sensor_id is None:
        return Selection("invalid_selection", "The voltage-sensor identifier is invalid.", node_id)
    return Selection("selected", f"Node {node_id}, voltage sensor {sensor_id}.", node_id, sensor_id)


def resolve_selection(node_data: Any, edge_data: Any = None) -> Selection:
    """Resolve exactly one node and one associated symmetric voltage sensor.

    PGM-DS node data uses associated_ids={'node': [...],
    'sym_voltage_sensor': [...]}. Multiple selections are not silently reduced
    to an arbitrary first item.
    """
    nodes = node_data or []
    edges = edge_data or []
    if not isinstance(nodes, list) or not isinstance(edges, list):
        return Selection("invalid_selection", "Invalid Cytoscape selection data.")
    if not nodes and not edges:
        return Selection("no_selection", "Select one network node to view its voltage comparison.")
    if edges and not nodes:
        return Selection("unsupported_selection", "Select a node, not an edge, for voltage comparison.")
    if len(nodes) != 1 or edges:
        return Selection("multiple_selection", "Select exactly one node and no edges.")

    error, node_info = _validate_selected_node(nodes[0])
    if error is not None:
        return error
    node_id, associated = node_info
    return _resolve_sensor(node_id, associated)


def empty_figure(message: str) -> go.Figure:
    fig = go.Figure()
    fig.update_layout(
        template="plotly_white",
        title="POC-04: Measurement-to-estimate comparison",
        xaxis_title="Scenario index",
        yaxis_title="Voltage magnitude (V)",
        annotations=[{"text": message, "x": 0.5, "y": 0.5, "xref": "paper", "yref": "paper", "showarrow": False}],
    )
    return fig


def comparison_figure(rows: list[dict], node_id: int, sensor_id: int) -> go.Figure:
    """Plot scenario-indexed pairs. Missing values remain gaps."""
    scenarios = [int(row["scenario"]) for row in rows]
    measured = [float(row["measured"]) for row in rows]
    estimated = [float(row["estimated"]) for row in rows]
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=scenarios, y=measured, mode="lines+markers", name="Measured",
        connectgaps=False,
    ))
    fig.add_trace(go.Scatter(
        x=scenarios, y=estimated, mode="lines+markers", name="Estimated",
        connectgaps=False,
    ))
    fig.update_layout(
        title=f"POC-04: Node {node_id} / voltage sensor {sensor_id}",
        xaxis_title="Scenario index (not timestamp)",
        yaxis_title="Voltage magnitude (V)",
        template="plotly_white", hovermode="x unified",
    )
    return fig


def render_selection(
    node_data: Any,
    edge_data: Any,
    sensors: np.ndarray | None,
    updates: np.ndarray | None,
    outputs: np.ndarray | None,
) -> tuple[go.Figure, str]:
    """Pure callback logic, independently testable without running a server."""
    selection = resolve_selection(node_data, edge_data)
    if selection.status != "selected":
        return empty_figure(selection.message), selection.message
    if sensors is None or updates is None or outputs is None:
        message = "Measurement or estimation data is unavailable."
        return empty_figure(message), message
    try:
        rows = map_voltage_measurements(sensors, updates, outputs, selection.sensor_id)
        if not rows or any(int(row["node_id"]) != selection.node_id for row in rows):
            message = "Selected sensor does not map to the selected node."
            return empty_figure(message), message
    except (ValueError, KeyError, TypeError, IndexError) as exc:
        message = f"Comparison unavailable: {exc}"
        return empty_figure(message), message
    counts = {status: sum(row["status"] == status for row in rows)
              for status in ("matched", "missing_measurement", "missing_estimate")}
    message = (f"Node {selection.node_id}; sensor {selection.sensor_id}; "
               f"{len(rows)} scenarios; {counts['matched']} matched; "
               f"{counts['missing_measurement']} missing measurements; "
               f"{counts['missing_estimate']} missing estimates. "
               "Scenario indices are not timestamps.")
    return comparison_figure(rows, selection.node_id, selection.sensor_id), message


def create_demo_fixture():
    """Two voltage sensors, three scenarios; genuine PGM structured-array schemas."""
    from power_grid_model import ComponentType, DatasetType, initialize_array

    sensors = initialize_array(DatasetType.input, ComponentType.sym_voltage_sensor, 2)
    sensors["id"] = [101, 202]
    sensors["measured_object"] = [10, 20]

    updates = initialize_array(DatasetType.update, ComponentType.sym_voltage_sensor, (3, 2))
    updates["id"] = [[101, 202], [202, 101], [101, 202]]
    updates["u_measured"] = [[230.0, 118.0], [119.0, 231.0], [229.0, 117.0]]

    outputs = initialize_array(DatasetType.sym_output, ComponentType.node, (3, 2))
    outputs["id"] = [[10, 20], [20, 10], [10, 20]]
    outputs["u"] = [[229.5, 118.2], [119.1, 230.5], [228.5, 117.2]]
    return sensors, updates, outputs


def create_demo_elements() -> list[dict]:
    """Synthetic elements with the EXACT selection-data keys from PGM-DS parsers.py."""
    return [
        {"data": {"id": "10", "group": "node", "associated_ids": {
            "node": [10], "sym_voltage_sensor": [101]}}, "position": {"x": 80, "y": 90}},
        {"data": {"id": "20", "group": "node", "associated_ids": {
            "node": [20], "sym_voltage_sensor": [202]}}, "position": {"x": 260, "y": 90}},
        {"data": {"id": "30", "group": "node", "associated_ids": {
            "node": [30]}}, "position": {"x": 170, "y": 210}},
        {"data": {"id": "301", "source": "10", "target": "20", "group": "line",
                  "associated_ids": {"line": [301]}}, "classes": "demo-edge"},
    ]


def read_arrays_from_server_state():
    """Optional adapter for use INSIDE the same PGM-DS visualiser process.

    A separate Dash process cannot read another process's module-level state.
    Grid's IdArray is converted to a minimal structured array because the
    POC-01 mapping function expects NumPy field indexing.
    """
    from power_grid_model import ComponentType
    from power_grid_model_ds._core.visualizer.server_state import (
        get_grid, get_output_data, get_update_data,
    )
    grid = get_grid()
    update_data = get_update_data() or {}
    output_data = get_output_data() or {}
    sensors = np.array(
        [(int(sensor.id.item()), int(sensor.measured_object.item()))
         for sensor in grid.sym_voltage_sensor],
        dtype=[("id", np.int32), ("measured_object", np.int32)],
    )
    return (sensors, update_data.get(ComponentType.sym_voltage_sensor),
            output_data.get(ComponentType.node))


def create_app(
    elements: list[dict] | None = None,
    data_provider: Callable | None = None,
):
    """Run an ISOLATED Dash demo; does not register the original callbacks."""
    import dash_cytoscape as cyto
    from dash import Dash, Input, Output, dcc, html

    if elements is None:
        elements = create_demo_elements()
    if data_provider is None:
        fixture = create_demo_fixture()
        data_provider = lambda: fixture

    app = Dash(__name__)
    app.layout = html.Div([
        html.H3("POC-04 — Isolated Cytoscape-to-Plotly selection test"),
        html.P("Synthetic PGM arrays. Select one node. Scenario indices are not timestamps."),
        cyto.Cytoscape(
            id="cytoscape-graph", elements=elements,
            layout={"name": "preset"},
            style={"width": "100%", "height": "380px"},
            boxSelectionEnabled=True,
            stylesheet=[
                {"selector": "node", "style": {"label": "data(id)", "background-color": "#4B80B8", "color": "#263D54", "text-valign": "top"}},
                {"selector": "edge", "style": {"line-color": "#8A98A6", "width": 3}},
                {"selector": ":selected", "style": {"background-color": "#E39B38", "line-color": "#E39B38"}},
            ],
        ),
        html.Div("Select one node to view its voltage comparison.", id="poc04-comparison-status"),
        dcc.Graph(id="poc04-comparison-graph", figure=empty_figure("Select one node.")),
    ], style={"maxWidth": "1000px", "margin": "auto"})

    @app.callback(
        Output("poc04-comparison-graph", "figure"),
        Output("poc04-comparison-status", "children"),
        Input("cytoscape-graph", "selectedNodeData"),
        Input("cytoscape-graph", "selectedEdgeData"),
    )
    def update_comparison(node_data, edge_data):
        try:
            sensors, updates, outputs = data_provider()
        except (RuntimeError, ValueError) as exc:
            message = f"Comparison data unavailable: {exc}"
            return empty_figure(message), message
        return render_selection(node_data, edge_data, sensors, updates, outputs)

    return app


def main():
    parser = argparse.ArgumentParser(description="POC-04 isolated Dash selection demonstration")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8054)
    args = parser.parse_args()
    print("POC-04: ISOLATED demonstration with synthetic PGM datasets.")
    print("POC-04: Original PGM-DS callbacks and application are NOT modified or tested here.")
    print(f"POC-04: Open http://{args.host}:{args.port}")
    create_app().run(host=args.host, port=args.port, debug=False)


if __name__ == "__main__":
    main()
