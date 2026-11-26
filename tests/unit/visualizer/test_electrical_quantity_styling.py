# SPDX-FileCopyrightText: Contributors to the Power Grid Model project <powergridmodel@lfenergy.org>
#
# SPDX-License-Identifier: MPL-2.0

"""Tests for electrical quantity colour mapping."""

from copy import deepcopy

import pytest

from power_grid_model_ds._core.visualizer.electrical_quantity_styling import (
    MISSING_COLOR,
    apply_electrical_colors,
    clear_electrical_colors,
)


def _node(node_id: int) -> dict:
    return {
        "data": {
            "id": str(node_id),
            "group": "node",
            "associated_ids": {"node": [node_id]},
        },
        "classes": "node",
    }


def _line(line_id: int) -> dict:
    return {
        "data": {
            "id": str(line_id),
            "group": "line",
            "source": "1",
            "target": "2",
            "associated_ids": {"line": [line_id]},
        },
        "classes": "branch",
    }


def test_node_values_are_mapped_by_associated_id():
    elements = [_node(1), _node(2)]

    updated, legend = apply_electrical_colors(
        elements,
        "node",
        {1: 0.95, 2: 1.05},
    )

    assert updated[0]["data"]["electrical_value"] == pytest.approx(0.95)
    assert updated[1]["data"]["electrical_value"] == pytest.approx(1.05)
    assert updated[0]["data"]["electrical_color"] != updated[1]["data"]["electrical_color"]
    assert legend["minimum"] == pytest.approx(0.95)
    assert legend["maximum"] == pytest.approx(1.05)


def test_missing_values_receive_neutral_color():
    updated, legend = apply_electrical_colors(
        [_node(1), _node(2)],
        "node",
        {1: 1.0},
    )

    assert updated[1]["data"]["electrical_color"] == MISSING_COLOR
    assert "electrical_value" not in updated[1]["data"]
    assert legend["missing_count"] == 1


def test_unrelated_component_is_not_colored():
    updated, _ = apply_electrical_colors(
        [_node(1), _line(10)],
        "node",
        {1: 1.0},
    )

    assert "electrical_color" in updated[0]["data"]
    assert "electrical_color" not in updated[1]["data"]


def test_original_elements_are_not_modified():
    elements = [_node(1), _line(10)]
    original = deepcopy(elements)

    apply_electrical_colors(elements, "node", {1: 1.0})

    assert elements == original


def test_topology_and_classes_are_preserved():
    elements = [_line(10)]

    updated, _ = apply_electrical_colors(
        elements,
        "line",
        {10: 80.0},
    )

    assert updated[0]["data"]["source"] == "1"
    assert updated[0]["data"]["target"] == "2"
    assert updated[0]["data"]["id"] == elements[0]["data"]["id"]
    assert updated[0]["data"]["associated_ids"] == elements[0]["data"]["associated_ids"]
    assert set(updated[0]["classes"].split()) == {
        "branch",
        "electrical-heatmap",
    }
    assert elements[0]["classes"] == "branch"


def test_multiple_associated_values_are_rejected():
    element = _node(1)
    element["data"]["associated_ids"]["node"] = [1, 2]

    with pytest.raises(ValueError, match="multiple electrical values"):
        apply_electrical_colors(
            [element],
            "node",
            {1: 0.98, 2: 1.02},
        )


def test_three_winding_transformer_edges_share_component_value():
    elements = [
        {
            "data": {
                "id": f"100_{index}",
                "group": "three_winding_transformer",
                "associated_ids": {"three_winding_transformer": [100]},
            },
            "classes": "branch transformer",
        }
        for index in range(3)
    ]

    updated, legend = apply_electrical_colors(
        elements,
        "three_winding_transformer",
        {100: 72.0},
    )

    assert all(element["data"]["electrical_value"] == 72.0 for element in updated)
    assert len({element["data"]["electrical_color"] for element in updated}) == 1
    assert legend["missing_count"] == 0


def test_colour_scale_uses_expected_endpoints_and_midpoint():
    """Known values must map to the expected rainbow endpoints and midpoint."""
    elements = [_node(1), _node(2), _node(3)]

    updated, legend = apply_electrical_colors(
        elements,
        "node",
        {
            1: 0.95,
            2: 1.00,
            3: 1.05,
        },
    )

    colours = {int(element["data"]["id"]): element["data"]["electrical_color"] for element in updated}

    assert colours[1] == "#6A0DAD"
    assert colours[2] == "#16C685"
    assert colours[3] == "#DC2626"

    assert legend["minimum"] == pytest.approx(0.95)
    assert legend["maximum"] == pytest.approx(1.05)
    assert legend["missing_count"] == 0


