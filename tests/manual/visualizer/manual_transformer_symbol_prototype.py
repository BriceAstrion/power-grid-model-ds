
"""Prototype for a draggable transformer with connection anchors.

Run:
    python tests/manual/visualizer/manual_transformer_symbol_prototype.py
"""

import base64

import dash_cytoscape as cyto
from dash import Dash, Input, Output, callback, html

app = Dash(__name__)

TRANSFORMER_SVG = """
<svg xmlns="http://www.w3.org/2000/svg"
     width="90" height="60" viewBox="0 0 90 60">
  <circle cx="33" cy="30" r="22"
          fill="none" stroke="#2979B8" stroke-width="3"/>
  <circle cx="57" cy="30" r="22"
          fill="none" stroke="#2979B8" stroke-width="3"/>
</svg>
"""

TRANSFORMER_IMAGE = (
    "data:image/svg+xml;base64,"
    + base64.b64encode(
        TRANSFORMER_SVG.encode("utf-8")
    ).decode("ascii")
)

# The transformer parent is a visual representation of the
# original electrical component. The child nodes are visual
# connection anchors, not additional electrical buses.
elements = [
    {
        "data": {"id": "node-1", "label": "Node 1"},
        "position": {"x": 100, "y": 180},
        "grabbable": True,
    },
    {
        "data": {"id": "node-2", "label": "Node 2"},
        "position": {"x": 500, "y": 180},
        "grabbable": True,
    },
    {
        "data": {
            "id": "transformer-symbol-1",
            "component_id": "transformer-1",
            "component_type": "transformer",
        },
        "classes": "transformer-symbol",
        "grabbable": True,
        "selectable": True,
    },
    {
        "data": {
            "id": "transformer-anchor-left",
            "parent": "transformer-symbol-1",
        },
        "position": {"x": 266, "y": 180},
        "classes": "transformer-anchor",
        "grabbable": False,
        "selectable": False,
    },
    {
        "data": {
            "id": "transformer-anchor-right",
            "parent": "transformer-symbol-1",
        },
        "position": {"x": 334, "y": 180},
        "classes": "transformer-anchor",
        "grabbable": False,
        "selectable": False,
    },
    {
        "data": {
            "id": "visual-connection-1",
            "source": "node-1",
            "target": "transformer-anchor-left",
            "visual_only": True,
        },
        "classes": "visual-connection",
        "selectable": False,
    },
    {
        "data": {
            "id": "visual-connection-2",
            "source": "transformer-anchor-right",
            "target": "node-2",
            "visual_only": True,
        },
        "classes": "visual-connection",
        "selectable": False,
    },
]

stylesheet = [
    {
        "selector": "node",
        "style": {
            "label": "data(label)",
            "background-color": "#2979B8",
            "color": "#222222",
            "width": 42,
            "height": 42,
            "text-valign": "bottom",
            "text-margin-y": 10,
        },
    },
    {
        "selector": ".transformer-symbol",
        "style": {
            "shape": "rectangle",
            "background-color": "#FFFFFF",
            "background-opacity": 0,
            "background-image": TRANSFORMER_IMAGE,
            "background-fit": "contain",
            "background-image-opacity": 1,
            "border-width": 0,
            "label": "",
            "padding": 0,
            "min-width": 90,
            "min-height": 60,
        },
    },
    {
        "selector": ".transformer-anchor",
        "style": {
            "shape": "ellipse",
            "width": 1,
            "height": 1,
            "background-opacity": 0,
            "border-width": 0,
            "label": "",
        },
    },
    {
        "selector": ".visual-connection",
        "style": {
            "width": 3,
            "line-color": "#555555",
            "curve-style": "straight",
            "target-arrow-shape": "none",
            "source-endpoint": "outside-to-node",
            "target-endpoint": "outside-to-node",
        },
    },
]

app.layout = html.Div(
    [
        html.H3("Transformer connection-anchor prototype"),
        html.P(
            "Drag the transformer and both electrical nodes. "
            "Check whether the connection lines remain attached "
            "to the blue winding circles."
        ),
        cyto.Cytoscape(
            id="transformer-prototype",
            elements=elements,
            stylesheet=stylesheet,
            layout={"name": "preset"},
            style={
                "width": "100%",
                "height": "65vh",
                "border": "1px solid #AAAAAA",
            },
            minZoom=0.05,
            maxZoom=3.0,
            boxSelectionEnabled=True,
        ),
        html.Div(
            "No transformer selected.",
            id="selection-result",
            role="status",
        ),
    ],
    style={"padding": "20px"},
)


@callback(
    Output("selection-result", "children"),
    Input("transformer-prototype", "tapNodeData"),
)
def show_selected_component(node_data):
    """Map visual selection to the electrical component."""
    if node_data is None:
        return "No transformer selected."

    component_id = node_data.get("component_id")

    if component_id:
        return f"Selected electrical component: {component_id}"

    if node_data.get("parent") == "transformer-symbol-1":
        return "Transformer connection anchor clicked."

    return f"Selected network node: {node_data['id']}"


if __name__ == "__main__":
    app.run(debug=True, port=8051)
