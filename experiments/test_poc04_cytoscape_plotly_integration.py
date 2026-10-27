"""POC-04 isolated selection integration tests with synthetic PGM datasets.

Tests of the pure callback logic are not end-to-end browser tests of PGM-DS.
"""
import copy

import numpy as np
import pytest

from poc04_cytoscape_plotly_integration import (
    create_app,
    create_demo_elements,
    create_demo_fixture,
    read_arrays_from_server_state,
    render_selection,
    resolve_selection,
)


@pytest.fixture
def datasets():
    return create_demo_fixture()


@pytest.fixture
def elements():
    return create_demo_elements()


def node(elements, node_id):
    return next(element["data"] for element in elements
                if element["data"]["id"] == str(node_id))


def test_tc01_select_node_with_comparison_data(datasets, elements):
    fig, message = render_selection([node(elements, 10)], [], *datasets)
    assert len(fig.data) == 2
    assert list(fig.data[0].y) == [230.0, 231.0, 229.0]
    assert list(fig.data[1].y) == [229.5, 230.5, 228.5]
    assert list(fig.data[0].x) == [0, 1, 2]
    assert "Node 10" in message
    assert "3 matched" in message


def test_tc02_select_different_node(datasets, elements):
    fig, message = render_selection([node(elements, 20)], [], *datasets)
    assert list(fig.data[0].y) == [118.0, 119.0, 117.0]
    assert list(fig.data[1].y) == [118.2, 119.1, 117.2]
    assert "Node 20" in message
    assert "sensor 202" in message


def test_tc03_sequential_selection_uses_current_node(datasets, elements):
    first, _ = render_selection([node(elements, 10)], [], *datasets)
    second, _ = render_selection([node(elements, 20)], [], *datasets)
    third, _ = render_selection([node(elements, 10)], [], *datasets)
    assert list(first.data[0].y) == list(third.data[0].y)
    assert list(first.data[0].y) != list(second.data[0].y)


def test_tc04_clear_selection_returns_empty_state(datasets):
    fig, message = render_selection([], [], *datasets)
    assert len(fig.data) == 0
    assert "Select one network node" in message


def test_tc05_node_without_sensor_returns_no_data(datasets, elements):
    fig, message = render_selection([node(elements, 30)], [], *datasets)
    assert len(fig.data) == 0
    assert "no associated symmetric voltage sensor" in message


def test_tc06_edge_selection_is_not_treated_as_node(datasets, elements):
    edge = next(element["data"] for element in elements if "source" in element["data"])
    fig, message = render_selection([], [edge], *datasets)
    assert len(fig.data) == 0
    assert "not an edge" in message


def test_tc07_datasets_and_elements_not_mutated(datasets, elements):
    original = [array.copy() for array in datasets]
    original_elements = copy.deepcopy(elements)
    render_selection([node(elements, 10)], [], *datasets)
    for current, previous in zip(datasets, original):
        assert current.dtype == previous.dtype
        assert current.shape == previous.shape
        for field in current.dtype.names:
            np.testing.assert_array_equal(current[field], previous[field])
    assert elements == original_elements


def test_tc08_multiple_nodes_do_not_choose_arbitrarily(datasets, elements):
    fig, message = render_selection([node(elements, 10), node(elements, 20)], [], *datasets)
    assert len(fig.data) == 0
    assert "exactly one node" in message


def test_tc09_multiple_voltage_sensors_are_ambiguous(datasets, elements):
    selected = copy.deepcopy(node(elements, 10))
    selected["associated_ids"]["sym_voltage_sensor"].append(999)
    fig, message = render_selection([selected], [], *datasets)
    assert len(fig.data) == 0
    assert "multiple voltage sensors" in message


def test_tc10_sensor_node_mismatch_rejected(datasets, elements):
    selected = copy.deepcopy(node(elements, 10))
    selected["associated_ids"]["sym_voltage_sensor"] = [202]
    fig, message = render_selection([selected], [], *datasets)
    assert len(fig.data) == 0
    assert "does not map to the selected node" in message


def test_tc11_missing_estimate_preserves_gap(datasets, elements):
    sensors, updates, outputs = datasets
    outputs["u"][1, 1] = np.nan  # node 10 in scenario 1
    fig, message = render_selection([node(elements, 10)], [], sensors, updates, outputs)
    assert len(fig.data) == 2
    assert np.isnan(fig.data[1].y[1])
    assert fig.data[1].connectgaps is False
    assert "1 missing estimates" in message


def test_tc12_missing_data_is_not_fabricated(datasets, elements):
    sensors, updates, _ = datasets
    fig, message = render_selection([node(elements, 10)], [], sensors, updates, None)
    assert len(fig.data) == 0
    assert "unavailable" in message


def test_tc13_selected_node_identifier_must_be_consistent(datasets, elements):
    selected = copy.deepcopy(node(elements, 10))
    selected["associated_ids"]["node"] = [20]
    fig, message = render_selection([selected], [], *datasets)
    assert len(fig.data) == 0
    assert "inconsistent" in message


def test_tc14_node_plus_edge_is_ambiguous(datasets, elements):
    edge = next(element["data"] for element in elements if "source" in element["data"])
    fig, message = render_selection([node(elements, 10)], [edge], *datasets)
    assert len(fig.data) == 0
    assert "exactly one node" in message


def test_tc15_dash_callback_has_separate_outputs(elements):
    app = create_app()
    outputs = set()
    inputs = set()
    for meta in app.callback_map.values():
        output = meta["output"]
        if isinstance(output, (list, tuple)):
            outputs.update(f"{o.component_id}.{o.component_property}" for o in output)
        else:
            outputs.add(f"{output.component_id}.{output.component_property}")
        inputs.update(f"{i['id']}.{i['property']}" for i in meta["inputs"])
    assert "poc04-comparison-graph.figure" in outputs
    assert "poc04-comparison-status.children" in outputs
    assert "selection-output.children" not in outputs
    assert "selection-graph.figure" not in outputs
    assert "cytoscape-graph.selectedNodeData" in inputs
    assert "cytoscape-graph.selectedEdgeData" in inputs


def test_tc16_invalid_node_data_is_handled(datasets):
    result = resolve_selection([{"group": "node", "id": "10", "associated_ids": {"node": [10],
                             "sym_voltage_sensor": ["not-an-id"]}}])
    assert result.status == "invalid_selection"
    fig, message = render_selection([{"group": "node", "id": "10", "associated_ids": {"node": [10],
                                   "sym_voltage_sensor": ["not-an-id"]}}], [], *datasets)
    assert len(fig.data) == 0
    assert "invalid" in message
