# SPDX-FileCopyrightText: Contributors to the Power Grid Model project <powergridmodel@lfenergy.org>
#
# SPDX-License-Identifier: MPL-2.0

from typing import Any

import dash_ag_grid as dag
import numpy as np
import plotly.graph_objects as go
from dash import ALL, Input, Output, State, callback, callback_context, dcc, html, no_update
from dash.exceptions import PreventUpdate
from power_grid_model import ComponentType

from power_grid_model_ds._core.model.grids.base import Grid
from power_grid_model_ds._core.visualizer.callbacks.sigma_multiplier import (
    has_sigma_comparison_metadata,
    is_valid_sigma_multiplier,
    matches_comparison_selection,
    update_retained_sigma_bands,
)
from power_grid_model_ds._core.visualizer.comparison_plot import (
    ComparisonPlotOptions,
    create_measurement_comparison_figure,
)
from power_grid_model_ds._core.visualizer.grid_utils import get_attr_data_from_dataset
from power_grid_model_ds._core.visualizer.layout.selection_output import (
    SELECTION_OUTPUT_HTML,
)
from power_grid_model_ds._core.visualizer.measurement_comparison import (
    MeasurementComparison,
    VoltageComparison,
    get_symmetric_power_comparison,
    get_symmetric_voltage_comparison,
)
from power_grid_model_ds._core.visualizer.server_state import get_grid, get_output_data, get_update_data
from power_grid_model_ds._core.visualizer.uncertainty_diagnostic_plot import create_uncertainty_diagnostic_figure
from power_grid_model_ds.arrays import IdArray

_BATCH_ARRAY_NDIM = 2


@callback(
    Output("selection-output", "children"),
    Input("cytoscape-graph", "selectedNodeData"),
    Input("cytoscape-graph", "selectedEdgeData"),
)
def display_selected_elements(node_data: list[dict[str, Any]], edge_data: list[dict[str, Any]]):
    """Display the selected elements and their associated components."""
    if not node_data and not edge_data:
        return SELECTION_OUTPUT_HTML.children

    items_to_visualize: dict[str, list[int]] = {}
    for node_edge_data in [node_data, edge_data]:
        if node_edge_data is None:
            continue

        for elm in node_edge_data:
            for group, pgm_ids in elm["associated_ids"].items():
                if group not in items_to_visualize:
                    items_to_visualize[group] = []
                items_to_visualize[group].extend(pgm_ids)

    grid: Grid = get_grid()

    tables: list[html.H5 | dag.AgGrid] = []

    for comp_type, ids in items_to_visualize.items():
        unique_ids = list(set(ids))
        data = getattr(grid, comp_type).filter(id=unique_ids)

        tables.append(
            html.H5(
                comp_type,
                style={"marginTop": "15px", "textAlign": "left"},
            )
        )
        tables.append(_to_data_table(array_data=data, group=comp_type))

    return tables


def _to_data_table(array_data: IdArray, group):
    """Convert component attributes into an AG Grid table."""
    data_table_headers: list[dict[str, str]] = [{"field": col, "headerName": col} for col in array_data.columns]

    list_array_data = []

    for entry in array_data:
        record_dict = {}

        for col in array_data.columns:
            if entry[col].ndim == 1:
                record_dict[col] = entry[col].item()
            else:
                record_dict[col] = entry[col].tolist().pop()

        list_array_data.append(record_dict)

    return dag.AgGrid(  # type: ignore[attr-defined]
        id={"type": "selection-table", "group": group},
        getRowId="params.data.id",
        rowData=list_array_data,
        columnDefs=data_table_headers,
        defaultColDef={"filter": True},
        dashGridOptions={
            "maintainColumnOrder": True,
            "animateRows": False,
        },
        columnSize="sizeToFit",
    )


def _create_voltage_comparison_figure(
    comparison: VoltageComparison,
    sensor_id: int,
    sigma_multiplier: float = 3.0,
) -> go.Figure:
    """Preserve voltage presentation through the shared plotter."""
    return create_measurement_comparison_figure(
        comparison,
        ComparisonPlotOptions(
            title=f"sym_voltage_sensor - voltage comparison - id={sensor_id}",
            quantity="voltage",
            unit="V",
            sensor_id=sensor_id,
            comparison_type=ComponentType.sym_voltage_sensor.value,
        ),
        sigma_multiplier=sigma_multiplier,
    )


