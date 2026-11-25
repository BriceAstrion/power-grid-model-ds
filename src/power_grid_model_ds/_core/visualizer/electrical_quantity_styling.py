# SPDX-FileCopyrightText: Contributors to the Power Grid Model project <powergridmodel@lfenergy.org>
#
# SPDX-License-Identifier: MPL-2.0

"""Map electrical quantity results to Cytoscape element data."""

from collections.abc import Mapping, Sequence
from copy import deepcopy
from typing import Any

SENSOR_GROUPS = frozenset(
    {
        "sym_voltage_sensor",
        "asym_voltage_sensor",
        "sym_power_sensor",
        "asym_power_sensor",
        "sym_current_sensor",
        "asym_current_sensor",
    }
)

MISSING_COLOR = "#9CA3AF"
ELECTRICAL_HEATMAP_CLASS = "electrical-heatmap"

# Continuous rainbow-style scale: purple -> blue -> cyan -> green -> yellow -> orange -> red.
RAINBOW_STOPS = (
    (106, 13, 173),
    (59, 40, 204),
    (24, 91, 219),
    (0, 170, 232),
    (0, 206, 181),
    (45, 190, 85),
    (162, 218, 35),
    (255, 230, 0),
    (255, 147, 0),
    (220, 38, 38),
)

LOW_COLOR = RAINBOW_STOPS[0]
HIGH_COLOR = RAINBOW_STOPS[-1]


def _interpolate_color(value: float, minimum: float, maximum: float) -> str:
    """Interpolate a colour over the selected value range."""
    fraction = 0.5 if minimum == maximum else (value - minimum) / (maximum - minimum)
    fraction = max(0.0, min(1.0, fraction))

    position = fraction * (len(RAINBOW_STOPS) - 1)
    lower_index = min(int(position), len(RAINBOW_STOPS) - 2)
    local_fraction = position - lower_index

    low = RAINBOW_STOPS[lower_index]
    high = RAINBOW_STOPS[lower_index + 1]

    channels = [round(a + (b - a) * local_fraction) for a, b in zip(low, high, strict=True)]

    return f"#{channels[0]:02X}{channels[1]:02X}{channels[2]:02X}"


def _remove_electrical_styling(element: dict[str, Any]) -> None:
    """Remove electrical data and its styling class from an element."""
    data = element.get("data", {})

    data.pop("electrical_value", None)
    data.pop("electrical_color", None)

    classes = element.get("classes", "").split()

    if ELECTRICAL_HEATMAP_CLASS in classes:
        element["classes"] = " ".join(style_class for style_class in classes if style_class != ELECTRICAL_HEATMAP_CLASS)


def _enable_electrical_styling(element: dict[str, Any]) -> None:
    """Activate electrical colouring while preserving component classes."""
    classes = element.get("classes", "").split()

    if ELECTRICAL_HEATMAP_CLASS not in classes:
        classes.append(ELECTRICAL_HEATMAP_CLASS)

    element["classes"] = " ".join(classes)


def apply_electrical_colors(
    elements: Sequence[dict[str, Any]],
    component_group: str,
    values: Mapping[int, float],
) -> tuple[list[dict[str, Any]], dict[str, float | int | None]]:
    """Add electrical display data to matching Cytoscape elements.

    The original elements are not modified. Missing results receive a
    neutral colour. Previous electrical styling is removed. Sensor values
    use existing associations; the largest absolute residual retains its sign.
    Equal magnitudes are resolved by the lowest sensor ID.
    """
    updated_elements = deepcopy(list(elements))
    matched_elements: list[tuple[dict[str, Any], float]] = []
    missing_count = 0

    is_sensor = component_group in SENSOR_GROUPS

    for element in updated_elements:
        _remove_electrical_styling(element)

        data = element.get("data", {})

        associated_ids = data.get("associated_ids", {}).get(component_group, [])
        if is_sensor:
            if not associated_ids:
                continue
        elif data.get("group") != component_group:
            continue

        matching_ids = [component_id for component_id in associated_ids if component_id in values]

        if not is_sensor and len(matching_ids) > 1:
            raise ValueError("A visual element maps to multiple electrical values.")

        _enable_electrical_styling(element)

        if not matching_ids:
            data["electrical_color"] = MISSING_COLOR
            missing_count += 1
            continue

        selected_id = max(matching_ids, key=lambda component_id: (abs(values[component_id]), -component_id))
        matched_elements.append((data, values[selected_id]))

    minimum = min((value for _, value in matched_elements), default=None)
    maximum = max((value for _, value in matched_elements), default=None)

    if minimum is not None and maximum is not None:
        for data, value in matched_elements:
            data["electrical_value"] = value
            data["electrical_color"] = _interpolate_color(
                value,
                minimum,
                maximum,
            )

    return updated_elements, {
        "minimum": minimum,
        "maximum": maximum,
        "missing_count": missing_count,
    }


def clear_electrical_colors(
    elements: Sequence[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Restore default component styling without modifying source elements."""
    updated_elements = deepcopy(list(elements))

    for element in updated_elements:
        _remove_electrical_styling(element)

    return updated_elements
