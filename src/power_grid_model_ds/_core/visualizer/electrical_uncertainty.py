# SPDX-FileCopyrightText: Contributors to the Power Grid Model project <powergridmodel@lfenergy.org>
#
# SPDX-License-Identifier: MPL-2.0

"""Prepare uncertainty-relative electrical quantities for one scenario."""

from collections.abc import Mapping

import numpy as np
from power_grid_model import ComponentType
from power_grid_model.data_types import DenseBatchArray

from power_grid_model_ds import Grid
from power_grid_model_ds._core.visualizer.electrical_quantity_utils import (
    extract_scenario_values,
    get_available_scalar_attributes,
)
from power_grid_model_ds._core.visualizer.uncertainty_diagnostics import calculate_uncertainty_relative_discrepancy

SIGMA_ATTRIBUTES = {
    (ComponentType.sym_voltage_sensor, "u_residual"): "u_sigma",
    (ComponentType.sym_power_sensor, "p_residual"): "p_sigma",
    (ComponentType.sym_power_sensor, "q_residual"): "q_sigma",
}


def get_effective_sigma(
    grid: Grid,
    update_data: Mapping[ComponentType, DenseBatchArray] | None,
    component: ComponentType,
    sigma_attribute: str,
    scenario_index: int,
) -> dict[int, float]:
    """Resolve base and specified scenario uncertainty values by sensor ID."""
    if scenario_index < 0:
        raise IndexError("Scenario index must be non-negative")
    sensors = getattr(grid, component.value)
    values = {
        int(sensor_id): float(sigma)
        for sensor_id, sigma in zip(sensors.id, getattr(sensors, sigma_attribute), strict=True)
    }
    if len(values) != len(sensors.id):
        raise ValueError("Duplicate sensor ID in grid")
    if update_data is None or component not in update_data:
        return values
    updates = update_data[component]
    if scenario_index >= updates.shape[0]:
        raise IndexError("Scenario index outside sensor updates")
    if sigma_attribute not in (updates.dtype.names or ()):
        return values
    seen: set[int] = set()
    for row in updates[scenario_index]:
        sensor_id = int(row["id"])
        if sensor_id not in values:
            continue
        if sensor_id in seen:
            raise ValueError(f"Duplicate sensor update ID {sensor_id}")
        seen.add(sensor_id)
        sigma = float(row[sigma_attribute])
        if not np.isnan(sigma):
            values[sensor_id] = sigma
    return values


def extract_uncertainty_relative_values(
    grid: Grid,
    update_data: Mapping[ComponentType, DenseBatchArray] | None,
    output_data: Mapping[ComponentType, DenseBatchArray] | None,
    quantity: tuple[ComponentType, str],
    scenario_index: int,
) -> dict[int, float]:
    """Return finite absolute residual-to-sigma ratios keyed by sensor ID."""
    component, residual_attribute = quantity
    sigma_attribute = SIGMA_ATTRIBUTES[quantity]
    residuals = extract_scenario_values(output_data, component, residual_attribute, scenario_index)
    sigmas = get_effective_sigma(grid, update_data, component, sigma_attribute, scenario_index)
    ids = list(residuals)
    residual = np.asarray(list(residuals.values()), dtype=np.float64)
    sigma = np.asarray([sigmas.get(sensor_id, np.nan) for sensor_id in ids], dtype=np.float64)
    # Invalid uncertainty is unavailable for this sensor, not the entire heatmap.
    sigma[sigma < 0] = np.nan
    ratios = calculate_uncertainty_relative_discrepancy(residual, sigma)
    return {sensor_id: float(ratio) for sensor_id, ratio in zip(ids, ratios, strict=True) if np.isfinite(ratio)}


DERIVED_QUANTITIES = {(component, f"{residual}_over_sigma"): residual for component, residual in SIGMA_ATTRIBUTES}


def get_available_electrical_quantities(
    output_data: Mapping[ComponentType, DenseBatchArray] | None,
) -> dict[str, list[str]]:
    """Discover native scalar fields and supported derived diagnostic fields."""
    available = get_available_scalar_attributes(output_data)
    for (component, derived), residual in DERIVED_QUANTITIES.items():
        attributes = available.get(component.value, [])
        if residual in attributes and derived not in attributes:
            attributes.append(derived)
    return available
