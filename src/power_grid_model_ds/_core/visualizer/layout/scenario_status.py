# SPDX-FileCopyrightText: Contributors to the Power Grid Model project <powergridmodel@lfenergy.org>
#
# SPDX-License-Identifier: MPL-2.0

"""Display batch scenario calculation status."""

from dash import html

from power_grid_model_ds._core.visualizer.scenario_status import ScenarioStatus

_PANEL_STYLE = {
    "backgroundColor": "#ffffff",
    "color": "#212529",
    "padding": "12px",
    "border": "1px solid #dee2e6",
    "borderRadius": "8px",
    "fontSize": "13px",
}

_HEADING_STYLE = {
    "fontSize": "14px",
    "fontWeight": "600",
    "margin": "0",
}

_SUMMARY_STYLE = {
    "display": "grid",
    "gridTemplateColumns": "repeat(2, minmax(0, 1fr))",
    "gap": "8px",
    "marginTop": "12px",
}

_STATUS_CARD_STYLE = {
    "border": "1px solid #e2e8f0",
    "borderRadius": "8px",
    "padding": "10px",
    "minWidth": "0",
}

_DETAILS_STYLE = {
    "marginTop": "12px",
    "paddingTop": "10px",
    "borderTop": "1px solid #e2e8f0",
}

_NOTE_STYLE = {
    "display": "flex",
    "alignItems": "flex-start",
    "gap": "7px",
    "marginTop": "12px",
    "fontSize": "12px",
    "color": "#64748b",
}


def _icon(name: str, color: str, size: str = "16px") -> html.I:
    """Return a decorative Bootstrap Icon."""
    return html.I(
        className=f"bi bi-{name}",
        **{"aria-hidden": "true"},
        style={"color": color, "fontSize": size},
    )


def _status_card(count: int, label: str, icon: str, color: str) -> html.Div:
    """Display a reported outcome count with its label."""
    return html.Div(
        [
            html.Div(
                [
                    _icon(icon, color, "18px"),
                    html.Span(
                        str(count),
                        style={
                            "fontSize": "20px",
                            "fontWeight": "600",
                            "lineHeight": "1.2",
                        },
                    ),
                ],
                style={
                    "display": "flex",
                    "alignItems": "center",
                    "gap": "8px",
                },
            ),
            html.Div(
                label,
                style={
                    "fontSize": "12px",
                    "color": "#64748b",
                    "marginTop": "5px",
                },
            ),
        ],
        style=_STATUS_CARD_STYLE,
    )


def _get_status_summary(succeeded: int, failed: int) -> html.Div:
    """Display succeeded and failed scenario counts."""
    return html.Div(
        [
            _status_card(succeeded, "succeeded", "check-circle-fill", "#176b38"),
            _status_card(failed, "failed", "x-circle-fill", "#a61b1b"),
        ],
        style=_SUMMARY_STYLE,
    )


def _get_failure_details(status: ScenarioStatus) -> html.Details:
    """Show individual failed scenarios in an expandable section."""
    failures = []

    for scenario in sorted(status.failed_scenarios):
        message = status.error_for(scenario)
        description = f"Scenario {scenario}: {message}" if message else f"Scenario {scenario}: calculation failed"
        failures.append(
            html.Li(
                description,
                style={"marginBottom": "6px", "overflowWrap": "anywhere"},
            )
        )

    failed = len(status.failed_scenarios)

    return html.Details(
        [
            html.Summary(
                [
                    _icon("exclamation-circle", "#a61b1b"),
                    html.Span(f"Show failed scenarios ({failed})"),
                    _icon("chevron-down", "#64748b", "12px"),
                ],
                style={
                    "display": "flex",
                    "alignItems": "center",
                    "gap": "8px",
                    "cursor": "pointer",
                    "fontWeight": "600",
                    "listStyle": "none",
                },
            ),
            html.Ul(
                failures,
                style={
                    "margin": "10px 0 0",
                    "paddingLeft": "20px",
                    "fontSize": "12px",
                },
            ),
        ],
        style=_DETAILS_STYLE,
    )


def _information_note(text: str) -> html.Div:
    """Display a concise note without implying unreported outcomes succeeded."""
    return html.Div(
        [
            _icon("info-circle", "#64748b", "13px"),
            html.Span(text),
        ],
        style=_NOTE_STYLE,
    )


def get_scenario_status_html(status: ScenarioStatus | None) -> html.Section:
    """Build a compact summary of reported scenario outcomes."""
    heading = html.Div(
        [
            _icon("activity", "#64748b"),
            html.H2(
                "Calculation status",
                id="scenario-status-heading",
                style=_HEADING_STYLE,
            ),
        ],
        style={
            "display": "flex",
            "alignItems": "center",
            "gap": "8px",
        },
    )

    if status is None:
        content = [
            heading,
            _information_note("Calculation status unavailable. Output validity has not been verified."),
        ]
    else:
        succeeded = len(status.succeeded_scenarios)
        failed = len(status.failed_scenarios)

        content = [
            heading,
            _get_status_summary(succeeded, failed),
        ]

        if failed:
            content.append(_get_failure_details(status))

        content.append(
            _information_note(
                "Only reported calculation outcomes are counted. The status of any other scenarios is unknown."
            )
        )

    return html.Section(
        content,
        id="scenario-status",
        **{"aria-labelledby": "scenario-status-heading"},
        style=_PANEL_STYLE,
    )
