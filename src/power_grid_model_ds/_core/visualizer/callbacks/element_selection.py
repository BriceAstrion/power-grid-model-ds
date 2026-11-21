# SPDX-FileCopyrightText: Contributors to the Power Grid Model project <powergridmodel@lfenergy.org>
#
# SPDX-License-Identifier: MPL-2.0

from typing import Any, LiteralString, cast
from urllib.parse import quote

import numpy as np
import plotly.graph_objects as go
from dash import ALL, MATCH, Input, Output, State, callback, callback_context, dcc, html, no_update
from dash.exceptions import PreventUpdate
from power_grid_model import ComponentType

from power_grid_model_ds._core.model.grids.base import Grid
from power_grid_model_ds._core.visualizer.callbacks import uncertainty_callbacks
from power_grid_model_ds._core.visualizer.comparison_plot import (
    ComparisonPlotOptions,
    create_measurement_comparison_figure,
)
from power_grid_model_ds._core.visualizer.graph_action_styles import (
    GRAPH_ACTION_BUTTON_STYLE,
    GRAPH_ACTION_HEADER_STYLE,
)
from power_grid_model_ds._core.visualizer.graph_selections import (
    GraphSelection,
    add_graph_selection,
    clear_graph_selections,
    remove_graph_selection,
)
from power_grid_model_ds._core.visualizer.grid_utils import get_attr_data_from_dataset
from power_grid_model_ds._core.visualizer.layout.selection_output import SELECTION_OUTPUT_HTML
from power_grid_model_ds._core.visualizer.measurement_comparison import (
    DENSE_BATCH_NDIM,
    VoltageComparison,
    get_symmetric_power_comparison,
    get_symmetric_voltage_comparison,
)
from power_grid_model_ds._core.visualizer.scenario_selection import (
    get_component_state,
    get_effective_component_state,
    get_scenario_count,
    is_valid_scenario_index,
)
from power_grid_model_ds._core.visualizer.server_state import get_grid, get_output_data, get_update_data
from power_grid_model_ds.arrays import IdArray

# Preserve the existing imports used by callers and unit tests after moving
# the callback implementations to uncertainty_callbacks.py.
update_uncertainty_diagnostic_graph = uncertainty_callbacks.update_uncertainty_diagnostic_graph
update_uncertainty_diagnostic_status = uncertainty_callbacks.update_uncertainty_diagnostic_status

# AG Grid-style narrowing horizontal bars, used only in the attribute inspector.
_FILTER_ICON = "data:image/svg+xml," + quote(
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" '
    'fill="none" stroke="#444" stroke-width="2.2" stroke-linecap="square">'
    '<path d="M3 6H21 M7 12H17 M10 18H14"/></svg>'
)
_BORDER_STYLE = "1px solid #dee2e6"


_OPERATORS = [
    {"label": "Equals (=)", "value": "="},
    {"label": "Not equal (!=)", "value": "!="},
    {"label": "Greater than (>)", "value": ">"},
    {"label": "Less than (<)", "value": "<"},
    {"label": "Contains", "value": "contains"},
]


OUTPUT_PREFIX = "output__"
SCALAR_ARRAY_DIMENSIONS = 2
PHASE_COLORS = ("red", "green", "blue")

BATCH_DIMENSIONS = DENSE_BATCH_NDIM


@callback(
    Output("selection-output", "children"),
    Input("cytoscape-graph", "selectedNodeData"),
    Input("cytoscape-graph", "selectedEdgeData"),
    Input("scenario-selector", "value"),
)
def display_selected_elements(
    node_data: list[dict[str, Any]] | None,
    edge_data: list[dict[str, Any]] | None,
    scenario_index: int | None = None,
):
    """Show the attributes of selected network components."""
    if not node_data and not edge_data:
        return SELECTION_OUTPUT_HTML.children

    items_to_visualize: dict[str, list[int]] = {}
    for elements in (node_data, edge_data):
        for element in elements or []:
            for group, pgm_ids in element["associated_ids"].items():
                items_to_visualize.setdefault(group, []).extend(pgm_ids)

    grid: Grid = get_grid()
    panels: list[Any] = []
    for group, ids in items_to_visualize.items():
        data = getattr(grid, group).filter(id=list(set(ids)))
        panels.append(html.H5(group, style={"marginTop": "15px", "textAlign": "left"}))
        panels.append(_to_data_table(data, group, _scenario_rows(data, group, scenario_index)))
    return panels


