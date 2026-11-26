# SPDX-FileCopyrightText: Contributors to the Power Grid Model project <powergridmodel@lfenergy.org>
#
# SPDX-License-Identifier: MPL-2.0

"""Focused tests for the additive generic measurement-comparison API.

Copy to tests/unit/visualizer/test_generic_measurement_comparison.py.
"""

from types import SimpleNamespace
from unittest.mock import Mock

import numpy as np
import pytest
from numpy.testing import assert_allclose, assert_array_equal
from power_grid_model import ComponentType, MeasuredTerminalType

from power_grid_model_ds._core.visualizer import measurement_comparison as module


def _array(ids, **fields):
    """Minimal stand-in for the grid's column-oriented IdArray interface."""
    return SimpleNamespace(id=np.asarray(ids, dtype=np.int64), **{k: np.asarray(v) for k, v in fields.items()})


def _grid(sensor_type, sensor_id, measured_object, terminal=None, components=None):
    values = {"measured_object": [measured_object]}
    if terminal is not None:
        values["measured_terminal_type"] = [terminal.value]
    grid = SimpleNamespace(**{sensor_type.value: _array([sensor_id], **values)})
    for component, ids in (components or {}).items():
        setattr(grid, component.value, _array(ids))
    return grid


@pytest.mark.parametrize("sensor_type", [ComponentType.sym_voltage_sensor, ComponentType.asym_voltage_sensor])
def test_voltage_sensor_maps_to_node(sensor_type):
    grid = _grid(sensor_type, 17, 42)
    assert module.get_associated_sensor_data(grid, sensor_type, 17, "u_measured") == (ComponentType.node, "u", 42)


@pytest.mark.parametrize(
    ("terminal", "component", "attribute", "expected"),
    [
        (MeasuredTerminalType.branch_from, ComponentType.line, "p_measured", "p_from"),
        (MeasuredTerminalType.branch_to, ComponentType.transformer, "q_measured", "q_to"),
        (MeasuredTerminalType.branch3_2, ComponentType.three_winding_transformer, "i_measured", "i_2"),
        (MeasuredTerminalType.source, ComponentType.source, "p_measured", "p"),
        (MeasuredTerminalType.shunt, ComponentType.shunt, "q_measured", "q"),
        (MeasuredTerminalType.load, ComponentType.sym_load, "p_measured", "p"),
        (MeasuredTerminalType.generator, ComponentType.sym_gen, "i_measured", "i"),
    ],
)
def test_flow_sensor_maps_to_expected_output(terminal, component, attribute, expected):
    sensor_type = ComponentType.sym_power_sensor if attribute != "i_measured" else ComponentType.sym_current_sensor
    grid = _grid(sensor_type, 17, 42, terminal, {component: [42]})
    # Grid stand-in exposes all candidate component collections, even when empty.
    for candidate in module._FLOW_SENSOR_TERMINAL_COMPONENT_TYPES[terminal]:
        if not hasattr(grid, candidate.value):
            setattr(grid, candidate.value, _array([]))
    assert module.get_associated_sensor_data(grid, sensor_type, 17, attribute) == (component, expected, 42)


def test_flow_mapping_ignores_other_component_ids():
    grid = _grid(
        ComponentType.sym_power_sensor,
        17,
        42,
        MeasuredTerminalType.branch_from,
        {ComponentType.line: [99], ComponentType.transformer: [42]},
    )
    for candidate in module._BRANCH_COMPONENT_TYPES:
        if not hasattr(grid, candidate.value):
            setattr(grid, candidate.value, _array([]))
    assert module.get_associated_sensor_data(grid, ComponentType.sym_power_sensor, 17, "p_measured") == (
        ComponentType.transformer,
        "p_from",
        42,
    )


@pytest.mark.parametrize("sensor_id", [999, 18])
def test_missing_sensor_rejected(sensor_id):
    grid = _grid(ComponentType.sym_voltage_sensor, 17, 42)
    with pytest.raises(ValueError, match="exactly one"):
        module.get_associated_sensor_data(grid, ComponentType.sym_voltage_sensor, sensor_id, "u_measured")


def test_duplicate_sensor_rejected():
    grid = SimpleNamespace(sym_voltage_sensor=_array([17, 17], measured_object=[42, 43]))
    with pytest.raises(ValueError, match="exactly one"):
        module.get_associated_sensor_data(grid, ComponentType.sym_voltage_sensor, 17, "u_measured")


def test_wrong_voltage_attribute_rejected():
    grid = _grid(ComponentType.sym_voltage_sensor, 17, 42)
    with pytest.raises(ValueError, match="Voltage sensors"):
        module.get_associated_sensor_data(grid, ComponentType.sym_voltage_sensor, 17, "p_measured")


def test_unknown_attribute_rejected():
    grid = _grid(ComponentType.sym_voltage_sensor, 17, 42)
    with pytest.raises(ValueError, match="Unsupported measured attribute"):
        module.get_associated_sensor_data(grid, ComponentType.sym_voltage_sensor, 17, "angle_measured")


def test_non_sensor_component_rejected():
    with pytest.raises(ValueError, match="Unsupported sensor type"):
        module.get_associated_sensor_data(SimpleNamespace(), ComponentType.node, 17, "u_measured")


def test_missing_measured_component_rejected():
    grid = _grid(ComponentType.sym_power_sensor, 17, 42, MeasuredTerminalType.source, {ComponentType.source: [99]})
    with pytest.raises(ValueError, match="was not found"):
        module.get_associated_sensor_data(grid, ComponentType.sym_power_sensor, 17, "p_measured")


