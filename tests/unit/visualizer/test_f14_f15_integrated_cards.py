# SPDX-FileCopyrightText: Contributors to the Power Grid Model project <powergridmodel@lfenergy.org>
#
# SPDX-License-Identifier: MPL-2.0

"""Regression checks for the single-entry F14/F15 retained workspace."""

from dash import dcc, html
from plotly import graph_objects as go

from power_grid_model_ds._core.visualizer.callbacks import (
    element_selection as es,
    retained_uncertainty_integration as ri,
)


def _selection(sensor_id=101, column="u_measured", group="sym_voltage_sensor"):
    return {"group": group, "id": sensor_id, "column": column}


def _figure():
    return go.Figure(data=[go.Scatter(x=[0, 1], y=[230, 231])])


def test_one_entry_contains_measurement_then_uncertainty(monkeypatch):
    """Only one calculation and one enclosing card per retained selection."""
    calls = []

    def render(selection, multiplier):
        calls.append((selection, multiplier))
        return _figure(), {"display": "block"}, {}

    monkeypatch.setattr(es, "cell_selection_graph", render)
    monkeypatch.setattr(
        ri,
        "render_diagnostic",
        lambda *_args: [html.H6("Uncertainty-relative discrepancy"), dcc.Graph(figure=_figure())],
    )
    selection = _selection()
    cards = es.render_retained_graphs([selection], 2.0)
    assert len(cards) == 1
    assert calls == [(selection, 2.0)]
    card = cards[0]
    assert isinstance(card.children[2], dcc.Graph)
    diagnostic = card.children[3]
    assert any(isinstance(item, dcc.Graph) for item in diagnostic.children)


def test_hidden_uncertainty_preserves_measurement(monkeypatch):
    monkeypatch.setattr(es, "cell_selection_graph", lambda *_args: (_figure(), {"display": "block"}, {}))
    monkeypatch.setattr(
        ri,
        "render_diagnostic",
        lambda _fig, _style, sel, hidden: [] if ri.measurement_key(sel) in hidden else [dcc.Graph(figure=_figure())],
    )
    selection = _selection()
    key = ri.measurement_key(selection)
    cards = es.render_retained_graphs([selection], 2.0, [key])
    assert len(cards) == 1
    assert isinstance(cards[0].children[2], dcc.Graph)
    assert cards[0].children[3].style == {"display": "none"}
    assert es.render_retained_graphs([], 2.0, []) == []


def test_power_p_and_q_have_distinct_keys():
    p_key = ri.measurement_key(_selection(910003, "p_measured", "sym_power_sensor"))
    q_key = ri.measurement_key(_selection(910003, "q_measured", "sym_power_sensor"))
    assert p_key != q_key
