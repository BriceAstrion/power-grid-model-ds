# SPDX-FileCopyrightText: Contributors to the Power Grid Model project <powergridmodel@lfenergy.org>
#
# SPDX-License-Identifier: MPL-2.0

"""Unit tests for the configurable measurement-comparison sigma multiplier."""

from copy import deepcopy

import numpy as np
import pytest
from dash.exceptions import PreventUpdate

from power_grid_model_ds._core.visualizer.callbacks.element_selection import (
    _update_retained_measurements,
    update_sigma_multiplier_visibility,
)
from power_grid_model_ds._core.visualizer.callbacks.sigma_multiplier import update_voltage_sigma_bands


@pytest.fixture
def comparison_figure():
    return {
        "data": [
            {"name": "Lower sigma bound", "y": [224.0, 226.0, 224.0]},
            {"name": "Measurement +/- 3 sigma", "y": [236.0, 244.0, 236.0]},
            {"name": "Measured voltage", "y": [230.0, 235.0, 230.0]},
            {"name": "Calculated voltage", "y": [229.0, 231.0, 228.0]},
        ],
        "layout": {
            "meta": {
                "comparison_type": "sym_voltage_sensor",
                "sensor_id": 17,
                "sigma": [2.0, 3.0, 2.0],
                "measured": [230.0, 235.0, 230.0],
            }
        },
    }


@pytest.fixture
def selected_cell():
    return {"group": "sym_voltage_sensor", "id": 17, "column": "u_measured"}


def _patch_assignments(patch):
    """Return the assigned locations and values from a Dash Patch."""
    operations = patch.to_plotly_json()["operations"]
    assert all(operation["operation"] == "Assign" for operation in operations)
    return {tuple(operation["location"]): operation["params"]["value"] for operation in operations}


@pytest.mark.parametrize(
    ("multiplier", "expected_lower", "expected_upper"),
    [
        (0, [230.0, 235.0, 230.0], [230.0, 235.0, 230.0]),
        (2, [226.0, 229.0, 226.0], [234.0, 241.0, 234.0]),
        (4, [222.0, 223.0, 222.0], [238.0, 247.0, 238.0]),
        (0.5, [229.0, 233.5, 229.0], [231.0, 236.5, 231.0]),
    ],
)
def test_multiplier_updates_only_sigma_bands(
    comparison_figure, selected_cell, multiplier, expected_lower, expected_upper
):
    original = deepcopy(comparison_figure)
    assignments = _patch_assignments(update_voltage_sigma_bands(multiplier, comparison_figure, selected_cell))
    assert set(assignments) == {("data", 0, "y"), ("data", 1, "y"), ("data", 1, "name")}
    np.testing.assert_allclose(assignments[("data", 0, "y")], expected_lower)
    np.testing.assert_allclose(assignments[("data", 1, "y")], expected_upper)
    assert assignments[("data", 1, "name")] == f"Measurement +/- {multiplier:g} sigma"
    assert comparison_figure == original


def test_repeated_changes_use_original_sigma(comparison_figure, selected_cell):
    first = _patch_assignments(update_voltage_sigma_bands(2, comparison_figure, selected_cell))
    second = _patch_assignments(update_voltage_sigma_bands(4, comparison_figure, selected_cell))
    np.testing.assert_allclose(first[("data", 0, "y")], [226, 229, 226])
    np.testing.assert_allclose(second[("data", 0, "y")], [222, 223, 222])
    np.testing.assert_allclose(second[("data", 1, "y")], [238, 247, 238])


@pytest.mark.parametrize("invalid", [None, -1, -0.1, float("nan"), float("inf"), -float("inf"), True, "2"])
def test_invalid_multiplier_is_ignored(comparison_figure, selected_cell, invalid):
    with pytest.raises(PreventUpdate):
        update_voltage_sigma_bands(invalid, comparison_figure, selected_cell)


@pytest.mark.parametrize(
    "cell",
    [
        None,
        {"group": "sym_voltage_sensor", "id": 18, "column": "u_measured"},
        {"group": "sym_voltage_sensor", "id": 17, "column": "sigma"},
        {"group": "node", "id": 17, "column": "u_measured"},
    ],
)
def test_unrelated_selection_is_ignored(comparison_figure, cell):
    with pytest.raises(PreventUpdate):
        update_voltage_sigma_bands(2, comparison_figure, cell)


def test_non_comparison_graph_is_ignored(comparison_figure, selected_cell):
    comparison_figure["layout"].pop("meta")
    with pytest.raises(PreventUpdate):
        update_voltage_sigma_bands(2, comparison_figure, selected_cell)


def test_missing_sigma_values_remain_missing(comparison_figure, selected_cell):
    comparison_figure["layout"]["meta"]["sigma"] = [2.0, None, 2.0]
    assignments = _patch_assignments(update_voltage_sigma_bands(2, comparison_figure, selected_cell))
    assert np.isnan(assignments[("data", 0, "y")][1])
    assert np.isnan(assignments[("data", 1, "y")][1])
    assert assignments[("data", 0, "y")][0] == 226
    assert assignments[("data", 0, "y")][2] == 226


