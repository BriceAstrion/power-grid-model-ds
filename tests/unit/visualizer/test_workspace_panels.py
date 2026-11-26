# SPDX-FileCopyrightText: Contributors to the Power Grid Model project <powergridmodel@lfenergy.org>
#
# SPDX-License-Identifier: MPL-2.0

from power_grid_model_ds._core.visualizer.callbacks.workspace import (
    CENTER_COLUMN,
    DEFAULT_STATE,
    next_panel_state,
    panel_icons,
    panel_styles,
)


def test_left_panel_collapses_and_center_expands():
    state = next_panel_state(DEFAULT_STATE, "workspace-toggle-left")
    grid, left, right = panel_styles(state)

    assert state["left"] is False
    assert state["right"] is True
    assert left["display"] == "none"
    assert right.get("display") != "none"
    assert grid["gridTemplateColumns"].startswith("0px ")


def test_right_panel_collapses_independently():
    state = next_panel_state(DEFAULT_STATE, "workspace-toggle-right")
    grid, left, right = panel_styles(state)

    assert state["left"] is True
    assert state["right"] is False
    assert left.get("display") != "none"
    assert right["display"] == "none"
    assert grid["gridTemplateColumns"].endswith(" 0px")


def test_fullscreen_closes_both_panels():
    state = next_panel_state(DEFAULT_STATE, "workspace-toggle-fullscreen")

    assert state["left"] is False
    assert state["right"] is False

    grid, _, _ = panel_styles(state)
    assert grid["gridTemplateColumns"] == f"0px {CENTER_COLUMN} 0px"


def test_fullscreen_restores_previous_visibility():
    state = next_panel_state(DEFAULT_STATE, "workspace-toggle-left")
    state = next_panel_state(state, "workspace-toggle-fullscreen")
    state = next_panel_state(state, "workspace-toggle-fullscreen")

    assert state["left"] is False
    assert state["right"] is True
    assert state["before_fullscreen"] is None


def test_manual_collapse_both_then_fullscreen_restores_panels():
    state = next_panel_state(DEFAULT_STATE, "workspace-toggle-left")
    state = next_panel_state(state, "workspace-toggle-right")

    assert state["left"] is False
    assert state["right"] is False
    assert state["before_fullscreen"] is None

    _, _, fullscreen_icon = panel_icons(state)
    assert fullscreen_icon.icon == "lucide:minimize"

    state = next_panel_state(state, "workspace-toggle-fullscreen")

    assert state["left"] is True
    assert state["right"] is True
    assert state["before_fullscreen"] is None

    _, _, fullscreen_icon = panel_icons(state)
    assert fullscreen_icon.icon == "lucide:maximize"


def test_fullscreen_restores_previous_asymmetric_arrangement():
    state = next_panel_state(DEFAULT_STATE, "workspace-toggle-left")

    assert state["left"] is False
    assert state["right"] is True

    state = next_panel_state(state, "workspace-toggle-fullscreen")

    assert state["left"] is False
    assert state["right"] is False
    assert state["before_fullscreen"] == {
        "left": False,
        "right": True,
    }

    state = next_panel_state(state, "workspace-toggle-fullscreen")

    assert state["left"] is False
    assert state["right"] is True
    assert state["before_fullscreen"] is None


def test_manual_change_after_fullscreen_updates_icon():
    state = next_panel_state(DEFAULT_STATE, "workspace-toggle-fullscreen")

    _, _, fullscreen_icon = panel_icons(state)
    assert fullscreen_icon.icon == "lucide:minimize"

    state = next_panel_state(state, "workspace-toggle-left")

    assert state["left"] is True
    assert state["right"] is False
    assert state["before_fullscreen"] is None

    _, _, fullscreen_icon = panel_icons(state)
    assert fullscreen_icon.icon == "lucide:maximize"


def test_desktop_workspace_default_proportions():
    """Both open panels use a 1:2:1 desktop grid."""
    grid, left, right = panel_styles(DEFAULT_STATE)

    assert grid["gridTemplateColumns"] == ("minmax(340px, 1fr) minmax(0, 2fr) minmax(340px, 1fr)")
    assert left["display"] == "block"
    assert right["display"] == "block"


def test_desktop_workspace_left_closed_proportions():
    """Closing the left panel preserves the central track."""
    state = next_panel_state(
        DEFAULT_STATE,
        "workspace-toggle-left",
    )
    grid, left, right = panel_styles(state)

    assert grid["gridTemplateColumns"] == ("0px minmax(0, 2fr) minmax(340px, 1fr)")
    assert left["display"] == "none"
    assert right["display"] == "block"


def test_desktop_workspace_right_closed_proportions():
    """Closing the right panel preserves the central track."""
    state = next_panel_state(
        DEFAULT_STATE,
        "workspace-toggle-right",
    )
    grid, left, right = panel_styles(state)

    assert grid["gridTemplateColumns"] == ("minmax(340px, 1fr) minmax(0, 2fr) 0px")
    assert left["display"] == "block"
    assert right["display"] == "none"


def test_desktop_workspace_fullscreen_proportions():
    """Fullscreen assigns the available width to the network."""
    state = next_panel_state(
        DEFAULT_STATE,
        "workspace-toggle-fullscreen",
    )
    grid, left, right = panel_styles(state)

    assert grid["gridTemplateColumns"] == ("0px minmax(0, 2fr) 0px")
    assert left["display"] == "none"
    assert right["display"] == "none"
