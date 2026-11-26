# SPDX-FileCopyrightText: Contributors to the Power Grid Model project <powergridmodel@lfenergy.org>
#
# SPDX-License-Identifier: MPL-2.0

"""F15 uncertainty diagnostics within F14's retained-graph workspace."""

from dash import ALL, Input, Output, State, callback, callback_context, dcc, html
from dash.exceptions import PreventUpdate
from power_grid_model import ComponentType

from power_grid_model_ds._core.visualizer.callbacks.uncertainty_callbacks import (
    _get_uncertainty_diagnostic_comparison,
)
from power_grid_model_ds._core.visualizer.graph_action_styles import (
    GRAPH_ACTION_BUTTON_STYLE,
    GRAPH_ACTION_HEADER_STYLE,
)
from power_grid_model_ds._core.visualizer.uncertainty_diagnostic_plot import (
    create_uncertainty_diagnostic_figure,
)


def measurement_key(selection):
    """Use a stable key that distinguishes voltage, active and reactive power."""
    if not isinstance(selection, dict):
        return None
    group, column, sensor_id = (selection.get(k) for k in ("group", "column", "id"))
    supported = {
        ("sym_voltage_sensor", "u_measured"),
        ("sym_power_sensor", "p_measured"),
        ("sym_power_sensor", "q_measured"),
    }
    if (group, column) not in supported or isinstance(sensor_id, bool):
        return None
    try:
        return f"{group}|{int(sensor_id)}|{column}"
    except (TypeError, ValueError, OverflowError):
        return None


def render_diagnostic(figure, graph_style, selection, hidden_diagnostics=None):
    """Build the optional F15 graph below the matching retained F14 graph."""
    key = measurement_key(selection)
    if key is None or key in (hidden_diagnostics or []):
        return []
    comparison = _get_uncertainty_diagnostic_comparison(figure.to_plotly_json(), graph_style, selection)
    if comparison is None:
        # Explain unavailable sigma only when the comparison metadata supplies
        # a documented diagnostic status; do not infer validity from missing data.
        meta = getattr(figure.layout, "meta", None)
        if isinstance(meta, dict):
            messages = {
                "sigma_missing": "Normalized residual unavailable: measurement sigma is missing.",
                "sigma_nonfinite": "Normalized residual unavailable: no finite sigma values.",
            }
            message = messages.get(meta.get("uncertainty_diagnostic_status"))
            if message:
                return [html.P(message, role="status")]
        return []
    try:
        diagnostic = create_uncertainty_diagnostic_figure(
            comparison,
            title=f"Normalized residual — {key.replace('|', ' / ')}",
        )
    except ValueError:
        return []
    return [
        html.Div(
            [
                html.H6("Normalized residual"),
                html.Button(
                    [html.I(className="fa-solid fa-xmark", style={"marginRight": "8px"}), "Remove normalized residual"],
                    id={"type": "remove-retained-uncertainty", "key": key},
                    n_clicks=0,
                    className="btn btn-outline-danger",
                    style=GRAPH_ACTION_BUTTON_STYLE,
                    title="Remove this normalized residual graph without removing the measurement graph",
                ),
            ],
            style=GRAPH_ACTION_HEADER_STYLE,
        ),
        dcc.Graph(figure=diagnostic, config={"displaylogo": False}),
    ]


def render_retained_graph_card(index, selection, figure, graph_style, hidden_diagnostics=None):
    """Create a retained graph card with a working Remove button."""
    diagnostic_content = render_diagnostic(figure, graph_style, selection, hidden_diagnostics)
    title = f"{selection['group']} | ID {selection['id']} | {selection['column']}"
    remove_label = (
        "Remove measurement + normalized residual"
        if any(isinstance(item, dcc.Graph) for item in diagnostic_content)
        else "Remove"
    )
    if graph_style.get("display") == "none":
        content = html.P(
            "Graph data unavailable for this selection or the current sigma multiplier is invalid.",
        )
    else:
        key = measurement_key(selection)
        if key is not None and isinstance(figure.layout.meta, dict) and "sigma" in figure.layout.meta:
            content = dcc.Graph(
                id={"type": "retained-sigma-comparison", "key": key},
                figure=figure,
                config={"displaylogo": False},
            )
        else:
            content = dcc.Graph(figure=figure, config={"displaylogo": False})
    scenario_range = "Scenario range unavailable"
    if figure.data and figure.data[0].x is not None and len(figure.data[0].x) > 0:
        scenario_range = f"Scenario indices: {figure.data[0].x[0]} to {figure.data[0].x[-1]}"
    voltage = (
        selection["group"] == ComponentType.sym_voltage_sensor.value
        and selection["column"] == "u_measured"
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
                            remove_label,
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
            html.Div(
                diagnostic_content,
                id={
                    "type": "retained-uncertainty-content",
                    "key": measurement_key(selection),
                },
            )
            if diagnostic_content
            else html.Div(style={"display": "none"}),
        ],
        style={
            "border": "1px solid #dddddd",
            "borderRadius": "6px",
            "padding": "12px",
            "marginBottom": "15px",
        },
    )


@callback(
    Output("retained-uncertainty-hidden", "data"),
    Input({"type": "remove-retained-uncertainty", "key": ALL}, "n_clicks"),
    Input("clear-retained-graphs", "n_clicks"),
    Input("selected-selection-cell", "data"),
    State("retained-uncertainty-hidden", "data"),
    prevent_initial_call=True,
)
def update_hidden_diagnostics(_clicks, _clear_clicks, _selected_cell, hidden):
    """Remove only the diagnostic; allow reselection to restore it."""
    triggered = callback_context.triggered_id
    if triggered == "clear-retained-graphs":
        return []
    if triggered == "selected-selection-cell":
        # Re-selecting a measurement restores its diagnostic when available.
        key = measurement_key(_selected_cell)
        if key is None or key not in (hidden or []):
            raise PreventUpdate
        return [item for item in hidden if item != key]
    if not isinstance(triggered, dict) or triggered.get("type") != "remove-retained-uncertainty":
        raise PreventUpdate
    if not callback_context.triggered or not callback_context.triggered[0].get("value"):
        raise PreventUpdate
    key = triggered.get("key")
    if not isinstance(key, str):
        raise PreventUpdate
    return list(dict.fromkeys([*(hidden or []), key]))
