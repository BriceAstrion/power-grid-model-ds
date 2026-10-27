
"""Automated verification tests for POC-01.

The tests use synthetic Power Grid Model datasets.
They do not execute a state-estimation calculation.
"""

import numpy as np
import pytest

from poc01_voltage_mapping import (
    create_fixture,
    map_voltage_measurements,
)


@pytest.fixture
def datasets():
    """Provide fresh datasets for each test."""
    return create_fixture()


def test_tc01_matches_reordered_components(datasets):
    sensors, updates, outputs = datasets

    results = map_voltage_measurements(
        sensors, updates, outputs, sensor_id=101
    )

    assert [row["scenario"] for row in results] == [0, 1, 2]
    assert [row["measured"] for row in results] == [
        230.0, 231.0, 229.0
    ]
    assert [row["estimated"] for row in results] == [
        229.5, 230.5, 228.5
    ]
    assert all(row["status"] == "matched" for row in results)


def test_tc02_reports_missing_estimate(datasets):
    sensors, updates, outputs = datasets
    outputs["u"][1, 1] = np.nan

    results = map_voltage_measurements(
        sensors, updates, outputs, sensor_id=101
    )

    assert results[1]["status"] == "missing_estimate"
    assert np.isnan(results[1]["estimated"])


def test_tc03_rejects_unknown_sensor(datasets):
    sensors, updates, outputs = datasets

    with pytest.raises(ValueError, match="Expected one sensor"):
        map_voltage_measurements(
            sensors, updates, outputs, sensor_id=404
        )


def test_tc04_reports_missing_measurement(datasets):
    sensors, updates, outputs = datasets
    updates["u_measured"][1, 0] = np.nan

    results = map_voltage_measurements(
        sensors, updates, outputs, sensor_id=101
    )

    assert results[1]["status"] == "missing_measurement"
    assert np.isnan(results[1]["measured"])


def test_tc05_rejects_duplicate_sensor_id(datasets):
    sensors, updates, outputs = datasets
    updates["id"][0, 0] = 101

    with pytest.raises(ValueError, match="Duplicate matching ID"):
        map_voltage_measurements(
            sensors, updates, outputs, sensor_id=101
        )


def test_tc06_rejects_inconsistent_scenario_counts(datasets):
    sensors, updates, outputs = datasets
    outputs = outputs[:2].copy()

    with pytest.raises(ValueError, match="scenario counts differ"):
        map_voltage_measurements(
            sensors, updates, outputs, sensor_id=101
        )


def test_tc07_reports_missing_node_output(datasets):
    sensors, updates, outputs = datasets
    outputs["id"][1, 1] = 30

    results = map_voltage_measurements(
        sensors, updates, outputs, sensor_id=101
    )

    assert results[1]["status"] == "missing_estimate"
    assert np.isnan(results[1]["estimated"])


def test_tc08_rejects_duplicate_node_id(datasets):
    sensors, updates, outputs = datasets
    outputs["id"][0, 1] = 10

    with pytest.raises(ValueError, match="Duplicate matching ID"):
        map_voltage_measurements(
            sensors, updates, outputs, sensor_id=101
        )


def test_tc09_reports_absent_measurement_record(datasets):
    sensors, updates, outputs = datasets
    updates["id"][1, 0] = 777

    results = map_voltage_measurements(
        sensors, updates, outputs, sensor_id=101
    )

    assert results[1]["status"] == "missing_measurement"
    assert np.isnan(results[1]["measured"])


def test_tc10_rejects_non_batch_input(datasets):
    sensors, updates, outputs = datasets

    with pytest.raises(
        ValueError, match="Expected dense two-dimensional"
    ):
        map_voltage_measurements(
            sensors, updates[0], outputs, sensor_id=101
        )


def test_tc11_rejects_duplicate_sensor_definition(datasets):
    sensors, updates, outputs = datasets
    duplicate_sensors = np.concatenate([sensors, sensors])

    with pytest.raises(ValueError, match="Expected one sensor"):
        map_voltage_measurements(
            duplicate_sensors, updates, outputs, sensor_id=101
        )
