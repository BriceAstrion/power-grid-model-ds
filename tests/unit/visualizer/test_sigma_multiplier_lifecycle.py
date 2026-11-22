# SPDX-FileCopyrightText: Contributors to the Power Grid Model project <powergridmodel@lfenergy.org>
#
# SPDX-License-Identifier: MPL-2.0

"""Regression tests for the shared sigma multiplier callback lifecycle."""

from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import Mock

import numpy as np
import plotly.graph_objects as go
import pytest
from dash.exceptions import PreventUpdate

from power_grid_model_ds._core.visualizer.callbacks import element_selection


@pytest.mark.parametrize("value", [0, 0.5, 2, 5.0])
def test_store_accepts_valid_multiplier(value):
    """Store a valid multiplier for subsequent measurement selections."""
    stored = element_selection.store_valid_sigma_multiplier(value)

    assert stored == float(value)
    assert isinstance(stored, float)


@pytest.mark.parametrize(
    "value",
    [None, -1, True, "2", float("nan"), float("inf"), -float("inf")],
)
def test_store_rejects_invalid_multiplier(value):
    """Do not replace the last valid multiplier with invalid input."""
    with pytest.raises(PreventUpdate):
        element_selection.store_valid_sigma_multiplier(value)


@pytest.mark.parametrize(
    ("group", "attribute", "helper_name"),
    [
        (
            "sym_voltage_sensor",
            "u_measured",
            "_get_voltage_comparison_figure",
        ),
        (
            "sym_power_sensor",
            "p_measured",
            "_get_power_comparison_figure",
        ),
        (
            "sym_power_sensor",
            "q_measured",
            "_get_power_comparison_figure",
        ),
    ],
)
def test_new_selection_receives_stored_multiplier(monkeypatch, group, attribute, helper_name):
    """Forward the current valid multiplier to the comparison builder."""
    multiplier = element_selection.store_valid_sigma_multiplier(1.5)

    expected = go.Figure(data=[go.Scatter(y=[1.0, 2.0])])
    builder = Mock(return_value=expected)

    monkeypatch.setattr(element_selection, helper_name, builder)

    figure, style = element_selection.cell_selection_graph(
        {"group": group, "id": 17, "column": attribute},
        node_data=[{"id": "node-1"}],
        edge_data=[],
        sigma_multiplier=multiplier,
    )

    assert figure is expected
    assert style == {"display": "block"}

    if group == "sym_voltage_sensor":
        builder.assert_called_once_with(17, multiplier)
    else:
        builder.assert_called_once_with(17, attribute, multiplier)


def _make_entry(group, sensor_id, attribute):
    """Create a retained measurement with independently known bounds."""
    return {
        "key": f"{group}|{sensor_id}|{attribute}",
        "comparison": {
            "data": [
                {"name": "Lower sigma bound", "y": [94.0, 101.0]},
                {"name": "Measurement +/- 3 sigma", "y": [106.0, 119.0]},
                {"name": "Measured", "y": [100.0, 110.0]},
                {"name": "Calculated", "y": [99.0, 108.0]},
            ],
            "layout": {
                "meta": {
                    "comparison_type": group,
                    "sensor_id": sensor_id,
                    "measurement_attribute": attribute,
                    "scenario_indices": [0, 1],
                    "measured": [100.0, 110.0],
                    "estimated": [99.0, 108.0],
                    "sigma": [2.0, 3.0],
                },
            },
        },
        "diagnostic": {
            "data": [{"y": [0.5, 2.0 / 3.0]}],
            "layout": {
                "meta": {
                    "retention_group": group,
                    "retention_sensor_id": sensor_id,
                    "retention_attribute": attribute,
                },
            },
        },
    }


def _make_entries():
    """Provide voltage and distinct active/reactive power comparisons."""
    return [
        _make_entry("sym_voltage_sensor", 17, "u_measured"),
        _make_entry("sym_power_sensor", 18, "p_measured"),
        _make_entry("sym_power_sensor", 18, "q_measured"),
    ]


def _trigger_multiplier(monkeypatch, entries, multiplier):
    """Invoke retention with a multiplier-store callback trigger."""
    monkeypatch.setattr(
        element_selection,
        "callback_context",
        SimpleNamespace(
            triggered_id="valid-sigma-multiplier",
            triggered=[
                {
                    "prop_id": "valid-sigma-multiplier.data",
                    "value": multiplier,
                },
            ],
        ),
    )

    # Supply a valid but unretained active comparison. A multiplier
    # change must not capture it or restore a previously removed graph.
    active = _make_entry("sym_voltage_sensor", 99, "u_measured")

    return element_selection.retain_uncertainty_diagnostics(
        [active["diagnostic"], {"display": "block"}],
        {
            "multiplier": multiplier,
            "removal_controls": [[], [], 0],
        },
        [active["comparison"], {"display": "block"}],
        {
            "group": "sym_voltage_sensor",
            "id": 99,
            "column": "u_measured",
        },
        entries,
    )


def test_multiplier_callback_updates_existing_entries_only(monkeypatch):
    """Update all bands without capturing the active comparison."""
    entries = _make_entries()
    original = deepcopy(entries)

    updated = _trigger_multiplier(monkeypatch, entries, 2.0)

    assert len(updated) == len(original)

    for before, after in zip(original, updated, strict=True):
        assert after["key"] == before["key"]

        np.testing.assert_allclose(
            after["comparison"]["data"][0]["y"],
            [96.0, 104.0],
        )
        np.testing.assert_allclose(
            after["comparison"]["data"][1]["y"],
            [104.0, 116.0],
        )

        assert after["comparison"]["data"][1]["name"] == ("Measurement +/- 2 sigma")

        assert after["comparison"]["data"][2:] == (before["comparison"]["data"][2:])
        assert after["comparison"]["layout"] == (before["comparison"]["layout"])
        assert after["diagnostic"] == before["diagnostic"]

    assert entries == original


def test_multiplier_callback_preserves_removed_diagnostic(monkeypatch):
    """Do not restore a diagnostic removed from a retained comparison."""
    entries = _make_entries()

    entries = element_selection._update_retained_measurements(
        entries,
        action="remove-diagnostic",
        key=entries[0]["key"],
    )

    updated = _trigger_multiplier(monkeypatch, entries, 2.0)

    assert len(updated) == len(entries)
    assert updated[0]["diagnostic"] is None
    assert updated[0]["comparison"]["data"][1]["name"] == ("Measurement +/- 2 sigma")


def test_multiplier_callback_preserves_removed_comparison(monkeypatch):
    """Do not restore a removed measurement pair."""
    entries = _make_entries()
    removed_key = entries[1]["key"]

    entries = element_selection._update_retained_measurements(
        entries,
        action="remove-measurement",
        key=removed_key,
    )

    updated = _trigger_multiplier(monkeypatch, entries, 2.0)

    assert len(updated) == len(entries)
    assert all(item["key"] != removed_key for item in updated)


def test_multiplier_callback_does_not_repopulate_workspace(monkeypatch):
    """An empty workspace must remain empty after a multiplier change."""
    entries = element_selection._update_retained_measurements(
        _make_entries(),
        action="clear",
    )

    with pytest.raises(PreventUpdate):
        _trigger_multiplier(monkeypatch, entries, 2.0)


def test_multiplier_callback_rejects_invalid_value(monkeypatch):
    """Reject invalid multiplier state without modifying retained graphs."""
    entries = _make_entries()
    original = deepcopy(entries)

    with pytest.raises(PreventUpdate):
        _trigger_multiplier(monkeypatch, entries, -1.0)

    assert entries == original
