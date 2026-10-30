# SPDX-FileCopyrightText: Contributors to the Power Grid Model project <powergridmodel@lfenergy.org>
#
# SPDX-License-Identifier: MPL-2.0

"""Contains selectors for the Cytoscape stylesheet."""

import base64

from power_grid_model_ds._core.visualizer.layout.colors import CYTO_COLORS
from power_grid_model_ds._core.visualizer.styling_classification import StyleClass

NODE_SIZE = 75
BRANCH_WIDTH = 10

_BRANCH_STYLE = {
    "selector": f".{StyleClass.BRANCH.value}",
    "style": {
        "line-color": CYTO_COLORS[StyleClass.BRANCH],
        "target-arrow-color": CYTO_COLORS[StyleClass.BRANCH],
        "curve-style": "bezier",
        "target-arrow-shape": "triangle",
        "width": BRANCH_WIDTH,
    },
}
_NODE_STYLE = {
    "selector": f".{StyleClass.NODE.value}",
    "style": {
        "label": "data(id)",
        "border-width": 5,
        "border-color": "black",
        "font-size": 25,
        "text-halign": "center",
        "text-valign": "center",
        "background-color": CYTO_COLORS[StyleClass.NODE],
        "text-background-color": CYTO_COLORS[StyleClass.NODE],
        "text-background-opacity": 1,
        "text-background-shape": "round-rectangle",
        "width": NODE_SIZE,
        "height": NODE_SIZE,
    },
}
_NODE_LARGE_ID_STYLE = {
    "selector": f".{StyleClass.LARGE_ID_NODE.value}",
    "style": {"font-size": 15},
}
_SELECTED_NODE_STYLE = {
    "selector": f".{StyleClass.NODE.value}:selected, .{StyleClass.NODE.value}:active",
    "style": {"border-width": 5, "border-color": CYTO_COLORS["selected"]},
}

_APPLIANCE_GHOST_NODE_STYLE = {
    "selector": f".{StyleClass.APPLIANCE_GHOST_NODE.value}",
    "style": {
        "label": "",
        "border-width": 5,
        "border-color": "black",
        "font-size": 25,
        "text-halign": "center",
        "text-valign": "center",
        "background-color": CYTO_COLORS["node"],
        "text-background-color": CYTO_COLORS["node"],
        "text-background-opacity": 1,
        "text-background-shape": "round-rectangle",
        "width": NODE_SIZE * 0.25,
        "height": NODE_SIZE * 0.25,
    },
}

_GENERATING_EDGE_STYLE = {
    "selector": f".{StyleClass.GENERATING_APPLIANCE.value}",
    "style": {
        "line-color": StyleClass.BRANCH,
        "curve-style": "bezier",
        "source-arrow-color": StyleClass.BRANCH,
        "source-arrow-shape": "vee",
        "arrow-scale": 3.0,
        "width": BRANCH_WIDTH * 0.5,
    },
}
_SOURCE_EDGE_STYLE = {
    "selector": f".{StyleClass.SOURCE.value}",
    "style": {
        "line-color": CYTO_COLORS["substation_node"],
        "source-arrow-color": CYTO_COLORS["substation_node"],
    },
}
_LOADING_EDGE_STYLE = {
    "selector": f".{StyleClass.LOADING_APPLIANCE.value}",
    "style": {
        "line-color": StyleClass.BRANCH,
        "curve-style": "bezier",
        "target-arrow-color": StyleClass.BRANCH,
        "target-arrow-shape": "vee",
        "arrow-scale": 3.0,
        "width": BRANCH_WIDTH * 0.5,
    },
}

_SELECTED_BRANCH_STYLE = {
    "selector": f".{StyleClass.BRANCH.value}:selected, .{StyleClass.BRANCH.value}:active",
    "style": {"line-color": CYTO_COLORS["selected"], "target-arrow-color": CYTO_COLORS["selected"], "width": 10},
}


