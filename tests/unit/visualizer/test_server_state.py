# SPDX-FileCopyrightText: 2025 Contributors to the Power Grid Model project <powergridmodel@lfenergy.org>
#
# SPDX-License-Identifier: MPL-2.0

import numpy as np
import pytest
from power_grid_model import ComponentType, DatasetType, initialize_array

from power_grid_model_ds._core.model.grids.base import Grid
from power_grid_model_ds._core.visualizer import server_state


@pytest.fixture(autouse=True)
def reset_server_state() -> None:
    """Reset module-level state before every test."""
    server_state._state = server_state._AppState()


def make_update_data(scenario_count: int):
    """Create valid PGM update data for an empty grid."""
    return {
        ComponentType.node: initialize_array(
            DatasetType.update,
            ComponentType.node,
            (scenario_count, 0),
        )
    }


def make_output_data(scenario_count: int):
    """Create valid PGM output data for an empty grid."""
    return {
        ComponentType.node: initialize_array(
            DatasetType.sym_output,
            ComponentType.node,
            (scenario_count, 0),
        )
    }


def test_server_state():
    assert server_state._state.grid is None

    test_grid_data = Grid.empty()
    update_data = make_update_data(2)
    output_data = make_output_data(2)

    server_state.set_app_state(
        test_grid_data,
        update_data=update_data,
        output_data=output_data,
    )

    assert server_state.get_grid() is test_grid_data
    assert server_state.get_update_data() is update_data
    assert server_state.get_output_data() is output_data


def test_get_grid_uninitialized():
    assert server_state._state.grid is None

    with pytest.raises(RuntimeError, match="Grid state not initialized"):
        server_state.get_grid()


def test_reject_mismatched_update_and_output_scenario_counts():
    grid = Grid.empty()

    with pytest.raises(ValueError, match="same scenario count"):
        server_state.set_app_state(
            grid,
            update_data=make_update_data(2),
            output_data=make_output_data(3),
        )

    assert server_state._state.grid is None
    assert server_state._state.update_data is None
    assert server_state._state.output_data is None


def test_reject_inconsistent_component_scenario_counts():
    output_data = {
        ComponentType.node: initialize_array(
            DatasetType.sym_output,
            ComponentType.node,
            (3, 0),
        ),
        ComponentType.source: initialize_array(
            DatasetType.sym_output,
            ComponentType.source,
            (2, 0),
        ),
    }

    with pytest.raises(ValueError, match=r"inconsistent|invalid dataset dimensions"):
        server_state.set_app_state(
            Grid.empty(),
            output_data=output_data,
        )

    assert server_state._state.grid is None
    assert server_state._state.output_data is None


def test_single_dataset_does_not_require_the_other_dataset():
    grid = Grid.empty()
    output_data = make_output_data(3)

    server_state.set_app_state(grid, output_data=output_data)

    assert server_state.get_grid() is grid
    assert server_state.get_output_data() is output_data
    assert server_state.get_update_data() is None


def test_invalid_scenario_counts_preserve_existing_state():
    """Rejected datasets must not replace initialized state."""
    original_grid = Grid.empty()
    original_output = make_output_data(2)

    server_state.set_app_state(
        original_grid,
        output_data=original_output,
    )

    with pytest.raises(ValueError, match="same scenario count"):
        server_state.set_app_state(
            Grid.empty(),
            update_data=make_update_data(2),
            output_data=make_output_data(3),
        )

    assert server_state.get_grid() is original_grid
    assert server_state.get_output_data() is original_output
    assert server_state.get_update_data() is None


@pytest.mark.parametrize(
    ("scenario_ids", "expected_message"),
    [
        ([1, 1], "IDs must match grid IDs"),
        ([1, 999], "IDs must match grid IDs"),
        ([1], "IDs must match grid IDs"),
    ],
    ids=["duplicate-id", "unknown-id", "missing-id"],
)
def test_reject_invalid_output_component_ids(scenario_ids, expected_message):
    """Output IDs must match the grid IDs in every scenario."""
    grid = Grid.empty()
    grid.node = grid.node.__class__.empty(2)
    grid.node.id = np.array([1, 2], dtype=np.int32)

    output = initialize_array(
        DatasetType.sym_output,
        ComponentType.node,
        (2, len(scenario_ids)),
    )
    output["id"] = [scenario_ids, scenario_ids]

    with pytest.raises(ValueError, match=expected_message):
        server_state.set_app_state(
            grid,
            output_data={ComponentType.node: output},
        )

    assert server_state._state.grid is None
    assert server_state._state.output_data is None
