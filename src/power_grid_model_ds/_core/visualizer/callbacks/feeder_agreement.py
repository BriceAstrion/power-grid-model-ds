# SPDX-FileCopyrightText: Contributors to the Power Grid Model project <powergridmodel@lfenergy.org>
#
# SPDX-License-Identifier: MPL-2.0

"""Scenario-aware callbacks for the F13 agreement overview."""

from dash import ALL, Input, Output, State, callback, ctx, no_update
from dash.exceptions import PreventUpdate

from power_grid_model_ds._core.visualizer import server_state
from power_grid_model_ds._core.visualizer.feeder_agreement_adapter import (
    prepare_voltage_agreement_overview,
)
from power_grid_model_ds._core.visualizer.feeder_agreement_selection import (
    DEFAULT_PAGE_SIZE,
    MeasurementSort,
    build_page_window,
    paginate_measurements,
)
from power_grid_model_ds._core.visualizer.layout.feeder_agreement import (
    DETAILS_ID,
    GROUP_ID,
    GROUP_OPTIONS_ID,
    NEXT_ID,
    PAGE_BUTTON_TYPE,
    PAGE_NUMBERS_ID,
    PAGE_STATUS_ID,
    PAGE_STORE_ID,
    PREVIOUS_ID,
    SCOPE_BUTTON_TYPE,
    SORT_ID,
    SUMMARY_ID,
    group_options,
    render_details,
    render_measurement_page,
    render_page_numbers,
    render_summary,
    selected_group,
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

    try:
        count = get_scenario_count(update_data, output_data)
    except (ValueError, TypeError, KeyError, IndexError, NotImplementedError) as error:
        return None, f"Agreement overview unavailable: {error}"

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
    except (ValueError, TypeError, KeyError, IndexError, NotImplementedError) as error:
        return None, f"Agreement overview unavailable: {error}"

    return overview, None


def resolve_scope_click(
    triggered_id: object,
    click_count: object,
    options: list[dict[str, str]],
) -> str | None:
    """Resolve an actual click on an available summary scope."""
    if not isinstance(triggered_id, dict):
        return None

    if triggered_id.get("type") != SCOPE_BUTTON_TYPE:
        return None

    if isinstance(click_count, bool) or not isinstance(click_count, int) or click_count <= 0:
        return None

    scope = triggered_id.get("scope")

    if not isinstance(scope, str):
        return None

    valid_values = {option["value"] for option in options}

    return scope if scope in valid_values else None


def choose_group(
    options: list[dict[str, str]],
    current_value: str | None,
) -> str:
    """Preserve an available group or reset to the network summary."""
    valid_values = {option["value"] for option in options}

    if current_value in valid_values:
        return current_value

    return "network"


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
    selection = choose_group(options, current_group)

    return (
        render_summary(overview, selection),
        options,
        selection,
    )


def handle_scope_click(
    triggered_id: object,
    click_count: object,
    options: list[dict[str, str]],
    current_group: str | None,
):
    """Change only the stored scope after a valid scope click."""
    selection = resolve_scope_click(triggered_id, click_count, options)

    if selection is None or selection == current_group:
        return no_update, no_update, no_update

    return no_update, no_update, selection


@callback(
    Output(SUMMARY_ID, "children"),
    Output(GROUP_OPTIONS_ID, "data"),
    Output(GROUP_ID, "data"),
    Input("scenario-selector", "value"),
    Input(
        {"type": SCOPE_BUTTON_TYPE, "scope": ALL},
        "n_clicks",
    ),
    State(GROUP_OPTIONS_ID, "data"),
    State(GROUP_ID, "data"),
)
def update_summary_selection(
    scenario_index: object,
    _scope_clicks: list[int | None],
    options: list[dict[str, str]] | None,
    current_group: str | None,
):
    """Handle scenario changes and dynamic summary button clicks."""
    triggered_id = ctx.triggered_id

    if triggered_id is None or "scenario-selector.value" in ctx.triggered_prop_ids:
        return update_agreement_summary(scenario_index, current_group)

    click_count = ctx.triggered[0]["value"] if ctx.triggered else None

    return handle_scope_click(
        triggered_id,
        click_count,
        options or [],
        current_group,
    )


def scope_pressed_states(
    selection: str | None,
    button_ids: list[dict[str, str]],
) -> list[str]:
    """Synchronise the accessible selected state of scope buttons."""
    return ["true" if button_id.get("scope") == selection else "false" for button_id in button_ids]


@callback(
    Output(
        {"type": SCOPE_BUTTON_TYPE, "scope": ALL},
        "aria-pressed",
    ),
    Input(GROUP_ID, "data"),
    State(
        {"type": SCOPE_BUTTON_TYPE, "scope": ALL},
        "id",
    ),
)
def synchronise_scope_buttons(
    selection: str | None,
    button_ids: list[dict[str, str]],
) -> list[str]:
    """Reflect stored scope selection without replacing summary buttons."""
    return scope_pressed_states(selection, button_ids)


def resolve_page_click(triggered_id: object, click_count: object, current_page: object) -> int:
    """Reject malformed, initial and redundant numbered page events."""
    if not isinstance(triggered_id, dict) or triggered_id.get("type") != PAGE_BUTTON_TYPE:
        raise PreventUpdate
    if isinstance(click_count, bool) or not isinstance(click_count, int) or click_count <= 0:
        raise PreventUpdate
    index = triggered_id.get("page")
    if isinstance(index, bool) or not isinstance(index, int) or index < 0 or index == current_page:
        raise PreventUpdate
    return index


def requested_page_index(
    triggered_id: object,
    current_page: object,
) -> int:
    """Resolve navigation or reset to the first page."""
    if isinstance(current_page, bool) or not isinstance(current_page, int) or current_page < 0:
        current_page = 0

    if isinstance(triggered_id, dict) and triggered_id.get("type") == PAGE_BUTTON_TYPE:
        return resolve_page_click(triggered_id, 1, current_page)

    if triggered_id == NEXT_ID:
        return current_page + 1

    if triggered_id == PREVIOUS_ID:
        return max(0, current_page - 1)

    return 0


def resolve_sort_mode(value: object) -> MeasurementSort:
    """Use the default sorting mode for invalid interface state."""
    if isinstance(value, str):
        try:
            return MeasurementSort(value)
        except ValueError:
            pass

    return MeasurementSort.LARGEST


def prepare_measurement_page(
    scenario_index: object,
    selection: str | None,
    sort_value: object,
    current_page: object,
    triggered_id: object,
):
    """Prepare the current page and its navigation state."""
    overview, _message = _prepare_overview(scenario_index)

    if overview is None:
        return None, 0, "", True, True, []

    group = selected_group(overview, selection)

    if group is None or not group.records:
        return (
            render_details(overview, selection),
            0,
            "",
            True,
            True,
            [],
        )

    requested = requested_page_index(triggered_id, current_page)
    if isinstance(triggered_id, dict) and triggered_id.get("type") == PAGE_BUTTON_TYPE:
        page_count = (group.total_count + DEFAULT_PAGE_SIZE - 1) // DEFAULT_PAGE_SIZE
        if isinstance(current_page, bool) or not isinstance(current_page, int):
            raise PreventUpdate
        if requested not in build_page_window(current_page, page_count):
            raise PreventUpdate

    sort_mode = resolve_sort_mode(sort_value)

    page = paginate_measurements(
        group,
        sort_mode=sort_mode,
        page_index=requested,
    )

    noun = "record" if page.total_count == 1 else "records"
    status = f"{page.total_count} {noun}"

    return (
        render_measurement_page(page),
        page.page_index,
        status,
        page.page_index == 0,
        page.page_index >= page.page_count - 1,
        render_page_numbers(page),
    )


def resolve_measurement_trigger(
    triggered_properties: set[str],
    triggered_id: object,
    navigation_clicks: tuple[object, object],
    *,
    navigation_disabled: tuple[bool, bool],
    page_event: tuple[object, object] = (None, None),
) -> object:
    """Prioritise data changes and ignore redundant navigation."""
    previous_clicks, next_clicks = navigation_clicks
    previous_disabled, next_disabled = navigation_disabled

    reset_properties = (
        "scenario-selector.value",
        f"{GROUP_ID}.data",
        f"{SORT_ID}.value",
    )

    for property_id in reset_properties:
        if property_id in triggered_properties:
            return property_id.rsplit(".", 1)[0]

    if triggered_id is None and not triggered_properties:
        return None

    previous_triggered = f"{PREVIOUS_ID}.n_clicks" in triggered_properties
    next_triggered = f"{NEXT_ID}.n_clicks" in triggered_properties

    if isinstance(triggered_id, dict):
        if previous_triggered or next_triggered or len(triggered_properties) != 1:
            raise PreventUpdate
        click_count, current_page = page_event
        resolve_page_click(triggered_id, click_count, current_page)
        return triggered_id

    if previous_triggered and next_triggered:
        raise PreventUpdate

    if previous_triggered:
        if (
            previous_disabled
            or isinstance(previous_clicks, bool)
            or not isinstance(previous_clicks, int)
            or previous_clicks <= 0
        ):
            raise PreventUpdate

        return PREVIOUS_ID

    if next_triggered:
        if next_disabled or isinstance(next_clicks, bool) or not isinstance(next_clicks, int) or next_clicks <= 0:
            raise PreventUpdate

        return NEXT_ID

    raise PreventUpdate


@callback(
    Output(DETAILS_ID, "children"),
    Output(PAGE_STORE_ID, "data"),
    Output(PAGE_STATUS_ID, "children"),
    Output(PREVIOUS_ID, "disabled"),
    Output(NEXT_ID, "disabled"),
    Output(PAGE_NUMBERS_ID, "children"),
    Input("scenario-selector", "value"),
    Input(GROUP_ID, "data"),
    Input(SORT_ID, "value"),
    Input(PREVIOUS_ID, "n_clicks"),
    Input(NEXT_ID, "n_clicks"),
    Input({"type": PAGE_BUTTON_TYPE, "page": ALL}, "n_clicks"),
    State(PAGE_STORE_ID, "data"),
    State(PREVIOUS_ID, "disabled"),
    State(NEXT_ID, "disabled"),
)
# Dash supplies the declared inputs and states as positional arguments.
# pylint: disable-next=too-many-arguments,too-many-positional-arguments
def update_measurement_page(  # noqa: PLR0913, PLR0917
    scenario_index: object,
    selection: str | None,
    sort_value: object,
    previous_clicks: int | None,
    next_clicks: int | None,
    _page_clicks: list[int | None],
    current_page: object,
    previous_disabled: bool,
    next_disabled: bool,
):
    """Update measurement details and browser-local pagination."""
    click_count = ctx.triggered[0]["value"] if isinstance(ctx.triggered_id, dict) and ctx.triggered else None
    triggered_id = resolve_measurement_trigger(
        set(ctx.triggered_prop_ids),
        ctx.triggered_id,
        (previous_clicks, next_clicks),
        navigation_disabled=(
            previous_disabled,
            next_disabled,
        ),
        page_event=(click_count, current_page),
    )

    return prepare_measurement_page(
        scenario_index,
        selection,
        sort_value,
        current_page,
        triggered_id,
    )
