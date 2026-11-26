# SPDX-FileCopyrightText: Contributors to the Power Grid Model project <powergridmodel@lfenergy.org>
#
# SPDX-License-Identifier: MPL-2.0

"""Tests for F13 measurement and feeder grouping."""

import math
import sys

import numpy as np
import pytest

from power_grid_model_ds._core.visualizer.feeder_agreement import (
    AgreementGroup,
    DiscrepancyStatistics,
    FeederStatus,
    MeasurementIdentity,
    MeasurementStatus,
    _finite_or_none,
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


def test_feeder_groups_have_deterministic_order():
    records = [
        _record(sensor_id=1, feeder_id=204),
        _record(sensor_id=2, feeder_id=201),
        _record(sensor_id=3, feeder_id=203),
    ]

    overview = build_agreement_overview(records, scenario_index=0)

    assert list(overview.feeders) == [201, 203, 204]


def test_grouping_preserves_record_order():
    records = [
        _record(sensor_id=3, feeder_id=201),
        _record(sensor_id=1, feeder_id=None),
        _record(sensor_id=2, feeder_id=201),
        _record(sensor_id=4, feeder_id=None),
    ]

    overview = build_agreement_overview(records, scenario_index=0)

    assert overview.network.records == tuple(records)
    assert overview.feeders[201].records == (records[0], records[2])
    assert overview.unassigned.records == (records[1], records[3])


def test_empty_agreement_overview():
    overview = build_agreement_overview([], scenario_index=0)

    assert overview.scenario_index == 0
    assert overview.network.total_count == 0
    assert overview.network.available_count == 0
    assert overview.network.unavailable_count == 0
    assert overview.feeders == {}
    assert overview.unassigned.total_count == 0


@pytest.mark.parametrize(
    ("measured", "estimated", "expected"),
    [
        (100.0, 97.0, 3.0),
        (97.0, 100.0, 3.0),
        (100.0, 100.0, 0.0),
        (None, 100.0, None),
        (100.0, None, None),
        (np.nan, 100.0, None),
        (100.0, np.inf, None),
    ],
)
def test_absolute_discrepancy(measured, estimated, expected):
    record = _record(
        sensor_id=1,
        feeder_id=201,
        measured=measured,
        estimated=estimated,
    )

    assert record.absolute_discrepancy == expected


def test_unmatched_pair_has_no_discrepancy():
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
        estimated=90.0,
        feeder_id=201,
        matched=False,
    )

    assert record.absolute_discrepancy is None


def test_network_discrepancy_statistics():
    records = [
        _record(
            sensor_id=1,
            feeder_id=201,
            measured=100.0,
            estimated=98.0,
        ),
        _record(
            sensor_id=2,
            feeder_id=201,
            measured=100.0,
            estimated=104.0,
        ),
        _record(
            sensor_id=3,
            feeder_id=None,
            measured=100.0,
            estimated=106.0,
        ),
    ]

    overview = build_agreement_overview(records, scenario_index=0)

    assert overview.network.mean_absolute_discrepancy == 4.0
    assert overview.network.max_absolute_discrepancy == 6.0
    assert overview.feeders[201].mean_absolute_discrepancy == 3.0
    assert overview.feeders[201].max_absolute_discrepancy == 4.0
    assert overview.unassigned.mean_absolute_discrepancy == 6.0
    assert overview.unassigned.max_absolute_discrepancy == 6.0
    assert overview.network.min_absolute_discrepancy == 2.0
    assert overview.feeders[201].min_absolute_discrepancy == 2.0
    assert overview.unassigned.min_absolute_discrepancy == 6.0


def test_unavailable_pairs_are_excluded_from_statistics():
    records = [
        _record(
            sensor_id=1,
            feeder_id=201,
            measured=100.0,
            estimated=96.0,
        ),
        _record(
            sensor_id=2,
            feeder_id=201,
            measured=None,
        ),
        _record(
            sensor_id=3,
            feeder_id=201,
            estimated=None,
        ),
        _record(
            sensor_id=4,
            feeder_id=201,
            measured=100.0,
            estimated=100.0,
        ),
    ]

    overview = build_agreement_overview(records, scenario_index=0)

    assert overview.network.total_count == 4
    assert overview.network.available_count == 2
    assert overview.network.unavailable_count == 2
    assert overview.network.mean_absolute_discrepancy == 2.0
    assert overview.network.max_absolute_discrepancy == 4.0
    assert overview.network.min_absolute_discrepancy == 0.0


