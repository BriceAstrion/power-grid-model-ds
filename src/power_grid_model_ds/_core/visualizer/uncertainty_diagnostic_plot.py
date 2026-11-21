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
    )

    return fig
