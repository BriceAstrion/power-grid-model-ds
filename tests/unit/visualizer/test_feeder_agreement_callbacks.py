# SPDX-FileCopyrightText: Contributors to the Power Grid Model project <powergridmodel@lfenergy.org>
#
# SPDX-License-Identifier: MPL-2.0

"""Unit tests for F13 scenario and drilldown callbacks."""

from unittest.mock import patch

import pytest
from dash import html, no_update
from dash.exceptions import PreventUpdate
from power_grid_model import ComponentType, DatasetType, initialize_array

from power_grid_model_ds._core.visualizer import feeder_agreement_selection
from power_grid_model_ds._core.visualizer.callbacks.feeder_agreement import (
    _prepare_overview,
    choose_group,
    handle_scope_click,
    prepare_measurement_page,
    requested_page_index,
    resolve_measurement_trigger,
    resolve_page_click,
    resolve_sort_mode,
    scope_pressed_states,
    update_agreement_summary,
    update_measurement_page,
)
from power_grid_model_ds._core.visualizer.feeder_agreement import (
    MeasurementIdentity,
    build_agreement_overview,
    make_agreement_record,
)


def _overview(scenario_index: int = 0):
    record = make_agreement_record(
        MeasurementIdentity(
            scenario_index=scenario_index,
            sensor_id=11,
            component_id=1,
            quantity="voltage",
            unit="V",
        ),
        measured=10490.0,
        estimated=10488.0,
        feeder_id=201,
    )
    return build_agreement_overview([record], scenario_index)


def _components(component):
    """Yield a Dash component and all its descendants."""
    if isinstance(component, (list, tuple)):
        for child in component:
            yield from _components(child)
        return

    if not hasattr(component, "children"):
        return

    yield component

    children = component.children
    if children is not None:
        yield from _components(children)


def _table_rows(table):
    """Extract table cells in row order."""
    return [
        [str(cell.children) for cell in (row.children or [])] for row in _components(table) if isinstance(row, html.Tr)
    ]


def test_available_group_is_preserved():
    options = [
        {"label": "Entire network", "value": "network"},
        {"label": "Feeder 201", "value": "feeder:201"},
    ]

    assert choose_group(options, "feeder:201") == "feeder:201"


def test_missing_group_resets_to_network():
    options = [
        {"label": "Entire network", "value": "network"},
        {"label": "Feeder 202", "value": "feeder:202"},
    ]

    assert choose_group(options, "feeder:201") == "network"


def test_missing_scenario_is_explained():
    overview, message = _prepare_overview(None)

    assert overview is None
    assert message is not None
    assert "Select a scenario index" in message


def test_invalid_scenario_is_rejected():
    with (
        patch(
            "power_grid_model_ds._core.visualizer.callbacks.feeder_agreement.server_state.get_update_data",
            return_value={},
        ),
        patch(
            "power_grid_model_ds._core.visualizer.callbacks.feeder_agreement.server_state.get_output_data",
            return_value={},
        ),
        patch(
            "power_grid_model_ds._core.visualizer.callbacks.feeder_agreement.get_scenario_count",
            return_value=2,
        ),
    ):
        overview, message = _prepare_overview(5)

    assert overview is None
    assert message == "Select a valid scenario index."


def test_missing_output_data_is_explained():
    with (
        patch(
            "power_grid_model_ds._core.visualizer.callbacks.feeder_agreement.server_state.get_update_data",
            return_value={},
        ),
        patch(
            "power_grid_model_ds._core.visualizer.callbacks.feeder_agreement.server_state.get_output_data",
            return_value=None,
        ),
        patch(
            "power_grid_model_ds._core.visualizer.callbacks.feeder_agreement.get_scenario_count",
            return_value=2,
        ),
    ):
        overview, message = _prepare_overview(0)

    assert overview is None
    assert message is not None
    assert "no output data" in message