@callback(
    Output("selected-selection-cell", "data"),
    Input({"type": "selection-table", "group": ALL}, "cellClicked"),
    Input("cytoscape-graph", "selectedNodeData"),
    Input("cytoscape-graph", "selectedEdgeData"),
    prevent_initial_call=True,
)
def store_selected_cell(_, _node_data, _edge_data):
    """Remember a selected cell and clear it when network selection changes."""
    triggered_id = callback_context.triggered_id

    # The displayed component tables may change with the network selection.
    # Clear the previous cell so its graph is not shown for a new selection.
    if triggered_id == "cytoscape-graph":
        return None

    triggered = callback_context.triggered

    if (
        not triggered
        or not isinstance(triggered_id, dict)
        or "selection-table" not in triggered[0]["prop_id"]
        or "cellClicked" not in triggered[0]["prop_id"]
    ):
        return no_update

    value = triggered[0]["value"]
    group = triggered_id.get("group")

    if not isinstance(value, dict) or not isinstance(group, str):
        return no_update

    try:
        component_type = ComponentType(group)
        component_id = int(value["rowId"])
        column_id = value["colId"]
    except (KeyError, TypeError, ValueError):
        return no_update

    if not isinstance(column_id, str):
        return no_update

    return {
        "group": component_type.value,
        "id": component_id,
        "column": column_id,
    }


def _get_voltage_comparison_figure(sensor_id: int, sigma_multiplier: float = 3.0) -> go.Figure | None:
    """Build a comparison graph when symmetric batch node output is available."""
    output_data = get_output_data()
    if output_data is None or ComponentType.node not in output_data:
        return None

    node_output = output_data[ComponentType.node]
    if not isinstance(node_output, np.ndarray) or node_output.ndim != _BATCH_ARRAY_NDIM:
        return None

    field_names = node_output.dtype.names
    if field_names is None or not {"id", "u"}.issubset(field_names):
        return None

    fields = node_output.dtype.fields
    if fields is None or fields["u"][0].subdtype is not None:
        return None

    comparison = get_symmetric_voltage_comparison(
        grid=get_grid(),
        update_data=get_update_data(),
        output_data=output_data,
        sensor_id=sensor_id,
    )
    if comparison is None:
        return None

    return _create_voltage_comparison_figure(comparison, sensor_id=sensor_id, sigma_multiplier=sigma_multiplier)


def _get_power_comparison_figure(
    sensor_id: int, measurement_attribute: str, sigma_multiplier: float = 3.0
) -> go.Figure | None:
    """Build a source-terminal symmetric power comparison."""
    if measurement_attribute not in ("p_measured", "q_measured"):
        return None

    output_data = get_output_data()
    if output_data is None or ComponentType.source not in output_data:
        return None

    source_output = output_data[ComponentType.source]
    quantity = measurement_attribute[0]
    if not _has_scalar_batch_fields(source_output, {"id", quantity}, quantity):
        return None

    try:
        comparison = get_symmetric_power_comparison(
            grid=get_grid(),
            update_data=get_update_data(),
            output_data=output_data,
            sensor_id=sensor_id,
            measurement_attribute=measurement_attribute,
        )
    except NotImplementedError:
        # Other terminal mappings are outside the scope of PR5.
        return None

    quantity_label = "active power" if quantity == "p" else "reactive power"
    return create_measurement_comparison_figure(
        comparison,
        ComparisonPlotOptions(
            title=f"sym_power_sensor - {quantity_label} comparison - id={sensor_id}",
            quantity=quantity_label,
            unit="W" if quantity == "p" else "var",
            sensor_id=sensor_id,
            comparison_type=ComponentType.sym_power_sensor.value,
            measurement_attribute=measurement_attribute,
        ),
        sigma_multiplier=sigma_multiplier,
    )


def _has_scalar_batch_fields(data: Any, required: set[str], quantity: str) -> bool:
    """Check that batch output provides the required scalar attributes."""
    if not isinstance(data, np.ndarray) or data.ndim != _BATCH_ARRAY_NDIM:
        return False
    names = data.dtype.names
    fields = data.dtype.fields
    return (
        names is not None and required.issubset(names) and fields is not None and fields[quantity][0].subdtype is None
    )


