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
from power_grid_model_ds._core.visualizer.uncertainty_diagnostics import get_uncertainty_relative_discrepancy

_MAX_UNAVAILABLE_PREVIEW = 5


def create_uncertainty_diagnostic_figure(
    comparison: VoltageComparison | MeasurementComparison,
    *,
    title: str = "Uncertainty-relative discrepancy",
) -> go.Figure:
    """Create a scenario-aligned uncertainty-relative discrepancy figure."""
    discrepancy = get_uncertainty_relative_discrepancy(comparison)

    finite = np.isfinite(discrepancy)
    display_values = np.where(finite, discrepancy, np.nan)

    hover_values = [
        "Unavailable" if np.isnan(value) else "Infinite discrepancy" if np.isinf(value) else f"{value:.4g}"
        for value in discrepancy
    ]

    fig = go.Figure()

    sigma = comparison.sigma
    unavailable = []
    for i, scenario in enumerate(comparison.scenario_indices):
        if np.isfinite(discrepancy[i]):
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
            reason = "discrepancy unavailable"
        unavailable.append(f"{scenario}: {reason}")

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

    fig.add_trace(
        go.Scatter(
            x=comparison.scenario_indices,
            y=display_values,
            customdata=hover_values,
            mode="lines+markers",
            name="Absolute discrepancy / sigma",
            line={"width": 2, "color": "royalblue"},
            hovertemplate=("Scenario: %{x}<br>Discrepancy: %{customdata}<extra></extra>"),
        )
    )

    if np.any(finite):
        fig.add_hline(
            y=1.0,
            line_dash="dash",
            line_color="gray",
            annotation_text="1 sigma reference",
            annotation_position="top right",
        )

    fig.update_layout(
        title=title,
        xaxis_title="Scenario Index",
        yaxis_title="Absolute discrepancy / sigma",
        template="plotly_white",
        hovermode="x unified",
        showlegend=False,
        margin={"t": 105},
    )

    return fig
