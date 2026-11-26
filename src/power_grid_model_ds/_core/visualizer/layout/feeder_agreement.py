# SPDX-FileCopyrightText: Contributors to the Power Grid Model project <powergridmodel@lfenergy.org>
#
# SPDX-License-Identifier: MPL-2.0

"""Read-only Dash presentation for F13 aggregated agreement records."""

from typing import Any, cast

from dash import dcc, html

from power_grid_model_ds._core.visualizer.feeder_agreement import (
    AgreementGroup,
    AgreementOverview,
    AgreementRecord,
)
from power_grid_model_ds._core.visualizer.feeder_agreement_selection import (
    MeasurementPage,
    MeasurementSort,
    build_page_window,
    paginate_measurements,
)

# Dash component IDs. Keep these stable for existing callbacks.
PANEL_ID = "f13-agreement-panel"
SUMMARY_ID = "f13-agreement-summary"
GROUP_ID = "f13-agreement-group"
GROUP_OPTIONS_ID = "f13-agreement-group-options"
DETAILS_ID = "f13-agreement-details"
SORT_ID = "f13-agreement-sort"
SCOPE_BUTTON_TYPE = "f13-agreement-scope"
PAGE_STORE_ID = "f13-agreement-page"
PAGE_STATUS_ID = "f13-agreement-page-status"
PREVIOUS_ID = "f13-agreement-previous"
NEXT_ID = "f13-agreement-next"
PAGE_NUMBERS_ID = "f13-agreement-page-numbers"
PAGE_BUTTON_TYPE = "f13-agreement-page-number"

# Presentation constants.
# Match the existing component inspector where appropriate.
BORDER_COLOR = "#dee2e6"
HEADER_BACKGROUND = "#f1f3f5"
TEXT_COLOR = "#212529"
SECONDARY_TEXT_COLOR = "#495057"
VALUE_COLOR = "#084298"

BODY_FONT_SIZE = "1rem"
SUPPORTING_FONT_SIZE = "0.875rem"
BODY_LINE_HEIGHT = "1.5"

# Use scientific notation outside the compact decimal range.
SUMMARY_DECIMAL_MIN = 0.01
SUMMARY_DECIMAL_MAX = 1000000

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
# Present compact descriptive statistics for the selected scenario.
SUMMARY_CONTAINER_STYLE = {
    "width": "100%",
    "maxWidth": "100%",
    "overflowX": "auto",
    "marginTop": "12px",
    "boxSizing": "border-box",
}

SUMMARY_TABLE_STYLE = {
    "width": "100%",
    "minWidth": "0",
    "tableLayout": "auto",
    "borderCollapse": "collapse",
    "fontSize": SUPPORTING_FONT_SIZE,
    "lineHeight": BODY_LINE_HEIGHT,
    "color": TEXT_COLOR,
}

SUMMARY_HEADER_CELL_STYLE = {
    "padding": "6px 4px",
    "backgroundColor": HEADER_BACKGROUND,
    "borderBottom": TABLE_BORDER,
    "textAlign": "center",
    "fontWeight": "600",
    "fontSize": SUPPORTING_FONT_SIZE,
    "whiteSpace": "normal",
    "overflowWrap": "normal",
}

