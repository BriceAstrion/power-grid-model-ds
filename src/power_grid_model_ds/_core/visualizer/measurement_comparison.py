# SPDX-FileCopyrightText: Contributors to the Power Grid Model project <powergridmodel@lfenergy.org>
#
# SPDX-License-Identifier: MPL-2.0

"""Prepare scenario-aligned voltage and symmetric power comparisons."""

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray
from power_grid_model import ComponentType, MeasuredTerminalType
from power_grid_model.data_types import BatchDataset

from power_grid_model_ds._core.model.grids.base import Grid
from power_grid_model_ds._core.visualizer.grid_utils import get_attr_data_from_dataset
from power_grid_model_ds.arrays import SymVoltageSensorArray

DENSE_BATCH_NDIM = 2


@dataclass(frozen=True)
class VoltageComparison:
    """Aligned voltage sensor values, retaining the integrated branch API."""

    sensor_id: int
    node_id: int
    scenarios: NDArray[np.int64]
    measured: NDArray[np.float64]
    estimated: NDArray[np.float64]
    sigma: NDArray[np.float64] | None = None

    @property
    def scenario_indices(self) -> NDArray[np.int64]:
        """Expose scenario positions to the reusable plotter."""
        return self.scenarios


@dataclass(frozen=True)
class MeasurementComparison:
    """Generic aligned measurement and estimate series with optional sigma."""

    scenario_indices: NDArray[np.int64]
    measured: NDArray[np.float64]
    estimated: NDArray[np.float64]
    sigma: NDArray[np.float64] | None = None


