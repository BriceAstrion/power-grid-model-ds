# SPDX-FileCopyrightText: Contributors to the Power Grid Model project <powergridmodel@lfenergy.org>
#
# SPDX-License-Identifier: MPL-2.0

"""Shared rendering preparation for appliance presentation symbols."""

from collections.abc import Callable
from typing import Any


def prepare_appliance_rendering(
    elements: list[dict[str, Any]],
    add_visuals: Callable[[list[dict[str, Any]]], list[dict[str, Any]]],
    groups: frozenset[str],
    symbol_group: str,
    hidden_class: str,
) -> list[dict[str, Any]]:
    """Add appliance visuals and hide originals with replacement symbols."""
    result = add_visuals(elements)

    converted = {str(item["data"]["component_id"]) for item in result if item["data"].get("group") == symbol_group}

    for item in result:
        data = item["data"]

        if data.get("group") not in groups or str(data.get("id")) not in converted:
            continue

        classes = item.get("classes", "").split()
        if hidden_class not in classes:
            classes.append(hidden_class)

        item["classes"] = " ".join(classes)

    return result