_SUBSTATION_NODE_STYLE = {
    "selector": f".{StyleClass.SUBSTATION_NODE.value}",
    "style": {
        "label": "data(id)",
        "shape": "diamond",
        "background-color": CYTO_COLORS[StyleClass.SUBSTATION_NODE],
        "text-background-color": CYTO_COLORS[StyleClass.SUBSTATION_NODE],
        "width": NODE_SIZE * 1.2,
        "height": NODE_SIZE * 1.2,
        "color": "white",
    },
}
_TRANSFORMER_STYLE = {
    "selector": f".{StyleClass.TRANSFORMER.value}",
    "style": {
        "line-color": CYTO_COLORS[StyleClass.TRANSFORMER],
        "target-arrow-color": CYTO_COLORS[StyleClass.TRANSFORMER],
    },
}
_TWO_WINDING_TRANSFORMER_STYLE = {
    "selector": f'edge.{StyleClass.TRANSFORMER.value}[group = "transformer"]',
    "style": {
        "line-color": CYTO_COLORS[StyleClass.TRANSFORMER],
        "target-arrow-color": CYTO_COLORS[StyleClass.TRANSFORMER],
        "target-arrow-shape": "none",
    },
}
_SELECTED_TRANSFORMER_STYLE = {
    "selector": f".{StyleClass.TRANSFORMER.value}:selected, .{StyleClass.TRANSFORMER.value}:active",
    "style": {
        "line-color": CYTO_COLORS["selected_transformer"],
        "target-arrow-color": CYTO_COLORS["selected_transformer"],
    },
}

_LINK_STYLE = {
    "selector": f".{StyleClass.LINK.value}",
    "style": {"line-color": CYTO_COLORS[StyleClass.LINK], "target-arrow-color": CYTO_COLORS[StyleClass.LINK]},
}

_SELECTED_LINK_STYLE = {
    "selector": f".{StyleClass.LINK.value}:selected, .{StyleClass.LINK.value}:active",
    "style": {"line-color": CYTO_COLORS["selected_link"], "target-arrow-color": CYTO_COLORS["selected_link"]},
}

_GENERIC_BRANCH_STYLE = {
    "selector": f".{StyleClass.GENERIC_BRANCH.value}",
    "style": {
        "line-color": CYTO_COLORS[StyleClass.GENERIC_BRANCH],
        "target-arrow-color": CYTO_COLORS[StyleClass.GENERIC_BRANCH],
    },
}
_SELECTED_GENERIC_BRANCH_STYLE = {
    "selector": f".{StyleClass.GENERIC_BRANCH.value}:selected, .{StyleClass.GENERIC_BRANCH.value}:active",
    "style": {
        "line-color": CYTO_COLORS["selected_generic_branch"],
        "target-arrow-color": CYTO_COLORS["selected_generic_branch"],
    },
}

_ASYM_LINE_STYLE = {
    "selector": f".{StyleClass.ASYM_LINE.value}",
    "style": {"line-color": CYTO_COLORS[StyleClass.ASYM_LINE], "target-arrow-color": CYTO_COLORS[StyleClass.ASYM_LINE]},
}

_SELECTED_ASYM_LINE_STYLE = {
    "selector": f".{StyleClass.ASYM_LINE.value}:selected, .{StyleClass.ASYM_LINE.value}:active",
    "style": {
        "line-color": CYTO_COLORS["selected_asym_line"],
        "target-arrow-color": CYTO_COLORS["selected_asym_line"],
    },
}
_OPEN_BRANCH_STYLE = {
    "selector": f".{StyleClass.OPEN_BRANCH.value}",
    "style": {
        "line-style": "dashed",
        "target-arrow-color": CYTO_COLORS[StyleClass.OPEN_BRANCH],
        "source-arrow-color": CYTO_COLORS[StyleClass.OPEN_BRANCH],
    },
}
_OPEN_FROM_SIDE_BRANCH_STYLE = {
    "selector": f".{StyleClass.OPEN_BRANCH_FROM.value}",
    "style": {
        "source-arrow-shape": "diamond",
        "source-arrow-fill": "hollow",
    },
}
_OPEN_TO_SIDE_BRANCH_STYLE = {
    "selector": f".{StyleClass.OPEN_BRANCH_TO.value}",
    "style": {
        "target-arrow-shape": "diamond",
        "target-arrow-fill": "hollow",
    },
}

_OPEN_LOADING_EDGE_STYLE = {
    "selector": f".{StyleClass.OPEN_LOADING_APPLIANCE.value}",
    "style": {
        "line-style": "dashed",
        "line-color": CYTO_COLORS["open_branch"],
        "target-arrow-color": CYTO_COLORS["open_branch"],
        "target-arrow-fill": "hollow",
    },
}
_OPEN_GENERATING_EDGE_STYLE = {
    "selector": f".{StyleClass.OPEN_GENERATING_APPLIANCE.value}",
    "style": {
        "line-style": "dashed",
        "line-color": CYTO_COLORS["open_branch"],
        "source-arrow-color": CYTO_COLORS["open_branch"],
        "source-arrow-fill": "hollow",
    },
}