def test_unmatched_records_are_excluded_from_statistics():
    identity = MeasurementIdentity(
        scenario_index=0,
        sensor_id=2,
        component_id=102,
        quantity="voltage",
        unit="V",
    )

    unmatched = make_agreement_record(
        identity,
        measured=100.0,
        estimated=50.0,
        feeder_id=201,
        matched=False,
    )

    records = [
        _record(
            sensor_id=1,
            feeder_id=201,
            measured=100.0,
            estimated=98.0,
        ),
        unmatched,
    ]

    overview = build_agreement_overview(records, scenario_index=0)

    assert overview.network.total_count == 2
    assert overview.network.available_count == 1
    assert overview.network.unavailable_count == 1
    assert overview.network.mean_absolute_discrepancy == 2.0
    assert overview.network.max_absolute_discrepancy == 2.0
    assert overview.network.min_absolute_discrepancy == 2.0


def test_empty_group_has_no_discrepancy_statistics():
    overview = build_agreement_overview([], scenario_index=0)

    assert overview.network.mean_absolute_discrepancy is None
    assert overview.network.max_absolute_discrepancy is None
    assert overview.unassigned.mean_absolute_discrepancy is None
    assert overview.unassigned.max_absolute_discrepancy is None
    assert overview.network.min_absolute_discrepancy is None
    assert overview.unassigned.min_absolute_discrepancy is None


def test_all_unavailable_group_has_no_discrepancy_statistics():
    records = [
        _record(
            sensor_id=1,
            feeder_id=201,
            measured=None,
        ),
        _record(
            sensor_id=2,
            feeder_id=201,
            estimated=None,
        ),
    ]

    overview = build_agreement_overview(records, scenario_index=0)

    assert overview.network.available_count == 0
    assert overview.network.mean_absolute_discrepancy is None
    assert overview.network.max_absolute_discrepancy is None
    assert overview.network.min_absolute_discrepancy is None


def test_zero_discrepancy_is_not_unavailable():
    records = [
        _record(
            sensor_id=1,
            feeder_id=201,
            measured=100.0,
            estimated=100.0,
        ),
    ]

    overview = build_agreement_overview(records, scenario_index=0)

    assert overview.network.mean_absolute_discrepancy == 0.0
    assert overview.network.max_absolute_discrepancy == 0.0
    assert overview.network.min_absolute_discrepancy == 0.0


@pytest.mark.parametrize(
    ("quantity", "unit"),
    [
        ("voltage", "kV"),
        ("power", "W"),
    ],
)
def test_incompatible_quantities_or_units_are_not_aggregated(
    quantity,
    unit,
):
    identity = MeasurementIdentity(
        scenario_index=0,
        sensor_id=2,
        component_id=102,
        quantity=quantity,
        unit=unit,
    )

    other = make_agreement_record(
        identity,
        measured=100.0,
        estimated=90.0,
        feeder_id=201,
    )

    records = [
        _record(sensor_id=1, feeder_id=201),
        other,
    ]

    overview = build_agreement_overview(records, scenario_index=0)

    assert overview.network.available_count == 2
    assert overview.network.mean_absolute_discrepancy is None
    assert overview.network.max_absolute_discrepancy is None
    assert overview.network.min_absolute_discrepancy is None


def test_discrepancy_statistics_do_not_mix_scenarios():
    records = [
        _record(
            sensor_id=1,
            feeder_id=201,
            scenario_index=0,
            measured=100.0,
            estimated=99.0,
        ),
        _record(
            sensor_id=1,
            feeder_id=201,
            scenario_index=1,
            measured=100.0,
            estimated=80.0,
        ),
    ]

    first = build_agreement_overview(records, scenario_index=0)
    second = build_agreement_overview(records, scenario_index=1)

    assert first.network.mean_absolute_discrepancy == 1.0
    assert first.network.max_absolute_discrepancy == 1.0
    assert second.network.mean_absolute_discrepancy == 20.0
    assert second.network.max_absolute_discrepancy == 20.0
    assert first.network.min_absolute_discrepancy == 1.0
    assert second.network.min_absolute_discrepancy == 20.0


