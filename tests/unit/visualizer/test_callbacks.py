# SPDX-FileCopyrightText: 2025 Contributors to the Power Grid Model project <powergridmodel@lfenergy.org>
#
# SPDX-License-Identifier: MPL-2.0

from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from dash import html, no_update
from dash.exceptions import PreventUpdate
from plotly import graph_objs as go
from power_grid_model import ComponentType, initialize_array

from power_grid_model_ds._core.model.dtypes.typing import NDArray3
from power_grid_model_ds._core.model.grids.base import Grid
from power_grid_model_ds._core.visualizer import server_state
from power_grid_model_ds._core.visualizer.callbacks.config import (
    scale_elements,
    update_arrows,
    update_layout,
)
from power_grid_model_ds._core.visualizer.callbacks.element_selection import (
    _attribute_value_button,
    _matches,
    cell_selection_graph,
    display_selected_elements,
    store_selected_cell,
    toggle_attribute_filter,
    update_attribute_values,
)
from power_grid_model_ds._core.visualizer.callbacks.search_form import HIGHLIGHT_STYLE, search_element
from power_grid_model_ds._core.visualizer.layout.cytoscape_styling import DEFAULT_STYLESHEET
from power_grid_model_ds._core.visualizer.layout.selection_output import SELECTION_OUTPUT_HTML
from power_grid_model_ds.arrays import NodeArray

_EDGE_INDEX = 3

_CTX_PATH = "power_grid_model_ds._core.visualizer.callbacks.element_selection.callback_context"
_CALLBACK_PATH = "power_grid_model_ds._core.visualizer.callbacks.element_selection"

_NODE_SELECTION = {
    "group": "node",
    "id": 1,
    "column": "u_rated",
}

_VOLTAGE_SELECTION = {
    "group": "sym_voltage_sensor",
    "id": 101,
    "column": "u_measured",
}


class ThreePhaseNodeArray(NodeArray):
    three_phase_quantity: NDArray3[np.float64]


class ThreePhaseGrid(Grid):
    node: ThreePhaseNodeArray


def test_scale_elements():
    original = deepcopy(DEFAULT_STYLESHEET)

    stored, displayed = scale_elements(
        node_scale=1.2,
        edge_scale=1.3,
        stored_stylesheet=original,
        current_stylesheet=original,
    )

    assert stored == displayed
    assert stored != original
    assert original == DEFAULT_STYLESHEET


def test_search_element_no_input():
    with pytest.raises(PreventUpdate):
        search_element(
            group="",
            column="",
            operator="",
            value="",
            stylesheet=DEFAULT_STYLESHEET,
        )


def test_search_element_with_asym_column():
    server_state.set_app_state(Grid.empty())

    with pytest.raises(PreventUpdate):
        search_element(
            group="asym_gen",
            column="p_specified",
            operator="=",
            value="100",
            stylesheet=DEFAULT_STYLESHEET,
        )


@pytest.mark.parametrize(
    ("group", "column", "operator", "value", "expected_selectors"),
    [
        pytest.param(
            "node",
            "id",
            "=",
            "1",
            [{"selector": "#1", "style": HIGHLIGHT_STYLE}],
            id="node id equal",
        ),
        pytest.param(
            "branches",
            "id",
            "!=",
            "12",
            [{"selector": "#23", "style": HIGHLIGHT_STYLE}],
            id="branch id not equal",
        ),
        pytest.param(
            "line",
            "from_node",
            ">",
            "1",
            [{"selector": "#23", "style": HIGHLIGHT_STYLE}],
            id="line from_node greater",
        ),
        pytest.param(
            "line",
            "to_node",
            "<",
            "10",
            [
                {"selector": "#12", "style": HIGHLIGHT_STYLE},
                {"selector": "#23", "style": HIGHLIGHT_STYLE},
            ],
            id="line to node smaller",
        ),
    ],
)
def test_search_element_with_input(
    group,
    column,
    operator,
    value,
    expected_selectors,
):
    server_state.set_app_state(Grid.from_txt("S1 2 12", "2 3 23"))

    result = search_element(
        group,
        column,
        operator,
        value,
        DEFAULT_STYLESHEET,
    )

    assert len(result) == len(DEFAULT_STYLESHEET) + len(expected_selectors)
    assert result[-len(expected_selectors) :] == expected_selectors