_TRANSFORMER_SYMBOL_SVG = """
<svg xmlns="http://www.w3.org/2000/svg"
     width="90" height="60" viewBox="0 0 90 60">
  <circle cx="33" cy="30" r="22"
          fill="none" stroke="#42B7FF" stroke-width="5"/>
  <circle cx="57" cy="30" r="22"
          fill="none" stroke="#42B7FF" stroke-width="5"/>
</svg>
"""

_TRANSFORMER_SYMBOL_IMAGE = (
    "data:image/svg+xml;base64,"
    + base64.b64encode(_TRANSFORMER_SYMBOL_SVG.encode("utf-8")).decode("ascii")
)

_TRANSFORMER_ORIGINAL_HIDDEN_STYLE = {
    "selector": ".transformer-original-hidden",
    "style": {
        "display": "none",
    },
}

_TRANSFORMER_SYMBOL_STYLE = {
    "selector": ".transformer-symbol",
    "style": {
        "shape": "rectangle",
        "background-opacity": 0,
        "background-image": _TRANSFORMER_SYMBOL_IMAGE,
        "background-fit": "contain",
        "background-image-opacity": 1,
        "border-width": 0,
        "label": "",
        "padding": 0,
        "min-width": 120,
        "min-height": 80,
    },
}

_TRANSFORMER_ANCHOR_STYLE = {
    "selector": ".transformer-anchor",
    "style": {
        "shape": "ellipse",
        "width": 1,
        "height": 1,
        "background-opacity": 0,
        "border-width": 0,
        "label": "",
    },
}

_TRANSFORMER_VISUAL_CONNECTION_STYLE = {
    "selector": ".transformer-visual-connection",
    "style": {
        "width": BRANCH_WIDTH,
        "line-color": "#FFD13B",
        "line-style": "solid",
        "curve-style": "straight",
        "target-arrow-shape": "none",
        "source-arrow-shape": "none",
        "source-endpoint": "outside-to-node",
        "target-endpoint": "outside-to-node",
    },
}

_TRANSFORMER_VISUAL_OPEN_FROM_STYLE = {
    "selector": ".transformer-visual-open-from",
    "style": {
        "line-style": "dashed",
        "source-arrow-shape": "diamond",
        "source-arrow-fill": "hollow",
        "source-arrow-color": "#FFD13B",
    },
}

_TRANSFORMER_VISUAL_OPEN_TO_STYLE = {
    "selector": ".transformer-visual-open-to",
    "style": {
        "line-style": "dashed",
        "target-arrow-shape": "diamond",
        "target-arrow-fill": "hollow",
        "target-arrow-color": "#FFD13B",
    },
}

DEFAULT_STYLESHEET = [
    _NODE_STYLE,
    _NODE_LARGE_ID_STYLE,
    _SUBSTATION_NODE_STYLE,
    _BRANCH_STYLE,
    _TRANSFORMER_STYLE,
    _TWO_WINDING_TRANSFORMER_STYLE,
    _LINK_STYLE,
    _SELECTED_NODE_STYLE,
    _SELECTED_BRANCH_STYLE,
    _SELECTED_TRANSFORMER_STYLE,
    _SELECTED_LINK_STYLE,
    _GENERIC_BRANCH_STYLE,
    _SELECTED_GENERIC_BRANCH_STYLE,
    _ASYM_LINE_STYLE,
    _SELECTED_ASYM_LINE_STYLE,
    _APPLIANCE_GHOST_NODE_STYLE,
    _GENERATING_EDGE_STYLE,
    _LOADING_EDGE_STYLE,
    _SOURCE_EDGE_STYLE,
    # Note: Keep the OPEN BRANCH styles last in list, otherwise they potentially get overridden.
    _OPEN_BRANCH_STYLE,
    _OPEN_FROM_SIDE_BRANCH_STYLE,
    _OPEN_TO_SIDE_BRANCH_STYLE,
    _OPEN_LOADING_EDGE_STYLE,
    _OPEN_GENERATING_EDGE_STYLE,
    _TRANSFORMER_ORIGINAL_HIDDEN_STYLE,
    _TRANSFORMER_SYMBOL_STYLE,
    _TRANSFORMER_ANCHOR_STYLE,
    _TRANSFORMER_VISUAL_CONNECTION_STYLE,
    _TRANSFORMER_VISUAL_OPEN_FROM_STYLE,
    _TRANSFORMER_VISUAL_OPEN_TO_STYLE,
]
