# SPDX-FileCopyrightText: Contributors to the Power Grid Model project <powergridmodel@lfenergy.org>
#
# SPDX-License-Identifier: MPL-2.0

"""Prepare load presentation elements for Cytoscape."""

from typing import Any

from power_grid_model_ds._core.visualizer.appliance_rendering import prepare_appliance_rendering
from power_grid_model_ds._core.visualizer.load_constants import (
    LOAD_GROUPS,
    LOAD_ORIGINAL_HIDDEN_CLASS,
    LOAD_SYMBOL_GROUP,
)
from power_grid_model_ds._core.visualizer.load_visuals import add_load_visuals


def prepare_load_rendering(elements: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Add load symbols while retaining the original electrical elements."""
    return prepare_appliance_rendering(
        elements,
        add_load_visuals,
        LOAD_GROUPS,
        LOAD_SYMBOL_GROUP,
        LOAD_ORIGINAL_HIDDEN_CLASS,
    )
