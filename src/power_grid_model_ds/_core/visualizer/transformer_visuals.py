# SPDX-FileCopyrightText: Contributors to the Power Grid Model project <powergridmodel@lfenergy.org>
#
# SPDX-License-Identifier: MPL-2.0

"""Add presentation-only symbols for positioned two-winding transformers."""

from copy import deepcopy
from math import atan2, degrees, hypot
from typing import Any

from power_grid_model_ds._core.visualizer.layout.colors import CYTO_COLORS
from power_grid_model_ds._core.visualizer.styling_classification import StyleClass
from power_grid_model_ds._core.visualizer.transformer_constants import (
    MIN_TRANSFORMER_CONNECTION_LENGTH,
    TRANSFORMER_CONNECTION_CLASS,
    TRANSFORMER_FROM_SUFFIX,
    TRANSFORMER_GROUP,
    TRANSFORMER_OPEN_CLASS,
    TRANSFORMER_OPEN_FROM_CLASS,
    TRANSFORMER_OPEN_TO_CLASS,
    TRANSFORMER_SYMBOL_CLASS,
    TRANSFORMER_SYMBOL_GROUP,
    TRANSFORMER_SYMBOL_SUFFIX,
    TRANSFORMER_TO_SUFFIX,
    TRANSFORMER_VISUAL_PREFIX,
    VISUAL_ONLY_KEY,
)
from power_grid_model_ds._core.visualizer.visual_elements import add_visual_elements


def _connection_classes(classes: set[str]) -> tuple[str, str]:
    """Preserve open-terminal classifications on visual connections."""
    from_classes = [TRANSFORMER_CONNECTION_CLASS]
    to_classes = [TRANSFORMER_CONNECTION_CLASS]

    if StyleClass.OPEN_BRANCH.value in classes:
        from_classes.append(TRANSFORMER_OPEN_CLASS)
        to_classes.append(TRANSFORMER_OPEN_CLASS)
    if StyleClass.OPEN_BRANCH_FROM.value in classes:
        from_classes.append(TRANSFORMER_OPEN_FROM_CLASS)
    if StyleClass.OPEN_BRANCH_TO.value in classes:
        to_classes.append(TRANSFORMER_OPEN_TO_CLASS)

    return " ".join(from_classes), " ".join(to_classes)


def _create_transformer_visuals(
    data: dict[str, Any],
    source_position: dict[str, float],
    target_position: dict[str, float],
    classes: set[str],
) -> list[dict[str, Any]]:
    """Create a transformer symbol and its two visual connections."""
    transformer_id = str(data["id"])
    prefix = f"{TRANSFORMER_VISUAL_PREFIX}{transformer_id}"
    symbol_id = f"{prefix}{TRANSFORMER_SYMBOL_SUFFIX}"

    midpoint = {
        "x": (source_position["x"] + target_position["x"]) / 2,
        "y": (source_position["y"] + target_position["y"]) / 2,
    }
    angle = degrees(
        atan2(
            target_position["y"] - source_position["y"],
            target_position["x"] - source_position["x"],
        )
    )
    from_classes, to_classes = _connection_classes(classes)

    return [
        {
            "data": {
                "id": symbol_id,
                "group": TRANSFORMER_SYMBOL_GROUP,
                "component_id": transformer_id,
                "symbol_angle": angle,
                "symbol_color": CYTO_COLORS[StyleClass.TRANSFORMER],
                "symbol_selected_color": CYTO_COLORS["selected_transformer"],
                "associated_ids": deepcopy(data.get("associated_ids", {})),
                VISUAL_ONLY_KEY: True,
            },
            "position": midpoint,
            "classes": TRANSFORMER_SYMBOL_CLASS,
            "grabbable": True,
            "selectable": True,
        },
        {
            "data": {
                "id": f"{prefix}{TRANSFORMER_FROM_SUFFIX}",
                "source": data["source"],
                "target": symbol_id,
                "associated_ids": {},
                VISUAL_ONLY_KEY: True,
            },
            "classes": from_classes,
            "selectable": False,
        },
        {
            "data": {
                "id": f"{prefix}{TRANSFORMER_TO_SUFFIX}",
                "source": symbol_id,
                "target": data["target"],
                "associated_ids": {},
                VISUAL_ONLY_KEY: True,
            },
            "classes": to_classes,
            "selectable": False,
        },
    ]


def _visuals_for_transformer(
    item: dict[str, Any],
    nodes: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    """Return visual elements when both endpoints have usable positions."""
    data = item["data"]

    if data.get("group") != TRANSFORMER_GROUP or "source" not in data or "target" not in data:
        return []

    source = nodes.get(str(data["source"]))
    target = nodes.get(str(data["target"]))

    if not source or not target or "position" not in source or "position" not in target:
        return []

    source_position = source["position"]
    target_position = target["position"]

    if (
        hypot(
            target_position["x"] - source_position["x"],
            target_position["y"] - source_position["y"],
        )
        <= MIN_TRANSFORMER_CONNECTION_LENGTH
    ):
        return []

    return _create_transformer_visuals(
        data,
        source_position,
        target_position,
        set(item.get("classes", "").split()),
    )


def add_transformer_visuals(elements: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Keep original electrical edges and add symbols for positioned endpoints."""
    return add_visual_elements(elements, _visuals_for_transformer, "transformer")
