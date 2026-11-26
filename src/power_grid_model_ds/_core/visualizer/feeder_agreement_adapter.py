# SPDX-FileCopyrightText: Contributors to the Power Grid Model project <powergridmodel@lfenergy.org>
#
# SPDX-License-Identifier: MPL-2.0

"""Read-only scenario-specific voltage measurement preparation for F13."""

from collections.abc import Iterable

import numpy as np
from power_grid_model import ComponentType
from power_grid_model.data_types import BatchDataset

from power_grid_model_ds._core.model.constants import EMPTY_ID
from power_grid_model_ds._core.model.grids.base import Grid
from power_grid_model_ds._core.visualizer.electrical_quantity_utils import (
    extract_scenario_values,
)
from power_grid_model_ds._core.visualizer.feeder_agreement import (
    AgreementOverview,
    AgreementRecord,
    MeasurementIdentity,
    build_agreement_overview,
    make_agreement_record,
)

DENSE_BATCH_NDIM = 2


def _build_node_lookup(
    grid: Grid,
) -> tuple[dict[int, int | None], set[int]]:
    """Index node feeder IDs and identify ambiguous node associations."""
    lookup: dict[int, int | None] = {}
    duplicate_ids: set[int] = set()

    for node_id, feeder_id in zip(
        grid.node.id,
        grid.node.feeder_branch_id,
        strict=True,
    ):
        node_key = int(node_id)
        feeder_key = int(feeder_id)

        if node_key in lookup:
            duplicate_ids.add(node_key)
            lookup[node_key] = None
        elif feeder_key == int(EMPTY_ID):
            lookup[node_key] = None
        else:
            lookup[node_key] = feeder_key

    return lookup, duplicate_ids


def _build_sensor_lookup(grid: Grid) -> dict[int, tuple[int, float]]:
    """Index voltage sensors by their ID."""
    sensors = grid.sym_voltage_sensor
    lookup: dict[int, tuple[int, float]] = {}

    for sensor_id, node_id, measured in zip(
        sensors.id,
        sensors.measured_object,
        sensors.u_measured,
        strict=True,
    ):
        key = int(sensor_id)

        if key in lookup:
            raise ValueError(f"Duplicate voltage sensor ID {key} in grid.")

        lookup[key] = (int(node_id), float(measured))

    return lookup


def _get_dense_component(
    dataset: BatchDataset,
    component: ComponentType,
) -> np.ndarray:
    """Validate the supported dense batch representation."""
    data = dataset[component]

    if not isinstance(data, np.ndarray) or data.ndim != DENSE_BATCH_NDIM:
        raise NotImplementedError("Voltage agreement requires dense batch arrays.")

    if data.dtype.names is None or "id" not in data.dtype.names:
        raise NotImplementedError("Voltage agreement requires explicit component IDs.")

    return data


def _get_voltage_estimates(
    output_data: BatchDataset,
    scenario_index: int,
) -> dict[int, float]:
    """Extract finite node voltage estimates for one scenario."""
    if ComponentType.node not in output_data:
        raise ValueError("Node output is required for voltage comparison")

    data = _get_dense_component(output_data, ComponentType.node)

    if "u" not in (data.dtype.names or ()):
        raise ValueError("Node output must contain a 'u' field")

    if scenario_index >= data.shape[0]:
        raise ValueError("Scenario index is outside the comparison range.")

    return extract_scenario_values(
        {ComponentType.node: data},
        ComponentType.node,
        "u",
        scenario_index,
    )


def _get_measurement_updates(
    update_data: BatchDataset | None,
    scenario_index: int,
    scenario_count: int,
    sensor_lookup: dict[int, tuple[int, float]],
) -> dict[int, float]:
    """Extract explicitly specified voltage updates for one scenario.

    NaN updates retain the original grid measurement.
    Non-finite specified values remain available for status handling.
    """
    component = ComponentType.sym_voltage_sensor

    if update_data is None or component not in update_data:
        return {}

    updates = _get_dense_component(update_data, component)

    if updates.shape[0] != scenario_count:
        raise ValueError("Sensor updates must match the output scenario count")

    if "u_measured" not in (updates.dtype.names or ()):
        return {}

    values: dict[int, float] = {}
    seen: set[int] = set()

    for row in updates[scenario_index]:
        sensor_id = int(row["id"])

        if sensor_id not in sensor_lookup:
            continue

        if sensor_id in seen:
            raise ValueError(f"Duplicate sensor ID {sensor_id} in updates")

        seen.add(sensor_id)
        measured = float(row["u_measured"])

        if not np.isnan(measured):
            values[sensor_id] = measured

    return values


def prepare_voltage_agreement_records(
    *,
    grid: Grid,
    update_data: BatchDataset | None,
    output_data: BatchDataset,
    scenario_index: int,
    sensor_ids: Iterable[int] | None = None,
) -> list[AgreementRecord]:
    """Prepare voltage agreement records for one selected scenario."""
    if isinstance(scenario_index, bool) or not isinstance(scenario_index, int) or scenario_index < 0:
        raise ValueError("Scenario index must be a non-negative integer.")

    estimates = _get_voltage_estimates(output_data, scenario_index)

    sensor_lookup = _build_sensor_lookup(grid)
    feeder_lookup, duplicate_node_ids = _build_node_lookup(grid)

    updates = _get_measurement_updates(
        update_data,
        scenario_index,
        _get_dense_component(output_data, ComponentType.node).shape[0],
        sensor_lookup,
    )

    if sensor_ids is None:
        sensor_ids = sensor_lookup

    records: list[AgreementRecord] = []

    for sensor_id in map(int, sensor_ids):
        if sensor_id not in sensor_lookup:
            raise ValueError(f"Expected exactly one voltage sensor with ID {sensor_id}")

        node_id, base_measurement = sensor_lookup[sensor_id]
        matched = node_id != int(EMPTY_ID) and node_id in feeder_lookup and node_id not in duplicate_node_ids

        records.append(
            make_agreement_record(
                MeasurementIdentity(
                    scenario_index=scenario_index,
                    sensor_id=sensor_id,
                    component_id=node_id,
                    quantity="voltage",
                    unit="V",
                ),
                measured=updates.get(sensor_id, base_measurement),
                estimated=estimates.get(node_id) if matched else None,
                feeder_id=feeder_lookup.get(node_id) if matched else None,
                matched=matched,
            )
        )

    return records


def prepare_voltage_agreement_overview(
    *,
    grid: Grid,
    update_data: BatchDataset | None,
    output_data: BatchDataset,
    scenario_index: int,
) -> AgreementOverview:
    """Prepare network and feeder groups for one scenario."""
    records = prepare_voltage_agreement_records(
        grid=grid,
        update_data=update_data,
        output_data=output_data,
        scenario_index=scenario_index,
    )

    return build_agreement_overview(records, scenario_index)
