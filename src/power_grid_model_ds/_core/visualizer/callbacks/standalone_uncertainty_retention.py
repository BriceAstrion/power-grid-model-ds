# SPDX-FileCopyrightText: Contributors to the Power Grid Model project <powergridmodel@lfenergy.org>
#
# SPDX-License-Identifier: MPL-2.0

"""Pure standalone F15 retention compatibility helpers.

No Dash callbacks are registered here. The integrated F14 workspace remains
responsible for actual graph retention and diagnostic rendering.
"""

from dash import dcc, html
from power_grid_model import ComponentType

from power_grid_model_ds._core.visualizer.callbacks.uncertainty_callbacks import _matches_comparison_selection


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

    if not isinstance(meta, dict) or not _matches_comparison_selection(meta, selected_cell):
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
        remove_label = "Remove measurement + uncertainty" if has_diagnostic else "Remove"
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
                            html.Strong("Uncertainty-relative discrepancy"),
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
                                    "Remove uncertainty",
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


def hide_active_graphs_when_retained(entries, selected_cell):
    """Avoid duplicating the active pair above its retained workspace entry."""
    identity = _measurement_identity(selected_cell)
    if identity is not None and any(
        isinstance(item, dict) and item.get("key") == identity
        for item in (entries if isinstance(entries, list) else [])
    ):
        return {"display": "none"}
    return {"display": "block"}
