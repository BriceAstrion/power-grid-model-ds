# SPDX-FileCopyrightText: Contributors to the Power Grid Model project <powergridmodel@lfenergy.org>
#
# SPDX-License-Identifier: MPL-2.0

"""Build the electrical quantity legend displayed above the graph."""

from typing import Any, cast

from dash import html

from power_grid_model_ds._core.visualizer.electrical_quantity_styling import (
    MISSING_COLOR,
    RAINBOW_STOPS,
    SENSOR_GROUPS,
)

# Electrical quantity labels and units follow the PGM output schema.
# https://power-grid-model.readthedocs.io/en/stable/user_manual/components.html
QUANTITY_LABELS = {
    # Node quantities
    "u_pu": ("Voltage magnitude", "p.u."),
    "u": ("Voltage magnitude", "V"),
    "u_angle": ("Voltage angle", "rad"),
    # Power and current quantities
    "p": ("Active power", "W"),
    "q": ("Reactive power", "var"),
    "i": ("Current magnitude", "A"),
    "s": ("Apparent power", "VA"),
    "pf": ("Power factor", ""),
    # Branch quantities
    "loading": ("Relative loading", ""),
    "p_from": ("Active power - from side", "W"),
    "q_from": ("Reactive power - from side", "var"),
    "i_from": ("Current magnitude - from side", "A"),
    "s_from": ("Apparent power - from side", "VA"),
    "p_to": ("Active power - to side", "W"),
    "q_to": ("Reactive power - to side", "var"),
    "i_to": ("Current magnitude - to side", "A"),
    "s_to": ("Apparent power - to side", "VA"),
    # Three-winding transformer quantities
    "loading_1": ("Loading - winding 1", ""),
    "loading_2": ("Loading - winding 2", ""),
    "loading_3": ("Loading - winding 3", ""),
    "p_1": ("Active power - winding 1", "W"),
    "q_1": ("Reactive power - winding 1", "var"),
    "i_1": ("Current magnitude - winding 1", "A"),
    "s_1": ("Apparent power - winding 1", "VA"),
    "p_2": ("Active power - winding 2", "W"),
    "q_2": ("Reactive power - winding 2", "var"),
    "i_2": ("Current magnitude - winding 2", "A"),
    "s_2": ("Apparent power - winding 2", "VA"),
    "p_3": ("Active power - winding 3", "W"),
    "q_3": ("Reactive power - winding 3", "var"),
    "i_3": ("Current magnitude - winding 3", "A"),
    "s_3": ("Apparent power - winding 3", "VA"),
    # Derived uncertainty-relative discrepancies
    "u_residual_over_sigma": ("Voltage magnitude discrepancy / sigma", ""),
    "p_residual_over_sigma": ("Active power discrepancy / sigma", ""),
    "q_residual_over_sigma": ("Reactive power discrepancy / sigma", ""),
    # State-estimation sensor residuals
    "u_residual": ("Voltage magnitude residual", "V"),
    "u_angle_residual": ("Voltage angle residual", "rad"),
    "p_residual": ("Active power residual", "W"),
    "q_residual": ("Reactive power residual", "var"),
    "i_residual": ("Current magnitude residual", "A"),
    "i_angle_residual": ("Current angle residual", "rad"),
}


def _rgb_to_hex(color: tuple[int, int, int]) -> str:
    """Convert an RGB tuple to a CSS hexadecimal colour."""
    return f"#{color[0]:02X}{color[1]:02X}{color[2]:02X}"