def test_show_arrows():
    original = deepcopy(DEFAULT_STYLESHEET)

    stored, displayed = update_arrows(
        show_arrows=True,
        stored_stylesheet=original,
        current_stylesheet=original,
    )

    assert stored == displayed
    assert displayed[_EDGE_INDEX]["style"]["target-arrow-shape"] == "triangle"
    assert original == DEFAULT_STYLESHEET


def test_hide_arrows():
    original = deepcopy(DEFAULT_STYLESHEET)

    stored, displayed = update_arrows(
        show_arrows=False,
        stored_stylesheet=original,
        current_stylesheet=original,
    )

    assert stored == displayed
    assert displayed[_EDGE_INDEX]["style"]["target-arrow-shape"] == "none"
    assert original == DEFAULT_STYLESHEET


def test_hidden_arrows_remain_hidden_after_scaling():
    """Scaling must preserve the user's branch-arrow setting."""
    original = deepcopy(DEFAULT_STYLESHEET)

    stored_stylesheet, displayed_stylesheet = update_arrows(
        show_arrows=False,
        stored_stylesheet=original,
        current_stylesheet=original,
    )

    assert original == DEFAULT_STYLESHEET

    stored_stylesheet, displayed_stylesheet = scale_elements(
        node_scale=1.2,
        edge_scale=1.3,
        stored_stylesheet=stored_stylesheet,
        current_stylesheet=displayed_stylesheet,
    )

    branch_rules = [
        rule for rule in displayed_stylesheet if rule["selector"] == ".branch" and "target-arrow-shape" in rule["style"]
    ]

    assert branch_rules[-1]["style"]["target-arrow-shape"] == "none"
    assert stored_stylesheet == displayed_stylesheet


def test_arrow_toggle_does_not_store_search_highlights():
    """Temporary search highlights must not become persistent display settings."""
    base_stylesheet = deepcopy(DEFAULT_STYLESHEET)

    highlighted_stylesheet = [
        *deepcopy(base_stylesheet),
        {"selector": "#123", "style": deepcopy(HIGHLIGHT_STYLE)},
    ]
    original_highlighted_stylesheet = deepcopy(highlighted_stylesheet)

    stored_stylesheet, displayed_stylesheet = update_arrows(
        show_arrows=False,
        stored_stylesheet=base_stylesheet,
        current_stylesheet=highlighted_stylesheet,
    )

    # Search highlights remain visible.
    assert any(rule["selector"] == "#123" for rule in displayed_stylesheet)

    # Search highlights are not persisted in the base stylesheet.
    assert not any(rule["selector"] == "#123" for rule in stored_stylesheet)

    # Both outputs reflect the new arrow setting.
    assert stored_stylesheet[_EDGE_INDEX]["style"]["target-arrow-shape"] == "none"
    assert displayed_stylesheet[_EDGE_INDEX]["style"]["target-arrow-shape"] == "none"

    # Neither input stylesheet is modified in place.
    assert base_stylesheet == DEFAULT_STYLESHEET
    assert highlighted_stylesheet == original_highlighted_stylesheet


def test_scaling_preserves_search_highlights_without_storing_them():
    """Scaling must retain temporary highlights only in the displayed stylesheet."""
    base_stylesheet = deepcopy(DEFAULT_STYLESHEET)
    highlighted_stylesheet = [
        *deepcopy(base_stylesheet),
        {"selector": "#123", "style": deepcopy(HIGHLIGHT_STYLE)},
    ]

    stored_stylesheet, displayed_stylesheet = scale_elements(
        node_scale=1.2,
        edge_scale=1.3,
        stored_stylesheet=base_stylesheet,
        current_stylesheet=highlighted_stylesheet,
    )

    assert any(rule["selector"] == "#123" for rule in displayed_stylesheet)
    assert not any(rule["selector"] == "#123" for rule in stored_stylesheet)

    assert stored_stylesheet != base_stylesheet
    assert displayed_stylesheet != highlighted_stylesheet

    assert base_stylesheet == DEFAULT_STYLESHEET


