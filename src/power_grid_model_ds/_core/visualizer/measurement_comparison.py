# SPDX-FileCopyrightText: Contributors to the Power Grid Model project <powergridmodel@lfenergy.org>
#
# SPDX-License-Identifier: MPL-2.0

"""Data preparation for measured-versus-estimated comparisons."""

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray
from power_grid_model import ComponentType
from power_grid_model.data_types import BatchDataset

from power_grid_model_ds._core.model.grids.base import Grid
from power_grid_model_ds._core.visualizer.grid_utils import get_attr_data_from_dataset


@dataclass(frozen=True)
class VoltageComparison:
    """Aligned symmetric voltage values for a sensor and its measured node."""

    sensor_id: int
    node_id: int
    scenarios: NDArray[np.int64]
    measured: NDArray[np.float64]
    estimated: NDArray[np.float64]
    sigma: NDArray[np.float64]


def align_voltage_series(
    *,
    sensor_id: int,
    node_id: int,
    measurement_scenarios: NDArray,
    measured: NDArray,
    sigma: NDArray,
    estimate_scenarios: NDArray,
    estimated: NDArray,
) -> VoltageComparison:
    """Align voltage measurements and estimates by scenario index.

    The caller must supply the verified sensor-to-node mapping.
    Scenario indices are not assumed to be timestamps.
    """
    measurement_scenarios = np.asarray(measurement_scenarios)
    estimate_scenarios = np.asarray(estimate_scenarios)
    measured = np.asarray(measured, dtype=np.float64)
    sigma = np.asarray(sigma, dtype=np.float64)
    estimated = np.asarray(estimated, dtype=np.float64)

    arrays = (
        measurement_scenarios,
        measured,
        sigma,
        estimate_scenarios,
        estimated,
    )
    if any(array.ndim != 1 for array in arrays):
        raise ValueError("Symmetric voltage comparison requires 1D arrays.")

    if not (
        len(measurement_scenarios) == len(measured) == len(sigma)
        and len(estimate_scenarios) == len(estimated)
    ):
        raise ValueError("Scenario and value array lengths do not match.")

    for scenarios in (measurement_scenarios, estimate_scenarios):
        if not np.issubdtype(scenarios.dtype, np.integer):
            raise ValueError("Scenario indices must be integers.")
        if len(np.unique(scenarios)) != len(scenarios):
            raise ValueError("Duplicate scenario indices are not supported.")

    if not (
        np.all(np.isfinite(measured))
        and np.all(np.isfinite(estimated))
        and np.all(np.isfinite(sigma))
    ):
        raise ValueError("Comparison contains non-finite values.")

    if np.any(sigma <= 0):
        raise ValueError("Sigma values must be positive.")

    common_scenarios, measurement_indices, estimate_indices = (
        np.intersect1d(
            measurement_scenarios,
            estimate_scenarios,
            return_indices=True,
        )
    )

    if common_scenarios.size == 0:
        raise ValueError("No matching measurement and estimate scenarios.")

    return VoltageComparison(
        sensor_id=sensor_id,
        node_id=node_id,
        scenarios=common_scenarios,
        measured=measured[measurement_indices],
        estimated=estimated[estimate_indices],
        sigma=sigma[measurement_indices],
    )


def prepare_voltage_comparison(
    *,
    grid: Grid,
    update_data: BatchDataset | None,
    output_data: BatchDataset | None,
    sensor_id: int,
) -> VoltageComparison:
    """Prepare a symmetric voltage comparison from batch datasets.

    Requires scenario-dependent measurement and sigma values.
    Static-only measurements are not yet supported.
    """
    sensor_matches = grid.sym_voltage_sensor.filter(id=[sensor_id])

    if sensor_matches.size != 1:
        raise ValueError(
            f"Expected exactly one symmetric voltage sensor with id={sensor_id}."
        )

    node_id = int(sensor_matches.measured_object[0])

    sensor_type = ComponentType.sym_voltage_sensor
    node_type = ComponentType.node

    if update_data is None or sensor_type not in update_data:
        raise ValueError(
            "Scenario-dependent symmetric voltage measurements are unavailable."
        )

    if output_data is None or node_type not in output_data:
        raise ValueError("Estimated node output data is unavailable.")

    required_measurement_fields = {"id", "u_measured", "u_sigma"}
    required_output_fields = {"id", "u"}

    measurement_fields = set(update_data[sensor_type].dtype.names or ())
    output_fields = set(output_data[node_type].dtype.names or ())

    if not required_measurement_fields.issubset(measurement_fields):
        raise ValueError(
            "Measurement update data lacks required voltage or sigma fields."
        )

    if not required_output_fields.issubset(output_fields):
        raise ValueError("Node output data lacks the voltage field.")

    measurement_scenarios, measured = get_attr_data_from_dataset(
        update_data, sensor_type, "u_measured", sensor_id
    )

    sigma_scenarios, sigma = get_attr_data_from_dataset(
        update_data, sensor_type, "u_sigma", sensor_id
    )

    estimate_scenarios, estimated = get_attr_data_from_dataset(
        output_data, node_type, "u", node_id
    )

    if not np.array_equal(measurement_scenarios, sigma_scenarios):
        raise ValueError("Measurement and sigma scenario indices differ.")

    return align_voltage_series(
        sensor_id=sensor_id,
        node_id=node_id,
        measurement_scenarios=measurement_scenarios,
        measured=measured,
        sigma=sigma,
        estimate_scenarios=estimate_scenarios,
        estimated=estimated,
    )


def calculate_sigma_bands(
    comparison: VoltageComparison,
    multiplier: float = 3.0,
) -> tuple[np.ndarray, np.ndarray]:
    """Calculate measurement-centred sigma bands.

    The multiplier affects only the displayed bands.
    It does not rerun state estimation.
    """
    if not np.isfinite(multiplier) or multiplier < 0:
        raise ValueError(
            "Sigma multiplier must be a finite, non-negative number."
        )

    lower = comparison.measured - multiplier * comparison.sigma
    upper = comparison.measured + multiplier * comparison.sigma

    if not np.all(np.isfinite(lower)) or not np.all(np.isfinite(upper)):
        raise ValueError("Calculated sigma bands contain non-finite values.")

    return lower, upper
