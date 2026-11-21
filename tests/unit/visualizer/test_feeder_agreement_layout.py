# SPDX-FileCopyrightText: Contributors to the Power Grid Model project <powergridmodel@lfenergy.org>
#
# SPDX-License-Identifier: MPL-2.0

"""Unit tests for the F13 overview and drilldown presentation."""

from dash import dcc, html

from power_grid_model_ds._core.visualizer.feeder_agreement import (
    MeasurementIdentity,
    build_agreement_overview,
    make_agreement_record,
)
from power_grid_model_ds._core.visualizer.layout.feeder_agreement import (
    get_feeder_agreement_html,
    group_options,
    render_details,
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


def _table_rows(table):
    """Extract visible table cells in row order."""
    return [
        [str(cell.children) for cell in (row.children or [])] for row in _components(table) if isinstance(row, html.Tr)
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
    assert isinstance(dropdown, dcc.Dropdown)
    assert isinstance(details, html.Div)

    assert getattr(dropdown, "value", None) == "network"
    assert getattr(dropdown, "clearable", None) is False


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
    assert titles == ["Aggregated agreement overview"]


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


def test_summary_contains_descriptive_counts():
    summary = render_summary(_overview())

    tables = _tables(summary)
    assert len(tables) == 1

    rows = _table_rows(tables[0])

    assert rows == [
        ["Scope", "Total", "Available", "Unavailable"],
        ["Entire network", "3", "2", "1"],
        ["Feeder 201", "2", "1", "1"],
        ["Unassigned", "1", "1", "0"],
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

    headings = [item.children for item in _components(details) if isinstance(item, html.H5)]

    assert headings == [
        "Sensor 11 — Node 1",
        "Sensor 12 — Node 2",
    ]

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


def test_measurement_values_use_blue_text():
    details = render_details(_overview(), "feeder:201")

    tables = _tables(details)
    assert tables

    for table in tables:
        body = next(item for item in _components(table) if isinstance(item, html.Tbody))

        assert body.children is not None
        for row in body.children:
            value_cell = row.children[1]

            assert isinstance(value_cell, html.Td)
            assert value_cell.style["color"] == "#0d6efd"


def test_empty_drilldown_has_explicit_message():
    overview = build_agreement_overview([], 0)
    details = render_details(overview, "network")

    assert isinstance(details, html.Div)
    assert details.role == "status"
    assert "No contributing measurements" in str(details.children)