SUMMARY_CELL_STYLE = {
    "padding": "6px 4px",
    "borderBottom": TABLE_BORDER,
    "textAlign": "left",
    "overflowWrap": "normal",
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
    "color": VALUE_COLOR,
    "fontWeight": "600",
    "fontSize": "0.875rem",
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
                                "Measurement agreement",
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
                            html.Details(
                                [
                                    html.Summary(
                                        [
                                            html.Span("Voltage (V)"),
                                            html.I(
                                                className="fas fa-info-circle",
                                                **cast(
                                                    dict[str, Any],
                                                    {"aria-hidden": "true"},
                                                ),
                                            ),
                                        ],
                                        className="agreement-information-summary",
                                        **cast(
                                            dict[str, Any],
                                            {"aria-label": "Voltage measurement information"},
                                        ),
                                    ),
                                    html.P(
                                        "Statistics include available "
                                        "measurement-estimate pairs only. "
                                        "Differences do not establish estimator "
                                        "validity. Feeder attribution uses stored "
                                        "feeder IDs and is not independently "
                                        "verified.",
                                        style=SUPPORTING_TEXT_STYLE.copy(),
                                    ),
                                ],
                                className="agreement-information",
                            ),
                            html.Div(
                                "Select a scenario index to view measurements.",
                                id=SUMMARY_ID,
                                role="status",
                                style=SUPPORTING_TEXT_STYLE.copy(),
                            ),
                            dcc.Store(
                                id=GROUP_ID,
                                storage_type="memory",
                                data="network",
                            ),
                            dcc.Store(
                                id=GROUP_OPTIONS_ID,
                                storage_type="memory",
                                data=[
                                    {
                                        "label": "Entire network",
                                        "value": "network",
                                    },
                                ],
                            ),
                            html.Div(
                                [
                                    html.H5(
                                        "Measurements",
                                        className="agreement-details-title",
                                    ),
                                    html.Span(
                                        id=PAGE_STATUS_ID,
                                        role="status",
                                        className="agreement-record-count",
                                    ),
                                ],
                                className="agreement-details-heading",
                            ),
                            html.Div(
                                [
                                    html.Label(
                                        "Sort by",
                                        htmlFor=SORT_ID,
                                        className="agreement-sort-label",
                                    ),
                                    dcc.Dropdown(
                                        id=SORT_ID,
                                        options=[
                                            {
                                                "label": "Largest difference",
                                                "value": MeasurementSort.LARGEST.value,
                                            },
                                            {
                                                "label": "Smallest difference",
                                                "value": MeasurementSort.SMALLEST.value,
                                            },
                                            {
                                                "label": "Sensor ID",
                                                "value": MeasurementSort.SENSOR.value,
                                            },
                                        ],
                                        value=MeasurementSort.LARGEST.value,
                                        clearable=False,
                                        style=DROPDOWN_STYLE.copy(),
                                    ),
                                ],
                                className="agreement-sort-row",
                            ),
                            dcc.Store(
                                id=PAGE_STORE_ID,
                                storage_type="memory",
                                data=0,
                            ),
                            html.Div(id=DETAILS_ID),
                            html.Div(
                                [
                                    html.Button(
                                        "Prev",
                                        id=PREVIOUS_ID,
                                        **cast(dict[str, Any], {"aria-label": "Previous page"}),
                                        n_clicks=0,
                                        disabled=True,
                                        type="button",
                                        className="agreement-page-button",
                                    ),
                                    html.Div(
                                        id=PAGE_NUMBERS_ID,
                                        children=[],
                                        className="agreement-page-numbers",
                                    ),
                                    html.Button(
                                        "Next",
                                        id=NEXT_ID,
                                        n_clicks=0,
                                        disabled=True,
                                        type="button",
                                        className="agreement-page-button",
                                    ),
                                ],
                                className="agreement-pagination",
                                role="navigation",
                                **cast(dict[str, Any], {"aria-label": "Measurement pages"}),
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
            {"aria-label": "Measurement agreement"},
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
    rows: list[list[str | html.Button | html.Span]],
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
            className="agreement-summary-table",
        ),
        style=SUMMARY_CONTAINER_STYLE.copy(),
        className="agreement-summary-container",
    )


def _availability_counter(
    label: str,
    value: str,
) -> html.Div:
    """Render an adaptive descriptive availability counter."""
    return html.Div(
        [
            html.Div(
                label,
                className="agreement-counter-label",
            ),
            html.Div(
                value,
                className="agreement-counter-value",
            ),
        ],
        className="agreement-availability-counter",
    )


def render_scope_button(
    label: str,
    scope: str,
    *,
    selected: bool = False,
    disabled: bool = False,
) -> html.Button:
    """Render a keyboard-accessible summary scope selector."""
    return html.Button(
        label,
        id={"type": SCOPE_BUTTON_TYPE, "scope": scope},
        n_clicks=0,
        type="button",
        disabled=disabled,
        className="agreement-scope-button",
        **cast(dict[str, Any], {"aria-pressed": "true" if selected else "false"}),
    )


def _pair_count(available: int, total: int) -> html.Span:
    """Allow pair counts to wrap only between complete counts."""
    return html.Span(
        [html.Span(f"{available}/"), html.Span(str(total))],
        className="agreement-pair-count",
    )


def _summary_number(value: float | None) -> str:
    """Format discrepancies without hiding small nonzero values."""
    if value is None:
        return "\u2014"

    if 0 < abs(value) < SUMMARY_DECIMAL_MIN or abs(value) >= SUMMARY_DECIMAL_MAX:
        mantissa, exponent = f"{value:.2e}".split("e")
        mantissa = mantissa.rstrip("0").rstrip(".")
        return f"{mantissa}e{int(exponent)}"

    formatted = f"{value:.2f}"
    return formatted.rstrip("0").rstrip(".")


