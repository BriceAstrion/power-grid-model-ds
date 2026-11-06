# SPDX-FileCopyrightText: Contributors to the Power Grid Model project <powergridmodel@lfenergy.org>
#
# SPDX-License-Identifier: MPL-2.0

"""Layout for selected-node diagnostics."""

from dash import html


def get_diagnostic_overview_html():
    """Build the selected-node diagnostics panel."""
    return html.Section(
        [
            html.H2(
                "Selected-node diagnostics",
                id="diagnostic-overview-heading",
                style={"fontSize": "20px", "fontWeight": "600"},
            ),
            html.Div(
                "Select a network node to view diagnostics.",
                id="diagnostic-overview-content",
                role="status",
            ),
        ],
        id="diagnostic-overview",
        **{"aria-labelledby": "diagnostic-overview-heading"},
        style={
            "backgroundColor": "#ffffff",
            "color": "#212529",
            "padding": "16px 20px",
            "borderBottom": "1px solid #ced4da",
        },
    )