_FILTER_POPUP_STYLE = {
    "display": "none",
    "position": "absolute",
    "right": "0",
    "top": "100%",
    "zIndex": 20,
    "padding": "10px",
    "backgroundColor": "white",
    "border": _BORDER_STYLE,
    "boxShadow": "0 2px 8px #0002",
}


def _attribute_row(attribute: str, group: str) -> html.Div:
    """Build one attribute row with a filter popup controlled by Dash."""
    return html.Div(
        [
            html.Div(
                [
                    html.Span(
                        f"Output: {attribute.removeprefix('output__')}"
                        if attribute.startswith("output__")
                        else attribute,
                        style={"overflowWrap": "anywhere"},
                    ),
                    html.Div(
                        [
                            html.Button(
                                html.Img(src=_FILTER_ICON, alt="", style={"width": "16px", "height": "16px"}),
                                id={"type": "attribute-filter-toggle", "group": group, "attribute": attribute},
                                n_clicks=0,
                                type="button",
                                title=f"Filter {attribute}",
                                **{"aria-label": f"Filter {attribute}"},  # type: ignore[arg-type]
                                style={
                                    "display": "flex",
                                    "alignItems": "center",
                                    "justifyContent": "center",
                                    "cursor": "pointer",
                                    "width": "22px",
                                    "height": "24px",
                                    "border": "none",
                                    "background": "transparent",
                                    "padding": "0",
                                },
                            ),
                            html.Div(
                                [
                                    dcc.Dropdown(
                                        id={
                                            "type": "attribute-filter-operator",
                                            "group": group,
                                            "attribute": attribute,
                                        },
                                        options=_OPERATORS,
                                        value="=",
                                        clearable=False,
                                        style={"minWidth": "145px"},
                                    ),
                                    dcc.Input(
                                        id={
                                            "type": "attribute-filter-value",
                                            "group": group,
                                            "attribute": attribute,
                                        },
                                        type="text",
                                        placeholder="Filter value",
                                        debounce=True,
                                        style={"width": "145px", "marginTop": "6px"},
                                    ),
                                ],
                                id={"type": "attribute-filter-popup", "group": group, "attribute": attribute},
                                style=_FILTER_POPUP_STYLE.copy(),
                            ),
                        ],
                        style={"position": "relative"},
                    ),
                ],
                style={
                    "display": "flex",
                    "justifyContent": "space-between",
                    "alignItems": "center",
                    "gap": "8px",
                    "minWidth": "0",
                    "padding": "10px",
                    "borderRight": _BORDER_STYLE,
                },
            ),
            html.Div(
                id={"type": "attribute-values", "group": group, "attribute": attribute},
                style={"minWidth": "0", "padding": "10px", "overflowWrap": "anywhere"},
            ),
        ],
        style={
            "display": "grid",
            "gridTemplateColumns": "minmax(0, 1fr) minmax(0, 1fr)",
            "borderBottom": _BORDER_STYLE,
            "alignItems": "stretch",
        },
    )


def _create_voltage_comparison_figure(
    comparison: VoltageComparison,
    sensor_id: int,
    sigma_multiplier: float = 2.0,
) -> go.Figure:
    """Preserve the existing voltage presentation via the shared plotter."""
    return create_measurement_comparison_figure(
        cast(Any, comparison),
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
    Input({"type": "attribute-plot", "group": ALL, "attribute": ALL, "pgm_id": ALL}, "n_clicks"),
    Input("cytoscape-graph", "selectedNodeData"),
    Input("cytoscape-graph", "selectedEdgeData"),
    prevent_initial_call=True,
)
def store_selected_cell(_clicks, _node_data, _edge_data):
    """Capture existing inspector button clicks and clear temporary selection on network changes."""
    triggered_id = callback_context.triggered_id
    if triggered_id == "cytoscape-graph":
        return None
    if not isinstance(triggered_id, dict) or triggered_id.get("type") != "attribute-plot":
        return no_update
    if not callback_context.triggered or not callback_context.triggered[0].get("value"):
        return no_update
    try:
        group = ComponentType(triggered_id["group"]).value
        component_id = int(triggered_id["pgm_id"])
        column = triggered_id["attribute"]
    except (KeyError, TypeError, ValueError):
        return no_update
    if not isinstance(column, str):
        return no_update
    return {"group": group, "id": component_id, "column": column}


