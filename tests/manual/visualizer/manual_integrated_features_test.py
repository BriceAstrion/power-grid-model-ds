# SPDX-FileCopyrightText: Contributors to the Power Grid Model project <powergridmodel@lfenergy.org>
#
# SPDX-License-Identifier: MPL-2.0

"""Manual browser test for integrated visualiser functionality.

Covers interactive inspection of F01-F04 and F07 using a real
state-estimation network and solver-produced scenario outcomes.

Run from the repository root:
    uv run --no-sync python tests/manual/visualizer/manual_integrated_features_test.py
"""

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
from power_grid_model_ds._core.visualizer.scenario_status import (
    CalculationStatus,
    scenario_status_from_batch_error,
)
from power_grid_model_ds.visualizer import visualize


def load_fixture():
    """Load the existing integration-test network fixture."""
    repo_root = Path(__file__).resolve().parents[3]
    fixture_path = repo_root / "tests" / "integration" / "visualizer" / "_state_estimation_fixture.py"

    spec = importlib.util.spec_from_file_location(
        "_state_estimation_fixture",
        fixture_path,
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load fixture: {fixture_path}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.make_state_estimation_input_data()


def make_scenario_updates(input_data):
    """Prepare two scenarios, including one with unusable sensor sigmas."""
    update_data = {}

    for component, sigma_field in (
        (ComponentType.sym_voltage_sensor, AttributeType.u_sigma),
        (ComponentType.sym_power_sensor, AttributeType.power_sigma),
        (ComponentType.sym_current_sensor, AttributeType.i_sigma),
    ):
        sensor_ids = input_data[component][AttributeType.id]
        updates = initialize_array(
            DatasetType.update,
            component,
            (2, len(sensor_ids)),
        )
        updates[AttributeType.id] = np.tile(sensor_ids, (2, 1))
        updates[sigma_field][1, :] = np.inf
        update_data[component] = updates

    return update_data


def run_state_estimation(input_data, update_data):
    """Calculate real results and verify the expected scenario outcomes."""
    model = PowerGridModel(input_data)

    output_data = model.calculate_state_estimation(
        update_data=update_data,
        symmetric=True,
        error_tolerance=1e-8,
        max_iterations=20,
        calculation_method=CalculationMethod.iterative_linear,
        continue_on_batch_error=True,
    )

    if output_data[ComponentType.node].shape[0] != 2:
        raise RuntimeError("Expected two state-estimation scenarios.")

    batch_error = model.batch_error
    if batch_error is None:
        raise RuntimeError("Expected a solver-reported failure for scenario 1.")

    status = scenario_status_from_batch_error(
        batch_error,
        scenario_count=2,
    )

    if status.status_for(0) != CalculationStatus.SUCCEEDED or status.status_for(1) != CalculationStatus.FAILED:
        raise RuntimeError("Unexpected scenario outcomes; cannot use this test setup.")

    return output_data, status


def print_test_information(input_data, status):
    """Print reproducible reference information for browser inspection."""
    print("\n=== Integrated visualiser manual test ===")
    print("Requirements: F01, F02, F03, F04, F07")

    print("\nNetwork nodes:")
    for node_id in input_data[ComponentType.node][AttributeType.id]:
        print(f"  Node {int(node_id)}")

    print("\nNetwork lines:")
    lines = input_data[ComponentType.line]
    for line in lines:
        print(
            f"  Line {int(line[AttributeType.id])}: "
            f"node {int(line[AttributeType.from_node])} -> "
            f"node {int(line[AttributeType.to_node])}"
        )

    print("\nVoltage sensor associations:")
    sensors = input_data[ComponentType.sym_voltage_sensor]
    for sensor in sensors:
        print(f"  Node {int(sensor[AttributeType.measured_object])}: Sensor {int(sensor[AttributeType.id])}")

    print("\nState-estimation scenario outcomes:")
    for scenario in (0, 1):
        result = status.status_for(scenario)
        print(f"  Scenario {scenario}: {result}")
        error = status.error_for(scenario)
        if error:
            print(f"    Solver error: {error}")

    print("\n=== Browser inspection checklist ===")
    print("F01: Inspect available electrical information controls.")
    print("F02: Identify nodes 1, 2 and 6 and the network components.")
    print("F03: Inspect attributes for individual and multiple nodes.")
    print("F04: Verify lines 3 (1-2), 5 (2-6), 8 (1-6).")
    print("F07: Verify one succeeded and one failed scenario.")
    print("F07: Select nodes 1, 2 and 6 together.")
    print("     Expected voltage sensors: 11, 12 and 13 respectively.")
    print("F07: Deselect nodes and verify diagnostics update.")
    print("\nRecord any discrepancies and capture browser evidence.")


def main():
    input_data = load_fixture()
    update_data = make_scenario_updates(input_data)
    output_data, status = run_state_estimation(input_data, update_data)

    interface = PowerGridModelInterface(input_data=input_data)
    grid = interface.create_grid_from_input_data()

    print_test_information(input_data, status)

    print("\nStarting visualiser: http://127.0.0.1:8050")
    visualize(
        grid,
        update_data=update_data,
        output_data=output_data,
        scenario_status=status,
        debug=False,
        port=8050,
    )


if __name__ == "__main__":
    main()
