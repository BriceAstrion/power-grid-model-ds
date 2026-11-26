# SPDX-FileCopyrightText: Contributors to the Power Grid Model project <powergridmodel@lfenergy.org>
#
# SPDX-License-Identifier: MPL-2.0

"""Availability messages for uncertainty-relative diagnostics."""

import numpy as np
from power_grid_model import ComponentType

from power_grid_model_ds._core.visualizer.callbacks.element_selection import (
    update_uncertainty_diagnostic_status,
)
from power_grid_model_ds._core.visualizer.comparison_plot import (
    ComparisonPlotOptions,
    create_measurement_comparison_figure,
)
from power_grid_model_ds._core.visualizer.measurement_comparison import MeasurementComparison


def _comparison_figure(sigma):
    comparison = MeasurementComparison(
        scenario_indices=np.array([0, 1, 2]),
        measured=np.array([230.0, 231.0, 232.0]),
        estimated=np.array([229.0, 231.0, 230.0]),
        sigma=sigma,
    )
    options = ComparisonPlotOptions(
        title="Voltage comparison",
        quantity="voltage",
        unit="V",
        sensor_id=101,
        comparison_type=ComponentType.sym_voltage_sensor.value,
    )
    return create_measurement_comparison_figure(comparison, options).to_dict()


def _selected_cell(sensor_id=101, column="u_measured"):
    return {
        "group": ComponentType.sym_voltage_sensor.value,
        "id": sensor_id,
        "column": column,
    }


def test_status_when_sigma_is_missing():
    figure = _comparison_figure(None)
    assert len(figure["data"]) == 2  # Measured and calculated are retained.
    message, style = update_uncertainty_diagnostic_status(figure, {"display": "block"}, _selected_cell())
    assert "measurement uncertainty (sigma) is missing" in message
    assert style["display"] == "block"


def test_status_when_no_finite_sigma_exists():
    figure = _comparison_figure(np.array([np.nan, np.inf, np.nan]))
    message, style = update_uncertainty_diagnostic_status(figure, {"display": "block"}, _selected_cell())
    assert "no finite sigma values" in message
    assert style["display"] == "block"


def test_status_hidden_when_sigma_is_available():
    figure = _comparison_figure(np.array([1.0, np.nan, 2.0]))
    assert update_uncertainty_diagnostic_status(figure, {"display": "block"}, _selected_cell()) == (
        "",
        {"display": "none"},
    )


def test_status_hidden_for_other_sensor_or_attribute():
    figure = _comparison_figure(None)
    for selected in (_selected_cell(sensor_id=999), _selected_cell(column="u_sigma")):
        assert update_uncertainty_diagnostic_status(figure, {"display": "block"}, selected) == ("", {"display": "none"})


def test_status_hidden_for_hidden_or_invalid_graph():
    figure = _comparison_figure(None)
    assert update_uncertainty_diagnostic_status(figure, {"display": "none"}, _selected_cell()) == (
        "",
        {"display": "none"},
    )
    assert update_uncertainty_diagnostic_status(None, {"display": "block"}, _selected_cell()) == (
        "",
        {"display": "none"},
    )
