# SPDX-FileCopyrightText: Contributors to the Power Grid Model project <powergridmodel@lfenergy.org>
#
# SPDX-License-Identifier: MPL-2.0

"""Shared helpers for adding presentation-only Cytoscape elements."""

from collections.abc import Callable
from copy import deepcopy
from typing import Any

VisualElement = dict[str, Any]
VisualFactory = Callable[
    [VisualElement, dict[str, VisualElement]],
    list[VisualElement],
]


def add_visual_elements(
    elements: list[VisualElement],
    create_visuals: VisualFactory,
    component_name: str,
) -> list[VisualElement]:
    """Add presentation elements while preserving the original elements."""
    result = deepcopy(elements)

    nodes = {
        str(item["data"]["id"]): item
        for item in elements
        if "source" not in item["data"] and "target" not in item["data"]
    }
    existing_ids = {str(item["data"]["id"]) for item in elements}

    for item in elements:
        visuals = create_visuals(item, nodes)
        if not visuals:
            continue

        new_ids = {str(visual["data"]["id"]) for visual in visuals}
        if len(new_ids) != len(visuals) or existing_ids & new_ids:
            raise ValueError(f"Visual element ID collision for {component_name} {item['data']['id']}")

        existing_ids.update(new_ids)
        result.extend(visuals)

    return result
