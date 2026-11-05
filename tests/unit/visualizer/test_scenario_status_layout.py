# SPDX-FileCopyrightText: Contributors to the Power Grid Model project <powergridmodel@lfenergy.org>
#
# SPDX-License-Identifier: MPL-2.0

from unittest.mock import patch

from dash import html
from dash.development.base_component import Component

from power_grid_model_ds._core.model.grids.base import Grid
from power_grid_model_ds._core.visualizer.app import get_app_layout
from power_grid_model_ds._core.visualizer.layout.scenario_status import get_scenario_status_html
from power_grid_model_ds._core.visualizer.scenario_status import ScenarioStatus


def _get_text(component):
    """Collect text from nested Dash components."""
    if isinstance(component, str):
        return component

    if isinstance(component, (list, tuple)):
        return " ".join(_get_text(child) for child in component)

    if isinstance(component, Component):
        return _get_text(component.children)

    return ""


def _find_components(component, component_type):
    """Find nested Dash components of the requested type."""
    if isinstance(component, component_type):
        yield component

    if isinstance(component, Component):
        yield from _find_components(
            getattr(component, "children", None),
            component_type,
        )
    elif isinstance(component, (list, tuple)):
        for child in component:
            yield from _find_components(child, component_type)


def _assert_status_counts(panel, succeeded, failed):
    """Verify that each reported count has the correct outcome label."""
    cards = [
        component
        for component in _find_components(panel, html.Div)
        if isinstance(getattr(component, "children", None), list)
        and len(component.children) == 2
        and isinstance(component.children[1], html.Div)
        and component.children[1].children in ("succeeded", "failed")
    ]

    assert len(cards) == 2

    counts = {}
    for card in cards:
        label = card.children[1].children
        counts[label] = _get_text(card.children[0]).strip()

    assert counts == {
        "succeeded": str(succeeded),
        "failed": str(failed),
    }


def test_status_panel_without_status():
    panel = get_scenario_status_html(None)

    assert panel.id == "scenario-status"
    assert "Output validity has not been verified" in _get_text(panel)


def test_status_panel_with_successful_scenarios():
    status = ScenarioStatus(
        succeeded_scenarios=frozenset({0, 1}),
        failed_scenarios=frozenset(),
    )

    panel = get_scenario_status_html(status)

    _assert_status_counts(panel, succeeded=2, failed=0)
    assert not list(_find_components(panel, html.Details))


def test_status_panel_with_failed_scenario():
    status = ScenarioStatus(
        succeeded_scenarios=frozenset({0, 2}),
        failed_scenarios=frozenset({1}),
        failed_scenario_messages=((1, "Solver did not converge"),),
    )

    panel = get_scenario_status_html(status)
    content = _get_text(panel)

    _assert_status_counts(panel, succeeded=2, failed=1)
    assert "Scenario 1: Solver did not converge" in content
    assert len(list(_find_components(panel, html.Details))) == 1
    assert len(list(_find_components(panel, html.Summary))) == 1


def test_status_panel_with_unreported_scenarios():
    status = ScenarioStatus(
        succeeded_scenarios=frozenset({0}),
        failed_scenarios=frozenset(),
    )

    content = _get_text(get_scenario_status_html(status))

    assert "The status of any other scenarios is unknown" in content


def test_app_layout_includes_scenario_status_panel():
    status = ScenarioStatus(
        succeeded_scenarios=frozenset({0}),
        failed_scenarios=frozenset({1}),
        failed_scenario_messages=((1, "Solver did not converge"),),
    )

    with patch(
        "power_grid_model_ds._core.visualizer.server_state.get_scenario_status",
        return_value=status,
    ):
        layout = get_app_layout(Grid.empty())

    panels = [
        component
        for component in _find_components(layout, html.Section)
        if getattr(component, "id", None) == "scenario-status"
    ]
    left_panels = [
        component
        for component in _find_components(layout, html.Div)
        if getattr(component, "id", None) == "workspace-left-panel"
    ]

    assert len(panels) == 1
    assert len(left_panels) == 1

    sidebar_status_panels = [
        component
        for component in _find_components(left_panels[0], html.Section)
        if getattr(component, "id", None) == "scenario-status"
    ]

    assert len(sidebar_status_panels) == 1
    assert sidebar_status_panels[0] is panels[0]
    assert "Scenario 1: Solver did not converge" in _get_text(panels[0])
