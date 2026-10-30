
# SPDX-FileCopyrightText: Contributors to the Power Grid Model project <powergridmodel@lfenergy.org>
#
# SPDX-License-Identifier: MPL-2.0

"""Callbacks for collapsible visualiser workspace panels."""

from copy import deepcopy
from typing import Any

from dash import Input, Output, State, callback, clientside_callback, ctx
from dash_iconify import DashIconify

DEFAULT_STATE: dict[str, Any] = {
    "left": True,
    "right": True,
    "before_fullscreen": None,
}

PANEL_BORDER = "1px solid #dee2e6"

LEFT_STYLE = {
    "gridColumn": "1",
    "display": "block",
    "minWidth": "0",
    "padding": "1rem",
    "backgroundColor": "#f8f9fa",
    "borderRight": PANEL_BORDER,
}

RIGHT_STYLE = {
    "gridColumn": "3",
    "display": "block",
    "minWidth": "0",
    "maxHeight": "80vh",
    "overflow": "auto",
    "padding": "0.75rem",
    "borderLeft": PANEL_BORDER,
}



def next_panel_state(
    state: dict[str, Any] | None,
    triggered_id: str | None,
) -> dict[str, Any]:
    """Calculate the next workspace state without mutating input."""
    updated = deepcopy(state if state is not None else DEFAULT_STATE)

    updated.setdefault("left", True)
    updated.setdefault("right", True)
    updated.setdefault("before_fullscreen", None)

    if triggered_id == "workspace-toggle-fullscreen":
        both_closed = not updated["left"] and not updated["right"]

        if both_closed:
            # Restore the arrangement saved when fullscreen
            # was activated, or open both panels if the user
            # manually collapsed them.
            previous = updated["before_fullscreen"]

            if previous is not None:
                updated["left"] = previous["left"]
                updated["right"] = previous["right"]
            else:
                updated["left"] = True
                updated["right"] = True

            updated["before_fullscreen"] = None

        else:
            # Remember the current arrangement before
            # expanding the network to the full width.
            updated["before_fullscreen"] = {
                "left": updated["left"],
                "right": updated["right"],
            }
            updated["left"] = False
            updated["right"] = False

    elif triggered_id == "workspace-toggle-left":
        updated["left"] = not updated["left"]

        # A manual change cancels the saved fullscreen
        # arrangement. The icon follows actual visibility.
        updated["before_fullscreen"] = None

    elif triggered_id == "workspace-toggle-right":
        updated["right"] = not updated["right"]

        updated["before_fullscreen"] = None

    return updated


def panel_styles(
    state: dict[str, Any],
) -> tuple[
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
]:
    """Return grid, left-panel and right-panel styles."""
    left_open = bool(state.get("left", True))
    right_open = bool(state.get("right", True))

    # Keep three grid tracks so that the center panel
    # always occupies the second track.
    left_column = "minmax(220px, 1fr)" if left_open else "0px"
    center_column = "minmax(0, 2.4fr)"
    right_column = (
        "minmax(320px, 1.4fr)" if right_open else "0px"
    )

    grid_style = {
        "display": "grid",
        "gridTemplateColumns": (
            f"{left_column} "
            f"{center_column} "
            f"{right_column}"
        ),
        "width": "100%",
        "minHeight": "80vh",
        "overflowX": "auto",
    }

    left_style = LEFT_STYLE.copy()
    right_style = RIGHT_STYLE.copy()

    if not left_open:
        left_style["display"] = "none"

    if not right_open:
        right_style["display"] = "none"

    return grid_style, left_style, right_style


def panel_icons(
    state: dict[str, Any],
) -> tuple[DashIconify, DashIconify, DashIconify]:
    """Build icons from the actual workspace panel visibility."""
    left_open = bool(state.get("left", True))
    right_open = bool(state.get("right", True))

    both_closed = not left_open and not right_open

    left_icon = DashIconify(
        icon=(
            "lucide:panel-left-close"
            if left_open
            else "lucide:panel-left-open"
        ),
        width=18,
    )

    right_icon = DashIconify(
        icon=(
            "lucide:panel-right-close"
            if right_open
            else "lucide:panel-right-open"
        ),
        width=18,
    )

    fullscreen_icon = DashIconify(
        icon=(
            "lucide:minimize"
            if both_closed
            else "lucide:maximize"
        ),
        width=18,
    )

    return left_icon, right_icon, fullscreen_icon


