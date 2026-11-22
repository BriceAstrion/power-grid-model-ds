# SPDX-FileCopyrightText: Contributors to the Power Grid Model project <powergridmodel@lfenergy.org>
#
# SPDX-License-Identifier: MPL-2.0

"""Sigma-multiplier behavior in the integrated visualizer callback architecture."""

from unittest.mock import Mock

import numpy as np
import pytest
from dash import dcc
from power_grid_model import ComponentType

from power_grid_model_ds._core.visualizer.callbacks import element_selection
from power_grid_model_ds._core.visualizer.measurement_comparison import (
    MeasurementComparison,
    VoltageComparison,
)


@pytest.fixture
def voltage_comparison():
    return VoltageComparison(
        sensor_id=17,
        node_id=10,
        scenarios=np.array([0, 1, 2]),
        measured=np.array([230.0, 235.0, 230.0]),
        estimated=np.array([229.0, 231.0, 228.0]),
        sigma=np.array([2.0, 3.0, 2.0]),
    )


@pytest.fixture
def power_comparison():
    return MeasurementComparison(
        scenario_indices=np.array([0, 1]),
        measured=np.array([10.0, 10.0]),
        estimated=np.array([9.0, 11.0]),
        sigma=np.array([2.0, 2.0]),
    )


@pytest.fixture
def voltage_data(monkeypatch, voltage_comparison):
    node_output = np.zeros((3, 1), dtype=[("id", "i4"), ("u", "f8")])
    node_output["id"] = 10
    monkeypatch.setattr(
        element_selection,
        "get_output_data",
        Mock(return_value={ComponentType.node: node_output}),
    )
    monkeypatch.setattr(element_selection, "get_update_data", Mock(return_value=None))
    monkeypatch.setattr(element_selection, "get_grid", Mock(return_value=object()))
    monkeypatch.setattr(
        element_selection, "get_symmetric_voltage_comparison", lambda *_args, **_kwargs: voltage_comparison
    )
    return {"group": "sym_voltage_sensor", "id": 17, "column": "u_measured"}


@pytest.fixture
def power_data(monkeypatch, power_comparison):
    source_output = np.zeros((2, 1), dtype=[("id", "i4"), ("p", "f8"), ("q", "f8")])
    source_output["id"] = 10

    monkeypatch.setattr(
        element_selection,
        "get_output_data",
        Mock(return_value={ComponentType.source: source_output}),
    )
    monkeypatch.setattr(element_selection, "get_update_data", Mock(return_value=None))
    monkeypatch.setattr(element_selection, "get_grid", Mock(return_value=object()))
    monkeypatch.setattr(
        element_selection,
        "get_symmetric_power_comparison",
        Mock(return_value=power_comparison),
    )

    return {"group": "sym_power_sensor", "id": 201, "column": "p_measured"}


def _visible_figure(selection, multiplier):
    figure, graph_style, controls_style = element_selection.cell_selection_graph(selection, multiplier)
    assert graph_style == {"display": "block"}
    assert controls_style == {"display": "block"}
    return figure


@pytest.mark.parametrize(
    ("multiplier", "expected_lower", "expected_upper"),
    [
        (0, [230.0, 235.0, 230.0], [230.0, 235.0, 230.0]),
        (2, [226.0, 229.0, 226.0], [234.0, 241.0, 234.0]),
        (4, [222.0, 223.0, 222.0], [238.0, 247.0, 238.0]),
        (0.5, [229.0, 233.5, 229.0], [231.0, 236.5, 231.0]),
    ],
)
def test_voltage_multiplier_recalculates_only_sigma_values(
    voltage_data, voltage_comparison, multiplier, expected_lower, expected_upper
):
    figure = _visible_figure(voltage_data, multiplier)
    np.testing.assert_allclose(figure.data[0].y, expected_lower)
    np.testing.assert_allclose(figure.data[1].y, expected_upper)
    np.testing.assert_array_equal(figure.data[2].y, voltage_comparison.measured)
    np.testing.assert_array_equal(figure.data[3].y, voltage_comparison.estimated)
    assert figure.data[1].name == f"Measurement +/- {multiplier:g} sigma"
    assert figure.layout.meta["sensor_id"] == 17
    assert figure.layout.meta["comparison_type"] == "sym_voltage_sensor"


def test_repeated_voltage_changes_use_original_sigma(voltage_data):
    first = _visible_figure(voltage_data, 2)
    second = _visible_figure(voltage_data, 4)
    np.testing.assert_allclose(first.data[0].y, [226, 229, 226])
    np.testing.assert_allclose(second.data[0].y, [222, 223, 222])
    np.testing.assert_allclose(second.data[1].y, [238, 247, 238])