def _create_ordinary_selection_graph(comp_type, pgm_id, column_id, group):
    """Render an ordinary selected component attribute."""
    # Preserve existing behaviour for other component attributes.
    x_array, y_array = _get_y_data_for_cell_selection(
        comp_type,
        pgm_id,
        column_id,
    )

    if x_array is None or y_array is None:
        return go.Figure(), {"display": "none"}

    fig = go.Figure()

    if y_array.ndim == 1:
        fig.add_trace(
            go.Scatter(
                x=x_array,
                y=y_array,
                mode="lines",
                line={"width": 2},
            )
        )
    else:
        for i, color in zip(
            range(y_array.shape[1]),
            ["red", "green", "blue"],
            strict=True,
        ):
            fig.add_trace(
                go.Scatter(
                    x=x_array,
                    y=y_array[:, i],
                    mode="lines",
                    line={"width": 2, "color": color},
                    name=f"{column_id}_phase_{i}",
                )
            )

    fig.update_layout(
        title=f"{group} - {column_id} - id={pgm_id}",
        xaxis_title="Scenario Index",
        yaxis_title=column_id,
        template="plotly_white",
        hovermode="x unified",
        showlegend=False,
    )

    return fig, {"display": "block"}


@callback(
    Output("selection-graph", "figure"),
    Output("selection-graph", "style"),
    Input("selected-selection-cell", "data"),
    Input("cytoscape-graph", "selectedNodeData"),
    Input("cytoscape-graph", "selectedEdgeData"),
    State("valid-sigma-multiplier", "data"),
    prevent_initial_call=True,
)
def cell_selection_graph(
    selected_cell,
    node_data=None,
    edge_data=None,
    sigma_multiplier=3.0,
):
    """Render the selected attribute with optional measurement comparison."""
    if not is_valid_sigma_multiplier(sigma_multiplier):
        sigma_multiplier = 3.0
    hidden = {"display": "none"}
    visible = {"display": "block"}

    # Hide the graph when Cytoscape has no selected node or edge.
    # The default arguments preserve existing direct unit-test calls.
    if not isinstance(selected_cell, dict) or (
        (node_data is not None or edge_data is not None) and not node_data and not edge_data
    ):
        return go.Figure(), hidden

    try:
        group = selected_cell["group"]
        comp_type = ComponentType(group)
        pgm_id = int(selected_cell["id"])
        column_id = selected_cell["column"]

        if not isinstance(column_id, str):
            raise ValueError("Invalid selected column")

    except (KeyError, TypeError, ValueError):
        return go.Figure(), hidden

    if comp_type == ComponentType.sym_voltage_sensor and column_id == "u_measured":
        comparison_figure = _get_voltage_comparison_figure(pgm_id, sigma_multiplier)
        if comparison_figure is not None:
            return comparison_figure, visible

    if comp_type == ComponentType.sym_power_sensor and column_id in ("p_measured", "q_measured"):
        comparison_figure = _get_power_comparison_figure(pgm_id, column_id, sigma_multiplier)
        if comparison_figure is not None:
            return comparison_figure, visible

    return _create_ordinary_selection_graph(comp_type, pgm_id, column_id, group)


def _get_y_data_for_cell_selection(
    comp_type: ComponentType,
    pgm_id: int,
    attr: str,
) -> tuple[np.ndarray | None, np.ndarray | None]:
    """Extract the selected attribute from update or output data."""
    update_data = get_update_data()

    if update_data is not None and comp_type in update_data:
        update_names = update_data[comp_type].dtype.names

        if update_names is not None and attr in update_names:
            x_data, y_data = get_attr_data_from_dataset(
                update_data,
                comp_type,
                attr,
                pgm_id,
                get_grid(),
            )
            return x_data, y_data

    output_data = get_output_data()

    if output_data is not None and comp_type in output_data:
        output_names = output_data[comp_type].dtype.names

        if output_names is not None and attr in output_names:
            x_data, y_data = get_attr_data_from_dataset(
                output_data,
                comp_type,
                attr,
                pgm_id,
            )
            return x_data, y_data

    return None, None


