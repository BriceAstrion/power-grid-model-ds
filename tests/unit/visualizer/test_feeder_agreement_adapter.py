# SPDX-FileCopyrightText: Contributors to the Power Grid Model project <powergridmodel@lfenergy.org>
#
# SPDX-License-Identifier: MPL-2.0

"""Tests for scenario-specific F13 voltage agreement preparation."""

from types import SimpleNamespace

import numpy as np
import pytest
from power_grid_model import ComponentType

from power_grid_model_ds._core.model.constants import EMPTY_ID
from power_grid_model_ds._core.visualizer import feeder_agreement_adapter as adapter
from power_grid_model_ds._core.visualizer.feeder_agreement import (
    FeederStatus,
    MeasurementStatus,
)


def _grid():
    """Create a controlled grid-like object."""
    nodes = np.rec.array(
        [(101, 201), (102, 204)],
        dtype=[
            ("id", np.int32),
            ("feeder_branch_id", np.int32),
        ],
    )

    sensors = np.rec.array(
        [(11, 101, 100.0), (12, 102, 110.0)],
        dtype=[
            ("id", np.int32),
            ("measured_object", np.int32),
            ("u_measured", np.float64),
        ],
    )

    return SimpleNamespace(
        node=nodes,
        sym_voltage_sensor=sensors,
    )


def _outputs():
    """Create two scenarios of node voltage estimates."""
    data = np.array(
        [
            [(101, 99.0), (102, 109.0)],
            [(101, 102.0), (102, 112.0)],
        ],
        dtype=[("id", np.int32), ("u", np.float64)],
    )

    return {ComponentType.node: data}


def _updates():
    """Create two scenarios of voltage sensor updates."""
    data = np.array(
        [
            [(11, np.nan), (12, np.nan)],
            [(11, 101.0), (12, 111.0)],
        ],
        dtype=[("id", np.int32), ("u_measured", np.float64)],
    )

    return {ComponentType.sym_voltage_sensor: data}


def _records(
    grid=None,
    update_data=None,
    output_data=None,
    scenario_index=0,
    sensor_ids=None,
):
    """Prepare records with controlled defaults."""
    return adapter.prepare_voltage_agreement_records(
        grid=_grid() if grid is None else grid,
        update_data=update_data,
        output_data=_outputs() if output_data is None else output_data,
        scenario_index=scenario_index,
        sensor_ids=sensor_ids,
    )


def test_extracts_selected_scenario_values():
    records = _records(
        update_data=_updates(),
        scenario_index=1,
        sensor_ids=[11],
    )

    assert len(records) == 1
    record = records[0]

    assert record.scenario_index == 1
    assert record.sensor_id == 11
    assert record.component_id == 101
    assert record.measured == 101.0
    assert record.estimated == 102.0
    assert record.quantity == "voltage"
    assert record.unit == "V"
    assert record.status is MeasurementStatus.AVAILABLE


def test_resolves_existing_feeder_id():
    record = _records(sensor_ids=[11])[0]

    assert record.feeder_id == 201
    assert record.feeder_status is FeederStatus.UNVERIFIED


def test_empty_feeder_id_is_unassigned():
    grid = _grid()
    grid.node.feeder_branch_id[0] = int(EMPTY_ID)

    record = _records(grid=grid, sensor_ids=[11])[0]

    assert record.feeder_id is None
    assert record.feeder_status is FeederStatus.UNASSIGNED
    assert record.status is MeasurementStatus.AVAILABLE


@pytest.mark.parametrize(
    ("measured", "estimated", "expected"),
    [
        (np.nan, 99.0, MeasurementStatus.MISSING_MEASUREMENT),
        (100.0, np.nan, MeasurementStatus.MISSING_ESTIMATE),
        (100.0, np.inf, MeasurementStatus.MISSING_ESTIMATE),
    ],
)
def test_missing_values_remain_explicit(measured, estimated, expected):
    grid = _grid()
    outputs = _outputs()

    grid.sym_voltage_sensor.u_measured[0] = measured
    outputs[ComponentType.node]["u"][0, 0] = estimated

    record = _records(
        grid=grid,
        output_data=outputs,
        sensor_ids=[11],
    )[0]

    assert record.status is expected


def test_adapter_does_not_mutate_grid():
    grid = _grid()
    original_nodes = grid.node.copy()
    original_sensors = grid.sym_voltage_sensor.copy()

    _records(grid=grid, update_data=_updates())

    np.testing.assert_array_equal(grid.node, original_nodes)
    np.testing.assert_array_equal(
        grid.sym_voltage_sensor,
        original_sensors,
    )