def _remove_retained_graph(triggered_id, retained):
    """Remove a graph when a valid Remove button is clicked."""
    if triggered_id.get("type") != "remove-retained-graph":
        return no_update

    triggered = callback_context.triggered

    # A dynamically created button starts with n_clicks=0.
    # Its initial appearance must not remove a graph.
    if (
        not triggered
        or not isinstance(triggered[0].get("value"), int)
        or isinstance(triggered[0]["value"], bool)
        or triggered[0]["value"] <= 0
    ):
        return no_update

    index = triggered_id.get("index")

    if not isinstance(index, int) or isinstance(index, bool) or not 0 <= index < len(retained):
        return no_update

    return remove_graph_selection(
        retained,
        retained[index],
    )


def _add_retained_graph(selected_cell, retained):
    """Add a valid cell selection without duplicating a graph."""
    if not isinstance(selected_cell, dict):
        return no_update

    group = selected_cell.get("group")
    component_id = selected_cell.get("id")
    column = selected_cell.get("column")

    if (
        not isinstance(group, str)
        or not isinstance(component_id, int)
        or isinstance(component_id, bool)
        or not isinstance(column, str)
    ):
        return no_update

    selection: GraphSelection = {
        "group": group,
        "id": component_id,
        "column": column,
    }

    return add_graph_selection(
        retained,
        selection,
    )


@callback(
    Output("retained-graph-selections", "data"),
    Input("selected-selection-cell", "data"),
    Input("clear-retained-graphs", "n_clicks"),
    Input(
        {
            "type": "remove-retained-graph",
            "index": ALL,
        },
        "n_clicks",
    ),
    State("retained-graph-selections", "data"),
    prevent_initial_call=True,
)
def update_retained_graph_selections(
    selected_cell,
    _clear_clicks,
    _remove_clicks,
    retained_selections,
):
    """Add, remove or clear retained graph selections."""
    triggered_id = callback_context.triggered_id
    retained = retained_selections or []

    if triggered_id == "clear-retained-graphs":
        return clear_graph_selections()

    if isinstance(triggered_id, dict):
        return _remove_retained_graph(
            triggered_id,
            retained,
        )

    if triggered_id != "selected-selection-cell":
        return no_update

    return _add_retained_graph(
        selected_cell,
        retained,
    )


@callback(
    Output({"type": "attribute-filter-popup", "group": ALL, "attribute": ALL}, "style"),
    Input({"type": "attribute-filter-toggle", "group": ALL, "attribute": ALL}, "n_clicks"),
    State({"type": "attribute-filter-popup", "group": ALL, "attribute": ALL}, "id"),
    State({"type": "attribute-filter-popup", "group": ALL, "attribute": ALL}, "style"),
    prevent_initial_call=True,
)
def toggle_attribute_filter(_clicks, popup_ids, popup_styles):
    """Keep at most one attribute filter popup open across component groups."""
    clicked = callback_context.triggered_id
    if not isinstance(clicked, dict) or clicked.get("type") != "attribute-filter-toggle":
        raise PreventUpdate
    if not callback_context.triggered or not callback_context.triggered[0].get("value"):
        raise PreventUpdate

    target = next(
        (
            index
            for index, popup_id in enumerate(popup_ids)
            if popup_id["group"] == clicked["group"] and popup_id["attribute"] == clicked["attribute"]
        ),
        None,
    )
    if target is None:
        raise PreventUpdate

    should_open = (popup_styles[target] or {}).get("display") != "block"
    return [
        {**(style or _FILTER_POPUP_STYLE), "display": "block" if should_open and index == target else "none"}
        for index, style in enumerate(popup_styles)
    ]


