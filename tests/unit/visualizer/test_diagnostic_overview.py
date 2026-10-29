
# SPDX-FileCopyrightText: Contributors to the Power Grid Model project <powergridmodel@lfenergy.org>
#
# SPDX-License-Identifier: MPL-2.0

"""Tests for the selected-node diagnostic overview."""

from unittest.mock import patch

from dash import html

from power_grid_model_ds._core.model.grids.base import Grid
from power_grid_model_ds._core.visualizer.callbacks.diagnostic_overview import (
    build_calculation_summary,
    update_diagnostic_overview,
)
from power_grid_model_ds._core.visualizer.scenario_status import ScenarioStatus


def _visible_text(component):
    """Collect visible text from nested Dash components."""
    if isinstance(component, (list, tuple)):
        return " ".join(_visible_text(child) for child in component)

    if isinstance(component, str):
        return component

    if isinstance(component, (int, float)):
        return str(component)

    if isinstance(component, html.Div | html.P | html.H6 | html.Hr | html.Li | html.Ul):
        return _visible_text(component.children)

    return ""


def _example_status():
    return ScenarioStatus(
        succeeded_scenarios=frozenset({0}),
        failed_scenarios=frozenset({1}),
        failed_scenario_messages=(
            (1, "Not enough measurements available for state estimation."),
        ),
    )


def test_calculation_summary_without_status():
    """Missing status must not be interpreted as success."""
    summary = build_calculation_summary(None)

    assert "Calculation status unavailable" in _visible_text(summary)
    assert "Succeeded:" not in _visible_text(summary)


def test_calculation_summary_with_failure():
    """Reported successes and failures must be preserved."""
    summary = build_calculation_summary(_example_status())
    text = _visible_text(summary)

    assert "Succeeded: 1" in text
    assert "Failed: 1" in text
    assert "Unknown: not counted" in text
    assert "Scenario 1" in text
    assert "Not enough measurements available" in text


def test_overview_without_selection():
    """Batch calculation status is available even without a selected node."""
    grid = Grid.from_txt("S1 2 12", "2 3 23")

    with (
        patch(
            "power_grid_model_ds._core.visualizer.callbacks.diagnostic_overview.server_state.get_grid",
            return_value=grid,
        ),
        patch(
            "power_grid_model_ds._core.visualizer.callbacks.diagnostic_overview.server_state.get_scenario_status",
            return_value=_example_status(),
        ),
    ):
        result = update_diagnostic_overview(None)

    text = _visible_text(result)

    assert "Select one network node" in text
    assert "Succeeded: 1" in text
    assert "Failed: 1" in text


def test_overview_with_selected_node():
    """Selecting a valid node must display its ID."""
    grid = Grid.from_txt("S1 2 12", "2 3 23")

    with (
        patch(
            "power_grid_model_ds._core.visualizer.callbacks.diagnostic_overview.server_state.get_grid",
            return_value=grid,
        ),
        patch(
            "power_grid_model_ds._core.visualizer.callbacks.diagnostic_overview.server_state.get_scenario_status",
            return_value=None,
        ),
    ):
        result = update_diagnostic_overview([{"id": "1"}])

    text = _visible_text(result)

    assert "Selected node: 1" in text
    assert "Calculation status unavailable" in text


def test_overview_with_multiple_nodes():
    """Multiple selected nodes must not be reported as a single node."""
    grid = Grid.from_txt("S1 2 12", "2 3 23")

    with (
        patch(
            "power_grid_model_ds._core.visualizer.callbacks.diagnostic_overview.server_state.get_grid",
            return_value=grid,
        ),
        patch(
            "power_grid_model_ds._core.visualizer.callbacks.diagnostic_overview.server_state.get_scenario_status",
            return_value=None,
        ),
    ):
        result = update_diagnostic_overview([{"id": "1"}, {"id": "2"}])

    assert "Select one network node at a time" in _visible_text(result)


def test_overview_with_invalid_node():
    """An invalid node ID must not be presented as a valid network node."""
    grid = Grid.from_txt("S1 2 12", "2 3 23")

    with (
        patch(
            "power_grid_model_ds._core.visualizer.callbacks.diagnostic_overview.server_state.get_grid",
            return_value=grid,
        ),
        patch(
            "power_grid_model_ds._core.visualizer.callbacks.diagnostic_overview.server_state.get_scenario_status",
            return_value=None,
        ),
    ):
        result = update_diagnostic_overview([{"id": "invalid"}])

    assert "not a network node" in _visible_text(result)