def test_summary_reconciles_missing_feeder():
    with patch(
        "power_grid_model_ds._core.visualizer.callbacks.feeder_agreement._prepare_overview",
        return_value=(_overview(), None),
    ):
        summary, options, selected = update_agreement_summary(
            0,
            "feeder:999",
        )

    assert summary is not None
    assert options[1]["value"] == "feeder:201"
    assert selected == "network"


def test_summary_preserves_existing_feeder():
    with patch(
        "power_grid_model_ds._core.visualizer.callbacks.feeder_agreement._prepare_overview",
        return_value=(_overview(), None),
    ):
        _, _, selected = update_agreement_summary(
            0,
            "feeder:201",
        )

    assert selected == "feeder:201"


def test_details_follow_selected_scenario():
    with patch(
        "power_grid_model_ds._core.visualizer.callbacks.feeder_agreement._prepare_overview",
        return_value=(_overview(1), None),
    ) as prepare:
        details, page, status, previous, following, controls = prepare_measurement_page(
            1,
            "network",
            "largest",
            0,
            "scenario-selector",
        )
        prepare.assert_called_once_with(1)

    assert page == 0
    assert status == "1 record"
    assert previous is True
    assert following is True
    assert controls == []

    assert isinstance(details, html.Div)

    headings = [
        item.children
        for item in _components(details)
        if isinstance(item, html.Span) and getattr(item, "className", None) == "agreement-measurement-title"
    ]
    statuses = [
        item.children
        for item in _components(details)
        if isinstance(item, html.Span) and getattr(item, "className", None) == "agreement-measurement-status"
    ]

    assert headings == ["Sensor 11"]
    assert statuses == ["Node 1 · Available"]

    tables = [item for item in _components(details) if isinstance(item, html.Table)]

    assert len(tables) == 1

    rows = _table_rows(tables[0])

    assert ["Measured", "10490"] in rows
    assert ["Estimated", "10488"] in rows
    assert ["Feeder ID", "201"] in rows

    # The redundant measurement-count paragraph was removed.
    assert not any(
        isinstance(item, html.P) and "contributing measurement(s)" in str(item.children)
        for item in _components(details)
    )


def test_unavailable_scenario_clears_summary_selection():
    with patch(
        "power_grid_model_ds._core.visualizer.callbacks.feeder_agreement._prepare_overview",
        return_value=(None, "Select a valid scenario index."),
    ):
        message, options, selected = update_agreement_summary(
            99,
            "feeder:201",
        )

    assert message == "Select a valid scenario index."
    assert options == [
        {"label": "Entire network", "value": "network"},
    ]
    assert selected == "network"


@pytest.mark.parametrize(
    ("trigger", "current", "expected"),
    [
        ("f13-agreement-next", 0, 1),
        ("f13-agreement-next", 2, 3),
        ("f13-agreement-previous", 2, 1),
        ("f13-agreement-previous", 0, 0),
        ("scenario-selector", 3, 0),
        ("f13-agreement-group", 3, 0),
        ("f13-agreement-sort", 3, 0),
        (None, 3, 0),
        ("f13-agreement-next", None, 1),
        ("f13-agreement-next", True, 1),
        ("f13-agreement-next", -1, 1),
    ],
)
def test_navigation_page_index(trigger, current, expected):
    assert requested_page_index(trigger, current) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("largest", "largest"),
        ("smallest", "smallest"),
        ("sensor", "sensor"),
        ("invalid", "largest"),
        (None, "largest"),
    ],
)
def test_resolve_sort_mode(value, expected):
    assert resolve_sort_mode(value).value == expected


def _large_overview():
    records = [
        make_agreement_record(
            MeasurementIdentity(
                0,
                sensor_id,
                sensor_id + 100,
                "voltage",
                "V",
            ),
            measured=100.0,
            estimated=100.0 + sensor_id,
            feeder_id=201,
        )
        for sensor_id in range(1, 13)
    ]

    return build_agreement_overview(records, 0)