_SIGMA_CONTROL_HIDDEN = {"display": "none"}
_SIGMA_CONTROL_VISIBLE = {"display": "block", "marginBottom": "12px"}


@callback(
    Output("sigma-multiplier-control", "style"),
    Input("selection-graph", "figure"),
    Input("selection-graph", "style"),
    Input("retained-uncertainty-store", "data"),
)
def update_sigma_multiplier_visibility(figure, graph_style, entries=None):
    """Show the multiplier for active or retained sigma comparisons."""
    if isinstance(entries, list) and any(
        isinstance(item, dict)
        and isinstance(item.get("comparison"), dict)
        and has_sigma_comparison_metadata(item["comparison"])
        for item in entries
    ):
        return _SIGMA_CONTROL_VISIBLE

    visible = (
        isinstance(figure, dict)
        and isinstance(graph_style, dict)
        and graph_style.get("display") != "none"
        and has_sigma_comparison_metadata(figure)
    )
    return _SIGMA_CONTROL_VISIBLE if visible else _SIGMA_CONTROL_HIDDEN


@callback(
    Output("valid-sigma-multiplier", "data"),
    Input("sigma-multiplier-input", "value"),
    prevent_initial_call=True,
)
def store_valid_sigma_multiplier(value):
    """Preserve the last valid multiplier for this browser session."""
    if not is_valid_sigma_multiplier(value):
        raise PreventUpdate
    return float(value)


@callback(
    Output("sigma-multiplier-input", "invalid"),
    Output("sigma-multiplier-error-text", "children"),
    Output("sigma-multiplier-error", "style"),
    Output("sigma-multiplier-guidance", "style"),
    Input("sigma-multiplier-input", "value"),
)
def validate_sigma_multiplier(value):
    """Provide accessible feedback while keeping the last valid bands."""
    valid = is_valid_sigma_multiplier(value)
    if valid:
        return False, "", {"display": "none"}, {"display": "flex"}
    return (
        True,
        "Enter a finite number greater than or equal to zero.",
        {"display": "flex", "alignItems": "center", "justifyContent": "flex-end", "gap": "12px", "color": "#912018"},
        {"display": "none"},
    )


def _has_uncertainty_diagnostic_metadata(meta: dict) -> bool:
    """Check that the comparison figure contains all diagnostic source series."""
    return all(key in meta for key in ("scenario_indices", "measured", "estimated", "sigma"))


def _get_uncertainty_diagnostic_comparison(
    figure: dict | None,
    graph_style: dict | None,
    selected_cell: dict | None,
) -> MeasurementComparison | None:
    """Extract a valid comparison for uncertainty diagnostic rendering."""
    if (
        not isinstance(figure, dict)
        or not isinstance(graph_style, dict)
        or graph_style.get("display") == "none"
        or not isinstance(selected_cell, dict)
    ):
        return None

    layout = figure.get("layout")
    if not isinstance(layout, dict):
        return None

    meta = layout.get("meta")
    if (
        not isinstance(meta, dict)
        or not has_sigma_comparison_metadata(figure)
        or not _has_uncertainty_diagnostic_metadata(meta)
        or not matches_comparison_selection(meta, selected_cell)
    ):
        return None

    try:
        comparison = MeasurementComparison(
            scenario_indices=np.asarray(meta["scenario_indices"], dtype=np.intp),
            measured=np.asarray(meta["measured"], dtype=np.float64),
            estimated=np.asarray(meta["estimated"], dtype=np.float64),
            sigma=np.asarray(meta["sigma"], dtype=np.float64),
        )
    except (KeyError, TypeError, ValueError):
        return None

    arrays = (
        comparison.scenario_indices,
        comparison.measured,
        comparison.estimated,
        comparison.sigma,
    )

    if (
        any(array is None or array.ndim != 1 for array in arrays)
        or len({array.shape for array in arrays if array is not None}) != 1
    ):
        return None

    return comparison


