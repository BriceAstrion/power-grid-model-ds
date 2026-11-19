# SPDX-FileCopyrightText: Contributors to the Power Grid Model project <powergridmodel@lfenergy.org>
#
# SPDX-License-Identifier: MPL-2.0

"""Shared construction of appliance presentation elements."""

from copy import deepcopy
from dataclasses import dataclass
from typing import Any

from power_grid_model_ds._core.visualizer.visual_elements import add_visual_elements


@dataclass(frozen=True)
class ApplianceVisualConfig:
    """Configuration for a presentation-only appliance symbol."""

    groups: frozenset[str]
    symbol_group: str
    symbol_class: str
    connection_class: str
    open_class: str
    open_appliance_class: str
    visual_prefix: str
    symbol_suffix: str
    connection_suffix: str
    connection_length: int
    component_name: str
    placement: str = "right"


def add_appliance_visuals(
    elements: list[dict[str, Any]],
    config: ApplianceVisualConfig,
) -> list[dict[str, Any]]:
    """Create presentation symbols for appliances with positioned nodes."""

    def create_visuals(
        item: dict[str, Any],
        nodes: dict[str, dict[str, Any]],
    ) -> list[dict[str, Any]]:
        data = item["data"]

        if data.get("group") not in config.groups:
            return []

        source_id = str(data.get("source", ""))
        source = nodes.get(source_id)

        if source is None or "position" not in source:
            return []

        position = source["position"]
        component_id = str(data["id"])
        prefix = f"{config.visual_prefix}{component_id}"
        symbol_id = f"{prefix}{config.symbol_suffix}"

        classes = set(item.get("classes", "").split())
        is_open = config.open_appliance_class in classes

        connection_classes = [config.connection_class]
        if is_open:
            connection_classes.append(config.open_class)

        if config.placement == "above":
            symbol_position = {
                "x": position["x"],
                "y": position["y"] - config.connection_length,
            }
        else:
            symbol_position = {
                "x": position["x"] + config.connection_length,
                "y": position["y"],
            }

        return [
            {
                "data": {
                    "id": symbol_id,
                    "group": config.symbol_group,
                    "component_id": component_id,
                    "component_type": data["group"],
                    "associated_ids": deepcopy(data.get("associated_ids", {})),
                    "visual_only": True,
                },
                "position": symbol_position,
                "classes": config.symbol_class,
                "grabbable": True,
                "selectable": True,
            },
            {
                "data": {
                    "id": f"{prefix}{config.connection_suffix}",
                    "source": source_id,
                    "target": symbol_id,
                    "associated_ids": {},
                    "visual_only": True,
                },
                "classes": " ".join(connection_classes),
                "selectable": False,
            },
        ]

    return add_visual_elements(elements, create_visuals, config.component_name)