@pytest.mark.parametrize(
    (
        "current",
        "trigger",
        "expected_page",
        "expected_range",
        "expected_buttons",
    ),
    [
        (0, None, 0, (1, 5), (True, False)),
        (0, "f13-agreement-next", 1, (6, 10), (False, False)),
        (1, "f13-agreement-next", 2, (11, 12), (False, True)),
        (2, "f13-agreement-next", 2, (11, 12), (False, True)),
        (2, "f13-agreement-previous", 1, (6, 10), (False, False)),
        (2, "f13-agreement-sort", 0, (1, 5), (True, False)),
        (2, "f13-agreement-group", 0, (1, 5), (True, False)),
        (2, "scenario-selector", 0, (1, 5), (True, False)),
    ],
)
def test_measurement_page_navigation(
    current,
    trigger,
    expected_page,
    expected_range,
    expected_buttons,
):
    first, last = expected_range
    previous_disabled, next_disabled = expected_buttons

    with patch(
        "power_grid_model_ds._core.visualizer.callbacks.feeder_agreement._prepare_overview",
        return_value=(_large_overview(), None),
    ):
        details, page, status, previous, following, controls = prepare_measurement_page(
            0, "network", "largest", current, trigger
        )

    cards = [item for item in _components(details) if isinstance(item, html.Details)]

    assert page == expected_page
    assert len(cards) == last - first + 1
    assert status == "12 records"
    headings = [
        item.children
        for item in _components(details)
        if isinstance(item, html.Span) and getattr(item, "className", None) == "agreement-measurement-title"
    ]
    assert headings == [f"Sensor {13 - position}" for position in range(first, last + 1)]
    assert previous is previous_disabled
    assert following is next_disabled
    assert [button.children for button in controls] == ["1", "2", "3"]


@pytest.mark.parametrize(
    ("sort_mode", "expected"),
    [
        ("largest", [12, 11, 10, 9, 8]),
        ("smallest", [1, 2, 3, 4, 5]),
        ("sensor", [1, 2, 3, 4, 5]),
    ],
)
def test_measurement_page_sorting(sort_mode, expected):
    with patch(
        "power_grid_model_ds._core.visualizer.callbacks.feeder_agreement._prepare_overview",
        return_value=(_large_overview(), None),
    ):
        details, _, _, _, _, _ = prepare_measurement_page(0, "network", sort_mode, 0, None)

    headings = [
        item.children
        for item in _components(details)
        if isinstance(item, html.Span) and getattr(item, "className", None) == "agreement-measurement-title"
    ]
    statuses = [
        item.children
        for item in _components(details)
        if isinstance(item, html.Span) and getattr(item, "className", None) == "agreement-measurement-status"
    ]

    assert headings == [f"Sensor {sensor_id}" for sensor_id in expected]
    assert statuses == [f"Node {sensor_id + 100} · Available" for sensor_id in expected]


def test_unavailable_scenario_disables_pagination():
    with patch(
        "power_grid_model_ds._core.visualizer.callbacks.feeder_agreement._prepare_overview",
        return_value=(None, "Select a valid scenario index."),
    ):
        result = prepare_measurement_page(99, "network", "largest", 2, None)

    assert result == (None, 0, "", True, True, [])


@pytest.mark.parametrize(
    "selection",
    ["unassigned", "feeder:999"],
)
def test_empty_or_missing_group_disables_pagination(selection):
    with patch(
        "power_grid_model_ds._core.visualizer.callbacks.feeder_agreement._prepare_overview",
        return_value=(_large_overview(), None),
    ):
        details, page, status, previous, following, controls = prepare_measurement_page(
            0, selection, "largest", 2, None
        )

    assert isinstance(details, html.Div)
    assert page == 0
    assert status == ""
    assert previous is True
    assert following is True
    assert controls == []


