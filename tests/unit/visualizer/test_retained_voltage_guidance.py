# SPDX-FileCopyrightText: Contributors to the Power Grid Model project <powergridmodel@lfenergy.org>
#
# SPDX-License-Identifier: MPL-2.0

"""Regression tests for retained voltage-comparison guidance (F10/F11 + F14)."""

from types import SimpleNamespace
from unittest.mock import patch

import numpy as np
import pytest
from power_grid_model import ComponentType, initialize_array

from power_grid_model_ds._core.visualizer.callbacks.element_selection import (
    _has_retained_voltage_comparison,
    cell_selection_graph,
)
from power_grid_model_ds._core.visualizer.layout.selection_output import (
    restart_sigma_guidance_timer,
    update_sigma_guidance_expansion,
    update_voltage_comparison_guidance,
)

MODULE = "power_grid_model_ds._core.visualizer.callbacks.element_selection"
VOLTAGE = {"group": "sym_voltage_sensor", "id": 101, "column": "u_measured"}
OTHER = {"group": "node", "id": 10, "column": "u"}
VISIBLE = {"display": "block"}
HIDDEN = {"display": "none"}


@pytest.fixture
def voltage_data():
    nodes = initialize_array("sym_output", "node", (2, 1))
    nodes["id"] = 10
    nodes["u"][:, 0] = [229.0, 231.0]
    sensor = SimpleNamespace(
        id=np.array([101]),
        measured_object=np.array([10]),
        u_measured=np.array([230.0]),
        u_sigma=np.array([2.0]),
    )
    grid = SimpleNamespace(sym_voltage_sensor=sensor)
    with (
        patch(f"{MODULE}.get_output_data", return_value={ComponentType.node: nodes}),
        patch(f"{MODULE}.get_update_data", return_value=None),
        patch(f"{MODULE}.get_grid", return_value=grid),
    ):
        yield


def test_retained_comparison_available_after_selection_cleared(voltage_data):  # noqa: ARG001
    assert _has_retained_voltage_comparison([VOLTAGE])
    figure, graph_style, controls = cell_selection_graph(None, 2.0, [], [], [VOLTAGE])
    assert len(figure.data) == 0
    assert graph_style == HIDDEN
    assert controls == VISIBLE
    error, note = update_voltage_comparison_guidance(None, 2.0, HIDDEN, controls, [VOLTAGE])
    assert error == HIDDEN
    assert note["display"] == "flex"


def test_other_attribute_does_not_hide_retained_controls(voltage_data):  # noqa: ARG001
    _, _, controls = cell_selection_graph(OTHER, 2.0, retained_selections=[VOLTAGE])
    assert controls == VISIBLE


def test_removing_last_comparison_hides_controls(voltage_data):  # noqa: ARG001
    assert not _has_retained_voltage_comparison([])
    assert not _has_retained_voltage_comparison([OTHER])
    _, _, controls = cell_selection_graph(None, 2.0, retained_selections=[OTHER])
    assert controls == HIDDEN


def test_invalid_multiplier_keeps_controls_and_shows_error(voltage_data):  # noqa: ARG001
    _, _, controls = cell_selection_graph(None, -1, retained_selections=[VOLTAGE])
    assert controls == VISIBLE
    error, note = update_voltage_comparison_guidance(None, -1, HIDDEN, controls, [VOLTAGE])
    assert error["display"] == "flex"
    assert note == HIDDEN


def test_timer_uses_retained_voltage_selection():
    assert restart_sigma_guidance_timer(None, [VOLTAGE]) == (0, False)
    assert update_sigma_guidance_expansion(None, 0, [VOLTAGE]) is True
    assert update_sigma_guidance_expansion(None, 1, [VOLTAGE]) is False
    assert restart_sigma_guidance_timer(None, []) == (0, True)


def test_unsupported_output_does_not_enable_controls():
    with patch(f"{MODULE}.get_output_data", return_value=None):
        assert not _has_retained_voltage_comparison([VOLTAGE])
