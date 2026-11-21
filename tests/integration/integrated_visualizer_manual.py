# SPDX-FileCopyrightText: Contributors to the Power Grid Model project <powergridmodel@lfenergy.org>
#
# SPDX-License-Identifier: MPL-2.0

"""Manual integrated-visualizer scenarios for F01 and interacting features.

Run from the repository root:
    python -m tests.integration.integrated_visualizer_manual
    python -m tests.integration.integrated_visualizer_manual --list
    python -m tests.integration.integrated_visualizer_manual --case scalar
    python -m tests.integration.integrated_visualizer_manual --case asymmetric
    python -m tests.integration.integrated_visualizer_manual --case topology
    python -m tests.integration.integrated_visualizer_manual --case missing
    python -m tests.integration.integrated_visualizer_manual --case sparse
    python -m tests.integration.integrated_visualizer_manual --case no-output
    python -m tests.integration.integrated_visualizer_manual --case voltage-comparison
    python -m tests.integration.integrated_visualizer_manual --case power-p-comparison
    python -m tests.integration.integrated_visualizer_manual --case power-q-comparison
    python -m tests.integration.integrated_visualizer_manual --case missing-sigma
    python -m tests.integration.integrated_visualizer_manual --case combined-comparison
    python -m tests.integration.integrated_visualizer_manual --case component-symbols
    python -m tests.integration.integrated_visualizer_manual --validate-symbols

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
from power_grid_model_ds._core.visualizer.generator_constants import (
    GENERATOR_ORIGINAL_HIDDEN_CLASS,
    GENERATOR_SYMBOL_GROUP,
    GENERATOR_VISUAL_PREFIX,
)
from power_grid_model_ds._core.visualizer.layout.generator_rendering import prepare_generator_rendering
from power_grid_model_ds._core.visualizer.layout.load_rendering import prepare_load_rendering
from power_grid_model_ds._core.visualizer.load_constants import (
    LOAD_ORIGINAL_HIDDEN_CLASS,
    LOAD_SYMBOL_GROUP,
    LOAD_VISUAL_PREFIX,
)
from power_grid_model_ds._core.visualizer.scenario_selection import get_scenario_count as get_network_scenario_count
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
        for field, field_info in (arr.dtype.fields or {}).items():
            field_dtype = field_info[0]
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
    for field, field_info in (nodes.dtype.fields or {}).items():
        dtype = field_info[0]
        if field != "id" and dtype.subdtype is None and dtype.kind == "f":
            nodes[field][1, 0] = np.nan
            nodes[field][3, -1] = np.nan
    return grid, None, output


def _case_sparse():
    grid = _grid()
    # Only three nodes have output; other grid elements remain present.
    nodes = initialize_array(DatasetType.sym_output, ComponentType.node, (4, 3))
    nodes[AttributeType.id] = np.broadcast_to(grid.node.id[:3], (4, 3))
    for field, field_info in (nodes.dtype.fields or {}).items():
        dtype = field_info[0]
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
        source_ids = grid.source.id
        arr = initialize_array(DatasetType.sym_output, ComponentType.source, (4, len(source_ids)))
        arr["id"] = source_ids

        source_index = np.flatnonzero(source_ids == 910002)
        if len(source_index) != 1:
            raise RuntimeError("Comparison source 910002 must exist exactly once")

        arr["p"][:, source_index[0]] = [101.0, 103.0, 112.0, 114.0]
        arr["q"][:, source_index[0]] = [41.0, 42.0, 48.0, 48.0]
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


def _case_uncertainty_fluctuation():
    """Eight illustrative scenarios with varying normalized discrepancies."""
    grid = _grid()
    _append_comparison_sensors(grid, voltage=True, power=False)

    measured = np.array([400.0, 402.0, 405.0, 403.0, 408.0, 410.0, 407.0, 411.0])
    sigma = np.array([2.0, 2.0, 2.5, 2.0, 2.5, 2.0, 2.0, 2.5])
    expected_discrepancy = np.array([0.4, 1.6, 0.8, 2.4, 1.2, 0.3, 1.9, 0.7])

    estimated = measured + sigma * expected_discrepancy

    updates = initialize_array(
        DatasetType.update,
        ComponentType.sym_voltage_sensor,
        (8, 1),
    )
    updates["id"] = 910001
    updates["u_measured"][:, 0] = measured
    updates["u_sigma"][:, 0] = sigma

    # Include every grid node to satisfy server-state ID validation.
    node_ids = grid.node.id
    node_count = len(node_ids)

    output = initialize_array(
        DatasetType.sym_output,
        ComponentType.node,
        (8, node_count),
    )
    output["id"] = np.broadcast_to(
        node_ids,
        (8, node_count),
    )

    # The selected sensor measures the first grid node.
    # Assign its estimated voltage across all eight scenarios.
    output["u"][:, 0] = estimated
    output["energized"] = 1

    return (
        grid,
        {ComponentType.sym_voltage_sensor: updates},
        {ComponentType.node: output},
    )


# Deterministic symbol fixtures. Use existing coordinated-grid nodes, so each
# appliance has a real electrical connection rather than an isolated drawing.
SYMBOL_COMPONENTS = (
    ("sym_gen", 920001),
    ("asym_gen", 920002),
    ("sym_load", 920003),
    ("asym_load", 920004),
)


def _append_symbol_components(grid):
    node_ids = [int(value) for value in grid.node.id]
    if len(node_ids) < len(SYMBOL_COMPONENTS):
        raise RuntimeError("Symbol fixture requires at least four electrical nodes")

    for index, (name, component_id) in enumerate(SYMBOL_COMPONENTS):
        original = getattr(grid, name)
        if len(original) and component_id in original.id:
            raise RuntimeError(f"Duplicate test component ID: {component_id}")
        component = original.__class__.zeros(1)
        fields = component.dtype.names or ()
        for required in ("id", "node", "status"):
            if required not in fields:
                raise RuntimeError(f"{name} schema lacks {required}")
        component["id"] = component_id
        component["node"] = node_ids[index]
        component["status"] = 1
        grid.append(component, check_max_id=False)

    _validate_symbol_fixture(grid)


def _validate_symbol_fixture(grid):
    valid_nodes = {int(value) for value in grid.node.id}
    for name, component_id in SYMBOL_COMPONENTS:
        matches = getattr(grid, name)
        matches = matches[matches.id == component_id]
        if len(matches) != 1:
            raise AssertionError(f"Expected exactly one {name} with ID {component_id}")
        if int(matches["node"][0]) not in valid_nodes:
            raise AssertionError(f"{name} {component_id} has no valid electrical node")
        if int(matches["status"][0]) != 1:
            raise AssertionError(f"{name} {component_id} must be connected")
    print("PASS: four connected generator/load fixture components", flush=True)


def _validate_symbol_renderers():
    """Test presentation-element generation without claiming browser rendering."""
    for name, component_id in SYMBOL_COMPONENTS:
        is_generator = name.endswith("gen")
        renderer = prepare_generator_rendering if is_generator else prepare_load_rendering
        prefix = GENERATOR_VISUAL_PREFIX if is_generator else LOAD_VISUAL_PREFIX
        group = GENERATOR_SYMBOL_GROUP if is_generator else LOAD_SYMBOL_GROUP
        hidden = GENERATOR_ORIGINAL_HIDDEN_CLASS if is_generator else LOAD_ORIGINAL_HIDDEN_CLASS
        node_id = f"test_node_{component_id}"
        elements = [
            {"data": {"id": node_id, "group": "node"}, "position": {"x": 100, "y": 200}},
            {"data": {"id": str(component_id), "group": name, "source": node_id}, "classes": ""},
        ]
        result = renderer(elements)
        by_id = {str(item["data"]["id"]): item for item in result}
        if len(by_id) != len(result):
            raise AssertionError(f"Duplicate Cytoscape element IDs for {name}")
        symbol_id = f"{prefix}{component_id}__symbol"
        connection_id = f"{prefix}{component_id}__connection"
        symbol = by_id[symbol_id]
        connection = by_id[connection_id]
        original = by_id[str(component_id)]
        assert symbol["data"]["group"] == group, name
        assert symbol["data"]["visual_only"] is True, name
        assert symbol["data"]["component_id"] == str(component_id), name
        assert symbol["data"]["component_type"] == name, name
        assert connection["data"]["source"] == node_id, name
        assert connection["data"]["target"] == symbol_id, name
        assert connection["data"]["visual_only"] is True, name
        assert hidden in original["classes"].split(), name
        assert symbol["position"]["x"] == (100 if is_generator else 190), name
        assert symbol["position"]["y"] == (100 if is_generator else 200), name
        print(f"PASS: {name} symbol, connection, position and original", flush=True)


def _case_component_symbols():
    grid = _grid()
    _append_symbol_components(grid)
    _validate_symbol_renderers()
    # Supply four illustrative scenarios so the network-state selector is mounted.
    # This is not a substitute for testing the separate no-output layout case.
    return grid, None, _scalar_output(grid)


def _case_integrated():
    """Combine topology, scalar outputs, and both comparison sensor types.

    All data uses four matching scenarios. Values are illustrative, not
    calculated state-estimation results.
    """
    grid = _grid()
    _append_symbol_components(grid)
    _validate_symbol_renderers()
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
    "F15: For a selected voltage comparison, check the separate uncertainty-relative discrepancy graph appears.",
    "F15: Compare discrepancy values against |measured - estimated| / sigma for finite nonzero sigma.",
    (
        "F15/F14: Retain a comparison, select another component, and check whether "
        "the diagnostic follows the intended active selection; record any mismatch as FAIL."
    ),
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

SYMBOL_CHECKS = (
    "Verify sym_gen 920001 and asym_gen 920002 show generator symbols ABOVE their nodes.",
    "Verify sym_load 920003 and asym_load 920004 show load symbols RIGHT of their nodes.",
    "Verify the existing source symbol is visible; inspect source 910002 in the integrated case.",
    "Drag connected nodes and inspect whether symbols and connectors remain correctly aligned.",
    "Toggle appliance visibility and inspect original/visual element behavior.",
    "Select each appliance and check electrical selection and retained graphs remain functional.",
    "Inspect browser console and Dash terminal for rendering errors.",
)


CASES = {
    "uncertainty-fluctuation": ManualCase(
        "uncertainty-fluctuation",
        "F15: eight scenarios with varying uncertainty-relative discrepancies.",
        (
            "Select voltage sensor 910001 and u_measured.",
            "Verify eight observations with scenario indices 0 through 7.",
            "Verify discrepancies [0.4, 1.6, 0.8, 2.4, 1.2, 0.3, 1.9, 0.7].",
            "Verify the 1 sigma reference and hover values.",
            "Verify reference crossings are not labelled as estimator validity.",
        ),
        _case_uncertainty_fluctuation,
    ),
    "component-symbols": ManualCase(
        "component-symbols",
        "Connected symmetric/asymmetric generators and loads with source already in grid.",
        SYMBOL_CHECKS,
        _case_component_symbols,
    ),
    "integrated": ManualCase(
        "integrated",
        "Default demonstration: timestamped topology, scalar quantities, voltage and source-terminal p/q comparisons.",
        (
            *COMMON_CHECKS,
            "In Network state, switch between four observation times and inspect the two changing line statuses.",
            "Verify the first line from_status is 1, 0, 1, 1; the second is 1, 1, 1, 0.",
            *COMPARISON_CHECKS,
            *SYMBOL_CHECKS,
            (
                "F13: Check whether the aggregated agreement overview is available; "
                "verify record counts and status labels against source data, "
                "not an invented agreement score."
            ),
            (
                "F13: If feeder assignment evidence is absent, record feeder-level "
                "agreement verification as NOT TESTED, not PASS."
            ),
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
            "F15: Verify the diagnostic is hidden and a missing-sigma explanation is shown for the active comparison.",
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
        print("Electrical-output scenario count:", get_scenario_count(output), flush=True)
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
    parser.add_argument(
        "--validate-symbols",
        action="store_true",
        help="Validate symbol fixtures and rendering without Dash",
    )
    args = parser.parse_args()
    if args.list:
        for case in CASES.values():
            print(f"{case.name:12} {case.description}")
        return
    if args.validate_symbols:
        _case_component_symbols()
        print("Symbol fixture and element validation passed; browser rendering not checked.")
        return
    case = CASES[args.case]
    grid, update_data, output_data = case.build()
    _print_case(case, output_data)
    network_scenario_count = get_network_scenario_count(update_data, output_data)
    print(f"Network-state scenario count: {network_scenario_count}", flush=True)
    if network_scenario_count is None or network_scenario_count == 0:
        print(
            "WARNING: The current scenario-selection layout omits scenario-selector "
            "when no network scenarios are available; registered Dash callbacks "
            "may report a missing Input. This is a production layout issue.",
            flush=True,
        )
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
