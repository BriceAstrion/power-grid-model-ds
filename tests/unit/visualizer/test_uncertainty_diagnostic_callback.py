# SPDX-FileCopyrightText: Contributors to the Power Grid Model project <powergridmodel@lfenergy.org>
#
# SPDX-License-Identifier: MPL-2.0

"""Tests for uncertainty diagnostic visualizer callbacks."""

import numpy as np
import pytest
from power_grid_model import ComponentType

from power_grid_model_ds._core.visualizer.callbacks.element_selection import (
    update_uncertainty_diagnostic_graph,
)
from power_grid_model_ds._core.visualizer.comparison_plot import (
    ComparisonPlotOptions,
    create_measurement_comparison_figure,
)
from power_grid_model_ds._core.visualizer.measurement_comparison import (
    MeasurementComparison,
)


@pytest.fixture
def comparison():
    return MeasurementComparison(
        scenario_indices=np.array([0, 1, 2]),
        measured=np.array([230.0, 235.0, 230.0]),
        estimated=np.array([229.0, 231.0, 228.0]),
        sigma=np.array([2.0, 3.0, 2.0]),
    )


def create_comparison_figure(
    comparison,
    comparison_type=ComponentType.sym_voltage_sensor.value,
    measurement_attribute=None,
):
    """Create a serialized comparison figure with diagnostic metadata."""
    options = ComparisonPlotOptions(
        title="Measurement comparison",
        quantity="voltage",
        unit="V",
        sensor_id=101,
        comparison_type=comparison_type,
        measurement_attribute=measurement_attribute,
    )

    return create_measurement_comparison_figure(
        comparison,
        options,
    ).to_dict()


def create_selected_cell(
    comparison_type=ComponentType.sym_voltage_sensor.value,
    column="u_measured",
    sensor_id=101,
):
    """Create the selected measurement cell."""
    return {
        "group": comparison_type,
        "id": sensor_id,
        "column": column,
    }


def test_renders_voltage_uncertainty_diagnostic(comparison):
    figure = create_comparison_figure(comparison)
    selected_cell = create_selected_cell()

    diagnostic, style = update_uncertainty_diagnostic_graph(
        figure,
        {"display": "block"},
        selected_cell,
    )

    assert style == {"display": "block"}
    assert len(diagnostic.data) == 1

    np.testing.assert_array_equal(
        diagnostic.data[0].x,
        [0, 1, 2],
    )

    np.testing.assert_allclose(
        diagnostic.data[0].y,
        [0.5, 4.0 / 3.0, 1.0],
    )


def test_renders_power_uncertainty_diagnostic(comparison):
    comparison_type = ComponentType.sym_power_sensor.value

    figure = create_comparison_figure(
        comparison,
        comparison_type=comparison_type,
        measurement_attribute="p_measured",
    )

    selected_cell = create_selected_cell(
        comparison_type=comparison_type,
        column="p_measured",
    )

    diagnostic, style = update_uncertainty_diagnostic_graph(
        figure,
        {"display": "block"},
        selected_cell,
    )

    assert style == {"display": "block"}
    assert len(diagnostic.data) == 1


def test_hides_diagnostic_when_comparison_graph_is_hidden(comparison):
    figure = create_comparison_figure(comparison)

    diagnostic, style = update_uncertainty_diagnostic_graph(
        figure,
        {"display": "none"},
        create_selected_cell(),
    )

    assert style == {"display": "none"}
    assert len(diagnostic.data) == 0


def test_hides_diagnostic_when_sensor_does_not_match(comparison):
    figure = create_comparison_figure(comparison)

    diagnostic, style = update_uncertainty_diagnostic_graph(
        figure,
        {"display": "block"},
        create_selected_cell(sensor_id=999),
    )

    assert style == {"display": "none"}
    assert len(diagnostic.data) == 0


def test_hides_diagnostic_when_measurement_attribute_does_not_match(comparison):
    figure = create_comparison_figure(comparison)

    diagnostic, style = update_uncertainty_diagnostic_graph(
        figure,
        {"display": "block"},
        create_selected_cell(column="u_sigma"),
    )

    assert style == {"display": "none"}
    assert len(diagnostic.data) == 0


def test_hides_diagnostic_when_sigma_is_unavailable(comparison):
    comparison_without_sigma = MeasurementComparison(
        scenario_indices=comparison.scenario_indices,
        measured=comparison.measured,
        estimated=comparison.estimated,
        sigma=None,
    )

    figure = create_comparison_figure(comparison_without_sigma)

    diagnostic, style = update_uncertainty_diagnostic_graph(
        figure,
        {"display": "block"},
        create_selected_cell(),
    )

    assert style == {"display": "none"}
    assert len(diagnostic.data) == 0


def test_hides_diagnostic_when_metadata_arrays_have_different_shapes(comparison):
    figure = create_comparison_figure(comparison)

    figure["layout"]["meta"]["estimated"] = [229.0, 231.0]

    diagnostic, style = update_uncertainty_diagnostic_graph(
        figure,
        {"display": "block"},
        create_selected_cell(),
    )

    assert style == {"display": "none"}
    assert len(diagnostic.data) == 0


def test_hides_diagnostic_when_sigma_contains_negative_values(comparison):
    figure = create_comparison_figure(comparison)

    figure["layout"]["meta"]["sigma"] = [2.0, -1.0, 2.0]

    diagnostic, style = update_uncertainty_diagnostic_graph(
        figure,
        {"display": "block"},
        create_selected_cell(),
    )

    assert style == {"display": "none"}
    assert len(diagnostic.data) == 0


def test_hides_diagnostic_when_selection_is_missing(comparison):
    figure = create_comparison_figure(comparison)

    diagnostic, style = update_uncertainty_diagnostic_graph(
        figure,
        {"display": "block"},
        None,
    )

    assert style == {"display": "none"}
    assert len(diagnostic.data) == 0


def test_hides_diagnostic_when_figure_is_invalid():
    diagnostic, style = update_uncertainty_diagnostic_graph(
        None,
        {"display": "block"},
        create_selected_cell(),
    )

    assert style == {"display": "none"}
    assert len(diagnostic.data) == 0
