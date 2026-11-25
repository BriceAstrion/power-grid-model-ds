# SPDX-FileCopyrightText: Contributors to the Power Grid Model project <powergridmodel@lfenergy.org>
#
# SPDX-License-Identifier: MPL-2.0

"""Verify derived quantity discovery and heatmap routing."""

from types import SimpleNamespace

import numpy as np
import pytest
from power_grid_model import ComponentType, DatasetType, initialize_array

from power_grid_model_ds._core.visualizer import server_state
from power_grid_model_ds._core.visualizer.callbacks.config import update_appliances, update_electrical_attributes
from power_grid_model_ds._core.visualizer.electrical_uncertainty import get_available_electrical_quantities


@pytest.mark.parametrize(
    ("group", "residual", "sigma_attribute"),
    [
        (ComponentType.sym_voltage_sensor, "u_residual", "u_sigma"),
        (ComponentType.sym_power_sensor, "p_residual", "p_sigma"),
        (ComponentType.sym_power_sensor, "q_residual", "q_sigma"),
    ],
)
def test_derived_heatmap(monkeypatch, group, residual, sigma_attribute):
    output = initialize_array(DatasetType.sym_output, group, (2, 1))
    output["id"] = [[11], [11]]
    output[residual] = [[-6.0], [10.0]]
    data = {group: output}
    sensor = SimpleNamespace(id=np.array([11]), **{sigma_attribute: np.array([2.0])})
    grid = SimpleNamespace(**{group.value: sensor})
    monkeypatch.setattr(server_state, "get_grid", lambda: grid)
    monkeypatch.setattr(server_state, "get_update_data", lambda: None)
    monkeypatch.setattr(server_state, "get_output_data", lambda: data)
    derived = f"{residual}_over_sigma"
    available = get_available_electrical_quantities(data)
    options, _, disabled = update_electrical_attributes(group.value, available)
    assert not disabled
    assert {residual, derived} <= {option["value"] for option in options}
    parsed = {
        "1": {
            "data": {"id": "1", "group": "node", "associated_ids": {group.value: [11]}},
            "classes": "node",
        }
    }
    for scenario, expected in [(1, 3.0), (2, 5.0)]:
        elements, legend = update_appliances(
            show_appliances=True,
            component=group.value,
            quantity=derived,
            scenario_number=scenario,
            parsed_elements=parsed,
        )
        assert elements[0]["data"]["electrical_value"] == expected
        assert "discrepancy / sigma" in legend.children[0].children
    elements, _ = update_appliances(
        show_appliances=True, component=group.value, quantity=residual, scenario_number=1, parsed_elements=parsed
    )
    assert elements[0]["data"]["electrical_value"] == -6.0
    elements, legend = update_appliances(
        show_appliances=True, component=group.value, quantity=None, scenario_number=1, parsed_elements=parsed
    )
    assert elements == list(parsed.values())
    assert legend == ""


def test_no_derived_quantities_without_output():
    assert get_available_electrical_quantities(None) == {}


def test_unsupported_residuals_are_not_extended():
    group = ComponentType.sym_voltage_sensor
    output = initialize_array(DatasetType.sym_output, group, (1, 1))
    attributes = get_available_electrical_quantities({group: output})[group.value]
    assert "u_angle_residual" in attributes
    assert "u_angle_residual_over_sigma" not in attributes
