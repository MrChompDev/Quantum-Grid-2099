"""Adaptive playthrough bot for Quantum Grid 2099.

The BFS solver models the pure laser puzzle; this bot plays the REAL
game with live ICE: it plans routes that dodge daemon danger zones
(one-tick threat maps per kind), re-plans the instant reality diverges
(corruptor mirror flips, ICE strikes, a step that would enter fresh
danger, blocked moves), and falls back to the pure puzzle route only
when no safe route exists. It restarts the node only after a game over
or an unsolvable state - the recovery a human player has with K.

Used by tests/test_ice_playability.py (the winnability guarantee) and
scripts/audit_levels.py (full-campaign audit).
"""

import time

from qgrid import enemies as ice
from qgrid.game import BANDWIDTH_MAX, Game
from qgrid.physics import DIR4
from qgrid.solver import solve_level, solve_state

RESET_BUDGET = 8
TIME_LIMIT_S = 45.0


def _shadow_step(game, sp, sm, act) -> tuple[tuple[int, int], dict]:
    """Mirror one plan action onto the shadow (player, mirrors) state."""
    if act[0] == "m":
        nxt = (sp[0] + act[1], sp[1] + act[2])
        if 0 <= nxt[0] < game.layout.width and 0 <= nxt[1] < game.layout.height:
            terrain = game.layout.rows[nxt[1]][nxt[0]]
            if terrain not in ("#", ">", "<", "^", "v"):
                if nxt in game.layout.pads:
                    nxt = game.layout.pads[nxt]
                sp = nxt
        return sp, sm
    # rotate: underfoot first, then first adjacent in DIR4 order (same as
    # Game.do_rotate's deterministic target selection).
    target = sp if sp in sm else None
    if target is None:
        for dx, dy in DIR4:
            cand = (sp[0] + dx, sp[1] + dy)
            if cand in sm:
                target = cand
                break
    if target is not None:
        sm = dict(sm)
        sm[target] = "/" if sm[target] == "\\" else "\\"
    return sp, sm


def _danger_cells(game) -> set[tuple[int, int]]:
    """One-tick threat map: every cell a live daemon could strike this
    tick (its cell, its reach, or its pulse field)."""
    danger: set[tuple[int, int]] = set()
    layout = game.layout
    for en in game.daemons:
        if en.get("stun", 0) > 0:
            continue
        px, py = en["pos"]
        danger.add((px, py))
        kind = en["kind"]
        if kind == "volt":
            danger.update(ice._volt_field(layout, en, set()))
        elif kind == "sentinel":
            dx, dy = en["dir"]
            danger.update({(px + dx, py + dy), (px - dx, py - dy)})
        elif kind == "lancer":
            danger.update((px + dx, py + dy) for dx, dy in DIR4)
            dx, dy = en["dir"]
            danger.update({(px + dx, py + dy), (px + 2 * dx, py + 2 * dy)})
        else:  # hunter, corruptor, wraith: a step in any direction
            danger.update((px + dx, py + dy) for dx, dy in DIR4)
    return danger


def _safe_plan(game) -> tuple | None:
    """Plan around daemon danger zones; fall back to the pure route."""
    path = solve_state(
        game.layout, game.player, dict(game.mirrors), blocked=_danger_cells(game)
    )
    if path is None:
        path = solve_state(game.layout, game.player, dict(game.mirrors))
    return path


def bot_play(index: int) -> tuple[bool, int, int]:
    """Play a node with live ICE. Returns (won, strikes, resets)."""
    game = Game(index, BANDWIDTH_MAX)
    if not game.daemons:  # no ICE: the BFS replay IS the full game
        path = solve_level(game.layout)
        assert path is not None, f"node {index + 1} unsolvable"
        for act, dx, dy in path:
            if act == "m":
                assert game.do_move(dx, dy) == "ok"
            else:
                assert game.do_rotate()
        assert game.check_win()
        return True, 0, 0

    resets = 0
    won = False
    start = time.monotonic()
    while not won and resets < RESET_BUDGET:
        if time.monotonic() - start > TIME_LIMIT_S:
            break
        if game.game_over:
            game.restart()
            resets += 1
            continue
        path = _safe_plan(game)
        if path is None:
            game.restart()
            resets += 1
            continue
        sp, sm = game.player, dict(game.mirrors)
        while path and not game.game_over and not game.check_win():
            if time.monotonic() - start > TIME_LIMIT_S:
                break
            # Re-plan if the next step would walk into fresh danger.
            nxt_act = path[0]
            if nxt_act[0] == "m":
                nxt = (game.player[0] + nxt_act[1], game.player[1] + nxt_act[2])
                if nxt in game.layout.pads:
                    nxt = game.layout.pads[nxt]
                if nxt in _danger_cells(game):
                    break  # world moved under us: re-plan
            act = path[0]
            sp, sm = _shadow_step(game, sp, sm, act)
            if act[0] == "m":
                ok = game.do_move(act[1], act[2]) == "ok"
            else:
                ok = game.do_rotate()
            if not ok:
                break  # world moved under us: re-plan
            path = path[1:]
            if sm != game.mirrors:
                break  # a corruptor flipped a mirror: re-plan NOW
        won = game.check_win()
    return won, game.strikes, resets