@callback(
    Output("uncertainty-diagnostic-graph", "figure"),
    Output("uncertainty-diagnostic-graph", "style"),
    Input("selection-graph", "figure"),
    Input("selection-graph", "style"),
    Input("selected-selection-cell", "data"),
    prevent_initial_call=True,
)
def update_uncertainty_diagnostic_graph(figure, graph_style, selected_cell):
    """Render a separate uncertainty diagnostic for the active comparison."""
    comparison = _get_uncertainty_diagnostic_comparison(
        figure,
        graph_style,
        selected_cell,
    )

    if comparison is None:
        return go.Figure(), {"display": "none"}

    try:
        diagnostic_figure = create_uncertainty_diagnostic_figure(
            comparison,
            title=(
                "Normalized residual"
                f" - {selected_cell['group']} / {selected_cell['column']}"
                f" / sensor {selected_cell['id']}"
            ),
        )
    except ValueError:
        return go.Figure(), {"display": "none"}

    diagnostic_figure.update_layout(
        meta={
            "retention_group": selected_cell["group"],
            "retention_sensor_id": int(selected_cell["id"]),
            "retention_attribute": selected_cell["column"],
        }
    )
    return diagnostic_figure, {"display": "block"}


_UNCERTAINTY_STATUS_MESSAGES = {
    "sigma_missing": ("Normalized residual is unavailable because measurement uncertainty (sigma) is missing."),
    "sigma_nonfinite": ("Normalized residual is unavailable because no finite sigma values are available."),
}


@callback(
    Output("uncertainty-diagnostic-status", "children"),
    Output("uncertainty-diagnostic-status", "style"),
    Input("selection-graph", "figure"),
    Input("selection-graph", "style"),
    Input("selected-selection-cell", "data"),
    prevent_initial_call=True,
)
def update_uncertainty_diagnostic_status(figure, graph_style, selected_cell):
    """Explain why a selected comparison has no uncertainty diagnostic."""
    hidden = ("", {"display": "none"})
    if (
        not isinstance(figure, dict)
        or not isinstance(graph_style, dict)
        or graph_style.get("display") == "none"
        or not isinstance(selected_cell, dict)
    ):
        return hidden

    layout = figure.get("layout")
    if not isinstance(layout, dict):
        return hidden
    meta = layout.get("meta")
    if not isinstance(meta, dict) or not matches_comparison_selection(meta, selected_cell):
        return hidden

    message = _UNCERTAINTY_STATUS_MESSAGES.get(meta.get("uncertainty_diagnostic_status"))
    if message is None:
        return hidden
    return message, {"display": "block", "color": "#694100", "marginTop": "8px"}


# Standalone F15: each measurement owns a comparison and an optional diagnostic.
# The retained figures are snapshots from the current visualizer session.
def _measurement_identity(selected_cell):
    """Identify supported measurements without conflating p and q sensors."""
    if not isinstance(selected_cell, dict):
        return None
    group = selected_cell.get("group")
    attribute = selected_cell.get("column")
    allowed = {
        (ComponentType.sym_voltage_sensor.value, "u_measured"),
        (ComponentType.sym_power_sensor.value, "p_measured"),
        (ComponentType.sym_power_sensor.value, "q_measured"),
    }
    if (group, attribute) not in allowed:
        return None
    sensor_id = selected_cell.get("id")
    try:
        if isinstance(sensor_id, bool):
            raise ValueError("Boolean sensor ID")
        sensor_id = int(sensor_id)
    except (TypeError, ValueError, OverflowError):
        return None
    return f"{group}|{sensor_id}|{attribute}"


def _retained_uncertainty_key(figure):
    """Read the measurement identity attached to a diagnostic figure."""
    if not isinstance(figure, dict):
        return None
    layout = figure.get("layout")
    meta = layout.get("meta") if isinstance(layout, dict) else None
    if not isinstance(meta, dict):
        return None
    return _measurement_identity(
        {
            "group": meta.get("retention_group"),
            "id": meta.get("retention_sensor_id"),
            "column": meta.get("retention_attribute"),
        }
    )


def _valid_diagnostic(figure, style, identity):
    """Check the diagnostic belongs to the selected measurement and is visible."""
    if not isinstance(style, dict) or style.get("display") == "none":
        return False
    if _retained_uncertainty_key(figure) != identity:
        return False
    return isinstance(figure, dict) and bool(figure.get("data"))


