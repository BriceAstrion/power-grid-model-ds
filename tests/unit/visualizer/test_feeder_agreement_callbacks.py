# SPDX-FileCopyrightText: Contributors to the Power Grid Model project <powergridmodel@lfenergy.org>
#
# SPDX-License-Identifier: MPL-2.0

"""Unit tests for F13 scenario and drilldown callbacks."""

from unittest.mock import patch

from dash import html

from power_grid_model_ds._core.visualizer.callbacks.feeder_agreement import (
    _prepare_overview,
    choose_group,
    update_agreement_details,
    update_agreement_summary,
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
    ):
        details = update_agreement_details(1, "network")

    assert isinstance(details, html.Div)

    headings = [item.children for item in _components(details) if isinstance(item, html.H5)]

    assert headings == ["Sensor 11 — Node 1"]

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