@pytest.mark.parametrize(
    ("pairs", "expected"),
    [
        (
            [(100.0, 98.0), (100.0, 104.0), (100.0, 106.0)],
            DiscrepancyStatistics(2.0, 4.0, 6.0),
        ),
        (
            [(100.0, 100.0)],
            DiscrepancyStatistics(0.0, 0.0, 0.0),
        ),
        (
            [(100.0, 100.0), (100.0, 104.0), (None, 100.0)],
            DiscrepancyStatistics(0.0, 2.0, 4.0),
        ),
        (
            [(100.0, 97.0)],
            DiscrepancyStatistics(3.0, 3.0, 3.0),
        ),
        (
            [],
            DiscrepancyStatistics(None, None, None),
        ),
        (
            [(None, 100.0), (100.0, None)],
            DiscrepancyStatistics(None, None, None),
        ),
        (
            [(np.nan, 100.0), (100.0, np.inf)],
            DiscrepancyStatistics(None, None, None),
        ),
        (
            [(-1e308, 1e308)],
            DiscrepancyStatistics(None, None, None),
        ),
    ],
)
def test_combined_discrepancy_statistics(pairs, expected):
    records = tuple(
        _record(
            sensor_id=index,
            feeder_id=201,
            measured=measured,
            estimated=estimated,
        )
        for index, (measured, estimated) in enumerate(pairs)
    )

    group = AgreementGroup(records)

    statistics = group.discrepancy_statistics()

    assert statistics == expected
    assert statistics.minimum == group.min_absolute_discrepancy
    assert statistics.mean == group.mean_absolute_discrepancy
    assert statistics.maximum == group.max_absolute_discrepancy


@pytest.mark.parametrize(
    ("quantity", "unit"),
    [
        ("voltage", "kV"),
        ("power", "W"),
    ],
)
def test_combined_statistics_reject_incompatible_values(quantity, unit):
    identity = MeasurementIdentity(
        scenario_index=0,
        sensor_id=2,
        component_id=102,
        quantity=quantity,
        unit=unit,
    )

    other = make_agreement_record(
        identity,
        measured=100.0,
        estimated=90.0,
        feeder_id=201,
    )

    group = AgreementGroup(
        (
            _record(sensor_id=1, feeder_id=201),
            other,
        )
    )

    assert group.discrepancy_statistics() == DiscrepancyStatistics(None, None, None)


def test_combined_statistics_exclude_unmatched_records():
    identity = MeasurementIdentity(
        scenario_index=0,
        sensor_id=2,
        component_id=102,
        quantity="voltage",
        unit="V",
    )

    unmatched = make_agreement_record(
        identity,
        measured=100.0,
        estimated=50.0,
        feeder_id=201,
        matched=False,
    )

    group = AgreementGroup(
        (
            _record(
                sensor_id=1,
                feeder_id=201,
                measured=100.0,
                estimated=98.0,
            ),
            unmatched,
        )
    )

    assert group.discrepancy_statistics() == DiscrepancyStatistics(2.0, 2.0, 2.0)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, None),
        (0.0, 0.0),
        (-0.0, -0.0),
        (10500.0, 10500.0),
        (-10500.0, -10500.0),
        (10500, 10500.0),
        (float("nan"), None),
        (float("inf"), None),
        (float("-inf"), None),
        (sys.float_info.max, sys.float_info.max),
        (sys.float_info.min, sys.float_info.min),
        (math.ulp(0.0), math.ulp(0.0)),
        (np.float32(10500.25), 10500.25),
        (np.float64(10500.25), 10500.25),
        (np.int32(10500), 10500.0),
        (np.float64(np.nan), None),
        (np.float64(np.inf), None),
        (abs(1e308 - (-1e308)), None),
    ],
)
def test_scalar_finite_validation(value, expected):
    result = _finite_or_none(value)

    assert result == expected

    if expected is not None:
        assert type(result) is float
        assert math.copysign(1.0, result) == math.copysign(1.0, expected)
