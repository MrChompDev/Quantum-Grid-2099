"""Adaptive bot playthroughs of LIVE-ICE nodes.

Unlike the BFS replay (which assumes static mirrors and no daemons),
this bot plays the real game deterministically via qgrid.bot: it plans
BFS routes, re-plans the instant a corruptor flips a mirror or an ICE
strike lands, and restarts the node (K) when the bandwidth budget is
exhausted.

This is the winnability guarantee for nodes with ICE: a competent agent
that re-plans can clear them within the 100% budget.
"""

import pytest

from qgrid.bot import bot_play
from qgrid.levels import LEVELS

# All 48 nodes: the full-campaign winnability guarantee.
ALL_NODES = list(range(len(LEVELS)))


@pytest.mark.parametrize("index", ALL_NODES)
def test_node_winnable_with_live_ice(index):
    defn = LEVELS[index]
    won, strikes, resets = bot_play(index)
    assert won, (
        f"NODE {index + 1:02d} - {defn.name} not winnable "
        f"(strikes={strikes}, resets={resets})"
    )
