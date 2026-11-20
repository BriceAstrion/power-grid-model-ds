# SPDX-FileCopyrightText: Contributors to the Power Grid Model project <powergridmodel@lfenergy.org>
#
# SPDX-License-Identifier: MPL-2.0

"""Tests for symmetric voltage measurement comparisons."""

from types import SimpleNamespace

import numpy as np
import pytest
from numpy.testing import assert_array_equal
from power_grid_model import ComponentType, DatasetType, initialize_array

import power_grid_model_ds._core.visualizer.callbacks.element_selection as selection
from power_grid_model_ds import Grid
from power_grid_model_ds._core.visualizer.callbacks.element_selection import (
    _create_voltage_comparison_figure,
)
from power_grid_model_ds._core.visualizer.comparison_plot import create_measurement_comparison_figure
from power_grid_model_ds._core.visualizer.measurement_comparison import (
    MeasurementComparison,
    VoltageComparison,
    align_voltage_series,
    calculate_sigma_bands,
    get_measurement_sigma_bounds,
    get_symmetric_power_comparison,
    get_symmetric_voltage_comparison,
    get_voltage_sigma_bounds,
    prepare_voltage_comparison,
)


@pytest.fixture
def grid():
    """Create a minimal grid with one symmetric voltage sensor."""
    sensors = SimpleNamespace(
        id=np.array([101], dtype=np.int32),
        measured_object=np.array([10], dtype=np.int32),
        u_measured=np.array([230.0]),
        u_sigma=np.array([2.0]),
    )
    return SimpleNamespace(sym_voltage_sensor=sensors)


@pytest.fixture
def output_data():
    """Create three scenarios containing node voltage results."""
    nodes = initialize_array("sym_output", "node", (3, 1))
    nodes["id"] = 10
    nodes["u"][:, 0] = [229.0, 231.0, 228.0]
    return {ComponentType.node: nodes}


def test_base_measurements_are_repeated_across_scenarios(grid, output_data):
    """Without updates, each scenario uses the base sensor values."""
    result = get_symmetric_voltage_comparison(
        grid=grid,
        update_data=None,
        output_data=output_data,
        sensor_id=101,
    )

    assert_array_equal(result.scenario_indices, [0, 1, 2])
    assert_array_equal(result.measured, [230.0, 230.0, 230.0])
    assert_array_equal(result.estimated, [229.0, 231.0, 228.0])
    assert_array_equal(result.sigma, [2.0, 2.0, 2.0])


def test_measurement_update_affects_only_its_scenario(grid, output_data):
    """A measurement update must not change other scenarios."""
    updates = initialize_array("update", "sym_voltage_sensor", (3, 1))
    updates["id"] = 101
    updates["u_measured"][1, 0] = 235.0

    result = get_symmetric_voltage_comparison(
        grid,
        {ComponentType.sym_voltage_sensor: updates},
        output_data,
        101,
    )

    assert_array_equal(result.measured, [230.0, 235.0, 230.0])
    assert_array_equal(result.estimated, [229.0, 231.0, 228.0])
    assert_array_equal(result.sigma, [2.0, 2.0, 2.0])


def test_sigma_update_affects_only_its_scenario(grid, output_data):
    """Sigma updates must be independent of measurement updates."""
    updates = initialize_array("update", "sym_voltage_sensor", (3, 1))
    updates["id"] = 101
    updates["u_sigma"][2, 0] = 3.5

    result = get_symmetric_voltage_comparison(
        grid,
        {ComponentType.sym_voltage_sensor: updates},
        output_data,
        101,
    )

    assert_array_equal(result.measured, [230.0, 230.0, 230.0])
    assert_array_equal(result.sigma, [2.0, 2.0, 3.5])


def test_nan_updates_preserve_base_values(grid, output_data):
    """Unspecified floating-point updates retain base values."""
    updates = initialize_array("update", "sym_voltage_sensor", (3, 1))
    updates["id"] = 101

    result = get_symmetric_voltage_comparison(
        grid,
        {ComponentType.sym_voltage_sensor: updates},
        output_data,
        101,
    )

    assert_array_equal(result.measured, [230.0, 230.0, 230.0])
    assert_array_equal(result.sigma, [2.0, 2.0, 2.0])


