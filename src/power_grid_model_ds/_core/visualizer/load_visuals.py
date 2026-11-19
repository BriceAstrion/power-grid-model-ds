# SPDX-FileCopyrightText: Contributors to the Power Grid Model project <powergridmodel@lfenergy.org>
#
# SPDX-License-Identifier: MPL-2.0

"""Create presentation-only load symbols for positioned electrical nodes."""

from copy import deepcopy
from typing import Any

from power_grid_model_ds._core.visualizer.load_constants import (
    LOAD_CONNECTION_CLASS,
    LOAD_CONNECTION_LENGTH,
    LOAD_CONNECTION_SUFFIX,
    LOAD_GROUPS,
    LOAD_OPEN_CLASS,
    LOAD_SYMBOL_CLASS,
    LOAD_SYMBOL_GROUP,
    LOAD_SYMBOL_SUFFIX,
    LOAD_VISUAL_PREFIX,
    VISUAL_ONLY_KEY,
)
from power_grid_model_ds._core.visualizer.styling_classification import StyleClass
from power_grid_model_ds._core.visualizer.visual_elements import add_visual_elements


def _create_load_visuals(
    item: dict[str, Any],
    nodes: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    """Create a load symbol and connection when its node is positioned."""
    data = item["data"]

    if data.get("group") not in LOAD_GROUPS:
        return []

    source_id = str(data.get("source", ""))
    source = nodes.get(source_id)

    if source is None or "position" not in source:
        return []

    position = source["position"]
    load_id = str(data["id"])
    prefix = f"{LOAD_VISUAL_PREFIX}{load_id}"
    symbol_id = f"{prefix}{LOAD_SYMBOL_SUFFIX}"

    classes = set(item.get("classes", "").split())
    is_open = StyleClass.OPEN_LOADING_APPLIANCE.value in classes

    connection_classes = [LOAD_CONNECTION_CLASS]
    if is_open:
        connection_classes.append(LOAD_OPEN_CLASS)

    return [
        {
            "data": {
                "id": symbol_id,
                "group": LOAD_SYMBOL_GROUP,
                "component_id": load_id,
                "component_type": data["group"],
                "associated_ids": deepcopy(data.get("associated_ids", {})),
                VISUAL_ONLY_KEY: True,
            },
            "position": {
                "x": position["x"] + LOAD_CONNECTION_LENGTH,
                "y": position["y"],
            },
            "classes": LOAD_SYMBOL_CLASS,
            "grabbable": True,
            "selectable": True,
        },
        {
            "data": {
                "id": f"{prefix}{LOAD_CONNECTION_SUFFIX}",
                "source": source_id,
                "target": symbol_id,
                "associated_ids": {},
                VISUAL_ONLY_KEY: True,
            },
            "classes": " ".join(connection_classes),
            "selectable": False,
        },
    ]


def add_load_visuals(elements: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Retain original load elements and add their presentation symbols."""
    return add_visual_elements(elements, _create_load_visuals, "load")
