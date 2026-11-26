# SPDX-FileCopyrightText: Contributors to the Power Grid Model project <powergridmodel@lfenergy.org>
#
# SPDX-License-Identifier: MPL-2.0

"""Tests for electrical quantity Cytoscape styling."""

import pytest

from power_grid_model_ds._core.visualizer.layout import cytoscape_styling
from power_grid_model_ds._core.visualizer.layout.cytoscape_styling import DEFAULT_STYLESHEET
from power_grid_model_ds._core.visualizer.styling_classification import StyleClass


def _get_style(selector: str) -> dict:
    """Find exactly one stylesheet rule for the requested selector."""
    matching_rules = [rule["style"] for rule in DEFAULT_STYLESHEET if rule["selector"] == selector]

    assert len(matching_rules) == 1
    style = matching_rules[0]
    assert isinstance(style, dict)
    return style


def _get_rule_index(selector: str) -> int:
    """Find the position of a unique stylesheet rule."""
    matching_indices = [index for index, rule in enumerate(DEFAULT_STYLESHEET) if rule["selector"] == selector]

    assert len(matching_indices) == 1
    return matching_indices[0]


def test_electrical_node_color_uses_element_data():
    style = _get_style("node.electrical-heatmap[electrical_color]")

    assert style["background-color"] == "data(electrical_color)"
    assert style["text-background-color"] == "data(electrical_color)"


def test_electrical_edge_color_uses_element_data():
    style = _get_style("edge.electrical-heatmap[electrical_color]")

    assert style["line-color"] == "data(electrical_color)"
    assert style["target-arrow-color"] == "data(electrical_color)"
    assert style["source-arrow-color"] == "data(electrical_color)"


def test_open_branch_rules_follow_electrical_rules():
    """Open-branch styling must remain after electrical edge colouring."""
    open_branch_selector = f".{StyleClass.OPEN_BRANCH.value}"
    electrical_edge_selector = "edge.electrical-heatmap[electrical_color]"

    assert _get_rule_index(open_branch_selector) > _get_rule_index(electrical_edge_selector)


@pytest.mark.parametrize(
    ("selection_rule", "electrical_selector"),
    [
        (
            cytoscape_styling._SELECTED_NODE_STYLE,
            "node.electrical-heatmap[electrical_color]",
        ),
        (
            cytoscape_styling._SELECTED_BRANCH_STYLE,
            "edge.electrical-heatmap[electrical_color]",
        ),
        (
            cytoscape_styling._SELECTED_TRANSFORMER_STYLE,
            "edge.electrical-heatmap[electrical_color]",
        ),
        (
            cytoscape_styling._SELECTED_LINK_STYLE,
            "edge.electrical-heatmap[electrical_color]",
        ),
        (
            cytoscape_styling._SELECTED_GENERIC_BRANCH_STYLE,
            "edge.electrical-heatmap[electrical_color]",
        ),
        (
            cytoscape_styling._SELECTED_ASYM_LINE_STYLE,
            "edge.electrical-heatmap[electrical_color]",
        ),
    ],
    ids=[
        "node",
        "branch",
        "transformer",
        "link",
        "generic-branch",
        "asym-line",
    ],
)
def test_selection_rules_follow_electrical_rules(selection_rule, electrical_selector):
    """Selection highlighting must take precedence over heatmap colours."""
    assert _get_rule_index(selection_rule["selector"]) > _get_rule_index(electrical_selector)


@pytest.mark.parametrize(
    "open_rule",
    [
        cytoscape_styling._OPEN_BRANCH_STYLE,
        cytoscape_styling._OPEN_FROM_SIDE_BRANCH_STYLE,
        cytoscape_styling._OPEN_TO_SIDE_BRANCH_STYLE,
        cytoscape_styling._OPEN_LOADING_EDGE_STYLE,
        cytoscape_styling._OPEN_GENERATING_EDGE_STYLE,
    ],
    ids=[
        "open-branch",
        "open-from-side",
        "open-to-side",
        "open-loading-edge",
        "open-generating-edge",
    ],
)
def test_open_rules_follow_selection_rules(open_rule):
    """Open component styling must retain its original precedence."""
    selection_rules = [
        cytoscape_styling._SELECTED_NODE_STYLE,
        cytoscape_styling._SELECTED_BRANCH_STYLE,
        cytoscape_styling._SELECTED_TRANSFORMER_STYLE,
        cytoscape_styling._SELECTED_LINK_STYLE,
        cytoscape_styling._SELECTED_GENERIC_BRANCH_STYLE,
        cytoscape_styling._SELECTED_ASYM_LINE_STYLE,
    ]

    open_rule_index = _get_rule_index(open_rule["selector"])

    for selection_rule in selection_rules:
        assert open_rule_index > _get_rule_index(selection_rule["selector"])
