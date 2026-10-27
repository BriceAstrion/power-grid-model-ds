"""POC-02: Compare NumPy and pandas measurement-to-estimate preparation.

Uses the POC-01 NumPy function as the baseline. The pandas alternative uses
identical synthetic Power Grid Model structured-array inputs and returns the
same list-of-dicts interface. No state-estimation calculation is executed.

Run from the workspace root, with experiments/ on the Python import path:
    uv run --project .\\power-grid-model-ds python experiments/poc02_numpy_vs_pandas.py
    uv run --project .\\power-grid-model-ds python experiments/poc02_numpy_vs_pandas.py --benchmark
"""

from __future__ import annotations

import argparse
import csv
import platform
import statistics
import sys
from pathlib import Path
from time import perf_counter_ns

import numpy as np
import pandas as pd  # type: ignore[reportMissingImports]

from poc01_voltage_mapping import create_fixture, map_voltage_measurements


def map_voltage_measurements_pandas(sensors, updates, outputs, sensor_id):
    """Map PGM voltage values with DataFrame filtering and scenario joins.

    DataFrames are constructed once per batch. The selected measurement and
    estimate records are joined by scenario after identifier filtering.
    All conversion and join work is included in end-to-end timing.
    """
    sensor_frame = pd.DataFrame(
        {"id": sensors["id"], "measured_object": sensors["measured_object"]}
    )
    sensor_matches = sensor_frame.loc[sensor_frame["id"] == sensor_id]
    if len(sensor_matches) != 1:
        raise ValueError(
            f"Expected one sensor with ID {sensor_id}; "
            f"found {len(sensor_matches)}"
        )
    node_id = int(sensor_matches["measured_object"].iloc[0])

    if updates.ndim != 2 or outputs.ndim != 2:
        raise ValueError("Expected dense two-dimensional batch arrays")
    if updates.shape[0] != outputs.shape[0]:
        raise ValueError("Measurement and output scenario counts differ")

    scenario_count = updates.shape[0]
    measurement_frame = pd.DataFrame({
        "scenario": np.repeat(np.arange(scenario_count), updates.shape[1]),
        "id": updates["id"].reshape(-1),
        "measured": updates["u_measured"].reshape(-1),
    })
    estimate_frame = pd.DataFrame({
        "scenario": np.repeat(np.arange(scenario_count), outputs.shape[1]),
        "id": outputs["id"].reshape(-1),
        "estimated": outputs["u"].reshape(-1),
    })
    selected_measurements = measurement_frame.loc[
        measurement_frame["id"] == sensor_id, ["scenario", "measured"]
    ]
    selected_estimates = estimate_frame.loc[
        estimate_frame["id"] == node_id, ["scenario", "estimated"]
    ]

    # Match POC-01's rule: reject more than one matching record per scenario.
    duplicate_scenarios = []
    for selected in (selected_measurements, selected_estimates):
        duplicates = selected.loc[
            selected["scenario"].duplicated(keep=False), "scenario"
        ]
        if not duplicates.empty:
            duplicate_scenarios.append(int(duplicates.min()))
    if duplicate_scenarios:
        raise ValueError(
            f"Duplicate matching ID in scenario {min(duplicate_scenarios)}"
        )

    scenario_frame = pd.DataFrame({"scenario": np.arange(scenario_count)})
    paired = scenario_frame.merge(
        selected_measurements, how="left", on="scenario", sort=False,
        validate="one_to_one",
    ).merge(
        selected_estimates, how="left", on="scenario", sort=False,
        validate="one_to_one",
    )

    results = []
    for row in paired.itertuples(index=False):
        measured = float(row.measured)
        estimated = float(row.estimated)
        if not np.isfinite(measured):
            status = "missing_measurement"
        elif not np.isfinite(estimated):
            status = "missing_estimate"
        else:
            status = "matched"
        results.append({
            "scenario": int(row.scenario),
            "sensor_id": sensor_id,
            "node_id": node_id,
            "measured": measured,
            "estimated": estimated,
            "status": status,
        })
    return results


def assert_equivalent(left, right):
    """Compare POC-01-style outputs, treating corresponding NaNs as equal."""
    if len(left) != len(right):
        raise AssertionError(f"Different row counts: {len(left)} != {len(right)}")
    for index, (a, b) in enumerate(zip(left, right)):
        if a.keys() != b.keys():
            raise AssertionError(f"Different fields in scenario {index}")
        for field in a:
            av, bv = a[field], b[field]
            if field in ("measured", "estimated"):
                equal = bool(np.isclose(av, bv, rtol=0, atol=0, equal_nan=True))
            else:
                equal = av == bv
            if not equal:
                raise AssertionError(
                    f"Scenario {index}, {field}: NumPy={av!r}, pandas={bv!r}"
                )


