# SPDX-FileCopyrightText: Contributors to the Power Grid Model project <powergridmodel@lfenergy.org>
#
# SPDX-License-Identifier: MPL-2.0

"""Regression tests for breadthfirst electrical roots."""

import pytest

from power_grid_model_ds._core.model.grids.base import Grid
from power_grid_model_ds._core.visualizer.layout.header_config import LayoutOptions
from power_grid_model_ds._core.visualizer.layout.layout_config import layout_with_config
from power_grid_model_ds._core.visualizer.parsers import parse_element_data
from power_grid_model_ds._core.visualizer.parsing_utils import filter_out_appliances
from power_grid_model_ds.arrays import SourceArray


def _create_grid(source_nodes: tuple[int, ...]) -> Grid:
    """Create a network with explicitly defined source appliances."""
    grid = Grid.from_txt("1 2 12", "2 3 23")

    if source_nodes:
        sources = SourceArray.empty(len(source_nodes))
        sources.id = list(range(100, 100 + len(source_nodes)))
        sources.node = list(source_nodes)
        sources.status = 1
        sources.u_ref = 1.0
        grid.append(sources)

    assert len(grid.source) == len(source_nodes)
    return grid


def _root_ids(elements):
    """Return electrical nodes marked as breadthfirst roots."""
    return {
        element["data"]["id"]
        for element in elements
        if element["data"]["group"] == "node" and element["data"].get("source_root") == 1
    }


@pytest.mark.parametrize("show_appliances", [True, False])
def test_source_root_survives_appliance_visibility(show_appliances):
    """Use the electrical root regardless of appliance visibility."""
    grid = _create_grid((1,))
    elements = list(parse_element_data(grid).values())

    if not show_appliances:
        elements = filter_out_appliances(elements)

    assert _root_ids(elements) == {"1"}


def test_source_ghost_nodes_are_not_roots():
    """Graphical source endpoints must not be electrical roots."""
    grid = _create_grid((1,))
    elements = list(parse_element_data(grid).values())

    ghost_nodes = [element for element in elements if element["data"]["group"] == "source_ghost_node"]

    assert len(ghost_nodes) == 1
    assert all("source_root" not in element["data"] for element in ghost_nodes)


@pytest.mark.parametrize("show_appliances", [True, False])
def test_multiple_source_roots(show_appliances):
    """Preserve all source-connected electrical roots."""
    grid = _create_grid((1, 3))
    elements = list(parse_element_data(grid).values())

    if not show_appliances:
        elements = filter_out_appliances(elements)

    assert _root_ids(elements) == {"1", "3"}


def test_multiple_sources_on_same_node():
    """Multiple sources at one node produce one electrical root."""
    grid = _create_grid((1, 1))
    elements = list(parse_element_data(grid).values())

    assert _root_ids(elements) == {"1"}


def test_grid_without_sources_has_no_marked_roots():
    """Do not introduce artificial electrical roots."""
    grid = _create_grid(())
    elements = list(parse_element_data(grid).values())

    assert not _root_ids(elements)


def test_breadthfirst_uses_electrical_root_selector():
    """Select electrical nodes rather than appliance endpoints."""
    config = layout_with_config(
        LayoutOptions.BREADTHFIRST,
        source_available=True,
    )

    assert config["roots"] == 'node[group = "node"][source_root = 1]'
    assert config["spacingFactor"] == 2.5


def test_breadthfirst_without_sources():
    """Allow automatic root selection without sources."""
    config = layout_with_config(
        LayoutOptions.BREADTHFIRST,
        source_available=False,
    )

    assert "roots" not in config
