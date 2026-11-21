# SPDX-FileCopyrightText: Contributors to the Power Grid Model project <powergridmodel@lfenergy.org>
#
# SPDX-License-Identifier: MPL-2.0

"""Tests for F13 measurement and feeder grouping."""

import numpy as np
import pytest

from power_grid_model_ds._core.visualizer.feeder_agreement import (
    FeederStatus,
    MeasurementIdentity,
    MeasurementStatus,
    build_agreement_overview,
    make_agreement_record,
)


def _record(
    *,
    sensor_id: int,
    feeder_id: int | None,
    scenario_index: int = 0,
    measured: float | None = 100.0,
    estimated: float | None = 99.0,
):
    identity = MeasurementIdentity(
        scenario_index=scenario_index,
        sensor_id=sensor_id,
        component_id=sensor_id + 100,
        quantity="voltage",
        unit="V",
    )

    return make_agreement_record(
        identity,
        measured=measured,
        estimated=estimated,
        feeder_id=feeder_id,
    )


def test_network_and_feeder_grouping():
    records = [
        _record(sensor_id=1, feeder_id=201),
        _record(sensor_id=2, feeder_id=201),
        _record(sensor_id=3, feeder_id=204),
        _record(sensor_id=4, feeder_id=None),
    ]

    overview = build_agreement_overview(records, scenario_index=0)

    assert overview.network.total_count == 4
    assert overview.network.available_count == 4
    assert set(overview.feeders) == {201, 204}
    assert overview.feeders[201].total_count == 2
    assert overview.feeders[204].total_count == 1
    assert overview.unassigned.total_count == 1


def test_scenarios_are_not_mixed():
    records = [
        _record(sensor_id=1, feeder_id=201, scenario_index=0),
        _record(sensor_id=1, feeder_id=201, scenario_index=1),
    ]

    overview = build_agreement_overview(records, scenario_index=1)

    assert overview.network.total_count == 1
    assert overview.network.records[0].scenario_index == 1


@pytest.mark.parametrize(
    ("measured", "estimated", "expected"),
    [
        (None, 100.0, MeasurementStatus.MISSING_MEASUREMENT),
        (100.0, None, MeasurementStatus.MISSING_ESTIMATE),
        (np.nan, 100.0, MeasurementStatus.MISSING_MEASUREMENT),
        (100.0, np.inf, MeasurementStatus.MISSING_ESTIMATE),
    ],
)
def test_missing_values_are_explicit(measured, estimated, expected):
    record = _record(
        sensor_id=1,
        feeder_id=201,
        measured=measured,
        estimated=estimated,
    )

    assert record.status is expected


def test_missing_feeder_is_explicit():
    record = _record(sensor_id=1, feeder_id=None)

    assert record.status is MeasurementStatus.AVAILABLE
    assert record.feeder_status is FeederStatus.UNASSIGNED


def test_unmatched_record_is_explicit():
    identity = MeasurementIdentity(
        scenario_index=0,
        sensor_id=1,
        component_id=101,
        quantity="voltage",
        unit="V",
    )

    record = make_agreement_record(
        identity,
        measured=100.0,
        estimated=99.0,
        feeder_id=201,
        matched=False,
    )

    assert record.status is MeasurementStatus.UNMATCHED


@pytest.mark.parametrize("scenario_index", [-1, True])
def test_invalid_scenario_is_rejected(scenario_index):
    with pytest.raises(
        ValueError,
        match="Scenario index must be a non-negative integer",
    ):
        build_agreement_overview([], scenario_index)


def test_unverified_feeder_is_explicit():
    record = _record(sensor_id=1, feeder_id=201)

    assert record.feeder_status is FeederStatus.UNVERIFIED


def test_default_feeder_assignment_is_unverified():
    identity = MeasurementIdentity(
        scenario_index=0,
        sensor_id=1,
        component_id=101,
        quantity="voltage",
        unit="V",
    )

    record = make_agreement_record(
        identity,
        measured=100.0,
        estimated=99.0,
        feeder_id=201,
    )

    assert record.feeder_status is FeederStatus.UNVERIFIED
