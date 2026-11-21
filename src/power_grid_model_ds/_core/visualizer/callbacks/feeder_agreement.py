# SPDX-FileCopyrightText: Contributors to the Power Grid Model project <powergridmodel@lfenergy.org>
#
# SPDX-License-Identifier: MPL-2.0

"""Scenario-aware callbacks for the F13 agreement overview."""

from dash import Input, Output, State, callback

from power_grid_model_ds._core.visualizer import server_state
from power_grid_model_ds._core.visualizer.feeder_agreement_adapter import (
    prepare_voltage_agreement_overview,
)
from power_grid_model_ds._core.visualizer.layout.feeder_agreement import (
    DETAILS_ID,
    GROUP_ID,
    SUMMARY_ID,
    group_options,
    render_details,
    render_summary,
)
from power_grid_model_ds._core.visualizer.scenario_selection import (
    get_scenario_count,
)


def _prepare_overview(scenario_index: object):
    """Prepare a read-only overview or return an explanatory message."""
    if scenario_index is None or scenario_index == "":
        return None, "Select a scenario index to view measurements."

    update_data = server_state.get_update_data()
    output_data = server_state.get_output_data()

    count = get_scenario_count(update_data, output_data)

    if (
        isinstance(scenario_index, bool)
        or not isinstance(scenario_index, int)
        or count is None
        or not 0 <= scenario_index < count
    ):
        return None, "Select a valid scenario index."

    if output_data is None:
        return None, "Agreement overview unavailable: no output data."

    try:
        overview = prepare_voltage_agreement_overview(
            grid=server_state.get_grid(),
            update_data=update_data,
            output_data=output_data,
            scenario_index=scenario_index,
        )
    except (ValueError, TypeError, KeyError, IndexError) as error:
        return None, f"Agreement overview unavailable: {error}"

    return overview, None


def choose_group(
    options: list[dict[str, str]],
    current_value: str | None,
) -> str:
    """Preserve an available group or reset to the network summary."""
    valid_values = {option["value"] for option in options}

    if current_value in valid_values:
        return current_value

    return "network"


@callback(
    Output(SUMMARY_ID, "children"),
    Output(GROUP_ID, "options"),
    Output(GROUP_ID, "value"),
    Input("scenario-selector", "value"),
    State(GROUP_ID, "value"),
)
def update_agreement_summary(
    scenario_index: object,
    current_group: str | None,
):
    """Refresh the summary and reconcile the selected drilldown scope."""
    overview, message = _prepare_overview(scenario_index)

    if overview is None:
        return (
            message,
            [{"label": "Entire network", "value": "network"}],
            "network",
        )

    options = group_options(overview)

    return (
        render_summary(overview),
        options,
        choose_group(options, current_group),
    )


@callback(
    Output(DETAILS_ID, "children"),
    Input("scenario-selector", "value"),
    Input(GROUP_ID, "value"),
)
def update_agreement_details(
    scenario_index: object,
    selection: str | None,
):
    """Refresh contributing measurements for the selected scope."""
    overview, message = _prepare_overview(scenario_index)

    if overview is None:
        return message

    return render_details(overview, selection)
