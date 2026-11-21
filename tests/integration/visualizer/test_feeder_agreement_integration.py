# SPDX-FileCopyrightText: Contributors to the Power Grid Model project <powergridmodel@lfenergy.org>
#
# SPDX-License-Identifier: MPL-2.0

"""Integration tests for F13 with real PGM-DS grid and batch arrays."""

import numpy as np
import pytest
from power_grid_model import (
    AttributeType,
    ComponentType,
    DatasetType,
    initialize_array,
)

from power_grid_model_ds import Grid
from power_grid_model_ds._core.model.constants import EMPTY_ID
from power_grid_model_ds._core.visualizer.feeder_agreement import (
    FeederStatus,
    MeasurementStatus,
)
from power_grid_model_ds._core.visualizer.feeder_agreement_adapter import (
    prepare_voltage_agreement_overview,
    prepare_voltage_agreement_records,
)


@pytest.fixture
def agreement_data():
    """Build a real Grid with controlled two-scenario voltage data."""
    grid = Grid.empty()

    nodes = grid.node.__class__(
        id=[1, 2, 6],
        u_rated=[10500.0, 10500.0, 10500.0],
        feeder_branch_id=[201, 201, int(EMPTY_ID)],
    )
    grid.append(nodes, check_max_id=False)

    sensors = grid.sym_voltage_sensor.__class__.empty(3)
    sensors.id = np.array([11, 12, 13], dtype=np.int32)
    sensors.measured_object = np.array([1, 2, 6], dtype=np.int32)
    sensors.u_measured = np.array([10489.37, 9997.32, 10102.01], dtype=np.float64)
    sensors.u_sigma = np.array([1.0, 1.0, 1.0], dtype=np.float64)
    grid.append(sensors, check_max_id=False)

    sensor_updates = initialize_array(
        DatasetType.update,
        ComponentType.sym_voltage_sensor,
        (2, 3),
    )
    sensor_updates[AttributeType.id] = [11, 12, 13]
    sensor_updates[AttributeType.u_measured] = [
        [10489.37, 9997.32, 10102.01],
        [10490.0, 10010.0, 10120.0],
    ]

    node_outputs = initialize_array(
        DatasetType.sym_output,
        ComponentType.node,
        (2, 3),
    )
    node_outputs[AttributeType.id] = [1, 2, 6]
    node_outputs[AttributeType.u] = [
        [10488.0, 10000.0, 10100.0],
        [10491.0, 10008.0, 10119.0],
    ]
    node_outputs[AttributeType.energized] = 1

    return (
        grid,
        {ComponentType.sym_voltage_sensor: sensor_updates},
        {ComponentType.node: node_outputs},
    )


def test_real_grid_extracts_voltage_measurements(agreement_data):
    grid, update_data, output_data = agreement_data

    records = prepare_voltage_agreement_records(
        grid=grid,
        update_data=update_data,
        output_data=output_data,
        scenario_index=0,
    )

    assert len(records) == 3

    by_sensor = {record.sensor_id: record for record in records}

    assert set(by_sensor) == {11, 12, 13}

    assert by_sensor[11].component_id == 1
    assert by_sensor[12].component_id == 2
    assert by_sensor[13].component_id == 6

    assert by_sensor[11].measured == pytest.approx(10489.37)
    assert by_sensor[11].estimated == pytest.approx(10488.0)

    assert by_sensor[12].measured == pytest.approx(9997.32)
    assert by_sensor[12].estimated == pytest.approx(10000.0)

    assert by_sensor[13].measured == pytest.approx(10102.01)
    assert by_sensor[13].estimated == pytest.approx(10100.0)

    assert all(record.status is MeasurementStatus.AVAILABLE for record in records)


def test_real_grid_selects_scenario_independently(agreement_data):
    grid, update_data, output_data = agreement_data

    first = prepare_voltage_agreement_records(
        grid=grid,
        update_data=update_data,
        output_data=output_data,
        scenario_index=0,
    )

    second = prepare_voltage_agreement_records(
        grid=grid,
        update_data=update_data,
        output_data=output_data,
        scenario_index=1,
    )

    first_by_sensor = {record.sensor_id: record for record in first}
    second_by_sensor = {record.sensor_id: record for record in second}

    assert first_by_sensor[11].measured == pytest.approx(10489.37)
    assert second_by_sensor[11].measured == pytest.approx(10490.0)

    assert first_by_sensor[11].estimated == pytest.approx(10488.0)
    assert second_by_sensor[11].estimated == pytest.approx(10491.0)

    assert all(record.scenario_index == 0 for record in first)
    assert all(record.scenario_index == 1 for record in second)


def test_real_grid_groups_feeders_and_unassigned(agreement_data):
    grid, update_data, output_data = agreement_data

    overview = prepare_voltage_agreement_overview(
        grid=grid,
        update_data=update_data,
        output_data=output_data,
        scenario_index=0,
    )

    assert overview.network.total_count == 3
    assert overview.network.available_count == 3

    assert set(overview.feeders) == {201}
    assert overview.feeders[201].total_count == 2
    assert {record.sensor_id for record in overview.feeders[201].records} == {11, 12}

    assert overview.unassigned.total_count == 1
    assert overview.unassigned.records[0].sensor_id == 13

    for record in overview.feeders[201].records:
        assert record.feeder_status is FeederStatus.UNVERIFIED

    assert overview.unassigned.records[0].feeder_status is FeederStatus.UNASSIGNED


def test_real_grid_missing_estimate_is_explicit(agreement_data):
    grid, update_data, output_data = agreement_data

    node_outputs = output_data[ComponentType.node]
    node_outputs[AttributeType.u][1, 2] = np.nan

    records = prepare_voltage_agreement_records(
        grid=grid,
        update_data=update_data,
        output_data=output_data,
        scenario_index=1,
    )

    by_sensor = {record.sensor_id: record for record in records}

    assert by_sensor[13].status is MeasurementStatus.MISSING_ESTIMATE
    assert by_sensor[13].estimated is None
    assert by_sensor[13].measured == pytest.approx(10120.0)

    assert by_sensor[11].status is MeasurementStatus.AVAILABLE
    assert by_sensor[12].status is MeasurementStatus.AVAILABLE


def test_real_grid_adapter_does_not_modify_grid(agreement_data):
    grid, update_data, output_data = agreement_data

    original_node_ids = grid.node.id.copy()
    original_feeder_ids = grid.node.feeder_branch_id.copy()
    original_sensor_ids = grid.sym_voltage_sensor.id.copy()
    original_measurements = grid.sym_voltage_sensor.u_measured.copy()

    prepare_voltage_agreement_overview(
        grid=grid,
        update_data=update_data,
        output_data=output_data,
        scenario_index=1,
    )

    np.testing.assert_array_equal(grid.node.id, original_node_ids)
    np.testing.assert_array_equal(
        grid.node.feeder_branch_id,
        original_feeder_ids,
    )
    np.testing.assert_array_equal(
        grid.sym_voltage_sensor.id,
        original_sensor_ids,
    )
    np.testing.assert_array_equal(
        grid.sym_voltage_sensor.u_measured,
        original_measurements,
    )


def test_real_grid_rejects_out_of_range_scenario(agreement_data):
    grid, update_data, output_data = agreement_data

    with pytest.raises(ValueError, match="outside the comparison range"):
        prepare_voltage_agreement_records(
            grid=grid,
            update_data=update_data,
            output_data=output_data,
            scenario_index=2,
        )
