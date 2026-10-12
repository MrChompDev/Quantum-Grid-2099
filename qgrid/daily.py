"""THE DAILY GAUNTLET for Quantum Grid 2099.

One special node per calendar day, seeded from the date so every runner
on the server faces the same layout. Difficulty ramps through the week
(Monday is a warm-up, Sunday is six daemons deep), and each day's level
is generated once and cached in the save directory so the whole server
shares it instantly.

    rng   = Random("qg-daily-YYYYMMDD")
    index = WEEKLY[weekday]      # Mon 22 ... Sun 45 (source difficulty)
    level = generate_level(index, rng), renamed + re-lore'd

Scores post to the per-day hall of fame (board name "daily-YYYYMMDD");
personal bests and attempts persist in the runner's save.
"""

import datetime as _dt
import json
import os
from random import Random

from qgrid.generator import generate_level
from qgrid.save import save_dir

# Monday..Sunday -> campaign node index the gauntlet is drawn from.
# Ramps from sector-3 warm-ups to the six-daemon Sunday finale.
WEEKLY = (22, 26, 30, 34, 37, 41, 45)

DAILY_LORE = (
    "One node. One day. Every runner on the wire faces the same floor - "
    "same daemons, same optics, same clock. The board resets at midnight. "
    "Post a score they'll have to beat."
)


def day_key(date: _dt.date | None = None) -> str:
    """YYYYMMDD string for a gauntlet day (server-local midnight)."""
    if date is None:
        date = _dt.datetime.now().astimezone().date()
    return date.strftime("%Y%m%d")


def cache_path(key: str) -> str:
    return os.path.join(save_dir(), f"daily-{key}.json")


def daily_level(date: _dt.date | None = None) -> dict:
    """LevelDef-shaped dict for the gauntlet on `date` (cached per day).

    The dict carries everything LevelDef(**...) needs plus 'date' (the
    day key). The first session of the day pays the generation cost;
    every other session reads the shared cache.
    """
    key = day_key(date)
    cached = _read_cache(key)
    if cached is not None:
        cached["rows"] = tuple(cached["rows"])  # JSON round-trips lists
        return cached
    when = date if date is not None else _dt.datetime.now().astimezone().date()
    index = WEEKLY[when.weekday()]
    data = generate_level(index, Random(f"qg-daily-{key}"))
    data["name"] = f"GAUNTLET {when.strftime('%b %d').upper()}"
    data["lore"] = DAILY_LORE
    data["intro"] = (
        f"Daily gauntlet {when.strftime('%Y-%m-%d')}. {data['intro']}"
        " Score posts to today's board - one day, one layout, everyone."
    )
    data["date"] = key
    _write_cache(key, data)
    return data


def _read_cache(key: str) -> dict | None:
    try:
        with open(cache_path(key), encoding="utf-8") as fh:
            data = json.load(fh)
        if isinstance(data, dict) and data.get("date") == key and data.get("rows"):
            return data
    except (OSError, ValueError, TypeError):
        pass
    return None


def _write_cache(key: str, data: dict) -> None:
    try:
        os.makedirs(os.path.dirname(cache_path(key)) or ".", exist_ok=True)
        tmp = f"{cache_path(key)}.tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(data, fh, sort_keys=True)
        os.replace(tmp, cache_path(key))
    except OSError:
        pass  # cache is best-effort: regenerate next time
