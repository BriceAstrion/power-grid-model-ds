# SPDX-FileCopyrightText: Contributors to the Power Grid Model project <powergridmodel@lfenergy.org>
#
# SPDX-License-Identifier: MPL-2.0

"""Manual acceptance scenarios for the integrated PGM-DS visualizer.

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
    python -m tests.integration.integrated_visualizer_manual --validate-fixtures
    python -m tests.integration.integrated_visualizer_manual --case uncertainty-fluctuation
    python -m tests.integration.integrated_visualizer_manual --case zero-sigma
    python -m tests.integration.integrated_visualizer_manual --case nonfinite-sigma

Each --case starts one blocking Dash visualizer session. Stop the server
(Ctrl+C) before launching another case. The fixtures use illustrative
values; they are not power-flow or state-estimation calculations.

This is a *manual* acceptance harness. --validate-fixtures checks fixture
structure and expected numeric values, not browser rendering. Each UI check
requires a separately recorded PASS / FAIL / NOT TESTED with evidence.
The scenario-status interface is not part of the delivered integration.
"""

import argparse
import json
import sys
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from time import perf_counter

import numpy as np
from power_grid_model import (
    AttributeType,
    CalculationMethod,
    ComponentType,
    DatasetType,
    MeasuredTerminalType,
    initialize_array,
)

from power_grid_model_ds import Grid
from power_grid_model_ds._core.model.constants import EMPTY_ID
from power_grid_model_ds._core.visualizer.electrical_quantity_utils import (
    get_available_scalar_attributes,
    get_scenario_count,
)
from power_grid_model_ds._core.visualizer.electrical_uncertainty import extract_uncertainty_relative_values
from power_grid_model_ds._core.visualizer.feeder_agreement_adapter import prepare_voltage_agreement_overview
from power_grid_model_ds._core.visualizer.feeder_agreement_selection import MeasurementSort, paginate_measurements
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
from power_grid_model_ds._core.visualizer.measurement_comparison import (
    get_measurement_sigma_bounds,
    get_symmetric_power_comparison,
    get_symmetric_voltage_comparison,
)
from power_grid_model_ds._core.visualizer.scenario_selection import get_scenario_count as get_network_scenario_count
from power_grid_model_ds._core.visualizer.uncertainty_diagnostics import get_uncertainty_relative_discrepancy
from power_grid_model_ds.arrays import SymPowerSensorArray, SymVoltageSensorArray
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


def _case_zero_sigma():
    """Four observations: zero sigma is not a valid discrepancy divisor."""
    grid, updates, output = _case_voltage_comparison()
    updates[ComponentType.sym_voltage_sensor]["u_sigma"][:, 0] = [2.0, 0.0, 3.0, 0.0]
    return grid, updates, output


def _case_nonfinite_sigma():
    """Four observations: nonfinite uncertainty must not yield a numeric diagnostic."""
    grid, updates, output = _case_voltage_comparison()
    updates[ComponentType.sym_voltage_sensor]["u_sigma"][:, 0] = [2.0, np.nan, np.inf, 2.0]
    return grid, updates, output


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