@pytest.mark.parametrize("invalid", [None, -1, -0.1, float("nan"), float("inf"), -float("inf"), True, "2"])
def test_invalid_voltage_multiplier_hides_graph(voltage_data, invalid):
    figure, graph_style, controls_style = element_selection.cell_selection_graph(voltage_data, invalid)
    assert not figure.data
    assert graph_style == {"display": "none"}
    assert controls_style == {"display": "block"}


def test_missing_voltage_sigma_values_remain_missing(voltage_data, voltage_comparison, monkeypatch):
    comparison = VoltageComparison(
        sensor_id=voltage_comparison.sensor_id,
        node_id=voltage_comparison.node_id,
        scenarios=voltage_comparison.scenarios,
        measured=voltage_comparison.measured,
        estimated=voltage_comparison.estimated,
        sigma=np.array([2.0, np.nan, 2.0]),
    )
    monkeypatch.setattr(element_selection, "get_symmetric_voltage_comparison", lambda *_args, **_kwargs: comparison)
    figure = _visible_figure(voltage_data, 2)
    assert np.isnan(figure.data[0].y[1])
    assert np.isnan(figure.data[1].y[1])
    np.testing.assert_allclose([figure.data[0].y[0], figure.data[0].y[2]], [226, 226])


@pytest.mark.parametrize(
    ("attribute", "measured", "sigma"),
    [
        ("p_measured", [10.0, 10.0], [2.0, 2.0]),
        ("q_measured", [5.0, 5.0], [1.0, 1.0]),
    ],
)
def test_power_multiplier_recalculates_bands(power_data, monkeypatch, attribute, measured, sigma):
    comparison = MeasurementComparison(
        scenario_indices=np.array([0, 1]),
        measured=np.array(measured),
        estimated=np.array([9.0, 11.0]),
        sigma=np.array(sigma),
    )
    monkeypatch.setattr(element_selection, "get_symmetric_power_comparison", lambda *_args, **_kwargs: comparison)
    selection = {**power_data, "column": attribute}
    figure = _visible_figure(selection, 2)
    np.testing.assert_allclose(figure.data[0].y, np.array(measured) - 2 * np.array(sigma))
    np.testing.assert_allclose(figure.data[1].y, np.array(measured) + 2 * np.array(sigma))
    np.testing.assert_array_equal(figure.data[2].y, comparison.measured)
    np.testing.assert_array_equal(figure.data[3].y, comparison.estimated)
    assert figure.data[1].name == "Measurement +/- 2 sigma"
    assert figure.layout.meta["measurement_attribute"] == attribute


@pytest.mark.parametrize("invalid", [None, -1, float("nan"), float("inf"), True, "2"])
def test_invalid_power_multiplier_hides_graph(power_data, invalid):
    figure, graph_style, controls_style = element_selection.cell_selection_graph(power_data, invalid)
    assert not figure.data
    assert graph_style == {"display": "none"}
    assert controls_style == {"display": "block"}


def test_power_without_sigma_hides_controls(power_data, monkeypatch, power_comparison):
    comparison = MeasurementComparison(
        scenario_indices=power_comparison.scenario_indices,
        measured=power_comparison.measured,
        estimated=power_comparison.estimated,
        sigma=None,
    )
    monkeypatch.setattr(element_selection, "get_symmetric_power_comparison", lambda *_args, **_kwargs: comparison)
    figure, graph_style, controls_style = element_selection.cell_selection_graph(power_data, 2)
    assert graph_style == {"display": "block"}
    assert controls_style == {"display": "none"}
    assert len(figure.data) == 2


def test_power_with_sigma_shows_controls(power_data):
    figure, graph_style, controls_style = element_selection.cell_selection_graph(power_data, 2)
    assert graph_style == {"display": "block"}
    assert controls_style == {"display": "block"}
    assert len(figure.data) == 4


def test_non_comparison_selection_hides_controls(monkeypatch):
    monkeypatch.setattr(
        element_selection, "_create_attribute_graph", lambda *_args: (None, {"display": "block"}, {"display": "none"})
    )
    _, _, controls_style = element_selection.cell_selection_graph({"group": "node", "id": 10, "column": "u"}, 2)
    assert controls_style == {"display": "none"}


def test_retained_voltage_graph_responds_to_multiplier(voltage_data):
    cards = element_selection.render_retained_graphs([voltage_data], 4)
    assert len(cards) == 1
    graph = cards[0].children[2]
    assert isinstance(graph, dcc.Graph)
    np.testing.assert_allclose(graph.figure.data[0].y, [222, 223, 222])


def test_retained_power_graph_responds_to_multiplier(power_data):
    cards = element_selection.render_retained_graphs([power_data], 4)
    assert len(cards) == 1
    graph = cards[0].children[2]
    assert isinstance(graph, dcc.Graph)
    np.testing.assert_allclose(graph.figure.data[0].y, [2, 2])


def test_retained_comparison_keeps_controls_visible(voltage_data):
    _, _, controls_style = element_selection.cell_selection_graph(None, 2, retained_selections=[voltage_data])
    assert controls_style == {"display": "block"}
