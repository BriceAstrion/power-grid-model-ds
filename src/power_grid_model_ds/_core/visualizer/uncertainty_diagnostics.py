# SPDX-FileCopyrightText: Contributors to the Power Grid Model project <powergridmodel@lfenergy.org>
#
# SPDX-License-Identifier: MPL-2.0

"""Numerical uncertainty-relative diagnostics shared by visualiser features."""

import numpy as np
from numpy.typing import NDArray


def calculate_uncertainty_relative_discrepancy(
    residual: NDArray[np.float64], sigma: NDArray[np.float64] | None
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