# Checks are acceptance instructions, not claims of successful execution.
# A feature can be marked NOT TESTED when the fixture lacks the required data.
QUANTITY_CHECKS = (
    "F01: Select a node/line and supported scalar quantity; verify values, units, heatmap and legend.",
    "F01: Change quantity and component; unavailable attributes must not display stale values.",
    "F01: Select a graphable table cell; verify plotted series and selected component/attribute.",
)
SCENARIO_CHECKS = (
    "Scenario selection: switch 1, 2, 4, then 1; verify selected scenario and network values.",
    "Timestamp selection: only in cases with supplied timestamps, verify displayed time maps to the correct scenario.",
    "Scenario selection: repeated changes must not retain obsolete heatmap colors or legends.",
)
TOPOLOGY_CHECKS = (
    "Topology: first updated line from_status must be [1,0,1,1] over four scenarios.",
    "Topology: second updated line from_status must be [1,1,1,0] over four scenarios.",
    "Topology: inspect network styling and update-data presentation independently; report any mismatch.",
)
WORKSPACE_CHECKS = (
    "Workspace: toggle left and right panels separately and verify each panel's visibility.",
    "Workspace: enter fullscreen and leave it; verify the previous panel visibility is restored.",
    "Workspace: resize/drag network nodes, change scale, toggle appliances and check layout stability.",
    "Workspace: confirm graph and selection controls remain usable after panel toggles.",
)
RETAINED_GRAPH_CHECKS = (
    "F14: Retain graphs for two different components/attributes in the shared workspace.",
    (
        "F14: Change component, scenario and electrical attribute; retained graphs must "
        "remain independently identifiable."
    ),
    "F14: Re-select an already retained graph and check for duplicate prevention.",
    "F14: Remove one graph without removing the others; then clear all and re-add a graph.",
    "F14: Confirm each graph's own remove control and no stale selection or graph content.",
)
VOLTAGE_CHECKS = (
    "Voltage sensor 910001 u_measured: measured [400,405,410,415], estimated [401,404,412,414].",
    "Voltage sigma per scenario: [2,2,3,2]; inspect measurement-centered bands at multiplier 1.",
    "Change sigma multiplier to 2 then 3; bands should change, measured/estimated series should not.",
    "Enter an invalid sigma multiplier; inspect validation and confirm no misleading graph update.",
)
POWER_P_CHECKS = (
    "Source-terminal sensor 910003 p_measured: measured [100,105,110,115], estimated [101,103,112,114].",
    "Active-power sigma per scenario: [5,5,6,5]; verify the correct p_sigma field is used.",
)
POWER_Q_CHECKS = (
    "Source-terminal sensor 910003 q_measured: measured [40,43,46,49], estimated [41,42,48,48].",
    "Reactive-power sigma per scenario: [2,2,3,2]; verify the correct q_sigma field is used.",
)
DIAGNOSTIC_CHECKS = (
    "F15: Select a comparison and verify the separate normalized residual plot appears.",
    "F15: Verify |measured - estimated| / sigma for finite positive sigma, with correct scenario axis.",
    "F15: Inspect hover values and the 1-sigma reference; do not interpret crossings as automatic validity.",
    (
        "F15/F14: Retain a comparison, change the active selection and check the diagnostic "
        "tracks the intended selection."
    ),
    "F15: Select a non-comparison attribute and check that stale diagnostic content is cleared or hidden.",
    "F15: Confirm a retained diagnostic is labeled with the correct sensor ID and measured attribute.",
    "F15: Change the sigma-band multiplier; confirm the normalized discrepancy is not silently rescaled.",
)
# The unified F14/F15 workspace has independent diagnostic and measurement removal.
# These checks require both voltage and power sensors; use the integrated or
# combined-comparison case, not a single-sensor fixture.
INTEGRATED_RETENTION_CHECKS = (
    (
        "F14/F15: Retain voltage sensor 910001 u_measured and power sensor 910003 p_measured; expect "
        "two distinct cards, each with its comparison and diagnostic when available."
    ),
    (
        "F14/F15: Retain q_measured for sensor 910003 as well; p_measured and q_measured must be "
        "distinct retained selections."
    ),
    (
        "F14/F15: Remove only the p_measured diagnostic; its measurement comparison and the other "
        "retained cards must remain."
    ),
    (
        "F14/F15: Re-select p_measured; verify whether its diagnostic is restored without duplicating "
        "its measurement card."
    ),
    (
        "F14/F15: Remove the voltage measurement card; its diagnostic must disappear while both power "
        "measurement cards remain."
    ),
    (
        "F14/F15: Change selected component and scenario; retained cards and their sensor/attribute "
        "labels must remain correct."
    ),
    (
        "F14/F15: Clear all retained graphs; no retained comparison or diagnostic may remain. Re-select "
        "a measurement and confirm recovery."
    ),
    (
        "F14/F15: Inspect browser console and Dash terminal for duplicate-output, missing-component, or "
        "callback errors after removals."
    ),
)

# For this fixture, the known normalized discrepancies are calculated directly
# from the illustrative measurement, estimate and sigma arrays.
INTEGRATED_DIAGNOSTIC_VALUES = (
    "F15 voltage 910001 u_measured: normalized discrepancy [0.5,0.5,0.6666667,0.5] across scenarios 0-3.",
    "F15 power 910003 p_measured: normalized discrepancy [0.2,0.4,0.3333333,0.2] across scenarios 0-3.",
    "F15 power 910003 q_measured: normalized discrepancy [0.5,0.5,0.6666667,0.5] across scenarios 0-3.",
)

SYMBOL_CHECKS = (
    "Symbols: symmetric generator 920001 and asymmetric generator 920002 appear above their nodes.",
    "Symbols: symmetric load 920003 and asymmetric load 920004 appear to the right of their nodes.",
    "Symbols: inspect existing source and two-winding transformer representations where present in the grid.",
    "Symbols: drag connected nodes and check symbol/connector alignment and electrical connections.",
    "Symbols: toggle appliance visibility and confirm originals/visual symbols behave consistently.",
    "Symbols: select components and confirm data/graphs refer to electrical elements, not visual-only nodes.",
)
EDGE_CHECKS = (
    "Missing/unsupported data: do not display fabricated numerical values or misleading validity claims.",
    "After invalid selections, return to valid data and confirm that controls and graphs recover.",
    "Inspect browser console and Dash terminal for unexpected errors; record screenshots and steps.",
)


def _unique_checks(*groups: tuple[str, ...]) -> tuple[str, ...]:
    """Combine checklist groups while preserving order and removing repeated checks."""
    return tuple(dict.fromkeys(check for group in groups for check in group))


COMMON_CHECKS = _unique_checks(QUANTITY_CHECKS, SCENARIO_CHECKS, WORKSPACE_CHECKS, RETAINED_GRAPH_CHECKS, EDGE_CHECKS)
COMPARISON_CHECKS = _unique_checks(
    VOLTAGE_CHECKS,
    POWER_P_CHECKS,
    POWER_Q_CHECKS,
    DIAGNOSTIC_CHECKS,
    RETAINED_GRAPH_CHECKS,
    EDGE_CHECKS,
)


