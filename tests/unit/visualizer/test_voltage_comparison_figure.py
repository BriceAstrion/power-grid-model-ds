# SPDX-FileCopyrightText: Contributors to the Power Grid Model project <powergridmodel@lfenergy.org>
#
# SPDX-License-Identifier: MPL-2.0

import numpy as np
import pytest

from power_grid_model_ds._core.visualizer.measurement_comparison import (
    align_voltage_series,
    VoltageComparison,
)

from power_grid_model_ds._core.visualizer.voltage_comparison_figure import (
    create_voltage_comparison_figure,
)

from power_grid_model_ds._core.visualizer.scenario_status import ScenarioStatus


@pytest.fixture
def comparison():
    return align_voltage_series(
        sensor_id=12001,
        node_id=1001,
        measurement_scenarios=np.array([0, 1]),
        measured=np.array([230.0, 231.0]),
        sigma=np.array([1.0, 2.0]),
        estimate_scenarios=np.array([0, 1]),
        estimated=np.array([229.5, 230.5]),
    )


def test_figure_contains_four_traces(comparison):
    figure = create_voltage_comparison_figure(comparison)

    assert len(figure.data) == 4
    assert figure.data[1].fill == "tonexty"
    assert figure.layout.xaxis.title.text == "Scenario Index"
    assert figure.layout.yaxis.title.text == "Voltage (V)"


def test_figure_uses_three_sigma_by_default(comparison):
    figure = create_voltage_comparison_figure(comparison)

    np.testing.assert_allclose(figure.data[0].y, [227.0, 225.0])
    np.testing.assert_allclose(figure.data[1].y, [233.0, 237.0])


def test_multiplier_changes_only_band_traces(comparison):
    default_figure = create_voltage_comparison_figure(comparison)
    custom_figure = create_voltage_comparison_figure(
        comparison, multiplier=2.0
    )

    np.testing.assert_allclose(custom_figure.data[0].y, [228.0, 227.0])
    np.testing.assert_allclose(custom_figure.data[1].y, [232.0, 235.0])

    for index in (2, 3):
        np.testing.assert_array_equal(
            default_figure.data[index].y,
            custom_figure.data[index].y,
        )

def test_failed_scenario_estimate_is_not_plotted():
    comparison = VoltageComparison(
        sensor_id=12001,
        node_id=1001,
        scenarios=np.array([0, 1, 2, 3]),
        measured=np.array([230.0, 231.0, 232.0, 233.0]),
        estimated=np.array([229.5, 230.5, 231.5, 232.5]),
        sigma=np.array([1.0, 1.0, 1.0, 1.0]),
    )

    status = ScenarioStatus(
        succeeded_scenarios=frozenset({0, 2, 3}),
        failed_scenarios=frozenset({1}),
    )

    figure = create_voltage_comparison_figure(
        comparison,
        scenario_status=status,
    )

    estimate_trace = next(
        trace for trace in figure.data
        if trace.name == "Estimated voltage (succeeded)"
    )

    assert np.isnan(estimate_trace.y[1])
    np.testing.assert_allclose(
        np.asarray(estimate_trace.y)[[0, 2, 3]],
        [229.5, 231.5, 232.5],
    )

    failure_trace = next(
        trace for trace in figure.data
        if trace.name == "State estimation failed"
    )

    assert list(failure_trace.x) == [1]
    assert list(failure_trace.y) == [231.0]


def test_unknown_scenario_is_distinguished_from_success():
    comparison = VoltageComparison(
        sensor_id=12001,
        node_id=1001,
        scenarios=np.array([0, 1, 2]),
        measured=np.array([230.0, 231.0, 232.0]),
        estimated=np.array([229.5, 230.5, 231.5]),
        sigma=np.array([1.0, 1.0, 1.0]),
    )

    status = ScenarioStatus(
        succeeded_scenarios=frozenset({0, 2}),
        failed_scenarios=frozenset(),
    )

    figure = create_voltage_comparison_figure(
        comparison,
        scenario_status=status,
    )

    estimate_trace = next(
        trace for trace in figure.data
        if trace.name == "Estimated voltage (succeeded)"
    )

    assert np.isnan(estimate_trace.y[1])

    unknown_trace = next(
        trace for trace in figure.data
        if trace.name == "Estimated voltage (status unknown)"
    )

    assert list(unknown_trace.x) == [1]
    assert list(unknown_trace.y) == [230.5]


def test_measured_values_and_sigma_bands_remain_available_for_failed_scenarios():
    comparison = VoltageComparison(
        sensor_id=12001,
        node_id=1001,
        scenarios=np.array([0, 1, 2]),
        measured=np.array([230.0, 231.0, 232.0]),
        estimated=np.array([229.5, 230.5, 231.5]),
        sigma=np.array([2.0, 2.0, 2.0]),
    )

    status = ScenarioStatus(
        succeeded_scenarios=frozenset({0, 2}),
        failed_scenarios=frozenset({1}),
    )

    figure = create_voltage_comparison_figure(
        comparison,
        multiplier=3.0,
        scenario_status=status,
    )

    measured_trace = next(
        trace for trace in figure.data
        if trace.name == "Measured voltage"
    )

    np.testing.assert_allclose(measured_trace.y, comparison.measured)
    np.testing.assert_allclose(figure.data[0].y, [224.0, 225.0, 226.0])
    np.testing.assert_allclose(figure.data[1].y, [236.0, 237.0, 238.0])


def test_failed_scenario_with_unavailable_estimate_and_sigma():
    """Show a failure marker without inventing an estimate or sigma band."""
    comparison = VoltageComparison(
        sensor_id=12001,
        node_id=1001,
        scenarios=np.array([0, 1]),
        measured=np.array([10489.37, 10489.37]),
        estimated=np.array([10488.27, np.nan]),
        sigma=np.array([1.0, np.nan]),
    )

    status = ScenarioStatus(
        succeeded_scenarios=frozenset({0}),
        failed_scenarios=frozenset({1}),
    )

    figure = create_voltage_comparison_figure(
        comparison,
        multiplier=3.0,
        scenario_status=status,
    )

    # Valid sigma bands exist only for scenario 0.
    np.testing.assert_allclose(
        figure.data[0].y,
        [10486.37, np.nan],
        equal_nan=True,
    )
    np.testing.assert_allclose(
        figure.data[1].y,
        [10492.37, np.nan],
        equal_nan=True,
    )

    measured_trace = next(
        trace for trace in figure.data
        if trace.name == "Measured voltage"
    )
    np.testing.assert_allclose(
        measured_trace.y,
        [10489.37, 10489.37],
    )

    estimated_trace = next(
        trace for trace in figure.data
        if trace.name == "Estimated voltage (succeeded)"
    )
    np.testing.assert_allclose(
        estimated_trace.y,
        [10488.27, np.nan],
        equal_nan=True,
    )

    failure_trace = next(
        trace for trace in figure.data
        if trace.name == "State estimation failed"
    )

    assert list(failure_trace.x) == [1]
    assert list(failure_trace.y) == [10489.37]