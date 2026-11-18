# SPDX-FileCopyrightText: Contributors to the Power Grid Model project <powergridmodel@lfenergy.org>
#
# SPDX-License-Identifier: MPL-2.0

"""F05 date-and-time selection layout."""

from datetime import date

from dash import dcc, html

from power_grid_model_ds._core.visualizer.server_state import get_timestamps

NETWORK_STATE_TITLE = "Network state"

NETWORK_STATE_DESCRIPTION = "Inspect network components at an available timestamp."

NO_TIMESTAMPS_MESSAGE = "Timestamp-based network inspection is unavailable because no timestamps were provided."

NETWORK_STATE_CONTAINER_CLASS = "card shadow-sm border-0"

NETWORK_STATE_CONTAINER_STYLE = {
    "padding": "16px",
    "margin": "0",
    "borderRadius": "12px",
}

HIDDEN_CONTROL_STYLE = {
    "display": "none",
}

DATE_PICKER_CONFIG = {
    "display_format": "DD MMM YYYY",
    "clearable": False,
    "first_day_of_week": 1,
    "number_of_months_shown": 1,
    "day_size": 27,
}


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


def _network_state_header() -> html.Summary:
    """Build the shared Network state header."""
    return html.Summary(
        [
            html.I(
                className="fas fa-clock network-state-icon",
                **{"aria-hidden": "true"},  # type: ignore[arg-type]
            ),
            html.H4(
                NETWORK_STATE_TITLE,
                className="network-state-title",
            ),
            html.I(
                className="fas fa-chevron-down network-state-chevron",
                **{"aria-hidden": "true"},  # type: ignore[arg-type]
            ),
        ],
        className="network-state-summary",
    )


def _network_state_container(
    details: html.Details,
    selector: dcc.Dropdown,
) -> html.Div:
    """Wrap Network state in its existing sidebar card."""
    return html.Div(
        [
            details,
            selector,
        ],
        id="timestamp-selection-container",
        className=NETWORK_STATE_CONTAINER_CLASS,
        style=NETWORK_STATE_CONTAINER_STYLE.copy(),
    )


def _no_timestamps_layout() -> html.Div:
    """Show Network state when timestamp data is unavailable."""
    details = html.Details(
        [
            _network_state_header(),
            html.Div(
                [
                    html.P(
                        NO_TIMESTAMPS_MESSAGE,
                        className=("network-state-description text-muted"),
                    ),
                    html.Div(
                        id="timestamp-state-output",
                        children=None,
                    ),
                ],
                className="network-state-controls",
            ),
        ],
        id="network-state-details",
        open=True,
        className="network-state-details",
    )

    selector = dcc.Dropdown(
        id="timestamp-selector",
        options=[],
        value=None,
        clearable=False,
        disabled=True,
        style=HIDDEN_CONTROL_STYLE.copy(),
    )

    # Keep these IDs available for existing timestamp callbacks.
    container = _network_state_container(details, selector)

    container.children.extend(
        [
            dcc.DatePickerSingle(
                id="timestamp-date",
                disabled=True,
                style=HIDDEN_CONTROL_STYLE.copy(),
            ),
            dcc.Dropdown(
                id="timestamp-time",
                options=[],
                value=None,
                disabled=True,
                style=HIDDEN_CONTROL_STYLE.copy(),
            ),
        ]
    )

    return container


def _timestamp_controls(
    timestamps: tuple[str, ...],
) -> html.Div:
    """Build date and time controls for available observations."""
    dates = _available_dates(timestamps)
    initial_date = timestamps[0][:10]
    initial_options = _time_options(timestamps, initial_date)

    return html.Div(
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
                        **DATE_PICKER_CONFIG,
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
    )


def get_timestamp_selection_html() -> html.Div:
    """Build Network state for the left workspace sidebar."""
    timestamps = get_timestamps()

    if not timestamps:
        return _no_timestamps_layout()

    details = html.Details(
        [
            _network_state_header(),
            html.Div(
                [
                    html.P(
                        NETWORK_STATE_DESCRIPTION,
                        className=("network-state-description text-muted"),
                    ),
                    _timestamp_controls(timestamps),
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
    )

    selector = dcc.Dropdown(
        id="timestamp-selector",
        options=[
            {
                "label": timestamp,
                "value": index,
            }
            for index, timestamp in enumerate(timestamps)
        ],
        value=0,
        clearable=False,
        style=HIDDEN_CONTROL_STYLE.copy(),
    )

    return _network_state_container(details, selector)
