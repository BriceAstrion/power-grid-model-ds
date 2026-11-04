# SPDX-FileCopyrightText: Contributors to the Power Grid Model project <powergridmodel@lfenergy.org>
#
# SPDX-License-Identifier: MPL-2.0

"""Regression tests for electrical colouring and calculation status."""

from unittest.mock import patch

import numpy as np
import pytest
from power_grid_model import ComponentType

from power_grid_model_ds._core.visualizer.callbacks.config import update_appliances
from power_grid_model_ds._core.visualizer.scenario_status import ScenarioStatus


def _make_output():
    node_output = np.zeros(
        (2, 2),
        dtype=[("id", "i4"), ("u_pu", "f8")],
    )
    node_output["id"] = [[1, 2], [1, 2]]
    node_output["u_pu"] = [[0.98, 1.02], [0.96, 1.04]]
    return {ComponentType.node: node_output}


def _make_elements():
    return {
        f"node-{node_id}": {
            "data": {
                "id": f"node-{node_id}",
                "group": "node",
                "associated_ids": {"node": [node_id]},
            }
        }
        for node_id in (1, 2)
    }


def _run_callback(status, scenario_index=1):
    with (
        patch(
            "power_grid_model_ds._core.visualizer.callbacks.config."
            "server_state.get_output_data",
            return_value=_make_output(),
        ),
        patch(
            "power_grid_model_ds._core.visualizer.callbacks.config."
            "server_state.get_scenario_status",
            return_value=status,
        ),
    ):
        return update_appliances(
            show_appliances=False,
            quantity="u_pu",
            scenario_index=scenario_index,
            parsed_elements=_make_elements(),
        )


def _has_electrical_values(elements):
    return any(
        "electrical_value" in element["data"]
        for element in elements
    )


def _legend_text(component):
    """Collect text from a Dash component tree."""
    if component is None:
        return ""

    if isinstance(component, (str, int, float)):
        return str(component)

    if isinstance(component, (list, tuple)):
        return " ".join(_legend_text(child) for child in component)

    return _legend_text(getattr(component, "children", None))


def test_successful_scenario_displays_electrical_values():
    status = ScenarioStatus(
        succeeded_scenarios=frozenset({1}),
        failed_scenarios=frozenset({0}),
    )

    elements, legend = _run_callback(status)

    assert _has_electrical_values(elements)
    assert "Voltage magnitude" in _legend_text(legend)


@pytest.mark.parametrize(
    ("status", "expected_message"),
    [
        (
            ScenarioStatus(
                succeeded_scenarios=frozenset({0}),
                failed_scenarios=frozenset({1}),
            ),
            "calculation failed",
        ),
        (
            ScenarioStatus(
                succeeded_scenarios=frozenset({0}),
                failed_scenarios=frozenset(),
            ),
            "status is unknown",
        ),
    ],
)
def test_unsuccessful_or_unknown_scenario_suppresses_colouring(
    status, expected_message
):
    elements, legend = _run_callback(status)

    assert not _has_electrical_values(elements)
    assert all(
        "electrical_color" not in element["data"]
        for element in elements
    )
    assert expected_message in _legend_text(legend).lower()


def test_missing_status_preserves_colouring_with_warning():
    elements, legend = _run_callback(None)

    assert _has_electrical_values(elements)
    assert "Calculation status was not provided" in _legend_text(legend)


def test_switching_from_successful_to_failed_clears_colouring():
    status = ScenarioStatus(
        succeeded_scenarios=frozenset({0}),
        failed_scenarios=frozenset({1}),
    )

    successful_elements, _ = _run_callback(status, scenario_index=0)
    failed_elements, _ = _run_callback(status, scenario_index=1)

    assert _has_electrical_values(successful_elements)
    assert not _has_electrical_values(failed_elements)
    assert all(
        "electrical_color" not in element["data"]
        for element in failed_elements
    )
