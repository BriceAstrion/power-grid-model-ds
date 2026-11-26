# SPDX-FileCopyrightText: Contributors to the Power Grid Model project <powergridmodel@lfenergy.org>
#
# SPDX-License-Identifier: MPL-2.0

"""Timestamp mapping and component-state extraction for batch results."""

from collections.abc import Mapping, Sequence

import numpy as np
from power_grid_model import ComponentType
from power_grid_model.data_types import DenseBatchArray

from power_grid_model_ds._core.visualizer.scenario_selection import (
    _parse_timestamps,
    _validate_timestamp_count,
)

BatchData = Mapping[ComponentType, DenseBatchArray]

BATCH_DIMENSIONS = 2


def _get_scenario_count(datasets: tuple[BatchData | None, ...]) -> int:
    """Determine the common scenario count across supplied batch datasets."""
    scenario_counts = set()

    for dataset in datasets:
        if dataset is None:
            continue

        for array in dataset.values():
            if array.ndim != BATCH_DIMENSIONS:
                raise ValueError("Timestamp selection requires two-dimensional batch arrays")

            scenario_counts.add(array.shape[0])

    if not scenario_counts:
        raise ValueError("Timestamp selection requires batch data")

    if len(scenario_counts) != 1:
        raise ValueError("Batch datasets have inconsistent scenario counts")

    return scenario_counts.pop()


def validate_timestamps(
    timestamps: Sequence[str],
    *datasets: BatchData | None,
) -> tuple[str, ...]:
    """Validate timezone-aware timestamps against batch scenario counts."""
    values = _parse_timestamps(timestamps)
    scenario_count = _get_scenario_count(datasets)
    return _validate_timestamp_count(values, scenario_count)


def get_component_state(
    dataset: BatchData,
    component_type: ComponentType,
    component_id: int,
    scenario_index: int,
) -> dict[str, object] | None:
    """Return a component's available fields in one batch scenario.

    Component IDs are matched within the selected scenario because component
    ordering may differ between scenarios. Missing components return None.
    """
    if component_type not in dataset:
        return None

    array = dataset[component_type]

    if array.ndim != BATCH_DIMENSIONS:
        raise ValueError("Component-state inspection requires batch data")

    if (
        not isinstance(scenario_index, (int, np.integer))
        or isinstance(scenario_index, (bool, np.bool_))
        or scenario_index < 0
        or scenario_index >= array.shape[0]
    ):
        raise IndexError("Scenario index is outside the available batch range")

    scenario = array[scenario_index]
    matches = np.flatnonzero(scenario["id"] == component_id)

    if matches.size == 0:
        return None

    if matches.size > 1:
        raise ValueError(f"Duplicate component ID {component_id} in scenario {scenario_index}")

    record = scenario[int(matches[0])]

    return {field: record[field].tolist() for field in record.dtype.names or ()}
