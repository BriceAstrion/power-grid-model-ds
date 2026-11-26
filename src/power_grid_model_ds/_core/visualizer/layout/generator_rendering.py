# SPDX-FileCopyrightText: Contributors to the Power Grid Model project <powergridmodel@lfenergy.org>
#
# SPDX-License-Identifier: MPL-2.0

"""Prepare generator presentation elements for Cytoscape."""

from typing import Any

from power_grid_model_ds._core.visualizer.appliance_rendering import prepare_appliance_rendering
from power_grid_model_ds._core.visualizer.generator_constants import (
    GENERATOR_GROUPS,
    GENERATOR_ORIGINAL_HIDDEN_CLASS,
    GENERATOR_SYMBOL_GROUP,
)
from power_grid_model_ds._core.visualizer.generator_visuals import add_generator_visuals


def prepare_generator_rendering(elements: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Add generator symbols while retaining the original electrical elements."""
    return prepare_appliance_rendering(
        elements,
        add_generator_visuals,
        GENERATOR_GROUPS,
        GENERATOR_SYMBOL_GROUP,
        GENERATOR_ORIGINAL_HIDDEN_CLASS,
    )
