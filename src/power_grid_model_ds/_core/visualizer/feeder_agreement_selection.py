# SPDX-FileCopyrightText: Contributors to the Power Grid Model project <powergridmodel@lfenergy.org>
#
# SPDX-License-Identifier: MPL-2.0

"""Sorting and pagination for measurement agreement details."""

from dataclasses import dataclass
from enum import StrEnum

from power_grid_model_ds._core.visualizer.feeder_agreement import (
    AgreementGroup,
    AgreementRecord,
)

DEFAULT_PAGE_SIZE = 5
MAX_VISIBLE_PAGE_NUMBERS = 5
INTERIOR_PAGE_NUMBERS = MAX_VISIBLE_PAGE_NUMBERS - 2


class MeasurementSort(StrEnum):
    """Supported measurement sorting modes."""

    LARGEST = "largest"
    SMALLEST = "smallest"
    SENSOR = "sensor"


@dataclass(frozen=True)
class MeasurementPage:
    """One page of sorted measurement records."""

    records: tuple[AgreementRecord, ...]
    page_index: int
    page_count: int
    total_count: int
    page_size: int

    @property
    def first_position(self) -> int:
        """Return the first displayed record position."""
        if not self.records:
            return 0
        return self.page_index * self.page_size + 1

    @property
    def last_position(self) -> int:
        """Return the last displayed record position."""
        return self.page_index * self.page_size + len(self.records)


def sort_measurements(
    group: AgreementGroup,
    sort_mode: MeasurementSort,
) -> tuple[AgreementRecord, ...]:
    """Sort records without modifying the original group."""
    mode = MeasurementSort(sort_mode)

    if mode is MeasurementSort.SENSOR:
        return tuple(sorted(group.records, key=lambda record: record.sensor_id))

    def difference_key(
        record: AgreementRecord,
    ) -> tuple[bool, float, int]:
        difference = record.absolute_discrepancy

        if difference is None:
            return True, 0.0, record.sensor_id

        value = -difference if mode is MeasurementSort.LARGEST else difference

        return False, value, record.sensor_id

    return tuple(sorted(group.records, key=difference_key))


def paginate_measurements(
    group: AgreementGroup,
    *,
    sort_mode: MeasurementSort = MeasurementSort.LARGEST,
    page_index: int = 0,
    page_size: int = DEFAULT_PAGE_SIZE,
) -> MeasurementPage:
    """Return a bounded page from the complete sorted group."""
    if isinstance(page_size, bool) or not isinstance(page_size, int) or page_size <= 0:
        raise ValueError("Page size must be a positive integer.")

    if isinstance(page_index, bool) or not isinstance(page_index, int):
        raise ValueError("Page index must be an integer.")

    records = sort_measurements(group, sort_mode)
    total_count = len(records)

    page_count = (total_count + page_size - 1) // page_size

    bounded_index = min(
        max(page_index, 0),
        max(page_count - 1, 0),
    )

    start = bounded_index * page_size

    return MeasurementPage(
        records=records[start : start + page_size],
        page_index=bounded_index,
        page_count=page_count,
        total_count=total_count,
        page_size=page_size,
    )


def build_page_window(page_index: int, page_count: int) -> tuple[int | None, ...]:
    """Return visible zero-based page indices, with None marking omitted pages.

    Empty and single-page results need no navigation. Out-of-range indices
    are bounded consistently with paginate_measurements.
    """
    if isinstance(page_count, bool) or not isinstance(page_count, int) or page_count < 0:
        raise ValueError("Page count must be a non-negative integer.")
    if isinstance(page_index, bool) or not isinstance(page_index, int):
        raise ValueError("Page index must be an integer.")
    if page_count <= 1:
        return ()
    if page_count <= MAX_VISIBLE_PAGE_NUMBERS:
        return tuple(range(page_count))

    last = page_count - 1
    current = min(max(page_index, 0), last)
    start = max(1, min(current - 1, last - INTERIOR_PAGE_NUMBERS))
    indices = (0, *range(start, start + INTERIOR_PAGE_NUMBERS), last)
    window: list[int | None] = []
    previous = -1
    for index in indices:
        if index - previous > 1:
            window.append(None)
        window.append(index)
        previous = index
    return tuple(window)
