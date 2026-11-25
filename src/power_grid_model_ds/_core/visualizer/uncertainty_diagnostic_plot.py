# SPDX-FileCopyrightText: Contributors to the Power Grid Model project <powergridmodel@lfenergy.org>
#
# SPDX-License-Identifier: MPL-2.0

"""Plot uncertainty-relative measurement diagnostics."""

import numpy as np
import plotly.graph_objects as go

from power_grid_model_ds._core.visualizer.measurement_comparison import (
    MeasurementComparison,
    VoltageComparison,
)
from power_grid_model_ds._core.visualizer.uncertainty_diagnostics import (
    get_uncertainty_relative_discrepancy,
)

_MAX_UNAVAILABLE_PREVIEW = 5


def _format_value(value: float) -> str:
    """Format a diagnostic input without concealing unavailable values."""
    if np.isnan(value):
        return "Unavailable"
    if np.isposinf(value):
        return "Positive infinity"
    if np.isneginf(value):
        return "Negative infinity"
    return f"{value:.6g}"


def _add_isolated_points(fig: go.Figure, finite: np.ndarray) -> None:
    """Keep finite values visible when no adjacent line segment exists."""
    previous = np.zeros_like(finite)
    following = np.zeros_like(finite)
    previous[1:] = finite[:-1]
    following[:-1] = finite[1:]

    isolated = finite & ~previous & ~following

    if not np.any(isolated):
        return

    trace = fig.data[0]
    fig.add_trace(
        go.Scatter(
            x=np.asarray(trace.x)[isolated],
            y=np.asarray(trace.y)[isolated],
            customdata=np.asarray(trace.customdata)[isolated],
            mode="markers",
            name=trace.name,
            marker={
                "size": 9,
                "color": "royalblue",
                "line": {
                    "width": 1.5,
                    "color": "white",
                },
            },
            hovertemplate=trace.hovertemplate,
        )
    )


def create_uncertainty_diagnostic_figure(
    comparison: VoltageComparison | MeasurementComparison,
    *,
    title: str = "Normalized residual",
) -> go.Figure:
    """Create a scenario-aligned absolute normalized residual figure."""
    discrepancy = get_uncertainty_relative_discrepancy(comparison)

    finite = np.isfinite(discrepancy)
    display_values = np.where(finite, discrepancy, np.nan)

    sigma = comparison.sigma
    unavailable = []

    for i, scenario in enumerate(comparison.scenario_indices):
        if finite[i]:
            continue

        if sigma is None or not np.isfinite(sigma[i]):
            reason = "sigma unavailable"
        elif not np.isfinite(comparison.measured[i]) or not np.isfinite(comparison.estimated[i]):
            reason = "measurement or estimate unavailable"
        elif sigma[i] == 0 and np.isinf(discrepancy[i]):
            reason = "zero sigma; nonzero difference (infinite ratio)"
        elif sigma[i] == 0:
            reason = "zero sigma; zero difference (undefined ratio)"
        else:
            reason = "normalized residual unavailable"

        unavailable.append(f"{scenario}: {reason}")

    fig = go.Figure()

    if unavailable:
        preview = "; ".join(unavailable[:_MAX_UNAVAILABLE_PREVIEW])

        if len(unavailable) > _MAX_UNAVAILABLE_PREVIEW:
            preview += f"; and {len(unavailable) - _MAX_UNAVAILABLE_PREVIEW} more"

        fig.add_annotation(
            x=0,
            y=1.12,
            xref="paper",
            yref="paper",
            text=f"Unavailable scenarios ({len(unavailable)}): {preview}",
            showarrow=False,
            xanchor="left",
            align="left",
            font={"size": 11, "color": "#8B1E1E"},
        )

    # Retain the original discrepancy description in customdata[0].
    # Additional fields provide the underlying values on hover.
    hover_data = [
        [
            _format_value(float(discrepancy[i])),
            _format_value(float(comparison.measured[i])),
            _format_value(float(comparison.estimated[i])),
            (_format_value(float(sigma[i])) if sigma is not None else "Unavailable"),
        ]
        for i in range(len(comparison.scenario_indices))
    ]

    fig.add_trace(
        go.Scatter(
            x=comparison.scenario_indices,
            y=display_values,
            customdata=hover_data,
            mode="lines",
            name="Absolute normalized residual",
            line={
                "width": 2.5,
                "color": "royalblue",
            },
            connectgaps=False,
            hovertemplate=(
                "Scenario: %{x}<br>"
                "Measured: %{customdata[1]}<br>"
                "Calculated: %{customdata[2]}<br>"
                "Sigma: %{customdata[3]}<br>"
                "Absolute normalized residual: %{customdata[0]}"
                "<extra></extra>"
            ),
        )
    )

    _add_isolated_points(fig, finite)

    if np.any(finite):
        fig.add_hline(
            y=1.0,
            line_dash="dash",
            line_color="gray",
            line_width=1.5,
            annotation_text="1 sigma reference",
            annotation_position="top right",
        )

    fig.update_layout(
        title=title,
        xaxis_title="Scenario Index",
        yaxis_title="Absolute normalized residual",
        template="plotly_white",
        hovermode="closest",
        showlegend=False,
        margin={
            "t": 105,
            "l": 75,
            "r": 45,
            "b": 65,
        },
        height=430,
    )

    fig.update_xaxes(
        tickmode="auto",
        tickformat="d",
        showgrid=True,
        gridcolor="#e9eef5",
        zeroline=False,
    )

    fig.update_yaxes(
        rangemode="tozero",
        showgrid=True,
        gridcolor="#e9eef5",
        zeroline=False,
    )

    return fig
