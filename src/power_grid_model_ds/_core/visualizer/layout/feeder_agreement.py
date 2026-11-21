# SPDX-FileCopyrightText: Contributors to the Power Grid Model project <powergridmodel@lfenergy.org>
#
# SPDX-License-Identifier: MPL-2.0

"""Read-only Dash presentation for F13 aggregated agreement records."""

from typing import Any, cast

from dash import dcc, html

from power_grid_model_ds._core.visualizer.feeder_agreement import (
    AgreementGroup,
    AgreementOverview,
)

# Dash component IDs. Keep these stable for existing callbacks.
PANEL_ID = "f13-agreement-panel"
SUMMARY_ID = "f13-agreement-summary"
GROUP_ID = "f13-agreement-group"
DETAILS_ID = "f13-agreement-details"

# Presentation constants.
# Match the existing component inspector where appropriate.
BORDER_COLOR = "#dee2e6"
HEADER_BACKGROUND = "#f8f9fa"
TEXT_COLOR = "#212529"
SECONDARY_TEXT_COLOR = "#495057"
VALUE_COLOR = "#0d6efd"

BODY_FONT_SIZE = "1rem"
SUPPORTING_FONT_SIZE = "0.875rem"
BODY_LINE_HEIGHT = "1.5"

PANEL_PADDING = "12px"
CELL_PADDING = "10px"
SUMMARY_CELL_PADDING = "10px 8px"

TABLE_BORDER = f"1px solid {BORDER_COLOR}"


# General typography.
BODY_TEXT_STYLE = {
    "fontSize": BODY_FONT_SIZE,
    "lineHeight": BODY_LINE_HEIGHT,
    "color": TEXT_COLOR,
}

SUPPORTING_TEXT_STYLE = {
    "fontSize": SUPPORTING_FONT_SIZE,
    "lineHeight": BODY_LINE_HEIGHT,
    "color": SECONDARY_TEXT_COLOR,
}

SECTION_TITLE_STYLE = {
    "fontSize": "1.25rem",
    "fontWeight": "600",
    "lineHeight": "1.4",
    "color": TEXT_COLOR,
    "marginBottom": "12px",
}

SENSOR_TITLE_STYLE = {
    "fontSize": "1.125rem",
    "fontWeight": "600",
    "lineHeight": "1.4",
    "color": TEXT_COLOR,
    "marginTop": "16px",
    "marginBottom": "10px",
}


# Outer panel.
# Avoid an additional border around the whole F13 section.
PANEL_STYLE = {
    "padding": PANEL_PADDING,
    "marginBottom": "18px",
    "minWidth": 0,
    "width": "100%",
    "boxSizing": "border-box",
}

DESCRIPTION_STYLE = {
    **SUPPORTING_TEXT_STYLE,
    "marginBottom": "16px",
}

FOOTNOTE_STYLE = {
    **SUPPORTING_TEXT_STYLE,
    "marginTop": "16px",
    "marginBottom": "0",
}

SCENARIO_STYLE = {
    **BODY_TEXT_STYLE,
    "marginBottom": "10px",
}

GROUP_LABEL_STYLE = {
    **BODY_TEXT_STYLE,
    "display": "block",
    "fontWeight": "600",
    "marginTop": "16px",
    "marginBottom": "8px",
}

DROPDOWN_STYLE = {
    "width": "100%",
    "minWidth": 0,
    "fontSize": BODY_FONT_SIZE,
    "color": TEXT_COLOR,
}


# Summary table.
# Keep the existing four-column information structure.
SUMMARY_CONTAINER_STYLE = {
    "width": "100%",
    "maxWidth": "100%",
    "overflowX": "auto",
    "marginTop": "12px",
}

SUMMARY_TABLE_STYLE = {
    "width": "100%",
    "borderCollapse": "collapse",
    "fontSize": SUPPORTING_FONT_SIZE,
    "lineHeight": BODY_LINE_HEIGHT,
    "color": TEXT_COLOR,
}

SUMMARY_HEADER_CELL_STYLE = {
    "padding": SUMMARY_CELL_PADDING,
    "backgroundColor": HEADER_BACKGROUND,
    "borderBottom": TABLE_BORDER,
    "textAlign": "left",
    "fontWeight": "600",
    "overflowWrap": "anywhere",
}

SUMMARY_CELL_STYLE = {
    "padding": SUMMARY_CELL_PADDING,
    "borderBottom": TABLE_BORDER,
    "textAlign": "left",
    "overflowWrap": "anywhere",
}


# Measurement details.
DETAILS_CONTAINER_STYLE = {
    "width": "100%",
    "minWidth": 0,
    "marginTop": "12px",
}