def test_visibility_only_for_visible_comparison(comparison_figure):
    assert update_sigma_multiplier_visibility(comparison_figure, {"display": "block"})["display"] == "block"
    assert update_sigma_multiplier_visibility(comparison_figure, {"display": "none"}) == {"display": "none"}
    assert update_sigma_multiplier_visibility({}, {"display": "block"}) == {"display": "none"}
    assert update_sigma_multiplier_visibility(comparison_figure, None) == {"display": "none"}


def test_visibility_hides_for_fallback_graph(comparison_figure):
    comparison_figure["layout"].pop("meta")
    assert update_sigma_multiplier_visibility(comparison_figure, {"display": "block"}) == {"display": "none"}


def test_plotly_encoded_y_values_do_not_block_multiplier(comparison_figure, selected_cell):
    comparison_figure["data"][2]["y"] = {"dtype": "f8", "bdata": "opaque"}
    assignments = _patch_assignments(update_voltage_sigma_bands(2, comparison_figure, selected_cell))
    np.testing.assert_allclose(assignments[("data", 0, "y")], [226, 229, 226])
    np.testing.assert_allclose(assignments[("data", 1, "y")], [234, 241, 234])


@pytest.mark.parametrize(
    ("attribute", "measured", "sigma"),
    [
        ("p_measured", [10.0, 10.0], [2.0, 2.0]),
        ("q_measured", [5.0, 5.0], [1.0, 1.0]),
    ],
)
def test_power_multiplier_updates_bands(attribute, measured, sigma):
    figure = {
        "data": [
            {"name": "Lower sigma bound", "y": [0.0, 0.0]},
            {"name": "Measurement +/- 3 sigma", "y": [0.0, 0.0]},
            {"name": "Measured", "y": measured},
            {"name": "Calculated", "y": [9.0, 11.0]},
        ],
        "layout": {
            "meta": {
                "comparison_type": "sym_power_sensor",
                "sensor_id": 201,
                "measurement_attribute": attribute,
                "measured": measured,
                "sigma": sigma,
            }
        },
    }
    selected = {"group": "sym_power_sensor", "id": 201, "column": attribute}
    assignments = _patch_assignments(update_voltage_sigma_bands(2.0, figure, selected))
    np.testing.assert_allclose(assignments[("data", 0, "y")], np.array(measured) - 2 * np.array(sigma))
    np.testing.assert_allclose(assignments[("data", 1, "y")], np.array(measured) + 2 * np.array(sigma))
    assert assignments[("data", 1, "name")] == "Measurement +/- 2 sigma"


def test_power_multiplier_rejects_wrong_quantity():
    figure = {
        "data": [{}, {}, {}, {}],
        "layout": {
            "meta": {
                "comparison_type": "sym_power_sensor",
                "sensor_id": 201,
                "measurement_attribute": "p_measured",
                "measured": [10.0],
                "sigma": [2.0],
            }
        },
    }
    with pytest.raises(PreventUpdate):
        update_voltage_sigma_bands(2.0, figure, {"group": "sym_power_sensor", "id": 201, "column": "q_measured"})


def test_power_without_sigma_hides_multiplier():
    figure = {
        "data": [{}, {}],
        "layout": {
            "meta": {
                "comparison_type": "sym_power_sensor",
                "sensor_id": 201,
                "measurement_attribute": "p_measured",
            }
        },
    }
    assert update_sigma_multiplier_visibility(figure, {"display": "block"}) == {"display": "none"}


def test_power_with_sigma_shows_multiplier():
    figure = {
        "data": [{}, {}, {}, {}],
        "layout": {
            "meta": {
                "comparison_type": "sym_power_sensor",
                "sensor_id": 201,
                "measurement_attribute": "p_measured",
                "measured": [10.0],
                "sigma": [2.0],
            }
        },
    }
    assert update_sigma_multiplier_visibility(figure, {"display": "block"})["display"] == "block"


def _global_sigma_entries():
    """Create retained voltage, active and reactive power comparisons."""
    entries = []

    measurements = [
        ("sym_voltage_sensor", 403, "u_measured", [230.0, 235.0], [2.0, 3.0]),
        ("sym_power_sensor", 604, "p_measured", [10.0, 12.0], [2.0, 2.0]),
        ("sym_power_sensor", 604, "q_measured", [5.0, 6.0], [1.0, 1.0]),
    ]

    for group, sensor_id, attribute, measured, sigma in measurements:
        measured_array = np.asarray(measured)
        sigma_array = np.asarray(sigma)

        comparison = {
            "data": [
                {
                    "name": "Lower sigma bound",
                    "y": (measured_array - 3 * sigma_array).tolist(),
                },
                {
                    "name": "Measurement +/- 3 sigma",
                    "y": (measured_array + 3 * sigma_array).tolist(),
                },
                {"name": "Measured", "y": measured},
                {"name": "Calculated", "y": [value - 1 for value in measured]},
            ],
            "layout": {
                "meta": {
                    "comparison_type": group,
                    "sensor_id": sensor_id,
                    "measurement_attribute": attribute,
                    "measured": measured,
                    "sigma": sigma,
                }
            },
        }

        diagnostic = {
            "data": [
                {
                    "x": [0, 1],
                    "y": (1 / sigma_array).tolist(),
                    "mode": "lines",
                }
            ],
            "layout": {"title": "Normalized residual"},
        }

        entries.append(
            {
                "key": f"{group}|{sensor_id}|{attribute}",
                "comparison": comparison,
                "diagnostic": diagnostic,
            }
        )

    return entries


