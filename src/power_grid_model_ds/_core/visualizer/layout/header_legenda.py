# SPDX-FileCopyrightText: Contributors to the Power Grid Model project <powergridmodel@lfenergy.org>
#
# SPDX-License-Identifier: MPL-2.0

from urllib.parse import quote

import dash_bootstrap_components as dbc
from dash import html

from power_grid_model_ds._core.visualizer.layout.colors import CYTO_COLORS
from power_grid_model_ds._core.visualizer.layout.cytoscape_styling import _SOURCE_SYMBOL_IMAGE
from power_grid_model_ds._core.visualizer.styling_classification import StyleClass
from power_grid_model_ds._core.visualizer.transformer_constants import (
    TRANSFORMER_CIRCLE_OFFSET,
    TRANSFORMER_CIRCLE_RADIUS,
    TRANSFORMER_STROKE_WIDTH,
)

_BOOTSTRAP_ARROW_ICON_CLASS = "fas fa-arrow-right-long"
_MARGIN = "0 10px"

LEGENDA_STYLE = {"margin": _MARGIN, "text-shadow": "0 0 5px #000", "justify-content": "center"}

_FONT_SIZE = "2.5em"

NODE_ICON_STYLE = {"font-size": _FONT_SIZE, "margin": _MARGIN, "color": CYTO_COLORS[StyleClass.NODE]}
_SUBSTATION_ICON_STYLE = {"font-size": _FONT_SIZE, "margin": _MARGIN, "color": CYTO_COLORS[StyleClass.SUBSTATION_NODE]}
_LINE_ICON_STYLE = {"font-size": _FONT_SIZE, "margin": _MARGIN, "color": CYTO_COLORS[StyleClass.BRANCH]}
_LINK_ICON_STYLE = {"font-size": _FONT_SIZE, "margin": _MARGIN, "color": CYTO_COLORS[StyleClass.LINK]}
_LOAD_ICON_STYLE = {"width": "58px", "height": "32px", "margin": _MARGIN, "verticalAlign": "middle"}
_GENERATOR_ICON_STYLE = {"width": "58px", "height": "44px", "margin": _MARGIN, "verticalAlign": "middle"}
_SOURCE_ICON_STYLE = {"width": "36px", "height": "36px", "margin": _MARGIN, "verticalAlign": "middle"}
_TRANSFORMER_ICON_STYLE = {"width": "66px", "height": "44px", "margin": _MARGIN, "verticalAlign": "middle"}
_TRANSFORMER_LEGEND_EXTENT = 67
_TRANSFORMER_LEGEND_VIEWBOX = "-70 -48 140 96"


def _transformer_legend_symbol() -> html.Img:
    """Render the same winding dimensions as the Cytoscape transformer."""
    offset, radius = TRANSFORMER_CIRCLE_OFFSET, TRANSFORMER_CIRCLE_RADIUS
    extent = _TRANSFORMER_LEGEND_EXTENT
    color = CYTO_COLORS[StyleClass.TRANSFORMER]
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{_TRANSFORMER_LEGEND_VIEWBOX}" '
        f'fill="none" stroke="{color}" stroke-width="{TRANSFORMER_STROKE_WIDTH}">'
        f'<path d="M{-extent} 0 H{-offset - radius} M{offset + radius} 0 H{extent}"/>'
        f'<circle cx="{-offset}" cy="0" r="{radius}"/>'
        f'<circle cx="{offset}" cy="0" r="{radius}"/>'
        "</svg>"
    )
    return html.Img(id="transformer-icon", src="data:image/svg+xml," + quote(svg), style=_TRANSFORMER_ICON_STYLE)


def _load_legend_symbol() -> html.Img:
    """Render the open-arrow load symbol used in the Cytoscape visualizer."""
    color = "#FFF8F0"

    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 50" '
        f'fill="none" stroke="{color}" stroke-width="10" '
        'stroke-linecap="butt" stroke-linejoin="round">'
        '<path d="M5 25 H90 M70 5 L90 25 L70 45"/>'
        "</svg>"
    )

    return html.Img(
        id="load-icon",
        src="data:image/svg+xml," + quote(svg),
        style=_LOAD_ICON_STYLE,
    )


