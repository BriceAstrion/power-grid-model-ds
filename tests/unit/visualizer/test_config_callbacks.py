# SPDX-FileCopyrightText: Contributors to the Power Grid Model project <powergridmodel@lfenergy.org>
#
# SPDX-License-Identifier: MPL-2.0

"""Regression tests for transformer visibility in configuration callbacks."""

from copy import deepcopy

import pytest
from dash.exceptions import PreventUpdate

from power_grid_model_ds._core.visualizer.callbacks.config import update_appliances
from power_grid_model_ds._core.visualizer.layout.header_config import LayoutOptions


def _parsed_elements():
    elements = [
        {"data": {"id": "n1", "group": "node"}, "position": {"x": 0, "y": 0}},
        {"data": {"id": "n2", "group": "node"}, "position": {"x": 300, "y": 0}},
        {
            "data": {
                "id": "t1",
                "group": "transformer",
                "source": "n1",
                "target": "n2",
                "associated_ids": {"transformer": [123]},
            },
            "classes": "transformer",
        },
        {
            "data": {
                "id": "load1",
                "group": "sym_load",
                "source": "n2",
                "target": "load_ghost",
            },
        },
        {"data": {"id": "load_ghost", "group": "sym_load_ghost_node"}},
    ]
    return {element["data"]["id"]: element for element in elements}


def _groups(elements):
    return [element["data"].get("group") for element in elements]


@pytest.mark.parametrize("show_appliances", [False, True])
def test_transformer_symbol_preserved_for_both_appliance_states(show_appliances):
    elements, state = update_appliances(show_appliances, _parsed_elements(), {"name": LayoutOptions.PRESET.value})

    assert state is show_appliances
    assert _groups(elements).count("transformer_symbol") == 1

    transformer = next(element for element in elements if element["data"]["id"] == "t1")
    assert "transformer-original-hidden" in transformer["classes"]
    assert ("sym_load" in _groups(elements)) is show_appliances


def test_repeated_toggle_does_not_duplicate_transformer():
    parsed_elements = _parsed_elements()
    original = deepcopy(parsed_elements)

    for show in (True, False, True, False):
        elements, state = update_appliances(show, parsed_elements, {"name": LayoutOptions.PRESET.value})
        assert state is show
        assert _groups(elements).count("transformer_symbol") == 1

    assert parsed_elements == original


def test_non_preset_layout_does_not_add_transformer_symbol():
    show_appliances = False
    elements, _ = update_appliances(show_appliances, _parsed_elements(), {"name": LayoutOptions.GRID.value})

    assert "transformer" in _groups(elements)
    assert "transformer_symbol" not in _groups(elements)


def test_missing_parsed_elements_prevents_update():
    show_appliances = False
    with pytest.raises(PreventUpdate):
        update_appliances(show_appliances, None, {"name": LayoutOptions.PRESET.value})