def align_voltage_series(  # noqa: PLR0913  # pylint: disable=too-many-arguments,too-many-positional-arguments
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

    arrays = (measurement_scenarios, measured, sigma, estimate_scenarios, estimated)
    if any(array.ndim != 1 for array in arrays):
        raise ValueError("Symmetric voltage comparison requires 1D arrays.")

    if not (len(measurement_scenarios) == len(measured) == len(sigma) and len(estimate_scenarios) == len(estimated)):
        raise ValueError("Scenario and value array lengths do not match.")

    for scenarios in (measurement_scenarios, estimate_scenarios):
        if not np.issubdtype(scenarios.dtype, np.integer):
            raise ValueError("Scenario indices must be integers.")
        if len(np.unique(scenarios)) != len(scenarios):
            raise ValueError("Duplicate scenario indices are not supported.")

    if not (np.all(np.isfinite(measured)) and np.all(np.isfinite(estimated)) and np.all(np.isfinite(sigma))):
        raise ValueError("Comparison contains non-finite values.")

    if np.any(sigma <= 0):
        raise ValueError("Sigma values must be positive.")

    common_scenarios, measurement_indices, estimate_indices = np.intersect1d(
        measurement_scenarios,
        estimate_scenarios,
        return_indices=True,
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


def _validate_voltage_datasets(
    update_data: BatchDataset | None, output_data: BatchDataset | None
) -> tuple[BatchDataset, BatchDataset]:
    sensor_type = ComponentType.sym_voltage_sensor
    node_type = ComponentType.node

    if update_data is None or sensor_type not in update_data:
        raise ValueError("Scenario-dependent symmetric voltage measurements are unavailable.")

    if output_data is None or node_type not in output_data:
        raise ValueError("Estimated node output data is unavailable.")

    required_measurement_fields = {"id", "u_measured", "u_sigma"}
    required_output_fields = {"id", "u"}

    measurement_fields = set(_require_dense_ids(update_data, sensor_type).dtype.names or ())
    output_fields = set(_require_dense_ids(output_data, node_type).dtype.names or ())

    if not required_measurement_fields.issubset(measurement_fields):
        raise ValueError("Measurement update data lacks required voltage or sigma fields.")

    if not required_output_fields.issubset(output_fields):
        raise ValueError("Node output data lacks the voltage field.")

    return update_data, output_data


def _resolve_measurement_defaults(
    sensor_matches: SymVoltageSensorArray, measured: NDArray, sigma: NDArray
) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    measured = np.asarray(measured, dtype=np.float64).copy()
    sigma = np.asarray(sigma, dtype=np.float64).copy()
    measured = np.where(np.isnan(measured), float(sensor_matches.u_measured[0]), measured)
    sigma = np.where(np.isnan(sigma), float(sensor_matches.u_sigma[0]), sigma)
    return measured, sigma


def prepare_voltage_comparison(
    *, grid: Grid, update_data: BatchDataset | None, output_data: BatchDataset | None, sensor_id: int
) -> VoltageComparison:
    """Prepare a symmetric voltage comparison from batch datasets.

    Requires scenario-dependent measurement and sigma values.
    Static-only measurements are not yet supported.
    """
    sensor_matches = grid.sym_voltage_sensor.filter(id=[sensor_id])

    if sensor_matches.size != 1:
        raise ValueError(f"Expected exactly one symmetric voltage sensor with id={sensor_id}.")

    node_id = int(sensor_matches.measured_object[0])

    update_data, output_data = _validate_voltage_datasets(update_data, output_data)
    sensor_type = ComponentType.sym_voltage_sensor
    node_type = ComponentType.node

    measurement_scenarios, measured = get_attr_data_from_dataset(update_data, sensor_type, "u_measured", sensor_id)

    sigma_scenarios, sigma = get_attr_data_from_dataset(update_data, sensor_type, "u_sigma", sensor_id)

    estimate_scenarios, estimated = get_attr_data_from_dataset(output_data, node_type, "u", node_id)

    if not np.array_equal(measurement_scenarios, sigma_scenarios):
        raise ValueError("Measurement and sigma scenario indices differ.")

    # In PGM update arrays, NaN means the original input value
    # remains unchanged. Resolve these values from the grid.
    measured, sigma = _resolve_measurement_defaults(sensor_matches, measured, sigma)

    return align_voltage_series(
        sensor_id=sensor_id,
        node_id=node_id,
        measurement_scenarios=measurement_scenarios,
        measured=measured,
        sigma=sigma,
        estimate_scenarios=estimate_scenarios,
        estimated=estimated,
    )


def _require_dense_ids(dataset: BatchDataset, component: ComponentType) -> NDArray:
    """Return a dense component array with explicit IDs."""
    component_data = dataset[component]

    if not isinstance(component_data, np.ndarray) or component_data.ndim != DENSE_BATCH_NDIM:
        raise NotImplementedError(
            "Measurement comparison currently supports only dense batch arrays. "
            "Sparse and columnar batch data are not implemented."
        )

    if component_data.dtype.names is None or "id" not in component_data.dtype.names:
        raise NotImplementedError(
            "Measurement comparison requires an explicit 'id' field. "
            "Batch data without explicit component IDs are not implemented."
        )

    return component_data


def _get_estimated_voltages(output_data: BatchDataset, node_id: int) -> NDArray[np.float64]:
    """Return calculated node voltages, preserving missing scenarios as NaN."""
    node_output = _require_dense_ids(output_data, ComponentType.node)
    if node_output.dtype.names is None or "u" not in node_output.dtype.names:
        raise ValueError("Node output must contain a 'u' field")

    scenario_indices, voltages = get_attr_data_from_dataset(output_data, ComponentType.node, "u", node_id)
    if len(np.unique(scenario_indices)) != len(scenario_indices):
        raise ValueError(f"Duplicate node ID {node_id} in output")

    estimated = np.full(node_output.shape[0], np.nan, dtype=np.float64)
    estimated[scenario_indices] = voltages
    return estimated


def _apply_sensor_updates(  # noqa: PLR0913  # pylint: disable=too-many-arguments
    update_data: BatchDataset | None,
    scenario_count: int,
    sensor_id: int,
    measured: NDArray[np.float64],
    sigma: NDArray[np.float64],
    *,
    component: ComponentType = ComponentType.sym_voltage_sensor,
    measurement_attribute: str = "u_measured",
    sigma_attribute: str = "u_sigma",
) -> None:
    """Apply explicitly specified sensor updates at their scenario positions."""
    if update_data is None or component not in update_data:
        return

    sensor_updates = _require_dense_ids(update_data, component)
    if sensor_updates.shape[0] != scenario_count:
        raise ValueError("Sensor updates must match the output scenario count")

    field_names = sensor_updates.dtype.names
    if field_names is None:
        raise ValueError("Sensor updates require structured component data")

    for attribute, target in ((measurement_attribute, measured), (sigma_attribute, sigma)):
        if attribute not in field_names:
            continue
        scenario_indices, values = get_attr_data_from_dataset(update_data, component, attribute, sensor_id)
        if len(np.unique(scenario_indices)) != len(scenario_indices):
            raise ValueError(f"Duplicate sensor ID {sensor_id} in updates")
        specified = ~np.isnan(values)
        target[scenario_indices[specified]] = values[specified]


def _get_estimated_series(
    output_data: BatchDataset, component: ComponentType, attribute: str, object_id: int
) -> NDArray[np.float64]:
    """Extract an estimated scalar quantity, retaining missing scenarios as NaN."""
    if component not in output_data:
        raise ValueError(f"{component.value} output is required for comparison")

    data = _require_dense_ids(output_data, component)
    field_names = data.dtype.names
    fields = data.dtype.fields
    if field_names is None or fields is None or attribute not in field_names:
        raise ValueError(f"{component.value} output requires scalar '{attribute}'")

    field_dtype = next((dtype for name, dtype in fields.items() if name == attribute), None)
    if field_dtype is None or field_dtype[0].subdtype is not None:
        raise ValueError(f"{component.value} output requires scalar '{attribute}'")

    indices, values = get_attr_data_from_dataset(output_data, component, attribute, object_id)
    if len(np.unique(indices)) != len(indices):
        raise ValueError(f"Duplicate {component.value} ID {object_id} in output")

    estimated = np.full(data.shape[0], np.nan, dtype=np.float64)
    estimated[indices] = values

    return estimated


def get_symmetric_power_comparison(
    grid: Grid, update_data: BatchDataset | None, output_data: BatchDataset, sensor_id: int, measurement_attribute: str
) -> MeasurementComparison:
    """Compare a source-terminal power measurement with its calculated output.

    Only the verified source-terminal mapping is supported here. Other terminal
    types must be resolved against their actual component and output schema.
    `power_sigma` is deliberately ignored: bands use p_sigma or q_sigma only.
    """
    if measurement_attribute not in ("p_measured", "q_measured"):
        raise ValueError(f"Unsupported power measurement: {measurement_attribute}")

    sensors = grid.sym_power_sensor
    matches = np.flatnonzero(sensors.id == sensor_id)
    if matches.size != 1:
        raise ValueError(f"Expected exactly one power sensor with ID {sensor_id}")
    index = int(matches[0])
    terminal = int(sensors.measured_terminal_type[index])
    if terminal != MeasuredTerminalType.source.value:
        raise NotImplementedError(f"Power comparison for terminal type {terminal} is not implemented")

    estimated_attribute = measurement_attribute[0]  # 'p' or 'q'
    sigma_attribute = f"{estimated_attribute}_sigma"
    estimated = _get_estimated_series(
        output_data, ComponentType.source, estimated_attribute, int(sensors.measured_object[index])
    )
    count = len(estimated)
    measured = np.full(count, float(getattr(sensors, measurement_attribute)[index]), dtype=np.float64)
    sigma = np.full(count, float(getattr(sensors, sigma_attribute)[index]), dtype=np.float64)
    _apply_sensor_updates(
        update_data,
        count,
        sensor_id,
        measured,
        sigma,
        component=ComponentType.sym_power_sensor,
        measurement_attribute=measurement_attribute,
        sigma_attribute=sigma_attribute,
    )
    if np.any(np.isfinite(sigma) & (sigma < 0)):
        raise ValueError("Sigma values must be non-negative")

    # Missing sigma means no uncertainty bands, but comparison lines remain.
    return MeasurementComparison(
        scenario_indices=np.arange(count, dtype=np.intp),
        measured=measured,
        estimated=estimated,
        sigma=sigma if np.isfinite(sigma).any() else None,
    )


def get_symmetric_voltage_comparison(
    grid: Grid,
    update_data: BatchDataset | None,
    output_data: BatchDataset,
    sensor_id: int,
) -> VoltageComparison:
    """Compare base or updated sensor values with calculated node voltages.

    Scenario positions are preserved, and unspecified floating-point sensor
    updates retain the base-grid values. Only dense batch arrays with explicit
    IDs are currently supported.
    """
    sensors = grid.sym_voltage_sensor
    sensor_matches = np.flatnonzero(sensors.id == sensor_id)

    if sensor_matches.size != 1:
        raise ValueError(f"Expected exactly one voltage sensor with ID {sensor_id}")

    sensor_index = int(sensor_matches[0])
    node_id = int(sensors.measured_object[sensor_index])

    if ComponentType.node not in output_data:
        raise ValueError("Node output is required for voltage comparison")

    estimated = _get_estimated_voltages(output_data, node_id)
    scenario_count = len(estimated)
    scenario_indices = np.arange(scenario_count, dtype=np.intp)

    measured = np.full(scenario_count, float(sensors.u_measured[sensor_index]), dtype=np.float64)
    sigma = np.full(scenario_count, float(sensors.u_sigma[sensor_index]), dtype=np.float64)
    _apply_sensor_updates(update_data, scenario_count, sensor_id, measured, sigma)

    return VoltageComparison(
        sensor_id=sensor_id,
        node_id=node_id,
        scenarios=scenario_indices,
        measured=measured,
        estimated=estimated,
        sigma=sigma,
    )


def get_measurement_sigma_bounds(
    comparison: MeasurementComparison | VoltageComparison,
    multiplier: float,
) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    """Calculate measurement-centred uncertainty bounds for aligned series."""
    if not np.isfinite(multiplier) or multiplier < 0:
        raise ValueError("Sigma multiplier must be finite and non-negative")

    if comparison.sigma is None:
        raise ValueError("Measurement sigma is required to calculate bounds")

    if np.any(np.isfinite(comparison.sigma) & (comparison.sigma < 0)):
        raise ValueError("Sigma values must be non-negative")

    lower = comparison.measured - multiplier * comparison.sigma
    upper = comparison.measured + multiplier * comparison.sigma
    return lower, upper


def get_voltage_sigma_bounds(
    comparison: VoltageComparison,
    multiplier: float,
) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    """Compatibility wrapper for measurement-centred voltage bounds."""
    return get_measurement_sigma_bounds(comparison, multiplier)


def calculate_sigma_bands(
    comparison: VoltageComparison,
    multiplier: float = 3.0,
) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    """Calculate voltage bands using the existing integrated API."""
    return get_voltage_sigma_bounds(comparison, multiplier)
