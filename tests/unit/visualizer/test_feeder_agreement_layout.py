# SPDX-FileCopyrightText: Contributors to the Power Grid Model project <powergridmodel@lfenergy.org>
#
# SPDX-License-Identifier: MPL-2.0

"""Unit tests for the F13 overview and drilldown presentation."""

import pytest
from dash import dcc, html

from power_grid_model_ds._core.visualizer.feeder_agreement import (
    MeasurementIdentity,
    build_agreement_overview,
    make_agreement_record,
)
from power_grid_model_ds._core.visualizer.feeder_agreement_selection import MeasurementPage
from power_grid_model_ds._core.visualizer.layout.feeder_agreement import (
    NEXT_ID,
    PAGE_BUTTON_TYPE,
    PAGE_NUMBERS_ID,
    PREVIOUS_ID,
    _pair_count,
    _summary_number,
    get_feeder_agreement_html,
    group_options,
    render_details,
    render_page_numbers,
    render_summary,
    selected_group,
)


def _overview():
    records = [
        make_agreement_record(
            MeasurementIdentity(0, 11, 1, "voltage", "V"),
            measured=10490.0,
            estimated=10488.0,
            feeder_id=201,
        ),
        make_agreement_record(
            MeasurementIdentity(0, 12, 2, "voltage", "V"),
            measured=10000.0,
            estimated=None,
            feeder_id=201,
        ),
        make_agreement_record(
            MeasurementIdentity(0, 13, 6, "voltage", "V"),
            measured=10100.0,
            estimated=10099.0,
            feeder_id=None,
        ),
    ]
    return build_agreement_overview(records, 0)


def _components(component):
    """Yield Dash components and recursively inspect their children."""
    if isinstance(component, (list, tuple)):
        for child in component:
            yield from _components(child)
        return

    if not hasattr(component, "to_plotly_json"):
        return

    yield component

    if hasattr(component, "children"):
        children = component.children
        if children is not None:
            yield from _components(children)


def _component_with_id(component, component_id):
    """Find a Dash component with the requested assigned ID."""
    return next(
        (item for item in _components(component) if item.to_plotly_json()["props"].get("id") == component_id),
        None,
    )


def _tables(component):
    """Return all semantic HTML tables below a component."""
    return [item for item in _components(component) if isinstance(item, html.Table)]


def _cell_text(value):
    """Extract text without depending on presentation wrappers."""
    if isinstance(value, (list, tuple)):
        return "".join(_cell_text(child) for child in value)
    if hasattr(value, "children"):
        return _cell_text(value.children)
    return str(value)


def _table_rows(table):
    """Extract visible table cells in row order."""
    return [
        [_cell_text(cell.children) for cell in (row.children or [])]
        for row in _components(table)
        if isinstance(row, html.Tr)
    ]


def test_layout_has_persistent_callback_targets():
    panel = get_feeder_agreement_html()

    assert isinstance(panel, html.Section)
    assert panel.id == "f13-agreement-panel"

    summary = _component_with_id(
        panel,
        "f13-agreement-summary",
    )
    dropdown = _component_with_id(
        panel,
        "f13-agreement-group",
    )
    details = _component_with_id(
        panel,
        "f13-agreement-details",
    )

    assert isinstance(summary, html.Div)
    assert isinstance(dropdown, dcc.Store)
    assert isinstance(details, html.Div)

    assert dropdown.data == "network"
    assert dropdown.storage_type == "memory"
    assert not any(isinstance(item, dcc.Dropdown) and item.id == "f13-agreement-group" for item in _components(panel))


def test_layout_is_collapsible_and_expanded_by_default():
    panel = get_feeder_agreement_html()

    collapsible = _component_with_id(
        panel,
        "f13-agreement-details-section",
    )

    assert isinstance(collapsible, html.Details)
    assert getattr(collapsible, "open", None) is True
    assert collapsible.children is not None
    assert isinstance(collapsible.children[0], html.Summary)

    header = collapsible.children[0]
    assert header.className == "network-state-summary"

    titles = [item.children for item in _components(header) if isinstance(item, html.H4)]
    assert titles == ["Measurement agreement"]


