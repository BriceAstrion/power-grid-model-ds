# SPDX-FileCopyrightText: Contributors to the Power Grid Model project <powergridmodel@lfenergy.org>
#
# SPDX-License-Identifier: MPL-2.0

"""Dash application layout for the PGM-DS visualiser."""

from dash import dcc, html
from dash_iconify import DashIconify
from power_grid_model import ComponentType

from power_grid_model_ds._core.model.grids.base import Grid
from power_grid_model_ds._core.visualizer import server_state
from power_grid_model_ds._core.visualizer.callbacks import (  # noqa: F401  # pylint: disable=unused-import
    config,
    element_selection,
    header,
    scenario_selection,
    search_form,
    workspace,
)
from power_grid_model_ds._core.visualizer.callbacks.workspace import (
    DEFAULT_STATE,
    panel_styles,
)
from power_grid_model_ds._core.visualizer.electrical_quantity_utils import (
    get_available_scalar_attributes,
    get_scenario_count,
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
from power_grid_model_ds._core.visualizer.layout.node_overlap import (
    separate_coincident_nodes,
)
from power_grid_model_ds._core.visualizer.layout.scenario_selection import get_scenario_selection_html
from power_grid_model_ds._core.visualizer.layout.selection_output import (
    SELECTION_GRAPH_HTML,
    SELECTION_OUTPUT_HTML,
)
from power_grid_model_ds._core.visualizer.parsers import parse_element_data
from power_grid_model_ds._core.visualizer.parsing_utils import (
    filter_out_appliances,
)

GOOGLE_FONTS = "https://fonts.googleapis.com/css?family=Roboto:300,400,500,700&display=swap"
MDBOOTSTRAP = "https://cdnjs.cloudflare.com/ajax/libs/mdb-ui-kit/8.2.0/mdb.min.css"

PANEL_BORDER = "1px solid #dee2e6"

# Shared static layout styles. Keep component-specific callback state in its
# existing stores rather than in module-level mutable variables.
HEADER_DIVIDER_STYLE = {"borderColor": "white", "margin": "0"}
WORKSPACE_TOOLBAR_ACTIONS_STYLE = {
    "display": "flex",
    "alignItems": "center",
    "gap": "4px",
}
NETWORK_PANEL_STYLE = {
    "gridColumn": "2",
    "minWidth": "0",
    "width": "100%",
    "overflow": "hidden",
}
GRAPH_PANEL_STYLE = {
    "width": "100%",
    "padding": "1rem",
    "borderTop": PANEL_BORDER,
}
SCENARIO_WARNING_HIDDEN_STYLE = {"display": "none"}
NODE_POSITION_INITIAL_STATE = {"scale": 1.0, "manual_positions": {}}

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
            ComponentType.three_winding_transformer: (grid.three_winding_transformer.columns),
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
        **{"aria-label": label},  # type: ignore[arg-type]
        style=TOOLBAR_BUTTON_STYLE.copy(),
    )


def _get_workspace_toolbar() -> html.Div:
    """Create the sidebar and fullscreen controls."""
    return html.Div(
        [
            _workspace_button(
                "workspace-toggle-left",
                "lucide:panel-left-close",
                "Toggle network state panel",
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
                style=WORKSPACE_TOOLBAR_ACTIONS_STYLE.copy(),
            ),
        ],
        id="workspace-toolbar",
        style=TOOLBAR_STYLE,
    )