def render_summary(
    overview: AgreementOverview,
    selection: str = "network",
) -> html.Div:
    """Display availability and descriptive voltage discrepancies."""
    groups = [
        ("Entire network", "network", overview.network),
        *[(f"Feeder {feeder_id}", f"feeder:{feeder_id}", group) for feeder_id, group in overview.feeders.items()],
        ("Unassigned", "unassigned", overview.unassigned),
    ]

    rows: list[list[str | html.Button | html.Span]] = []

    for label, scope, group in groups:
        statistics = group.discrepancy_statistics()

        rows.append(
            [
                render_scope_button(
                    label,
                    scope,
                    selected=scope == selection,
                    disabled=scope == "unassigned" and not group.total_count,
                ),
                _pair_count(group.available_count, group.total_count),
                _summary_number(statistics.minimum),
                _summary_number(statistics.mean),
                _summary_number(statistics.maximum),
            ]
        )

    return html.Div(
        [
            html.Div(
                [
                    _availability_counter(
                        "Available",
                        (f"{overview.network.available_count}/{overview.network.total_count}"),
                    ),
                    _availability_counter(
                        "Unavailable",
                        str(overview.network.unavailable_count),
                    ),
                ],
                style={
                    "display": "grid",
                    "gridTemplateColumns": "repeat(2, minmax(0, 1fr))",
                    "gap": "8px",
                    "marginBottom": "10px",
                },
            ),
            _table(
                [
                    "Scope",
                    "Pairs",
                    "Min",
                    "Mean",
                    "Max",
                ],
                rows,
            ),
            html.P(
                "Absolute difference |\u0394| (V). Pairs: available/total.",
                style=FOOTNOTE_STYLE.copy(),
            ),
        ]
    )


def _number(value: float | None) -> str:
    """Format an available number or show a missing-value marker."""
    return "—" if value is None else f"{value:.6g}"


def _measurement_attributes(record: AgreementRecord) -> list[tuple[str, str]]:
    """Prepare attribute/value rows for a measurement."""
    return [
        ("Quantity", record.quantity),
        ("Measured", _number(record.measured)),
        ("Estimated", _number(record.estimated)),
        ("Absolute difference", _number(record.absolute_discrepancy)),
        ("Unit", record.unit),
        ("Data status", record.status.value.replace("_", " ").capitalize()),
        (
            "Feeder ID",
            "Unassigned" if record.feeder_id is None else str(record.feeder_id),
        ),
        ("Feeder status", record.feeder_status.value.capitalize()),
    ]


def _measurement_card(
    record: AgreementRecord,
) -> html.Details:
    """Render an expandable measurement with a visible summary."""
    attributes = _measurement_attributes(record)

    difference = record.absolute_discrepancy
    difference_label = "Unavailable" if difference is None else f"{_summary_number(difference)} {record.unit}"

    status = record.status.value.replace("_", " ").capitalize()

    return html.Details(
        [
            html.Summary(
                [
                    html.Span(
                        [
                            html.Span(
                                f"Sensor {record.sensor_id}",
                                className="agreement-measurement-title",
                            ),
                            html.Span(
                                f"Node {record.component_id} \u00b7 {status}",
                                className="agreement-measurement-status",
                            ),
                        ],
                        className="agreement-measurement-identity",
                    ),
                    html.Span(
                        difference_label,
                        className="agreement-measurement-value",
                    ),
                    html.I(
                        className="fas fa-chevron-down agreement-card-chevron",
                        **cast(dict[str, Any], {"aria-hidden": "true"}),
                    ),
                ],
                className="agreement-measurement-summary",
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
        open=False,
        className="agreement-measurement-card",
    )


def render_measurement_page(
    page: MeasurementPage,
) -> html.Div:
    """Render prepared measurement records without sorting again."""
    return html.Div(
        [_measurement_card(record) for record in page.records],
        style=DETAILS_CONTAINER_STYLE.copy(),
    )


def render_details(
    overview: AgreementOverview,
    selection: str | None,
    *,
    sort_mode: MeasurementSort = MeasurementSort.LARGEST,
    page_index: int = 0,
) -> html.Div:
    """Show one page of contributing measurements."""
    group = selected_group(overview, selection)

    if group is None:
        return html.Div(
            "The selected group is not available for this scenario.",
            role="status",
            style=SUPPORTING_TEXT_STYLE.copy(),
        )

    if not group.records:
        return html.Div(
            "No contributing measurements in this group.",
            role="status",
            style=SUPPORTING_TEXT_STYLE.copy(),
        )

    page = paginate_measurements(
        group,
        sort_mode=sort_mode,
        page_index=page_index,
    )

    return render_measurement_page(page)


def render_page_numbers(page: MeasurementPage) -> list[html.Button | html.Span]:
    """Render bounded page controls without preparing measurement data again."""
    controls: list[html.Button | html.Span] = []
    for index in build_page_window(page.page_index, page.page_count):
        if index is None:
            controls.append(
                html.Span(
                    "\u2026",
                    className="agreement-page-ellipsis",
                    **cast(dict[str, Any], {"aria-hidden": "true"}),
                )
            )
            continue

        active = index == page.page_index
        controls.append(
            html.Button(
                str(index + 1),
                id={"type": PAGE_BUTTON_TYPE, "page": index},
                type="button",
                n_clicks=0,
                className="agreement-page-number",
                **cast(
                    dict[str, Any],
                    {
                        "aria-label": f"Page {index + 1}",
                        "aria-current": "page" if active else "false",
                    },
                ),
            )
        )
    return controls
