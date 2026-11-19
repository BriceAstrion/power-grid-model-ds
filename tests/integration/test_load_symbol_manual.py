# SPDX-FileCopyrightText: Contributors to the Power Grid Model project <powergridmodel@lfenergy.org>
#
# SPDX-License-Identifier: MPL-2.0

"""Standalone manual integration test for load presentation symbols.

Run from the repository root:
    python -m tests.integration.test_load_symbol_manual
"""

from power_grid_model import LoadGenType

from power_grid_model_ds.arrays import SymLoadArray
from power_grid_model_ds.visualizer import visualize
from tests.integration.visualizer_tests import get_coordinated_three_phase_grid


def build_test_grid():
    """Create a positioned grid with connected and disconnected loads."""
    grid = get_coordinated_three_phase_grid()

    loads = SymLoadArray.zeros(2)
    loads.id = [100, 101]
    loads.node = [3, 7]
    loads.status = [1, 0]
    loads.type = [LoadGenType.const_power] * 2
    loads.p_specified = [250_000, 100_000]
    loads.q_specified = [50_000, 20_000]

    grid.append(loads)
    return grid


def main():
    grid = build_test_grid()

    print("\n=== LOAD SYMBOL INTEGRATION TEST ===", flush=True)
    print(f"Symmetric loads: {len(grid.sym_load)}", flush=True)
    print(f"Load IDs: {grid.sym_load.id.tolist()}", flush=True)
    print(f"Connected nodes: {grid.sym_load.node.tolist()}", flush=True)
    print(f"Load statuses: {grid.sym_load.status.tolist()}", flush=True)

    assert len(grid.sym_load) == 2
    assert grid.sym_load.id.tolist() == [100, 101]

    print("\nStarting Dash visualizer...", flush=True)
    print("Use the PRESET layout to inspect the load symbols.", flush=True)

    visualize(grid=grid, debug=False)


if __name__ == "__main__":
    main()
