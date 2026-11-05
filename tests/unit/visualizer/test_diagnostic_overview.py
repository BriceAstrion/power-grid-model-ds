# SPDX-FileCopyrightText: Contributors to the Power Grid Model project <powergridmodel@lfenergy.org>
#
# SPDX-License-Identifier: MPL-2.0

"""Tests for the selected-node diagnostic overview."""

from unittest.mock import patch

from dash.development.base_component import Component

from power_grid_model_ds._core.model.grids.base import Grid
from power_grid_model_ds._core.visualizer.callbacks.diagnostic_overview import (
    update_diagnostic_overview,
)


def _visible_text(component):
    """Collect visible text from nested Dash components."""
    if isinstance(component, (list, tuple)):
        return " ".join(_visible_text(child) for child in component)

    if isinstance(component, str):
        return component

    if isinstance(component, (int, float)):
        return str(component)

    if isinstance(component, Component):
        return _visible_text(getattr(component, "children", None))

    return ""


def test_overview_without_selection():
    """Prompt for node selection without duplicating calculation status."""
    grid = Grid.from_txt("S1 2 12", "2 3 23")

    with patch(
        "power_grid_model_ds._core.visualizer.callbacks.diagnostic_overview.server_state.get_grid",
        return_value=grid,
    ):
        result = update_diagnostic_overview(None)

    text = _visible_text(result)

    assert "Select a network node to view diagnostics." in text
    assert "Calculation status" not in text
    assert "Succeeded:" not in text
    assert "Failed:" not in text


def test_overview_with_selected_node():
    """Selecting a valid node must display its ID and node diagnostics."""
    grid = Grid.from_txt("S1 2 12", "2 3 23")

    with patch(
        "power_grid_model_ds._core.visualizer.callbacks.diagnostic_overview.server_state.get_grid",
        return_value=grid,
    ):
        result = update_diagnostic_overview([{"id": "1"}])

    text = _visible_text(result)

    assert "Node" in text
    assert "1" in text
    assert "Calculation status" not in text


def test_overview_with_multiple_nodes():
    """Multiple selected nodes must not be reported as a single node."""
    grid = Grid.from_txt("S1 2 12", "2 3 23")

    with patch(
        "power_grid_model_ds._core.visualizer.callbacks.diagnostic_overview.server_state.get_grid",
        return_value=grid,
    ):
        result = update_diagnostic_overview([{"id": "1"}, {"id": "2"}])

    assert "Select one network node at a time" in _visible_text(result)


def test_overview_with_invalid_node():
    """An invalid node ID must not be presented as a valid network node."""
    grid = Grid.from_txt("S1 2 12", "2 3 23")

    with patch(
        "power_grid_model_ds._core.visualizer.callbacks.diagnostic_overview.server_state.get_grid",
        return_value=grid,
    ):
        result = update_diagnostic_overview([{"id": "invalid"}])

    assert "not a network node" in _visible_text(result)