def test_element_selection_callback():
    grid = ThreePhaseGrid.empty()
    grid.node = ThreePhaseNodeArray.empty(1)
    grid.node.id = [1]
    grid.node.u_rated = [100.0]
    grid.node.three_phase_quantity = [[1.0, 2.0, 3.0]]

    server_state.set_app_state(grid)
    node_data = [{"id": "1", "group": "node", "associated_ids": {"node": [1]}}]

    result = display_selected_elements(node_data, [])
    assert result[0].children == "node"

    inspector = result[1]
    assert inspector.id == {"type": "selection-inspector", "group": "node"}
    records = inspector.children[0].data
    assert records == [
        {
            "id": 1,
            "u_rated": 100.0,
            "node_type": 0,
            "feeder_branch_id": -2147483648,
            "feeder_node_id": -2147483648,
            "three_phase_quantity": [1.0, 2.0, 3.0],
        }
    ]

    # One vertically arranged attribute row per original field.
    assert len(inspector.children) == len(records[0]) + 2
    for row, attribute in zip(inspector.children[2:], records[0], strict=True):
        name_and_filter, value_cell = row.children
        assert name_and_filter.children[0].children == attribute
        assert value_cell.id == {"type": "attribute-values", "group": "node", "attribute": attribute}
        filter_wrapper = name_and_filter.children[1]
        toggle, popup = filter_wrapper.children
        assert toggle.id == {"type": "attribute-filter-toggle", "group": "node", "attribute": attribute}
        assert popup.id == {"type": "attribute-filter-popup", "group": "node", "attribute": attribute}
        assert popup.style["display"] == "none"
        operator, value = popup.children
        assert operator.id["attribute"] == attribute
        assert value.id["attribute"] == attribute


def test_attribute_filter_popup_only_one_open():
    popup_ids = [
        {"type": "attribute-filter-popup", "group": "node", "attribute": attribute}
        for attribute in ("id", "u_rated", "node_type")
    ]
    closed = [{"display": "none"} for _ in popup_ids]
    ctx = MagicMock()
    ctx.triggered = [{"prop_id": "filter.n_clicks", "value": 1}]
    ctx.triggered_id = {"type": "attribute-filter-toggle", "group": "node", "attribute": "id"}

    with patch(_CTX_PATH, ctx):
        opened_id = toggle_attribute_filter([1, 0, 0], popup_ids, closed)
    assert [style["display"] for style in opened_id] == ["block", "none", "none"]

    ctx.triggered_id = {"type": "attribute-filter-toggle", "group": "node", "attribute": "u_rated"}
    with patch(_CTX_PATH, ctx):
        opened_rated = toggle_attribute_filter([1, 1, 0], popup_ids, opened_id)
    assert [style["display"] for style in opened_rated] == ["none", "block", "none"]

    with patch(_CTX_PATH, ctx):
        closed_again = toggle_attribute_filter([1, 2, 0], popup_ids, opened_rated)
    assert [style["display"] for style in closed_again] == ["none", "none", "none"]


def test_attribute_filter_popup_across_groups():
    popup_ids = [
        {"type": "attribute-filter-popup", "group": "node", "attribute": "id"},
        {"type": "attribute-filter-popup", "group": "source", "attribute": "id"},
    ]
    ctx = MagicMock()
    ctx.triggered = [{"prop_id": "filter.n_clicks", "value": 1}]
    ctx.triggered_id = {"type": "attribute-filter-toggle", "group": "source", "attribute": "id"}
    with patch(_CTX_PATH, ctx):
        result = toggle_attribute_filter([1, 1], popup_ids, [{"display": "block"}, {"display": "none"}])
    assert [style["display"] for style in result] == ["none", "block"]


def test_attribute_filter_comparisons():
    assert _matches(100.0, ">", "90")
    assert not _matches(100.0, "<", "90")
    assert _matches(100.0, "=", "100")
    assert _matches(100.0, "!=", "101")
    assert _matches([1.0, 2.0, 3.0], "contains", "2.0")
    assert not _matches([1.0, 2.0, 3.0], ">", "1")


