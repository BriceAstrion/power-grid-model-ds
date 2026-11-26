# SPDX-FileCopyrightText: Contributors to the Power Grid Model project <powergridmodel@lfenergy.org>
#
# SPDX-License-Identifier: MPL-2.0

from copy import deepcopy

from power_grid_model_ds._core.visualizer.callbacks.config import update_arrows
from power_grid_model_ds._core.visualizer.layout.colors import CYTO_COLORS
from power_grid_model_ds._core.visualizer.layout.cytoscape_styling import DEFAULT_STYLESHEET
from power_grid_model_ds._core.visualizer.styling_classification import StyleClass


def _get_style(stylesheet, style_class):
    selector = f".{style_class.value}"
    return next(rule["style"] for rule in stylesheet if rule["selector"] == selector)


def test_closed_link_has_tee_markers():
    style = _get_style(DEFAULT_STYLESHEET, StyleClass.LINK)

    assert style["source-arrow-shape"] == "tee"
    assert style["target-arrow-shape"] == "tee"


def test_open_link_preserves_open_endpoint_markers():
    stylesheet = DEFAULT_STYLESHEET

    link_index = next(i for i, rule in enumerate(stylesheet) if rule["selector"] == f".{StyleClass.LINK.value}")
    open_from_index = next(
        i for i, rule in enumerate(stylesheet) if rule["selector"] == f".{StyleClass.OPEN_BRANCH_FROM.value}"
    )
    open_to_index = next(
        i for i, rule in enumerate(stylesheet) if rule["selector"] == f".{StyleClass.OPEN_BRANCH_TO.value}"
    )

    assert link_index < open_from_index
    assert link_index < open_to_index
    assert _get_style(stylesheet, StyleClass.OPEN_BRANCH_FROM)["source-arrow-shape"] == "diamond"
    assert _get_style(stylesheet, StyleClass.OPEN_BRANCH_TO)["target-arrow-shape"] == "diamond"


def test_link_selection_colors_are_preserved():
    selector = f".{StyleClass.LINK.value}:selected, .{StyleClass.LINK.value}:active"
    style = next(rule["style"] for rule in DEFAULT_STYLESHEET if rule["selector"] == selector)

    assert style["line-color"] == CYTO_COLORS["selected_link"]
    assert style["source-arrow-color"] == CYTO_COLORS["selected_link"]
    assert style["target-arrow-color"] == CYTO_COLORS["selected_link"]


def test_arrow_toggle_preserves_link_markers():
    stylesheet = deepcopy(DEFAULT_STYLESHEET)

    for show_arrows in (False, True):
        stored_stylesheet, current_stylesheet = update_arrows(
            show_arrows,
            deepcopy(stylesheet),
            deepcopy(stylesheet),
        )

        for updated_stylesheet in (stored_stylesheet, current_stylesheet):
            link_style = _get_style(updated_stylesheet, StyleClass.LINK)

            assert link_style["source-arrow-shape"] == "tee"
            assert link_style["target-arrow-shape"] == "tee"
