# SPDX-FileCopyrightText: Contributors to the Power Grid Model project <powergridmodel@lfenergy.org>
#
# SPDX-License-Identifier: MPL-2.0

from urllib.parse import quote

import dash_bootstrap_components as dbc
from dash import html

from power_grid_model_ds._core.visualizer.layout.colors import CYTO_COLORS
from power_grid_model_ds._core.visualizer.styling_classification import StyleClass

_BOOTSTRAP_ARROW_ICON_CLASS = "fas fa-arrow-right-long"
_MARGIN = "0 10px"

LEGENDA_STYLE = {"margin": _MARGIN, "text-shadow": "0 0 5px #000", "justify-content": "center"}

_FONT_SIZE = "2.5em"

NODE_ICON_STYLE = {"font-size": _FONT_SIZE, "margin": _MARGIN, "color": CYTO_COLORS[StyleClass.NODE]}
_SUBSTATION_ICON_STYLE = {"font-size": _FONT_SIZE, "margin": _MARGIN, "color": CYTO_COLORS[StyleClass.SUBSTATION_NODE]}
_TRANSFORMER_ICON_STYLE = {"font-size": _FONT_SIZE, "margin": _MARGIN, "color": CYTO_COLORS[StyleClass.TRANSFORMER]}
_GENERIC_BRANCH_ICON_STYLE = {
    "font-size": _FONT_SIZE,
    "margin": _MARGIN,
    "color": CYTO_COLORS[StyleClass.GENERIC_BRANCH],
}
_ASYM_LINE_ICON_STYLE = {"font-size": _FONT_SIZE, "margin": _MARGIN, "color": CYTO_COLORS[StyleClass.ASYM_LINE]}
_OPEN_BRANCH_ICON_STYLE = {"font-size": _FONT_SIZE, "margin": _MARGIN, "color": CYTO_COLORS[StyleClass.OPEN_BRANCH]}


def _electrical_symbol(element_id: str, color: str, paths: str, stroke_width: int = 5) -> html.Img:
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 32" '
        f'fill="none" stroke="{color}" stroke-width="{stroke_width}">'
        f"{paths}</svg>"
    )
    return html.Img(
        id=element_id,
        src="data:image/svg+xml," + quote(svg),
        style={"width": "54px", "height": "32px", "margin": _MARGIN},
    )


LEGENDA_ELEMENTS = [
    html.I(className="fas fa-circle", id="node-icon", style=NODE_ICON_STYLE),
    dbc.Tooltip("Node", target="node-icon", placement="bottom"),
    html.I(className="fas fa-diamond", id="substation-icon", style=_SUBSTATION_ICON_STYLE),
    dbc.Tooltip("Substation", target="substation-icon", placement="bottom"),
    _electrical_symbol("line-icon", CYTO_COLORS[StyleClass.BRANCH], '<path d="M6 12 H94 M6 20 H94"/>'),
    dbc.Tooltip("Line", target="line-icon", placement="bottom"),
    html.I(className=_BOOTSTRAP_ARROW_ICON_CLASS, id="transformer-icon", style=_TRANSFORMER_ICON_STYLE),
    dbc.Tooltip("Transformer", target="transformer-icon", placement="bottom"),
    _electrical_symbol(
        "link-icon", CYTO_COLORS[StyleClass.LINK], '<path d="M6 16 H94 M6 9 V23 M94 9 V23"/>', stroke_width=7
    ),
    dbc.Tooltip("Link", target="link-icon", placement="bottom"),
    html.I(className=_BOOTSTRAP_ARROW_ICON_CLASS, id="generic-branch-icon", style=_GENERIC_BRANCH_ICON_STYLE),
    dbc.Tooltip("Generic Branch", target="generic-branch-icon", placement="bottom"),
    html.I(className=_BOOTSTRAP_ARROW_ICON_CLASS, id="asym-line-icon", style=_ASYM_LINE_ICON_STYLE),
    dbc.Tooltip("Asymmetrical Line", target="asym-line-icon", placement="bottom"),
    html.I(className="fas fa-ellipsis", id="open-branch-icon", style=_OPEN_BRANCH_ICON_STYLE),
    dbc.Tooltip("Open Branch", target="open-branch-icon", placement="bottom"),
]