@callback(
    Output("workspace-panel-state", "data"),
    Output("workspace-main", "style"),
    Output("workspace-left-panel", "style"),
    Output("workspace-details-panel", "style"),
    Output("workspace-toggle-left", "children"),
    Output("workspace-toggle-right", "children"),
    Output("workspace-toggle-fullscreen", "children"),
    Input("workspace-toggle-left", "n_clicks"),
    Input("workspace-toggle-right", "n_clicks"),
    Input("workspace-toggle-fullscreen", "n_clicks"),
    State("workspace-panel-state", "data"),
    prevent_initial_call=True,
)
def update_workspace(
    _left_clicks: int,
    _right_clicks: int,
    _fullscreen_clicks: int,
    current_state: dict[str, Any] | None,
) -> tuple[
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    DashIconify,
    DashIconify,
    DashIconify,
]:
    """Update panel visibility, grid sizing and toolbar icons."""
    updated = next_panel_state(
        current_state,
        ctx.triggered_id,
    )

    grid_style, left_style, right_style = panel_styles(
        updated
    )

    left_icon, right_icon, fullscreen_icon = panel_icons(
        updated
    )

    return (
        updated,
        grid_style,
        left_style,
        right_style,
        left_icon,
        right_icon,
        fullscreen_icon,
    )


# Recenter the existing network when the workspace changes size.
#
# Only zoom and pan are updated. Electrical node positions,
# transformer rendering, and the selected layout remain unchanged.
clientside_callback(
    """
    function(panelState, elements) {
        if (!panelState || !elements || !elements.length) {
            return [
                window.dash_clientside.no_update,
                window.dash_clientside.no_update
            ];
        }

        return new Promise(function(resolve) {
            window.setTimeout(function() {
                const container = document.getElementById(
                    "cytoscape-graph"
                );

                if (!container) {
                    resolve([
                        window.dash_clientside.no_update,
                        window.dash_clientside.no_update
                    ]);
                    return;
                }

                const rect = container.getBoundingClientRect();

                if (rect.width <= 0 || rect.height <= 0) {
                    resolve([
                        window.dash_clientside.no_update,
                        window.dash_clientside.no_update
                    ]);
                    return;
                }

                const positions = elements
                    .filter(function(element) {
                        return element.position &&
                            Number.isFinite(element.position.x) &&
                            Number.isFinite(element.position.y) &&
                            !(element.data &&
                              element.data.source !== undefined &&
                              element.data.target !== undefined);
                    })
                    .map(function(element) {
                        return element.position;
                    });

                if (!positions.length) {
                    resolve([
                        window.dash_clientside.no_update,
                        window.dash_clientside.no_update
                    ]);
                    return;
                }

                const xs = positions.map(function(p) {
                    return p.x;
                });

                const ys = positions.map(function(p) {
                    return p.y;
                });

                const minX = Math.min.apply(null, xs);
                const maxX = Math.max.apply(null, xs);
                const minY = Math.min.apply(null, ys);
                const maxY = Math.max.apply(null, ys);

                const padding = 70;

                const graphWidth = Math.max(maxX - minX, 1);
                const graphHeight = Math.max(maxY - minY, 1);

                const availableWidth = Math.max(
                    rect.width - 2 * padding,
                    1
                );

                const availableHeight = Math.max(
                    rect.height - 2 * padding,
                    1
                );

                const zoom = Math.max(
                    0.05,
                    Math.min(
                        3.0,
                        availableWidth / graphWidth,
                        availableHeight / graphHeight
                    )
                );

                const centerX = (minX + maxX) / 2;
                const centerY = (minY + maxY) / 2;

                const pan = {
                    x: rect.width / 2 - centerX * zoom,
                    y: rect.height / 2 - centerY * zoom
                };

                resolve([zoom, pan]);
            }, 150);
        });
    }
    """,
    Output(
        "cytoscape-graph",
        "zoom",
        allow_duplicate=True,
    ),
    Output(
        "cytoscape-graph",
        "pan",
        allow_duplicate=True,
    ),
    Input("workspace-panel-state", "data"),
    State("cytoscape-graph", "elements"),
    prevent_initial_call=True,
)