def _scope_options():
    return [
        {"label": "Entire network", "value": "network"},
        {"label": "Feeder 201", "value": "feeder:201"},
        {"label": "Unassigned", "value": "unassigned"},
    ]


@pytest.mark.parametrize(
    ("selection", "current"),
    [
        ("feeder:201", "network"),
        ("network", "feeder:201"),
        ("unassigned", "network"),
    ],
)
def test_scope_click_updates_only_dropdown(selection, current):
    result = handle_scope_click(
        {"type": "f13-agreement-scope", "scope": selection},
        1,
        _scope_options(),
        current,
    )

    assert result == (no_update, no_update, selection)


@pytest.mark.parametrize(
    ("selection", "click_count", "current"),
    [
        ("network", 1, "network"),
        ("feeder:201", 0, "network"),
        ("feeder:201", None, "network"),
        ("feeder:999", 1, "network"),
    ],
)
def test_scope_click_ignores_unchanged_or_invalid_events(selection, click_count, current):
    result = handle_scope_click(
        {"type": "f13-agreement-scope", "scope": selection},
        click_count,
        _scope_options(),
        current,
    )

    assert result == (no_update, no_update, no_update)


@pytest.mark.parametrize(
    ("selection", "expected"),
    [
        ("network", ["true", "false", "false"]),
        ("feeder:201", ["false", "true", "false"]),
        ("unassigned", ["false", "false", "true"]),
        ("feeder:999", ["false", "false", "false"]),
        (None, ["false", "false", "false"]),
    ],
)
def test_scope_pressed_states_follow_dropdown(selection, expected):
    button_ids = [{"type": "f13-agreement-scope", "scope": scope} for scope in ("network", "feeder:201", "unassigned")]

    assert scope_pressed_states(selection, button_ids) == expected


def test_scope_pressed_states_support_empty_summary():
    assert scope_pressed_states("network", []) == []


def test_reconciled_summary_marks_preserved_feeder():
    with patch(
        "power_grid_model_ds._core.visualizer.callbacks.feeder_agreement._prepare_overview",
        return_value=(_overview(), None),
    ):
        summary, _, selection = update_agreement_summary(0, "feeder:201")

    buttons = [item for item in _components(summary) if isinstance(item, html.Button)]

    selected = [button.id["scope"] for button in buttons if button.to_plotly_json()["props"]["aria-pressed"] == "true"]

    assert selection == "feeder:201"
    assert selected == ["feeder:201"]


def test_reconciled_summary_marks_network_fallback():
    with patch(
        "power_grid_model_ds._core.visualizer.callbacks.feeder_agreement._prepare_overview",
        return_value=(_overview(), None),
    ):
        summary, _, selection = update_agreement_summary(0, "feeder:999")

    buttons = [item for item in _components(summary) if isinstance(item, html.Button)]

    selected = [button.id["scope"] for button in buttons if button.to_plotly_json()["props"]["aria-pressed"] == "true"]

    assert selection == "network"
    assert selected == ["network"]


@pytest.mark.parametrize(
    "sort_mode",
    ["largest", "smallest", "sensor"],
)
def test_measurement_page_sorts_only_once(sort_mode):
    with (
        patch(
            "power_grid_model_ds._core.visualizer.callbacks.feeder_agreement._prepare_overview",
            return_value=(_large_overview(), None),
        ),
        patch.object(
            feeder_agreement_selection,
            "sort_measurements",
            wraps=feeder_agreement_selection.sort_measurements,
        ) as sort_records,
    ):
        details, page, status, previous, following, controls = prepare_measurement_page(
            0, "network", sort_mode, 0, None
        )

    sort_records.assert_called_once()

    cards = [item for item in _components(details) if isinstance(item, html.Details)]

    assert len(cards) == 5
    assert page == 0
    assert status == "12 records"
    assert previous is True
    assert following is False
    assert [button.children for button in controls] == ["1", "2", "3"]


