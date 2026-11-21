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
    """Provide scenario-aligned measurement comparison data."""
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
    """Voltage selection displays the expected normalized discrepancy."""
    figure = create_comparison_figure(comparison)
    selected_cell = create_selected_cell()

    diagnostic, style = update_uncertainty_diagnostic_graph(
        figure,
        {"display": "block"},
        selected_cell,
    )

    assert style == {"display": "block"}
    assert bool(diagnostic.data)

    np.testing.assert_array_equal(
        diagnostic.data[0].x,
        [0, 1, 2],
    )
    np.testing.assert_allclose(
        diagnostic.data[0].y,
        [0.5, 4.0 / 3.0, 1.0],
    )


@pytest.mark.parametrize(
    "measurement_attribute",
    ["p_measured", "q_measured"],
)
def test_renders_power_uncertainty_diagnostic(comparison, measurement_attribute):
    """Verify diagnostics for active and reactive power measurements."""
    comparison_type = ComponentType.sym_power_sensor.value

    figure = create_comparison_figure(
        comparison,
        comparison_type=comparison_type,
        measurement_attribute=measurement_attribute,
    )
    selected_cell = create_selected_cell(
        comparison_type=comparison_type,
        column=measurement_attribute,
    )

    diagnostic, style = update_uncertainty_diagnostic_graph(
        figure,
        {"display": "block"},
        selected_cell,
    )

    assert style == {"display": "block"}
    assert bool(diagnostic.data)

    np.testing.assert_array_equal(
        diagnostic.data[0].x,
        [0, 1, 2],
    )
    np.testing.assert_allclose(
        diagnostic.data[0].y,
        [0.5, 4.0 / 3.0, 1.0],
    )

    assert measurement_attribute in diagnostic.layout.title.text


def test_hides_diagnostic_when_comparison_graph_is_hidden(comparison):
    """Hide the diagnostic when the primary comparison is hidden."""
    figure = create_comparison_figure(comparison)

    diagnostic, style = update_uncertainty_diagnostic_graph(
        figure,
        {"display": "none"},
        create_selected_cell(),
    )

    assert style == {"display": "none"}
    assert not diagnostic.data


def test_hides_diagnostic_when_sensor_does_not_match(comparison):
    """Prevent displaying data for a different selected sensor."""
    figure = create_comparison_figure(comparison)

    diagnostic, style = update_uncertainty_diagnostic_graph(
        figure,
        {"display": "block"},
        create_selected_cell(sensor_id=999),
    )

    assert style == {"display": "none"}
    assert not diagnostic.data


def test_hides_diagnostic_when_measurement_attribute_does_not_match(
    comparison,
):
    """Prevent displaying the diagnostic for a different attribute."""
    figure = create_comparison_figure(comparison)

    diagnostic, style = update_uncertainty_diagnostic_graph(
        figure,
        {"display": "block"},
        create_selected_cell(column="u_sigma"),
    )

    assert style == {"display": "none"}
    assert not diagnostic.data


def test_hides_diagnostic_when_sigma_is_unavailable(comparison):
    """Hide the diagnostic when no sigma series exists."""
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
    assert not diagnostic.data


def test_hides_diagnostic_when_metadata_arrays_have_different_shapes(
    comparison,
):
    """Reject comparison metadata with inconsistent array lengths."""
    figure = create_comparison_figure(comparison)
    figure["layout"]["meta"]["estimated"] = [229.0, 231.0]

    diagnostic, style = update_uncertainty_diagnostic_graph(
        figure,
        {"display": "block"},
        create_selected_cell(),
    )

    assert style == {"display": "none"}
    assert not diagnostic.data


def test_hides_diagnostic_when_sigma_contains_negative_values(comparison):
    """Reject negative measurement uncertainty values."""
    figure = create_comparison_figure(comparison)
    figure["layout"]["meta"]["sigma"] = [2.0, -1.0, 2.0]

    diagnostic, style = update_uncertainty_diagnostic_graph(
        figure,
        {"display": "block"},
        create_selected_cell(),
    )

    assert style == {"display": "none"}
    assert not diagnostic.data


def test_hides_diagnostic_when_selection_is_missing(comparison):
    """Hide the diagnostic when no measurement cell is selected."""
    figure = create_comparison_figure(comparison)

    diagnostic, style = update_uncertainty_diagnostic_graph(
        figure,
        {"display": "block"},
        None,
    )

    assert style == {"display": "none"}
    assert not diagnostic.data


def test_hides_diagnostic_when_figure_is_invalid():
    """Handle missing comparison figures safely."""
    diagnostic, style = update_uncertainty_diagnostic_graph(
        None,
        {"display": "block"},
        create_selected_cell(),
    )

    assert style == {"display": "none"}
    assert not diagnostic.data


def test_diagnostic_title_identifies_selected_sensor_and_attribute(comparison):
    """The diagnostic title identifies the selected measurement."""
    figure = create_comparison_figure(comparison)

    diagnostic, style = update_uncertainty_diagnostic_graph(
        figure,
        {"display": "block"},
        create_selected_cell(),
    )

    assert style == {"display": "block"}
    assert "sensor 101" in diagnostic.layout.title.text
    assert "u_measured" in diagnostic.layout.title.text