def create_scaled_fixture(n_scenarios: int, n_components: int):
    """Scale the POC-01 schema while retaining exactly one matching ID per row.

    All values are synthetic. Each scenario contains one selected sensor (101)
    and node (10), placed at changing positions among unrelated records.
    """
    if n_scenarios < 1 or n_components < 2:
        raise ValueError("Need >=1 scenario and >=2 components")
    sensors, base_updates, base_outputs = create_fixture()
    updates = np.empty((n_scenarios, n_components), dtype=base_updates.dtype)
    outputs = np.empty((n_scenarios, n_components), dtype=base_outputs.dtype)
    # Copy a valid structured record to initialise every PGM field.
    updates[:] = base_updates[0, 0]
    outputs[:] = base_outputs[0, 0]
    updates["id"] = 1000 + np.arange(n_components)[None, :]
    outputs["id"] = 2000 + np.arange(n_components)[None, :]
    for scenario in range(n_scenarios):
        sensor_position = (scenario * 7 + 1) % n_components
        node_position = (scenario * 11) % n_components
        updates["id"][scenario, sensor_position] = 101
        outputs["id"][scenario, node_position] = 10
        updates["u_measured"][scenario, sensor_position] = (
            [230.0, 231.0, 229.0][scenario % 3]
        )
        outputs["u"][scenario, node_position] = (
            [229.5, 230.5, 228.5][scenario % 3]
        )
    return sensors, updates, outputs


def _measure_ns(func, args, repeats: int, warmups: int):
    for _ in range(warmups):
        func(*args, sensor_id=101)
    durations = []
    for _ in range(repeats):
        start = perf_counter_ns()
        func(*args, sensor_id=101)
        durations.append(perf_counter_ns() - start)
    return durations


def run_benchmark(output_csv: Path, repeats: int = 7, warmups: int = 2):
    """Record raw end-to-end times, including pandas conversion overhead.

    Times are for a single selected sensor, not an all-sensors batch join.
    Python and dependency versions are recorded alongside each measurement.
    """
    if repeats < 1 or warmups < 0:
        raise ValueError("repeats must be positive and warmups nonnegative")
    cases = [(3, 2), (30, 50), (100, 500)]
    rows = []
    for n_scenarios, n_components in cases:
        args = create_scaled_fixture(n_scenarios, n_components)
        assert_equivalent(
            map_voltage_measurements(*args, sensor_id=101),
            map_voltage_measurements_pandas(*args, sensor_id=101),
        )
        for name, func in (
            ("numpy", map_voltage_measurements),
            ("pandas", map_voltage_measurements_pandas),
        ):
            durations = _measure_ns(func, args, repeats, warmups)
            for trial, duration in enumerate(durations, start=1):
                rows.append({
                    "scenarios": n_scenarios,
                    "components_per_scenario": n_components,
                    "implementation": name,
                    "trial": trial,
                    "elapsed_ms": f"{duration / 1_000_000:.6f}",
                    "python": platform.python_version(),
                    "numpy": np.__version__,
                    "pandas": pd.__version__,
                    "platform": platform.platform(),
                })
            print(
                f"{n_scenarios:>3} scenarios x {n_components:>3} components | "
                f"{name:>6} | median {statistics.median(durations) / 1e6:.4f} ms "
                f"({repeats} runs)"
            )
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    with output_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"Raw benchmark measurements saved to: {output_csv}")


def main():
    parser = argparse.ArgumentParser(description="POC-02 NumPy/pandas comparison")
    parser.add_argument("--benchmark", action="store_true", help="Run timed comparisons")
    parser.add_argument("--repeats", type=int, default=7)
    parser.add_argument("--warmups", type=int, default=2)
    parser.add_argument(
        "--csv", type=Path,
        default=Path(__file__).with_name("poc02_benchmark_results.csv"),
    )
    options = parser.parse_args()
    sensors, updates, outputs = create_fixture()
    numpy_results = map_voltage_measurements(sensors, updates, outputs, sensor_id=101)
    pandas_results = map_voltage_measurements_pandas(sensors, updates, outputs, sensor_id=101)
    assert_equivalent(numpy_results, pandas_results)
    print("POC-02: Baseline fixture parity PASS (three scenarios)")
    print(f"Python {sys.version.split()[0]}; NumPy {np.__version__}; pandas {pd.__version__}")
    for row in pandas_results:
        print(row)
    if options.benchmark:
        run_benchmark(options.csv, repeats=options.repeats, warmups=options.warmups)


if __name__ == "__main__":
    main()