def test_group_options_include_network_feeder_and_unassigned():
    assert group_options(_overview()) == [
        {"label": "Entire network", "value": "network"},
        {"label": "Feeder 201", "value": "feeder:201"},
        {"label": "Unassigned measurements", "value": "unassigned"},
    ]


def test_network_group_contains_all_measurements():
    group = selected_group(_overview(), "network")

    assert group is not None
    assert group.total_count == 3


def test_feeder_drilldown_contains_only_contributing_sensors():
    group = selected_group(_overview(), "feeder:201")

    assert group is not None
    assert {record.sensor_id for record in group.records} == {11, 12}


def test_unassigned_drilldown_is_separate():
    group = selected_group(_overview(), "unassigned")

    assert group is not None
    assert [record.sensor_id for record in group.records] == [13]


def test_unknown_group_is_rejected():
    assert selected_group(_overview(), "feeder:999") is None
    assert selected_group(_overview(), "feeder:invalid") is None


def test_summary_contains_availability_and_statistics():
    summary = render_summary(_overview())

    tables = _tables(summary)
    assert len(tables) == 1

    rows = _table_rows(tables[0])

    assert rows == [
        ["Scope", "Pairs", "Min", "Mean", "Max"],
        ["Entire network", "2/3", "1", "1.5", "2"],
        ["Feeder 201", "1/2", "2", "2", "2"],
        ["Unassigned", "1/1", "1", "1", "1"],
    ]


def test_summary_does_not_repeat_scenario_index():
    summary = render_summary(_overview())

    paragraphs = [str(item.children) for item in _components(summary) if isinstance(item, html.P)]

    assert not any("Scenario index:" in paragraph for paragraph in paragraphs)


def test_details_contain_missing_estimate_record():
    details = render_details(_overview(), "feeder:201")

    assert isinstance(details, html.Div)

    tables = _tables(details)
    assert len(tables) == 2

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

    assert headings == ["Sensor 11", "Sensor 12"]
    assert statuses == ["Node 1 · Available", "Node 2 · Missing estimate"]

    first_rows = _table_rows(tables[0])
    second_rows = _table_rows(tables[1])

    assert ["Measured", "10490"] in first_rows
    assert ["Estimated", "10488"] in first_rows

    assert ["Measured", "10000"] in second_rows
    assert ["Estimated", "—"] in second_rows


def test_details_do_not_repeat_measurement_count():
    details = render_details(_overview(), "feeder:201")

    paragraphs = [str(item.children) for item in _components(details) if isinstance(item, html.P)]

    assert not any("contributing measurement(s)" in paragraph for paragraph in paragraphs)


def test_measurement_values_use_accessible_dark_blue_text():
    details = render_details(_overview(), "feeder:201")

    tables = _tables(details)
    assert tables

    for table in tables:
        body = next(item for item in _components(table) if isinstance(item, html.Tbody))

        assert body.children is not None
        for row in body.children:
            value_cell = row.children[1]

            assert isinstance(value_cell, html.Td)
            assert value_cell.style["color"] == "#084298"


def test_empty_drilldown_has_explicit_message():
    overview = build_agreement_overview([], 0)
    details = render_details(overview, "network")

    assert isinstance(details, html.Div)
    assert details.role == "status"
    assert "No contributing measurements" in str(details.children)


def test_summary_displays_availability_counters():
    summary = render_summary(_overview())

    values = [
        item.children for item in _components(summary) if isinstance(item, html.Div) and isinstance(item.children, str)
    ]

    assert "Available" in values
    assert "2/3" in values
    assert "Unavailable" in values
    assert "1" in values


def test_empty_summary_has_unavailable_statistics():
    overview = build_agreement_overview([], 0)
    summary = render_summary(overview)

    rows = _table_rows(_tables(summary)[0])

    assert rows[1] == ["Entire network", "0/0", "\u2014", "\u2014", "\u2014"]
    assert rows[2] == ["Unassigned", "0/0", "\u2014", "\u2014", "\u2014"]


