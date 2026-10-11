"""Adaptive playthrough bot for Quantum Grid 2099.

The BFS solver models the pure laser puzzle; this bot plays the REAL
game with live ICE: it executes BFS routes, keeps a shadow state that
mirrors the plan, and re-plans the instant reality diverges (corruptor
mirror flips, ICE strikes, blocked moves). It restarts the node only
after a game over or an unsolvable state - the recovery a human player
has with K.

Used by tests/test_ice_playability.py (the winnability guarantee) and
scripts/audit_levels.py (full-campaign audit).
"""

import time

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
        path = solve_state(game.layout, game.player, dict(game.mirrors))
        if path is None:
            game.restart()
            resets += 1
            continue
        sp, sm = game.player, dict(game.mirrors)
        while path and not game.game_over and not game.check_win():
            if time.monotonic() - start > TIME_LIMIT_S:
                break
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