@pytest.mark.parametrize("multiplier", [0, 0.5, 2, 4])
def test_global_multiplier_updates_all_retained_comparisons(multiplier):
    """Apply the same multiplier to all retained measurement comparisons."""
    entries = _global_sigma_entries()

    updated = _update_retained_measurements(
        entries,
        action="update-multiplier",
        multiplier=multiplier,
    )

    assert len(updated) == 3

    for entry in updated:
        figure = entry["comparison"]
        meta = figure["layout"]["meta"]
        measured = np.asarray(meta["measured"])
        sigma = np.asarray(meta["sigma"])

        np.testing.assert_allclose(
            figure["data"][0]["y"],
            measured - multiplier * sigma,
        )
        np.testing.assert_allclose(
            figure["data"][1]["y"],
            measured + multiplier * sigma,
        )

        assert figure["data"][1]["name"] == (f"Measurement +/- {multiplier:g} sigma")


def test_global_multiplier_preserves_diagnostics_and_measurements():
    """Changing the bands must not modify residuals or source series."""
    entries = _global_sigma_entries()
    original = deepcopy(entries)

    updated = _update_retained_measurements(
        entries,
        action="update-multiplier",
        multiplier=2,
    )

    for before, after in zip(original, updated, strict=True):
        assert after["key"] == before["key"]
        assert after["diagnostic"] == before["diagnostic"]
        assert after["comparison"]["data"][2:] == before["comparison"]["data"][2:]
        assert after["comparison"]["layout"] == before["comparison"]["layout"]

    assert entries == original


def test_global_multiplier_does_not_restore_removed_diagnostic():
    """A multiplier change must preserve independent diagnostic removal."""
    entries = _global_sigma_entries()
    key = entries[0]["key"]

    entries = _update_retained_measurements(
        entries,
        action="remove-diagnostic",
        key=key,
    )

    updated = _update_retained_measurements(
        entries,
        action="update-multiplier",
        multiplier=2,
    )

    assert len(updated) == 3
    assert updated[0]["diagnostic"] is None
    assert updated[0]["comparison"]["data"][1]["name"] == ("Measurement +/- 2 sigma")


def test_global_multiplier_does_not_restore_removed_measurement():
    """A multiplier change must not recreate a removed measurement pair."""
    entries = _global_sigma_entries()
    removed_key = entries[1]["key"]

    entries = _update_retained_measurements(
        entries,
        action="remove-measurement",
        key=removed_key,
    )

    updated = _update_retained_measurements(
        entries,
        action="update-multiplier",
        multiplier=2,
    )

    assert len(updated) == 2
    assert all(entry["key"] != removed_key for entry in updated)


def test_global_multiplier_after_clear_all():
    """Changing the multiplier must not repopulate an empty workspace."""
    entries = _update_retained_measurements(
        _global_sigma_entries(),
        action="clear",
    )

    assert (
        _update_retained_measurements(
            entries,
            action="update-multiplier",
            multiplier=2,
        )
        == []
    )


@pytest.mark.parametrize(
    "invalid",
    [None, -1, True, "2", float("nan"), float("inf"), -float("inf")],
)
def test_global_multiplier_invalid_input_preserves_entries(invalid):
    """Invalid input must preserve the last displayed comparison bands."""
    entries = _global_sigma_entries()
    original = deepcopy(entries)

    updated = _update_retained_measurements(
        entries,
        action="update-multiplier",
        multiplier=invalid,
    )

    assert updated == original
    assert entries == original


def test_global_multiplier_preserves_comparison_without_sigma():
    """Comparisons without uncertainty data must remain unchanged."""
    entries = _global_sigma_entries()

    figure = entries[0]["comparison"]
    figure["data"] = figure["data"][2:]
    figure["layout"]["meta"].pop("sigma")
    entries[0]["diagnostic"] = None

    original = deepcopy(entries[0])

    updated = _update_retained_measurements(
        entries,
        action="update-multiplier",
        multiplier=2,
    )

    assert updated[0] == original


def test_global_multiplier_visibility_with_retained_comparisons():
    """Keep the shared control visible after selecting an ordinary graph."""
    ordinary_figure = {"data": [{"y": [1.0, 2.0]}]}

    style = update_sigma_multiplier_visibility(
        ordinary_figure,
        {"display": "block"},
        _global_sigma_entries(),
    )

    assert style["display"] == "block"