def test_overview_groups_network_and_feeders():
    overview = adapter.prepare_voltage_agreement_overview(
        grid=_grid(),
        update_data=None,
        output_data=_outputs(),
        scenario_index=0,
    )

    assert overview.scenario_index == 0
    assert overview.network.total_count == 2
    assert overview.network.available_count == 2
    assert set(overview.feeders) == {201, 204}
    assert overview.feeders[201].records[0].sensor_id == 11
    assert overview.feeders[204].records[0].sensor_id == 12
    assert overview.unassigned.total_count == 0


def test_missing_node_is_unmatched():
    grid = _grid()
    grid.sym_voltage_sensor.measured_object[0] = 999

    record = _records(grid=grid, sensor_ids=[11])[0]

    assert record.feeder_id is None
    assert record.feeder_status is FeederStatus.UNASSIGNED
    assert record.status is MeasurementStatus.UNMATCHED
    assert record.measured == 100.0
    assert record.estimated is None
    assert record.absolute_discrepancy is None


def test_out_of_range_scenario_is_rejected():
    with pytest.raises(ValueError, match="outside the comparison range"):
        _records(scenario_index=5)


@pytest.mark.parametrize("scenario_index", [-1, True])
def test_invalid_scenario_is_rejected(scenario_index):
    with pytest.raises(ValueError, match="non-negative integer"):
        _records(scenario_index=scenario_index)


def test_duplicate_node_ids_are_unmatched():
    grid = _grid()
    grid.node.id[:] = 101

    record = _records(grid=grid, sensor_ids=[11])[0]

    assert record.feeder_id is None
    assert record.feeder_status is FeederStatus.UNASSIGNED
    assert record.status is MeasurementStatus.UNMATCHED
    assert record.measured == 100.0
    assert record.estimated is None
    assert record.absolute_discrepancy is None


def test_multiple_sensors_can_reference_same_node():
    grid = _grid()
    grid.sym_voltage_sensor.measured_object[:] = 101

    overview = adapter.prepare_voltage_agreement_overview(
        grid=grid,
        update_data=None,
        output_data=_outputs(),
        scenario_index=0,
    )

    assert overview.network.total_count == 2
    assert overview.feeders[201].total_count == 2
    assert [record.sensor_id for record in overview.feeders[201].records] == [11, 12]


def test_nan_update_retains_base_measurement():
    record = _records(
        update_data=_updates(),
        sensor_ids=[11],
    )[0]

    assert record.measured == 100.0


def test_static_measurement_without_updates():
    record = _records(
        scenario_index=1,
        sensor_ids=[11],
    )[0]

    assert record.measured == 100.0
    assert record.estimated == 102.0


def test_infinite_update_is_unavailable():
    updates = _updates()
    updates[ComponentType.sym_voltage_sensor]["u_measured"][0, 0] = np.inf

    record = _records(
        update_data=updates,
        sensor_ids=[11],
    )[0]

    assert record.measured is None
    assert record.status is MeasurementStatus.MISSING_MEASUREMENT


def test_absent_node_output_preserves_measurement_record():
    outputs = _outputs()
    outputs[ComponentType.node]["id"][0, 0] = 999

    record = _records(
        output_data=outputs,
        sensor_ids=[11],
    )[0]

    assert record.measured == 100.0
    assert record.estimated is None
    assert record.status is MeasurementStatus.MISSING_ESTIMATE


def test_output_values_are_matched_by_id():
    outputs = _outputs()
    outputs[ComponentType.node] = outputs[ComponentType.node][:, ::-1].copy()

    records = _records(output_data=outputs)

    assert records[0].estimated == 99.0
    assert records[1].estimated == 109.0


def test_updates_are_matched_by_sensor_id():
    updates = _updates()
    component = ComponentType.sym_voltage_sensor
    updates[component] = updates[component][:, ::-1].copy()

    records = _records(
        update_data=updates,
        scenario_index=1,
    )

    assert records[0].measured == 101.0
    assert records[1].measured == 111.0


def test_duplicate_output_ids_are_rejected():
    outputs = _outputs()
    outputs[ComponentType.node]["id"][0] = [101, 101]

    with pytest.raises(ValueError, match="Duplicate component ID"):
        _records(output_data=outputs)


def test_duplicate_sensor_update_ids_are_rejected():
    updates = _updates()
    updates[ComponentType.sym_voltage_sensor]["id"][0] = [11, 11]

    with pytest.raises(ValueError, match="Duplicate sensor ID"):
        _records(update_data=updates)


