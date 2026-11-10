# SPDX-FileCopyrightText: Contributors to the Power Grid Model project <powergridmodel@lfenergy.org>
#
# SPDX-License-Identifier: MPL-2.0
from dash.development.base_component import Component

from power_grid_model_ds._core.data_source.generator.grid_generators import RadialGridGenerator
from power_grid_model_ds._core.model.grids.base import Grid
from power_grid_model_ds._core.visualizer.app import get_app_layout
from power_grid_model_ds._core.visualizer.layout.cytoscape_html import get_cytoscape_html
from power_grid_model_ds._core.visualizer.layout.header_config import LayoutOptions


def test_get_cytoscape_html():
    elements = [{"data": {"id": "1", "group": "node"}}]
    cyto_html = get_cytoscape_html(LayoutOptions.PRESET, elements, [])
    assert cyto_html.children.elements == elements


def test_get_app_layout():
    grid = RadialGridGenerator(Grid).run()
    assert get_app_layout(grid)


def test_diagnostic_overview_container_removed_from_app_layout():
    """The removed diagnostic overview must not appear in the layout."""

    layout = get_app_layout(Grid.from_txt("S1 2 12", "2 3 23"))

    def count_diagnostic_containers(node):
        if isinstance(node, (list, tuple)):
            return sum(count_diagnostic_containers(child) for child in node)

        if not isinstance(node, Component):
            return 0

        count = int(
            getattr(node, "id", None) == "diagnostic-overview-content"
        )

        return count + count_diagnostic_containers(
            getattr(node, "children", None)
        )

    assert count_diagnostic_containers(layout) == 0