def _base_rows(array_data: IdArray) -> list[dict[str, Any]]:
    """Return independent Python values for the existing attribute inspector."""
    rows = []
    for entry in array_data:
        row = {}
        for attribute in array_data.columns:
            value = entry[attribute]
            row[attribute] = value.item() if value.ndim == 1 else value.tolist().pop()
        rows.append(row)
    return rows


def _scenario_rows(array_data: IdArray, group: str, scenario_index: int | None):
    """Overlay scenario inputs and append outputs to existing inspector records."""
    rows = _base_rows(array_data)
    update_data, output_data = get_update_data(), get_output_data()
    count = get_scenario_count(update_data, output_data)
    if scenario_index is None or not is_valid_scenario_index(scenario_index, count):
        return rows
    component_type = ComponentType(group)
    for row in rows:
        component_id = int(row["id"])
        effective = get_effective_component_state(row, update_data, component_type, component_id, scenario_index)
        if output_data is not None:
            output = get_component_state(output_data, component_type, component_id, scenario_index)
            if output:
                effective.update({f"{OUTPUT_PREFIX}{key}": value for key, value in output.items() if key != "id"})
        row.clear()
        row.update(effective)
    return rows


def _to_data_table(array_data: IdArray, group: str, records: list[dict[str, Any]] | None = None) -> html.Div:
    """Preserve the integrated inspector and expose scenario-effective attributes."""
    if records is None:
        records = _base_rows(array_data)
    attributes = list(array_data.columns)
    attributes.extend(sorted({key for record in records for key in record if key.startswith(OUTPUT_PREFIX)}))
    attribute_rows = [_attribute_row(attribute, group) for attribute in attributes]
    return html.Div(
        [
            dcc.Store(id={"type": "attribute-records", "group": group}, data=records),
            html.Div(
                [html.Strong("Attribute"), html.Strong("Value")],
                style={
                    "display": "grid",
                    "gridTemplateColumns": "1fr 1fr",
                    "padding": "10px",
                    "backgroundColor": "#f8f9fa",
                    "borderBottom": _BORDER_STYLE,
                },
            ),
            *attribute_rows,
        ],
        id={"type": "selection-inspector", "group": group},
        style={"border": _BORDER_STYLE, "borderRadius": "8px", "marginBottom": "16px"},
    )


def _matches(value: Any, operator: str, query: str) -> bool:
    """Compare one attribute value with a user-supplied filter."""
    if value is None:
        return False

    if operator == "contains":
        return query.casefold() in str(value).casefold()

    # Array-valued attributes support text equality but not numeric ordering.
    if isinstance(value, list):
        left, right = str(value), query
        return (left == right and operator == "=") or (left != right and operator == "!=")

    try:
        left_number, right_number = float(value), float(query)
    except (TypeError, ValueError):
        left_text, right_text = str(value), query
        return (left_text == right_text and operator == "=") or (left_text != right_text and operator == "!=")

    return {
        "=": left_number == right_number,
        "!=": left_number != right_number,
        ">": left_number > right_number,
        "<": left_number < right_number,
    }.get(operator, False)


def _active_attribute_filters(filter_ids, operators, values):
    return [
        (item_id["attribute"], operator, str(value).strip())
        for item_id, operator, value in zip(filter_ids, operators, values, strict=True)
        if value is not None and str(value).strip()
    ]


def _matching_attribute_records(records, active_filters):
    return [
        record
        for record in records
        if all(_matches(record.get(attribute), operator, query) for attribute, operator, query in active_filters)
    ]


def _has_scenario_attribute_data(group: str, component_id: int, attribute: str) -> bool:
    """Check whether a component has usable batch data for an attribute."""
    try:
        comp_type = ComponentType(group)
        x_array, y_array = _get_y_data_for_cell_selection(comp_type, component_id, attribute)
    except (KeyError, TypeError, ValueError, IndexError):
        return False

    return x_array is not None and y_array is not None and len(x_array) > 0 and len(y_array) > 0


