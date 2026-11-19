# SPDX-FileCopyrightText: Contributors to the Power Grid Model project <powergridmodel@lfenergy.org>
#
# SPDX-License-Identifier: MPL-2.0

"""Prepare load presentation elements for Cytoscape."""

from typing import Any

from power_grid_model_ds._core.visualizer.load_constants import (
    LOAD_GROUPS,
    LOAD_ORIGINAL_HIDDEN_CLASS,
    LOAD_SYMBOL_GROUP,
)
from power_grid_model_ds._core.visualizer.load_visuals import add_load_visuals


def prepare_load_rendering(
    elements: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Add load symbols while retaining the original electrical elements."""
    result = add_load_visuals(elements)

    converted = {str(item["data"]["component_id"]) for item in result if item["data"].get("group") == LOAD_SYMBOL_GROUP}

    for item in result:
        data = item["data"]

        if data.get("group") not in LOAD_GROUPS or str(data.get("id")) not in converted:
            continue

        classes = item.get("classes", "").split()

        if LOAD_ORIGINAL_HIDDEN_CLASS not in classes:
            classes.append(LOAD_ORIGINAL_HIDDEN_CLASS)

        item["classes"] = " ".join(classes)

    return result
