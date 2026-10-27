
"""POC-01: Map voltage measurements to estimated node voltages.

Uses synthetic Power Grid Model datasets.
No state-estimation calculation is performed.
"""

import numpy as np
from power_grid_model import ComponentType, DatasetType, initialize_array


def map_voltage_measurements(sensors, updates, outputs, sensor_id):
    """Match one voltage sensor to its node output by ID and scenario."""

    sensor_matches = sensors[sensors["id"] == sensor_id]
    _require_single_sensor(sensor_matches, sensor_id)

    node_id = int(sensor_matches["measured_object"][0])
    _validate_batches(updates, outputs)

    return [
        _map_scenario(updates, outputs, scenario, sensor_id, node_id)
        for scenario in range(updates.shape[0])
    ]


def _require_single_sensor(sensor_matches, sensor_id):
    """Ensure that exactly one sensor matches the requested ID."""
    if len(sensor_matches) != 1:
        raise ValueError(
            f"Expected one sensor with ID {sensor_id}; "
            f"found {len(sensor_matches)}"
        )


def _validate_batches(updates, outputs):
    """Check batch dimensions and scenario counts."""
    if updates.ndim != 2 or outputs.ndim != 2:
        raise ValueError("Expected dense two-dimensional batch arrays")

    if updates.shape[0] != outputs.shape[0]:
        raise ValueError("Measurement and output scenario counts differ")


def _map_scenario(updates, outputs, scenario, sensor_id, node_id):
    """Retrieve measurement and estimate for one scenario."""
    measurement_rows = updates[scenario][
        updates[scenario]["id"] == sensor_id
    ]
    estimate_rows = outputs[scenario][
        outputs[scenario]["id"] == node_id
    ]

    if len(measurement_rows) > 1 or len(estimate_rows) > 1:
        raise ValueError(
            f"Duplicate matching ID in scenario {scenario}"
        )

    measured = _get_value(measurement_rows, "u_measured")
    estimated = _get_value(estimate_rows, "u")

    return {
        "scenario": scenario,
        "sensor_id": sensor_id,
        "node_id": node_id,
        "measured": measured,
        "estimated": estimated,
        "status": _get_status(measured, estimated),
    }


def _get_value(rows, field):
    """Return the selected value or NaN when the record is absent."""
    if len(rows) == 0:
        return np.nan

    return float(rows[field][0])


def _get_status(measured, estimated):
    """Classify the availability of measurement and estimate."""
    if not np.isfinite(measured):
        return "missing_measurement"

    if not np.isfinite(estimated):
        return "missing_estimate"

    return "matched"


def create_fixture():
    """Create synthetic sensor, update and output datasets."""
    sensors = initialize_array(
        DatasetType.input,
        ComponentType.sym_voltage_sensor,
        1,
    )
    sensors["id"] = 101
    sensors["measured_object"] = 10

    updates = initialize_array(
        DatasetType.update,
        ComponentType.sym_voltage_sensor,
        (3, 2),
    )
    updates["id"] = [
        [999, 101],
        [101, 999],
        [999, 101],
    ]
    updates["u_measured"] = [
        [100.0, 230.0],
        [231.0, 100.0],
        [100.0, 229.0],
    ]

    outputs = initialize_array(
        DatasetType.sym_output,
        ComponentType.node,
        (3, 2),
    )
    outputs["id"] = [
        [10, 20],
        [20, 10],
        [10, 20],
    ]
    outputs["u"] = [
        [229.5, 100.0],
        [100.0, 230.5],
        [228.5, 100.0],
    ]

    return sensors, updates, outputs


def main():
    """Execute the initial POC-01 verification cases."""
    sensors, updates, outputs = create_fixture()

    # TC-01: Correct mapping with reordered components
    results = map_voltage_measurements(
        sensors, updates, outputs, sensor_id=101
    )

    print("POC-01: Normal mapping")
    for row in results:
        print(row)

    assert [r["measured"] for r in results] == [
        230.0, 231.0, 229.0
    ]
    assert [r["estimated"] for r in results] == [
        229.5, 230.5, 228.5
    ]
    assert all(r["status"] == "matched" for r in results)

    print("PASS: Correct ID-based mapping with reordered components")

    # TC-02: Missing estimated value
    outputs_missing = outputs.copy()
    outputs_missing["u"][1, 1] = np.nan

    missing_results = map_voltage_measurements(
        sensors, updates, outputs_missing, sensor_id=101
    )

    assert missing_results[1]["status"] == "missing_estimate"
    assert np.isnan(missing_results[1]["estimated"])

    print("PASS: Missing estimate reported")

    # TC-03: Unknown sensor ID
    try:
        map_voltage_measurements(
            sensors, updates, outputs, sensor_id=404
        )
    except ValueError:
        print("PASS: Unknown sensor ID rejected")
    else:
        raise AssertionError("Unknown sensor ID was not rejected")

    # TC-04: Missing measurement value
    updates_missing = updates.copy()
    updates_missing["u_measured"][1, 0] = np.nan

    results_missing = map_voltage_measurements(
        sensors, updates_missing, outputs, sensor_id=101
    )

    assert results_missing[1]["status"] == "missing_measurement"
    assert np.isnan(results_missing[1]["measured"])

    print("PASS: Missing measurement reported")

    # TC-05: Duplicate sensor ID in one scenario
    updates_duplicate = updates.copy()
    updates_duplicate["id"][0, 0] = 101

    try:
        map_voltage_measurements(
            sensors, updates_duplicate, outputs, sensor_id=101
        )
    except ValueError:
        print("PASS: Duplicate sensor ID rejected")
    else:
        raise AssertionError("Duplicate sensor ID was not rejected")

    # TC-06: Inconsistent scenario counts
    outputs_short = outputs[:2].copy()

    try:
        map_voltage_measurements(
            sensors, updates, outputs_short, sensor_id=101
        )
    except ValueError:
        print("PASS: Inconsistent scenario counts rejected")
    else:
        raise AssertionError("Scenario mismatch was not rejected")

    # TC-07: Missing node output record
    outputs_missing_node = outputs.copy()
    outputs_missing_node["id"][1, 1] = 30

    results_missing_node = map_voltage_measurements(
        sensors, updates, outputs_missing_node, sensor_id=101
    )

    assert results_missing_node[1]["status"] == "missing_estimate"
    assert np.isnan(results_missing_node[1]["estimated"])

    print("PASS: Missing node output reported")

    print("\nPOC-01: All 7 initial checks passed")


if __name__ == "__main__":
    main()
