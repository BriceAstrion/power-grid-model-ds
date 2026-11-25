# SPDX-FileCopyrightText: Contributors to the Power Grid Model project <powergridmodel@lfenergy.org>
#
# SPDX-License-Identifier: MPL-2.0

"""Calculate uncertainty-relative measurement diagnostics."""

import numpy as np
from numpy.typing import NDArray

from power_grid_model_ds._core.visualizer.measurement_comparison import (
    MeasurementComparison,
    VoltageComparison,
)


def calculate_uncertainty_relative_discrepancy(
    residual: NDArray[np.float64],
    sigma: NDArray[np.float64] | None,
) -> NDArray[np.float64]:
    """Return absolute residual divided by measurement standard deviation.

    Missing or non-finite inputs produce NaN. Zero sigma produces infinity
    for a nonzero residual and NaN for a zero residual. Negative finite
    sigma is invalid and raises ValueError.
    """
    residual = np.asarray(residual, dtype=np.float64)
    result = np.full(residual.shape, np.nan, dtype=np.float64)

    if sigma is None:
        return result

    sigma = np.asarray(sigma, dtype=np.float64)

    if residual.shape != sigma.shape:
        raise ValueError("Residual and sigma arrays must have matching shapes")

    if np.any(np.isfinite(sigma) & (sigma < 0)):
        raise ValueError("Sigma values must be non-negative")

    valid = np.isfinite(residual) & np.isfinite(sigma)

    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        result[valid] = np.abs(residual[valid]) / np.abs(sigma[valid])

    return result


def get_uncertainty_relative_discrepancy(
    comparison: VoltageComparison | MeasurementComparison,
) -> NDArray[np.float64]:
    """Calculate the uncertainty-relative discrepancy for a comparison."""
    if comparison.sigma is None:
        return np.full(comparison.measured.shape, np.nan, dtype=np.float64)

    measured = np.asarray(comparison.measured, dtype=np.float64)
    estimated = np.asarray(comparison.estimated, dtype=np.float64)
    sigma = np.asarray(comparison.sigma, dtype=np.float64)

    if measured.shape != estimated.shape or measured.shape != sigma.shape:
        raise ValueError("Measured, estimated and sigma arrays must have matching shapes")

    with np.errstate(invalid="ignore", over="ignore"):
        residual = measured - estimated

    return calculate_uncertainty_relative_discrepancy(residual, sigma)
