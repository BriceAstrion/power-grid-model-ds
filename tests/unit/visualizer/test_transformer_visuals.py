
# SPDX-FileCopyrightText: Contributors to the Power Grid Model project <powergridmodel@lfenergy.org>
#
# SPDX-License-Identifier: MPL-2.0

"""Tests for transformer visual-element mapping."""

from copy import deepcopy

from power_grid_model_ds._core.visualizer.transformer_visuals import (
    add_transformer_visuals,
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


def test_original_elements_are_preserved():
    original = make_elements()
    snapshot = deepcopy(original)

    result = add_transformer_visuals(original)

    assert result[:3] == snapshot
    assert original == snapshot


def test_transformer_visual_elements_are_created():
    result = add_transformer_visuals(make_elements())

    assert len(result) == 8

    symbol = result[3]
    assert symbol["data"]["component_id"] == "10"
    assert symbol["data"]["associated_ids"] == {"transformer": [10]}
    assert symbol["grabbable"] is True

    left = result[4]
    right = result[5]

    assert left["data"]["parent"] == symbol["data"]["id"]
    assert right["data"]["parent"] == symbol["data"]["id"]

    assert left["position"] == {"x": 266, "y": 180}
    assert right["position"] == {"x": 334, "y": 180}


def test_visual_connections_preserve_electrical_endpoints():
    result = add_transformer_visuals(make_elements())

    original_edge = result[2]["data"]
    first_connection = result[6]["data"]
    second_connection = result[7]["data"]

    assert original_edge["source"] == "1"
    assert original_edge["target"] == "2"

    assert first_connection["source"] == "1"
    assert first_connection["target"] == result[4]["data"]["id"]

    assert second_connection["source"] == result[5]["data"]["id"]
    assert second_connection["target"] == "2"


def test_three_winding_transformer_is_not_modified():
    elements = make_elements()
    elements[2]["data"]["group"] = "three_winding_transformer"

    result = add_transformer_visuals(elements)

    assert result == elements


def test_missing_node_positions_leave_graph_unchanged():
    elements = make_elements()
    del elements[0]["position"]

    result = add_transformer_visuals(elements)

    assert result == elements
