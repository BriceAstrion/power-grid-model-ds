# SPDX-FileCopyrightText: Contributors to the Power Grid Model project <powergridmodel@lfenergy.org>
#
# SPDX-License-Identifier: MPL-2.0

"""Layout for symmetric voltage measurement comparisons."""

from dash import dcc, html


VOLTAGE_COMPARISON_HTML = html.Div(
    [
        html.H4("Voltage measurement comparison"),
        dcc.Markdown(
            "Select one network node to inspect its symmetric voltage sensors. "
            "The comparison uses scenario indices, not timestamps."
        ),
        html.Label("Voltage sensor"),
        dcc.Dropdown(
            id="voltage-comparison-sensor",
            options=[],
            placeholder="Select a node with a voltage sensor",
            clearable=False,
        ),
        html.Label(
            "Sigma multiplier",
            style={"display": "block", "marginTop": "15px"},
        ),
        dcc.Slider(
            id="voltage-comparison-multiplier",
            min=0,
            max=5,
            step=0.5,
            value=3,
            marks={value: str(value) for value in range(6)},
            tooltip={"placement": "bottom"},
        ),
        html.Div(
            id="voltage-comparison-message",
            style={"marginTop": "15px"},
        ),
        dcc.Graph(
            id="voltage-comparison-graph",
            style={"display": "none"},
        ),
    ],
    style={
        "margin": "20px 10px",
        "padding": "15px",
        "border": "1px solid #ddd",
        "borderRadius": "5px",
    },
)
