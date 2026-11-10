# SPDX-FileCopyrightText: Contributors to the Power Grid Model project <powergridmodel@lfenergy.org>
#
# SPDX-License-Identifier: MPL-2.0

"""Tests for contextual F11 validation and timed NF07 guidance."""

import math

import pytest

from power_grid_model_ds._core.visualizer.layout.selection_output import (
    SELECTION_GRAPH_HTML,
    restart_sigma_guidance_timer,
    update_sigma_guidance_expansion,
    update_sigma_multiplier_input_style,
    update_voltage_comparison_guidance,
)

VOLTAGE_CELL = {"group": "sym_voltage_sensor", "id": 101, "column": "u_measured"}
VISIBLE = {"display": "block"}
HIDDEN = {"display": "none"}

NOTE_VISIBLE = {
    "display": "flex",
    "alignItems": "center",
    "justifyContent": "flex-end",
    "columnGap": "16px",
    "rowGap": "8px",
    "flexWrap": "wrap",
    "fontSize": "14px",
    "color": "#694100",
}

ERROR_VISIBLE = {
    "display": "flex",
    "alignItems": "center",
    "justifyContent": "flex-end",
    "columnGap": "16px",
    "rowGap": "8px",
    "flexWrap": "wrap",
    "fontSize": "16px",
    "color": "#912018",
}


def test_guidance_layout_and_timer():
    controls = next(
        child for child in SELECTION_GRAPH_HTML.children if getattr(child, "id", None) == "sigma-multiplier-controls"
    )
    assert controls.id == "sigma-multiplier-controls"
    assert controls.style["display"] == "none"

    header, input_row = controls.children
    assert header.style["display"] == "flex"
    assert header.style["justifyContent"] == "space-between"
    assert header.children[0].children == "Sigma multiplier"

    note = header.children[1]
    assert note.id == "voltage-comparison-uncertainty-note"
    assert note.style["columnGap"] == "16px"
    assert "do not establish result validity" in note.children[1].children

    details = note.children[2]
    assert details.id == "sigma-guidance-details"
    assert details.children[0].children == "Why?"

    error = header.children[2]
    assert error.id == "sigma-multiplier-error"
    assert error.role == "alert"
    assert error.children[1].children == ("Enter a finite number greater than or equal to zero.")

    error_icon = error.children[0]
    assert error_icon.style["display"] == "inline-flex"
    assert error_icon.style["alignItems"] == "center"
    assert error_icon.style["justifyContent"] == "center"

    error_text = error.children[1]
    assert "style" not in error_text.to_plotly_json()["props"]

    sigma_input = input_row.children[0]
    assert sigma_input.id == "sigma-multiplier"
    assert len(input_row.children) == 1

    timer = next(
        child for child in SELECTION_GRAPH_HTML.children if getattr(child, "id", None) == "sigma-guidance-timer"
    )
    assert timer.id == "sigma-guidance-timer"
    assert timer.interval == 5000
    assert timer.max_intervals == 1
    assert timer.disabled is True


@pytest.mark.parametrize("multiplier", [0, 1, 2.0, 3.5])
def test_valid_multiplier_shows_note(multiplier):
    assert update_voltage_comparison_guidance(VOLTAGE_CELL, multiplier, VISIBLE, VISIBLE) == (HIDDEN, NOTE_VISIBLE)


@pytest.mark.parametrize(
    "multiplier",
    [None, -1, math.nan, math.inf, -math.inf, "invalid"],
)
def test_invalid_multiplier_shows_error(multiplier):
    assert update_voltage_comparison_guidance(VOLTAGE_CELL, multiplier, HIDDEN, VISIBLE) == (ERROR_VISIBLE, HIDDEN)


@pytest.mark.parametrize(
    "cell",
    [None, {}, {"group": "node", "column": "u"}],
)
def test_other_selection_hides_guidance(cell):
    assert update_voltage_comparison_guidance(cell, -1, VISIBLE, VISIBLE) == (HIDDEN, HIDDEN)

    assert restart_sigma_guidance_timer(cell) == (0, True)
    assert update_sigma_guidance_expansion(cell, 0) is False


def test_hidden_controls_hide_guidance():
    assert update_voltage_comparison_guidance(VOLTAGE_CELL, -1, HIDDEN, HIDDEN) == (HIDDEN, HIDDEN)


def test_hidden_graph_hides_note():
    assert update_voltage_comparison_guidance(VOLTAGE_CELL, 2, HIDDEN, VISIBLE) == (HIDDEN, HIDDEN)


def test_new_voltage_selection_starts_five_second_timer():
    assert restart_sigma_guidance_timer(VOLTAGE_CELL) == (0, False)
    assert update_sigma_guidance_expansion(VOLTAGE_CELL, 0) is True


def test_timer_collapses_details():
    assert update_sigma_guidance_expansion(VOLTAGE_CELL, 1) is False


@pytest.mark.parametrize("multiplier", [0, 1, 2.0, 3.0, 3.5])
def test_valid_multiplier_has_normal_input_style(multiplier):
    assert update_sigma_multiplier_input_style(VOLTAGE_CELL, multiplier, VISIBLE) == {
        "width": "100px",
        "padding": "6px 8px",
    }


@pytest.mark.parametrize("multiplier", [None, -1, math.nan, math.inf, -math.inf, "invalid"])
def test_invalid_multiplier_highlights_input(multiplier):
    style = update_sigma_multiplier_input_style(VOLTAGE_CELL, multiplier, VISIBLE)
    assert style["border"] == "2px solid #b42318"
    assert style["color"] == "#b42318"


@pytest.mark.parametrize("cell", [None, {}, {"group": "node", "column": "u"}])
def test_other_selection_does_not_highlight_multiplier(cell):
    assert "border" not in update_sigma_multiplier_input_style(cell, -1, VISIBLE)


def test_hidden_controls_do_not_highlight_multiplier():
    assert "border" not in update_sigma_multiplier_input_style(VOLTAGE_CELL, -1, HIDDEN)


def test_retained_voltage_selection_keeps_guidance_and_validation():
    retained = [VOLTAGE_CELL]
    assert update_voltage_comparison_guidance(None, 2.0, HIDDEN, VISIBLE, retained) == (HIDDEN, NOTE_VISIBLE)
    assert update_voltage_comparison_guidance(None, -1, HIDDEN, VISIBLE, retained) == (ERROR_VISIBLE, HIDDEN)
    assert update_sigma_multiplier_input_style(None, -1, VISIBLE, retained)["border"] == "2px solid #b42318"
    assert restart_sigma_guidance_timer(None, retained) == (0, False)
    assert update_sigma_guidance_expansion(None, 0, retained) is True
    assert update_sigma_guidance_expansion(None, 1, retained) is False


def test_non_voltage_retained_selection_does_not_start_guidance_timer():
    retained = [{"group": "node", "id": 1, "column": "u_rated"}]
    assert restart_sigma_guidance_timer(None, retained) == (0, True)
    assert update_sigma_guidance_expansion(None, 0, retained) is False