def test_missing_node_result_preserves_scenario_position(grid, output_data):
    """A missing node result must not shift later scenarios."""
    nodes = output_data[ComponentType.node].copy()
    nodes["id"][1, 0] = 99

    result = get_symmetric_voltage_comparison(
        grid,
        None,
        {ComponentType.node: nodes},
        101,
    )

    assert_array_equal(result.scenario_indices, [0, 1, 2])
    assert_array_equal(result.estimated, [229.0, np.nan, 228.0])


def test_unknown_sensor_raises_value_error(grid, output_data):
    """An unknown sensor ID must be rejected."""
    with pytest.raises(ValueError, match="Expected exactly one voltage sensor"):
        get_symmetric_voltage_comparison(grid, None, output_data, 999)


def test_duplicate_sensor_id_raises_value_error(grid, output_data):
    """Ambiguous sensor IDs must be rejected."""
    grid.sym_voltage_sensor.id = np.array([101, 101])

    with pytest.raises(ValueError, match="Expected exactly one voltage sensor"):
        get_symmetric_voltage_comparison(grid, None, output_data, 101)


def test_missing_node_output_raises_value_error(grid):
    """Node output is required for this comparison."""
    with pytest.raises(ValueError, match="Node output is required"):
        get_symmetric_voltage_comparison(grid, None, {}, 101)


def test_mismatched_scenario_counts_raise_value_error(grid, output_data):
    """Sensor updates must match the number of output scenarios."""
    updates = initialize_array("update", "sym_voltage_sensor", (2, 1))
    updates["id"] = 101

    with pytest.raises(ValueError, match="scenario count"):
        get_symmetric_voltage_comparison(
            grid,
            {ComponentType.sym_voltage_sensor: updates},
            output_data,
            101,
        )


def test_duplicate_node_output_raises_value_error(grid):
    """Multiple matching node results in one scenario are invalid."""
    nodes = initialize_array("sym_output", "node", (3, 2))
    nodes["id"][:, 0] = 10
    nodes["id"][:, 1] = 99
    nodes["id"][1, 1] = 10

    with pytest.raises(ValueError, match="Duplicate node ID"):
        get_symmetric_voltage_comparison(
            grid,
            None,
            {ComponentType.node: nodes},
            101,
        )


def test_comparison_does_not_modify_input_data(grid, output_data):
    """Preparing a comparison must not mutate the supplied data."""
    updates = initialize_array("update", "sym_voltage_sensor", (3, 1))
    updates["id"] = 101
    updates["u_measured"][1, 0] = 235.0

    original_updates = updates.copy()
    original_nodes = output_data[ComponentType.node].copy()
    original_measurements = grid.sym_voltage_sensor.u_measured.copy()

    get_symmetric_voltage_comparison(
        grid,
        {ComponentType.sym_voltage_sensor: updates},
        output_data,
        101,
    )

    # Compare structured arrays field by field so NaN values
    # are treated as equal when they occur in the same positions.
    for field in updates.dtype.names or ():
        assert_array_equal(
            updates[field],
            original_updates[field],
        )

    for field in original_nodes.dtype.names or ():
        assert_array_equal(
            output_data[ComponentType.node][field],
            original_nodes[field],
        )

    assert_array_equal(
        grid.sym_voltage_sensor.u_measured,
        original_measurements,
    )


@pytest.mark.parametrize(
    ("multiplier", "expected_lower", "expected_upper"),
    [
        (0.0, [230.0, 235.0], [230.0, 235.0]),
        (1.0, [228.0, 232.0], [232.0, 238.0]),
        (2.0, [226.0, 229.0], [234.0, 241.0]),
        (3.0, [224.0, 226.0], [236.0, 244.0]),
    ],
)
def test_voltage_sigma_bounds(
    multiplier,
    expected_lower,
    expected_upper,
):
    comparison = VoltageComparison(
        sensor_id=101,
        node_id=10,
        scenarios=np.array([0, 1]),
        measured=np.array([230.0, 235.0]),
        estimated=np.array([231.0, 234.0]),
        sigma=np.array([2.0, 3.0]),
    )

    lower, upper = get_voltage_sigma_bounds(comparison, multiplier)

    np.testing.assert_allclose(lower, expected_lower)
    np.testing.assert_allclose(upper, expected_upper)


@pytest.mark.parametrize("multiplier", [-1.0, np.nan, np.inf])
def test_voltage_sigma_bounds_reject_invalid_multiplier(multiplier):
    comparison = VoltageComparison(
        sensor_id=101,
        node_id=10,
        scenarios=np.array([0]),
        measured=np.array([230.0]),
        estimated=np.array([231.0]),
        sigma=np.array([2.0]),
    )

    with pytest.raises(ValueError, match="Sigma multiplier"):
        get_voltage_sigma_bounds(comparison, multiplier)


