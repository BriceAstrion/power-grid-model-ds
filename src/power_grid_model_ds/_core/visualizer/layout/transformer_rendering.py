# SPDX-FileCopyrightText: Contributors to the Power Grid Model project <powergridmodel@lfenergy.org>
#
# SPDX-License-Identifier: MPL-2.0

"""Prepare two-winding transformer elements for Cytoscape rendering."""

from typing import Any

from power_grid_model_ds._core.visualizer.transformer_visuals import add_transformer_visuals


def prepare_transformer_rendering(
    elements: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Add visual transformers and hide only their original rendered edges.

    The original electrical edge data remains in the returned elements.
    Transformers without positioned endpoints are left unchanged.
    """
    result = add_transformer_visuals(elements)

    transformed_ids = {
        element["data"]["component_id"]
        for element in result
        if element["data"].get("group") == "transformer_symbol"
    }

    for element in result:
        data = element["data"]

        if data.get("group") != "transformer":
            continue

        if str(data["id"]) not in transformed_ids:
            continue

        classes = element.get("classes", "").split()
        if "transformer-original-hidden" not in classes:
            classes.append("transformer-original-hidden")

        element["classes"] = " ".join(classes)

    return result
