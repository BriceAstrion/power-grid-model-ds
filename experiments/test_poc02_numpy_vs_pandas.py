"""POC-02 verification of NumPy/pandas output and error-handling parity.

The 11 POC-01 mutations are repeated for both implementations. All fixtures
are synthetic; no state-estimation calculation is executed.
"""

import numpy as np
import pytest

from poc01_voltage_mapping import create_fixture, map_voltage_measurements
from poc02_numpy_vs_pandas import (
    assert_equivalent,
    create_scaled_fixture,
    map_voltage_measurements_pandas,
)


@pytest.fixture
def datasets():
    return create_fixture()


def check_valid(datasets):
    numpy_result = map_voltage_measurements(*datasets, sensor_id=101)
    pandas_result = map_voltage_measurements_pandas(*datasets, sensor_id=101)
    assert_equivalent(numpy_result, pandas_result)
    return numpy_result, pandas_result


def check_invalid(datasets, sensor_id, message):
    for func in (map_voltage_measurements, map_voltage_measurements_pandas):
        with pytest.raises(ValueError, match=message):
            func(*datasets, sensor_id=sensor_id)


def test_tc01_reordered_component_ids(datasets):
    numpy_result, pandas_result = check_valid(datasets)
    for result in (numpy_result, pandas_result):
        assert [r["scenario"] for r in result] == [0, 1, 2]
        assert [r["measured"] for r in result] == [230.0, 231.0, 229.0]
        assert [r["estimated"] for r in result] == [229.5, 230.5, 228.5]
        assert all(r["status"] == "matched" for r in result)


def test_tc02_nan_estimate(datasets):
    datasets[2]["u"][1, 1] = np.nan
    for result in check_valid(datasets):
        assert result[1]["status"] == "missing_estimate"
        assert np.isnan(result[1]["estimated"])


def test_tc03_unknown_sensor(datasets):
    check_invalid(datasets, 404, "Expected one sensor")


def test_tc04_nan_measurement(datasets):
    datasets[1]["u_measured"][1, 0] = np.nan
    for result in check_valid(datasets):
        assert result[1]["status"] == "missing_measurement"
        assert np.isnan(result[1]["measured"])


def test_tc05_duplicate_update_sensor_id(datasets):
    datasets[1]["id"][0, 0] = 101
    check_invalid(datasets, 101, "Duplicate matching ID")


def test_tc06_scenario_count_mismatch(datasets):
    sensors, updates, outputs = datasets
    check_invalid((sensors, updates, outputs[:2].copy()), 101, "scenario counts differ")


def test_tc07_missing_node_output(datasets):
    datasets[2]["id"][1, 1] = 30
    for result in check_valid(datasets):
        assert result[1]["status"] == "missing_estimate"
        assert np.isnan(result[1]["estimated"])


def test_tc08_duplicate_node_id(datasets):
    datasets[2]["id"][0, 1] = 10
    check_invalid(datasets, 101, "Duplicate matching ID")


def test_tc09_absent_measurement_record(datasets):
    datasets[1]["id"][1, 0] = 777
    for result in check_valid(datasets):
        assert result[1]["status"] == "missing_measurement"
        assert np.isnan(result[1]["measured"])


def test_tc10_non_batch_input(datasets):
    sensors, updates, outputs = datasets
    check_invalid((sensors, updates[0], outputs), 101, "Expected dense two-dimensional")


def test_tc11_duplicate_sensor_definition(datasets):
    sensors, updates, outputs = datasets
    check_invalid((np.concatenate([sensors, sensors]), updates, outputs),
                  101, "Expected one sensor")


def test_tc12_nonfinite_estimate_infinity(datasets):
    datasets[2]["u"][1, 1] = np.inf
    for result in check_valid(datasets):
        assert result[1]["status"] == "missing_estimate"


def test_tc13_both_values_missing_measurement_precedence(datasets):
    datasets[1]["u_measured"][1, 0] = np.nan
    datasets[2]["u"][1, 1] = np.nan
    for result in check_valid(datasets):
        assert result[1]["status"] == "missing_measurement"
        assert np.isnan(result[1]["estimated"])


@pytest.mark.parametrize("scenarios,components", [(1, 2), (3, 7), (8, 13)])
def test_tc14_scaled_fixture_parity(scenarios, components):
    datasets = create_scaled_fixture(scenarios, components)
    numpy_result, pandas_result = check_valid(datasets)
    assert len(numpy_result) == len(pandas_result) == scenarios


def test_tc15_mapping_does_not_mutate_inputs(datasets):
    original = tuple(array.copy() for array in datasets)

    check_valid(datasets)

    for array, before in zip(datasets, original):
        assert array.shape == before.shape
        assert array.dtype == before.dtype

        for field in array.dtype.names:
            np.testing.assert_array_equal(
                array[field],
                before[field],
                err_msg=f"Input field '{field}' was modified",
            )