def test_voltage_sigma_bounds_preserve_missing_sigma():
    comparison = VoltageComparison(
        sensor_id=101,
        node_id=10,
        scenarios=np.array([0, 1]),
        measured=np.array([230.0, 235.0]),
        estimated=np.array([231.0, 234.0]),
        sigma=np.array([2.0, np.nan]),
    )

    lower, upper = get_voltage_sigma_bounds(comparison, 2.0)

    np.testing.assert_allclose(lower, [226.0, np.nan])
    np.testing.assert_allclose(upper, [234.0, np.nan])


def test_voltage_comparison_figure_contains_sigma_bands():
    comparison = VoltageComparison(
        sensor_id=101,
        node_id=10,
        scenarios=np.array([0, 1, 2]),
        measured=np.array([230.0, 235.0, 230.0]),
        estimated=np.array([229.0, 231.0, 228.0]),
        sigma=np.array([2.0, 3.0, 2.0]),
    )

    figure = _create_voltage_comparison_figure(
        comparison,
        sensor_id=101,
        sigma_multiplier=2.0,
    )

    assert len(figure.data) == 4

    np.testing.assert_array_equal(
        figure.data[0].y,
        [226.0, 229.0, 226.0],
    )
    np.testing.assert_array_equal(
        figure.data[1].y,
        [234.0, 241.0, 234.0],
    )
    np.testing.assert_array_equal(
        figure.data[2].y,
        [230.0, 235.0, 230.0],
    )
    np.testing.assert_array_equal(
        figure.data[3].y,
        [229.0, 231.0, 228.0],
    )

    assert figure.data[1].fill == "tonexty"
    assert figure.data[2].name == "Measured voltage"
    assert figure.data[3].name == "Calculated voltage"
    assert figure.layout.showlegend is True


def test_voltage_comparison_figure_preserves_missing_values():
    comparison = VoltageComparison(
        sensor_id=101,
        node_id=10,
        scenarios=np.array([0, 1, 2]),
        measured=np.array([230.0, 230.0, 230.0]),
        estimated=np.array([229.0, np.nan, 228.0]),
        sigma=np.array([2.0, np.nan, 2.0]),
    )

    figure = _create_voltage_comparison_figure(
        comparison,
        sensor_id=101,
        sigma_multiplier=2.0,
    )

    np.testing.assert_allclose(
        figure.data[0].y,
        [226.0, np.nan, 226.0],
    )
    np.testing.assert_allclose(
        figure.data[1].y,
        [234.0, np.nan, 234.0],
    )
    np.testing.assert_allclose(
        figure.data[3].y,
        [229.0, np.nan, 228.0],
    )


@pytest.mark.parametrize("unsupported", [{"indptr": np.array([0, 1])}, np.zeros(3)])
def test_sparse_or_non_dense_sensor_updates_skip_comparison(monkeypatch, output_data, unsupported):
    """Unsupported sensor updates must not enter the dense voltage comparison."""
    monkeypatch.setattr(selection, "get_output_data", lambda: output_data)
    monkeypatch.setattr(
        selection,
        "get_update_data",
        lambda: {ComponentType.sym_voltage_sensor: unsupported},
    )

    assert selection._voltage_comparison_graph(101, 2.0) is None


@pytest.mark.parametrize("unsupported", [{"indptr": np.array([0, 1])}, np.zeros(3)])
def test_unsupported_sensor_updates_do_not_crash_cell_selection(monkeypatch, output_data, unsupported):
    """An unsupported update representation must not crash the selection callback."""
    monkeypatch.setattr(selection, "get_output_data", lambda: output_data)
    monkeypatch.setattr(
        selection,
        "get_update_data",
        lambda: {ComponentType.sym_voltage_sensor: unsupported},
    )

    figure, graph_style, controls_style = selection.cell_selection_graph(
        {"group": ComponentType.sym_voltage_sensor.value, "id": 101, "column": "u_measured"},
        2.0,
    )

    assert len(figure.data) == 0
    assert graph_style == {"display": "none"}
    assert controls_style == {"display": "none"}