def _get_electrical_quantity_controls(
    scenario_count: int,
    available_attributes: dict[str, list[str]],
) -> html.Section:
    """Build independent component/attribute controls for scalar output heatmaps."""
    components = sorted(available_attributes)
    fields = [
        (
            "Component",
            "electrical-component-dropdown",
            dcc.Dropdown(
                id="electrical-component-dropdown",
                options=[{"label": name.replace("_", " ").title(), "value": name} for name in components],
                value=None,
                placeholder="Select component",
                clearable=True,
                disabled=not components,
            ),
        ),
        (
            "Attribute",
            "electrical-quantity-dropdown",
            dcc.Dropdown(
                id="electrical-quantity-dropdown",
                options=[],
                value=None,
                placeholder="Select attribute",
                clearable=True,
                disabled=True,
            ),
        ),
        (
            "Scenario (1-based)",
            "electrical-scenario-input",
            dcc.Input(
                id="electrical-scenario-input",
                type="number",
                step=1,
                value=None,
                placeholder="Scenario number",
                disabled=scenario_count == 0,
            ),
        ),
    ]
    controls = []
    for label, control_id, control in fields:
        children = [
            html.Label(label, htmlFor=control_id, className="electrical-control-label"),
            html.Div(control, className="electrical-dropdown-container"),
        ]
        if control_id == "electrical-scenario-input":
            children.append(
                html.Div(
                    [
                        html.Div(className="electrical-scenario-callout-arrow"),
                        html.Div(
                            [
                                html.Span("!", className="electrical-scenario-warning-icon", **{"aria-hidden": "true"}),
                                html.Div(
                                    [
                                        html.Strong("Invalid scenario", className="electrical-scenario-warning-title"),
                                        html.Div(id="electrical-scenario-warning-text"),
                                    ],
                                    className="electrical-scenario-warning-body",
                                ),
                            ],
                            className="electrical-scenario-warning-row",
                        ),
                    ],
                    id="electrical-scenario-warning",
                    className="electrical-scenario-warning",
                    role="alert",
                    style=SCENARIO_WARNING_HIDDEN_STYLE.copy(),
                )
            )
        controls.append(
            html.Div(
                children,
                className="electrical-control-field electrical-scenario-anchor"
                if control_id == "electrical-scenario-input"
                else "electrical-control-field",
            )
        )
    return html.Section(
        [
            dcc.Store(id="electrical-available-attributes", data=available_attributes),
            html.Div(controls, className="electrical-controls-grid"),
            dcc.Store(id="electrical-scenario-count", data=scenario_count),
            html.Div(
                "",
                id="electrical-quantity-legend",
                className="electrical-quantity-legend",
                role="status",
                **{"aria-live": "polite"},  # type: ignore[arg-type]
            ),
        ],
        className="electrical-quantity-panel",
        **{"aria-label": "Electrical quantity configuration"},  # type: ignore[arg-type]
    )


def get_app_layout(grid: Grid) -> html.Div:
    """Build the PGM-DS visualiser application layout."""
    columns_store = _get_columns_store(grid)

    layout = get_default_graph_layout(grid.node)
    viz_elements_dict = parse_element_data(grid)

    # Separate overlapping nodes for display without changing the original topology.
    display_elements_dict = separate_coincident_nodes(
        viz_elements_dict,
        node_scale=1.0,
    )

    initial_elements = filter_out_appliances(display_elements_dict.values())

    source_available = grid.source.size != 0

    cytoscape_html = get_cytoscape_html(
        layout,
        initial_elements,
        source_available,
    )

    initial_state = DEFAULT_STATE.copy()

    grid_style, left_style, right_style = panel_styles(initial_state)

    output_data = server_state.get_output_data()

    scenario_count = get_scenario_count(output_data)
    available_attributes = get_available_scalar_attributes(output_data)

    electrical_controls = _get_electrical_quantity_controls(
        scenario_count,
        available_attributes,
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
            # F04: Track node scale and manually adjusted display positions.
            dcc.Store(
                id="node-position-state-store",
                data={
                    "scale": NODE_POSITION_INITIAL_STATE["scale"],
                    "manual_positions": NODE_POSITION_INITIAL_STATE["manual_positions"].copy(),
                },
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
            html.Hr(style=HEADER_DIVIDER_STYLE.copy()),
            # F01: Electrical quantity and scenario controls.
            electrical_controls,
            # Compact toolbar above the workspace.
            _get_workspace_toolbar(),
            # Three-column workspace.
            html.Div(
                [
                    # Left: network state (moved from the details panel).
                    html.Div(
                        [get_scenario_selection_html()],
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
                        style=NETWORK_PANEL_STYLE.copy(),
                    ),
                    # Right: selected component attributes and comparisons.
                    html.Div(
                        [SELECTION_OUTPUT_HTML],
                        id="workspace-details-panel",
                        style=right_style,
                    ),
                ],
                id="workspace-main",
                style=grid_style,
            ),
            # Preserve retained attribute and measurement-comparison graphs.
            html.Div(
                [
                    SELECTION_GRAPH_HTML,
                ],
                id="workspace-diagnostics-panel",
                style=GRAPH_PANEL_STYLE.copy(),
            ),
        ],
    )
