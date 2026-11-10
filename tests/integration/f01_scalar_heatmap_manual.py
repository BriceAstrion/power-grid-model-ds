# SPDX-FileCopyrightText: Contributors to the Power Grid Model project <powergridmodel@lfenergy.org>
#
# SPDX-License-Identifier: MPL-2.0

"""Manual integrated-visualizer scenarios for F01 and interacting features.

Run from the repository root:
    python -m tests.integration.f01_scalar_heatmap_manual --list
    python -m tests.integration.f01_scalar_heatmap_manual --case scalar
    python -m tests.integration.f01_scalar_heatmap_manual --case asymmetric
    python -m tests.integration.f01_scalar_heatmap_manual --case topology
    python -m tests.integration.f01_scalar_heatmap_manual --case missing
    python -m tests.integration.f01_scalar_heatmap_manual --case sparse
    python -m tests.integration.f01_scalar_heatmap_manual --case no-output

Each --case starts one blocking Dash visualizer session. Stop the server
(Ctrl+C) before launching another case. The fixtures use illustrative
values; they are not power-flow or state-estimation calculations.

This is a *manual* test harness: it checks fixture structure before launch,
but does not automatically assert browser rendering or interactions.
"""

import argparse
from collections.abc import Callable
from dataclasses import dataclass

import numpy as np
from power_grid_model import AttributeType, ComponentType, DatasetType, initialize_array

from power_grid_model_ds._core.visualizer.electrical_quantity_utils import (
    get_available_scalar_attributes,
    get_scenario_count,
)
from power_grid_model_ds.visualizer import visualize
from tests.integration.visualizer_tests import get_coordinated_three_phase_grid


@dataclass(frozen=True)
class ManualCase:
    name: str
    description: str
    checks: tuple[str, ...]
    build: Callable


def _grid():
    return get_coordinated_three_phase_grid()


def _scalar_output(grid, scenario_count=4):
    """Build deterministic symmetric node/line scalar output."""
    output = {}
    for component, ids in (
        (ComponentType.node, grid.node.id),
        (ComponentType.line, grid.line.id),
    ):
        arr = initialize_array(DatasetType.sym_output, component, (scenario_count, len(ids)))
        arr[AttributeType.id] = np.broadcast_to(ids, (scenario_count, len(ids)))
        for field in arr.dtype.names or ():
            field_dtype = arr.dtype.fields[field][0]
            if field != "id" and field_dtype.subdtype is None and field_dtype.kind == "f":
                # Different scenarios and components yield distinguishable values.
                offset = 100.0 if component == ComponentType.line else 0.0
                arr[field] = np.array(
                    [
                        [offset + 10.0 * (scenario + 1) + index + 1 for index in range(len(ids))]
                        for scenario in range(scenario_count)
                    ],
                    dtype=float,
                )
        output[component] = arr
    return output


def _case_scalar():
    grid = _grid()
    return grid, None, _scalar_output(grid)


def _case_asymmetric():
    grid = _grid()
    nodes = initialize_array(DatasetType.asym_output, ComponentType.node, (4, 3))
    nodes[AttributeType.id] = np.broadcast_to(grid.node.id[:3], (4, 3))
    nodes[AttributeType.u] = [
        [[401.0, 402.0, 403.0], [404.0, 405.0, 406.0], [407.0, 408.0, 409.0]],
        [[410.0, 411.0, 412.0], [413.0, 414.0, 415.0], [416.0, 417.0, 418.0]],
        [[419.0, 420.0, 421.0], [422.0, 423.0, 424.0], [425.0, 426.0, 427.0]],
        [[428.0, 429.0, 430.0], [431.0, 432.0, 433.0], [434.0, 435.0, 436.0]],
    ]
    nodes[AttributeType.energized] = 1
    nodes[AttributeType.energized][1, 2] = 0
    return grid, None, {ComponentType.node: nodes}


TOPOLOGY_TIMESTAMPS = (
    "2026-11-07T10:00:00+01:00",
    "2026-11-07T11:00:00+01:00",
    "2026-11-07T12:00:00+01:00",
    "2026-11-07T13:00:00+01:00",
)


def _case_topology():
    grid = _grid()
    output = _scalar_output(grid)
    lines_update = initialize_array(DatasetType.update, ComponentType.line, (4, 2))
    lines_update[AttributeType.id] = np.broadcast_to(grid.line.id[:2], (4, 2))
    lines_update[AttributeType.from_status] = 1
    lines_update[AttributeType.from_status][1, 0] = 0
    lines_update[AttributeType.from_status][3, 1] = 0
    return grid, {ComponentType.line: lines_update}, output


def _case_missing():
    grid = _grid()
    output = _scalar_output(grid)
    nodes = output[ComponentType.node]
    # Missing values in selected nodes and scenarios, leaving other data intact.
    for field in nodes.dtype.names or ():
        dtype = nodes.dtype.fields[field][0]
        if field != "id" and dtype.subdtype is None and dtype.kind == "f":
            nodes[field][1, 0] = np.nan
            nodes[field][3, -1] = np.nan
    return grid, None, output