def test_summary_explains_absolute_difference_notation():
    summary = render_summary(_overview())

    paragraphs = [str(item.children) for item in _components(summary) if isinstance(item, html.P)]

    assert any("Absolute difference |\u0394| (V)." in paragraph for paragraph in paragraphs)


def test_details_display_absolute_difference_and_readable_status():
    details = render_details(_overview(), "feeder:201")

    tables = _tables(details)

    available_rows = _table_rows(tables[0])
    unavailable_rows = _table_rows(tables[1])

    assert ["Absolute difference", "2"] in available_rows
    assert ["Data status", "Available"] in available_rows

    assert ["Absolute difference", "\u2014"] in unavailable_rows
    assert ["Data status", "Missing estimate"] in unavailable_rows


def test_measurement_cards_are_collapsed_by_default():
    details = render_details(_overview(), "feeder:201")

    cards = [item for item in _components(details) if isinstance(item, html.Details)]

    assert len(cards) == 2

    for card in cards:
        assert card.open is False
        assert isinstance(card.children[0], html.Summary)


def test_measurement_summary_displays_available_difference():
    details = render_details(_overview(), "feeder:201")

    summaries = [item for item in _components(details) if isinstance(item, html.Summary)]

    values = [item.children for item in _components(summaries[0]) if isinstance(item, html.Span)]

    assert "2 V" in values

    statuses = [
        item.children
        for item in _components(summaries[0])
        if isinstance(item, html.Span) and getattr(item, "className", None) == "agreement-measurement-status"
    ]

    assert statuses == ["Node 1 · Available"]


def test_measurement_summary_displays_unavailable_difference():
    details = render_details(_overview(), "feeder:201")

    summaries = [item for item in _components(details) if isinstance(item, html.Summary)]

    values = [item.children for item in _components(summaries[1]) if isinstance(item, html.Span)]

    assert "Unavailable" in values

    statuses = [
        item.children
        for item in _components(summaries[1])
        if isinstance(item, html.Span) and getattr(item, "className", None) == "agreement-measurement-status"
    ]

    assert statuses == ["Node 2 · Missing estimate"]


def test_expandable_measurements_retain_attribute_tables():
    details = render_details(_overview(), "feeder:201")

    cards = [item for item in _components(details) if isinstance(item, html.Details)]

    for card in cards:
        assert len(_tables(card)) == 1

    rows = _table_rows(_tables(cards[0])[0])

    assert ["Measured", "10490"] in rows
    assert ["Estimated", "10488"] in rows
    assert ["Feeder ID", "201"] in rows
    assert ["Feeder status", "Unverified"] in rows


def _scope_buttons(summary):
    return [
        item
        for item in _components(summary)
        if isinstance(item, html.Button) and isinstance(item.id, dict) and item.id.get("type") == "f13-agreement-scope"
    ]


def test_summary_scope_buttons_have_unique_ids():
    buttons = _scope_buttons(render_summary(_overview()))

    assert [button.id["scope"] for button in buttons] == [
        "network",
        "feeder:201",
        "unassigned",
    ]

    assert all(button.type == "button" for button in buttons)
    assert all(button.n_clicks == 0 for button in buttons)


def test_network_scope_is_selected_by_default():
    buttons = _scope_buttons(render_summary(_overview()))

    assert [button.to_plotly_json()["props"]["aria-pressed"] for button in buttons] == ["true", "false", "false"]


def test_summary_preserves_selected_feeder():
    buttons = _scope_buttons(render_summary(_overview(), "feeder:201"))

    assert [button.to_plotly_json()["props"]["aria-pressed"] for button in buttons] == ["false", "true", "false"]


def test_empty_unassigned_scope_is_disabled():
    overview = build_agreement_overview([], 0)
    buttons = _scope_buttons(render_summary(overview))

    assert buttons[0].disabled is False
    assert buttons[1].id["scope"] == "unassigned"
    assert buttons[1].disabled is True


def test_available_unassigned_scope_is_enabled():
    buttons = _scope_buttons(render_summary(_overview()))

    assert buttons[-1].id["scope"] == "unassigned"
    assert buttons[-1].disabled is False