def test_empty_measurement_group_does_not_sort():
    with (
        patch(
            "power_grid_model_ds._core.visualizer.callbacks.feeder_agreement._prepare_overview",
            return_value=(_large_overview(), None),
        ),
        patch.object(
            feeder_agreement_selection,
            "sort_measurements",
            wraps=feeder_agreement_selection.sort_measurements,
        ) as sort_records,
    ):
        details, page, status, previous, following, controls = prepare_measurement_page(
            0, "unassigned", "largest", 0, None
        )

    sort_records.assert_not_called()

    assert isinstance(details, html.Div)
    assert page == 0
    assert status == ""
    assert previous is True
    assert following is True
    assert controls == []


@pytest.mark.parametrize(
    ("update_data", "output_data"),
    [
        ({}, None),
        (None, {}),
        ({}, {}),
    ],
)
def test_empty_datasets_are_explained(update_data, output_data):
    with (
        patch(
            "power_grid_model_ds._core.visualizer.callbacks.feeder_agreement.server_state.get_update_data",
            return_value=update_data,
        ),
        patch(
            "power_grid_model_ds._core.visualizer.callbacks.feeder_agreement.server_state.get_output_data",
            return_value=output_data,
        ),
    ):
        overview, message = _prepare_overview(0)

    assert overview is None
    assert message is not None
    assert "empty batch dataset" in message


def test_unsupported_dataset_representation_is_explained():
    with (
        patch(
            "power_grid_model_ds._core.visualizer.callbacks.feeder_agreement.server_state.get_update_data",
            return_value=None,
        ),
        patch(
            "power_grid_model_ds._core.visualizer.callbacks.feeder_agreement.server_state.get_output_data",
            return_value={"node": object()},
        ),
        patch(
            "power_grid_model_ds._core.visualizer.callbacks.feeder_agreement.server_state.get_grid",
            return_value=object(),
        ),
        patch(
            "power_grid_model_ds._core.visualizer.callbacks.feeder_agreement.get_scenario_count",
            return_value=1,
        ),
        patch(
            "power_grid_model_ds._core.visualizer.callbacks.feeder_agreement.prepare_voltage_agreement_overview",
            side_effect=NotImplementedError("Voltage agreement requires dense batch arrays."),
        ),
    ):
        overview, message = _prepare_overview(0)

    assert overview is None
    assert message == ("Agreement overview unavailable: Voltage agreement requires dense batch arrays.")


def test_real_single_output_dataset_is_explained():
    output = initialize_array(
        DatasetType.sym_output,
        ComponentType.node,
        1,
    )
    output["id"] = 1
    output["u"] = 10488.0

    with (
        patch(
            "power_grid_model_ds._core.visualizer.callbacks.feeder_agreement.server_state.get_update_data",
            return_value=None,
        ),
        patch(
            "power_grid_model_ds._core.visualizer.callbacks.feeder_agreement.server_state.get_output_data",
            return_value={ComponentType.node: output},
        ),
        patch(
            "power_grid_model_ds._core.visualizer.callbacks.feeder_agreement.server_state.get_grid",
            return_value=object(),
        ),
    ):
        overview, message = _prepare_overview(0)

    assert overview is None
    assert message is not None
    assert message.startswith("Agreement overview unavailable:")


def test_real_inconsistent_scenario_counts_are_explained():
    updates = initialize_array(
        DatasetType.update,
        ComponentType.node,
        (2, 1),
    )
    outputs = initialize_array(
        DatasetType.sym_output,
        ComponentType.node,
        (3, 1),
    )

    with (
        patch(
            "power_grid_model_ds._core.visualizer.callbacks.feeder_agreement.server_state.get_update_data",
            return_value={ComponentType.node: updates},
        ),
        patch(
            "power_grid_model_ds._core.visualizer.callbacks.feeder_agreement.server_state.get_output_data",
            return_value={ComponentType.node: outputs},
        ),
    ):
        overview, message = _prepare_overview(0)

    assert overview is None
    assert message is not None
    assert "inconsistent scenario counts" in message


