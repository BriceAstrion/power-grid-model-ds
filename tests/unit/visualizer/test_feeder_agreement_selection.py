# SPDX-FileCopyrightText: Contributors to the Power Grid Model project <powergridmodel@lfenergy.org>
#
# SPDX-License-Identifier: MPL-2.0

"""Tests for agreement measurement sorting and pagination."""

from itertools import pairwise

import pytest

from power_grid_model_ds._core.visualizer.feeder_agreement import (
    AgreementGroup,
    MeasurementIdentity,
    make_agreement_record,
)
from power_grid_model_ds._core.visualizer.feeder_agreement_selection import (
    MeasurementSort,
    build_page_window,
    paginate_measurements,
    sort_measurements,
)


def _record(sensor_id, difference):
    return make_agreement_record(
        MeasurementIdentity(0, sensor_id, sensor_id + 100, "voltage", "V"),
        measured=100.0,
        estimated=(None if difference is None else 100.0 + difference),
        feeder_id=201,
    )


def _group():
    return AgreementGroup(
        (
            _record(13, 2.0),
            _record(11, None),
            _record(15, 0.0),
            _record(12, 4.0),
            _record(14, 2.0),
            _record(16, None),
            _record(17, 1.0),
        )
    )


def _ids(records):
    return [record.sensor_id for record in records]


@pytest.mark.parametrize(
    ("mode", "expected"),
    [
        (
            MeasurementSort.LARGEST,
            [12, 13, 14, 17, 15, 11, 16],
        ),
        (
            MeasurementSort.SMALLEST,
            [15, 17, 13, 14, 12, 11, 16],
        ),
        (
            MeasurementSort.SENSOR,
            [11, 12, 13, 14, 15, 16, 17],
        ),
    ],
)
def test_sort_measurements(mode, expected):
    assert _ids(sort_measurements(_group(), mode)) == expected


def test_sorting_does_not_modify_original_group():
    group = _group()
    original = group.records

    sort_measurements(group, MeasurementSort.LARGEST)

    assert group.records == original
    assert _ids(group.records) == [13, 11, 15, 12, 14, 16, 17]


def test_first_page_contains_five_sorted_records():
    page = paginate_measurements(_group())

    assert _ids(page.records) == [12, 13, 14, 17, 15]
    assert page.page_index == 0
    assert page.page_count == 2
    assert page.total_count == 7
    assert page.first_position == 1
    assert page.last_position == 5


def test_last_page_retains_unavailable_measurements():
    page = paginate_measurements(_group(), page_index=1)

    assert _ids(page.records) == [11, 16]
    assert page.first_position == 6
    assert page.last_position == 7


def test_sorting_is_applied_before_pagination():
    page = paginate_measurements(
        _group(),
        sort_mode=MeasurementSort.SMALLEST,
        page_size=2,
    )

    assert _ids(page.records) == [15, 17]


def test_pagination_does_not_lose_or_duplicate_records():
    group = _group()

    first = paginate_measurements(group)
    second = paginate_measurements(group, page_index=1)

    combined = first.records + second.records

    assert len(combined) == group.total_count
    assert _ids(combined) == _ids(sort_measurements(group, MeasurementSort.LARGEST))


@pytest.mark.parametrize(
    ("requested", "expected"),
    [(-1, 0), (0, 0), (1, 1), (99, 1)],
)
def test_page_index_is_bounded(requested, expected):
    page = paginate_measurements(
        _group(),
        page_index=requested,
    )

    assert page.page_index == expected


def test_empty_group_returns_empty_page():
    page = paginate_measurements(AgreementGroup(()))

    assert page.records == ()
    assert page.page_count == 0
    assert page.page_index == 0
    assert page.total_count == 0
    assert page.first_position == 0
    assert page.last_position == 0


@pytest.mark.parametrize("page_size", [0, -1, True, 1.5])
def test_invalid_page_size_is_rejected(page_size):
    with pytest.raises(ValueError, match="positive integer"):
        paginate_measurements(_group(), page_size=page_size)


@pytest.mark.parametrize("page_index", [True, 1.5, None])
def test_invalid_page_index_is_rejected(page_index):
    with pytest.raises(ValueError, match="must be an integer"):
        paginate_measurements(_group(), page_index=page_index)


def test_invalid_sort_mode_is_rejected():
    with pytest.raises(ValueError, match="is not a valid MeasurementSort"):
        sort_measurements(_group(), "unknown")


@pytest.mark.parametrize(
    ("page_index", "page_count", "expected"),
    [
        (0, 0, ()),
        (0, 1, ()),
        (0, 2, (0, 1)),
        (1, 3, (0, 1, 2)),
        (2, 5, (0, 1, 2, 3, 4)),
        (0, 6, (0, 1, 2, 3, None, 5)),
        (0, 13, (0, 1, 2, 3, None, 12)),
        (6, 13, (0, None, 5, 6, 7, None, 12)),
        (12, 13, (0, None, 9, 10, 11, 12)),
        (-1, 13, (0, 1, 2, 3, None, 12)),
        (99, 13, (0, None, 9, 10, 11, 12)),
        (4999, 10000, (0, None, 4998, 4999, 5000, None, 9999)),
    ],
)
def test_build_page_window(page_index, page_count, expected):
    assert build_page_window(page_index, page_count) == expected


@pytest.mark.parametrize("page_count", [-1, True, 1.5, None])
def test_page_window_rejects_invalid_count(page_count):
    with pytest.raises(ValueError, match="non-negative integer"):
        build_page_window(0, page_count)


@pytest.mark.parametrize("page_index", [True, 1.5, None])
def test_page_window_rejects_invalid_index(page_index):
    with pytest.raises(ValueError, match="must be an integer"):
        build_page_window(page_index, 13)


@pytest.mark.parametrize("page_count", [2, 5, 6, 13, 10000])
def test_page_window_invariants(page_count):
    max_buttons = 5
    max_ellipses = 2
    for current in range(page_count):
        window = build_page_window(current, page_count)
        indices = [index for index in window if index is not None]
        assert indices == sorted(set(indices))
        assert indices[0] == 0
        assert indices[-1] == page_count - 1
        assert current in indices
        assert len(indices) <= max_buttons
        assert window.count(None) <= max_ellipses
        expected: list[int | None] = [indices[0]]
        for previous, following in pairwise(indices):
            if following - previous > 1:
                expected.append(None)
            expected.append(following)
        assert window == tuple(expected)
