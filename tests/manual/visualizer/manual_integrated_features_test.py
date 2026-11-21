# SPDX-FileCopyrightText: Contributors to the Power Grid Model project <powergridmodel@lfenergy.org>
#
# SPDX-License-Identifier: MPL-2.0

"""Manual browser test for integrated visualiser functionality.

Uses real state-estimation results to inspect electrical information,
network components, node positions, and voltage measurements.

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
    """Prepare two scenarios with finite sensor uncertainties."""
    update_data = {}

    for component, _sigma_field in (
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
        update_data[component] = updates

    return update_data


def run_state_estimation(input_data, update_data):
    """Calculate two scenarios and reject reported batch failures."""
    model = PowerGridModel(input_data)

    output_data = model.calculate_state_estimation(
        update_data=update_data,
        symmetric=True,
        error_tolerance=1e-8,
        max_iterations=20,
        calculation_method=CalculationMethod.iterative_linear,
        continue_on_batch_error=True,
    )

    if model.batch_error is not None:
        raise RuntimeError(
            "State estimation reported a batch error. The manual visualiser test requires successful scenarios."
        )

    if output_data[ComponentType.node].shape[0] != 2:
        raise RuntimeError("Expected two state-estimation scenarios.")

    return output_data


def print_test_information(input_data):
    """Print network references and browser inspection tasks."""
    print("\n=== Integrated visualiser manual test ===")
    print("State estimation: two scenarios without reported batch errors")

    print("\nNetwork nodes:")
    for node_id in input_data[ComponentType.node][AttributeType.id]:
        print(f"  Node {int(node_id)}")

    print("\nNetwork lines:")
    for line in input_data[ComponentType.line]:
        print(
            f"  Line {int(line[AttributeType.id])}: "
            f"node {int(line[AttributeType.from_node])} -> "
            f"node {int(line[AttributeType.to_node])}"
        )

    print("\nVoltage sensor associations:")
    for sensor in input_data[ComponentType.sym_voltage_sensor]:
        print(f"  Node {int(sensor[AttributeType.measured_object])}: Sensor {int(sensor[AttributeType.id])}")

    print("\n=== Browser inspection checklist ===")
    print("1. Inspect available electrical information controls.")
    print("2. Identify nodes and network components.")
    print("3. Inspect attributes for individual and multiple nodes.")
    print("4. Verify network connections and node positions.")
    print("5. Select a node with a symmetric voltage sensor.")
    print("6. Compare measured and estimated voltage series.")
    print("7. Change the sigma multiplier and inspect the bands.")
    print("8. Inspect the F13 aggregated agreement overview, where available; do not infer feeder assignments.")
    print("9. Inspect F15 uncertainty-relative discrepancy for finite sigma and compare to source values.")
    print("10. Retain comparison graphs, change active component, and check diagnostic for stale values.")
    print("\nRecord discrepancies and capture browser evidence.")


def main():
    input_data = load_fixture()
    update_data = make_scenario_updates(input_data)
    output_data = run_state_estimation(input_data, update_data)

    interface = PowerGridModelInterface(input_data=input_data)
    grid = interface.create_grid_from_input_data()

    print_test_information(input_data)

    print("\nStarting visualiser: http://127.0.0.1:8050")
    visualize(
        grid,
        update_data=update_data,
        output_data=output_data,
        debug=False,
        port=8050,
    )


if __name__ == "__main__":
    main()