def test_attribute_filter_restricts_multiple_components():
    group = "node"
    filter_ids = [
        {"type": "attribute-filter-value", "group": group, "attribute": "u_rated"},
        {"type": "attribute-filter-value", "group": group, "attribute": "node_type"},
    ]
    output_ids = [
        {"type": "attribute-values", "group": group, "attribute": "id"},
        {"type": "attribute-values", "group": group, "attribute": "u_rated"},
    ]
    records = [
        {"id": 1, "u_rated": 100.0, "node_type": 0},
        {"id": 2, "u_rated": 200.0, "node_type": 0},
    ]
    cells = update_attribute_values([">", "="], ["150", "0"], filter_ids, records, output_ids)
    assert len(cells) == 2
    assert len(cells[0].children) == 1
    assert cells[0].children[0].children == "ID 2: 2"
    assert cells[1].children[0].children == "ID 2: 200.0"


@pytest.mark.parametrize(
    ("node_data", "edge_data"),
    [
        ([], []),
        (None, None),
    ],
)
def test_display_selected_element_none(node_data, edge_data):
    result = display_selected_elements(node_data, edge_data)
    assert result == SELECTION_OUTPUT_HTML.children


def test_update_layout():
    assert update_layout("circle", [0, 1, 2]) == {"name": "circle", "animate": True}


@pytest.fixture
def mock_cell_clicked_ctx():
    """Simulate clicking a value in the vertical attribute inspector."""
    ctx = MagicMock()
    ctx.triggered = [
        {
            "prop_id": '{"type":"attribute-plot","group":"node","attribute":"u_rated","pgm_id":1}.n_clicks',
            "value": 1,
        }
    ]
    ctx.triggered_id = {"type": "attribute-plot", "group": "node", "attribute": "u_rated", "pgm_id": 1}
    return ctx


def test_missing_static_attribute_with_scenario_data_is_clickable():
    """A missing static value remains selectable when batch output exists."""
    dtype = np.dtype(
        [
            ("id", np.int32),
            ("u_pu", np.float64),
        ]
    )

    output_data = {
        ComponentType.node: np.array(
            [
                [(1, 0.97)],
                [(1, 0.98)],
                [(1, 0.99)],
                [(1, 1.00)],
            ],
            dtype=dtype,
        )
    }

    server_state.set_app_state(
        Grid.empty(),
        output_data=output_data,
    )

    result = _attribute_value_button(
        record={"id": 1, "u_pu": None},
        attribute="u_pu",
        group="node",
        include_id=False,
    )

    assert isinstance(result, html.Button)
    assert result.id == {
        "type": "attribute-plot",
        "group": "node",
        "attribute": "u_pu",
        "pgm_id": 1,
    }


def test_missing_static_attribute_without_scenario_data_is_not_clickable():
    """A missing static value must not create a plot button without batch data."""
    server_state.set_app_state(Grid.empty())

    result = _attribute_value_button(
        record={"id": 1, "u_ref": None},
        attribute="u_ref",
        group="source",
        include_id=False,
    )

    assert isinstance(result, html.Span)
    assert not isinstance(result, html.Button)


def test_cell_selection_graph_invalid_trigger():
    fig, style, controls_style = cell_selection_graph(None, 2.0)

    assert style == {"display": "none"}
    assert controls_style == {"display": "none"}
    assert fig == go.Figure()


def test_cell_selection_graph_ignores_non_click(mock_cell_clicked_ctx):
    """Initial button creation must not trigger a scenario plot."""
    mock_cell_clicked_ctx.triggered[0]["value"] = 0
    with patch(_CTX_PATH, mock_cell_clicked_ctx):
        selected = store_selected_cell(None, None, None)
    assert selected is no_update


def test_cell_selection_graph_no_data():
    server_state.set_app_state(Grid.empty())

    fig, style, controls_style = cell_selection_graph(
        _NODE_SELECTION,
        2.0,
    )

    assert style == {"display": "none"}
    assert controls_style == {"display": "none"}
    assert fig == go.Figure()