def test_dense_node_output_without_explicit_ids_is_not_implemented(monkeypatch):
    """Dense node output with implicit IDs must report the unsupported feature."""
    nodes = np.zeros((3, 1), dtype=[("u", "f8")])
    monkeypatch.setattr(selection, "get_output_data", lambda: {ComponentType.node: nodes})
    monkeypatch.setattr(selection, "get_update_data", lambda: None)

    with pytest.raises(NotImplementedError, match="explicit component IDs"):
        selection._voltage_comparison_graph(101, 2.0)


def test_dense_sensor_updates_without_explicit_ids_are_not_implemented(monkeypatch, output_data):
    """Dense sensor updates with implicit IDs must report the unsupported feature."""
    updates = np.zeros((3, 1), dtype=[("u_measured", "f8")])
    monkeypatch.setattr(selection, "get_output_data", lambda: output_data)
    monkeypatch.setattr(
        selection,
        "get_update_data",
        lambda: {ComponentType.sym_voltage_sensor: updates},
    )

    with pytest.raises(NotImplementedError, match="explicit component IDs"):
        selection._voltage_comparison_graph(101, 2.0)


def test_attribute_selector_falls_back_to_dense_output_after_unsupported_update(monkeypatch, output_data):
    """Unsupported update data must not prevent selection from valid dense output."""
    monkeypatch.setattr(
        selection,
        "get_update_data",
        lambda: {ComponentType.node: {"indptr": np.array([0, 1])}},
    )
    monkeypatch.setattr(selection, "get_output_data", lambda: output_data)

    scenarios, values = selection._get_y_data_for_cell_selection(ComponentType.node, 10, "u")

    assert_array_equal(scenarios, [0, 1, 2])
    assert_array_equal(values, [229.0, 231.0, 228.0])


def test_supported_dense_voltage_comparison_still_renders(monkeypatch, grid, output_data):
    """Compatibility checks must not block the supported dense comparison."""
    monkeypatch.setattr(selection, "get_grid", lambda: grid)
    monkeypatch.setattr(selection, "get_update_data", lambda: None)
    monkeypatch.setattr(selection, "get_output_data", lambda: output_data)

    result = selection._voltage_comparison_graph(101, 2.0)

    assert result is not None
    figure, graph_style, controls_style = result
    assert len(figure.data) == 4
    assert graph_style == {"display": "block"}
    assert controls_style == {"display": "block"}


# Tests retained from the integrated visualizer branch.


def test_aligns_matching_scenarios():
    result = align_voltage_series(
        sensor_id=12001,
        node_id=1001,
        measurement_scenarios=np.array([0, 2, 3]),
        measured=np.array([230.0, 231.0, 229.0]),
        sigma=np.array([1.0, 1.5, 1.0]),
        estimate_scenarios=np.array([3, 0, 1, 2]),
        estimated=np.array([228.5, 229.5, 230.0, 230.5]),
    )

    np.testing.assert_array_equal(result.scenarios, [0, 2, 3])
    np.testing.assert_allclose(result.measured, [230.0, 231.0, 229.0])
    np.testing.assert_allclose(result.estimated, [229.5, 230.5, 228.5])
    np.testing.assert_allclose(result.sigma, [1.0, 1.5, 1.0])
    assert result.sensor_id == 12001
    assert result.node_id == 1001


def test_rejects_no_common_scenarios():
    with pytest.raises(ValueError, match="No matching"):
        align_voltage_series(
            sensor_id=12001,
            node_id=1001,
            measurement_scenarios=np.array([0, 1]),
            measured=np.array([230.0, 231.0]),
            sigma=np.array([1.0, 1.0]),
            estimate_scenarios=np.array([2, 3]),
            estimated=np.array([230.0, 231.0]),
        )


def test_rejects_duplicate_scenarios():
    with pytest.raises(ValueError, match="Duplicate"):
        align_voltage_series(
            sensor_id=12001,
            node_id=1001,
            measurement_scenarios=np.array([0, 0]),
            measured=np.array([230.0, 231.0]),
            sigma=np.array([1.0, 1.0]),
            estimate_scenarios=np.array([0, 1]),
            estimated=np.array([230.0, 231.0]),
        )


def test_rejects_invalid_sigma():
    with pytest.raises(ValueError, match="Sigma values must be positive"):
        align_voltage_series(
            sensor_id=12001,
            node_id=1001,
            measurement_scenarios=np.array([0, 1]),
            measured=np.array([230.0, 231.0]),
            sigma=np.array([1.0, 0.0]),
            estimate_scenarios=np.array([0, 1]),
            estimated=np.array([230.0, 231.0]),
        )


