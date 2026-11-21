# SPDX-FileCopyrightText: Contributors to the Power Grid Model project <powergridmodel@lfenergy.org>
#
# SPDX-License-Identifier: MPL-2.0

"""Uncertainty-based diagnostics for measurement comparisons."""

import numpy as np
from numpy.typing import NDArray

from power_grid_model_ds._core.visualizer.measurement_comparison import (
    MeasurementComparison,
    VoltageComparison,
)


def get_uncertainty_relative_discrepancy(
    comparison: VoltageComparison | MeasurementComparison,
) -> NDArray[np.float64]:
    """Calculate the absolute measurement discrepancy relative to sigma.

    The result is aligned with the comparison scenario indices.

    Scenarios with missing or non-finite measurement, estimate or sigma
    return NaN. Zero sigma produces infinity for a non-zero discrepancy
    and NaN when the discrepancy is also zero.
    """
    if comparison.sigma is None:
        return np.full(
            comparison.measured.shape,
            np.nan,
            dtype=np.float64,
        )

    measured = np.asarray(comparison.measured, dtype=np.float64)
    estimated = np.asarray(comparison.estimated, dtype=np.float64)
    sigma = np.asarray(comparison.sigma, dtype=np.float64)

    if measured.shape != estimated.shape or measured.shape != sigma.shape:
        raise ValueError("Measured, estimated and sigma arrays must have matching shapes")

    if np.any(np.isfinite(sigma) & (sigma < 0)):
        raise ValueError("Sigma values must be non-negative")

    discrepancy = np.full(measured.shape, np.nan, dtype=np.float64)

    valid = np.isfinite(measured) & np.isfinite(estimated) & np.isfinite(sigma)

    difference = np.abs(measured[valid] - estimated[valid])
    valid_sigma = sigma[valid]

    with np.errstate(divide="ignore", invalid="ignore"):
        discrepancy[valid] = difference / valid_sigma

    return discrepancy