def test_cell_selection_graph_with_output_data():
    dtype = np.dtype(
        [
            ("id", np.int32),
            ("u_rated", np.float64),
        ]
    )

    output_data = {
        ComponentType.node: np.array(
            [
                [(1, 400.0)],
                [(9, 99.0)],
                [(1, 410.0)],
            ],
            dtype=dtype,
        )
    }

    server_state.set_app_state(
        Grid.empty(),
        output_data=output_data,
    )

    fig, style, controls_style = cell_selection_graph(
        _NODE_SELECTION,
        2.0,
    )

    assert style == {"display": "block"}
    assert controls_style == {"display": "none"}
    assert len(fig.data) == 1

    np.testing.assert_allclose(
        fig.data[0].y,
        [400.0, 410.0],
    )
    np.testing.assert_allclose(
        fig.data[0].x,
        [0, 2],
    )


def test_cell_selection_graph_three_phase_output_data():
    dtype = np.dtype(
        [
            ("id", np.int32),
            ("u_rated", np.float64, (3,)),
        ]
    )

    output_data = {
        ComponentType.node: np.array(
            [
                [(1, [400.0, 401.0, 402.0])],
                [(9, [99.0, 99.0, 99.0])],
                [(1, [410.0, 411.0, 412.0])],
            ],
            dtype=dtype,
        )
    }

    server_state.set_app_state(
        Grid.empty(),
        output_data=output_data,
    )

    fig, style, controls_style = cell_selection_graph(
        _NODE_SELECTION,
        2.0,
    )

    assert style == {"display": "block"}
    assert controls_style == {"display": "none"}
    assert len(fig.data) == 3

    np.testing.assert_allclose(
        fig.data[0].y,
        [400.0, 410.0],
    )
    np.testing.assert_allclose(
        fig.data[1].y,
        [401.0, 411.0],
    )
    np.testing.assert_allclose(
        fig.data[2].y,
        [402.0, 412.0],
    )

    for trace in fig.data:
        np.testing.assert_allclose(
            trace.x,
            [0, 2],
        )


@pytest.fixture
def mock_voltage_sensor_ctx():
    """Simulate clicking u_measured for symmetric voltage sensor 101."""
    ctx = MagicMock()

    ctx.triggered = [
        {
            "prop_id": (
                '{"type":"attribute-plot","group":"sym_voltage_sensor","attribute":"u_measured","pgm_id":101}.n_clicks'
            ),
            "value": 1,
        }
    ]
    ctx.triggered_id = {
        "type": "attribute-plot",
        "group": "sym_voltage_sensor",
        "attribute": "u_measured",
        "pgm_id": 101,
    }

    return ctx


@pytest.fixture
def voltage_sensor_grid():
    """Provide sensor attributes required by the comparison helper."""
    sensors = SimpleNamespace(
        id=np.array([101], dtype=np.int32),
        measured_object=np.array([10], dtype=np.int32),
        u_measured=np.array([230.0]),
        u_sigma=np.array([2.0]),
    )

    return SimpleNamespace(
        sym_voltage_sensor=sensors,
    )


def test_cell_selection_graph_voltage_comparison(voltage_sensor_grid):
    """Selecting u_measured displays measured and calculated voltages."""
    nodes = initialize_array(
        "sym_output",
        "node",
        (3, 1),
    )
    nodes["id"] = 10
    nodes["u"][:, 0] = [229.0, 231.0, 228.0]

    updates = initialize_array(
        "update",
        "sym_voltage_sensor",
        (3, 1),
    )
    updates["id"] = 101
    updates["u_measured"][1, 0] = 235.0

    output_data = {
        ComponentType.node: nodes,
    }

    update_data = {
        ComponentType.sym_voltage_sensor: updates,
    }

    with (
        patch(
            f"{_CALLBACK_PATH}.get_grid",
            return_value=voltage_sensor_grid,
        ),
        patch(
            f"{_CALLBACK_PATH}.get_output_data",
            return_value=output_data,
        ),
        patch(
            f"{_CALLBACK_PATH}.get_update_data",
            return_value=update_data,
        ),
    ):
        fig, style, controls_style = cell_selection_graph(
            _VOLTAGE_SELECTION,
            2.0,
        )

    assert style == {"display": "block"}
    assert controls_style == {"display": "block"}
    assert len(fig.data) == 4

    assert fig.data[2].name == "Measured voltage"
    assert fig.data[3].name == "Calculated voltage"

    np.testing.assert_array_equal(
        fig.data[2].x,
        [0, 1, 2],
    )
    np.testing.assert_array_equal(
        fig.data[2].y,
        [230.0, 235.0, 230.0],
    )
    np.testing.assert_array_equal(
        fig.data[3].y,
        [229.0, 231.0, 228.0],
    )

    np.testing.assert_array_equal(
        fig.data[0].y,
        [226.0, 231.0, 226.0],
    )
    np.testing.assert_array_equal(
        fig.data[1].y,
        [234.0, 239.0, 234.0],
    )

    assert fig.layout.showlegend is True