def test_summary_can_select_unassigned_scope():
    buttons = _scope_buttons(render_summary(_overview(), "unassigned"))

    assert [button.to_plotly_json()["props"]["aria-pressed"] for button in buttons] == ["false", "false", "true"]


def test_summary_collects_discrepancies_once_per_group(monkeypatch):
    overview = _overview()
    group_type = type(overview.network)
    original_collect = group_type._absolute_discrepancies
    collected_groups = []

    def counted_collection(group):
        collected_groups.append(group)
        return original_collect(group)

    monkeypatch.setattr(
        group_type,
        "_absolute_discrepancies",
        counted_collection,
    )

    result = render_summary(overview)

    expected_groups = [
        overview.network,
        *overview.feeders.values(),
        overview.unassigned,
    ]

    assert result is not None
    assert len(collected_groups) == len(expected_groups)

    assert [id(group) for group in collected_groups] == [id(group) for group in expected_groups]


def test_numbered_pagination_has_persistent_targets():
    panel = get_feeder_agreement_html()
    numbers = _component_with_id(panel, PAGE_NUMBERS_ID)
    assert isinstance(numbers, html.Div)
    assert numbers.children == []
    for component_id in (PREVIOUS_ID, NEXT_ID):
        button = _component_with_id(panel, component_id)
        assert isinstance(button, html.Button)
        assert button.disabled is True


@pytest.mark.parametrize("count", [0, 1])
def test_page_numbers_hidden_for_single_or_empty_page(count):
    page = MeasurementPage((), 0, count, count, 5)
    assert render_page_numbers(page) == []


@pytest.mark.parametrize(
    ("index", "count", "expected"),
    [
        (0, 3, ["1", "2", "3"]),
        (0, 13, ["1", "2", "3", "4", "\u2026", "13"]),
        (6, 13, ["1", "\u2026", "6", "7", "8", "\u2026", "13"]),
        (12, 13, ["1", "\u2026", "10", "11", "12", "13"]),
        (4999, 10000, ["1", "\u2026", "4999", "5000", "5001", "\u2026", "10000"]),
    ],
)
def test_render_page_numbers(index, count, expected):
    page = MeasurementPage((), index, count, count * 5, 5)
    controls = render_page_numbers(page)
    assert [control.children for control in controls] == expected
    buttons = [control for control in controls if isinstance(control, html.Button)]
    assert [button.id for button in buttons] == [
        {"type": PAGE_BUTTON_TYPE, "page": int(label) - 1} for label in expected if label != "\u2026"
    ]
    for button in buttons:
        props = button.to_plotly_json()["props"]
        assert button.n_clicks == 0
        assert button.type == "button"
        assert props["aria-label"] == f"Page {button.children}"
        assert props["aria-current"] == ("page" if button.id["page"] == index else "false")
    for control in controls:
        if isinstance(control, html.Span):
            assert control.to_plotly_json()["props"]["aria-hidden"] == "true"


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, "\u2014"),
        (0.0, "0"),
        (2.0, "2"),
        (2.1, "2.1"),
        (2.68, "2.68"),
        (0.01, "0.01"),
        (0.001, "1e-3"),
        (10000.5, "10000.5"),
        (19998.0, "19998"),
        (20000.0, "20000"),
        (100000.0, "100000"),
        (1000000.0, "1e6"),
    ],
)
def test_compact_summary_number(value, expected):
    assert _summary_number(value) == expected


@pytest.mark.parametrize(("available", "total"), [(0, 0), (2, 3), (1000, 1000), (10000, 10000), (49999, 50000)])
def test_pair_count_preserves_complete_numbers(available, total):
    pairs = _pair_count(available, total)
    assert pairs.className == "agreement-pair-count"
    assert all(isinstance(part, html.Span) for part in pairs.children)
    assert [part.children for part in pairs.children] == [f"{available}/", str(total)]
    assert _cell_text(pairs) == f"{available}/{total}"


def test_summary_table_uses_content_aware_layout():
    table = _tables(render_summary(_overview()))[0]
    assert table.style["tableLayout"] == "auto"
