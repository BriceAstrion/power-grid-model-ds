# SPDX-FileCopyrightText: Contributors to the Power Grid Model project <powergridmodel@lfenergy.org>
#
# SPDX-License-Identifier: MPL-2.0

"""F15 uncertainty diagnostics and compatibility helpers for selection graphs.

Imported by element_selection to register Dash callbacks at application startup.
"""

import math

import numpy as np
import plotly.graph_objects as go
from dash import Input, Output, Patch, callback
from dash.exceptions import PreventUpdate
from power_grid_model import ComponentType

from power_grid_model_ds._core.visualizer.measurement_comparison import MeasurementComparison
from power_grid_model_ds._core.visualizer.uncertainty_diagnostic_plot import create_uncertainty_diagnostic_figure

# F15 uncertainty diagnostic integration; sigma input remains managed by the integrated workspace.

_SIGMA_CONTROL_HIDDEN = {"display": "none"}
_SIGMA_CONTROL_VISIBLE = {"display": "block", "marginBottom": "12px"}


def update_sigma_multiplier_visibility(figure, graph_style):
    """Compatibility helper; the integrated workspace controls sigma visibility."""
    visible = (
        isinstance(figure, dict)
        and isinstance(graph_style, dict)
        and graph_style.get("display") != "none"
        and _has_sigma_comparison_metadata(figure)
    )
    return _SIGMA_CONTROL_VISIBLE if visible else _SIGMA_CONTROL_HIDDEN


def _has_sigma_comparison_metadata(figure: dict) -> bool:
    """Identify four-trace voltage or power comparisons with sigma metadata."""
    layout = figure.get("layout")
    if not isinstance(layout, dict):
        return False
    meta = layout.get("meta")
    if not isinstance(meta, dict):
        return False
    traces = figure.get("data")
    return (
        meta.get("comparison_type")
        in (
            ComponentType.sym_voltage_sensor.value,
            ComponentType.sym_power_sensor.value,
        )
        and isinstance(traces, list)
        and len(traces) == len(("lower", "upper", "measured", "calculated"))
        and "sigma" in meta
        and "measured" in meta
    )


def _matches_comparison_selection(meta: dict, selected_cell: dict) -> bool:
    """Ensure the selected sensor and quantity match the displayed figure."""
    comparison_type = meta.get("comparison_type")
    if comparison_type not in (
        ComponentType.sym_voltage_sensor.value,
        ComponentType.sym_power_sensor.value,
    ):
        return False
    expected_column = (
        "u_measured" if comparison_type == ComponentType.sym_voltage_sensor.value else meta.get("measurement_attribute")
    )
    if expected_column not in ("u_measured", "p_measured", "q_measured"):
        return False
    try:
        return (
            selected_cell["group"] == comparison_type
            and selected_cell["column"] == expected_column
            and int(selected_cell["id"]) == int(meta["sensor_id"])
        )
    except (KeyError, TypeError, ValueError):
        return False


def update_voltage_sigma_bands(multiplier, figure, selected_cell):
    """Update uncertainty bands without fetching data or rerunning state estimation."""
    if isinstance(multiplier, bool) or not isinstance(multiplier, (int, float)):
        raise PreventUpdate
    if not math.isfinite(multiplier) or multiplier < 0:
        raise PreventUpdate
    if not isinstance(figure, dict) or not isinstance(selected_cell, dict):
        raise PreventUpdate

    layout = figure.get("layout")
    if not isinstance(layout, dict):
        raise PreventUpdate
    meta = layout.get("meta")
    if not isinstance(meta, dict) or not _matches_comparison_selection(meta, selected_cell):
        raise PreventUpdate

    traces = figure.get("data")
    if not isinstance(traces, list) or len(traces) != len(("lower", "upper", "measured", "calculated")):
        raise PreventUpdate
    if not all(isinstance(trace, dict) for trace in traces):
        raise PreventUpdate

    try:
        sigma = np.asarray(meta["sigma"], dtype=float)
        measured = np.asarray(meta["measured"], dtype=float)
    except (KeyError, TypeError, ValueError) as exc:
        raise PreventUpdate from exc

    if sigma.ndim != 1 or measured.ndim != 1 or measured.shape != sigma.shape:
        raise PreventUpdate
    if np.any(np.isfinite(sigma) & (sigma < 0)):
        raise PreventUpdate

    lower = measured - multiplier * sigma
    upper = measured + multiplier * sigma

    return create_sigma_band_patch(lower, upper, multiplier)


def create_sigma_band_patch(lower: np.ndarray, upper: np.ndarray, multiplier: float) -> Patch:
    """Build the shared partial update for comparison bounds and legend."""
    patch = Patch()
    patch["data"][0]["y"] = lower.tolist()
    patch["data"][1]["y"] = upper.tolist()
    patch["data"][1]["name"] = f"Measurement +/- {multiplier:g} sigma"
    return patch


def validate_sigma_multiplier(value):
    """Provide accessible feedback while keeping the last valid bands."""
    valid = not isinstance(value, bool) and isinstance(value, (int, float)) and math.isfinite(value) and value >= 0
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
        or not _has_sigma_comparison_metadata(figure)
        or not _has_uncertainty_diagnostic_metadata(meta)
        or not _matches_comparison_selection(meta, selected_cell)
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
                f" — {selected_cell['group']} / {selected_cell['column']}"
                f" / sensor {selected_cell['id']}"
            ),
        )
    except ValueError:
        return go.Figure(), {"display": "none"}

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
    if not isinstance(meta, dict) or not _matches_comparison_selection(meta, selected_cell):
        return hidden

    message = _UNCERTAINTY_STATUS_MESSAGES.get(meta.get("uncertainty_diagnostic_status"))
    if message is None:
        return hidden
    return message, {"display": "block", "color": "#694100", "marginTop": "8px"}
