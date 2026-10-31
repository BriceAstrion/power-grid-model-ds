# SPDX-FileCopyrightText: Contributors to the Power Grid Model project <powergridmodel@lfenergy.org>
#
# SPDX-License-Identifier: MPL-2.0

from dash import dcc, html

SELECTION_OUTPUT_HEADER_STYLE = {"margin": "20px 0 10px 0"}
_SELECTION_OUTPUT_STYLE = {"overflowX": "scroll", "textAlign": "center", "margin": "10px"}

SELECTION_OUTPUT_HTML = html.Div(
    dcc.Markdown(
        "Click on a **node** or **edge** to display all its associated components and their attributes."
        "\nYou can also use Ctrl+Click (or Cmd+Click on Mac) to select multiple nodes or edges.",
        style=SELECTION_OUTPUT_HEADER_STYLE,
    ),
    id="selection-output",
    style=_SELECTION_OUTPUT_STYLE,
)


SELECTION_GRAPH_HTML = html.Div(
    [
        # Temporary cell selection used by the existing callback.
        dcc.Store(
            id="selected-selection-cell",
            storage_type="memory",
        ),
        # Explicitly retained graph selections for F14.
        dcc.Store(
            id="retained-graph-selections",
            data=[],
            storage_type="memory",
        ),
        html.Div(
            [
                html.Label(
                    "Sigma multiplier",
                    htmlFor="sigma-multiplier",
                ),
                dcc.Input(
                    id="sigma-multiplier",
                    type="number",
                    min=0,
                    step=0.5,
                    value=2.0,
                    debounce=True,
                    style={"width": "100px", "marginLeft": "10px"},
                ),
            ],
            id="sigma-multiplier-controls",
            style={"display": "none", "marginBottom": "10px"},
        ),
        # Keep the legacy graph mounted for its existing callback,
        # but display graphs through the retained collection instead.
        html.Div(
            dcc.Graph(
                id="selection-graph",
                style={"display": "none"},
            ),
            style={"display": "none"},
        ),
        html.Div(
            [
                html.Div(
                    [
                        html.H5(
                            "Selected graphs",
                            style={
                                "margin": "0",
                                "fontWeight": "600",
                            },
                        ),
                        html.Button(
                            [
                                html.I(
                                    className="fa-solid fa-trash-can",
                                    style={"marginRight": "8px"},
                                    **{"aria-hidden": "true"},
                                ),
                                "Clear all graphs",
                            ],
                            id="clear-retained-graphs",
                            n_clicks=0,
                            className="btn btn-danger",
                            title="Remove all selected graphs",
                            style={
                                "fontWeight": "600",
                                "borderRadius": "6px",
                                "padding": "8px 14px",
                                "minHeight": "44px",
                                "flexShrink": 0,
                            },
                        ),
                    ],
                    style={
                        "display": "flex",
                        "justifyContent": "space-between",
                        "alignItems": "center",
                        "gap": "16px",
                        "marginBottom": "16px",
                        "flexWrap": "wrap",
                    },
                ),
                html.Div(
                    id="retained-graphs-container",
                    children=[],
                ),
            ],
            id="retained-graphs-section",
            style={"marginTop": "15px"},
        ),
    ],
    style={"margin": "10px"},
)
