# SPDX-FileCopyrightText: Contributors to the Power Grid Model project <powergridmodel@lfenergy.org>
#
# SPDX-License-Identifier: MPL-2.0

import numpy as np
import pytest

from power_grid_model_ds._core.visualizer.measurement_comparison import (
    align_voltage_series,
)
from power_grid_model_ds._core.visualizer.voltage_comparison_figure import (
    create_voltage_comparison_figure,
)


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
    assert figure.layout.xaxis.tickmode == "linear"
    assert figure.layout.xaxis.tick0 == 0
    assert figure.layout.xaxis.dtick == 1


def test_figure_uses_three_sigma_by_default(comparison):
    figure = create_voltage_comparison_figure(comparison)

    np.testing.assert_allclose(figure.data[0].y, [227.0, 225.0])
    np.testing.assert_allclose(figure.data[1].y, [233.0, 237.0])


def test_multiplier_changes_only_band_traces(comparison):
    default_figure = create_voltage_comparison_figure(comparison)
    custom_figure = create_voltage_comparison_figure(comparison, multiplier=2.0)

    np.testing.assert_allclose(custom_figure.data[0].y, [228.0, 227.0])
    np.testing.assert_allclose(custom_figure.data[1].y, [232.0, 235.0])

    for index in (2, 3):
        np.testing.assert_array_equal(
            default_figure.data[index].y,
            custom_figure.data[index].y,
        )


def test_figure_preserves_measured_and_estimated_values(comparison):
    figure = create_voltage_comparison_figure(comparison)

    assert len(figure.data) == 4
    assert figure.data[2].name == "Measured voltage"
    assert figure.data[3].name == "Estimated voltage"

    np.testing.assert_allclose(
        figure.data[2].y,
        comparison.measured,
    )
    np.testing.assert_allclose(
        figure.data[3].y,
        comparison.estimated,
    )

    assert figure.data[3].connectgaps is False
    assert "result validity" in figure.layout.annotations[0].text