DETAILS_COUNT_STYLE = {
    **BODY_TEXT_STYLE,
    "marginTop": "12px",
    "marginBottom": "12px",
}

MEASUREMENT_CARD_STYLE = {
    "width": "100%",
    "minWidth": 0,
    "marginBottom": "20px",
}

DETAILS_TABLE_STYLE = {
    "width": "100%",
    "borderCollapse": "collapse",
    "tableLayout": "fixed",
    "fontSize": BODY_FONT_SIZE,
    "lineHeight": BODY_LINE_HEIGHT,
    "color": TEXT_COLOR,
    "border": TABLE_BORDER,
    "borderRadius": "8px",
    "overflowWrap": "anywhere",
}

DETAILS_HEADER_CELL_STYLE = {
    "width": "50%",
    "padding": CELL_PADDING,
    "backgroundColor": HEADER_BACKGROUND,
    "borderBottom": TABLE_BORDER,
    "textAlign": "left",
    "fontWeight": "600",
    "overflowWrap": "anywhere",
}

DETAILS_ATTRIBUTE_CELL_STYLE = {
    "width": "50%",
    "padding": CELL_PADDING,
    "borderRight": TABLE_BORDER,
    "borderBottom": TABLE_BORDER,
    "verticalAlign": "top",
    "overflowWrap": "anywhere",
}

DETAILS_VALUE_CELL_STYLE = {
    "width": "50%",
    "padding": CELL_PADDING,
    "borderBottom": TABLE_BORDER,
    "verticalAlign": "top",
    "overflowWrap": "anywhere",
    "color": VALUE_COLOR,
}

SUMMARY_VALUE_CELL_STYLE = {
    **SUMMARY_CELL_STYLE,
    "color": "#0d6efd",
    "fontWeight": "600",
    "fontSize": "1rem",
    "textAlign": "center",
    "fontVariantNumeric": "tabular-nums",
}


def get_feeder_agreement_html() -> html.Section:
    """Build a collapsible F13 overview with persistent callback targets."""
    return html.Section(
        [
            html.Details(
                [
                    html.Summary(
                        [
                            html.I(
                                className=("fas fa-chart-bar network-state-icon"),
                                **cast(
                                    dict[str, Any],
                                    {"aria-hidden": "true"},
                                ),
                            ),
                            html.H4(
                                "Aggregated agreement overview",
                                className="network-state-title",
                            ),
                            html.I(
                                className=("fas fa-chevron-down network-state-chevron"),
                                **cast(
                                    dict[str, Any],
                                    {"aria-hidden": "true"},
                                ),
                            ),
                        ],
                        className="network-state-summary",
                    ),
                    html.Div(
                        [
                            html.P(
                                "Measured and estimated symmetric voltage "
                                "records. Counts describe data availability, "
                                "not estimator validity.",
                                style=DESCRIPTION_STYLE.copy(),
                            ),
                            html.Div(
                                "Select a scenario index to view measurements.",
                                id=SUMMARY_ID,
                                role="status",
                            ),
                            html.Label(
                                "Inspect contributing measurements",
                                htmlFor=GROUP_ID,
                                style=GROUP_LABEL_STYLE.copy(),
                            ),
                            dcc.Dropdown(
                                id=GROUP_ID,
                                options=[
                                    {
                                        "label": "Entire network",
                                        "value": "network",
                                    },
                                ],
                                value="network",
                                clearable=False,
                                style=DROPDOWN_STYLE.copy(),
                            ),
                            html.Div(id=DETAILS_ID),
                            html.P(
                                "Feeder attribution is based on stored feeder "
                                "IDs and is not independently verified by "
                                "this overview.",
                                style=FOOTNOTE_STYLE.copy(),
                            ),
                        ],
                        className="network-state-controls",
                    ),
                ],
                id="f13-agreement-details-section",
                open=True,
                className="network-state-details",
            ),
        ],
        id=PANEL_ID,
        style=PANEL_STYLE.copy(),
        **cast(
            dict[str, Any],
            {"aria-label": "Aggregated agreement overview"},
        ),
    )


def group_options(
    overview: AgreementOverview,
) -> list[dict[str, str]]:
    """Provide network, feeder and unassigned drilldown choices."""
    options = [
        {
            "label": "Entire network",
            "value": "network",
        },
    ]

    options.extend(
        {
            "label": f"Feeder {feeder_id}",
            "value": f"feeder:{feeder_id}",
        }
        for feeder_id in overview.feeders
    )

    if overview.unassigned.total_count:
        options.append(
            {
                "label": "Unassigned measurements",
                "value": "unassigned",
            }
        )

    return options


