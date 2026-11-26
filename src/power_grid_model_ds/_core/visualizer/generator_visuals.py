# SPDX-FileCopyrightText: Contributors to the Power Grid Model project <powergridmodel@lfenergy.org>
#
# SPDX-License-Identifier: MPL-2.0

"""Create presentation-only generator symbols."""

from typing import Any

from power_grid_model_ds._core.visualizer.appliance_visuals import (
    ApplianceConnectionConfig,
    ApplianceSymbolConfig,
    ApplianceVisualConfig,
    add_appliance_visuals,
)
from power_grid_model_ds._core.visualizer.generator_constants import (
    GENERATOR_CONNECTION_CLASS,
    GENERATOR_CONNECTION_LENGTH,
    GENERATOR_CONNECTION_SUFFIX,
    GENERATOR_GROUPS,
    GENERATOR_OPEN_CLASS,
    GENERATOR_SYMBOL_CLASS,
    GENERATOR_SYMBOL_GROUP,
    GENERATOR_SYMBOL_SUFFIX,
    GENERATOR_VISUAL_PREFIX,
)
from power_grid_model_ds._core.visualizer.styling_classification import StyleClass

_GENERATOR_CONFIG = ApplianceVisualConfig(
    groups=GENERATOR_GROUPS,
    symbol=ApplianceSymbolConfig(
        group=GENERATOR_SYMBOL_GROUP,
        css_class=GENERATOR_SYMBOL_CLASS,
        visual_prefix=GENERATOR_VISUAL_PREFIX,
        suffix=GENERATOR_SYMBOL_SUFFIX,
    ),
    connection=ApplianceConnectionConfig(
        css_class=GENERATOR_CONNECTION_CLASS,
        open_class=GENERATOR_OPEN_CLASS,
        open_appliance_class=StyleClass.OPEN_GENERATING_APPLIANCE.value,
        suffix=GENERATOR_CONNECTION_SUFFIX,
        length=GENERATOR_CONNECTION_LENGTH,
    ),
    component_name="generator",
    placement="above",
)


def add_generator_visuals(elements: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Retain original generators and add their presentation symbols."""
    return add_appliance_visuals(elements, _GENERATOR_CONFIG)
