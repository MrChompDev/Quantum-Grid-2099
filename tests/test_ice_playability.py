"""Adaptive bot playthroughs of LIVE-ICE nodes.

Unlike the BFS replay (which assumes static mirrors and no daemons),
this bot simulates the real game deterministically and:
  - plans a BFS route from the current state,
  - executes it action-by-action,
  - re-plans when ICE changes the situation (strikes, corruptor flips),
  - restarts the node (K) when the bandwidth budget is exhausted.

This is the winnability guarantee for nodes with ICE: a competent agent
that re-plans can clear them within the 100% budget.
"""

import time

import pytest

from qgrid.game import Game
from qgrid.levels import LEVELS
from qgrid.solver import solve_state

# One representative live-ICE node per daemon type/mix:
#   19 COLD STEEL (sentinel), 20 THE HUNTER (sentinel+hunter),
#   26 SIDE STEP (sentinel+pads), 34 DAEMON DANCE (corruptor)
ICE_NODES = [19, 20, 26, 34]

BUDGET_ATTEMPTS = 6
TIME_LIMIT_S = 90.0


def bot_play(index: int) -> tuple[bool, int, int]:
    """Play a node with live ICE. Returns (won, strikes_used, resets_used)."""
    game = Game(index, 100)
    assert game.daemons, f"node {index + 1} expected ICE"
    resets = 0
    start = time.monotonic()
    for _ in range(BUDGET_ATTEMPTS):
        path = solve_state(game.layout, game.player, dict(game.mirrors))
        while path:
            if game.check_win():
                return True, game.strikes, resets
            if time.monotonic() - start > TIME_LIMIT_S:
                return False, game.strikes, resets
            act = path[0]
            if act[0] == "m":
                ok = game.do_move(act[1], act[2]) == "ok"
            else:
                ok = game.do_rotate()
            if not ok:
                break  # world moved under us: re-plan
            if game.check_win():
                return True, game.strikes, resets
            if game.game_over:
                break
            # If a daemon strike recalls nothing but the plan assumed a
            # different position, or a corruptor flipped a mirror, the
            # plan's tail may be stale - just finish it and re-plan.
            path = path[1:]
        if game.check_win():
            return True, game.strikes, resets
        if game.game_over or path == () or not path:
            game.restart()
            resets += 1
    return game.check_win(), game.strikes, resets


@pytest.mark.parametrize("index", ICE_NODES)
def test_live_ice_node_winnable(index):
    defn = LEVELS[index]
    won, strikes, resets = bot_play(index)
    assert won, (
        f"NODE {index + 1:02d} - {defn.name} not winnable with live ICE "
        f"(strikes={strikes}, resets={resets})"
    )
