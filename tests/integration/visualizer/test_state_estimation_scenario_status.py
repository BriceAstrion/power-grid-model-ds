# SPDX-FileCopyrightText: Contributors to the Power Grid Model project <powergridmodel@lfenergy.org>
#
# SPDX-License-Identifier: MPL-2.0

"""Integration test for real state-estimation batch failures."""

import numpy as np

from _state_estimation_fixture import make_state_estimation_input_data

from power_grid_model import (
    AttributeType,
    CalculationMethod,
    ComponentType,
    DatasetType,
    PowerGridModel,
    initialize_array,
)

from power_grid_model_ds._core.visualizer.scenario_status import (
    CalculationStatus,
    scenario_status_from_batch_error,
)


def test_real_batch_failure_scenario_status():
    """Convert actual solver batch-error metadata into visualiser statuses."""

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

    assert output_data[ComponentType.node].shape[0] == 2
    assert batch_error is not None

    assert list(batch_error.succeeded_scenarios) == [0]
    assert list(batch_error.failed_scenarios) == [1]

    status = scenario_status_from_batch_error(
        batch_error,
        scenario_count=2,
    )

    assert status.status_for(0) == CalculationStatus.SUCCEEDED
    assert status.status_for(1) == CalculationStatus.FAILED

    assert len(status.error_messages) == 1
    assert "Not enough measurements" in status.error_messages[0]