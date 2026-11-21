# SPDX-FileCopyrightText: Contributors to the Power Grid Model project <powergridmodel@lfenergy.org>
#
# SPDX-License-Identifier: MPL-2.0

"""Tests for the F13 voltage agreement adapter."""

from types import SimpleNamespace
from unittest.mock import Mock

import numpy as np
import pytest

from power_grid_model_ds._core.model.constants import EMPTY_ID
from power_grid_model_ds._core.visualizer import feeder_agreement_adapter as adapter
from power_grid_model_ds._core.visualizer.feeder_agreement import (
    FeederStatus,
    MeasurementStatus,
)


def _grid(
    *,
    feeder_ids=(201, 204),
    sensor_ids=(11, 12),
):
    """Create a controlled grid-like object for adapter tests."""
    nodes = np.zeros(
        len(feeder_ids),
        dtype=[
            ("id", np.int32),
            ("feeder_branch_id", np.int32),
        ],
    )
    nodes["id"] = np.arange(101, 101 + len(feeder_ids))
    nodes["feeder_branch_id"] = feeder_ids

    sensors = np.zeros(
        len(sensor_ids),
        dtype=[("id", np.int32)],
    )
    sensors["id"] = sensor_ids

    return SimpleNamespace(
        node=np.rec.array(nodes),
        sym_voltage_sensor=np.rec.array(sensors),
    )


def _comparison(
    *,
    node_id=101,
    measured=(100.0, 101.0),
    estimated=(99.0, 102.0),
    scenario_indices=(0, 1),
):
    """Create a controlled voltage comparison."""
    return SimpleNamespace(
        node_id=node_id,
        measured=np.asarray(measured, dtype=float),
        estimated=np.asarray(estimated, dtype=float),
        scenario_indices=np.asarray(scenario_indices, dtype=int),
    )


def test_extracts_selected_scenario_values(monkeypatch):
    grid = _grid(sensor_ids=(11,))
    comparison = _comparison()

    mock = Mock(return_value=comparison)
    monkeypatch.setattr(adapter, "get_symmetric_voltage_comparison", mock)

    records = adapter.prepare_voltage_agreement_records(
        grid=grid,
        update_data=None,
        output_data={},
        scenario_index=1,
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

    mock.assert_called_once_with(grid, None, {}, 11)


def test_resolves_existing_feeder_id(monkeypatch):
    grid = _grid(sensor_ids=(11,))

    monkeypatch.setattr(
        adapter,
        "get_symmetric_voltage_comparison",
        Mock(return_value=_comparison()),
    )

    records = adapter.prepare_voltage_agreement_records(
        grid=grid,
        update_data=None,
        output_data={},
        scenario_index=0,
    )

    assert records[0].feeder_id == 201
    assert records[0].feeder_status is FeederStatus.UNVERIFIED


def test_empty_feeder_id_is_unassigned(monkeypatch):
    grid = _grid(
        feeder_ids=(int(EMPTY_ID),),
        sensor_ids=(11,),
    )

    monkeypatch.setattr(
        adapter,
        "get_symmetric_voltage_comparison",
        Mock(return_value=_comparison()),
    )

    records = adapter.prepare_voltage_agreement_records(
        grid=grid,
        update_data=None,
        output_data={},
        scenario_index=0,
    )

    record = records[0]

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
def test_missing_values_remain_explicit(
    monkeypatch,
    measured,
    estimated,
    expected,
):
    grid = _grid(sensor_ids=(11,))

    comparison = _comparison(
        measured=(measured,),
        estimated=(estimated,),
        scenario_indices=(0,),
    )

    monkeypatch.setattr(
        adapter,
        "get_symmetric_voltage_comparison",
        Mock(return_value=comparison),
    )

    records = adapter.prepare_voltage_agreement_records(
        grid=grid,
        update_data=None,
        output_data={},
        scenario_index=0,
    )

    assert records[0].status is expected


def test_adapter_does_not_mutate_grid(monkeypatch):
    grid = _grid(sensor_ids=(11,))
    original_nodes = grid.node.copy()
    original_sensors = grid.sym_voltage_sensor.copy()

    monkeypatch.setattr(
        adapter,
        "get_symmetric_voltage_comparison",
        Mock(return_value=_comparison()),
    )

    adapter.prepare_voltage_agreement_records(
        grid=grid,
        update_data=None,
        output_data={},
        scenario_index=0,
    )

    np.testing.assert_array_equal(grid.node, original_nodes)
    np.testing.assert_array_equal(
        grid.sym_voltage_sensor,
        original_sensors,
    )


def test_overview_groups_network_and_feeders(monkeypatch):
    grid = _grid()

    def comparison_for_sensor(_grid, _updates, _outputs, sensor_id):
        return _comparison(
            node_id=101 if sensor_id == 11 else 102,
        )

    monkeypatch.setattr(
        adapter,
        "get_symmetric_voltage_comparison",
        comparison_for_sensor,
    )

    overview = adapter.prepare_voltage_agreement_overview(
        grid=grid,
        update_data=None,
        output_data={},
        scenario_index=0,
    )

    assert overview.scenario_index == 0
    assert overview.network.total_count == 2
    assert overview.network.available_count == 2
    assert set(overview.feeders) == {201, 204}
    assert overview.feeders[201].records[0].sensor_id == 11
    assert overview.feeders[204].records[0].sensor_id == 12
    assert overview.unassigned.total_count == 0


def test_missing_node_does_not_create_feeder_assignment(monkeypatch):
    grid = _grid(sensor_ids=(11,))

    monkeypatch.setattr(
        adapter,
        "get_symmetric_voltage_comparison",
        Mock(return_value=_comparison(node_id=999)),
    )

    records = adapter.prepare_voltage_agreement_records(
        grid=grid,
        update_data=None,
        output_data={},
        scenario_index=0,
    )

    assert records[0].feeder_id is None
    assert records[0].feeder_status is FeederStatus.UNASSIGNED


def test_out_of_range_scenario_is_rejected(monkeypatch):
    grid = _grid(sensor_ids=(11,))

    monkeypatch.setattr(
        adapter,
        "get_symmetric_voltage_comparison",
        Mock(return_value=_comparison()),
    )

    with pytest.raises(ValueError, match="outside the comparison range"):
        adapter.prepare_voltage_agreement_records(
            grid=grid,
            update_data=None,
            output_data={},
            scenario_index=5,
        )


@pytest.mark.parametrize("scenario_index", [-1, True])
def test_invalid_scenario_is_rejected(scenario_index):
    with pytest.raises(ValueError, match="non-negative integer"):
        adapter.prepare_voltage_agreement_records(
            grid=_grid(),
            update_data=None,
            output_data={},
            scenario_index=scenario_index,
        )