@pytest.mark.parametrize(
    ("properties", "triggered_id", "expected"),
    [
        (set(), None, None),
        (
            {"scenario-selector.value"},
            "scenario-selector",
            "scenario-selector",
        ),
        (
            {
                "scenario-selector.value",
                "f13-agreement-next.n_clicks",
            },
            "f13-agreement-next",
            "scenario-selector",
        ),
        (
            {
                "f13-agreement-group.data",
                "f13-agreement-next.n_clicks",
            },
            "f13-agreement-next",
            "f13-agreement-group",
        ),
        (
            {
                "f13-agreement-sort.value",
                "f13-agreement-previous.n_clicks",
            },
            "f13-agreement-previous",
            "f13-agreement-sort",
        ),
        (
            {
                "scenario-selector.value",
                "f13-agreement-group.data",
                "f13-agreement-sort.value",
            },
            "f13-agreement-sort",
            "scenario-selector",
        ),
    ],
)
def test_measurement_trigger_priority(
    properties,
    triggered_id,
    expected,
):
    result = resolve_measurement_trigger(properties, triggered_id, (1, 1), navigation_disabled=(True, True))

    assert result == expected


@pytest.mark.parametrize(
    ("button", "click_count", "disabled"),
    [
        ("f13-agreement-previous", 1, True),
        ("f13-agreement-next", 1, True),
        ("f13-agreement-previous", 0, False),
        ("f13-agreement-next", 0, False),
        ("f13-agreement-previous", None, False),
        ("f13-agreement-next", None, False),
        ("f13-agreement-next", True, False),
        ("f13-agreement-next", -1, False),
    ],
)
def test_redundant_navigation_is_ignored(
    button,
    click_count,
    disabled,
):
    with pytest.raises(PreventUpdate):
        resolve_measurement_trigger(
            {f"{button}.n_clicks"}, button, (click_count, click_count), navigation_disabled=(disabled, disabled)
        )


@pytest.mark.parametrize(
    "button",
    [
        "f13-agreement-previous",
        "f13-agreement-next",
    ],
)
def test_enabled_navigation_is_preserved(button):
    result = resolve_measurement_trigger({f"{button}.n_clicks"}, button, (1, 1), navigation_disabled=(False, False))

    assert result == button


def test_conflicting_navigation_is_ignored():
    with pytest.raises(PreventUpdate):
        resolve_measurement_trigger(
            {"f13-agreement-previous.n_clicks", "f13-agreement-next.n_clicks"},
            "f13-agreement-next",
            (1, 1),
            navigation_disabled=(False, False),
        )


@pytest.mark.parametrize(
    ("button", "previous_disabled", "next_disabled"),
    [
        ("f13-agreement-previous", True, False),
        ("f13-agreement-next", False, True),
    ],
)
def test_blocked_navigation_does_not_prepare_overview(
    button,
    previous_disabled,
    next_disabled,
):
    module = "power_grid_model_ds._core.visualizer.callbacks.feeder_agreement"

    with (
        patch(f"{module}.ctx") as context,
        patch(f"{module}._prepare_overview") as prepare,
    ):
        context.triggered_id = button
        context.triggered_prop_ids = {
            f"{button}.n_clicks": button,
        }

        with pytest.raises(PreventUpdate):
            update_measurement_page(
                0, "network", "largest", 1, 1, [], 0, previous_disabled=previous_disabled, next_disabled=next_disabled
            )

        prepare.assert_not_called()


