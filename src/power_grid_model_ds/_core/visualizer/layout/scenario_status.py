# SPDX-FileCopyrightText: Contributors to the Power Grid Model project <powergridmodel@lfenergy.org>
#
# SPDX-License-Identifier: MPL-2.0

"""Display batch scenario calculation status."""

from dash import html

from power_grid_model_ds._core.visualizer.scenario_status import ScenarioStatus

_PANEL_STYLE = {
    "backgroundColor": "#ffffff",
    "color": "#212529",
    "padding": "16px 20px",
    "borderBottom": "1px solid #ced4da",
    "fontSize": "16px",
}

_SUMMARY_STYLE = {
    "display": "flex",
    "flexWrap": "wrap",
    "gap": "24px",
    "marginBottom": "12px",
}

_STATUS_ITEM_STYLE = {
    "display": "flex",
    "alignItems": "center",
    "gap": "10px",
}

_HEADING_STYLE = {
    "fontSize": "20px",
    "fontWeight": "600",
    "margin": "0 0 12px",
}

_DETAILS_STYLE = {
    "marginTop": "12px",
    "padding": "12px",
    "border": "1px solid #ced4da",
    "borderRadius": "4px",
}

_SUCCESS_ICON_STYLE = {
    "color": "#176b38",
    "fontSize": "22px",
}

_FAILURE_ICON_STYLE = {
    "color": "#a61b1b",
    "fontSize": "22px",
}


def _get_status_summary(succeeded: int, failed: int) -> html.Div:
    """Display reported outcomes with accessible text labels."""
    return html.Div(
        [
            html.Div(
                [
                    html.I(
                        className="bi bi-check-circle-fill",
                        **{"aria-hidden": "true"},
                        style=_SUCCESS_ICON_STYLE,
                    ),
                    html.Span(f"{succeeded} succeeded"),
                ],
                style=_STATUS_ITEM_STYLE,
            ),
            html.Div(
                [
                    html.I(
                        className="bi bi-x-circle-fill",
                        **{"aria-hidden": "true"},
                        style=_FAILURE_ICON_STYLE,
                    ),
                    html.Span(f"{failed} failed"),
                ],
                style=_STATUS_ITEM_STYLE,
            ),
        ],
        style=_SUMMARY_STYLE,
    )


def _get_failure_details(status: ScenarioStatus) -> html.Details:
    """Show individual failed scenarios in an expandable section."""
    failures = []

    for scenario in sorted(status.failed_scenarios):
        message = status.error_for(scenario)
        description = f"Scenario {scenario}: {message}" if message else f"Scenario {scenario}: calculation failed"
        failures.append(html.Li(description))

    failed = len(status.failed_scenarios)

    return html.Details(
        [
            html.Summary(
                f"Show failed scenarios ({failed})",
                style={
                    "cursor": "pointer",
                    "fontWeight": "600",
                },
            ),
            html.Ul(
                failures,
                style={"marginBottom": "0"},
            ),
        ],
        style=_DETAILS_STYLE,
    )


def get_scenario_status_html(status: ScenarioStatus | None) -> html.Section:
    """Build a readable summary of reported scenario outcomes."""
    heading = html.H2(
        "Batch calculation status",
        id="scenario-status-heading",
        style=_HEADING_STYLE,
    )

    if status is None:
        content = [
            heading,
            html.P(
                "Calculation status unavailable. Output validity has not been verified.",
                style={"margin": "0"},
            ),
        ]
    else:
        succeeded = len(status.succeeded_scenarios)
        failed = len(status.failed_scenarios)

        content = [
            heading,
            _get_status_summary(succeeded, failed),
            html.P(
                "Only reported calculation outcomes are counted. The status of any other scenarios is unknown.",
                style={"margin": "0"},
            ),
        ]

        if failed:
            content.append(_get_failure_details(status))

    return html.Section(
        content,
        id="scenario-status",
        **{"aria-labelledby": "scenario-status-heading"},
        style=_PANEL_STYLE,
    )
