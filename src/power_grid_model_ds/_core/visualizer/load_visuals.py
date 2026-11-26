# SPDX-FileCopyrightText: Contributors to the Power Grid Model project <powergridmodel@lfenergy.org>
#
# SPDX-License-Identifier: MPL-2.0

"""Create presentation-only load symbols for positioned electrical nodes."""

from typing import Any

from power_grid_model_ds._core.visualizer.appliance_visuals import (
    ApplianceConnectionConfig,
    ApplianceSymbolConfig,
    ApplianceVisualConfig,
    add_appliance_visuals,
)
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
)
from power_grid_model_ds._core.visualizer.styling_classification import StyleClass

_LOAD_CONFIG = ApplianceVisualConfig(
    groups=LOAD_GROUPS,
    symbol=ApplianceSymbolConfig(
        group=LOAD_SYMBOL_GROUP,
        css_class=LOAD_SYMBOL_CLASS,
        visual_prefix=LOAD_VISUAL_PREFIX,
        suffix=LOAD_SYMBOL_SUFFIX,
    ),
    connection=ApplianceConnectionConfig(
        css_class=LOAD_CONNECTION_CLASS,
        open_class=LOAD_OPEN_CLASS,
        open_appliance_class=StyleClass.OPEN_LOADING_APPLIANCE.value,
        suffix=LOAD_CONNECTION_SUFFIX,
        length=LOAD_CONNECTION_LENGTH,
    ),
    component_name="load",
)


def add_load_visuals(elements: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Retain original load elements and add their presentation symbols."""
    return add_appliance_visuals(elements, _LOAD_CONFIG)