def test_cell_selection_graph_voltage_without_data():
    """Hide the graph when no comparison data is available."""
    with (
        patch(
            f"{_CALLBACK_PATH}.get_output_data",
            return_value=None,
        ),
        patch(
            f"{_CALLBACK_PATH}.get_update_data",
            return_value=None,
        ),
    ):
        fig, style, controls_style = cell_selection_graph(
            _VOLTAGE_SELECTION,
            2.0,
        )

    assert style == {"display": "none"}
    assert controls_style == {"display": "none"}
    assert fig == go.Figure()


def test_cell_selection_graph_voltage_falls_back_to_updates():
    """Preserve the update-series graph when node output is unavailable."""
    updates = initialize_array(
        "update",
        "sym_voltage_sensor",
        (3, 1),
    )
    updates["id"] = 101
    updates["u_measured"][:, 0] = [
        230.0,
        235.0,
        232.0,
    ]

    update_data = {
        ComponentType.sym_voltage_sensor: updates,
    }

    with (
        patch(
            f"{_CALLBACK_PATH}.get_output_data",
            return_value=None,
        ),
        patch(
            f"{_CALLBACK_PATH}.get_update_data",
            return_value=update_data,
        ),
    ):
        fig, style, controls_style = cell_selection_graph(
            _VOLTAGE_SELECTION,
            2.0,
        )

    assert style == {"display": "block"}
    assert controls_style == {"display": "none"}
    assert len(fig.data) == 1

    np.testing.assert_array_equal(
        fig.data[0].x,
        [0, 1, 2],
    )
    np.testing.assert_array_equal(
        fig.data[0].y,
        [230.0, 235.0, 232.0],
    )


def test_store_selected_voltage_sensor_cell(mock_voltage_sensor_ctx):
    """A sensor cell click is retained for subsequent graph updates."""
    with patch(
        _CTX_PATH,
        mock_voltage_sensor_ctx,
    ):
        selected_cell = store_selected_cell(None, None, None)

    assert selected_cell == {
        "group": "sym_voltage_sensor",
        "id": 101,
        "column": "u_measured",
    }


def test_changing_sigma_multiplier_updates_only_bounds(voltage_sensor_grid):
    """Changing the multiplier redraws bounds without changing voltage data."""
    nodes = initialize_array(
        "sym_output",
        "node",
        (2, 1),
    )
    nodes["id"] = 10
    nodes["u"][:, 0] = [231.0, 233.0]

    output_data = {
        ComponentType.node: nodes,
    }

    with (
        patch(
            f"{_CALLBACK_PATH}.get_grid",
            return_value=voltage_sensor_grid,
        ),
        patch(
            f"{_CALLBACK_PATH}.get_output_data",
            return_value=output_data,
        ),
        patch(
            f"{_CALLBACK_PATH}.get_update_data",
            return_value=None,
        ),
    ):
        figure_1, style_1, controls_1 = cell_selection_graph(
            _VOLTAGE_SELECTION,
            1.0,
        )

        figure_3, style_3, controls_3 = cell_selection_graph(
            _VOLTAGE_SELECTION,
            3.0,
        )

    assert style_1 == style_3 == {"display": "block"}
    assert controls_1 == controls_3 == {"display": "block"}

    # Measurement = 230 V; sigma = 2 V.
    np.testing.assert_allclose(
        figure_1.data[0].y,
        [228.0, 228.0],
    )
    np.testing.assert_allclose(
        figure_1.data[1].y,
        [232.0, 232.0],
    )

    np.testing.assert_allclose(
        figure_3.data[0].y,
        [224.0, 224.0],
    )
    np.testing.assert_allclose(
        figure_3.data[1].y,
        [236.0, 236.0],
    )

    # Neither the measured nor calculated series changes.
    for index in (2, 3):
        np.testing.assert_array_equal(
            figure_1.data[index].y,
            figure_3.data[index].y,
        )

    np.testing.assert_allclose(
        figure_1.data[2].y,
        [230.0, 230.0],
    )
    np.testing.assert_allclose(
        figure_1.data[3].y,
        [231.0, 233.0],
    )