def _attribute_value_button(record, attribute, group, include_id):
    value = record.get(attribute)
    label = "—" if value is None else str(value)
    if include_id:
        label = f"ID {record['id']}: {label}"
    if value is None and not _has_scenario_attribute_data(group, int(record["id"]), attribute):
        return html.Span(label)
    return html.Button(
        label,
        id={
            "type": "attribute-plot",
            "group": group,
            "attribute": attribute,
            "pgm_id": int(record["id"]),
        },
        n_clicks=0,
        title="Plot this attribute when scenario data is available",
        style={
            "border": "none",
            "background": "none",
            "padding": "0",
            "color": "#0d6efd",
            "textAlign": "left",
            "cursor": "pointer",
            "overflowWrap": "anywhere",
        },
    )


def _attribute_value_cell(output_id, matching, include_id):
    buttons = [
        _attribute_value_button(record, output_id["attribute"], output_id["group"], include_id) for record in matching
    ]
    if not buttons:
        return "—"
    return html.Div(buttons, style={"display": "flex", "flexDirection": "column", "gap": "4px"})


@callback(
    Output({"type": "attribute-values", "group": MATCH, "attribute": ALL}, "children"),
    Input({"type": "attribute-filter-operator", "group": MATCH, "attribute": ALL}, "value"),
    Input({"type": "attribute-filter-value", "group": MATCH, "attribute": ALL}, "value"),
    State({"type": "attribute-filter-value", "group": MATCH, "attribute": ALL}, "id"),
    State({"type": "attribute-records", "group": MATCH}, "data"),
    State({"type": "attribute-values", "group": MATCH, "attribute": ALL}, "id"),
)
def update_attribute_values(operators, values, filter_ids, records, output_ids):
    """Apply all active attribute filters to the selected components."""
    records = records or []
    active_filters = _active_attribute_filters(filter_ids, operators, values)
    matching = _matching_attribute_records(records, active_filters)
    include_id = len(records) > 1
    return [_attribute_value_cell(output_id, matching, include_id) for output_id in output_ids]


def _power_comparison_graph(  # noqa: PLR0911  # pylint: disable=too-many-return-statements
    sensor_id: int, measurement_attribute: str, sigma_multiplier: float | None
):
    """Build a source-terminal power comparison when calculated output is available."""
    output_data = get_output_data()
    if output_data is None or ComponentType.source not in output_data:
        return None
    source_output = output_data[ComponentType.source]
    if not _is_dense_batch_array(source_output):
        return None
    field = measurement_attribute[0]
    if source_output.dtype.fields is None or field not in source_output.dtype.fields:
        return None
    if source_output.dtype.fields[cast(LiteralString, field)][0].subdtype is not None:
        return None
    _require_explicit_ids(source_output)

    update_data = get_update_data()
    if update_data is not None and ComponentType.sym_power_sensor in update_data:
        updates = update_data[ComponentType.sym_power_sensor]
        if not _is_dense_batch_array(updates):
            return None
        _require_explicit_ids(updates)

    try:
        comparison = get_symmetric_power_comparison(
            grid=get_grid(),
            update_data=update_data,
            output_data=output_data,
            sensor_id=sensor_id,
            measurement_attribute=measurement_attribute,
        )
    except NotImplementedError:
        # An unsupported terminal must not be displayed as source power.
        return None

    if comparison.sigma is not None and (
        not isinstance(sigma_multiplier, (int, float))
        or isinstance(sigma_multiplier, bool)
        or not np.isfinite(sigma_multiplier)
        or sigma_multiplier < 0
    ):
        return go.Figure(), {"display": "none"}, {"display": "block"}
    quantity = "active power" if measurement_attribute == "p_measured" else "reactive power"
    unit = "W" if measurement_attribute == "p_measured" else "var"
    figure = create_measurement_comparison_figure(
        comparison,
        ComparisonPlotOptions(
            title=f"sym_power_sensor - {quantity} comparison - id={sensor_id}",
            quantity=quantity,
            unit=unit,
            sensor_id=sensor_id,
            comparison_type=ComponentType.sym_power_sensor.value,
            measurement_attribute=measurement_attribute,
        ),
        sigma_multiplier=float(sigma_multiplier)
        if isinstance(sigma_multiplier, (int, float)) and np.isfinite(sigma_multiplier)
        else 2.0,
    )
    controls_style = {"display": "block"} if comparison.sigma is not None else {"display": "none"}
    return figure, {"display": "block"}, controls_style