def test_duplicate_grid_sensor_ids_are_rejected():
    grid = _grid()
    grid.sym_voltage_sensor.id[:] = 11

    with pytest.raises(ValueError, match="Duplicate voltage sensor ID"):
        _records(grid=grid)


def test_inconsistent_scenario_counts_are_rejected():
    updates = _updates()
    component = ComponentType.sym_voltage_sensor
    updates[component] = updates[component][:1]

    with pytest.raises(ValueError, match="output scenario count"):
        _records(update_data=updates)


def test_unknown_requested_sensor_is_rejected():
    with pytest.raises(ValueError, match="voltage sensor with ID"):
        _records(sensor_ids=[999])


def test_requested_sensor_order_is_preserved():
    records = _records(sensor_ids=[12, 11])

    assert [record.sensor_id for record in records] == [12, 11]


def test_empty_sensor_selection():
    assert _records(sensor_ids=[]) == []


def test_missing_node_component_is_rejected():
    with pytest.raises(ValueError, match="Node output is required"):
        _records(output_data={})


def test_unsupported_batch_representation_is_rejected():
    outputs = _outputs()
    outputs[ComponentType.node] = outputs[ComponentType.node][0]

    with pytest.raises(NotImplementedError, match="dense batch arrays"):
        _records(output_data=outputs)


def test_missing_update_record_retains_base_measurement():
    updates = _updates()
    updates[ComponentType.sym_voltage_sensor]["id"][1, 0] = 999

    record = _records(
        update_data=updates,
        scenario_index=1,
        sensor_ids=[11],
    )[0]

    assert record.measured == 100.0


def test_output_id_does_not_establish_missing_grid_node():
    grid = _grid()
    outputs = _outputs()

    grid.sym_voltage_sensor.measured_object[0] = 999
    outputs[ComponentType.node]["id"][0, 0] = 999

    record = _records(
        grid=grid,
        output_data=outputs,
        sensor_ids=[11],
    )[0]

    assert record.component_id == 999
    assert record.measured == 100.0
    assert record.estimated is None
    assert record.status is MeasurementStatus.UNMATCHED
    assert record.absolute_discrepancy is None


def test_empty_measured_object_is_unmatched():
    grid = _grid()
    grid.sym_voltage_sensor.measured_object[0] = int(EMPTY_ID)

    record = _records(grid=grid, sensor_ids=[11])[0]

    assert record.status is MeasurementStatus.UNMATCHED
    assert record.estimated is None
    assert record.feeder_id is None
    assert record.absolute_discrepancy is None


def test_unmatched_status_takes_precedence_over_missing_measurement():
    grid = _grid()
    grid.sym_voltage_sensor.measured_object[0] = 999
    grid.sym_voltage_sensor.u_measured[0] = np.nan

    record = _records(grid=grid, sensor_ids=[11])[0]

    assert record.status is MeasurementStatus.UNMATCHED
    assert record.measured is None
    assert record.estimated is None


def test_missing_feeder_does_not_prevent_discrepancy_calculation():
    grid = _grid()
    grid.node.feeder_branch_id[0] = int(EMPTY_ID)

    record = _records(grid=grid, sensor_ids=[11])[0]

    assert record.status is MeasurementStatus.AVAILABLE
    assert record.feeder_status is FeederStatus.UNASSIGNED
    assert record.absolute_discrepancy == 1.0


def test_unmatched_record_remains_in_network_and_unassigned_groups():
    grid = _grid()
    grid.sym_voltage_sensor.measured_object[0] = 999

    overview = adapter.prepare_voltage_agreement_overview(
        grid=grid,
        update_data=None,
        output_data=_outputs(),
        scenario_index=0,
    )

    assert overview.network.total_count == 2
    assert overview.network.available_count == 1
    assert overview.network.unavailable_count == 1
    assert overview.network.mean_absolute_discrepancy == 1.0
    assert overview.network.max_absolute_discrepancy == 1.0

    assert set(overview.feeders) == {204}
    assert overview.unassigned.total_count == 1

    record = overview.unassigned.records[0]

    assert record.sensor_id == 11
    assert record.status is MeasurementStatus.UNMATCHED
    assert overview.unassigned.mean_absolute_discrepancy is None
    assert overview.unassigned.max_absolute_discrepancy is None


def test_duplicate_node_association_is_not_resolved_by_feeder_id():
    grid = _grid()
    grid.node.id[:] = 101
    grid.node.feeder_branch_id[:] = 201

    record = _records(grid=grid, sensor_ids=[11])[0]

    assert record.status is MeasurementStatus.UNMATCHED
    assert record.feeder_id is None
    assert record.estimated is None
