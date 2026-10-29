# SPDX-FileCopyrightText: Contributors to the Power Grid Model project <powergridmodel@lfenergy.org>
#
# SPDX-License-Identifier: MPL-2.0

from typing import Any
from urllib.parse import quote

import numpy as np
import plotly.graph_objects as go
from dash import ALL, MATCH, Input, Output, State, callback, callback_context, dcc, html
from dash.exceptions import PreventUpdate
from power_grid_model import ComponentType

from power_grid_model_ds._core.model.grids.base import Grid
from power_grid_model_ds._core.visualizer.grid_utils import get_attr_data_from_dataset
from power_grid_model_ds._core.visualizer.layout.selection_output import SELECTION_OUTPUT_HTML
from power_grid_model_ds._core.visualizer.server_state import get_grid, get_output_data, get_update_data
from power_grid_model_ds.arrays import IdArray

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


@callback(
    Output("selection-output", "children"),
    Input("cytoscape-graph", "selectedNodeData"),
    Input("cytoscape-graph", "selectedEdgeData"),
)
def display_selected_elements(node_data: list[dict[str, Any]], edge_data: list[dict[str, Any]]):
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
        panels.append(_to_data_table(data, group))
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
                    html.Span(attribute, style={"overflowWrap": "anywhere"}),
                    html.Div(
                        [
                            html.Button(
                                html.Img(src=_FILTER_ICON, alt="", style={"width": "16px", "height": "16px"}),
                                id={"type": "attribute-filter-toggle", "group": group, "attribute": attribute},
                                n_clicks=0,
                                type="button",
                                title=f"Filter {attribute}",
                                **{"aria-label": f"Filter {attribute}"},
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


def _to_data_table(array_data: IdArray, group: str) -> html.Div:
    """Render attribute rows with an independent filter for every attribute."""
    records: list[dict[str, Any]] = []
    for entry in array_data:
        record: dict[str, Any] = {}
        for attribute in array_data.columns:
            value = entry[attribute]
            record[attribute] = value.item() if value.ndim == 1 else value.tolist().pop()
        records.append(record)

    attribute_rows = [_attribute_row(attribute, group) for attribute in array_data.columns]

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


def _attribute_value_button(record, attribute, group, include_id):
    value = record.get(attribute)
    label = "—" if value is None else str(value)
    if include_id:
        label = f"ID {record['id']}: {label}"
    if value is None:
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
        _attribute_value_button(record, output_id["attribute"], output_id["group"], include_id)
        for record in matching
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


@callback(
    Output("selection-graph", "figure"),
    Output("selection-graph", "style"),
    Input({"type": "attribute-plot", "group": ALL, "attribute": ALL, "pgm_id": ALL}, "n_clicks"),
    prevent_initial_call=True,
)
def cell_selection_graph(_):
    """Plot the selected component attribute when scenario data exists."""
    triggered_id = callback_context.triggered_id
    if not isinstance(triggered_id, dict) or triggered_id.get("type") != "attribute-plot":
        return go.Figure(), {"display": "none"}
    if not callback_context.triggered or not callback_context.triggered[0].get("value"):
        return go.Figure(), {"display": "none"}

    group = triggered_id["group"]
    pgm_id = int(triggered_id["pgm_id"])
    attribute = triggered_id["attribute"]
    x_array, y_array = _get_y_data_for_cell_selection(ComponentType(group), pgm_id, attribute)
    if x_array is None or y_array is None:
        return go.Figure(), {"display": "none"}

    fig = go.Figure()
    if y_array.ndim == 1:
        fig.add_trace(go.Scatter(x=x_array, y=y_array, mode="lines", line={"width": 2}))
    else:
        for i, color in zip(range(y_array.shape[1]), ["red", "green", "blue"], strict=True):
            fig.add_trace(
                go.Scatter(
                    x=x_array,
                    y=y_array[:, i],
                    mode="lines",
                    line={"width": 2, "color": color},
                    name=f"{attribute}_phase_{i}",
                )
            )

    fig.update_layout(
        title=f"{group} - {attribute} - id={pgm_id}",
        xaxis_title="Scenario Index",
        yaxis_title=attribute,
        template="plotly_white",
        hovermode="x unified",
        showlegend=False,
    )
    return fig, {"display": "block"}


def _get_y_data_for_cell_selection(
    comp_type: ComponentType, pgm_id: int, attr: str
) -> tuple[np.ndarray | None, np.ndarray | None]:
    """Extract data from update_data or output_data."""
    update_data = get_update_data()
    if update_data is not None and comp_type in update_data:
        update_names = update_data[comp_type].dtype.names
        if update_names is not None and attr in update_names:
            return get_attr_data_from_dataset(update_data, comp_type, attr, pgm_id)
    output_data = get_output_data()
    if output_data is not None and comp_type in output_data:
        output_names = output_data[comp_type].dtype.names
        if output_names is not None and attr in output_names:
            return get_attr_data_from_dataset(output_data, comp_type, attr, pgm_id)
    return None, None
