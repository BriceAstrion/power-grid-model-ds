# SPDX-FileCopyrightText: Contributors to the Power Grid Model project <powergridmodel@lfenergy.org>
#
# SPDX-License-Identifier: MPL-2.0

"""Regression tests for generator presentation elements."""

from copy import deepcopy

import pytest

from power_grid_model_ds._core.visualizer.generator_constants import (
    GENERATOR_CONNECTION_CLASS,
    GENERATOR_OPEN_CLASS,
    GENERATOR_ORIGINAL_HIDDEN_CLASS,
    GENERATOR_SYMBOL_CLASS,
    GENERATOR_SYMBOL_GROUP,
)
from power_grid_model_ds._core.visualizer.generator_visuals import add_generator_visuals
from power_grid_model_ds._core.visualizer.layout.cytoscape_styling import DEFAULT_STYLESHEET
from power_grid_model_ds._core.visualizer.layout.generator_rendering import prepare_generator_rendering
from power_grid_model_ds._core.visualizer.layout.load_rendering import prepare_load_rendering


def _elements(group: str = "sym_gen", classes: str = "generating_appliance") -> list[dict]:
    return [
        {
            "data": {"id": "n1", "group": "node"},
            "position": {"x": 0, "y": 0},
        },
        {
            "data": {
                "id": "g1_ghost_node",
                "group": f"{group}_ghost_node",
                "associated_ids": {group: [123]},
            },
            "position": {"x": 0, "y": 0},
            "classes": "appliance_ghost_node",
            "selectable": False,
        },
        {
            "data": {
                "id": "g1",
                "group": group,
                "source": "n1",
                "target": "g1_ghost_node",
                "associated_ids": {group: [123]},
            },
            "classes": classes,
        },
    ]


def _symbol(elements: list[dict]) -> dict:
    return next(item for item in elements if item["data"].get("group") == GENERATOR_SYMBOL_GROUP)


def _connection(elements: list[dict]) -> dict:
    return next(item for item in elements if item["data"].get("visual_only") and "source" in item["data"])


@pytest.mark.parametrize("group", ["sym_gen", "asym_gen"])
def test_generator_adds_symbol_and_connection(group):
    original = _elements(group=group)
    result = prepare_generator_rendering(original)

    assert len(original) == 3
    assert len(result) == 5

    symbol = _symbol(result)
    connection = _connection(result)

    assert symbol["data"]["id"] == "__visual_generator__g1__symbol"
    assert symbol["data"]["component_id"] == "g1"
    assert symbol["data"]["component_type"] == group
    assert symbol["data"]["associated_ids"] == {group: [123]}
    assert symbol["data"]["visual_only"] is True
    assert symbol["position"] == {"x": 0, "y": -100}
    assert symbol["selectable"] is True
    assert symbol["grabbable"] is True
    assert GENERATOR_SYMBOL_CLASS in symbol["classes"]

    assert connection["data"]["id"] == "__visual_generator__g1__connection"
    assert connection["data"]["source"] == "n1"
    assert connection["data"]["target"] == symbol["data"]["id"]
    assert connection["selectable"] is False
    assert GENERATOR_CONNECTION_CLASS in connection["classes"]


def test_original_generator_is_preserved_and_hidden():
    original = _elements()
    snapshot = deepcopy(original)

    result = prepare_generator_rendering(original)

    assert original == snapshot
    assert result[2]["data"] == original[2]["data"]
    assert GENERATOR_ORIGINAL_HIDDEN_CLASS in result[2]["classes"].split()
    assert GENERATOR_ORIGINAL_HIDDEN_CLASS not in original[2]["classes"]


def test_source_component_is_not_converted():
    original = _elements(group="source")
    assert prepare_generator_rendering(original) == original


def test_generator_without_positioned_node_is_unchanged():
    original = _elements()
    del original[0]["position"]

    assert prepare_generator_rendering(original) == original


def test_generator_with_missing_source_node_is_unchanged():
    original = _elements()
    original[2]["data"]["source"] = "missing"

    assert prepare_generator_rendering(original) == original


def test_original_generator_is_not_hidden_when_conversion_fails():
    original = _elements()
    del original[0]["position"]

    result = prepare_generator_rendering(original)

    assert GENERATOR_ORIGINAL_HIDDEN_CLASS not in result[2]["classes"]


def test_open_generator_connection_has_open_class():
    original = _elements(classes="generating_appliance open_generating_appliance")

    result = prepare_generator_rendering(original)
    connection = _connection(result)

    assert GENERATOR_OPEN_CLASS in connection["classes"].split()


def test_closed_generator_connection_has_no_open_class():
    result = prepare_generator_rendering(_elements())

    assert GENERATOR_OPEN_CLASS not in _connection(result)["classes"].split()


def test_generator_visual_ids_cannot_collide():
    original = _elements()
    original.append(
        {
            "data": {"id": "__visual_generator__g1__symbol"},
            "position": {"x": 500, "y": 0},
        }
    )

    with pytest.raises(ValueError, match="Visual element ID collision"):
        add_generator_visuals(original)


def test_generator_and_load_visuals_coexist():
    original = _elements()
    original.extend(
        [
            {
                "data": {
                    "id": "l1_ghost_node",
                    "group": "sym_load_ghost_node",
                    "associated_ids": {"sym_load": [456]},
                },
                "position": {"x": 0, "y": 0},
                "classes": "appliance_ghost_node",
            },
            {
                "data": {
                    "id": "l1",
                    "group": "sym_load",
                    "source": "n1",
                    "target": "l1_ghost_node",
                    "associated_ids": {"sym_load": [456]},
                },
                "classes": "loading_appliance",
            },
        ]
    )

    result = prepare_generator_rendering(prepare_load_rendering(original))

    groups = [item["data"].get("group") for item in result]

    assert groups.count("generator_symbol") == 1
    assert groups.count("load_symbol") == 1

    generator = next(item for item in result if item["data"].get("id") == "g1")
    load = next(item for item in result if item["data"].get("id") == "l1")

    assert GENERATOR_ORIGINAL_HIDDEN_CLASS in generator["classes"]
    assert "load-original-hidden" in load["classes"]


def test_rebuilding_from_original_does_not_accumulate_visuals():
    original = _elements()

    first = prepare_generator_rendering(original)
    second = prepare_generator_rendering(original)

    assert first == second
    assert len(first) == 5
    assert len(second) == 5


def test_generator_styles_are_registered():
    rules = {rule["selector"]: rule["style"] for rule in DEFAULT_STYLESHEET}

    assert rules[f".{GENERATOR_ORIGINAL_HIDDEN_CLASS}"]["display"] == "none"

    symbol = rules[f".{GENERATOR_SYMBOL_CLASS}"]
    assert symbol["shape"] == "ellipse"
    assert symbol["background-opacity"] == 0
    assert symbol["border-width"] == 0

    connection = rules[f".{GENERATOR_CONNECTION_CLASS}"]
    assert connection["opacity"] == 0
    assert connection["target-arrow-shape"] == "none"
