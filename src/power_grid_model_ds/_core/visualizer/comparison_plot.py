# SPDX-FileCopyrightText: Contributors to the Power Grid Model project <powergridmodel@lfenergy.org>
#
# SPDX-License-Identifier: MPL-2.0

"""Reusable measured-versus-calculated comparison figures."""

from dataclasses import dataclass

import numpy as np
import plotly.graph_objects as go

from power_grid_model_ds._core.visualizer.measurement_comparison import (
    MeasurementComparison,
    VoltageComparison,
    get_measurement_sigma_bounds,
)


@dataclass(frozen=True)
class ComparisonPlotOptions:
    """Presentation settings and optional identification for a comparison."""

    title: str
    quantity: str
    unit: str
    sensor_id: int | None = None
    comparison_type: str | None = None
    measurement_attribute: str | None = None


def create_measurement_comparison_figure(  # noqa: PLR0913  # pylint: disable=too-many-arguments
    comparison: VoltageComparison | MeasurementComparison,
    options: ComparisonPlotOptions | None = None,
    sigma_multiplier: float = 3.0,
    *,
    title: str | None = None,
    quantity: str | None = None,
    unit: str | None = None,
    estimated_label: str = "Calculated",
) -> go.Figure:
    """Plot measured and calculated series, optionally with measurement-centred sigma bands.

    Supports both the existing keyword-based API and ComparisonPlotOptions.
    """
    if not np.isfinite(sigma_multiplier) or sigma_multiplier < 0:
        raise ValueError("Sigma multiplier must be finite and non-negative")

    if options is None:
        if title is None or quantity is None or unit is None:
            raise TypeError("Provide ComparisonPlotOptions or title, quantity and unit")
        options = ComparisonPlotOptions(title=title, quantity=quantity, unit=unit)
    elif title is not None or quantity is not None or unit is not None:
        raise TypeError("Do not combine ComparisonPlotOptions with title, quantity or unit")

    sigma = comparison.sigma
    has_sigma = sigma is not None and bool(np.any(np.isfinite(sigma)))
    fig = go.Figure()

    if has_sigma:
        lower, upper = get_measurement_sigma_bounds(comparison, sigma_multiplier)
        fig.add_trace(
            go.Scatter(
                x=comparison.scenario_indices,
                y=lower,
                mode="lines",
                line={"width": 0},
                showlegend=False,
                hoverinfo="skip",
                name="Lower sigma bound",
            )
        )
        fig.add_trace(
            go.Scatter(
                x=comparison.scenario_indices,
                y=upper,
                mode="lines",
                line={"width": 0},
                fill="tonexty",
                fillcolor="rgba(100, 149, 237, 0.20)",
                name=f"Measurement +/- {sigma_multiplier:g} sigma",
                hoverinfo="skip",
            )
        )

    fig.add_trace(
        go.Scatter(
            x=comparison.scenario_indices,
            y=comparison.measured,
            mode="lines",
            name=f"Measured {options.quantity}",
            line={"width": 2, "color": "royalblue"},
        )
    )
    fig.add_trace(
        go.Scatter(
            x=comparison.scenario_indices,
            y=comparison.estimated,
            mode="lines",
            name=f"{estimated_label} {options.quantity}",
            line={"width": 2, "color": "darkorange", "dash": "dash"},
        )
    )

    layout = {
        "title": options.title,
        "xaxis_title": "Scenario Index",
        "yaxis_title": (
            f"{options.quantity.capitalize()} ({options.unit})" if options.unit else options.quantity.capitalize()
        ),
        "template": "plotly_white",
        "hovermode": "x unified",
        "showlegend": True,
    }

    if options.sensor_id is not None and options.comparison_type is not None:
        meta = {
            "comparison_type": options.comparison_type,
            "sensor_id": options.sensor_id,
        }
        if options.measurement_attribute is not None:
            meta["measurement_attribute"] = options.measurement_attribute
        if has_sigma:
            # Retain aligned inputs for F15 without changing the existing sigma-band calculation.
            meta["scenario_indices"] = np.asarray(comparison.scenario_indices).tolist()
            meta["measured"] = np.asarray(comparison.measured).tolist()
            meta["estimated"] = np.asarray(comparison.estimated).tolist()
            meta["sigma"] = np.asarray(sigma).tolist()
        if sigma is None:
            meta["uncertainty_diagnostic_status"] = "sigma_missing"
        elif not has_sigma:
            meta["uncertainty_diagnostic_status"] = "sigma_nonfinite"
        layout["meta"] = meta

    fig.update_layout(**layout)
    return fig
