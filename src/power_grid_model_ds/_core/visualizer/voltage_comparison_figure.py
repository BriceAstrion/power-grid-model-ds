# SPDX-FileCopyrightText: Contributors to the Power Grid Model project <powergridmodel@lfenergy.org>
#
# SPDX-License-Identifier: MPL-2.0

"""Plotly figure generation for symmetric voltage comparisons."""

import plotly.graph_objects as go

from power_grid_model_ds._core.visualizer.measurement_comparison import (
    VoltageComparison,
    calculate_sigma_bands,
)

_LINES_AND_MARKERS = "lines+markers"


def create_voltage_comparison_figure(
    comparison: VoltageComparison,
    multiplier: float = 3.0,
) -> go.Figure:
    """Plot measured and estimated voltages with measurement-centred sigma bands."""
    lower, upper = calculate_sigma_bands(comparison, multiplier)

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=comparison.scenarios,
            y=lower,
            mode="lines",
            line={"width": 0},
            name="Lower sigma bound",
            showlegend=False,
            hovertemplate="Scenario %{x}<br>Lower: %{y:.2f} V<extra></extra>",
        )
    )

    fig.add_trace(
        go.Scatter(
            x=comparison.scenarios,
            y=upper,
            mode="lines",
            fill="tonexty",
            fillcolor="rgba(31, 119, 180, 0.18)",
            line={"width": 0},
            name=f"Measured +/- {multiplier:g} sigma",
            hovertemplate="Scenario %{x}<br>Upper: %{y:.2f} V<extra></extra>",
        )
    )

    fig.add_trace(
        go.Scatter(
            x=comparison.scenarios,
            y=comparison.measured,
            mode=_LINES_AND_MARKERS,
            name="Measured voltage",
            line={"color": "#1f77b4", "width": 2},
        )
    )

    fig.add_trace(
        go.Scatter(
            x=comparison.scenarios,
            y=comparison.estimated,
            mode=_LINES_AND_MARKERS,
            name="Estimated voltage",
            line={"color": "#d62728", "width": 2},
            connectgaps=False,
        )
    )

    fig.update_layout(
        title=(f"Voltage comparison - sensor {comparison.sensor_id}, node {comparison.node_id}"),
        xaxis_title="Scenario Index",
        xaxis={
            "tickmode": "linear",
            "tick0": 0,
            "dtick": 1,
        },
        yaxis_title="Voltage (V)",
        template="plotly_white",
        hovermode="x unified",
        showlegend=True,
        annotations=[
            {
                "text": (
                    "Sigma bands are centred on measurements; being inside a band does not establish result validity."
                ),
                "xref": "paper",
                "yref": "paper",
                "x": 0,
                "y": -0.25,
                "showarrow": False,
                "xanchor": "left",
                "align": "left",
                "font": {"size": 11},
            }
        ],
        margin={"b": 115},
    )

    return fig
