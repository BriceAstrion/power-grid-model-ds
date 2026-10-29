# SPDX-FileCopyrightText: Contributors to the Power Grid Model project <powergridmodel@lfenergy.org>
#
# SPDX-License-Identifier: MPL-2.0

"""Plotly figure generation for symmetric voltage comparisons."""

import numpy as np
import plotly.graph_objects as go

from power_grid_model_ds._core.visualizer.measurement_comparison import (
    VoltageComparison,
    calculate_sigma_bands,
)
from power_grid_model_ds._core.visualizer.scenario_status import (
    CalculationStatus,
    ScenarioStatus,
)

_LINES_AND_MARKERS = "lines+markers"

def create_voltage_comparison_figure(
    comparison: VoltageComparison,
    multiplier: float = 3.0,
    scenario_status: ScenarioStatus | None = None,
) -> go.Figure:
    """Plot voltage comparison while distinguishing calculation outcomes."""
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

    if scenario_status is None:
        # Preserve the existing figure for callers without status metadata.
        fig.add_trace(
            go.Scatter(
                x=comparison.scenarios,
                y=comparison.estimated,
                mode=_LINES_AND_MARKERS,
                name="Estimated voltage (status unknown)",
                line={"color": "#d62728", "width": 2},
            )
        )
        status_note = "Calculation status was not provided."

    else:
        statuses = [
            scenario_status.status_for(int(index))
            for index in comparison.scenarios
        ]

        succeeded = np.array(
            [status == CalculationStatus.SUCCEEDED for status in statuses]
        )
        failed = np.array(
            [status == CalculationStatus.FAILED for status in statuses]
        )
        unknown = np.array(
            [status == CalculationStatus.UNKNOWN for status in statuses]
        )

        # NaN creates gaps, preventing lines through failed scenarios.
        successful_estimates = np.where(
            succeeded, comparison.estimated, np.nan
        )

        fig.add_trace(
            go.Scatter(
                x=comparison.scenarios,
                y=successful_estimates,
                mode=_LINES_AND_MARKERS,
                connectgaps=False,
                name="Estimated voltage (succeeded)",
                line={"color": "#d62728", "width": 2},
            )
        )

        if np.any(unknown):
            fig.add_trace(
                go.Scatter(
                    x=comparison.scenarios[unknown],
                    y=comparison.estimated[unknown],
                    mode="markers",
                    name="Estimated voltage (status unknown)",
                    marker={
                        "color": "#ff7f0e",
                        "symbol": "circle-open",
                        "size": 10,
                        "line": {"width": 2},
                    },
                )
            )

        if np.any(failed):
            fig.add_trace(
                go.Scatter(
                    x=comparison.scenarios[failed],
                    y=comparison.measured[failed],
                    mode="markers",
                    name="State estimation failed",
                    marker={
                        "color": "#000000",
                        "symbol": "x",
                        "size": 12,
                        "line": {"width": 2},
                    },
                    hovertemplate=(
                        "Scenario %{x}<br>"
                        "State estimation failed"
                        "<extra></extra>"
                    ),
                )
            )

        status_note = (
            f"Calculation status: {np.count_nonzero(succeeded)} succeeded, "
            f"{np.count_nonzero(failed)} failed, "
            f"{np.count_nonzero(unknown)} unknown."
        )

    fig.update_layout(
        title=(
            f"Voltage comparison - sensor {comparison.sensor_id}, "
            f"node {comparison.node_id}"
        ),
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
                    "Sigma bands are centred on measurements; "
                    "being inside a band does not establish result validity."
                    f"<br>{status_note}"
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