def test_rejects_non_finite_values():
    with pytest.raises(ValueError, match="non-finite"):
        align_voltage_series(
            sensor_id=12001,
            node_id=1001,
            measurement_scenarios=np.array([0, 1]),
            measured=np.array([230.0, np.nan]),
            sigma=np.array([1.0, 1.0]),
            estimate_scenarios=np.array([0, 1]),
            estimated=np.array([230.0, 231.0]),
        )


def test_prepares_voltage_comparison_from_pgm_datasets():
    """Match a voltage sensor to its node and align batch scenarios."""
    grid = Grid.empty()

    nodes = grid.node.__class__.empty(1)
    nodes.id = np.array([1001], dtype=np.int32)
    grid.append(nodes)

    sensors = grid.sym_voltage_sensor.__class__.empty(1)
    sensors.id = np.array([12001], dtype=np.int32)
    sensors.measured_object = np.array([1001], dtype=np.int32)
    grid.append(sensors)

    sensor_updates = initialize_array(
        DatasetType.update,
        ComponentType.sym_voltage_sensor,
        (3, 1),
    )
    sensor_updates["id"][:, 0] = 12001
    sensor_updates["u_measured"][:, 0] = [230.0, 231.0, 229.0]
    sensor_updates["u_sigma"][:, 0] = [1.0, 1.5, 1.0]

    node_outputs = initialize_array(
        DatasetType.sym_output,
        ComponentType.node,
        (3, 1),
    )
    node_outputs["id"][:, 0] = 1001
    node_outputs["u"][:, 0] = [229.5, 230.5, 228.5]

    result = prepare_voltage_comparison(
        grid=grid,
        update_data={ComponentType.sym_voltage_sensor: sensor_updates},
        output_data={ComponentType.node: node_outputs},
        sensor_id=12001,
    )

    assert result.sensor_id == 12001
    assert result.node_id == 1001

    np.testing.assert_array_equal(result.scenarios, [0, 1, 2])
    np.testing.assert_allclose(result.measured, [230.0, 231.0, 229.0])
    np.testing.assert_allclose(result.estimated, [229.5, 230.5, 228.5])
    np.testing.assert_allclose(result.sigma, [1.0, 1.5, 1.0])


def test_calculates_default_three_sigma_bands():
    comparison = align_voltage_series(
        sensor_id=12001,
        node_id=1001,
        measurement_scenarios=np.array([0, 1]),
        measured=np.array([230.0, 231.0]),
        sigma=np.array([1.0, 2.0]),
        estimate_scenarios=np.array([0, 1]),
        estimated=np.array([229.5, 230.5]),
    )

    lower, upper = calculate_sigma_bands(comparison)

    np.testing.assert_allclose(lower, [227.0, 225.0])
    np.testing.assert_allclose(upper, [233.0, 237.0])


def test_calculates_bands_with_custom_multiplier():
    comparison = align_voltage_series(
        sensor_id=12001,
        node_id=1001,
        measurement_scenarios=np.array([0]),
        measured=np.array([230.0]),
        sigma=np.array([1.5]),
        estimate_scenarios=np.array([0]),
        estimated=np.array([229.0]),
    )

    lower, upper = calculate_sigma_bands(comparison, multiplier=2.0)

    np.testing.assert_allclose(lower, [227.0])
    np.testing.assert_allclose(upper, [233.0])


@pytest.mark.parametrize("multiplier", [-1.0, np.nan, np.inf])
def test_rejects_invalid_sigma_multiplier(multiplier):
    comparison = align_voltage_series(
        sensor_id=12001,
        node_id=1001,
        measurement_scenarios=np.array([0]),
        measured=np.array([230.0]),
        sigma=np.array([1.0]),
        estimate_scenarios=np.array([0]),
        estimated=np.array([229.5]),
    )

    with pytest.raises(ValueError, match="Sigma multiplier"):
        calculate_sigma_bands(comparison, multiplier=multiplier)


def test_preserves_available_estimates_without_status_metadata():
    comparison = align_voltage_series(
        sensor_id=12001,
        node_id=1001,
        measurement_scenarios=np.array([0, 1]),
        measured=np.array([230.0, 231.0]),
        sigma=np.array([1.0, 1.0]),
        estimate_scenarios=np.array([0, 1]),
        estimated=np.array([229.5, 230.5]),
    )

    np.testing.assert_array_equal(comparison.scenarios, [0, 1])
    np.testing.assert_allclose(comparison.estimated, [229.5, 230.5])


