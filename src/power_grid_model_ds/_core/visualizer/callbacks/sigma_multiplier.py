# SPDX-FileCopyrightText: Contributors to the Power Grid Model project <powergridmodel@lfenergy.org>
# SPDX-License-Identifier: MPL-2.0

"""Sigma multiplier validation and comparison band updates."""

import math

import numpy as np
from dash import Patch
from dash.exceptions import PreventUpdate
from power_grid_model import ComponentType

_MEASUREMENT_IDENTITY_PART_COUNT = 3


def has_sigma_comparison_metadata(figure: dict) -> bool:
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


def matches_comparison_selection(meta: dict, selected_cell: dict) -> bool:
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


def is_valid_sigma_multiplier(value):
    """Check that a multiplier is finite and non-negative."""
    return not isinstance(value, bool) and isinstance(value, (int, float)) and math.isfinite(value) and value >= 0


def update_voltage_sigma_bands(multiplier, figure, selected_cell):
    """Update uncertainty bands without fetching data or rerunning state estimation."""
    if not is_valid_sigma_multiplier(multiplier):
        raise PreventUpdate
    if not isinstance(figure, dict) or not isinstance(selected_cell, dict):
        raise PreventUpdate

    layout = figure.get("layout")
    if not isinstance(layout, dict):
        raise PreventUpdate
    meta = layout.get("meta")
    if not isinstance(meta, dict) or not matches_comparison_selection(meta, selected_cell):
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

    finite_sigma = np.where(np.isfinite(sigma), sigma, np.nan)
    lower = measured - multiplier * finite_sigma
    upper = measured + multiplier * finite_sigma

    patch = Patch()
    patch["data"][0]["y"] = lower.tolist()
    patch["data"][1]["y"] = upper.tolist()
    patch["data"][1]["name"] = f"Measurement +/- {multiplier:g} sigma"
    return patch


def update_retained_sigma_bands(retained, multiplier):
    """Update comparison bands without modifying the original figures."""
    if not is_valid_sigma_multiplier(multiplier):
        return retained

    for item in retained:
        figure = item.get("comparison")
        if not isinstance(figure, dict) or not has_sigma_comparison_metadata(figure):
            continue

        identity = item["key"].split("|")
        if len(identity) != _MEASUREMENT_IDENTITY_PART_COUNT:
            continue

        group, sensor_id, attribute = identity

        selected_cell = {
            "group": group,
            "id": sensor_id,
            "column": attribute,
        }

        try:
            patch = update_voltage_sigma_bands(multiplier, figure, selected_cell)
        except PreventUpdate:
            continue

        # Copy only the modified containers, not the diagnostic or source arrays.
        traces = list(figure["data"])
        traces[0] = dict(traces[0])
        traces[1] = dict(traces[1])

        for operation in patch.to_plotly_json()["operations"]:
            _, index, field = operation["location"]
            traces[index][field] = operation["params"]["value"]

        item["comparison"] = {**figure, "data": traces}

    return retained