def selected_group(
    overview: AgreementOverview,
    selection: str | None,
) -> AgreementGroup | None:
    """Resolve a drilldown choice without modifying the overview."""
    if selection == "network":
        return overview.network

    if selection == "unassigned":
        return overview.unassigned

    if isinstance(selection, str) and selection.startswith("feeder:"):
        try:
            feeder_id = int(selection.removeprefix("feeder:"))
        except ValueError:
            return None

        return overview.feeders.get(feeder_id)

    return None


def _table(
    headers: list[str],
    rows: list[list[str]],
) -> html.Div:
    """Render the descriptive summary with semantic table markup."""
    return html.Div(
        html.Table(
            [
                html.Thead(
                    html.Tr(
                        [
                            html.Th(
                                header,
                                scope="col",
                                style=SUMMARY_HEADER_CELL_STYLE.copy(),
                            )
                            for header in headers
                        ]
                    )
                ),
                html.Tbody(
                    [
                        html.Tr(
                            [
                                html.Td(
                                    value,
                                    style=(
                                        SUMMARY_CELL_STYLE.copy() if index == 0 else SUMMARY_VALUE_CELL_STYLE.copy()
                                    ),
                                )
                                for index, value in enumerate(row)
                            ]
                        )
                        for row in rows
                    ]
                ),
            ],
            style=SUMMARY_TABLE_STYLE.copy(),
        ),
        style=SUMMARY_CONTAINER_STYLE.copy(),
    )


def render_summary(
    overview: AgreementOverview,
) -> html.Div:
    """Display descriptive counts without an agreement score."""
    groups = [
        ("Entire network", overview.network),
        *[(f"Feeder {feeder_id}", group) for feeder_id, group in overview.feeders.items()],
        ("Unassigned", overview.unassigned),
    ]

    rows = [
        [
            label,
            str(group.total_count),
            str(group.available_count),
            str(group.unavailable_count),
        ]
        for label, group in groups
    ]

    return html.Div(
        _table(
            [
                "Scope",
                "Total",
                "Available",
                "Unavailable",
            ],
            rows,
        )
    )


def _number(value: float | None) -> str:
    """Format an available number or show a missing-value marker."""
    return "—" if value is None else f"{value:.6g}"


def _measurement_attributes(record) -> list[tuple[str, str]]:
    """Prepare attribute/value rows for a measurement."""
    return [
        ("Quantity", record.quantity),
        ("Measured", _number(record.measured)),
        ("Estimated", _number(record.estimated)),
        ("Unit", record.unit),
        ("Data status", record.status.value),
        (
            "Feeder ID",
            "Unassigned" if record.feeder_id is None else str(record.feeder_id),
        ),
        ("Feeder status", record.feeder_status.value),
    ]


def _measurement_card(record) -> html.Div:
    """Render a measurement using the existing inspector's visual style."""
    attributes = _measurement_attributes(record)

    return html.Div(
        [
            html.H5(
                f"Sensor {record.sensor_id} — Node {record.component_id}",
                style=SENSOR_TITLE_STYLE.copy(),
            ),
            html.Table(
                [
                    html.Thead(
                        html.Tr(
                            [
                                html.Th(
                                    "Attribute",
                                    scope="col",
                                    style=DETAILS_HEADER_CELL_STYLE.copy(),
                                ),
                                html.Th(
                                    "Value",
                                    scope="col",
                                    style=DETAILS_HEADER_CELL_STYLE.copy(),
                                ),
                            ]
                        )
                    ),
                    html.Tbody(
                        [
                            html.Tr(
                                [
                                    html.Td(
                                        name,
                                        style=DETAILS_ATTRIBUTE_CELL_STYLE.copy(),
                                    ),
                                    html.Td(
                                        value,
                                        style=DETAILS_VALUE_CELL_STYLE.copy(),
                                    ),
                                ]
                            )
                            for name, value in attributes
                        ]
                    ),
                ],
                style=DETAILS_TABLE_STYLE.copy(),
            ),
        ],
        style=MEASUREMENT_CARD_STYLE.copy(),
    )


def render_details(
    overview: AgreementOverview,
    selection: str | None,
) -> html.Div:
    """Show contributing measurements as attribute/value tables."""
    group = selected_group(overview, selection)

    if group is None:
        return html.Div(
            "The selected group is not available for this scenario.",
            role="status",
        )

    if not group.records:
        return html.Div(
            "No contributing measurements in this group.",
            role="status",
        )

    return html.Div(
        [_measurement_card(record) for record in group.records],
        style=DETAILS_CONTAINER_STYLE.copy(),
    )