def test_generic_comparison_without_sigma_plots_two_series():
    comparison = MeasurementComparison(
        scenario_indices=np.array([0, 1]),
        measured=np.array([10.0, 11.0]),
        estimated=np.array([9.5, 10.5]),
    )
    figure = create_measurement_comparison_figure(comparison, title="Power comparison", quantity="power", unit="W")
    assert len(figure.data) == 2
    assert figure.data[0].name == "Measured power"
    assert figure.data[1].name == "Calculated power"
    assert figure.layout.yaxis.title.text == "Power (W)"


def test_generic_comparison_sigma_bounds_and_labels():
    comparison = MeasurementComparison(
        scenario_indices=np.array([0, 1]),
        measured=np.array([10.0, 11.0]),
        estimated=np.array([9.5, 10.5]),
        sigma=np.array([1.0, 2.0]),
    )
    lower, upper = get_measurement_sigma_bounds(comparison, 2.0)
    assert_array_equal(lower, [8.0, 7.0])
    assert_array_equal(upper, [12.0, 15.0])
    figure = create_measurement_comparison_figure(comparison, title="Power comparison", quantity="power", unit="W")
    assert len(figure.data) == 4
    assert figure.data[2].name == "Measured power"
    assert figure.data[3].name == "Calculated power"


def test_generic_sigma_bounds_require_uncertainty():
    comparison = MeasurementComparison(
        scenario_indices=np.array([0]),
        measured=np.array([10.0]),
        estimated=np.array([9.5]),
    )
    with pytest.raises(ValueError, match="Measurement sigma is required"):
        get_measurement_sigma_bounds(comparison, 2.0)


@pytest.fixture
def power_grid():
    """Minimal source-terminal symmetric power sensor with independent sigmas."""
    sensors = SimpleNamespace(
        id=np.array([201], dtype=np.int32),
        measured_object=np.array([20], dtype=np.int32),
        measured_terminal_type=np.array([2], dtype=np.int8),
        p_measured=np.array([10.0]),
        q_measured=np.array([5.0]),
        power_sigma=np.array([999.0]),
        p_sigma=np.array([2.0]),
        q_sigma=np.array([1.0]),
    )
    return SimpleNamespace(sym_power_sensor=sensors)


@pytest.fixture
def power_output():
    source = initialize_array("sym_output", "source", (3, 1))
    source["id"] = 20
    source["p"][:, 0] = [9.0, 11.0, 8.0]
    source["q"][:, 0] = [4.0, 6.0, 3.0]
    return {ComponentType.source: source}


@pytest.mark.parametrize(
    ("attribute", "expected_estimated", "expected_sigma"),
    [
        ("p_measured", [9.0, 11.0, 8.0], [2.0, 2.0, 2.0]),
        ("q_measured", [4.0, 6.0, 3.0], [1.0, 1.0, 1.0]),
    ],
)
def test_power_comparison_uses_separate_sigma_fields(
    power_grid, power_output, attribute, expected_estimated, expected_sigma
):
    result = get_symmetric_power_comparison(power_grid, None, power_output, 201, attribute)
    assert_array_equal(result.scenario_indices, [0, 1, 2])
    assert_array_equal(result.estimated, expected_estimated)
    assert_array_equal(result.sigma, expected_sigma)
    lower, upper = get_measurement_sigma_bounds(result, 2.0)
    assert_array_equal(lower, result.measured - 2 * np.array(expected_sigma))
    assert_array_equal(upper, result.measured + 2 * np.array(expected_sigma))


def test_power_updates_preserve_other_scenarios(power_grid, power_output):
    updates = initialize_array("update", "sym_power_sensor", (3, 1))
    updates["id"] = 201
    updates["p_measured"][1, 0] = 15.0
    updates["p_sigma"][2, 0] = 4.0
    updates["power_sigma"][:, 0] = [1000.0, 2000.0, 3000.0]
    result = get_symmetric_power_comparison(
        power_grid, {ComponentType.sym_power_sensor: updates}, power_output, 201, "p_measured"
    )
    assert_array_equal(result.measured, [10.0, 15.0, 10.0])
    assert_array_equal(result.sigma, [2.0, 2.0, 4.0])


