# SPDX-FileCopyrightText: Contributors to the Power Grid Model project <powergridmodel@lfenergy.org>
#
# SPDX-License-Identifier: MPL-2.0

"""Prepare scenario-specific measurement agreement groups for F13."""

import math
from dataclasses import dataclass
from enum import StrEnum
from statistics import mean

import numpy as np


class MeasurementStatus(StrEnum):
    """Availability of the measured and estimated values."""

    AVAILABLE = "available"
    MISSING_MEASUREMENT = "missing_measurement"
    MISSING_ESTIMATE = "missing_estimate"
    UNMATCHED = "unmatched"


class FeederStatus(StrEnum):
    """Evidence available for assigning a measurement to a feeder."""

    ASSIGNED = "assigned"
    UNASSIGNED = "unassigned"
    UNVERIFIED = "unverified"


@dataclass(frozen=True)
class MeasurementIdentity:
    """Identify a measurement and its corresponding component."""

    scenario_index: int
    sensor_id: int
    component_id: int
    quantity: str
    unit: str


@dataclass(frozen=True)
class AgreementRecord:  # pylint: disable=too-many-instance-attributes
    """A measurement and estimate for one scenario.

    The ten fields are the stable record schema used by agreement grouping.
    """

    scenario_index: int
    sensor_id: int
    component_id: int
    quantity: str
    unit: str
    measured: float | None
    estimated: float | None
    feeder_id: int | None
    status: MeasurementStatus
    feeder_status: FeederStatus

    @property
    def absolute_discrepancy(self) -> float | None:
        """Return the absolute difference for an available pair."""
        if self.status is not MeasurementStatus.AVAILABLE:
            return None

        if self.measured is None or self.estimated is None:
            return None

        return _finite_or_none(abs(self.estimated - self.measured))


@dataclass(frozen=True)
class DiscrepancyStatistics:
    """Descriptive statistics for comparable measurement pairs."""

    minimum: float | None
    mean: float | None
    maximum: float | None


@dataclass(frozen=True)
class AgreementGroup:
    """Measurement records belonging to one aggregation scope."""

    records: tuple[AgreementRecord, ...]

    @property
    def total_count(self) -> int:
        """Return the number of records."""
        return len(self.records)

    @property
    def available_count(self) -> int:
        """Count records with both measured and estimated values."""
        return sum(record.status is MeasurementStatus.AVAILABLE for record in self.records)

    @property
    def unavailable_count(self) -> int:
        """Count records without a usable measurement pair."""
        return self.total_count - self.available_count

    def _absolute_discrepancies(self) -> list[float]:
        """Collect finite discrepancies with compatible quantities and units."""
        discrepancies: list[float] = []
        quantity_units: set[tuple[str, str]] = set()

        for record in self.records:
            discrepancy = record.absolute_discrepancy

            if discrepancy is None:
                continue

            quantity_units.add((record.quantity, record.unit))

            if len(quantity_units) > 1:
                return []

            discrepancies.append(discrepancy)

        return discrepancies

    def discrepancy_statistics(self) -> DiscrepancyStatistics:
        """Calculate all discrepancy statistics from one collection."""
        discrepancies = self._absolute_discrepancies()

        if not discrepancies:
            return DiscrepancyStatistics(
                minimum=None,
                mean=None,
                maximum=None,
            )

        return DiscrepancyStatistics(
            minimum=min(discrepancies),
            mean=mean(discrepancies),
            maximum=max(discrepancies),
        )

    @property
    def mean_absolute_discrepancy(self) -> float | None:
        """Return the mean absolute discrepancy of comparable pairs."""
        discrepancies = self._absolute_discrepancies()

        if not discrepancies:
            return None

        return mean(discrepancies)

    @property
    def min_absolute_discrepancy(self) -> float | None:
        """Return the smallest available absolute difference."""
        discrepancies = self._absolute_discrepancies()
        return min(discrepancies, default=None)

    @property
    def max_absolute_discrepancy(self) -> float | None:
        """Return the largest absolute discrepancy of comparable pairs."""
        discrepancies = self._absolute_discrepancies()

        return max(discrepancies, default=None)


@dataclass(frozen=True)
class AgreementOverview:
    """Network-wide and feeder-grouped measurement records."""

    scenario_index: int
    network: AgreementGroup
    feeders: dict[int, AgreementGroup]
    unassigned: AgreementGroup


def _finite_or_none(value: float | None) -> float | None:
    """Convert missing or non-finite values to None."""
    if value is None:
        return None

    numeric = float(value)
    return numeric if math.isfinite(numeric) else None


def _validate_scenario_index(scenario_index: int) -> None:
    """Reject invalid scenario indices."""
    if isinstance(scenario_index, bool) or not isinstance(scenario_index, (int, np.integer)) or scenario_index < 0:
        raise ValueError("Scenario index must be a non-negative integer.")


def make_agreement_record(
    identity: MeasurementIdentity,
    *,
    measured: float | None,
    estimated: float | None,
    feeder_id: int | None,
    matched: bool = True,
) -> AgreementRecord:
    """Create a record with independent measurement and feeder statuses."""
    _validate_scenario_index(identity.scenario_index)

    measured = _finite_or_none(measured)
    estimated = _finite_or_none(estimated)

    if not matched:
        status = MeasurementStatus.UNMATCHED
    elif measured is None:
        status = MeasurementStatus.MISSING_MEASUREMENT
    elif estimated is None:
        status = MeasurementStatus.MISSING_ESTIMATE
    else:
        status = MeasurementStatus.AVAILABLE

    feeder_status = FeederStatus.UNASSIGNED if feeder_id is None else FeederStatus.UNVERIFIED

    return AgreementRecord(
        scenario_index=identity.scenario_index,
        sensor_id=identity.sensor_id,
        component_id=identity.component_id,
        quantity=identity.quantity,
        unit=identity.unit,
        measured=measured,
        estimated=estimated,
        feeder_id=feeder_id,
        status=status,
        feeder_status=feeder_status,
    )


def build_agreement_overview(
    records: list[AgreementRecord],
    scenario_index: int,
) -> AgreementOverview:
    """Group records for descriptive measurement discrepancy analysis."""
    _validate_scenario_index(scenario_index)

    selected: list[AgreementRecord] = []
    feeder_records: dict[int, list[AgreementRecord]] = {}
    unassigned: list[AgreementRecord] = []

    for record in records:
        if record.scenario_index != scenario_index:
            continue

        selected.append(record)

        if record.feeder_id is None:
            unassigned.append(record)
        else:
            feeder_records.setdefault(record.feeder_id, []).append(record)

    feeders = {feeder_id: AgreementGroup(tuple(feeder_records[feeder_id])) for feeder_id in sorted(feeder_records)}

    return AgreementOverview(
        scenario_index=scenario_index,
        network=AgreementGroup(tuple(selected)),
        feeders=feeders,
        unassigned=AgreementGroup(tuple(unassigned)),
    )
