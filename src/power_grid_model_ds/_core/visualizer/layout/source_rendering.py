# SPDX-FileCopyrightText: Contributors to the Power Grid Model project <powergridmodel@lfenergy.org>
#
# SPDX-License-Identifier: MPL-2.0

"""Place AC source symbols without obscuring other positioned grid elements."""

from copy import deepcopy
from typing import Any

_SOURCE_GROUP = "source"
_SOURCE_GHOST_GROUP = "source_ghost_node"
_SOURCE_SIZE = 100
_CLEARANCE = 12

_SYMBOL_SIZES = {
    "generator_symbol": (80, 80),
    "load_symbol": (100, 60),
    "transformer_symbol": (112, 76),
    _SOURCE_GHOST_GROUP: (_SOURCE_SIZE, _SOURCE_SIZE),
}

Bounds = tuple[float, float, float, float]
Point = tuple[float, float]


def _position(item: dict[str, Any]) -> Point | None:
    position = item.get("position")
    if not isinstance(position, dict) or "x" not in position or "y" not in position:
        return None
    return float(position["x"]), float(position["y"])


def _bounds(item: dict[str, Any]) -> Bounds | None:
    point = _position(item)
    if point is None:
        return None

    group = item["data"].get("group")
    width, height = _SYMBOL_SIZES.get(group, (50, 50))
    x, y = point
    return x - width / 2, y - height / 2, x + width / 2, y + height / 2


def _overlaps(first: Bounds, second: Bounds) -> bool:
    return not (
        first[2] + _CLEARANCE <= second[0]
        or second[2] + _CLEARANCE <= first[0]
        or first[3] + _CLEARANCE <= second[1]
        or second[3] + _CLEARANCE <= first[1]
    )


def _segment_intersects_bounds(start: Point, end: Point, bounds: Bounds) -> bool:
    """Check a straight segment against a rectangle with clearance."""
    left, top, right, bottom = bounds
    left -= _CLEARANCE
    top -= _CLEARANCE
    right += _CLEARANCE
    bottom += _CLEARANCE

    dx = end[0] - start[0]
    dy = end[1] - start[1]
    enter, leave = 0.0, 1.0

    for p, q in ((-dx, start[0] - left), (dx, right - start[0]), (-dy, start[1] - top), (dy, bottom - start[1])):
        if p == 0:
            if q < 0:
                return False
            continue
        fraction = q / p
        if p < 0:
            enter = max(enter, fraction)
        else:
            leave = min(leave, fraction)
        if enter > leave:
            return False
    return True


def _grid_segments(elements: list[dict[str, Any]], by_id: dict[str, dict[str, Any]]) -> list[tuple[Point, Point]]:
    segments = []
    for item in elements:
        data = item["data"]
        if "source" not in data or "target" not in data:
            continue
        if data.get("group") == _SOURCE_GROUP or data.get("visual_only"):
            continue
        if "hidden" in item.get("classes", ""):
            continue
        start = by_id.get(str(data["source"]))
        end = by_id.get(str(data["target"]))
        if start is None or end is None:
            continue
        start_position = _position(start)
        end_position = _position(end)
        if start_position is not None and end_position is not None:
            segments.append((start_position, end_position))
    return segments


def _source_candidates(origin: Point) -> list[Point]:
    candidates = []
    for distance in (120, 180, 240, 320, 420):
        candidates.extend(
            (
                (origin[0] + distance, origin[1]),
                (origin[0], origin[1] + distance),
                (origin[0] - distance, origin[1]),
                (origin[0], origin[1] - distance),
                (origin[0] + distance, origin[1] + distance),
                (origin[0] - distance, origin[1] + distance),
                (origin[0] + distance, origin[1] - distance),
                (origin[0] - distance, origin[1] - distance),
            )
        )
    return candidates


def _find_source_position(
    origin: Point,
    node_bounds: Bounds | None,
    occupied: list[Bounds],
    fixed_occupied: list[Bounds],
    segments: list[tuple[Point, Point]],
) -> Point | None:
    for x, y in _source_candidates(origin):
        bounds = (x - _SOURCE_SIZE / 2, y - _SOURCE_SIZE / 2, x + _SOURCE_SIZE / 2, y + _SOURCE_SIZE / 2)
        if any(_overlaps(bounds, other) for other in occupied):
            continue
        if any(_segment_intersects_bounds(start, end, bounds) for start, end in segments):
            continue
        if any(_segment_intersects_bounds(origin, (x, y), other) for other in fixed_occupied if other != node_bounds):
            continue
        return x, y
    return None


def prepare_source_rendering(elements: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Reposition existing source ghost nodes in a preset, positioned graph.

    Electrical edges, identifiers and associations are left unchanged. If no
    candidate is free, the source keeps its original position.
    """
    result = deepcopy(elements)
    by_id = {str(item["data"]["id"]): item for item in result}
    sources = sorted(
        (item for item in result if item["data"].get("group") == _SOURCE_GROUP and "source" in item["data"]),
        key=lambda item: str(item["data"]["id"]),
    )
    source_ghost_ids = {str(item["data"].get("target")) for item in sources}

    occupied = [
        bounds
        for item in result
        if str(item["data"]["id"]) not in source_ghost_ids
        if "source" not in item["data"] and "target" not in item["data"]
        if (bounds := _bounds(item)) is not None
    ]
    fixed_occupied = occupied.copy()
    segments = _grid_segments(result, by_id)

    for source in sources:
        data = source["data"]
        node = by_id.get(str(data["source"]))
        ghost = by_id.get(str(data["target"]))
        if node is None or ghost is None:
            continue
        origin = _position(node)
        if origin is None:
            continue

        chosen = _find_source_position(origin, _bounds(node), occupied, fixed_occupied, segments)
        if chosen is not None:
            ghost["position"] = {"x": chosen[0], "y": chosen[1]}
        current_bounds = _bounds(ghost)
        if current_bounds is not None:
            occupied.append(current_bounds)

    return result