def test_power_without_individual_sigma_has_two_traces(power_grid, power_output):
    power_grid.sym_power_sensor.p_sigma[:] = np.nan
    result = get_symmetric_power_comparison(power_grid, None, power_output, 201, "p_measured")
    assert result.sigma is None
    fig = create_measurement_comparison_figure(result, title="P", quantity="active power", unit="W")
    assert len(fig.data) == 2


def test_power_zero_sigma_is_provided(power_grid, power_output):
    power_grid.sym_power_sensor.p_sigma[:] = 0.0
    result = get_symmetric_power_comparison(power_grid, None, power_output, 201, "p_measured")
    assert_array_equal(result.sigma, [0.0, 0.0, 0.0])


def test_unsupported_power_terminal_is_explicit(power_grid, power_output):
    power_grid.sym_power_sensor.measured_terminal_type[:] = 0
    with pytest.raises(NotImplementedError, match="terminal type"):
        get_symmetric_power_comparison(power_grid, None, power_output, 201, "p_measured")


def test_power_selection_displays_four_traces(monkeypatch, power_grid, power_output):
    monkeypatch.setattr(selection, "get_grid", lambda: power_grid)
    monkeypatch.setattr(selection, "get_update_data", lambda: None)
    monkeypatch.setattr(selection, "get_output_data", lambda: power_output)
    figure, graph_style, controls_style = selection.cell_selection_graph(
        {"group": "sym_power_sensor", "id": 201, "column": "p_measured"}, 2.0
    )
    assert len(figure.data) == 4
    assert_array_equal(figure.data[0].y, [6.0, 6.0, 6.0])
    assert_array_equal(figure.data[1].y, [14.0, 14.0, 14.0])
    assert graph_style == {"display": "block"}
    assert controls_style == {"display": "block"}


def test_power_selection_without_sigma_hides_controls(monkeypatch, power_grid, power_output):
    power_grid.sym_power_sensor.q_sigma[:] = np.nan
    monkeypatch.setattr(selection, "get_grid", lambda: power_grid)
    monkeypatch.setattr(selection, "get_update_data", lambda: None)
    monkeypatch.setattr(selection, "get_output_data", lambda: power_output)
    figure, graph_style, controls_style = selection.cell_selection_graph(
        {"group": "sym_power_sensor", "id": 201, "column": "q_measured"}, 2.0
    )
    assert len(figure.data) == 2
    assert graph_style == {"display": "block"}
    assert controls_style == {"display": "none"}


# Additional regression cases from the incoming power-comparison branch.


def test_missing_sensor_update_row_preserves_base_and_alignment(grid, output_data):
    updates = initialize_array("update", "sym_voltage_sensor", (3, 1))
    updates["id"] = 101
    updates["id"][1, 0] = 999
    updates["u_measured"][2, 0] = 237.0
    comparison = get_symmetric_voltage_comparison(grid, {ComponentType.sym_voltage_sensor: updates}, output_data, 101)
    assert comparison is not None
    assert_array_equal(comparison.scenario_indices, [0, 1, 2])
    assert_array_equal(comparison.measured, [230.0, 230.0, 237.0])


def test_missing_power_result_preserves_scenario(power_grid, power_output):
    source = power_output[ComponentType.source].copy()
    source["id"][1, 0] = 999

    result = get_symmetric_power_comparison(
        power_grid,
        None,
        {ComponentType.source: source},
        201,
        "p_measured",
    )

    assert_array_equal(result.estimated, [9.0, np.nan, 8.0])


def test_duplicate_power_output_is_rejected(power_grid):
    source = initialize_array("sym_output", "source", (2, 2))
    source["id"][:, 0] = 20
    source["id"][:, 1] = 99
    source["id"][1, 1] = 20

    with pytest.raises(ValueError, match="Duplicate source ID"):
        get_symmetric_power_comparison(
            power_grid,
            None,
            {ComponentType.source: source},
            201,
            "p_measured",
        )


def test_unknown_power_sensor_is_rejected(power_grid, power_output):
    with pytest.raises(ValueError, match="Expected exactly one power sensor"):
        get_symmetric_power_comparison(power_grid, None, power_output, 999, "p_measured")


def test_invalid_power_measurement_is_rejected(power_grid, power_output):
    with pytest.raises(ValueError, match="Unsupported power measurement"):
        get_symmetric_power_comparison(power_grid, None, power_output, 201, "power_sigma")
