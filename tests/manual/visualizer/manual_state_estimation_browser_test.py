# SPDX-FileCopyrightText: Contributors to the Power Grid Model project <powergridmodel@lfenergy.org>
#
# SPDX-License-Identifier: MPL-2.0

"""Manual browser verification using real state-estimation results."""

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
    """Create two scenarios without deliberately invalid sensor values."""
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


def main():
    input_data = load_fixture()
    update_data = make_scenario_updates(input_data)

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
        raise RuntimeError("State estimation reported a batch error; expected successful scenarios.")

    if output_data[ComponentType.node].shape[0] != 2:
        raise RuntimeError("Expected two state-estimation scenarios.")

    interface = PowerGridModelInterface(input_data=input_data)
    grid = interface.create_grid_from_input_data()

    print("Calculated two scenarios without reported batch errors.")
    print("Starting visualiser at http://127.0.0.1:8050")

    visualize(
        grid,
        update_data=update_data,
        output_data=output_data,
        debug=False,
        port=8050,
    )


if __name__ == "__main__":
    main()