@pytest.mark.parametrize(
    "reset_property",
    [
        "scenario-selector.value",
        "f13-agreement-group.data",
        "f13-agreement-sort.value",
    ],
)
def test_data_change_resets_page_despite_navigation(
    reset_property,
):
    module = "power_grid_model_ds._core.visualizer.callbacks.feeder_agreement"

    with (
        patch(f"{module}.ctx") as context,
        patch(
            f"{module}._prepare_overview",
            return_value=(_large_overview(), None),
        ) as prepare,
    ):
        context.triggered_id = "f13-agreement-next"
        context.triggered_prop_ids = {
            "f13-agreement-next.n_clicks": "f13-agreement-next",
            reset_property: reset_property.rsplit(".", 1)[0],
        }

        details, page, status, previous, following, controls = update_measurement_page(
            0, "network", "largest", 1, 1, [], 2, previous_disabled=False, next_disabled=True
        )

        prepare.assert_called_once_with(0)

    assert isinstance(details, html.Div)
    assert page == 0
    assert status == "12 records"
    assert previous is True
    assert following is False

    assert [button.children for button in controls] == ["1", "2", "3"]


@pytest.mark.parametrize("click_count", [None, 0, -1, True, 1.5])
def test_numbered_page_ignores_invalid_clicks(click_count):
    with pytest.raises(PreventUpdate):
        resolve_page_click({"type": "f13-agreement-page-number", "page": 2}, click_count, 0)


@pytest.mark.parametrize("index", [None, -1, True, 1.5, 0])
def test_numbered_page_ignores_invalid_indices(index):
    with pytest.raises(PreventUpdate):
        resolve_page_click({"type": "f13-agreement-page-number", "page": index}, 1, 0)


def test_numbered_page_direct_navigation():
    module = "power_grid_model_ds._core.visualizer.callbacks.feeder_agreement"
    button = {"type": "f13-agreement-page-number", "page": 2}
    with (
        patch(f"{module}.ctx") as context,
        patch(f"{module}._prepare_overview", return_value=(_large_overview(), None)),
    ):
        context.triggered_id = button
        context.triggered_prop_ids = {'{"page":2,"type":"f13-agreement-page-number"}.n_clicks': button}
        context.triggered = [{"value": 1}]
        details, page, status, previous, following, controls = update_measurement_page(
            0, "network", "largest", 0, 0, [0, 0, 1], 0, previous_disabled=True, next_disabled=False
        )
    assert page == 2
    assert status == "12 records"
    assert previous is False
    assert following is True
    assert len([item for item in _components(details) if isinstance(item, html.Details)]) == 2
    assert [item.to_plotly_json()["props"]["aria-current"] for item in controls] == ["false", "false", "page"]


def test_numbered_page_rejects_out_of_range_before_sorting():
    module = "power_grid_model_ds._core.visualizer.callbacks.feeder_agreement"
    with (
        patch(f"{module}._prepare_overview", return_value=(_large_overview(), None)),
        patch(f"{module}.paginate_measurements") as paginate,
        pytest.raises(PreventUpdate),
    ):
        prepare_measurement_page(0, "network", "largest", 0, {"type": "f13-agreement-page-number", "page": 99})
    paginate.assert_not_called()


def test_numbered_page_reset_priority():
    button = {"type": "f13-agreement-page-number", "page": 2}
    assert (
        resolve_measurement_trigger(
            {"scenario-selector.value", "page.n_clicks"},
            button,
            (0, 0),
            navigation_disabled=(True, False),
            page_event=(1, 0),
        )
        == "scenario-selector"
    )


def test_numbered_page_initial_event_does_not_prepare():
    module = "power_grid_model_ds._core.visualizer.callbacks.feeder_agreement"
    button = {"type": "f13-agreement-page-number", "page": 2}
    with (
        patch(f"{module}.ctx") as context,
        patch(f"{module}._prepare_overview") as prepare,
    ):
        context.triggered_id = button
        context.triggered_prop_ids = {'{"page":2,"type":"f13-agreement-page-number"}.n_clicks': button}
        context.triggered = [{"value": 0}]
        with pytest.raises(PreventUpdate):
            update_measurement_page(
                0, "network", "largest", 0, 0, [0, 0, 0], 0, previous_disabled=True, next_disabled=False
            )
        prepare.assert_not_called()
