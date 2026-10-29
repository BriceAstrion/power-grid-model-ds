
# SPDX-FileCopyrightText: Contributors to the Power Grid Model project <powergridmodel@lfenergy.org>
#
# SPDX-License-Identifier: MPL-2.0

"""Build visual-only elements for two-winding transformers."""

from copy import deepcopy
from typing import Any


def add_transformer_visuals(
    elements: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Add transformer symbols and anchors without changing original elements.

    Only transformers with positioned endpoint nodes are handled.
    This first implementation supports preset coordinates.
    """
    result = deepcopy(elements)

    nodes = {
        element["data"]["id"]: element
        for element in elements
        if "source" not in element["data"]
    }
    existing_ids = {str(element["data"]["id"]) for element in elements}

    for element in elements:
        data = element["data"]

        if data.get("group") != "transformer":
            continue

        if "source" not in data or "target" not in data:
            continue

        source = nodes.get(data["source"])
        target = nodes.get(data["target"])

        if source is None or target is None:
            continue

        if "position" not in source or "position" not in target:
            continue

        source_position = source["position"]
        target_position = target["position"]

        midpoint_x = (source_position["x"] + target_position["x"]) / 2
        midpoint_y = (source_position["y"] + target_position["y"]) / 2

        transformer_id = str(data["id"])
        prefix = f"__visual_transformer__{transformer_id}"

        symbol_id = f"{prefix}__symbol"
        left_id = f"{prefix}__left"
        right_id = f"{prefix}__right"
        first_edge_id = f"{prefix}__connection_1"
        second_edge_id = f"{prefix}__connection_2"

        new_ids = {
            symbol_id,
            left_id,
            right_id,
            first_edge_id,
            second_edge_id,
        }

        if existing_ids & new_ids:
            raise ValueError(
                f"Visual element ID collision for transformer {transformer_id}"
            )

        existing_ids.update(new_ids)

        result.extend(
            [
                {
                    "data": {
                        "id": symbol_id,
                        "component_id": transformer_id,
                        "group": "transformer_symbol",
                        "associated_ids": deepcopy(data["associated_ids"]),
                        "visual_only": True,
                    },
                    "classes": "transformer-symbol",
                    "grabbable": True,
                    "selectable": True,
                },
                {
                    "data": {
                        "id": left_id,
                        "parent": symbol_id,
                        "associated_ids": {},
                        "visual_only": True,
                    },
                    "position": {
                        "x": midpoint_x - 34,
                        "y": midpoint_y,
                    },
                    "classes": "transformer-anchor",
                    "grabbable": False,
                    "selectable": False,
                },
                {
                    "data": {
                        "id": right_id,
                        "parent": symbol_id,
                        "associated_ids": {},
                        "visual_only": True,
                    },
                    "position": {
                        "x": midpoint_x + 34,
                        "y": midpoint_y,
                    },
                    "classes": "transformer-anchor",
                    "grabbable": False,
                    "selectable": False,
                },
                {
                    "data": {
                        "id": first_edge_id,
                        "source": data["source"],
                        "target": left_id,
                        "associated_ids": {},
                        "visual_only": True,
                    },
                    "classes": "transformer-visual-connection",
                    "selectable": False,
                },
                {
                    "data": {
                        "id": second_edge_id,
                        "source": right_id,
                        "target": data["target"],
                        "associated_ids": {},
                        "visual_only": True,
                    },
                    "classes": "transformer-visual-connection",
                    "selectable": False,
                },
            ]
        )

    return result
