# SPDX-FileCopyrightText: Contributors to the Power Grid Model project <powergridmodel@lfenergy.org>
#
# SPDX-License-Identifier: MPL-2.0
"""Standalone F15 paired measurement and uncertainty retention tests."""

import json

import numpy as np
import plotly.graph_objects as go
from plotly.utils import PlotlyJSONEncoder
from power_grid_model import ComponentType

from power_grid_model_ds._core.visualizer.callbacks.element_selection import (
    _measurement_identity,
    _update_retained_measurements,
    hide_active_graphs_when_retained,
    render_retained_uncertainty_diagnostics,
)


def selected(sensor_id=101, attribute="u_measured", group=ComponentType.sym_voltage_sensor.value):
    return {"group": group, "id": sensor_id, "column": attribute}


def comparison(cell):
    return {
        "layout": {
            "meta": {
                "comparison_type": cell["group"],
                "sensor_id": cell["id"],
                "measurement_attribute": cell["column"],
            }
        },
        "data": [{"y": [230, 231]}],
    }


def diagnostic(cell):
    fig = go.Figure(data=[go.Scatter(y=np.array([1.0, 0.5]))])
    fig.update_layout(
        meta={
            "retention_group": cell["group"],
            "retention_sensor_id": cell["id"],
            "retention_attribute": cell["column"],
        }
    )
    return json.loads(json.dumps(fig, cls=PlotlyJSONEncoder))


def capture(entries, cell, diagnostic_figure=None, diagnostic_style=None):
    return _update_retained_measurements(
        entries,
        action="capture",
        selected_cell=cell,
        comparison=comparison(cell),
        comparison_style={"display": "block"},
        diagnostic=diagnostic(cell) if diagnostic_figure is None else diagnostic_figure,
        diagnostic_style={"display": "block"} if diagnostic_style is None else diagnostic_style,
    )


def test_two_voltage_sensors_retain_both_graph_pairs():
    first, second = selected(101), selected(102)
    entries = capture(capture([], first), second)
    assert len(entries) == 2
    assert all(isinstance(item["comparison"], dict) for item in entries)
    assert all(isinstance(item["diagnostic"], dict) for item in entries)
    style, cards = render_retained_uncertainty_diagnostics(entries)
    assert style["display"] == "block"
    assert len(cards) == 2
    assert hide_active_graphs_when_retained(entries, second) == {"display": "none"}


def test_power_p_and_q_are_distinct_measurements():
    p = selected(103, "p_measured", ComponentType.sym_power_sensor.value)
    q = selected(103, "q_measured", ComponentType.sym_power_sensor.value)
    entries = capture(capture([], p), q)
    assert len(entries) == 2
    assert entries[0]["key"] != entries[1]["key"]


def test_removing_measurement_cascades_to_its_diagnostic():
    entries = capture(capture([], selected(101)), selected(102))
    entries = _update_retained_measurements(entries, action="remove-measurement", key=entries[0]["key"])
    assert len(entries) == 1
    assert entries[0]["key"] == _measurement_identity(selected(102))
    assert entries[0]["diagnostic"] is not None


def test_removing_uncertainty_preserves_measurement_and_reselection_restores_it():
    cell = selected(101)
    entries = capture([], cell)
    entries = _update_retained_measurements(entries, action="remove-diagnostic", key=entries[0]["key"])
    assert len(entries) == 1
    assert entries[0]["comparison"] is not None
    assert entries[0]["diagnostic"] is None
    entries = capture(entries, cell)
    assert len(entries) == 1
    assert entries[0]["diagnostic"] is not None


def test_missing_sigma_keeps_measurement_without_diagnostic():
    cell = selected(101)
    entries = capture([], cell, diagnostic_style={"display": "none"})
    assert len(entries) == 1
    assert entries[0]["diagnostic"] is None


def test_reselection_does_not_duplicate_and_clear_all_removes_everything():
    cell = selected(101)
    entries = capture(capture([], cell), cell)
    assert len(entries) == 1
    assert _update_retained_measurements(entries, action="clear") == []


def test_rejects_mismatched_comparison_identity():
    cell = selected(101)
    other = selected(102)
    entries = _update_retained_measurements(
        [],
        action="capture",
        selected_cell=cell,
        comparison=comparison(other),
        comparison_style={"display": "block"},
        diagnostic=diagnostic(cell),
        diagnostic_style={"display": "block"},
    )
    assert entries == []
