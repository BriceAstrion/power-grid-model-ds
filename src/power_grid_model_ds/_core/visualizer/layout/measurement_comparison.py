
"""PoC-04 measurement comparison panel."""

from dash import dcc, html

MEASUREMENT_COMPARISON_HTML = html.Div(
    [
        html.H4("Voltage measurement comparison"),

        html.Label("Sigma multiplier (k)"),

        dcc.Slider(
            id="sigma-multiplier",
            min=0,
            max=5,
            step=0.5,
            value=1,
            marks={
                0: "0",
                1: "1",
                2: "2",
                3: "3",
                4: "4",
                5: "5",
            },
            updatemode="mouseup",
        ),

        html.Div(
            id="measurement-comparison-status",
            role="status",
        ),

        dcc.Graph(
            id="measurement-comparison-graph",
        ),
    ],
    style={"margin": "20px"},
)
