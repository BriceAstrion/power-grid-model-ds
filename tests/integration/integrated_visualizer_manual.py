# SPDX-FileCopyrightText: Contributors to the Power Grid Model project <powergridmodel@lfenergy.org>
#
# SPDX-License-Identifier: MPL-2.0

"""Manual integrated-visualizer scenarios for F01 and interacting features.

Run from the repository root:
    python -m tests.integration.f01_scalar_heatmap_manual
    python -m tests.integration.f01_scalar_heatmap_manual --list
    python -m tests.integration.f01_scalar_heatmap_manual --case scalar
    python -m tests.integration.f01_scalar_heatmap_manual --case asymmetric
    python -m tests.integration.f01_scalar_heatmap_manual --case topology
    python -m tests.integration.f01_scalar_heatmap_manual --case missing
    python -m tests.integration.f01_scalar_heatmap_manual --case sparse
    python -m tests.integration.f01_scalar_heatmap_manual --case no-output
    python -m tests.integration.f01_scalar_heatmap_manual --case voltage-comparison
    python -m tests.integration.f01_scalar_heatmap_manual --case power-p-comparison
    python -m tests.integration.f01_scalar_heatmap_manual --case power-q-comparison
    python -m tests.integration.f01_scalar_heatmap_manual --case missing-sigma
    python -m tests.integration.f01_scalar_heatmap_manual --case combined-comparison

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
from power_grid_model import AttributeType, ComponentType, DatasetType, MeasuredTerminalType, initialize_array

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


# Issue #378: deterministic sensor comparisons, without running state estimation.
# Power comparison currently supports source terminals only. The comparison
# implementation reads p_sigma/q_sigma, not the legacy power_sigma field.
COMPARISON_TIMESTAMPS = (
    "2026-11-10T09:00:00+01:00",
    "2026-11-10T10:00:00+01:00",
    "2026-11-10T11:00:00+01:00",
    "2026-11-10T12:00:00+01:00",
)


def _append_comparison_sensors(grid, *, voltage=True, power=True, missing_sigma=False):
    """Append sensors with IDs distinct from the coordinated-grid fixtures."""
    updates = {}
    if voltage:
        node_id = int(grid.node.id[0])
        sensor = grid.sym_voltage_sensor.__class__.zeros(1)
        sensor["id"] = 910001
        sensor["measured_object"] = node_id
        sensor["u_measured"] = 400.0
        sensor["u_sigma"] = np.nan if missing_sigma else 2.0
        grid.append(sensor, check_max_id=False)

        arr = initialize_array(DatasetType.update, ComponentType.sym_voltage_sensor, (4, 1))
        arr["id"] = 910001
        arr["u_measured"][:, 0] = [400.0, 405.0, 410.0, 415.0]
        if not missing_sigma:
            arr["u_sigma"][:, 0] = [2.0, 2.0, 3.0, 2.0]
        updates[ComponentType.sym_voltage_sensor] = arr

    if power:
        if not hasattr(MeasuredTerminalType, "source"):
            raise RuntimeError("Installed Power Grid Model does not expose MeasuredTerminalType.source")
        # Add a dedicated source so the fixture does not depend on whether the
        # coordinated grid already contains sources.
        source_id = 910002
        source = grid.source.__class__.zeros(1)
        source["id"] = source_id
        source["node"] = int(grid.node.id[0])
        source["status"] = 1
        source["u_ref"] = 1.0
        grid.append(source, check_max_id=False)

        sensor = grid.sym_power_sensor.__class__.zeros(1)
        sensor["id"] = 910003
        sensor["measured_object"] = source_id
        sensor["measured_terminal_type"] = MeasuredTerminalType.source
        sensor["p_measured"] = [100.0]
        sensor["q_measured"] = [40.0]
        fields = sensor.dtype.names or ()
        for field, value in (("p_sigma", 5.0), ("q_sigma", 2.0)):
            if field not in fields:
                raise RuntimeError(f"Symmetric power sensor schema lacks {field}; cannot test Issue #378")
            sensor[field] = np.nan if missing_sigma else value
        grid.append(sensor, check_max_id=False)

        arr = initialize_array(DatasetType.update, ComponentType.sym_power_sensor, (4, 1))
        arr["id"] = 910003
        arr["p_measured"][:, 0] = [100.0, 105.0, 110.0, 115.0]
        arr["q_measured"][:, 0] = [40.0, 43.0, 46.0, 49.0]
        if not missing_sigma:
            arr["p_sigma"][:, 0] = [5.0, 5.0, 6.0, 5.0]
            arr["q_sigma"][:, 0] = [2.0, 2.0, 3.0, 2.0]
        updates[ComponentType.sym_power_sensor] = arr
    return updates


def _comparison_output(grid, *, voltage=True, power=True):
    output = {}
    if voltage:
        node_id = int(grid.node.id[0])
        arr = initialize_array(DatasetType.sym_output, ComponentType.node, (4, 1))
        arr["id"] = node_id
        arr["u"][:, 0] = [401.0, 404.0, 412.0, 414.0]
        arr["energized"][:, 0] = 1
        output[ComponentType.node] = arr
    if power:
        arr = initialize_array(DatasetType.sym_output, ComponentType.source, (4, 1))
        arr["id"] = 910002
        arr["p"][:, 0] = [101.0, 103.0, 112.0, 114.0]
        arr["q"][:, 0] = [41.0, 42.0, 48.0, 48.0]
        output[ComponentType.source] = arr
    return output


def _case_comparison(*, voltage=True, power=True, missing_sigma=False):
    grid = _grid()
    updates = _append_comparison_sensors(grid, voltage=voltage, power=power, missing_sigma=missing_sigma)
    output = _comparison_output(grid, voltage=voltage, power=power)
    return grid, updates, output


def _case_voltage_comparison():
    return _case_comparison(voltage=True, power=False)


def _case_power_p_comparison():
    return _case_comparison(voltage=False, power=True)


def _case_power_q_comparison():
    return _case_comparison(voltage=False, power=True)


def _case_missing_sigma():
    return _case_comparison(voltage=True, power=True, missing_sigma=True)


def _case_combined_comparison():
    return _case_comparison(voltage=True, power=True)


def _case_integrated():
    """Combine topology, scalar outputs, and both comparison sensor types.

    All data uses four matching scenarios. Values are illustrative, not
    calculated state-estimation results.
    """
    grid = _grid()
    updates = _append_comparison_sensors(grid, voltage=True, power=True)

    # F05: two lines change status across the four observations.
    lines_update = initialize_array(DatasetType.update, ComponentType.line, (4, 2))
    lines_update[AttributeType.id] = np.broadcast_to(grid.line.id[:2], (4, 2))
    lines_update[AttributeType.from_status] = 1
    lines_update[AttributeType.from_status][1, 0] = 0
    lines_update[AttributeType.from_status][3, 1] = 0
    updates[ComponentType.line] = lines_update

    # F01: retain full node and line scalar outputs for quantity selection.
    output = _scalar_output(grid)
    # Issue #378: provide the estimated voltage for the measured node, and
    # estimated p/q at the dedicated source terminal.
    node_id = int(grid.node.id[0])
    node_rows = np.flatnonzero(output[ComponentType.node]["id"][0] == node_id)
    if len(node_rows) != 1:
        raise RuntimeError("Integrated fixture cannot identify the voltage sensor's node")
    output[ComponentType.node]["u"][:, int(node_rows[0])] = [401.0, 404.0, 412.0, 414.0]
    output.update(_comparison_output(grid, voltage=False, power=True))
    return grid, updates, output


COMPARISON_CHECKS = (
    "Select sensor 910001 u_measured; expect measured [400,405,410,415] and calculated [401,404,412,414].",
    "Select sensor 910003 p_measured; expect measured [100,105,110,115] and calculated [101,103,112,114].",
    "Select sensor 910003 q_measured; expect measured [40,43,46,49] and calculated [41,42,48,48].",
    "For available sigma, inspect bands and change multiplier (for example 1, 2, 3); check bands update.",
    "Retain voltage, p and q graphs; select another component; verify retained graphs remain.",
    "Remove one retained graph, clear all, and re-add; verify no duplicates or stale controls.",
    "Check ordinary attribute graph selection and network interactions still work.",
    "Inspect browser console and server terminal for unexpected errors.",
)

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
    "integrated": ManualCase(
        "integrated",
        "Default demonstration: timestamped topology, scalar quantities, voltage and source-terminal p/q comparisons.",
        (
            *COMMON_CHECKS,
            "In Network state, switch between four observation times and inspect the two changing line statuses.",
            "Verify the first line from_status is 1, 0, 1, 1; the second is 1, 1, 1, 0.",
            *COMPARISON_CHECKS,
        ),
        _case_integrated,
    ),
    "voltage-comparison": ManualCase(
        "voltage-comparison",
        "Issue #378: voltage sensor 910001, four measured/estimated scenarios with sigma.",
        (COMPARISON_CHECKS[0], COMPARISON_CHECKS[3], COMPARISON_CHECKS[5], COMPARISON_CHECKS[7]),
        _case_voltage_comparison,
    ),
    "power-p-comparison": ManualCase(
        "power-p-comparison",
        "Issue #378: source-terminal power sensor 910003, active power and sigma.",
        (COMPARISON_CHECKS[1], COMPARISON_CHECKS[3], COMPARISON_CHECKS[5], COMPARISON_CHECKS[7]),
        _case_power_p_comparison,
    ),
    "power-q-comparison": ManualCase(
        "power-q-comparison",
        "Issue #378: source-terminal power sensor 910003, reactive power and sigma.",
        (COMPARISON_CHECKS[2], COMPARISON_CHECKS[3], COMPARISON_CHECKS[5], COMPARISON_CHECKS[7]),
        _case_power_q_comparison,
    ),
    "missing-sigma": ManualCase(
        "missing-sigma",
        "Issue #378: measured/estimated voltage and power with unavailable sigma.",
        (
            "Select voltage u_measured and power p_measured/q_measured; verify both comparison lines appear.",
            "Verify no sigma bands or active sigma controls appear for these selections.",
            COMPARISON_CHECKS[5],
            COMPARISON_CHECKS[7],
        ),
        _case_missing_sigma,
    ),
    "combined-comparison": ManualCase(
        "combined-comparison",
        "Issue #378: voltage, active power and reactive power in the same session.",
        COMPARISON_CHECKS,
        _case_combined_comparison,
    ),
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
    print("\nNOT COVERED: actual state-estimation calculations, scenario-status propagation,", flush=True)
    print("network replacement within a session, or unsupported power-terminal comparisons.", flush=True)
    print("Fixtures are illustrative; manual checks are NOT automatically marked as passed.", flush=True)
    print("Stop the server with Ctrl+C before running another case.\n", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", choices=tuple(CASES), default="integrated")
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
    timestamps = (
        TOPOLOGY_TIMESTAMPS
        if args.case in ("topology", "integrated")
        else COMPARISON_TIMESTAMPS
        if "comparison" in args.case or args.case == "missing-sigma"
        else None
    )
    visualize(
        grid=grid,
        update_data=update_data,
        output_data=output_data,
        debug=not args.no_debug,
        timestamps=timestamps,
    )


if __name__ == "__main__":
    main()