def _generator_legend_symbol() -> html.Img:
    """Render the circular generator symbol used in the Cytoscape visualizer."""
    color = "#D0FFE5"

    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 120 80" '
        f'fill="none" stroke="{color}" stroke-width="8">'
        '<path d="M5 40 H40"/>'
        '<circle cx="76" cy="40" r="34"/>'
        f'<text x="76" y="41" fill="{color}" stroke="none" '
        'font-family="Arial, sans-serif" font-size="38" font-weight="bold" '
        'text-anchor="middle" dominant-baseline="middle">G</text>'
        "</svg>"
    )

    return html.Img(
        id="generator-icon",
        src="data:image/svg+xml," + quote(svg),
        style=_GENERATOR_ICON_STYLE,
    )


_GENERIC_BRANCH_ICON_STYLE = {
    "font-size": _FONT_SIZE,
    "margin": _MARGIN,
    "color": CYTO_COLORS[StyleClass.GENERIC_BRANCH],
}
_ASYM_LINE_ICON_STYLE = {"font-size": _FONT_SIZE, "margin": _MARGIN, "color": CYTO_COLORS[StyleClass.ASYM_LINE]}
_OPEN_BRANCH_ICON_STYLE = {"font-size": _FONT_SIZE, "margin": _MARGIN, "color": CYTO_COLORS[StyleClass.OPEN_BRANCH]}
_SOURCE_ICON_STYLE = {"width": "36px", "height": "36px", "margin": _MARGIN}
LEGENDA_ELEMENTS = [
    html.Img(src=_SOURCE_SYMBOL_IMAGE, id="source-icon", style=_SOURCE_ICON_STYLE),
    dbc.Tooltip("AC Source", target="source-icon", placement="bottom"),
    html.I(className="fas fa-circle", id="node-icon", style=NODE_ICON_STYLE),
    dbc.Tooltip("Node", target="node-icon", placement="bottom"),
    html.I(className="fas fa-diamond", id="substation-icon", style=_SUBSTATION_ICON_STYLE),
    dbc.Tooltip("Substation", target="substation-icon", placement="bottom"),
    html.I(className=_BOOTSTRAP_ARROW_ICON_CLASS, id="line-icon", style=_LINE_ICON_STYLE),
    dbc.Tooltip("Line", target="line-icon", placement="bottom"),
    _load_legend_symbol(),
    dbc.Tooltip("Load (Belasting)", target="load-icon", placement="bottom"),
    _generator_legend_symbol(),
    dbc.Tooltip("Generator", target="generator-icon", placement="bottom"),
    _transformer_legend_symbol(),
    dbc.Tooltip("Transformer", target="transformer-icon", placement="bottom"),
    html.I(className=_BOOTSTRAP_ARROW_ICON_CLASS, id="link-icon", style=_LINK_ICON_STYLE),
    dbc.Tooltip("Link", target="link-icon", placement="bottom"),
    html.I(className=_BOOTSTRAP_ARROW_ICON_CLASS, id="generic-branch-icon", style=_GENERIC_BRANCH_ICON_STYLE),
    dbc.Tooltip("Generic Branch", target="generic-branch-icon", placement="bottom"),
    html.I(className=_BOOTSTRAP_ARROW_ICON_CLASS, id="asym-line-icon", style=_ASYM_LINE_ICON_STYLE),
    dbc.Tooltip("Asymmetrical Line", target="asym-line-icon", placement="bottom"),
    html.I(className="fas fa-ellipsis", id="open-branch-icon", style=_OPEN_BRANCH_ICON_STYLE),
    dbc.Tooltip("Open Branch", target="open-branch-icon", placement="bottom"),
]