@callback(
    Output("selection-graph", "figure"),
    Output("selection-graph", "style"),
    Output("sigma-multiplier-controls", "style"),
    Input("selected-selection-cell", "data"),
    Input("sigma-multiplier", "value"),
    Input("cytoscape-graph", "selectedNodeData"),
    Input("cytoscape-graph", "selectedEdgeData"),
    Input("retained-graph-selections", "data"),
    prevent_initial_call=True,
)
def cell_selection_graph(selected_cell, sigma_multiplier, node_data=None, edge_data=None, retained_selections=None):
    """Render the legacy graph and keep controls available for retained comparisons."""
    hidden = {"display": "none"}
    retained_controls = (
        ({"display": "block"} if _has_retained_voltage_comparison(retained_selections) else hidden)
        if retained_selections is not None
        else None
    )

    if not isinstance(selected_cell, dict) or (
        (node_data is not None or edge_data is not None) and not node_data and not edge_data
    ):
        return go.Figure(), hidden, retained_controls or hidden
    try:
        comp_type = ComponentType(selected_cell["group"])
        component_id = int(selected_cell["id"])
        column = selected_cell["column"]
        if not isinstance(column, str):
            return go.Figure(), hidden, retained_controls or hidden
    except (KeyError, TypeError, ValueError):
        return go.Figure(), hidden, retained_controls or hidden
    if comp_type == ComponentType.sym_voltage_sensor and column == "u_measured":
        result = _try_voltage_comparison(component_id, sigma_multiplier)
        if result is not None:
            return (*result[:2], retained_controls if retained_controls is not None else result[2])
    if comp_type == ComponentType.sym_power_sensor and column in ("p_measured", "q_measured"):
        result = _power_comparison_graph(component_id, column, sigma_multiplier)
        if result is not None:
            return (*result[:2], retained_controls if retained_controls is not None else result[2])
    result = _create_attribute_graph(comp_type, component_id, column)
    return (*result[:2], retained_controls if retained_controls is not None else result[2])


def _has_retained_voltage_comparison(retained_selections) -> bool:
    """Enable sigma controls for retained voltage or power comparisons with uncertainty."""
    if not isinstance(retained_selections, list):
        return False
    output_data = get_output_data()
    if output_data is None:
        return False
    update_data = get_update_data()
    for selection in retained_selections:
        if not isinstance(selection, dict):
            continue
        group, column, sensor_id = selection.get("group"), selection.get("column"), selection.get("id")
        if not isinstance(sensor_id, int) or isinstance(sensor_id, bool):
            continue
        try:
            if group == ComponentType.sym_voltage_sensor.value and column == "u_measured":
                if ComponentType.node not in output_data or not _is_supported_node_output(
                    output_data[ComponentType.node]
                ):
                    continue
                comparison = get_symmetric_voltage_comparison(get_grid(), update_data, output_data, sensor_id)
            elif group == ComponentType.sym_power_sensor.value and column in ("p_measured", "q_measured"):
                if ComponentType.source not in output_data or not _is_dense_batch_array(
                    output_data[ComponentType.source]
                ):
                    continue
                comparison = get_symmetric_power_comparison(get_grid(), update_data, output_data, sensor_id, column)
            else:
                continue
        except (ValueError, TypeError, KeyError, AttributeError, NotImplementedError):
            continue
        if comparison.sigma is not None:
            return True
    return False


def _is_supported_node_output(node_output: object) -> bool:
    """Check whether node output supports dense-batch voltage comparison."""
    if not isinstance(node_output, np.ndarray):
        return False

    if node_output.ndim != BATCH_DIMENSIONS:
        return False

    names = node_output.dtype.names
    if names is None or not {"id", "u"}.issubset(names):
        return False

    fields = node_output.dtype.fields
    return fields is not None and fields["u"][0].subdtype is None