CASES = {
    "integrated": ManualCase(
        "integrated",
        "Four-scenario integration: electrical quantities, topology, timestamps, sensors, symbols and workspace.",
        _unique_checks(
            COMMON_CHECKS,
            TOPOLOGY_CHECKS,
            COMPARISON_CHECKS,
            INTEGRATED_DIAGNOSTIC_VALUES,
            INTEGRATED_RETENTION_CHECKS,
            SYMBOL_CHECKS,
        ),
        _case_integrated,
    ),
    "scalar": ManualCase(
        "scalar", "Symmetric node/line quantities across four scenarios.", COMMON_CHECKS, _case_scalar
    ),
    "asymmetric": ManualCase(
        "asymmetric",
        "Asymmetric node voltage and one de-energized result.",
        _unique_checks(
            (
                "Inspect phase-dependent values and unavailable scalar attributes.",
                "Scenario 2 contains a de-energized node; check its presentation.",
            ),
            WORKSPACE_CHECKS,
            EDGE_CHECKS,
        ),
        _case_asymmetric,
    ),
    "topology": ManualCase(
        "topology",
        "Four scenario-dependent line updates with timestamps.",
        _unique_checks(SCENARIO_CHECKS, TOPOLOGY_CHECKS, WORKSPACE_CHECKS, RETAINED_GRAPH_CHECKS, EDGE_CHECKS),
        _case_topology,
    ),
    "missing": ManualCase(
        "missing",
        "NaN output values in scenarios 2 and 4.",
        _unique_checks(
            (
                "Inspect missing-value color/legend; no fabricated values.",
                "Switch between valid and missing scenarios and verify recovery.",
            ),
            COMMON_CHECKS,
        ),
        _case_missing,
    ),
    "sparse": ManualCase(
        "sparse",
        "Only three nodes have calculation output.",
        _unique_checks(("Inspect nodes without output and unavailable line quantities.",), COMMON_CHECKS),
        _case_sparse,
    ),
    "no-output": ManualCase(
        "no-output",
        "Grid with no calculation output.",
        _unique_checks(
            (
                "No calculated-value heatmap, graph, sigma controls or stale diagnostic should be shown.",
                "Check network selection, dragging and appliance visibility without output.",
            ),
            EDGE_CHECKS,
        ),
        _case_no_output,
    ),
    "voltage-comparison": ManualCase(
        "voltage-comparison",
        "Voltage measurement, estimate, sigma bands and F15 diagnostic.",
        _unique_checks(VOLTAGE_CHECKS, DIAGNOSTIC_CHECKS, RETAINED_GRAPH_CHECKS, EDGE_CHECKS),
        _case_voltage_comparison,
    ),
    "power-p-comparison": ManualCase(
        "power-p-comparison",
        "Source-terminal active power measurement and estimate.",
        _unique_checks(POWER_P_CHECKS, DIAGNOSTIC_CHECKS, RETAINED_GRAPH_CHECKS, EDGE_CHECKS),
        _case_power_p_comparison,
    ),
    "power-q-comparison": ManualCase(
        "power-q-comparison",
        "Source-terminal reactive power measurement and estimate.",
        _unique_checks(POWER_Q_CHECKS, DIAGNOSTIC_CHECKS, RETAINED_GRAPH_CHECKS, EDGE_CHECKS),
        _case_power_q_comparison,
    ),
    "combined-comparison": ManualCase(
        "combined-comparison",
        "Voltage and source-terminal active/reactive power in one session.",
        _unique_checks(COMPARISON_CHECKS, INTEGRATED_DIAGNOSTIC_VALUES, INTEGRATED_RETENTION_CHECKS, WORKSPACE_CHECKS),
        _case_combined_comparison,
    ),
    "missing-sigma": ManualCase(
        "missing-sigma",
        "Voltage and power comparison with unavailable sigma.",
        _unique_checks(
            (
                "Measured and estimated series should still be inspectable.",
                "No misleading sigma bands or enabled multiplier control for missing sigma.",
                "F15: diagnostic is hidden or explains missing sigma for the active comparison.",
            ),
            RETAINED_GRAPH_CHECKS,
            EDGE_CHECKS,
        ),
        _case_missing_sigma,
    ),
    "zero-sigma": ManualCase(
        "zero-sigma",
        "Voltage comparison with zero sigma in scenarios 2 and 4.",
        _unique_checks(
            (
                "Inspect scenarios 2 and 4: zero sigma must not produce infinity or a fabricated discrepancy.",
                "Check the diagnostic explanation/omission and unaffected finite-sigma observations.",
            ),
            EDGE_CHECKS,
        ),
        _case_zero_sigma,
    ),
    "nonfinite-sigma": ManualCase(
        "nonfinite-sigma",
        "Voltage comparison with NaN and infinite sigma.",
        _unique_checks(
            (
                "Inspect scenarios 2 (NaN) and 3 (infinite): no misleading numeric discrepancy.",
                "Check available finite-sigma observations and any diagnostic status message.",
            ),
            EDGE_CHECKS,
        ),
        _case_nonfinite_sigma,
    ),
    "uncertainty-fluctuation": ManualCase(
        "uncertainty-fluctuation",
        "Eight voltage observations with known F15 normalized discrepancies.",
        _unique_checks(
            (
                "Select voltage sensor 910001 u_measured; expect scenario indices 0 through 7.",
                "Expected |estimated-measured|/sigma: [0.4,1.6,0.8,2.4,1.2,0.3,1.9,0.7].",
                "Inspect 1-sigma reference, hover values and crossings without automatic validity labels.",
            ),
            RETAINED_GRAPH_CHECKS,
            EDGE_CHECKS,
        ),
        _case_uncertainty_fluctuation,
    ),
    "component-symbols": ManualCase(
        "component-symbols",
        "Connected symmetric/asymmetric generators and loads.",
        _unique_checks(SYMBOL_CHECKS, WORKSPACE_CHECKS, EDGE_CHECKS),
        _case_component_symbols,
    ),
}


