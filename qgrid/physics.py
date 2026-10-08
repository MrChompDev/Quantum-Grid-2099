"""Beam optics / ray-tracing engine for Quantum Grid 2099.

Rays are traced from every emitter across the grid:
  - Walls (#) block the beam.
  - Mirrors (/ and \\) bend the beam 90 degrees per the reflection table.
  - Receptors (*) are powered by the beam and let it pass through.
  - The player probe (@) absorbs the beam.
  - The beam leaves a trail on empty floor: '=' horizontal, '|' vertical.
  - A cell hit from both axes renders as '+'.

Loop protection: a beam stops if it re-enters the same cell travelling
in the same direction (prevents infinite mirror loops).
"""

from dataclasses import dataclass, field

DIR4 = ((0, -1), (0, 1), (-1, 0), (1, 0))

# Emitter glyph -> direction vector (dx, dy). +x right, +y down.
DIR_VEC: dict[str, tuple[int, int]] = {
    ">": (1, 0),
    "<": (-1, 0),
    "^": (0, -1),
    "v": (0, 1),
}

# Mirror glyph -> {incoming direction: outgoing direction}
REFLECT: dict[str, dict[tuple[int, int], tuple[int, int]]] = {
    "/": {
        (1, 0): (0, -1),  # right -> up
        (-1, 0): (0, 1),  # left  -> down
        (0, -1): (1, 0),  # up    -> right
        (0, 1): (-1, 0),  # down  -> left
    },
    "\\": {
        (1, 0): (0, 1),  # right -> down
        (-1, 0): (0, -1),  # left  -> up
        (0, -1): (-1, 0),  # up    -> left
        (0, 1): (1, 0),  # down  -> right
    },
}

MIRRORS = ("/", "\\")


@dataclass
class BeamTrace:
    h: set[tuple[int, int]] = field(default_factory=set)
    v: set[tuple[int, int]] = field(default_factory=set)
    powered: set[tuple[int, int]] = field(default_factory=set)


def trace_beam(
    layout, player: tuple[int, int], mirrors: dict[tuple[int, int], str]
) -> BeamTrace:
    """Trace every emitter's beam across the grid and return the resulting trace."""
    trace = BeamTrace()
    for (ex, ey), dch in layout.emitters:
        dx, dy = DIR_VEC[dch]
        x, y = ex, ey
        seen: set[tuple[int, int, int, int]] = set()
        while True:
            nx, ny = x + dx, y + dy
            if not (0 <= nx < layout.width and 0 <= ny < layout.height):
                break
            key = (nx, ny, dx, dy)
            if key in seen:
                break
            seen.add(key)
            terrain = layout.rows[ny][nx]
            if terrain == "#":
                break
            if (nx, ny) in mirrors:
                dx, dy = REFLECT[mirrors[(nx, ny)]][(dx, dy)]
                x, y = nx, ny
                continue
            if terrain == "*":
                trace.powered.add((nx, ny))
            if (nx, ny) == player:
                if dx:
                    trace.h.add((nx, ny))
                else:
                    trace.v.add((nx, ny))
                break
            if terrain == "*":
                if dx:
                    trace.h.add((nx, ny))
                else:
                    trace.v.add((nx, ny))
                x, y = nx, ny
                continue
            if dx:
                trace.h.add((nx, ny))
            else:
                trace.v.add((nx, ny))
            x, y = nx, ny
    return trace
