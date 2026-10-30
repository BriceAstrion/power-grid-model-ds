# SPDX-FileCopyrightText: Contributors to the Power Grid Model project <powergridmodel@lfenergy.org>
#
# SPDX-License-Identifier: MPL-2.0

"""Tests for two-winding transformer rendering preparation."""

from copy import deepcopy

from power_grid_model_ds._core.visualizer.layout.transformer_rendering import (
    prepare_transformer_rendering,
)


def make_elements():
    return [
        {
            "data": {"id": "1", "associated_ids": {"node": [1]}},
            "position": {"x": 100, "y": 180},
        },
        {
            "data": {"id": "2", "associated_ids": {"node": [2]}},
            "position": {"x": 500, "y": 180},
        },
        {
            "data": {
                "id": "10",
                "source": "1",
                "target": "2",
                "group": "transformer",
                "associated_ids": {"transformer": [10]},
            },
            "classes": "branch transformer",
        },
    ]


def test_original_electrical_data_is_preserved():
    elements = make_elements()
    original = deepcopy(elements)

    result = prepare_transformer_rendering(elements)

    assert elements == original

    transformer = result[2]
    assert transformer["data"] == original[2]["data"]
    assert transformer["data"]["source"] == "1"
    assert transformer["data"]["target"] == "2"
    assert transformer["data"]["associated_ids"] == {"transformer": [10]}


def test_only_replaced_transformer_edge_is_hidden():
    result = prepare_transformer_rendering(make_elements())

    assert "transformer-original-hidden" in result[2]["classes"]
    assert "transformer-original-hidden" not in result[0].get("classes", "")
    assert "transformer-original-hidden" not in result[1].get("classes", "")


def test_visual_symbol_preserves_component_selection_mapping():
    result = prepare_transformer_rendering(make_elements())

    symbols = [
        element
        for element in result
        if element["data"].get("group") == "transformer_symbol"
    ]

    assert len(symbols) == 1
    assert symbols[0]["data"]["component_id"] == "10"
    assert symbols[0]["data"]["associated_ids"] == {"transformer": [10]}
    assert symbols[0]["selectable"] is True
    assert symbols[0]["grabbable"] is True


def test_unpositioned_transformer_is_not_hidden():
    elements = make_elements()
    del elements[0]["position"]

    result = prepare_transformer_rendering(elements)

    assert result == elements


def test_three_winding_transformer_remains_unchanged():
    elements = make_elements()
    elements[2]["data"]["group"] = "three_winding_transformer"

    result = prepare_transformer_rendering(elements)

    assert result == elements