def _validate_fixture(case_name, grid, updates, output):
    """Check deterministic fixture invariants; never claim UI acceptance."""
    count = get_network_scenario_count(updates, output)
    if output is not None:
        output_count = get_scenario_count(output)
        if count != output_count:
            raise AssertionError(f"{case_name}: output scenario count mismatch")
    if case_name in {"topology", "integrated"}:
        lines = updates[ComponentType.line]
        np.testing.assert_array_equal(lines["from_status"][:, 0], [1, 0, 1, 1])
        np.testing.assert_array_equal(lines["from_status"][:, 1], [1, 1, 1, 0])
    if case_name in {"integrated", "combined-comparison"}:
        voltage = updates[ComponentType.sym_voltage_sensor]
        power = updates[ComponentType.sym_power_sensor]
        node = output[ComponentType.node]
        source = output[ComponentType.source]
        voltage_id = int(grid.node.id[0])
        voltage_column = np.flatnonzero(node["id"][0] == voltage_id)
        source_column = np.flatnonzero(source["id"][0] == 910002)
        if len(voltage_column) != 1 or len(source_column) != 1:
            raise AssertionError(f"{case_name}: expected exactly one measured node and source")
        for measured, estimated, sigma, expected in (
            (
                voltage["u_measured"][:, 0],
                node["u"][:, voltage_column[0]],
                voltage["u_sigma"][:, 0],
                [0.5, 0.5, 2 / 3, 0.5],
            ),
            (
                power["p_measured"][:, 0],
                source["p"][:, source_column[0]],
                power["p_sigma"][:, 0],
                [0.2, 0.4, 1 / 3, 0.2],
            ),
            (
                power["q_measured"][:, 0],
                source["q"][:, source_column[0]],
                power["q_sigma"][:, 0],
                [0.5, 0.5, 2 / 3, 0.5],
            ),
        ):
            np.testing.assert_allclose(np.abs(measured - estimated) / sigma, expected, rtol=0, atol=1e-10)
    if case_name == "uncertainty-fluctuation":
        if output is None:
            raise AssertionError(f"{case_name}: missing output data")
        sensor = updates[ComponentType.sym_voltage_sensor]
        measured = sensor["u_measured"][:, 0]
        sigma = sensor["u_sigma"][:, 0]
        estimated = output[ComponentType.node]["u"][:, 0]
        np.testing.assert_allclose(
            np.abs(measured - estimated) / sigma,
            [0.4, 1.6, 0.8, 2.4, 1.2, 0.3, 1.9, 0.7],
            rtol=0,
            atol=1e-10,
        )
    if case_name == "zero-sigma":
        np.testing.assert_array_equal(updates[ComponentType.sym_voltage_sensor]["u_sigma"][:, 0], [2, 0, 3, 0])
    if case_name == "nonfinite-sigma":
        sigma = updates[ComponentType.sym_voltage_sensor]["u_sigma"][:, 0]
        if not (np.isnan(sigma[1]) and np.isinf(sigma[2])):
            raise AssertionError("Expected NaN and infinite sigma")
    if case_name in {"component-symbols", "integrated"}:
        _validate_symbol_fixture(grid)
    print(f"PASS: fixture structure for {case_name} (browser not checked)", flush=True)


def _validate_all_fixtures():
    for case in CASES.values():
        grid, updates, output = case.build()
        _validate_fixture(case.name, grid, updates, output)
    print(f"Validated {len(CASES)} fixture cases; no browser acceptance assertions performed.")


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
    parser.add_argument(
        "--case",
        choices=(*CASES, "calculated", "f13-agreement", "f13-pagination", "f13-scalability", "f13-missing"),
        default="integrated",
    )
    parser.add_argument("--list", action="store_true", help="List available manual scenarios and exit")
    parser.add_argument("--no-debug", action="store_true", help="Disable Dash debug mode")
    parser.add_argument("--validate-fixtures", action="store_true", help="Check all fixtures without launching Dash")
    parser.add_argument(
        "--validate-symbols",
        action="store_true",
        help="Validate symbol fixtures and rendering without Dash",
    )
    parser.add_argument("--nodes", type=int, default=100)
    parser.add_argument("--days", type=int, default=2)
    parser.add_argument("--step-minutes", type=int, default=15)
    parser.add_argument("--records", type=int)
    parser.add_argument("--port", type=int, default=8050)
    parser.add_argument("--generator-dir", type=Path)
    parser.add_argument("--verify-only", action="store_true")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    if args.nodes < 2 or args.days < 1 or args.step_minutes < 1 or 60 % args.step_minutes:
        parser.error("Require nodes >= 2, days >= 1 and a positive divisor of 60 for step-minutes")
    if not 1 <= args.port <= 65535 or (args.records is not None and args.records < 1):
        parser.error("Invalid port or record count")
    if args.case not in CASES and not (args.list or args.validate_fixtures or args.validate_symbols):
        run_extended_case(args)
        return
    if args.list:
        for case in CASES.values():
            print(f"{case.name:12} {case.description}")
        print("Additional cases: calculated, f13-agreement, f13-pagination, f13-scalability, f13-missing")
        return
    if args.validate_fixtures:
        _validate_all_fixtures()
        return
    if args.validate_symbols:
        _case_component_symbols()
        print("Symbol fixture and element validation passed; browser rendering not checked.")
        return
    case = CASES[args.case]
    grid, update_data, output_data = case.build()
    _validate_fixture(case.name, grid, update_data, output_data)
    _print_case(case, output_data)
    if args.verify_only:
        return
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
        if args.case
        in {
            "voltage-comparison",
            "power-p-comparison",
            "power-q-comparison",
            "combined-comparison",
            "missing-sigma",
            "zero-sigma",
            "nonfinite-sigma",
        }
        else None
    )
    visualize(
        grid=grid,
        update_data=update_data,
        output_data=output_data,
        debug=not args.no_debug,
        port=args.port,
        timestamps=timestamps,
    )


