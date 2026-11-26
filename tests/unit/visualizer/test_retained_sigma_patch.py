# SPDX-FileCopyrightText: Contributors to the Power Grid Model project <powergridmodel@lfenergy.org>
#
# SPDX-License-Identifier: MPL-2.0

"""Targeted retained sigma-band updates."""

import numpy as np
import pytest
from dash.exceptions import PreventUpdate

from power_grid_model_ds._core.visualizer.callbacks import element_selection as es
from power_grid_model_ds._core.visualizer.measurement_comparison import MeasurementComparison


@pytest.mark.parametrize(
    ("group", "column"),
    [
        ("sym_voltage_sensor", "u_measured"),
        ("sym_power_sensor", "p_measured"),
        ("sym_power_sensor", "q_measured"),
    ],
)
@pytest.mark.parametrize("multiplier", [0.0, 2.0, 3.0])
def test_patch_only_bounds(monkeypatch, group, column, multiplier):
    comparison = MeasurementComparison(
        scenario_indices=np.array([0, 1]),
        measured=np.array([100.0, 110.0]),
        estimated=np.array([101.0, 112.0]),
        sigma=np.array([2.0, 3.0]),
    )
    monkeypatch.setattr(es, "get_grid", lambda: None)
    monkeypatch.setattr(es, "get_update_data", lambda: None)
    monkeypatch.setattr(es, "get_output_data", dict)
    monkeypatch.setattr(es, "get_symmetric_voltage_comparison", lambda *_: comparison)
    monkeypatch.setattr(es, "get_symmetric_power_comparison", lambda *_: comparison)
    patch = es.update_retained_sigma_bands(
        multiplier, {"type": "retained-sigma-comparison", "key": f"{group}|101|{column}"}
    )
    operations = patch.to_plotly_json()["operations"]
    assert [op["location"] for op in operations] == [["data", 0, "y"], ["data", 1, "y"], ["data", 1, "name"]]
    assert operations[0]["params"]["value"] == [100 - 2 * multiplier, 110 - 3 * multiplier]
    assert operations[1]["params"]["value"] == [100 + 2 * multiplier, 110 + 3 * multiplier]
    assert operations[2]["params"]["value"] == f"Measurement +/- {multiplier:g} sigma"


@pytest.mark.parametrize("value", [None, True, -1, "2", float("nan"), float("inf")])
def test_invalid_multiplier(value):
    with pytest.raises(PreventUpdate):
        es.update_retained_sigma_bands(value, {"key": "sym_voltage_sensor|101|u_measured"})


@pytest.mark.parametrize("key", ["bad", "node|101|u", "sym_power_sensor|101|u_measured"])
def test_unsupported_identity(key):
    with pytest.raises(PreventUpdate):
        es.update_retained_sigma_bands(2.0, {"key": key})