def _capture_retained_measurement(retained, selected_cell, comparison_pair, diagnostic_pair):
    """Capture a comparison and its matching uncertainty diagnostic."""
    comparison, comparison_style = comparison_pair
    diagnostic, diagnostic_style = diagnostic_pair

    identity = _measurement_identity(selected_cell)
    if identity is None or not isinstance(comparison, dict):
        return retained

    if not isinstance(comparison_style, dict) or comparison_style.get("display") == "none":
        return retained

    layout = comparison.get("layout")
    meta = layout.get("meta") if isinstance(layout, dict) else None

    if not isinstance(meta, dict) or not matches_comparison_selection(meta, selected_cell):
        return retained

    if not comparison.get("data"):
        return retained

    updated = {
        "key": identity,
        "comparison": comparison,
        "diagnostic": (diagnostic if _valid_diagnostic(diagnostic, diagnostic_style, identity) else None),
    }

    for index, item in enumerate(retained):
        if item["key"] == identity:
            retained[index] = updated
            break
    else:
        retained.append(updated)

    return retained


def _remove_retained_measurement(retained, action, key):
    """Remove a measurement pair or only its uncertainty diagnostic."""
    if action == "remove-measurement":
        return [item for item in retained if item["key"] != key]

    if action == "remove-diagnostic":
        for item in retained:
            if item["key"] == key:
                item["diagnostic"] = None

    return retained


def _update_retained_measurements(entries, *, action, **options):
    """Update retained measurements according to the requested action."""
    retained = [
        dict(item)
        for item in (entries if isinstance(entries, list) else [])
        if isinstance(item, dict) and isinstance(item.get("key"), str)
    ]

    if action == "clear":
        return []

    if action in ("remove-measurement", "remove-diagnostic"):
        return _remove_retained_measurement(retained, action, options.get("key"))

    if action == "update-multiplier":
        return update_retained_sigma_bands(retained, options.get("multiplier"))

    if action == "capture":
        return _capture_retained_measurement(
            retained,
            options.get("selected_cell"),
            (
                options.get("comparison"),
                options.get("comparison_style"),
            ),
            (
                options.get("diagnostic"),
                options.get("diagnostic_style"),
            ),
        )

    return retained


@callback(
    output=Output("retained-uncertainty-store", "data"),
    inputs={
        "diagnostic_pair": [
            Input("uncertainty-diagnostic-graph", "figure"),
            Input("uncertainty-diagnostic-graph", "style"),
        ],
        "workspace_controls": {
            "multiplier": Input("valid-sigma-multiplier", "data"),
            "removal_controls": [
                Input({"type": "retained-measurement-remove", "index": ALL}, "n_clicks"),
                Input({"type": "retained-uncertainty-remove", "index": ALL}, "n_clicks"),
                Input("retained-uncertainty-clear", "n_clicks"),
            ],
        },
    },
    state={
        "comparison_pair": [
            State("selection-graph", "figure"),
            State("selection-graph", "style"),
        ],
        "selected_cell": State("selected-selection-cell", "data"),
        "entries": State("retained-uncertainty-store", "data"),
    },
    prevent_initial_call=True,
)
def retain_uncertainty_diagnostics(
    diagnostic_pair,
    workspace_controls,
    comparison_pair,
    selected_cell,
    entries,
):
    """Capture graphs or handle retention and multiplier controls."""
    diagnostic, diagnostic_style = diagnostic_pair
    comparison, comparison_style = comparison_pair

    multiplier = workspace_controls["multiplier"]
    triggered = callback_context.triggered_id

    if triggered == "valid-sigma-multiplier":
        if not entries or not is_valid_sigma_multiplier(multiplier):
            raise PreventUpdate
        return _update_retained_measurements(entries, action="update-multiplier", multiplier=multiplier)

    if triggered == "retained-uncertainty-clear":
        return _update_retained_measurements(entries, action="clear")

    if isinstance(triggered, dict):
        if not callback_context.triggered or not callback_context.triggered[0].get("value"):
            raise PreventUpdate

        kind = triggered.get("type")
        if kind in ("retained-measurement-remove", "retained-uncertainty-remove"):
            return _update_retained_measurements(
                entries,
                action=("remove-measurement" if kind == "retained-measurement-remove" else "remove-diagnostic"),
                key=triggered.get("index"),
            )

    if triggered == "uncertainty-diagnostic-graph":
        retained = _update_retained_measurements(
            entries,
            action="capture",
            selected_cell=selected_cell,
            comparison=comparison,
            comparison_style=comparison_style,
            diagnostic=diagnostic,
            diagnostic_style=diagnostic_style,
        )
        return _update_retained_measurements(retained, action="update-multiplier", multiplier=multiplier)

    raise PreventUpdate


