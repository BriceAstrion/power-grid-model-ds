# SPDX-FileCopyrightText: Contributors to the Power Grid Model project <powergridmodel@lfenergy.org>
#
# SPDX-License-Identifier: MPL-2.0

"""Represent state-estimation calculation status for batch scenarios."""

from dataclasses import dataclass
from enum import Enum

import numpy as np
from numpy.typing import NDArray
from power_grid_model.errors import PowerGridBatchError


class CalculationStatus(str, Enum):
    """Calculation outcome for one scenario."""

    SUCCEEDED = "succeeded"
    FAILED = "failed"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class ScenarioStatus:
    """Scenario indices and their reported calculation outcomes."""

    succeeded_scenarios: frozenset[int]
    failed_scenarios: frozenset[int]
    error_messages: tuple[str, ...] = ()

    def status_for(self, scenario: int) -> CalculationStatus:
        """Return the reported status for a scenario index."""
        if scenario in self.failed_scenarios:
            return CalculationStatus.FAILED

        if scenario in self.succeeded_scenarios:
            return CalculationStatus.SUCCEEDED

        return CalculationStatus.UNKNOWN


def scenario_status_from_batch_error(
    batch_error: PowerGridBatchError | None,
    *,
    scenario_count: int | None = None,
) -> ScenarioStatus:
    """Convert Power Grid Model batch-error information to scenario status.

    When no batch error is present, scenario status is only marked as
    successful if the caller explicitly supplies the scenario count.
    """
    if scenario_count is not None and scenario_count < 0:
        raise ValueError("Scenario count must not be negative.")

    if batch_error is None:
        succeeded = (
            frozenset(range(scenario_count))
            if scenario_count is not None
            else frozenset()
        )
        return ScenarioStatus(
            succeeded_scenarios=succeeded,
            failed_scenarios=frozenset(),
        )

    failed = frozenset(int(index) for index in batch_error.failed_scenarios)
    succeeded = frozenset(
        int(index) for index in batch_error.succeeded_scenarios
    )

    if failed & succeeded:
        raise ValueError(
            "A scenario cannot be both successful and failed."
        )

    if scenario_count is not None:
        valid_indices = set(range(scenario_count))
        if not (failed | succeeded) <= valid_indices:
            raise ValueError("Scenario status contains an invalid index.")

    return ScenarioStatus(
        succeeded_scenarios=succeeded,
        failed_scenarios=failed,
        error_messages=tuple(str(message) for message in batch_error.error_messages),
    )