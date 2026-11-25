# SPDX-FileCopyrightText: Contributors to the Power Grid Model project <powergridmodel@lfenergy.org>
#
# SPDX-License-Identifier: MPL-2.0

"""Tests for electrical quantity labels and units."""

import pytest

from power_grid_model_ds._core.visualizer.electrical_quantity_legend import (
    build_electrical_legend,
)


@pytest.mark.parametrize(
    ("quantity", "component", "expected_title"),
    [
        ("u_pu", "node", "Voltage magnitude (p.u.)"),
        ("u", "node", "Voltage magnitude (V)"),
        ("u_angle", "node", "Voltage angle (rad)"),
        ("p", "sym_load", "Active power (W)"),
        ("q", "sym_load", "Reactive power (var)"),
        ("i", "source", "Current magnitude (A)"),
        ("s", "source", "Apparent power (VA)"),
        ("pf", "source", "Power factor"),
        ("loading", "line", "Relative loading"),
        ("p_from", "line", "Active power - from side (W)"),
        ("q_to", "line", "Reactive power - to side (var)"),
        ("i_from", "transformer", "Current magnitude - from side (A)"),
        ("s_to", "transformer", "Apparent power - to side (VA)"),
        (
            "p_1",
            "three_winding_transformer",
            "Active power - winding 1 (W)",
        ),
        (
            "loading_2",
            "three_winding_transformer",
            "Loading - winding 2",
        ),
        ("u_residual_over_sigma", "sym_voltage_sensor", "Voltage magnitude discrepancy / sigma"),
        ("p_residual_over_sigma", "sym_power_sensor", "Active power discrepancy / sigma"),
        ("q_residual_over_sigma", "sym_power_sensor", "Reactive power discrepancy / sigma"),
        ("u_residual", "sym_voltage_sensor", "Voltage magnitude residual (V)"),
        ("u_angle_residual", "sym_voltage_sensor", "Voltage angle residual (rad)"),
        ("p_residual", "sym_power_sensor", "Active power residual (W)"),
        ("q_residual", "sym_power_sensor", "Reactive power residual (var)"),
        ("i_residual", "sym_current_sensor", "Current magnitude residual (A)"),
        ("i_angle_residual", "sym_current_sensor", "Current angle residual (rad)"),
    ],
)
def test_electrical_quantity_title(quantity, component, expected_title):
    """Known attributes display their electrical meaning and unit."""
    legend = build_electrical_legend(
        scenario_index=2,
        summary={
            "minimum": 0.1,
            "maximum": 0.9,
            "missing_count": 0,
        },
        quantity=quantity,
        component_group=component,
    )

    assert legend.children[0].children == f"{expected_title} - Scenario 3"


def test_unknown_attribute_preserves_generic_support():
    """Unknown output fields remain supported without an invented unit."""
    legend = build_electrical_legend(
        scenario_index=0,
        summary={
            "minimum": 1.0,
            "maximum": 2.0,
            "missing_count": 0,
        },
        quantity="future_attribute",
        component_group="node",
    )

    assert legend.children[0].children == "future_attribute - Scenario 1"


def test_loading_values_are_not_converted_to_percentages():
    """Loading retains the original PGM ratio."""
    legend = build_electrical_legend(
        scenario_index=0,
        summary={
            "minimum": 0.2,
            "maximum": 0.8,
            "missing_count": 0,
        },
        quantity="loading",
        component_group="line",
    )

    statistics = legend.children[1].children

    assert statistics[0].children[1].children == "0.2000"
    assert statistics[1].children[1].children == "0.8000"