def _is_dense_batch_array(component_data: Any) -> bool:
    """Whether the component uses a supported dense batch representation."""
    return isinstance(component_data, np.ndarray) and component_data.ndim == DENSE_BATCH_NDIM


def _require_explicit_ids(component_data: np.ndarray) -> None:
    """Reject dense batch arrays with implicit component IDs."""
    if component_data.dtype.names is None or "id" not in component_data.dtype.names:
        raise NotImplementedError("Batch data without explicit component IDs are not implemented.")


def _voltage_comparison_graph(sensor_id: int, sigma_multiplier: float | None):
    """Render a supported dense voltage comparison, preserving unsupported-data behavior."""
    output_data = get_output_data()
    if output_data is None or ComponentType.node not in output_data:
        return None
    node_output = output_data[ComponentType.node]
    if (
        not _is_dense_batch_array(node_output)
        or node_output.dtype.fields is None
        or "u" not in node_output.dtype.fields
        or node_output.dtype.fields["u"][0].subdtype is not None
    ):
        return None
    _require_explicit_ids(node_output)

    update_data = get_update_data()
    if update_data is not None and ComponentType.sym_voltage_sensor in update_data:
        sensor_updates = update_data[ComponentType.sym_voltage_sensor]
        if not _is_dense_batch_array(sensor_updates):
            return None
        _require_explicit_ids(sensor_updates)

    hidden = {"display": "none"}
    visible = {"display": "block"}
    if (
        not isinstance(sigma_multiplier, (int, float))
        or isinstance(sigma_multiplier, bool)
        or not np.isfinite(sigma_multiplier)
        or sigma_multiplier < 0
    ):
        return go.Figure(), hidden, visible

    try:
        comparison = get_symmetric_voltage_comparison(
            grid=get_grid(),
            update_data=update_data,
            output_data=output_data,
            sensor_id=sensor_id,
        )
        figure = _create_voltage_comparison_figure(comparison, sensor_id, float(sigma_multiplier))
    except (ValueError, TypeError, KeyError, AttributeError):
        return go.Figure(), hidden, visible
    return figure, visible, visible


def _try_voltage_comparison(sensor_id: int, sigma_multiplier: float | None):
    """Compatibility entry point for integrated retained-graph rendering."""
    return _voltage_comparison_graph(sensor_id, sigma_multiplier)


def _create_attribute_graph(comp_type: ComponentType, component_id: int, column: str):
    """Render a standard attribute graph without requiring a current network selection."""
    hidden = {"display": "none"}
    x_array, y_array = _get_y_data_for_cell_selection(comp_type, component_id, column)
    if x_array is None or y_array is None:
        return go.Figure(), hidden, hidden
    fig = go.Figure()
    if y_array.ndim == 1:
        fig.add_trace(go.Scatter(x=x_array, y=y_array, mode="lines", line={"width": 2}))
    else:
        for index in range(y_array.shape[1]):
            colour = ["red", "green", "blue"][index % 3]
            fig.add_trace(
                go.Scatter(
                    x=x_array,
                    y=y_array[:, index],
                    mode="lines",
                    line={"width": 2, "color": colour},
                    name=f"{column}_phase_{index}",
                )
            )
    fig.update_layout(
        title=f"{comp_type.value} - {column} - id={component_id}",
        xaxis_title="Scenario Index",
        yaxis_title=column,
        template="plotly_white",
        hovermode="x unified",
        showlegend=False,
    )
    return fig, {"display": "block"}, hidden


@callback(
    Output("retained-graphs-container", "children"),
    Input("retained-graph-selections", "data"),
    Input("sigma-multiplier", "value"),
)
def render_retained_graphs(retained_selections, sigma_multiplier):
    """Render retained selections independently of Cytoscape selection."""
    if not retained_selections:
        return []
    cards = []
    for index, selection in enumerate(retained_selections):
        if not isinstance(selection, dict):
            continue
        if not isinstance(selection.get("group"), str) or not isinstance(selection.get("column"), str):
            continue
        component_id = selection.get("id")
        if not isinstance(component_id, int) or isinstance(component_id, bool):
            continue
        cards.append(_render_retained_graph_card(index, selection, sigma_multiplier))
    return cards


