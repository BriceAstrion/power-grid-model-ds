
# SPDX-FileCopyrightText: Contributors to the Power Grid Model project <powergridmodel@lfenergy.org>
#
# SPDX-License-Identifier: MPL-2.0

"""Tests for transformer-specific Cytoscape styling."""

from power_grid_model_ds._core.visualizer.layout.cytoscape_styling import (
    DEFAULT_STYLESHEET,
)
from power_grid_model_ds._core.visualizer.styling_classification import StyleClass


def test_two_winding_transformer_has_specific_selector():
    """Two-winding transformers have a dedicated rendering rule."""
    selector = f'edge.{StyleClass.TRANSFORMER.value}[group = "transformer"]'

    matching_rules = [
        rule for rule in DEFAULT_STYLESHEET
        if rule["selector"] == selector
    ]

    assert len(matching_rules) == 1


def test_three_winding_transformer_keeps_general_transformer_style():
    """The general transformer rule remains available."""
    selector = f".{StyleClass.TRANSFORMER.value}"

    assert any(
        rule["selector"] == selector
        for rule in DEFAULT_STYLESHEET
    )


def test_open_connection_rules_remain_available():
    """Transformer styling must not remove connection-status rules."""
    selectors = {
        rule["selector"] for rule in DEFAULT_STYLESHEET
    }

    assert f".{StyleClass.OPEN_BRANCH.value}" in selectors
    assert f".{StyleClass.OPEN_BRANCH_FROM.value}" in selectors
    assert f".{StyleClass.OPEN_BRANCH_TO.value}" in selectors



def test_two_winding_transformer_has_no_direction_arrow():
    """A two-winding transformer is not shown as a directional branch."""
    selector = f'edge.{StyleClass.TRANSFORMER.value}[group = "transformer"]'

    rule = next(
        rule for rule in DEFAULT_STYLESHEET
        if rule["selector"] == selector
    )

    assert rule["style"]["target-arrow-shape"] == "none"


def test_open_to_indicator_overrides_transformer_arrow():
    """An open transformer connection retains its hollow endpoint marker."""
    transformer_selector = (
        f'edge.{StyleClass.TRANSFORMER.value}[group = "transformer"]'
    )
    open_to_selector = f".{StyleClass.OPEN_BRANCH_TO.value}"

    selectors = [
        rule["selector"] for rule in DEFAULT_STYLESHEET
    ]

    assert selectors.index(open_to_selector) > selectors.index(transformer_selector)

    open_to_rule = next(
        rule for rule in DEFAULT_STYLESHEET
        if rule["selector"] == open_to_selector
    )

    assert open_to_rule["style"]["target-arrow-shape"] == "diamond"
    assert open_to_rule["style"]["target-arrow-fill"] == "hollow"


def test_three_winding_transformer_does_not_use_two_winding_selector():
    """The dedicated rule must exclude three-winding transformer edges."""
    selector = f'edge.{StyleClass.TRANSFORMER.value}[group = "transformer"]'

    assert 'group = "transformer"' in selector
    assert 'group = "three_winding_transformer"' not in selector
