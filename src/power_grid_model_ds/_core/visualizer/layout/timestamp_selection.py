# SPDX-FileCopyrightText: Contributors to the Power Grid Model project <powergridmodel@lfenergy.org>
#
# SPDX-License-Identifier: MPL-2.0

"""F05 date-and-time selection layout."""

from datetime import date

from dash import dcc, html

from power_grid_model_ds._core.visualizer.server_state import get_timestamps


def _available_dates(timestamps: tuple[str, ...]) -> list[str]:
    """Return distinct observation dates in chronological order."""
    return sorted({timestamp[:10] for timestamp in timestamps})


def _disabled_dates(dates: list[str]) -> list[str]:
    """Return dates without observations within the available range."""
    if not dates:
        return []

    first = date.fromisoformat(dates[0])
    last = date.fromisoformat(dates[-1])
    available = set(dates)

    return [
        current.isoformat()
        for ordinal in range(first.toordinal(), last.toordinal() + 1)
        if (current := date.fromordinal(ordinal)).isoformat() not in available
    ]


def _time_options(
    timestamps: tuple[str, ...],
    selected_date: str,
) -> list[dict[str, str | int]]:
    """Map available times to their original scenario indices."""
    return [
        {
            "label": timestamp[11:],
            "value": index,
        }
        for index, timestamp in enumerate(timestamps)
        if timestamp[:10] == selected_date
    ]


def get_timestamp_selection_html() -> html.Div:
    """Build collapsible network-state controls and component details."""
    timestamps = get_timestamps()

    if not timestamps:
        return html.Div(id="timestamp-selection-container")

    dates = _available_dates(timestamps)
    initial_date = timestamps[0][:10]
    initial_options = _time_options(timestamps, initial_date)

    return html.Div(
        [
            html.Details(
                [
                    html.Summary(
                        [
                            html.I(
                                className="fas fa-clock network-state-icon",
                                **{"aria-hidden": "true"},  # type: ignore[arg-type]
                            ),
                            html.H4(
                                "Network state",
                                className="network-state-title",
                            ),
                            html.I(
                                className="fas fa-chevron-down network-state-chevron",
                                **{"aria-hidden": "true"},  # type: ignore[arg-type]
                            ),
                        ],
                        className="network-state-summary",
                    ),
                    html.Div(
                        [
                            html.P(
                                "Inspect network components at an available timestamp.",
                                className="network-state-description text-muted",
                            ),
                            html.Div(
                                [
                                    html.Div(
                                        [
                                            html.Label(
                                                "Observation date",
                                                htmlFor="timestamp-date",
                                                className="form-label fw-semibold",
                                            ),
                                            dcc.DatePickerSingle(
                                                id="timestamp-date",
                                                date=initial_date,
                                                min_date_allowed=dates[0],
                                                max_date_allowed=dates[-1],
                                                disabled_days=_disabled_dates(dates),
                                                display_format="DD MMM YYYY",
                                                clearable=False,
                                                first_day_of_week=1,
                                                number_of_months_shown=1,
                                                day_size=27,
                                            ),
                                        ],
                                        className="timestamp-control-field",
                                    ),
                                    html.Div(
                                        [
                                            html.Label(
                                                "Available time",
                                                htmlFor="timestamp-time",
                                                className="form-label fw-semibold",
                                            ),
                                            dcc.Dropdown(
                                                id="timestamp-time",
                                                options=initial_options,
                                                value=initial_options[0]["value"],
                                                clearable=False,
                                                searchable=True,
                                                className="timestamp-dropdown",
                                            ),
                                        ],
                                        className="timestamp-control-field",
                                    ),
                                ],
                                className="timestamp-controls-row",
                            ),
                        ],
                        className="network-state-controls",
                    ),
                    html.Hr(className="my-3"),
                    html.Div(
                        id="timestamp-state-output",
                        children=None,
                    ),
                ],
                id="network-state-details",
                open=True,
                className="network-state-details",
            ),
            dcc.Dropdown(
                id="timestamp-selector",
                options=[{"label": timestamp, "value": index} for index, timestamp in enumerate(timestamps)],
                value=0,
                clearable=False,
                style={"display": "none"},
            ),
        ],
        id="timestamp-selection-container",
        className="card shadow-sm border-0",
        style={
            "padding": "16px",
            "margin": "0",
            "borderRadius": "12px",
        },
    )