def _render_retained_graph_card(index, selection, sigma_multiplier):
    """Create a retained graph card with a working Remove button."""
    group, component_id, column = selection["group"], selection["id"], selection["column"]
    figure, graph_style, _ = cell_selection_graph(selection, sigma_multiplier)
    title = f"{group} | ID {component_id} | {column}"
    if graph_style.get("display") == "none":
        content = html.P("Graph data unavailable for this selection or the current sigma multiplier is invalid.")
    else:
        content = dcc.Graph(figure=figure, config={"displaylogo": False})
    scenario_range = "Scenario range unavailable"
    if figure.data and figure.data[0].x is not None and len(figure.data[0].x) > 0:
        values = figure.data[0].x
        scenario_range = f"Scenario indices: {values[0]} to {values[-1]}"
    voltage = (
        group == ComponentType.sym_voltage_sensor.value
        and column == "u_measured"
        and graph_style.get("display") == "block"
        and figure.layout.yaxis.title.text == "Voltage (V)"
    )
    unit_label = "Unit: V" if voltage else "Unit: not specified"
    return html.Div(
        [
            html.Div(
                [
                    html.H5(title),
                    html.Button(
                        [
                            html.I(
                                className="fa-solid fa-xmark",
                                style={"marginRight": "8px"},
                            ),
                            "Remove",
                        ],
                        id={"type": "remove-retained-graph", "index": index},
                        n_clicks=0,
                        className="btn btn-outline-danger",
                        title=f"Remove graph for {title}",
                        style={**GRAPH_ACTION_BUTTON_STYLE, "minWidth": "110px"},
                    ),
                ],
                style=GRAPH_ACTION_HEADER_STYLE,
            ),
            html.P(f"{unit_label} | {scenario_range}"),
            content,
        ],
        style={"border": "1px solid #dddddd", "borderRadius": "6px", "padding": "12px", "marginBottom": "15px"},
    )


def _add_attribute_traces(
    fig: go.Figure,
    x_array: np.ndarray,
    y_array: np.ndarray,
    column_id: str,
) -> bool:
    """Add scalar or multi-series traces without assuming exactly three phases."""
    x_values = np.asarray(x_array)
    y_values = np.asarray(y_array)

    if x_values.ndim != 1 or x_values.size == 0:
        return False

    if y_values.ndim == 1:
        if y_values.size != x_values.size:
            return False

        fig.add_trace(
            go.Scatter(
                x=x_values,
                y=y_values,
                mode="lines",
                line={"width": 2},
            )
        )
        return True

    if y_values.ndim != SCALAR_ARRAY_DIMENSIONS or y_values.shape[0] != x_values.size or y_values.shape[1] == 0:
        return False

    for index in range(y_values.shape[1]):
        color = PHASE_COLORS[index % len(PHASE_COLORS)]
        fig.add_trace(
            go.Scatter(
                x=x_values,
                y=y_values[:, index],
                mode="lines",
                line={"width": 2, "color": color},
                name=f"{column_id}_phase_{index}",
            )
        )

    return True


def _get_y_data_for_cell_selection(
    comp_type: ComponentType, pgm_id: int, attr: str
) -> tuple[np.ndarray | None, np.ndarray | None]:
    """Extract an attribute from supported dense update or output data."""
    if attr.startswith(OUTPUT_PREFIX):
        attr = attr.removeprefix(OUTPUT_PREFIX)
        datasets = ((get_output_data(), False),)
    else:
        datasets = ((get_update_data(), True), (get_output_data(), False))

    for dataset, is_update in datasets:
        if dataset is None or comp_type not in dataset:
            continue

        component_data = dataset[comp_type]
        if not _is_dense_batch_array(component_data):
            continue

        names = component_data.dtype.names
        if names is None or "id" not in names or attr not in names:
            continue

        return get_attr_data_from_dataset(dataset, comp_type, attr, pgm_id, grid=get_grid() if is_update else None)

    return None, None