@callback(
    Output("retained-uncertainty-section", "style"),
    Output("retained-uncertainty-list", "children"),
    Input("retained-uncertainty-store", "data"),
)
def render_retained_uncertainty_diagnostics(entries):
    """Render each comparison with its own independently removable diagnostic."""
    if not entries:
        return {"display": "none"}, []
    cards = []
    for item in entries:
        key = item.get("key")
        comparison = item.get("comparison")
        diagnostic = item.get("diagnostic")
        if not isinstance(key, str) or not isinstance(comparison, dict):
            continue
        title = key.replace("|", " / ")
        has_diagnostic = isinstance(diagnostic, dict)
        remove_label = "Remove measurement + normalized residual" if has_diagnostic else "Remove"
        children = [
            html.Div(
                [
                    html.Strong(title),
                    html.Button(
                        [
                            html.Span(
                                "✕",
                                style={
                                    "fontSize": "20px",
                                    "fontWeight": "bold",
                                    "marginRight": "0px",
                                    "verticalAlign": "middle",
                                },
                            ),
                            remove_label,
                        ],
                        id={"type": "retained-measurement-remove", "index": key},
                        n_clicks=0,
                        type="button",
                        className="btn btn-outline-danger",
                        style={
                            "display": "inline-flex",
                            "alignItems": "center",
                            "justifyContent": "center",
                            "gap": "8px",
                            "padding": "8px 14px",
                            "fontSize": "14px",
                            "fontWeight": "600",
                            "borderWidth": "2px",
                            "borderRadius": "7px",
                        },
                    ),
                ],
                style={"display": "flex", "justifyContent": "space-between", "alignItems": "center"},
            ),
            dcc.Graph(figure=comparison, config={"displayModeBar": True}),
        ]
        if has_diagnostic:
            children.extend(
                [
                    html.Div(
                        [
                            html.Strong("Normalized residual"),
                            html.Button(
                                [
                                    html.Span(
                                        "✕",
                                        style={
                                            "fontSize": "20px",
                                            "fontWeight": "bold",
                                            "marginRight": "0px",
                                            "verticalAlign": "middle",
                                        },
                                    ),
                                    "Remove normalized residual",
                                ],
                                id={"type": "retained-uncertainty-remove", "index": key},
                                n_clicks=0,
                                type="button",
                                className="btn btn-outline-danger",
                                style={
                                    "display": "inline-flex",
                                    "alignItems": "center",
                                    "justifyContent": "center",
                                    "gap": "8px",
                                    "padding": "8px 14px",
                                    "fontSize": "14px",
                                    "fontWeight": "600",
                                    "borderWidth": "2px",
                                    "borderRadius": "7px",
                                },
                            ),
                        ],
                        style={"display": "flex", "justifyContent": "space-between", "alignItems": "center"},
                    ),
                    dcc.Graph(figure=diagnostic, config={"displayModeBar": True}),
                ]
            )
        cards.append(
            html.Div(
                children,
                style={"border": "1px solid #ddd", "borderRadius": "6px", "padding": "12px", "marginBottom": "12px"},
            )
        )
    return ({"display": "block", "marginTop": "18px"}, cards) if cards else ({"display": "none"}, [])


@callback(
    Output("active-selection-graphs", "style"),
    Input("selection-graph", "figure"),
    Input("selected-selection-cell", "data"),
)
def hide_active_graphs_when_retained(figure, selected_cell):
    """Display measurement comparisons only in the retained workspace."""
    if isinstance(figure, dict) and isinstance(selected_cell, dict):
        layout = figure.get("layout")
        meta = layout.get("meta") if isinstance(layout, dict) else None
        if isinstance(meta, dict) and matches_comparison_selection(meta, selected_cell):
            return {"display": "none"}
    return {"display": "block"}