def _case_sparse():
    grid = _grid()
    # Only three nodes have output; other grid elements remain present.
    nodes = initialize_array(DatasetType.sym_output, ComponentType.node, (4, 3))
    nodes[AttributeType.id] = np.broadcast_to(grid.node.id[:3], (4, 3))
    for field in nodes.dtype.names or ():
        dtype = nodes.dtype.fields[field][0]
        if field != "id" and dtype.subdtype is None and dtype.kind == "f":
            nodes[field] = np.array([[10.0 * (scenario + 1) + i for i in range(3)] for scenario in range(4)])
    return grid, None, {ComponentType.node: nodes}


def _case_no_output():
    return _grid(), None, None


COMMON_CHECKS = (
    "Select an electrical component and available scalar attribute; check colors and legend.",
    "Switch scenarios 1, 2, 4, then 1; check colors/values update and no stale legend.",
    "Change attribute and component repeatedly; check invalid combinations are handled.",
    "Drag two nodes, change node scale, toggle appliances; check positions remain sensible.",
    "Select several graphable cells, retain graphs, prevent duplicates, remove one, clear all, re-add.",
    "With retained graphs present, switch component, attribute and scenario; check graph independence.",
    "Clear selections and reselect; check controls, legend and graphs recover correctly.",
    "Inspect browser console and server terminal for unexpected errors.",
)

CASES = {
    "scalar": ManualCase(
        "scalar",
        "Four symmetric-output scenarios with node and line scalar fields.",
        COMMON_CHECKS,
        _case_scalar,
    ),
    "asymmetric": ManualCase(
        "asymmetric",
        "Four asymmetric node-voltage scenarios, including one de-energized result.",
        (
            "Inspect phase-dependent quantities and any scalar-attribute availability limitations.",
            "Switch scenarios and inspect the de-energized node in scenario 2.",
            "Confirm node dragging, scaling, appliance visibility and graph selection still work.",
        ),
        _case_asymmetric,
    ),
    "topology": ManualCase(
        "topology",
        "Symmetric output plus scenario-dependent line status updates.",
        (
            *COMMON_CHECKS,
            "In Network state, inspect the selected line update at 10:00, 11:00, 12:00 and 13:00.",
            "For the first updated line, expect from_status 1, 0, 1, 1; for the second, 1, 1, 1, 0.",
            "Check whether the network line styling changes separately from the update-data card.",
            "Verify changing topology does not discard dragged positions or retained graphs unexpectedly.",
        ),
        _case_topology,
    ),
    "missing": ManualCase(
        "missing",
        "Symmetric scalar output with NaN values in scenarios 2 and 4.",
        (
            *COMMON_CHECKS,
            "Inspect missing-value coloring and legend handling; no fabricated numeric values.",
            "Switch from missing to valid scenarios and back; check recovery.",
        ),
        _case_missing,
    ),
    "sparse": ManualCase(
        "sparse",
        "Only three grid nodes have output; line and other node output is absent.",
        (
            "Check that unsupported component/attribute selections are unavailable or safely handled.",
            "Inspect nodes with no output and switch scenarios repeatedly.",
            "Check node positioning, appliance toggles and retained graph behavior.",
        ),
        _case_sparse,
    ),
    "no-output": ManualCase(
        "no-output",
        "Grid without calculation output.",
        (
            "Confirm electrical-quantity controls do not offer unavailable calculated values.",
            "Check basic network rendering, selection, node dragging and appliance visibility.",
            "Check no stale heatmap legend, sigma guidance or calculated-value graphs appear.",
        ),
        _case_no_output,
    ),
}


def _print_case(case, output):
    print(f"\nMANUAL CASE: {case.name}\n{case.description}", flush=True)
    if output is None:
        print("Calculation output: none", flush=True)
    else:
        print("Scenario count:", get_scenario_count(output), flush=True)
        print("Available scalar attributes:", get_available_scalar_attributes(output), flush=True)
    print("\nBrowser checklist (record PASS / FAIL / N/A and evidence):", flush=True)
    for number, check in enumerate(case.checks, 1):
        print(f"  {number:02d}. [ ] {check}", flush=True)
    print("\nNOT COVERED by these fixtures: actual symmetric voltage-sensor sigma-band comparisons,", flush=True)
    print("scenario calculation-status propagation, and network replacement within a session.", flush=True)
    print("Fixtures are illustrative; manual checks are NOT automatically marked as passed.", flush=True)
    print("Stop the server with Ctrl+C before running another case.\n", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", choices=tuple(CASES), default="scalar")
    parser.add_argument("--list", action="store_true", help="List available manual scenarios and exit")
    parser.add_argument("--no-debug", action="store_true", help="Disable Dash debug mode")
    args = parser.parse_args()
    if args.list:
        for case in CASES.values():
            print(f"{case.name:12} {case.description}")
        return
    case = CASES[args.case]
    grid, update_data, output_data = case.build()
    _print_case(case, output_data)
    timestamps = TOPOLOGY_TIMESTAMPS if args.case == "topology" else None
    visualize(
        grid=grid,
        update_data=update_data,
        output_data=output_data,
        debug=not args.no_debug,
        timestamps=timestamps,
    )


if __name__ == "__main__":
    main()
