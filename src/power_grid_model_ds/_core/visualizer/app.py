
# SPDX-FileCopyrightText: Contributors to the Power Grid Model project <powergridmodel@lfenergy.org>
#
# SPDX-License-Identifier: MPL-2.0

"""Dash application layout for the PGM-DS visualiser."""

from dash import dcc, html
from dash_iconify import DashIconify
from power_grid_model import ComponentType

from power_grid_model_ds._core.model.grids.base import Grid
from power_grid_model_ds._core.visualizer.callbacks import (  # noqa: F401  # pylint: disable=unused-import
    config,
    diagnostic_overview,
    element_selection,
    header,
    search_form,
    voltage_comparison,
    workspace,
)
from power_grid_model_ds._core.visualizer.callbacks.workspace import (
    DEFAULT_STATE,
    panel_styles,
)
from power_grid_model_ds._core.visualizer.layout.cytoscape_html import (
    get_cytoscape_html,
)
from power_grid_model_ds._core.visualizer.layout.cytoscape_styling import (
    DEFAULT_STYLESHEET,
)
from power_grid_model_ds._core.visualizer.layout.header import HEADER_HTML
from power_grid_model_ds._core.visualizer.layout.layout_config import (
    get_default_graph_layout,
)
from power_grid_model_ds._core.visualizer.layout.selection_output import (
    SELECTION_GRAPH_HTML,
    SELECTION_OUTPUT_HTML,
)
from power_grid_model_ds._core.visualizer.layout.voltage_comparison import (
    VOLTAGE_COMPARISON_HTML,
)
from power_grid_model_ds._core.visualizer.parsers import parse_element_data
from power_grid_model_ds._core.visualizer.parsing_utils import (
    filter_out_appliances,
)

GOOGLE_FONTS = (
    "https://fonts.googleapis.com/css?family="
    "Roboto:300,400,500,700&display=swap"
)
MDBOOTSTRAP = (
    "https://cdnjs.cloudflare.com/ajax/libs/"
    "mdb-ui-kit/8.2.0/mdb.min.css"
)

PANEL_BORDER = "1px solid #dee2e6"

TOOLBAR_STYLE = {
    "height": "32px",
    "minHeight": "32px",
    "width": "100%",
    "display": "flex",
    "alignItems": "center",
    "justifyContent": "space-between",
    "padding": "0 8px",
    "backgroundColor": "#f1f3f5",
    "borderBottom": PANEL_BORDER,
}

TOOLBAR_BUTTON_STYLE = {
    "border": "none",
    "background": "transparent",
    "padding": "2px",
    "width": "28px",
    "height": "28px",
    "display": "flex",
    "alignItems": "center",
    "justifyContent": "center",
    "cursor": "pointer",
    "color": "#343a40",
}


def _get_columns_store(grid: Grid) -> dcc.Store:
    """Store the available component columns."""
    return dcc.Store(
        id="columns-store",
        data={
            ComponentType.node: grid.node.columns,
            ComponentType.line: grid.line.columns,
            ComponentType.link: grid.link.columns,
            ComponentType.transformer: grid.transformer.columns,
            ComponentType.three_winding_transformer: (
                grid.three_winding_transformer.columns
            ),
            ComponentType.asym_line: grid.asym_line.columns,
            ComponentType.generic_branch: grid.generic_branch.columns,
            "branches": grid.branches.columns,
        },
    )


def _workspace_button(
    button_id: str,
    icon: str,
    label: str,
) -> html.Button:
    """Create a compact, accessible workspace toolbar button."""
    return html.Button(
        DashIconify(icon=icon, width=18),
        id=button_id,
        n_clicks=0,
        title=label,
        **{"aria-label": label},
        style=TOOLBAR_BUTTON_STYLE.copy(),
    )


def _get_workspace_toolbar() -> html.Div:
    """Create the sidebar and fullscreen controls."""
    return html.Div(
        [
            _workspace_button(
                "workspace-toggle-left",
                "lucide:panel-left-close",
                "Toggle diagnostic panel",
            ),
            html.Div(
                [
                    _workspace_button(
                        "workspace-toggle-fullscreen",
                        "lucide:maximize",
                        "Toggle network fullscreen",
                    ),
                    _workspace_button(
                        "workspace-toggle-right",
                        "lucide:panel-right-close",
                        "Toggle attributes panel",
                    ),
                ],
                style={
                    "display": "flex",
                    "alignItems": "center",
                    "gap": "4px",
                },
            ),
        ],
        id="workspace-toolbar",
        style=TOOLBAR_STYLE,
    )


def get_app_layout(grid: Grid) -> html.Div:
    """Build the PGM-DS visualiser application layout."""
    columns_store = _get_columns_store(grid)

    layout = get_default_graph_layout(grid.node)
    viz_elements_dict = parse_element_data(grid)

    initial_elements = filter_out_appliances(
        viz_elements_dict.values()
    )

    source_available = grid.source.size != 0

    cytoscape_html = get_cytoscape_html(
        layout,
        initial_elements,
        source_available,
    )

    initial_state = DEFAULT_STATE.copy()

    grid_style, left_style, right_style = panel_styles(
        initial_state
    )

    return html.Div(
        [
            columns_store,

            # State used by the workspace toolbar callbacks.
            dcc.Store(
                id="workspace-panel-state",
                data=initial_state,
            ),

            # Existing visualiser stores.
            dcc.Store(
                id="parsed-elements-store",
                data=viz_elements_dict,
            ),
            dcc.Store(
                id="stylesheet-store",
                data=DEFAULT_STYLESHEET,
            ),
            dcc.Store(
                id="source-available-store",
                data=source_available,
            ),
            dcc.Store(
                id="show-appliances-store",
                data=False,
                storage_type="session",
            ),

            # Preserve the existing navigation bar.
            HEADER_HTML,
            html.Hr(
                style={
                    "borderColor": "white",
                    "margin": "0",
                }
            ),

            # Compact toolbar above the workspace.
            _get_workspace_toolbar(),

            # Three-column workspace.
            html.Div(
                [
                    # Left: diagnostic overview.
                    html.Div(
                        [
                            html.H5("Diagnostic overview"),
                            html.P(
                                "Select a network component to "
                                "inspect its available data and "
                                "diagnostics.",
                                style={"fontSize": "0.9rem"},
                            ),
                            html.Hr(),
                            html.Div(
                                "No diagnostic summary selected.",
                                id="diagnostic-overview-content",
                                role="status",
                            ),
                        ],
                        id="workspace-left-panel",
                        style=left_style,
                    ),

                    # Center: interactive electrical network.
                    # Keep this permanently assigned to column 2.
                    html.Div(
                        [
                            cytoscape_html,
                        ],
                        id="workspace-network-panel",
                        style={
                            "gridColumn": "2",
                            "minWidth": "0",
                            "width": "100%",
                            "overflow": "hidden",
                        },
                    ),

                    # Right: component attributes.
                    html.Div(
                        [
                            SELECTION_OUTPUT_HTML,
                        ],
                        id="workspace-details-panel",
                        style=right_style,
                    ),
                ],
                id="workspace-main",
                style=grid_style,
            ),

            # Preserve the existing bottom diagnostic plots.
            html.Div(
                [
                    SELECTION_GRAPH_HTML,
                    VOLTAGE_COMPARISON_HTML,
                ],
                id="workspace-diagnostics-panel",
                style={
                    "width": "100%",
                    "padding": "1rem",
                    "borderTop": PANEL_BORDER,
                },
            ),
        ],
    )
