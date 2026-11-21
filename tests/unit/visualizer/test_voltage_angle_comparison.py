# SPDX-FileCopyrightText: Contributors to the Power Grid Model project <powergridmodel@lfenergy.org>
#
# SPDX-License-Identifier: MPL-2.0

"""Voltage-angle comparison: scenario alignment, wraparound, and plot metadata."""

import numpy as np
import pytest
from power_grid_model import ComponentType, initialize_array

from power_grid_model_ds import Grid
from power_grid_model_ds._core.visualizer.comparison_plot import (
    ComparisonPlotOptions,
    create_measurement_comparison_figure,
)
from power_grid_model_ds._core.visualizer.measurement_comparison import (
    get_symmetric_voltage_angle_comparison,
    wrapped_angle_difference,
)
from power_grid_model_ds.arrays import NodeArray, SymVoltageSensorArray


def test_wrapped_angle_difference_boundary():
    measured = np.deg2rad(np.array([179.0, -179.0, 0.0, np.nan]))
    estimated = np.deg2rad(np.array([-179.0, 179.0, 0.0, 0.0]))
    residual = wrapped_angle_difference(measured, estimated)
    np.testing.assert_allclose(np.rad2deg(residual[:3]), [-2.0, 2.0, 0.0], atol=1e-12)
    assert np.isnan(residual[3])
    assert wrapped_angle_difference(np.array([np.pi]), np.array([0.0]))[0] == pytest.approx(np.pi)
    assert wrapped_angle_difference(np.array([-np.pi]), np.array([0.0]))[0] == pytest.approx(np.pi)


def test_wrapped_angle_difference_rejects_shape_mismatch():
    with pytest.raises(ValueError, match="matching shapes"):
        wrapped_angle_difference(np.array([0.0]), np.array([0.0, 1.0]))


def test_angle_comparison_uses_base_and_scenario_updates():
    grid = Grid.empty()
    nodes = NodeArray.zeros(1)
    nodes["id"] = [10]
    nodes["u_rated"] = [230.0]
    grid.append(nodes)
    sensors = SymVoltageSensorArray.zeros(1)
    sensors["id"] = [101]
    sensors["measured_object"] = [10]
    sensors["u_angle_measured"] = [0.25]
    sensors["u_sigma"] = [2.0]
    grid.append(sensors)

    node_output = initialize_array("sym_output", "node", (2, 1))
    node_output["id"] = 10
    node_output["u_angle"][:, 0] = [0.2, 0.3]
    updates = initialize_array("update", "sym_voltage_sensor", (2, 1))
    updates["id"] = 101
    updates["u_angle_measured"][0, 0] = 0.4
    # The second scenario is intentionally left unset (NaN sentinel).
    comparison = get_symmetric_voltage_angle_comparison(
        grid,
        {ComponentType.sym_voltage_sensor: updates},
        {ComponentType.node: node_output},
        sensor_id=101,
    )
    assert comparison is not None
    np.testing.assert_array_equal(comparison.scenario_indices, [0, 1])
    np.testing.assert_allclose(comparison.measured, [0.4, 0.25])
    np.testing.assert_allclose(comparison.estimated, [0.2, 0.3])
    assert comparison.sigma is None

    figure = create_measurement_comparison_figure(
        comparison,
        ComparisonPlotOptions(
            title="Angle comparison",
            quantity="voltage angle",
            unit="rad",
            sensor_id=101,
            comparison_type="sym_voltage_sensor",
            measurement_attribute="u_angle_measured",
            angular=True,
        ),
    )
    assert len(figure.data) == 2
    assert all(trace.mode == "markers" for trace in figure.data)
    assert "sigma" not in figure.layout.meta
    assert figure.layout.meta["measurement_attribute"] == "u_angle_measured"
    np.testing.assert_allclose(figure.data[0].customdata, [0.2, -0.05])
