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
from power_grid_model_ds._core.visualizer.scenario_status import scenario_status_from_batch_error
from power_grid_model_ds.visualizer import visualize

# Reuse the network from the existing integration-test fixture.
repo_root = Path(__file__).resolve().parents[3]
fixture_dir = repo_root / "tests" / "integration" / "visualizer"
fixture_path = fixture_dir / "_state_estimation_fixture.py"
fixture_spec = importlib.util.spec_from_file_location("_state_estimation_fixture", fixture_path)
if fixture_spec is None or fixture_spec.loader is None:
    raise ImportError(f"Could not load state-estimation fixture from {fixture_path}")
fixture_module = importlib.util.module_from_spec(fixture_spec)
fixture_spec.loader.exec_module(fixture_module)
make_state_estimation_input_data = fixture_module.make_state_estimation_input_data


def main():
    input_data = make_state_estimation_input_data()

    model = PowerGridModel(input_data)
    update_data = {}

    for component, sigma_field in (
        (ComponentType.sym_voltage_sensor, AttributeType.u_sigma),
        (ComponentType.sym_power_sensor, AttributeType.power_sigma),
        (ComponentType.sym_current_sensor, AttributeType.i_sigma),
    ):
        sensor_ids = input_data[component][AttributeType.id]
        count = len(sensor_ids)

        updates = initialize_array(
            DatasetType.update,
            component,
            (2, count),
        )
        updates[AttributeType.id] = np.tile(sensor_ids, (2, 1))
        updates[sigma_field][1, :] = np.inf

        update_data[component] = updates

    output_data = model.calculate_state_estimation(
        update_data=update_data,
        symmetric=True,
        error_tolerance=1e-8,
        max_iterations=20,
        calculation_method=CalculationMethod.iterative_linear,
        continue_on_batch_error=True,
    )

    batch_error = model.batch_error
    if batch_error is None:
        raise RuntimeError("Expected scenario 1 to fail, but no batch error was returned.")

    scenario_status = scenario_status_from_batch_error(
        batch_error,
        scenario_count=2,
    )

    print("Succeeded scenarios:", sorted(scenario_status.succeeded_scenarios))
    print("Failed scenarios:", sorted(scenario_status.failed_scenarios))
    print("Scenario 1 error:", scenario_status.error_for(1))

    interface = PowerGridModelInterface(input_data=input_data)
    grid = interface.create_grid_from_input_data()

    print("Starting visualiser at http://127.0.0.1:8050")

    visualize(
        grid,
        update_data=update_data,
        output_data=output_data,
        scenario_status=scenario_status,
        debug=False,
        port=8050,
    )


if __name__ == "__main__":
    main()