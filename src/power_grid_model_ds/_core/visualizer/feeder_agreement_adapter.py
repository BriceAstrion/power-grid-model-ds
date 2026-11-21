# SPDX-FileCopyrightText: Contributors to the Power Grid Model project <powergridmodel@lfenergy.org>
#
# SPDX-License-Identifier: MPL-2.0

"""Read-only voltage measurement preparation for F13."""

from collections.abc import Iterable

import numpy as np
from power_grid_model.data_types import BatchDataset

from power_grid_model_ds._core.model.constants import EMPTY_ID
from power_grid_model_ds._core.model.grids.base import Grid
from power_grid_model_ds._core.visualizer.feeder_agreement import (
    AgreementRecord,
    MeasurementIdentity,
    build_agreement_overview,
    make_agreement_record,
)
from power_grid_model_ds._core.visualizer.measurement_comparison import (
    get_symmetric_voltage_comparison,
)


def _resolve_feeder_id(grid: Grid, node_id: int) -> int | None:
    """Read the feeder identifier without modifying the grid."""
    nodes = grid.node
    matches = np.flatnonzero(nodes.id == node_id)

    if matches.size != 1:
        return None

    feeder_id = int(nodes.feeder_branch_id[int(matches[0])])

    if feeder_id == int(EMPTY_ID):
        return None

    return feeder_id


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

    if sensor_ids is None:
        sensor_ids = (int(sensor_id) for sensor_id in grid.sym_voltage_sensor.id)

    records: list[AgreementRecord] = []

    for sensor_id in sensor_ids:
        comparison = get_symmetric_voltage_comparison(
            grid,
            update_data,
            output_data,
            int(sensor_id),
        )

        if scenario_index >= len(comparison.scenario_indices):
            raise ValueError("Scenario index is outside the comparison range.")

        node_id = comparison.node_id
        feeder_id = _resolve_feeder_id(grid, node_id)

        identity = MeasurementIdentity(
            scenario_index=scenario_index,
            sensor_id=int(sensor_id),
            component_id=node_id,
            quantity="voltage",
            unit="V",
        )

        record = make_agreement_record(
            identity,
            measured=float(comparison.measured[scenario_index]),
            estimated=float(comparison.estimated[scenario_index]),
            feeder_id=feeder_id,
        )

        records.append(record)

    return records


def prepare_voltage_agreement_overview(
    *,
    grid: Grid,
    update_data: BatchDataset | None,
    output_data: BatchDataset,
    scenario_index: int,
):
    """Prepare network and feeder groups for one scenario."""
    records = prepare_voltage_agreement_records(
        grid=grid,
        update_data=update_data,
        output_data=output_data,
        scenario_index=scenario_index,
    )

    return build_agreement_overview(records, scenario_index)