def test_equal_values_use_single_midpoint_colour():
    """An equal-value scenario must not produce a false colour range."""
    updated, legend = apply_electrical_colors(
        [_node(1), _node(2)],
        "node",
        {
            1: 1.0,
            2: 1.0,
        },
    )

    assert updated[0]["data"]["electrical_color"] == "#16C685"
    assert updated[1]["data"]["electrical_color"] == "#16C685"
    assert legend["minimum"] == legend["maximum"]


def test_missing_value_does_not_change_colour_range():
    """Missing nodes must not affect the minimum or maximum."""
    updated, legend = apply_electrical_colors(
        [_node(1), _node(2), _node(3)],
        "node",
        {
            1: 0.95,
            3: 1.05,
        },
    )

    assert updated[0]["data"]["electrical_color"] == "#6A0DAD"
    assert updated[1]["data"]["electrical_color"] == MISSING_COLOR
    assert updated[2]["data"]["electrical_color"] == "#DC2626"

    assert legend["minimum"] == pytest.approx(0.95)
    assert legend["maximum"] == pytest.approx(1.05)
    assert legend["missing_count"] == 1


def test_clearing_electrical_colors_restores_original_data():
    original = [_node(1), _node(2)]
    colored, _ = apply_electrical_colors(original, "node", {1: 0.95, 2: 1.05})
    assert clear_electrical_colors(colored) == original


def test_clearing_colors_preserves_topology():
    original = [_node(1), _line(10)]
    for group, values in [("node", {1: 1.0}), ("line", {10: 80.0})]:
        colored, _ = apply_electrical_colors(original, group, values)
        assert clear_electrical_colors(colored) == original


@pytest.mark.parametrize(
    "group",
    [
        "sym_voltage_sensor",
        "asym_voltage_sensor",
        "sym_power_sensor",
        "asym_power_sensor",
        "sym_current_sensor",
        "asym_current_sensor",
    ],
)
def test_sensor_association_mapping(group):
    elements = [_node(1), _node(2), _node(3)]
    elements[0]["data"]["associated_ids"][group] = [403]
    elements[1]["data"]["associated_ids"][group] = [404]
    original = deepcopy(elements)
    updated, summary = apply_electrical_colors(elements, group, {403: -12.0})
    assert updated[0]["data"]["electrical_value"] == -12.0
    assert updated[1]["data"]["electrical_color"] == MISSING_COLOR
    assert "electrical_value" not in updated[1]["data"]
    assert updated[2] == elements[2]
    assert summary == {"minimum": -12.0, "maximum": -12.0, "missing_count": 1}
    assert elements == original
    assert clear_electrical_colors(updated) == original


@pytest.mark.parametrize("ids", [[403, 404, 405], [405, 404, 403]])
def test_multiple_sensor_values_preserve_largest_signed_residual(ids):
    element = _node(1)
    element["data"]["associated_ids"]["sym_voltage_sensor"] = ids
    updated, summary = apply_electrical_colors([element], "sym_voltage_sensor", {403: -35.0, 404: 35.0, 405: 12.0})
    assert updated[0]["data"]["electrical_value"] == -35.0
    assert summary["minimum"] == summary["maximum"] == -35.0


def test_branch_sensor_and_switch_to_node_quantity():
    elements = [_node(1), _line(10)]
    elements[1]["data"]["associated_ids"]["sym_power_sensor"] = [403]
    updated, _ = apply_electrical_colors(elements, "sym_power_sensor", {403: 20.0})
    assert updated[1]["data"]["electrical_value"] == 20.0
    switched, _ = apply_electrical_colors(updated, "node", {1: 1.0})
    assert switched[1] == elements[1]
    assert switched[0]["data"]["electrical_value"] == 1.0


def test_all_sensor_values_missing():
    element = _node(1)
    element["data"]["associated_ids"]["sym_voltage_sensor"] = [403]
    updated, summary = apply_electrical_colors([element], "sym_voltage_sensor", {})
    assert updated[0]["data"]["electrical_color"] == MISSING_COLOR
    assert summary == {"minimum": None, "maximum": None, "missing_count": 1}


def test_ordinary_quantity_does_not_colour_associated_node():
    element = _node(1)
    element["data"]["associated_ids"]["sym_load"] = [403]
    updated, _ = apply_electrical_colors([element], "sym_load", {403: 20.0})
    assert updated == [element]