@pytest.mark.parametrize(
    "multiplier",
    [None, -1, np.nan, np.inf],
)
def test_invalid_sigma_multiplier_hides_comparison(multiplier):
    """Reject invalid multiplier values before calculating bounds."""
    nodes = initialize_array(
        "sym_output",
        "node",
        (1, 1),
    )
    nodes["id"] = 10
    nodes["u"][0, 0] = 231.0

    with patch(
        f"{_CALLBACK_PATH}.get_output_data",
        return_value={ComponentType.node: nodes},
    ):
        figure, graph_style, controls_style = cell_selection_graph(
            _VOLTAGE_SELECTION,
            multiplier,
        )

    assert figure == go.Figure()
    assert graph_style == {"display": "none"}
    assert controls_style == {"display": "block"}


@pytest.mark.parametrize(
    "triggered_property",
    ["selectedNodeData", "selectedEdgeData"],
)
def test_store_selected_cell_clears_on_network_selection_change(
    triggered_property,
):
    """Changing the selected network elements clears the stored cell."""
    ctx = MagicMock()
    ctx.triggered_id = "cytoscape-graph"
    ctx.triggered = [
        {
            "prop_id": f"cytoscape-graph.{triggered_property}",
            "value": [],
        }
    ]

    with patch(_CTX_PATH, ctx):
        selected_cell = store_selected_cell(None, [], [])

    assert selected_cell is None


def test_voltage_comparison_hides_when_network_selection_cleared():
    selected_cell = {
        "group": ComponentType.sym_voltage_sensor.value,
        "id": 101,
        "column": "u_measured",
    }

    figure, graph_style, controls_style = cell_selection_graph(
        selected_cell,
        2.0,
        [],
        [],
    )

    assert len(figure.data) == 0
    assert graph_style == {"display": "none"}
    assert controls_style == {"display": "none"}


def test_voltage_comparison_falls_back_for_asymmetric_node_output():
    """Asymmetric node output must not enter the symmetric comparison."""
    nodes = initialize_array(
        "asym_output",
        "node",
        (2, 1),
    )
    nodes["id"] = 10
    nodes["u"][:, 0] = [
        [229.0, 230.0, 231.0],
        [232.0, 233.0, 234.0],
    ]

    updates = initialize_array(
        "update",
        "sym_voltage_sensor",
        (2, 1),
    )
    updates["id"] = 101
    updates["u_measured"][:, 0] = [230.0, 232.0]

    with (
        patch(
            f"{_CALLBACK_PATH}.get_output_data",
            return_value={ComponentType.node: nodes},
        ),
        patch(
            f"{_CALLBACK_PATH}.get_update_data",
            return_value={ComponentType.sym_voltage_sensor: updates},
        ),
    ):
        figure, graph_style, controls_style = cell_selection_graph(
            _VOLTAGE_SELECTION,
            2.0,
        )

    assert graph_style == {"display": "block"}
    assert controls_style == {"display": "none"}
    assert len(figure.data) == 1

    np.testing.assert_array_equal(
        figure.data[0].x,
        [0, 1],
    )
    np.testing.assert_array_equal(
        figure.data[0].y,
        [230.0, 232.0],
    )