def test_absent_candidate_component_collection_is_handled():
    """Expose whether mapping assumes all grid component collections exist."""
    grid = _grid(
        ComponentType.sym_power_sensor, 17, 42, MeasuredTerminalType.branch_from, {ComponentType.transformer: [42]}
    )
    assert module.get_associated_sensor_data(grid, ComponentType.sym_power_sensor, 17, "p_measured") == (
        ComponentType.transformer,
        "p_from",
        42,
    )


def test_generic_voltage_preserves_scenarios_and_missing_estimates(monkeypatch):
    voltage = module.VoltageComparison(
        sensor_id=17,
        node_id=42,
        scenarios=np.array([0, 1, 2]),
        measured=np.array([230.0, 231.0, 232.0]),
        estimated=np.array([229.0, np.nan, 233.0]),
        sigma=np.array([1.0, 1.0, 2.0]),
    )
    wrapped = Mock(return_value=voltage)
    monkeypatch.setattr(module, "get_symmetric_voltage_comparison", wrapped)
    grid, updates, outputs = object(), object(), object()
    result = module.get_sensor_comparison(grid, ComponentType.sym_voltage_sensor, 17, "u_measured", updates, outputs)
    wrapped.assert_called_once_with(grid, updates, outputs, 17)
    assert isinstance(result, module.MeasurementComparison)
    assert_array_equal(result.scenario_indices, [0, 1, 2])
    assert_array_equal(result.measured, voltage.measured)
    assert_array_equal(result.estimated, voltage.estimated)
    assert_array_equal(result.sigma, voltage.sigma)


@pytest.mark.parametrize("attribute", ["p_measured", "q_measured"])
def test_generic_power_delegates_to_existing_function(monkeypatch, attribute):
    comparison = module.MeasurementComparison(np.array([0, 1]), np.array([5.0, 6.0]), np.array([4.0, np.nan]), None)
    wrapped = Mock(return_value=comparison)
    monkeypatch.setattr(module, "get_symmetric_power_comparison", wrapped)
    grid, updates, outputs = object(), object(), object()
    result = module.get_sensor_comparison(grid, ComponentType.sym_power_sensor, 17, attribute, updates, outputs)
    assert result is comparison
    wrapped.assert_called_once_with(grid, updates, outputs, 17, attribute)


@pytest.mark.parametrize(
    ("sensor_type", "attribute"),
    [
        (ComponentType.asym_voltage_sensor, "u_measured"),
        (ComponentType.sym_current_sensor, "i_measured"),
        (ComponentType.asym_power_sensor, "p_measured"),
    ],
)
def test_generic_comparison_rejects_unimplemented_types(sensor_type, attribute):
    with pytest.raises(NotImplementedError, match="validated phase and output support"):
        module.get_sensor_comparison(object(), sensor_type, 17, attribute, None, {})


def _comparison(measured, sigma):
    measured = np.asarray(measured, dtype=float)
    return module.MeasurementComparison(
        scenario_indices=np.arange(measured.shape[0]),
        measured=measured,
        estimated=np.zeros_like(measured),
        sigma=None if sigma is None else np.asarray(sigma, dtype=float),
    )


def test_scalar_sigma_bounds():
    lower, upper = module.get_sigma_bounds(_comparison([10.0, 20.0], [1.0, 2.0]), 2.0)
    assert_allclose(lower, [8.0, 16.0])
    assert_allclose(upper, [12.0, 24.0])


def test_three_phase_sigma_bounds_with_phase_sigma():
    comparison = _comparison([[10.0, 20.0, 30.0], [40.0, 50.0, 60.0]], [[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]])
    lower, upper = module.get_sigma_bounds(comparison, 2.0)
    assert_allclose(lower, [[8.0, 16.0, 24.0], [32.0, 40.0, 48.0]])
    assert_allclose(upper, [[12.0, 24.0, 36.0], [48.0, 60.0, 72.0]])


def test_three_phase_sigma_bounds_with_scenario_sigma():
    comparison = _comparison([[10.0, 20.0, 30.0], [40.0, 50.0, 60.0]], [1.0, 2.0])
    lower, upper = module.get_sigma_bounds(comparison, 2.0)
    assert_allclose(lower, [[8.0, 18.0, 28.0], [36.0, 46.0, 56.0]])
    assert_allclose(upper, [[12.0, 22.0, 32.0], [44.0, 54.0, 64.0]])


def test_nonfinite_sigma_becomes_nan_without_hiding_valid_phases():
    lower, upper = module.get_sigma_bounds(_comparison([[10.0, 20.0]], [[1.0, np.nan]]), 2.0)
    assert_allclose(lower, [[8.0, np.nan]])
    assert_allclose(upper, [[12.0, np.nan]])


@pytest.mark.parametrize("multiplier", [-1.0, float("nan"), float("inf")])
def test_invalid_sigma_multiplier_rejected(multiplier):
    with pytest.raises(ValueError, match="finite and non-negative"):
        module.get_sigma_bounds(_comparison([10.0], [1.0]), multiplier)


def test_missing_sigma_rejected():
    with pytest.raises(ValueError, match="required"):
        module.get_sigma_bounds(_comparison([10.0], None), 2.0)


def test_negative_sigma_rejected():
    with pytest.raises(ValueError, match="non-negative"):
        module.get_sigma_bounds(_comparison([10.0], [-1.0]), 2.0)


@pytest.mark.parametrize(
    ("measured", "sigma"),
    [([[10.0, 20.0], [30.0, 40.0]], [1.0]), ([[10.0, 20.0]], [[1.0, 2.0, 3.0]]), ([10.0, 20.0], [1.0])],
)
def test_incompatible_sigma_shapes_rejected(measured, sigma):
    with pytest.raises(ValueError, match="Sigma"):
        module.get_sigma_bounds(_comparison(measured, sigma), 2.0)