def build_electrical_legend(
    scenario_index: int,
    summary: dict[str, float | int | None],
    *,
    quantity: str = "u_pu",
    component_group: str = "node",
) -> html.Div:
    """Create a labelled legend for the selected electrical quantity."""
    minimum = summary.get("minimum")
    maximum = summary.get("maximum")
    missing_count = int(summary.get("missing_count") or 0)

    quantity_label, unit = QUANTITY_LABELS.get(quantity, (quantity, ""))
    unit_suffix = f" ({unit})" if unit else ""
    component_label = "nodes" if component_group == "node" else f"{component_group.replace('_', ' ')} elements"

    has_values = minimum is not None and maximum is not None
    has_range = has_values and minimum != maximum

    statistics = html.Div(
        [
            html.Div(
                [
                    html.Span(
                        "Minimum",
                        className="electrical-stat-label",
                    ),
                    html.Strong(
                        f"{minimum:.4f}" if minimum is not None else "N/A",
                        className="electrical-stat-value",
                    ),
                ],
                className="electrical-stat",
            ),
            html.Div(
                [
                    html.Span(
                        "Maximum",
                        className="electrical-stat-label",
                    ),
                    html.Strong(
                        f"{maximum:.4f}" if maximum is not None else "N/A",
                        className="electrical-stat-value",
                    ),
                ],
                className="electrical-stat",
            ),
            html.Div(
                [
                    html.Span(
                        f"Missing {component_label}",
                        className="electrical-stat-label",
                    ),
                    html.Strong(
                        str(missing_count),
                        className="electrical-stat-value",
                    ),
                ],
                className="electrical-stat",
            ),
        ],
        className="electrical-legend-statistics",
    )

    content = [
        html.H3(
            f"{quantity_label}{unit_suffix} - Scenario {scenario_index + 1}",
            className="electrical-legend-title",
        ),
        statistics,
    ]

    if has_range:
        content.extend(
            [
                html.Div(
                    "Relative value colour scale",
                    className="electrical-scale-title",
                ),
                html.Div(
                    className="electrical-scale-bar",
                    style={
                        "background": (
                            "linear-gradient(to right, "
                            + ", ".join(
                                f"{_rgb_to_hex(color)} {index * 100 / (len(RAINBOW_STOPS) - 1):.3f}%"
                                for index, color in enumerate(RAINBOW_STOPS)
                            )
                            + ")"
                        ),
                    },
                    role="img",
                    **cast(
                        dict[str, Any],
                        {
                            "aria-label": (
                                f"Colour scale from {minimum:.4f} {unit} in purple to {maximum:.4f} {unit} in red."
                            ),
                        },
                    ),
                ),
                html.Div(
                    [
                        html.Span(f"Low: {minimum:.4f} {unit}"),
                        html.Span(f"High: {maximum:.4f} {unit}"),
                    ],
                    className="electrical-scale-endpoints",
                ),
            ]
        )

    elif has_values:
        content.append(
            html.P(
                "All displayed values are equal. A single midpoint colour is used.",
                className="electrical-legend-note",
            )
        )

    else:
        content.append(
            html.P(
                f"No {quantity_label.lower()} values are available for the displayed {component_label}.",
                className="electrical-legend-note",
            )
        )

    if missing_count:
        content.append(
            html.Div(
                [
                    html.Span(
                        className="electrical-missing-swatch",
                        style={
                            "backgroundColor": MISSING_COLOR,
                        },
                        **cast(
                            dict[str, Any],
                            {
                                "aria-hidden": "true",
                            },
                        ),
                    ),
                    html.Span(f"Grey indicates missing values ({missing_count} {component_label})."),
                ],
                className="electrical-missing-description",
            )
        )

    if quantity in {"u_residual_over_sigma", "p_residual_over_sigma", "q_residual_over_sigma"}:
        content.append(
            html.P(
                "Absolute residual divided by measurement sigma (dimensionless). "
                "Missing, invalid or non-finite ratios are excluded from the colour scale. "
                "For multiple sensors, the largest finite ratio is displayed; ties use the lowest sensor ID. "
                "Statistics describe displayed elements.",
                className="electrical-legend-note",
            )
        )
    elif component_group in SENSOR_GROUPS:
        content.append(
            html.P(
                "For multiple sensor results on an element, the largest absolute residual is displayed with its sign. "
                "Equal magnitudes use the lowest sensor ID. Statistics describe displayed elements.",
                className="electrical-legend-note",
            )
        )

    content.append(
        html.P(
            "Colours show relative values only; they do not establish whether an electrical value is acceptable.",
            className="electrical-legend-note",
        )
    )

    return html.Div(
        content,
        className="electrical-legend-content",
    )
