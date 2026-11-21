# SPDX-FileCopyrightText: Contributors to the Power Grid Model project <powergridmodel@lfenergy.org>
#
# SPDX-License-Identifier: MPL-2.0

"""Consolidated manual browser test for the integrated PGM-DS visualiser.

Run from the repository root (with the integrated source on PYTHONPATH):
    python tests/manual/visualizer/manual_integrated_visualizer.py

Uses the existing multi-component state-estimation fixture. The two calculated
scenarios are assigned explicit observation timestamps for F05.
This is a MANUAL browser test, not an automated UI test. A deliberately missing
result is not generated, so F05 missing-result handling remains untested.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
from power_grid_model import (
    AttributeType,
    CalculationMethod,
    ComponentType,
    DatasetType,
    PowerGridModel,
    initialize_array,
)

from power_grid_model_ds._core.power_grid_model_interface import PowerGridModelInterface
from power_grid_model_ds.visualizer import visualize

REPO_ROOT = Path(__file__).resolve().parents[3]
FIXTURE_PATH = REPO_ROOT / "tests/integration/visualizer/_state_estimation_fixture.py"
TIMESTAMPS = (
    "2026-11-07T10:00:00+01:00",
    "2026-11-07T10:15:00+01:00",
)


def load_input_data():
    """Reuse the repository's actual, multi-component SE fixture."""
    if not FIXTURE_PATH.is_file():
        raise FileNotFoundError(f"Expected integration fixture: {FIXTURE_PATH}")
    spec = importlib.util.spec_from_file_location("_manual_se_fixture", FIXTURE_PATH)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load {FIXTURE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.make_state_estimation_input_data()


def make_updates(input_data):
    """Use the same two-scenario sensor updates as the existing manual test."""
    updates = {}
    for component in (
        ComponentType.sym_voltage_sensor,
        ComponentType.sym_power_sensor,
        ComponentType.sym_current_sensor,
    ):
        ids = input_data[component][AttributeType.id]
        array = initialize_array(DatasetType.update, component, (2, len(ids)))
        array[AttributeType.id] = np.tile(ids, (2, 1))
        updates[component] = array
    return updates


def calculate(input_data, updates):
    model = PowerGridModel(input_data)
    result = model.calculate_state_estimation(
        update_data=updates,
        symmetric=True,
        error_tolerance=1e-8,
        max_iterations=20,
        calculation_method=CalculationMethod.iterative_linear,
        continue_on_batch_error=True,
    )
    if model.batch_error is not None:
        raise RuntimeError(f"State estimation reported batch errors: {model.batch_error}")
    if result[ComponentType.node].shape[0] != 2:
        raise RuntimeError("Expected two state-estimation scenarios")
    return result


def show_reference_data(input_data, result):
    print("\n=== SOURCE DATA: verify against the browser ===")
    for component in (ComponentType.node, ComponentType.line, ComponentType.sym_load):
        print(f"\n{component.value} IDs:", [int(x) for x in input_data[component][AttributeType.id]])

    print("\nLine connectivity (line ID: from -> to):")
    for line in input_data[ComponentType.line]:
        print(
            f"  {int(line[AttributeType.id])}: "
            f"{int(line[AttributeType.from_node])} -> {int(line[AttributeType.to_node])}"
        )

    print("\nVoltage sensors (sensor ID -> node, measurement, sigma):")
    for sensor in input_data[ComponentType.sym_voltage_sensor]:
        print(
            f"  {int(sensor[AttributeType.id])} -> node {int(sensor[AttributeType.measured_object])}, "
            f"u_measured={float(sensor[AttributeType.u_measured]):.5f} V, "
            f"u_sigma={float(sensor[AttributeType.u_sigma]):.5f} V"
        )

    print("\nEstimated node voltages, as returned by PGM (not hard-coded):")
    for scenario_index, scenario in enumerate(result[ComponentType.node]):
        print(f"  Scenario {scenario_index}:")
        for node in scenario:
            print(f"    node {int(node[AttributeType.id])}: u={float(node[AttributeType.u]):.5f} V")


def show_checklist():
    print("\n=== MANUAL BROWSER ACCEPTANCE CHECKLIST ===")
    print(
        "[ ] F01: Select two available electrical quantities; verify network encoding, "
        "legend, units, and unavailable-value handling."
    )
    print("[ ] F02: Select nodes 1, 2, 6 and lines 3, 5, 8; verify IDs against the source data above.")
    print(
        "[ ] F03: Open node, line, load and sensor details; verify source values "
        "and that unrelated detail plots do not open automatically."
    )
    print(
        "[ ] F04: Inspect line connectivity and arrow directions; compare each line "
        "with the from/to node references printed above."
    )
    print(
        "[ ] F04: Check whether topology remains understandable after layout/configuration changes; "
        "overlap/crossing edge cases are NOT covered by this fixture."
    )
    print("[ ] F05: Expand Network state; verify observation date and the two available times.")
    print(
        "[ ] F05: Select each time and a node; compare displayed output values "
        "with the printed calculated node voltages."
    )
    print("[ ] F05: Verify available update values for selected sensors, where provided.")
    print("[ ] F05 NOT COVERED: Missing-result handling requires a deliberately incomplete result fixture.")
    print(
        "[ ] F10: Select a symmetric voltage sensor and u_measured; "
        "compare measured/estimated series over both scenario indices."
    )
    print("[ ] F10: Check plotted values against the reference data and confirm sensor-to-node mapping.")
    print("[ ] F11: Set sigma multiplier to 1, 2, 3; check band widths and unchanged measured/estimated traces.")
    print("[ ] F11: Open 'Why?' guidance; verify it does not equate in-band values with valid results.")
    print("[ ] F14: Retain voltage, angle and another available quantity graph simultaneously.")
    print("[ ] F14: Remove one graph; verify others persist; re-add it; then clear all graphs.")
    print(
        "[ ] F13: Inspect aggregated measurement agreement and availability statuses; "
        "verify feeder assignment evidence."
    )
    print("[ ] F15: For voltage comparison with finite sigma, inspect uncertainty-relative discrepancy values.")
    print("[ ] F15: With a retained comparison, change active component and check diagnostic state for stale content.")
    print("[ ] F15 NOT COVERED: Missing-sigma behavior requires the separate missing-sigma fixture.")
    print("[ ] General: Verify no Dash missing-ID/callback errors appear.")
    print("\nRecord PASS/FAIL/NOT TESTED per item and capture screenshots as evidence.")


def main():
    input_data = load_input_data()
    updates = make_updates(input_data)
    result = calculate(input_data, updates)
    grid = PowerGridModelInterface(input_data=input_data).create_grid_from_input_data()
    show_reference_data(input_data, result)
    show_checklist()
    print("\nF05 observation timestamps (scenario 0, scenario 1):", TIMESTAMPS)
    print("Starting visualiser at http://127.0.0.1:8050", flush=True)
    visualize(
        grid=grid,
        update_data=updates,
        output_data=result,
        timestamps=TIMESTAMPS,
        debug=False,
        port=8050,
    )


if __name__ == "__main__":
    main()