# Extended acceptance cases. Generator seeds retained from the shared dataset.
GRID_SEED = 20260522
PROFILE_SEED = 20260523
MEASUREMENT_SEED = 20260524


def attach_sensors(grid, sensor_input):
    """Copy calculation sensor definitions into native PGM-DS arrays."""
    for component, array_type in (
        (ComponentType.sym_voltage_sensor, SymVoltageSensorArray),
        (ComponentType.sym_power_sensor, SymPowerSensorArray),
    ):
        records = sensor_input[component]
        sensors = array_type.empty(len(records))
        for field in sensors.columns:
            if field in records.dtype.names:
                sensors[field] = records[field]
        grid.append(sensors)
        np.testing.assert_array_equal(getattr(grid, component.value).id, records["id"])
        np.testing.assert_array_equal(
            getattr(grid, component.value).measured_object,
            records["measured_object"],
        )
        print(f"PASS | Attached {len(sensors)} {component.value} definitions")
    grid.check_ids()


def generate_dataset(nr_nodes, nr_days, step_minutes, generator_dir):
    """Generate synthetic measurements and state-estimation results."""
    if generator_dir is None or not generator_dir.is_dir():
        raise ValueError("Supply --generator-dir pointing to power-grid-model-ai/tests/data")
    sys.path.insert(0, str(generator_dir.resolve()))
    # External generator location is supplied at runtime by --generator-dir.
    from _generate_synthetic_pgm_state_estimation_data import (  # noqa: PLC0415
        create_state_estimation_sensor_input,
        create_state_estimation_sensor_update_data,
        run_power_flow_truth,
        run_state_estimation,
        validate_datasets,
    )
    from _synthetic_pgm_common import create_synthetic_input_data, create_synthetic_load_update_data  # noqa: PLC0415

    scenario_count = nr_days * 24 * (60 // step_minutes)

    print("\n=== Dataset configuration ===")
    print("Target nodes:", nr_nodes)
    print("Days:", nr_days)
    print("Step minutes:", step_minutes)
    print("Requested scenarios:", scenario_count)

    start = perf_counter()

    grid, base_input = create_synthetic_input_data(
        nr_nodes=nr_nodes,
        nr_sources=1,
        nr_nops=0,
        seed=GRID_SEED,
        create_10_3_kv_net=False,
    )

    load_updates = create_synthetic_load_update_data(
        input_data=base_input,
        n_steps=scenario_count,
        step_minutes=step_minutes,
        seed=PROFILE_SEED,
    )

    truth_output = run_power_flow_truth(
        input_data=base_input,
        load_update_data=load_updates,
        calculation_method=CalculationMethod.newton_raphson,
    )

    sensor_input, sensor_metadata = create_state_estimation_sensor_input(
        input_data=base_input,
        truth_output_data=truth_output,
        measurement_seed=MEASUREMENT_SEED,
        voltage_relative_sigma=0.005,
        voltage_sigma_floor=5.0,
        power_relative_sigma=0.02,
        power_sigma_floor=50.0,
    )

    sensor_updates = create_state_estimation_sensor_update_data(
        input_data=sensor_input,
        truth_output_data=truth_output,
        sensor_metadata=sensor_metadata,
        measurement_seed=MEASUREMENT_SEED,
    )

    update_data = dict(load_updates)
    update_data.update(sensor_updates)

    validate_datasets(
        input_data=sensor_input,
        update_data=update_data,
    )

    attach_sensors(grid, sensor_input)

    preparation_time = perf_counter() - start

    calculation_start = perf_counter()

    output_data = run_state_estimation(
        input_data=sensor_input,
        update_data=update_data,
        calculation_method=CalculationMethod.iterative_linear,
    )

    calculation_time = perf_counter() - calculation_start

    print("\n=== Dataset generation completed ===")
    print("Actual grid nodes:", len(grid.node))
    print("Actual grid lines:", len(grid.line))
    print("Actual grid loads:", len(grid.sym_load))
    print("Voltage sensors in calculation input:", len(sensor_input[ComponentType.sym_voltage_sensor]))
    print("Power sensors in calculation input:", len(sensor_input[ComponentType.sym_power_sensor]))
    print(f"Preparation time: {preparation_time:.3f} s")
    print(f"State-estimation calculation time: {calculation_time:.3f} s")

    return grid, update_data, output_data, scenario_count


def build_controlled_dataset():
    """Reproduce the F13 integration-test dataset."""
    grid = Grid.empty()

    nodes = grid.node.__class__(
        id=[1, 2, 6],
        u_rated=[10500.0, 10500.0, 10500.0],
        feeder_branch_id=[201, 201, int(EMPTY_ID)],
    )
    grid.append(nodes, check_max_id=False)

    sensors = grid.sym_voltage_sensor.__class__.empty(3)
    sensors.id = np.array([11, 12, 13], dtype=np.int32)
    sensors.measured_object = np.array([1, 2, 6], dtype=np.int32)
    sensors.u_measured = np.array(
        [10489.37, 9997.32, 10102.01],
        dtype=np.float64,
    )
    sensors.u_sigma = np.array([1.0, 1.0, 1.0], dtype=np.float64)
    grid.append(sensors, check_max_id=False)

    sensor_updates = initialize_array(
        DatasetType.update,
        ComponentType.sym_voltage_sensor,
        (2, 3),
    )
    sensor_updates[AttributeType.id] = [11, 12, 13]
    sensor_updates[AttributeType.u_measured] = [
        [10489.37, 9997.32, 10102.01],
        [10490.0, 10010.0, 10120.0],
    ]

    node_outputs = initialize_array(
        DatasetType.sym_output,
        ComponentType.node,
        (2, 3),
    )
    node_outputs[AttributeType.id] = [1, 2, 6]
    node_outputs[AttributeType.u] = [
        [10488.0, 10000.0, 10100.0],
        [10491.0, 10008.0, 10119.0],
    ]
    node_outputs[AttributeType.energized] = 1

    update_data = {
        ComponentType.sym_voltage_sensor: sensor_updates,
    }
    output_data = {
        ComponentType.node: node_outputs,
    }

    return grid, update_data, output_data


def build_pagination_dataset(count):
    """Use the original three nodes with distinct synthetic sensor readings."""
    _, _, output_data = build_controlled_dataset()

    # Rebuild the grid to avoid retaining the original three sensors.
    grid = Grid.empty()
    nodes = grid.node.__class__(
        id=[1, 2, 6],
        u_rated=[10500.0, 10500.0, 10500.0],
        feeder_branch_id=[201, 201, int(EMPTY_ID)],
    )
    grid.append(nodes, check_max_id=False)
    indices = np.arange(count, dtype=np.int32)
    sensor_ids = indices + 11
    node_indices = indices % 3
    node_ids = np.array([1, 2, 6], dtype=np.int32)[node_indices]
    estimates = output_data[ComponentType.node][AttributeType.u][:, node_indices]
    measured = estimates + (indices + 1) * np.array([[1.0], [2.0]])
    sensors = grid.sym_voltage_sensor.__class__.empty(count)
    sensors.id = sensor_ids
    sensors.measured_object = node_ids
    sensors.u_measured = measured[0].copy()
    sensors.u_sigma = np.ones(count, dtype=np.float64)
    grid.append(sensors, check_max_id=False)
    updates = initialize_array(DatasetType.update, ComponentType.sym_voltage_sensor, (2, count))
    updates[AttributeType.id] = sensor_ids
    updates[AttributeType.u_measured] = measured
    return grid, {ComponentType.sym_voltage_sensor: updates}, output_data


def result_key(component, sensor_id, attribute, scenario):
    return f"{component.value}:{sensor_id}:{attribute}:{scenario}"


def finite_or_none(value):
    if value is None or not np.isfinite(value):
        return None
    return float(value)


def get_sensor_groups(grid):
    voltage_ids = [int(sensor_id) for sensor_id in grid.sym_voltage_sensor.id]

    source_mask = grid.sym_power_sensor.measured_terminal_type == MeasuredTerminalType.source.value

    power_ids = [int(sensor_id) for sensor_id in grid.sym_power_sensor.id[source_mask]]

    assert voltage_ids
    assert power_ids

    return [
        (
            ComponentType.sym_voltage_sensor,
            "u_residual",
            voltage_ids,
        ),
        (
            ComponentType.sym_power_sensor,
            "p_residual",
            power_ids,
        ),
        (
            ComponentType.sym_power_sensor,
            "q_residual",
            power_ids,
        ),
    ]


def extract_f01(grid, updates, output, groups, scenarios):
    results = {}

    for component, attribute, sensor_ids in groups:
        for scenario in scenarios:
            ratios = extract_uncertainty_relative_values(
                grid,
                updates,
                output,
                (component, attribute),
                scenario,
            )

            for sensor_id in sensor_ids:
                key = result_key(
                    component,
                    sensor_id,
                    attribute,
                    scenario,
                )

                results[key] = finite_or_none(ratios.get(sensor_id))

    return results


def extract_f15(grid, updates, output, groups, scenarios):
    count = get_scenario_count(output)

    results = {}

    for component, attribute, sensor_ids in groups:
        for sensor_id in sensor_ids:
            if component == ComponentType.sym_voltage_sensor:
                comparison = get_symmetric_voltage_comparison(
                    grid,
                    updates,
                    output,
                    sensor_id,
                )
            else:
                comparison = get_symmetric_power_comparison(
                    grid,
                    updates,
                    output,
                    sensor_id,
                    f"{attribute[0]}_measured",
                )

            assert comparison is not None

            np.testing.assert_array_equal(
                comparison.scenario_indices,
                np.arange(count),
            )

            ratios = get_uncertainty_relative_discrepancy(comparison)

            assert ratios.shape == (count,)

            for scenario in scenarios:
                key = result_key(
                    component,
                    sensor_id,
                    attribute,
                    scenario,
                )

                results[key] = finite_or_none(ratios[scenario])

    return results


F13_CHECKS = (
    "F13: Verify network and feeder counts, minimum, mean and maximum against printed references.",
    "F13: Select network, feeder and unassigned scopes; inspect contributing sensor identities.",
    "F13: Sort largest, smallest and sensor ID; expand cards and verify measured and estimated values.",
    "F13: For more than five records, navigate numbered pages, first/last and ellipses where applicable.",
    "F13: Switch scenario and scope; verify page resets and no stale records.",
    "F13: Missing pairs remain identifiable and do not contribute to statistics.",
    "F13: Check keyboard focus, readable counts and panel layout at different desktop widths.",
)


def agreement_sort_key(sensor_id, mode, expected):
    value = expected[sensor_id][1]
    if mode == MeasurementSort.SENSOR:
        return (sensor_id,)
    return (value is None, 0 if value is None else (-value if mode == MeasurementSort.LARGEST else value), sensor_id)


def agreement_reference(sensors, feeders, updates, output, scenario):
    rows = output[ComponentType.node][scenario]
    estimates = {int(row["id"]): float(row["u"]) for row in rows}
    changes = {int(row["id"]): float(row["u_measured"]) for row in updates[ComponentType.sym_voltage_sensor][scenario]}
    groups = {"network": [], "unassigned": []}
    expected = {}
    for raw_sid, raw_nid, base in zip(sensors.id, sensors.measured_object, sensors.u_measured, strict=True):
        sid, nid = int(raw_sid), int(raw_nid)
        measured = changes.get(sid, float(base))
        if np.isnan(measured):
            measured = float(base)
        estimated = estimates.get(nid, np.nan)
        matched = nid in feeders and nid != int(EMPTY_ID)
        status = (
            "unmatched"
            if not matched
            else "missing_measurement"
            if not np.isfinite(measured)
            else "missing_estimate"
            if not np.isfinite(estimated)
            else "available"
        )
        difference = abs(estimated - measured) if status == "available" else None
        feeder = feeders.get(nid, int(EMPTY_ID)) if matched else int(EMPTY_ID)
        scope = "unassigned" if feeder == int(EMPTY_ID) else str(feeder)
        expected[sid] = (status, difference)
        groups["network"].append(sid)
        groups.setdefault(scope, []).append(sid)
    return groups, expected


def verify_agreement_scope(group, ids, expected):
    assert {r.sensor_id for r in group.records} == set(ids)
    values = [expected[sid][1] for sid in ids if expected[sid][1] is not None]
    assert group.total_count == len(ids)
    assert group.available_count == len(values)
    assert group.unavailable_count == len(ids) - len(values)
    for record in group.records:
        status, difference = expected[record.sensor_id]
        assert record.status.value == status
        if difference is None:
            assert record.absolute_discrepancy is None
        else:
            np.testing.assert_allclose(record.absolute_discrepancy, difference)
    stats = group.discrepancy_statistics()
    reference = [float(np.min(values)), float(np.mean(values)), float(np.max(values))] if values else [None] * 3
    if values:
        np.testing.assert_allclose([stats.minimum, stats.mean, stats.maximum], reference)
    else:
        assert [stats.minimum, stats.mean, stats.maximum] == reference
    for mode in MeasurementSort:
        ordered = sorted(ids, key=lambda sid, mode=mode: agreement_sort_key(sid, mode, expected))
        for index in {0, max(0, (len(ids) - 1) // 5)}:
            page = paginate_measurements(group, sort_mode=mode, page_index=index)
            assert [r.sensor_id for r in page.records] == ordered[index * 5 : index * 5 + 5]
    return reference, len(values)


def verify_agreement(grid, updates, output, scenarios):
    """Independent ID-based reference from raw arrays, not production records."""
    results = []
    feeders = dict(zip(map(int, grid.node.id), map(int, grid.node.feeder_branch_id), strict=True))
    sensors = grid.sym_voltage_sensor
    for scenario in scenarios:
        groups, expected = agreement_reference(sensors, feeders, updates, output, scenario)
        overview = prepare_voltage_agreement_overview(
            grid=grid, update_data=updates, output_data=output, scenario_index=scenario
        )
        actual = {"network": overview.network, "unassigned": overview.unassigned}
        actual.update({str(key): group for key, group in overview.feeders.items()})
        assert actual.keys() == groups.keys()
        for scope, ids in groups.items():
            reference, available = verify_agreement_scope(actual[scope], ids, expected)
            row = {
                "scenario": scenario,
                "scope": scope,
                "total": len(ids),
                "available": available,
                "min_mean_max": reference,
            }
            results.append(row)
            print("PASS F13", row)
    return results


def verify_calculated_comparisons(grid, updates, output, scenarios):
    groups = get_sensor_groups(grid)
    f01 = extract_f01(grid, updates, output, groups, scenarios)
    f15 = extract_f15(grid, updates, output, groups, scenarios)
    assert f01.keys() == f15.keys()
    for key, value in f01.items():
        if value is None:
            assert f15[key] is None
        else:
            np.testing.assert_allclose(value, f15[key], rtol=1e-7, atol=1e-7)
    checked = 0
    for component, attribute, ids in groups:
        sensors = getattr(grid, component.value)
        quantity = attribute[0]
        target = ComponentType.node if quantity == "u" else ComponentType.source
        for sid in ids:
            i = int(np.flatnonzero(sensors.id == sid)[0])
            comparison = (
                get_symmetric_voltage_comparison(grid, updates, output, sid)
                if quantity == "u"
                else get_symmetric_power_comparison(grid, updates, output, sid, quantity + "_measured")
            )
            assert comparison is not None
            ratios = get_uncertainty_relative_discrepancy(comparison)
            for scenario in scenarios:
                rows = updates[component][scenario]
                row = rows[rows["id"] == sid][0]
                estimates = output[target][scenario]
                estimate = float(estimates[estimates["id"] == sensors.measured_object[i]][quantity][0])
                measured = float(row[quantity + "_measured"])
                sigma = float(sensors[quantity + "_sigma"][i])
                if quantity + "_sigma" in row.dtype.names and not np.isnan(row[quantity + "_sigma"]):
                    sigma = float(row[quantity + "_sigma"])
                assert np.isfinite(sigma)
                assert sigma > 0
                np.testing.assert_allclose(
                    [comparison.measured[scenario], comparison.estimated[scenario], comparison.sigma[scenario]],
                    [measured, estimate, sigma],
                )
                expected = abs(estimate - measured) / sigma
                np.testing.assert_allclose(ratios[scenario], expected, rtol=1e-7, atol=1e-7)
                np.testing.assert_allclose(
                    f01[result_key(component, sid, attribute, scenario)], expected, rtol=1e-7, atol=1e-7
                )
                for multiplier in (1, 2, 3):
                    lower, upper = get_measurement_sigma_bounds(comparison, multiplier)
                    np.testing.assert_allclose(
                        [lower[scenario], upper[scenario]],
                        [measured - multiplier * sigma, measured + multiplier * sigma],
                    )
                checked += 1
        print("PASS calculated comparison", attribute, "sensors", len(ids), "sampled scenarios", scenarios)
    assert checked > 0
    return {"sampled_comparisons": checked, "f01_f15_matches": len(f01)}


def run_extended_case(args):
    start = perf_counter()
    if args.case == "calculated":
        grid, updates, output, count = generate_dataset(args.nodes, args.days, args.step_minutes, args.generator_dir)
        step = args.step_minutes
    else:
        records = (
            args.records
            if args.records is not None
            else {"f13-agreement": 12, "f13-pagination": 65, "f13-scalability": 50000, "f13-missing": 12}[args.case]
        )
        grid, updates, output = build_controlled_dataset() if records == 3 else build_pagination_dataset(records)
        if args.case == "f13-missing":
            updates[ComponentType.sym_voltage_sensor]["u_measured"][0, 0] = np.inf
            output[ComponentType.node]["u"][1, 0] = np.nan
        count, step = 2, args.step_minutes
    preparation = perf_counter() - start
    assert get_scenario_count(output) == count
    scenarios = sorted({0, (count - 1) // 2, count - 1})
    start = perf_counter()
    agreement = verify_agreement(grid, updates, output, scenarios)
    comparisons = verify_calculated_comparisons(grid, updates, output, scenarios) if args.case == "calculated" else None
    checks = (
        _unique_checks(
            COMMON_CHECKS,
            F13_CHECKS,
            DIAGNOSTIC_CHECKS,
            (
                "Retain distinct voltage and source power comparisons; remove diagnostics and cards independently.",
                "Check sigma multipliers 1, 2 and 3 against reference values.",
            ),
        )
        if args.case == "calculated"
        else F13_CHECKS
    )
    report = {
        "case": args.case,
        "nodes": len(grid.node),
        "scenarios": count,
        "sampled_scenarios": scenarios,
        "preparation_seconds": preparation,
        "verification_seconds": perf_counter() - start,
        "agreement": agreement,
        "comparisons": comparisons,
        "browser_checks": [{"check": c, "status": "NOT TESTED"} for c in checks],
    }
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2, allow_nan=False), encoding="utf-8")
    print("PASS: sampled numerical verification; browser not tested")
    for check in checks:
        print("[ ]", check)
    if not args.verify_only:
        origin = datetime(2026, 1, 1, tzinfo=UTC)
        timestamps = tuple((origin + timedelta(minutes=step * i)).isoformat() for i in range(count))
        visualize(
            grid=grid, update_data=updates, output_data=output, debug=False, port=args.port, timestamps=timestamps
        )


if __name__ == "__main__":
    main()
