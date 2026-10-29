
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
